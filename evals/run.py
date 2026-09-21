"""Roda a bateria de casos contra o agente novo (agent_core), por modelo.

    python evals/run.py                              # os dois modelos padrao
    python evals/run.py --model groq/openai/gpt-oss-120b
    python evals/run.py --model google/gemini-3.6-flash --sleep 4
    python evals/run.py --list-google-models         # nomes validos para a chave

Cada caso recebe um thread_id novo (uuid4) e todos os turnos do caso usam o
MESMO thread_id - e isso que exercita a memoria. A avaliacao qualitativa
(`adequado`) fica em branco para preenchimento manual.
"""

import argparse
import time
import uuid
from pathlib import Path

from common import (
    RESULTS_DIR,
    bootstrap_path,
    call_with_retry,
    empty_result,
    extract_usage,
    load_cases,
    slugify,
    write_results,
)

bootstrap_path()

# Os dois modelos do comparativo da secao 5. Nomes confirmados contra a API
# em 21/09/2026: o `llama-3.3-70b-versatile` da Sprint 2 foi descontinuado pela
# Groq e o `gemini-2.0-flash` nao e mais servido a chaves novas.
DEFAULT_MODELS = [
    "groq/openai/gpt-oss-120b",
    "google/gemini-3.6-flash",
]

# Espera entre turnos, por provedor. O free tier do Gemini limita por minuto.
DEFAULT_SLEEP = {"groq": 0.5, "google": 4.0}


def parse_model(spec):
    if "/" not in spec:
        raise ValueError(
            f"Modelo {spec!r} invalido. Use provedor/modelo, "
            "ex: groq/openai/gpt-oss-120b"
        )

    provider, model_id = spec.split("/", 1)
    return provider.strip().lower(), model_id.strip()


def list_google_models():
    """Lista os modelos disponiveis para a chave configurada.

    Nome de modelo muda com o tempo; o nome exato usado na rodada vai para o
    relatorio.
    """
    import google.generativeai as genai

    from agent_core.config import require_api_key

    genai.configure(api_key=require_api_key("google"))

    print("Modelos disponiveis para esta chave (suportam generateContent):\n")

    for model in genai.list_models():
        if "generateContent" in getattr(model, "supported_generation_methods", []):
            print(f"  {model.name}")


def run_case(graph, case, model_name, sleep_seconds):
    from agent_core.graph import answer

    result = empty_result(case, model_name)
    thread_id = str(uuid.uuid4())

    total_in = 0
    total_out = 0
    saw_usage = False

    for index, turn in enumerate(case["turns"], start=1):
        started = time.perf_counter()

        try:
            payload = call_with_retry(
                lambda: answer(thread_id, turn, graph=graph),
                label=f"{model_name} {case['id']} turno {index}",
            )
        except Exception as exc:
            elapsed = time.perf_counter() - started
            result["erro"] = f"{type(exc).__name__}: {exc}"
            result["latencia_s"] = round(result["latencia_s"] + elapsed, 3)
            print(f"      ERRO no turno {index}: {result['erro']}")
            break

        elapsed = time.perf_counter() - started
        tokens_in, tokens_out = extract_usage(payload.get("message"))

        if tokens_in is not None or tokens_out is not None:
            saw_usage = True
            total_in += tokens_in or 0
            total_out += tokens_out or 0

        result["rota"].append(payload.get("route"))
        result["resposta"] = payload.get("response", "")
        result["latencia_s"] = round(result["latencia_s"] + elapsed, 3)
        result["turnos_detalhe"].append(
            {
                "turno": index,
                "pergunta": turn,
                "resposta": payload.get("response", ""),
                "rota": payload.get("route"),
                "blocked_reason": payload.get("blocked_reason"),
                "sources": [s.get("source") for s in payload.get("sources", [])],
                "latencia_s": round(elapsed, 3),
                "tokens_in": tokens_in,
                "tokens_out": tokens_out,
            }
        )

        print(
            f"      turno {index}/{len(case['turns'])} "
            f"rota={payload.get('route')} {elapsed:.2f}s"
        )

        if sleep_seconds:
            time.sleep(sleep_seconds)

    if saw_usage:
        result["tokens_in"] = total_in
        result["tokens_out"] = total_out

    return result


def run_model(spec, cases, sleep_seconds=None, temperature=None):
    from agent_core.config import build_chat_model, build_router_model
    from agent_core.graph import build_graph

    provider, model_id = parse_model(spec)

    if sleep_seconds is None:
        sleep_seconds = DEFAULT_SLEEP.get(provider, 1.0)

    chat_model = build_chat_model(
        provider=provider,
        model_id=model_id,
        temperature=temperature,
    )
    router_model = build_router_model(provider=provider, model_id=model_id)
    graph = build_graph(chat_model=chat_model, router_model=router_model)

    model_name = spec if temperature is None else f"{spec}@t{temperature}"

    print(f"\n{'=' * 68}\nMODELO: {model_name}\n{'=' * 68}")

    results = []

    for case in cases:
        print(f"  [{case['id']}] {case['tipo']}")
        results.append(run_case(graph, case, model_name, sleep_seconds))

    path = RESULTS_DIR / f"agent_{slugify(model_name)}.json"
    write_results(
        path,
        {
            "alvo": "agente",
            "model": model_name,
            "provider": provider,
            "model_id": model_id,
            "temperature": temperature,
            "total_casos": len(results),
            "resultados": results,
        },
    )

    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--model",
        action="append",
        dest="models",
        help="provedor/modelo. Pode repetir. Padrao: os dois do comparativo.",
    )
    parser.add_argument(
        "--sleep",
        type=float,
        default=None,
        help="segundos entre turnos (padrao por provedor)",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=None,
        help="sobrescreve a temperatura (experimento de parametro)",
    )
    parser.add_argument(
        "--list-google-models",
        action="store_true",
        help="lista os modelos Gemini validos para a chave e sai",
    )
    args = parser.parse_args()

    if args.list_google_models:
        list_google_models()
        return 0

    cases = load_cases()
    models = args.models or DEFAULT_MODELS

    print(f"{len(cases)} casos x {len(models)} modelo(s)")

    for spec in models:
        try:
            run_model(
                spec,
                cases,
                sleep_seconds=args.sleep,
                temperature=args.temperature,
            )
        except Exception as exc:
            # Um modelo indisponivel nao pode levar junto o resultado do outro.
            print(f"\n!! modelo {spec} falhou: {type(exc).__name__}: {exc}")

    print("\nPreencha o campo 'adequado' nos JSONs e rode:")
    print("    python evals/comparativo.py")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
