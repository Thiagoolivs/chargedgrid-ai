"""Roda a MESMA bateria contra o baseline da Sprint 2 - o "antes".

    python evals/run_legacy.py

IMPORTANTE: este harness exercita o caminho de producao da Sprint 2, nao uma
aproximacao dele. Usa o mesmo `ask_ai` assincrono, o mesmo `retrieve_context`
e o mesmo modulo `database` que `app/routes/chat.py` usa, montando o historico
exatamente como a rota monta: buscando as mensagens da conversa no SQLite
antes da chamada e gravando pergunta e resposta depois.

A Sprint 2 TEM memoria - manual, com janela das ultimas 10 mensagens
(`history[-10:]` em ai_service.py) persistida em SQLite. O comparativo da
Sprint 03 e portanto **memoria manual x memoria gerenciada pelo framework**,
que e exatamente o que a secao 6 pede. Nao e "sem memoria x com memoria".

Duas caracteristicas do baseline que valem observar nos resultados:

1. `ask_ai` corta antes de olhar o historico quando o contexto vem vazio:
   `if not context: return "Essa informacao nao esta documentada."`. Uma
   pergunta sobre a propria conversa cujo retrieval nao trouxe nada morre ai.
2. Toda pergunta passa pelo RAG, inclusive as conversacionais. Nao ha
   roteamento - por isso a rota registrada e sempre `rag_sempre`.

Limitacao de medicao: `ask_ai` devolve so a string da resposta, sem o objeto
de usage do SDK. Medir tokens exigiria alterar `ai_service.py`, que precisa
ficar intacto para o comparativo valer. Tokens ficam None; latencia e
qualidade sao medidas normalmente.
"""

import asyncio
import time

from common import (
    RESULTS_DIR,
    bootstrap_path,
    call_with_retry_async,
    empty_result,
    load_cases,
    write_results,
)

bootstrap_path()

MODEL_NAME = "baseline-sprint2/ask_ai+llama-3.3-70b-versatile"
SLEEP_SECONDS = 0.5


async def run_case(case):
    from app import database
    from app.services.ai_service import ask_ai
    from app.services.rag_service import retrieve_context

    result = empty_result(case, MODEL_NAME)

    # Uma conversa por caso, como faria um usuario real na interface.
    # database.MAX_CONVERSATIONS poda as mais antigas, mas so no momento da
    # criacao - o caso em andamento nunca perde o proprio historico.
    conversa = database.create_conversation(f"eval {case['id']}")
    result["conversation_id"] = conversa["id"]

    for index, turn in enumerate(case["turns"], start=1):
        started = time.perf_counter()

        try:
            # Historico montado como app/routes/chat.py monta: mensagens ja
            # gravadas, sem a pergunta atual (essa vai no parametro `message`).
            msgs = database.get_messages(conversa["id"])
            history = [{"role": m["role"], "content": m["content"]} for m in msgs]

            retrieval = retrieve_context(turn)
            resposta = await call_with_retry_async(
                lambda: ask_ai(
                    message=turn,
                    context=retrieval["context"],
                    history=history,
                ),
                label=f"baseline {case['id']} turno {index}",
            )

            database.add_message(conversa["id"], "user", turn)
            database.add_message(
                conversa["id"], "assistant", resposta, retrieval["sources"]
            )
        except Exception as exc:
            elapsed = time.perf_counter() - started
            result["erro"] = f"{type(exc).__name__}: {exc}"
            result["latencia_s"] = round(result["latencia_s"] + elapsed, 3)
            print(f"      ERRO no turno {index}: {result['erro']}")
            break

        elapsed = time.perf_counter() - started

        result["rota"].append("rag_sempre")
        result["resposta"] = resposta
        result["latencia_s"] = round(result["latencia_s"] + elapsed, 3)
        result["turnos_detalhe"].append(
            {
                "turno": index,
                "pergunta": turn,
                "resposta": resposta,
                "rota": "rag_sempre",
                "historico_recebido": len(history),
                "contexto_vazio": not retrieval["context"],
                "blocked_reason": None,
                "sources": [s.get("source") for s in retrieval.get("sources", [])],
                "latencia_s": round(elapsed, 3),
                "tokens_in": None,
                "tokens_out": None,
            }
        )

        print(
            f"      turno {index}/{len(case['turns'])} "
            f"historico={len(history)} msgs {elapsed:.2f}s"
        )

        if SLEEP_SECONDS:
            await asyncio.sleep(SLEEP_SECONDS)

    return result


async def run_all():
    from app import database

    database.init_db()
    cases = load_cases()

    print(f"{'=' * 68}\nBASELINE (antes) - Sprint 2: {MODEL_NAME}\n{'=' * 68}")
    print("Memoria manual: historico do SQLite, janela das ultimas 10 mensagens.")
    print(f"{len(cases)} casos\n")

    results = []

    for case in cases:
        print(f"  [{case['id']}] {case['tipo']}")
        results.append(await run_case(case))

    write_results(
        RESULTS_DIR / "baseline_sprint2.json",
        {
            "alvo": "baseline",
            "model": MODEL_NAME,
            "provider": "groq",
            "model_id": "llama-3.3-70b-versatile",
            "temperature": 0.05,
            "memoria": "manual: SQLite + janela de 10 mensagens",
            "roteamento": "nenhum: todo turno passa pelo RAG",
            "tokens_medidos": False,
            "total_casos": len(results),
            "resultados": results,
        },
    )

    print("\nPreencha o campo 'adequado' no JSON e rode:")
    print("    python evals/comparativo.py")


def main():
    asyncio.run(run_all())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
