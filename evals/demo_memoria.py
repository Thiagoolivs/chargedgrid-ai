"""Demonstracao de memoria conversacional (requisito 3.2 da Sprint 03).

    python evals/demo_memoria.py
    python evals/demo_memoria.py --caso M01 --model groq/llama-3.3-70b-versatile

Roda os casos de memoria turno a turno contra o modelo configurado e grava um
transcript em evals/results/demo_memoria.md, pronto para colar no relatorio.

A rubrica pede "pelo menos 3 turnos de interacao, evidenciando que o agente
consegue recuperar e utilizar corretamente informacoes de mensagens
anteriores". O transcript registra, por turno: a mensagem, a rota escolhida
pelo grafo, a resposta e a latencia. No fim de cada caso registra quantas
mensagens o checkpointer acumulou - a evidencia de que a memoria e do
framework e nao do prompt.

NAO precisa do indice FAISS: os casos de memoria sao roteados para `conversa`
e nao passam pelo retrieval. Basta a chave do provedor.
"""

import argparse
import time

from common import RESULTS_DIR, bootstrap_path, call_with_retry, load_cases

bootstrap_path()


def run_caso(graph, case, model_name):
    from agent_core.graph import answer

    thread_id = f"demo-{case['id']}"
    linhas = [
        f"### Caso {case['id']} — {case['tipo']}",
        "",
        f"- **Modelo:** `{model_name}`",
        f"- **thread_id:** `{thread_id}` (o mesmo nos {len(case['turns'])} turnos)",
        f"- **Esperado:** {case['esperado']}",
        "",
    ]

    print(f"\n{'=' * 70}\n{case['id']} — thread_id={thread_id}\n{'=' * 70}")

    for index, turn in enumerate(case["turns"], start=1):
        started = time.perf_counter()
        payload = call_with_retry(
            lambda: answer(thread_id, turn, graph=graph),
            label=f"{case['id']} turno {index}",
        )
        elapsed = time.perf_counter() - started

        print(f"\n[turno {index}] USUARIO: {turn}")
        print(f"[turno {index}] ROTA: {payload['route']}  ({elapsed:.2f}s)")
        print(f"[turno {index}] AGENTE: {payload['response']}")

        linhas += [
            f"**Turno {index} — usuário**",
            "",
            f"> {turn}",
            "",
            f"**Turno {index} — agente** · rota `{payload['route']}` · {elapsed:.2f}s",
            "",
            "```",
            payload["response"].strip(),
            "```",
            "",
        ]

    state = graph.get_state({"configurable": {"thread_id": thread_id}})
    total = len(state.values["messages"])

    linhas += [
        f"**Memória do framework:** o checkpointer acumulou **{total} mensagens** "
        f"para este `thread_id` ({len(case['turns'])} turnos de usuário + as "
        "respostas). Nenhuma lista de histórico é mantida pelo código da "
        "aplicação — o estado vem do `MemorySaver` do LangGraph.",
        "",
        "---",
        "",
    ]

    print(f"\n[checkpointer] {total} mensagens acumuladas no thread {thread_id}")
    return linhas


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default=None, help="provedor/modelo")
    parser.add_argument(
        "--caso",
        action="append",
        dest="casos",
        help="id do caso (padrao: M01, M02 e M03). Pode repetir.",
    )
    args = parser.parse_args()

    from agent_core.config import (
        ROUTER_MAX_TOKENS,
        ROUTER_TEMPERATURE,
        build_chat_model,
        describe_model,
    )
    from agent_core.graph import build_graph

    provider = model_id = None

    if args.model:
        provider, model_id = args.model.split("/", 1)

    chat_model = build_chat_model(provider=provider, model_id=model_id)
    router_model = build_chat_model(
        provider=provider,
        model_id=model_id,
        temperature=ROUTER_TEMPERATURE,
        max_tokens=ROUTER_MAX_TOKENS,
    )
    graph = build_graph(chat_model=chat_model, router_model=router_model)
    model_name = args.model or describe_model()

    alvos = args.casos or ["M01", "M02", "M03"]
    cases = [c for c in load_cases() if c["id"] in alvos]

    if not cases:
        print(f"Nenhum caso encontrado para {alvos}")
        return 1

    linhas = [
        "# Demonstração de memória conversacional — Sprint 03",
        "",
        "Requisito 3.2: memória por sessão usando os recursos do framework, "
        "com pelo menos 3 turnos de interação.",
        "",
        f"Gerado por `python evals/demo_memoria.py` em "
        f"{time.strftime('%Y-%m-%d %H:%M:%S')}.",
        "",
        "---",
        "",
    ]

    for case in cases:
        linhas += run_caso(graph, case, model_name)

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    destino = RESULTS_DIR / "demo_memoria.md"
    destino.write_text("\n".join(linhas), encoding="utf-8")

    print(f"\nTranscript gravado em {destino}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
