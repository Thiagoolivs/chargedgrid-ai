"""Configuracao de modelo do agente.

O mesmo grafo roda com qualquer um dos dois provedores comparados na Sprint 03.
A troca acontece por variavel de ambiente, sem alterar uma linha de codigo:

    MODEL_PROVIDER=groq    MODEL_ID=llama-3.3-70b-versatile
    MODEL_PROVIDER=google  MODEL_ID=gemini-2.0-flash

Nenhuma chave vive neste arquivo. As chaves saem do ambiente (ver .env.example).
"""

import os

from dotenv import load_dotenv

load_dotenv()

DEFAULT_PROVIDER = os.getenv("MODEL_PROVIDER", "groq").strip().lower()
DEFAULT_MODEL_ID = os.getenv("MODEL_ID", "llama-3.3-70b-versatile").strip()
DEFAULT_TEMPERATURE = float(os.getenv("MODEL_TEMPERATURE", "0.1"))
DEFAULT_MAX_TOKENS = int(os.getenv("MODEL_MAX_TOKENS", "1200"))

# Raciocinio interno (Gemini 3.x e equivalentes). DESLIGADO por padrao, e a
# razao e de medicao, nao de gosto: nesses modelos o `max_output_tokens` e um
# orcamento unico, dividido entre raciocinio e texto visivel. Com o limite de
# 1200 do baseline, o raciocinio consumia ~1.100 tokens e a resposta ao usuario
# era cortada no meio da frase (medido em 21/09/2026: F01 parou em 187
# caracteres com 1.196 tokens de saida). Desligado, os 1200 valem texto, como
# valem para o baseline - so assim o comparativo mede arquitetura e modelo, e
# nao quem gasta mais orcamento pensando.
DEFAULT_THINKING = os.getenv("MODEL_THINKING", "0").strip().lower() in (
    "1",
    "true",
    "sim",
    "yes",
    "on",
)

# O roteador classifica intencao. Precisa ser deterministico e curto:
# nao gera resposta para o usuario, so devolve um rotulo.
ROUTER_TEMPERATURE = 0.0
ROUTER_MAX_TOKENS = 64

# Chave de ambiente exigida por provedor.
_API_KEY_ENV = {
    "groq": "GROQ_API_KEY",
    "google": "GOOGLE_API_KEY",
}


def require_api_key(provider):
    """Falha cedo e com mensagem util quando a chave do provedor nao existe."""
    env_name = _API_KEY_ENV.get(provider)

    if env_name is None:
        raise ValueError(
            f"Provedor desconhecido: {provider!r}. "
            f"Use um destes: {', '.join(sorted(_API_KEY_ENV))}."
        )

    key = os.getenv(env_name)

    if not key:
        raise RuntimeError(
            f"{env_name} nao esta definida no ambiente. "
            f"Copie .env.example para .env e preencha antes de rodar o agente."
        )

    return key


def build_chat_model(
    provider=None,
    model_id=None,
    temperature=None,
    max_tokens=None,
    thinking=None,
):
    """Devolve um chat model LangChain ja configurado.

    Os parametros explicitos existem para o harness de avaliacao, que roda
    varios modelos no mesmo processo sem mexer em variavel de ambiente.

    `thinking` liga ou desliga o raciocinio interno onde o provedor permite.
    Quando fica em None, vale `MODEL_THINKING` do ambiente (padrao: desligado -
    ver o comentario de DEFAULT_THINKING).
    """
    provider = (provider or DEFAULT_PROVIDER).strip().lower()
    model_id = model_id or DEFAULT_MODEL_ID
    temperature = DEFAULT_TEMPERATURE if temperature is None else temperature
    max_tokens = DEFAULT_MAX_TOKENS if max_tokens is None else max_tokens
    thinking = DEFAULT_THINKING if thinking is None else thinking

    require_api_key(provider)

    if provider == "groq":
        from langchain_groq import ChatGroq

        return ChatGroq(
            model=model_id,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    if provider == "google":
        from langchain_google_genai import ChatGoogleGenerativeAI

        extra = {}

        if not thinking:
            # Os Gemini 3.x gastam o orcamento de saida em tokens de
            # raciocinio antes de emitir texto. Com os 64 tokens do roteador a
            # resposta vinha VAZIA e a rota caia sempre no fallback `tecnica`;
            # com os 1200 da geracao, a resposta saia truncada.
            extra["thinking_budget"] = 0

        return ChatGoogleGenerativeAI(
            model=model_id,
            temperature=temperature,
            max_output_tokens=max_tokens,
            **extra,
        )

    raise ValueError(f"Provedor nao suportado: {provider!r}")


def build_router_model(provider=None, model_id=None):
    """Modelo do no `router`: deterministico, curto e sem raciocinio interno.

    O roteador devolve um rotulo, nao texto para o usuario. Raciocinio interno
    aqui so consome o orcamento de saida e esvazia a resposta.
    """
    return build_chat_model(
        provider=provider,
        model_id=model_id,
        temperature=ROUTER_TEMPERATURE,
        max_tokens=ROUTER_MAX_TOKENS,
        thinking=False,
    )


def describe_model(provider=None, model_id=None, temperature=None):
    """Identificador legivel usado nos resultados dos experimentos."""
    provider = (provider or DEFAULT_PROVIDER).strip().lower()
    model_id = model_id or DEFAULT_MODEL_ID
    temperature = DEFAULT_TEMPERATURE if temperature is None else temperature

    return f"{provider}/{model_id}@t{temperature}"
