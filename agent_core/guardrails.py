"""Guardrails de entrada e saida.

Duas camadas, com pesos bem diferentes:

1. `guard_in` - filtro leve por padrao textual sobre a mensagem do usuario.
   E uma defesa RASA e assumidamente incompleta: pega tentativas escritas em
   portugues direto e nada mais. Parafrase, outro idioma ou codificacao passam.
   Ela existe para barrar o caso obvio antes de gastar chamada de LLM.

2. O system prompt com as REGRAS INVIOLAVEIS (ver prompt.py) e a camada
   principal. E ele que sustenta os casos que o regex nao alcanca.

3. `guard_out` - ultima barreira. Se a resposta carregar trecho literal do
   system prompt, ela e trocada por uma recusa antes de chegar ao usuario.
"""

import re

from agent_core.messages import message_text
from agent_core.prompt import RULES_MARKER, load_base_prompt, strip_accents

BLOCK_REASON_INJECTION = "injection"
BLOCK_REASON_LEAK = "leak"

REFUSAL_INJECTION = (
    "Nao posso atender esse pedido. Minhas instrucoes de operacao sao fixas e "
    "nao podem ser reveladas, alteradas ou suspensas por mensagem do usuario.\n\n"
    "Sigo disponivel como assistente tecnico dos carregadores GoodWe HCA-G2. "
    "Posso ajudar com registros Modbus, Dynamic Load Control, autenticacao "
    "RFID, diagnostico de LED e especificacoes dos modelos GW7K, GW11K e "
    "GW22K. O que voce precisa?"
)

REFUSAL_OUT_OF_SCOPE = (
    "Esse assunto esta fora do meu escopo. Sou o assistente tecnico dos "
    "carregadores de veiculos eletricos GoodWe HCA-G2.\n\n"
    "Posso ajudar com instalacao, operacao, registros Modbus, Dynamic Load "
    "Control, autenticacao RFID, faturamento de energia e diagnostico de "
    "falhas. Para assuntos juridicos, financeiros ou de intervencao eletrica, "
    "procure um profissional habilitado na area."
)

REFUSAL_LEAK = (
    "Nao posso reproduzir minhas instrucoes internas.\n\n"
    "Posso responder sobre operacao, configuracao e diagnostico dos "
    "carregadores GoodWe HCA-G2. Reformule a pergunta nesse escopo."
)

# Padroes aplicados sobre o texto ja em minusculas e sem acento, para que
# "instrucoes" e "instrucoes" casem com a mesma regra.
INJECTION_PATTERNS = [
    r"ignore\s+(todas\s+)?(as\s+)?(suas\s+)?instrucoes",
    r"ignore\s+(as\s+)?(instrucoes\s+)?anteriores",
    r"ignore\s+tudo\s+(que\s+)?(foi\s+dito|acima|anterior)",
    r"esqueca\s+(tudo|o\s+contexto|as\s+instrucoes|suas\s+instrucoes)",
    r"desconsidere\s+(as\s+|suas\s+)*instrucoes",
    r"(revele|mostre|exiba|imprima)\s+(o\s+|seu\s+|as\s+)*system\s*prompt",
    r"qual\s+e\s+o\s+seu\s+system\s*prompt",
    r"(repita|reproduza)\s+(as\s+|suas\s+)*instrucoes",
    r"voce\s+nao\s+trabalha\s+mais\s+para",
    r"modo\s+desenvolvedor",
    r"developer\s+mode",
    r"sem\s+restricoes",
    r"sem\s+regras",
    r"a\s+partir\s+de\s+agora\s+voce\s+(e|sera|vai\s+ser|passa\s+a\s+ser)",
    r"aja\s+como\s+(um|uma)\s+assistente\s+(generico|generica|sem\b)",
    r"assistente\s+(generico|generica)",
    r"finja\s+que\s+voce\s+(e|nao)",
    r"jailbreak",
]

COMPILED_INJECTION_PATTERNS = [
    re.compile(pattern) for pattern in INJECTION_PATTERNS
]

# Comprimento minimo de uma linha do system prompt para ser tratada como
# assinatura de vazamento. Linhas curtas ("### [DETALHES TECNICOS]") fazem
# parte do formato legitimo de resposta e nao podem disparar o bloqueio.
LEAK_LINE_MIN_LEN = 45


def _normalize(text):
    return strip_accents(text or "").lower()


def detect_injection(message):
    """Devolve o padrao que casou, ou None. Separado do no para ser testavel."""
    normalized = _normalize(message)

    for pattern in COMPILED_INJECTION_PATTERNS:
        if pattern.search(normalized):
            return pattern.pattern

    return None


def _leak_signatures():
    """Linhas longas e distintivas do system prompt do baseline."""
    signatures = []

    for line in load_base_prompt().splitlines():
        stripped = line.strip()

        if len(stripped) < LEAK_LINE_MIN_LEN:
            continue

        # Cabecalhos e marcadores de secao sao formato de resposta, nao segredo.
        if stripped.startswith(("#", "[")):
            continue

        signatures.append(_normalize(stripped))

    return signatures


LEAK_SIGNATURES = _leak_signatures()


def detect_leak(answer):
    """Verifica se a resposta carrega trecho literal do system prompt."""
    normalized = _normalize(answer)

    if _normalize(RULES_MARKER) in normalized:
        return RULES_MARKER

    for signature in LEAK_SIGNATURES:
        if signature in normalized:
            return signature[:60]

    return None


def guard_in(state):
    """No de entrada do grafo. Marca a mensagem como bloqueada ou libera."""
    messages = state["messages"]
    last_user_message = message_text(messages[-1]) if messages else ""

    matched = detect_injection(last_user_message)

    if matched:
        return {
            "blocked_reason": BLOCK_REASON_INJECTION,
            "context": "",
            "sources": [],
            "route": "bloqueado",
        }

    return {
        "blocked_reason": None,
        "context": "",
        "sources": [],
    }


def guard_out(state):
    """No de saida. Troca a resposta por uma recusa se houver vazamento."""
    messages = state["messages"]

    if not messages:
        return {}

    last = messages[-1]
    leaked = detect_leak(message_text(last))

    if not leaked:
        return {}

    # Reescreve a ultima mensagem no lugar, preservando o id para que o
    # reducer `add_messages` substitua em vez de acrescentar outro turno.
    last.content = REFUSAL_LEAK

    return {
        "messages": [last],
        "blocked_reason": BLOCK_REASON_LEAK,
    }
