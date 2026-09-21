"""Utilitarios compartilhados pelos harnesses de avaliacao."""

import json
import re
import sys
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
EVALS_DIR = BASE_DIR / "evals"
CASES_PATH = EVALS_DIR / "cases.json"
RESULTS_DIR = EVALS_DIR / "results"


def bootstrap_path():
    """Garante que `app` e `agent_core` sejam importaveis de qualquer cwd."""
    if str(BASE_DIR) not in sys.path:
        sys.path.insert(0, str(BASE_DIR))


def load_cases():
    return json.loads(CASES_PATH.read_text(encoding="utf-8"))


def slugify(name):
    return re.sub(r"[^a-zA-Z0-9]+", "_", name).strip("_").lower()


def extract_usage(message):
    """Extrai (tokens_in, tokens_out) de uma resposta de LLM.

    A estrutura muda entre provedores e entre versoes do LangChain, entao aqui
    tudo e opcional: se nada for encontrado devolve (None, None) em vez de
    levantar. Contagem de token nao pode derrubar a rodada de experimentos.
    """
    if message is None:
        return None, None

    usage = getattr(message, "usage_metadata", None)

    if isinstance(usage, dict):
        tokens_in = usage.get("input_tokens")
        tokens_out = usage.get("output_tokens")

        if tokens_in is not None or tokens_out is not None:
            return tokens_in, tokens_out

    metadata = getattr(message, "response_metadata", None)

    if isinstance(metadata, dict):
        for key in ("token_usage", "usage", "usage_metadata"):
            block = metadata.get(key)

            if not isinstance(block, dict):
                continue

            tokens_in = block.get("prompt_tokens") or block.get("input_tokens")
            tokens_out = (
                block.get("completion_tokens")
                or block.get("output_tokens")
                or block.get("candidates_token_count")
            )

            if tokens_in is not None or tokens_out is not None:
                return tokens_in, tokens_out

    return None, None


def is_rate_limit_error(exc):
    """Heuristica para 429 / cota estourada, que e o erro esperado no free tier."""
    text = f"{type(exc).__name__} {exc}".lower()
    markers = ("429", "rate limit", "rate_limit", "quota", "resource_exhausted", "too many requests")
    return any(marker in text for marker in markers)


def call_with_retry(fn, max_retries=4, base_delay=5.0, label=""):
    """Executa `fn`, repetindo em erro de limite de requisicao.

    O free tier do Gemini estoura por minuto. Sem isso o harness morre no meio
    da rodada e a bateria inteira e perdida.
    """
    attempt = 0

    while True:
        try:
            return fn()
        except Exception as exc:
            if not is_rate_limit_error(exc) or attempt >= max_retries:
                raise

            delay = base_delay * (2 ** attempt)
            attempt += 1
            print(
                f"      [limite de requisicao] {label} "
                f"tentativa {attempt}/{max_retries}, aguardando {delay:.0f}s",
                flush=True,
            )
            time.sleep(delay)


async def call_with_retry_async(fn, max_retries=4, base_delay=5.0, label=""):
    """Versao assincrona de call_with_retry. O ask_ai da Sprint 2 e async."""
    import asyncio

    attempt = 0

    while True:
        try:
            return await fn()
        except Exception as exc:
            if not is_rate_limit_error(exc) or attempt >= max_retries:
                raise

            delay = base_delay * (2 ** attempt)
            attempt += 1
            print(
                f"      [limite de requisicao] {label} "
                f"tentativa {attempt}/{max_retries}, aguardando {delay:.0f}s",
                flush=True,
            )
            await asyncio.sleep(delay)


def write_results(path, payload):
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"\nResultados gravados em {path}")


def empty_result(case, model_name):
    """Esqueleto de resultado. `adequado` fica None de proposito.

    A avaliacao qualitativa e manual: julgar resposta com outro LLM seria mais
    um ponto de falha e nao e pedido pela rubrica.
    """
    return {
        "model": model_name,
        "case": case["id"],
        "tipo": case["tipo"],
        "esperado": case["esperado"],
        "rota": [],
        "resposta": "",
        "latencia_s": 0.0,
        "tokens_in": None,
        "tokens_out": None,
        "turnos": len(case["turns"]),
        "turnos_detalhe": [],
        "erro": None,
        "adequado": None,
        "nota": "",
    }
