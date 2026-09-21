"""Nos do grafo: router, retrieve, generate e refuse.

Os nos que dependem de LLM sao construidos por fabricas que recebem o modelo
ja instanciado. E isso que permite rodar o mesmo grafo com Groq e com Gemini
no mesmo processo (harness de avaliacao) e testar o grafo com um modelo falso,
sem chave de API.
"""

import json
import re

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from agent_core.guardrails import REFUSAL_INJECTION, REFUSAL_OUT_OF_SCOPE
from agent_core.messages import message_text
from agent_core.prompt import build_system_prompt, turn_instructions

ROUTE_TECHNICAL = "tecnica"
ROUTE_CONVERSATION = "conversa"
ROUTE_OUT_OF_SCOPE = "fora_escopo"
VALID_ROUTES = {ROUTE_TECHNICAL, ROUTE_CONVERSATION, ROUTE_OUT_OF_SCOPE}

# Rota usada quando o classificador falha ou devolve lixo. Cair na busca
# documental e o erro mais barato: no pior caso o contexto vem irrelevante e o
# modelo o ignora. Cair em `fora_escopo` recusaria uma pergunta legitima.
ROUTE_FALLBACK = ROUTE_TECHNICAL

ROUTER_SYSTEM_PROMPT = """Voce e o classificador de intencao do ChargeGrid AI,
assistente tecnico de carregadores de veiculos eletricos GoodWe HCA-G2.

Leia o HISTORICO e a ULTIMA MENSAGEM e escolha exatamente uma rota:

REGRA DE DESEMPATE, aplique ANTES de tudo: o que decide a rota e o que a
mensagem PEDE, nao o assunto que ela cita. Mencionar carregador, modelo ou
eletroposto NAO torna a mensagem tecnica. So e "tecnica" quando a mensagem pede
um dado que precisa sair da documentacao GoodWe.

- "tecnica": a mensagem PERGUNTA algo cuja resposta esta na documentacao dos
  carregadores GoodWe ou da eletromobilidade - registros Modbus, LED,
  instalacao, Dynamic Load Control, RFID, faturamento de energia,
  especificacoes, diagnostico de falha. Use esta rota tambem quando a pergunta
  tiver angulo juridico, financeiro ou de intervencao eletrica MAS o assunto
  for carregador ou eletroposto: o assistente trata desses casos encaminhando a
  um profissional.

- "conversa": a mensagem NAO pede dado da documentacao. Cai aqui quando ela:
  (a) apenas INFORMA um dado do cenario do proprio usuario - local, quantidade,
      modelo instalado, horario, volume de atendimento - sem fazer pergunta;
  (b) pergunta sobre algo que o USUARIO ja disse nesta conversa;
  (c) pede resumo do que foi informado na conversa;
  (d) e saudacao, agradecimento ou confirmacao.
  Frase afirmativa sem ponto de interrogacao quase sempre e "conversa".

- "fora_escopo": o assunto nao tem relacao nenhuma com carregadores, veiculos
  eletricos ou energia. Exemplos: receita de bolo, politica, futebol, pedido
  de codigo generico.

EXEMPLOS RESOLVIDOS:
"Estou utilizando um carregador no condominio Solar Park." -> conversa
  (informa o cenario, nao pergunta nada)
"Existem 12 vagas de carregamento." -> conversa
  (informa um numero do cenario do usuario)
"Tenho um GW22K-HCA-20 instalado." -> conversa
  (informa o modelo que possui, nao pede especificacao)
"Ele esta conectado a um inversor GoodWe via Modbus TCP." -> conversa
  (informa a topologia da instalacao dele)
"Meu eletroposto atende 40 carros por dia." -> conversa
"O horario de pico e das 18h as 21h." -> conversa
"Qual modelo eu disse que tenho?" -> conversa
"Com base no que informei, resuma meu cenario de operacao." -> conversa
"Qual o registro Modbus para ligar o carregamento?" -> tecnica
"O LED vermelho esta fixo, o que verifico primeiro?" -> tecnica
"Qual a temperatura maxima de operacao do GW22K-HCA-20?" -> tecnica
"Posso processar meu condominio por nao instalar carregadores?" -> tecnica
"Me ensina a fazer um bolo de cenoura." -> fora_escopo

Responda SOMENTE com um JSON de um campo, sem texto em volta:
{"rota": "tecnica"} ou {"rota": "conversa"} ou {"rota": "fora_escopo"}"""

# Ate quantas mensagens anteriores entram no prompt do classificador. O
# roteador precisa do historico (e o que faz "quantas vagas eu disse?" virar
# `conversa`), mas nao precisa da conversa inteira.
ROUTER_HISTORY_LIMIT = 6


def _render_history(messages):
    """Historico compacto para o classificador."""
    previous = messages[:-1][-ROUTER_HISTORY_LIMIT:]

    if not previous:
        return "(sem historico: primeira mensagem da conversa)"

    lines = []

    for message in previous:
        role = "USUARIO" if isinstance(message, HumanMessage) else "ASSISTENTE"
        text = message_text(message).strip().replace("\n", " ")
        lines.append(f"{role}: {text[:300]}")

    return "\n".join(lines)


def parse_route(raw_text):
    """Extrai a rota de uma resposta de LLM, tolerando formato sujo.

    Aceita o JSON pedido, JSON embrulhado em markdown e ate a palavra solta.
    Devolve None quando nada reconhecivel aparece - quem chama decide o
    fallback.
    """
    if not raw_text:
        return None

    text = raw_text.strip()

    match = re.search(r"\{.*\}", text, re.DOTALL)

    if match:
        try:
            payload = json.loads(match.group(0))
            candidate = str(payload.get("rota", "")).strip().lower()

            if candidate in VALID_ROUTES:
                return candidate
        except (json.JSONDecodeError, AttributeError, TypeError):
            pass

    lowered = text.lower()

    for route in VALID_ROUTES:
        if re.search(rf"\b{route}\b", lowered):
            return route

    return None


def make_router_node(router_model):
    """No classificador. Decide qual aresta condicional o grafo segue."""

    def router(state):
        messages = state["messages"]
        last_message = message_text(messages[-1]) if messages else ""

        prompt = (
            f"HISTORICO DA CONVERSA:\n{_render_history(messages)}\n\n"
            f"ULTIMA MENSAGEM DO USUARIO:\n{last_message}\n\n"
            "Rota:"
        )

        try:
            response = router_model.invoke(
                [
                    SystemMessage(content=ROUTER_SYSTEM_PROMPT),
                    HumanMessage(content=prompt),
                ]
            )
            route = parse_route(message_text(response))
        except Exception:
            # Falha do classificador nunca derruba a resposta ao usuario.
            route = None

        return {"route": route or ROUTE_FALLBACK}

    return router


# O rag_service carrega o indice FAISS e o modelo de embedding no import, o que
# e lento e falha quando o indice nao foi gerado. Import tardio e cacheado: o
# agente so paga esse custo quando realmente precisa buscar documentacao.
_retrieve_context_fn = None
_retrieve_import_error = None


def _get_retrieve_context():
    global _retrieve_context_fn, _retrieve_import_error

    if _retrieve_context_fn is not None or _retrieve_import_error is not None:
        return _retrieve_context_fn

    try:
        from app.services.rag_service import retrieve_context

        _retrieve_context_fn = retrieve_context
    except Exception as exc:  # indice ausente, dependencia faltando, etc.
        _retrieve_import_error = exc

    return _retrieve_context_fn


def retrieve(state):
    """Busca documental. Consome o rag_service existente, sem altera-lo."""
    messages = state["messages"]
    question = message_text(messages[-1]) if messages else ""

    retrieve_context = _get_retrieve_context()

    if retrieve_context is None:
        # Sem indice, o agente segue respondendo pelo historico em vez de
        # quebrar a conversa inteira. O relatorio registra a degradacao.
        return {"context": "", "sources": []}

    try:
        retrieval = retrieve_context(question)
    except Exception:
        return {"context": "", "sources": []}

    return {
        "context": retrieval.get("context", ""),
        "sources": retrieval.get("sources", []),
    }


def make_generate_node(chat_model):
    """No de geracao. Recebe historico completo + contexto da rodada."""

    def generate(state):
        system_text = build_system_prompt()
        instructions = turn_instructions(
            state.get("route"),
            state.get("context", ""),
        )

        # Um unico SystemMessage seguido do historico. Evita system message no
        # fim da lista, que nem todo provedor aceita, e mantem o historico
        # intacto: nada de contexto recuperado e persistido em `messages`.
        conversation = [
            SystemMessage(content=f"{system_text}\n\n---\n\n{instructions}")
        ] + list(state["messages"])

        response = chat_model.invoke(conversation)

        # A AIMessage original e devolvida sem reconstrucao para preservar
        # `usage_metadata`, que o harness le para contar tokens.
        return {"messages": [response]}

    return generate


def refuse(state):
    """No de recusa. Atende tanto bloqueio de guardrail quanto fora de escopo."""
    if state.get("blocked_reason"):
        text = REFUSAL_INJECTION
        route = "bloqueado"
    else:
        text = REFUSAL_OUT_OF_SCOPE
        route = ROUTE_OUT_OF_SCOPE

    return {
        "messages": [AIMessage(content=text)],
        "route": route,
    }
