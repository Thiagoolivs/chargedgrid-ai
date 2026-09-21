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
de usage do SDK. Para medir tokens sem tocar em `ai_service.py`, este harness
intercepta o cliente Groq do modulo e le o `usage` da resposta crua. O codigo
do baseline continua byte a byte o mesmo.

SUBSTITUICAO DE MODELO (--model): a Groq descontinuou o
`llama-3.3-70b-versatile` que esta fixo em `ai_service.py:48`; toda chamada
retorna 404 model_not_found. Sem substituicao nao existe coluna "antes" no
comparativo da secao 6. A troca e feita AQUI, interceptando o argumento
`model` na chamada do SDK, e nao no arquivo do baseline - prompt, temperatura,
janela de historico, corte `if not context` e fluxo continuam identicos. O
relatorio declara a substituicao.
"""

import argparse
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

# Modelo escrito em app/services/ai_service.py:48. Mantido aqui so como
# registro do que a Sprint 2 usava - ele nao existe mais no catalogo da Groq.
ORIGINAL_MODEL_ID = "llama-3.3-70b-versatile"

# Substituto padrao. Mesmo provedor, para que a comparacao troque arquitetura e
# modelo, nunca provedor. Declarado no relatorio.
DEFAULT_MODEL_ID = "openai/gpt-oss-120b"

SLEEP_SECONDS = 0.5

# Preenchido por `patch_baseline_model`. O usage da ultima chamada fica aqui
# porque `ask_ai` devolve so a string; ler o objeto cru e a unica forma de
# contar tokens do baseline sem editar o arquivo protegido.
LAST_USAGE = {"tokens_in": None, "tokens_out": None}


def patch_baseline_model(model_id):
    """Intercepta o cliente Groq de `ai_service` sem alterar o modulo.

    Faz duas coisas na mesma camada, e so aqui no harness:

    1. substitui o `model=` da chamada, porque o modelo original foi retirado
       do catalogo do provedor;
    2. guarda o `usage` da resposta crua, para o comparativo ter tokens dos
       dois lados.

    O arquivo `app/services/ai_service.py` continua intacto - e ele o "antes"
    que a secao 6 manda comparar.
    """
    from app.services import ai_service

    original_create = ai_service.client.chat.completions.create

    async def create(*args, **kwargs):
        kwargs["model"] = model_id
        completion = await original_create(*args, **kwargs)

        usage = getattr(completion, "usage", None)
        LAST_USAGE["tokens_in"] = getattr(usage, "prompt_tokens", None)
        LAST_USAGE["tokens_out"] = getattr(usage, "completion_tokens", None)

        return completion

    ai_service.client.chat.completions.create = create


async def run_case(case, model_name):
    from app import database
    from app.services.ai_service import ask_ai
    from app.services.rag_service import retrieve_context

    result = empty_result(case, model_name)
    total_in = 0
    total_out = 0
    saw_usage = False

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
            LAST_USAGE["tokens_in"] = None
            LAST_USAGE["tokens_out"] = None
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
        tokens_in = LAST_USAGE["tokens_in"]
        tokens_out = LAST_USAGE["tokens_out"]

        if tokens_in is not None or tokens_out is not None:
            saw_usage = True
            total_in += tokens_in or 0
            total_out += tokens_out or 0

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
                "tokens_in": tokens_in,
                "tokens_out": tokens_out,
            }
        )

        print(
            f"      turno {index}/{len(case['turns'])} "
            f"historico={len(history)} msgs {elapsed:.2f}s"
        )

        if SLEEP_SECONDS:
            await asyncio.sleep(SLEEP_SECONDS)

    if saw_usage:
        result["tokens_in"] = total_in
        result["tokens_out"] = total_out

    return result


async def run_all(model_id):
    from app import database

    patch_baseline_model(model_id)

    database.init_db()
    cases = load_cases()

    model_name = f"baseline-sprint2/ask_ai+{model_id}"
    substituido = model_id != ORIGINAL_MODEL_ID

    print(f"{'=' * 68}\nBASELINE (antes) - Sprint 2: {model_name}\n{'=' * 68}")
    print("Memoria manual: historico do SQLite, janela das ultimas 10 mensagens.")

    if substituido:
        print(
            f"Modelo SUBSTITUIDO: {ORIGINAL_MODEL_ID} (descontinuado na Groq) "
            f"-> {model_id}."
        )
        print("ai_service.py NAO foi alterado: a troca e feita no cliente, aqui.")

    print(f"{len(cases)} casos\n")

    results = []

    for case in cases:
        print(f"  [{case['id']}] {case['tipo']}")
        results.append(await run_case(case, model_name))

    write_results(
        RESULTS_DIR / "baseline_sprint2.json",
        {
            "alvo": "baseline",
            "model": model_name,
            "provider": "groq",
            "model_id": model_id,
            "model_id_original": ORIGINAL_MODEL_ID,
            "modelo_substituido": substituido,
            "motivo_substituicao": (
                "A Groq removeu llama-3.3-70b-versatile do catalogo; a chamada "
                "retorna 404 model_not_found. A troca acontece no cliente, "
                "dentro do harness - app/services/ai_service.py segue intacto."
            )
            if substituido
            else None,
            "temperature": 0.05,
            "memoria": "manual: SQLite + janela de 10 mensagens",
            "roteamento": "nenhum: todo turno passa pelo RAG",
            "tokens_medidos": True,
            "total_casos": len(results),
            "resultados": results,
        },
    )

    print("\nPreencha o campo 'adequado' no JSON e rode:")
    print("    python evals/comparativo.py")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL_ID,
        help=(
            "id do modelo Groq usado no lugar do descontinuado "
            f"(padrao: {DEFAULT_MODEL_ID})"
        ),
    )
    args = parser.parse_args()

    asyncio.run(run_all(args.model))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
