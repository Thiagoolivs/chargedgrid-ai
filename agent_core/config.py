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
):
    """Devolve um chat model LangChain ja configurado.

    Os parametros explicitos existem para o harness de avaliacao, que roda
    varios modelos no mesmo processo sem mexer em variavel de ambiente.
    """
    provider = (provider or DEFAULT_PROVIDER).strip().lower()
    model_id = model_id or DEFAULT_MODEL_ID
    temperature = DEFAULT_TEMPERATURE if temperature is None else temperature
    max_tokens = DEFAULT_MAX_TOKENS if max_tokens is None else max_tokens

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

        return ChatGoogleGenerativeAI(
            model=model_id,
            temperature=temperature,
            max_output_tokens=max_tokens,
        )

    raise ValueError(f"Provedor nao suportado: {provider!r}")


def describe_model(provider=None, model_id=None, temperature=None):
    """Identificador legivel usado nos resultados dos experimentos."""
    provider = (provider or DEFAULT_PROVIDER).strip().lower()
    model_id = model_id or DEFAULT_MODEL_ID
    temperature = DEFAULT_TEMPERATURE if temperature is None else temperature

    return f"{provider}/{model_id}@t{temperature}"
