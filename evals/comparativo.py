"""Gera evals/results/comparativo.md a partir dos JSONs de resultado.

    python evals/comparativo.py

Le todos os arquivos de evals/results/ (baseline + modelos) e monta a tabela
antes x depois exigida pelo item 7.3 do relatorio.

E reexecutavel de proposito: a coluna `adequado` e preenchida a mao nos JSONs,
entao o comparativo precisa ser regerado depois dessa revisao. Enquanto
`adequado` estiver null, a taxa de acerto aparece como pendente - nenhum
numero e inventado aqui.
"""

import json
from collections import OrderedDict, defaultdict

from common import RESULTS_DIR

TIPOS_ORDEM = [
    "funcional",
    "memoria",
    "injection",
    "injection_multiturno",
    "specs",
    "juridico",
    "financeiro",
    "eletrico",
    "escopo",
]


def load_runs():
    """Baseline primeiro, depois os agentes em ordem alfabetica."""
    if not RESULTS_DIR.exists():
        return []

    paths = sorted(RESULTS_DIR.glob("*.json"))
    runs = []

    for path in paths:
        try:
            runs.append(json.loads(path.read_text(encoding="utf-8")))
        except json.JSONDecodeError as exc:
            print(f"  aviso: {path.name} ignorado ({exc})")

    runs.sort(key=lambda r: (r.get("alvo") != "baseline", r.get("model", "")))
    return runs


def _fmt(value, suffix="", casas=2):
    if value is None:
        return "n/d"
    return f"{value:.{casas}f}{suffix}"


def summarize(run):
    resultados = run.get("resultados", [])
    turnos = sum(r.get("turnos", 0) for r in resultados)
    latencia_total = sum(r.get("latencia_s") or 0 for r in resultados)

    avaliados = [r for r in resultados if r.get("adequado") is not None]
    acertos = [r for r in avaliados if r.get("adequado")]

    tokens_in = [r["tokens_in"] for r in resultados if r.get("tokens_in") is not None]
    tokens_out = [r["tokens_out"] for r in resultados if r.get("tokens_out") is not None]

    memoria = [r for r in resultados if r.get("tipo") == "memoria"]
    memoria_avaliada = [r for r in memoria if r.get("adequado") is not None]
    memoria_ok = [r for r in memoria if r.get("adequado")]

    erros = [r for r in resultados if r.get("erro")]

    return {
        "model": run.get("model", "?"),
        "alvo": run.get("alvo", "?"),
        "casos": len(resultados),
        "turnos": turnos,
        "avaliados": len(avaliados),
        "acertos": len(acertos),
        "taxa": (len(acertos) / len(avaliados) * 100) if avaliados else None,
        "latencia_turno": (latencia_total / turnos) if turnos else None,
        "latencia_total": latencia_total,
        "tokens_in_turno": (sum(tokens_in) / turnos) if tokens_in and turnos else None,
        "tokens_out_turno": (sum(tokens_out) / turnos) if tokens_out and turnos else None,
        "memoria_total": len(memoria),
        "memoria_ok": len(memoria_ok),
        "memoria_avaliada": len(memoria_avaliada),
        "erros": len(erros),
    }


def tabela_geral(sumarios):
    linhas = [
        "| Modelo | Casos | Avaliados | Acertos | Taxa | Latencia/turno | Tokens in/turno | Tokens out/turno | Memoria | Erros |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]

    for s in sumarios:
        memoria = (
            f"{s['memoria_ok']}/{s['memoria_total']}"
            if s["memoria_avaliada"]
            else f"pendente (0/{s['memoria_total']} avaliados)"
        )
        taxa = _fmt(s["taxa"], "%", 1) if s["taxa"] is not None else "pendente"

        linhas.append(
            f"| `{s['model']}` | {s['casos']} | {s['avaliados']} | {s['acertos']} | "
            f"{taxa} | {_fmt(s['latencia_turno'], ' s')} | "
            f"{_fmt(s['tokens_in_turno'], '', 0)} | {_fmt(s['tokens_out_turno'], '', 0)} | "
            f"{memoria} | {s['erros']} |"
        )

    return "\n".join(linhas)


def tabela_por_tipo(runs):
    modelos = [r.get("model", "?") for r in runs]
    por_tipo = defaultdict(lambda: defaultdict(lambda: [0, 0]))

    for run in runs:
        modelo = run.get("model", "?")

        for resultado in run.get("resultados", []):
            tipo = resultado.get("tipo", "?")

            if resultado.get("adequado") is None:
                continue

            por_tipo[tipo][modelo][1] += 1

            if resultado.get("adequado"):
                por_tipo[tipo][modelo][0] += 1

    tipos = [t for t in TIPOS_ORDEM if t in por_tipo]
    tipos += sorted(t for t in por_tipo if t not in TIPOS_ORDEM)

    if not tipos:
        return (
            "_Nenhum caso avaliado ainda. Preencha `adequado` (true/false) nos "
            "JSONs de `evals/results/` e rode `python evals/comparativo.py` de novo._"
        )

    linhas = [
        "| Tipo | " + " | ".join(f"`{m}`" for m in modelos) + " |",
        "|---" * (len(modelos) + 1) + "|",
    ]

    for tipo in tipos:
        celulas = []

        for modelo in modelos:
            ok, total = por_tipo[tipo][modelo]
            celulas.append(f"{ok}/{total}" if total else "pendente")

        linhas.append(f"| {tipo} | " + " | ".join(celulas) + " |")

    return "\n".join(linhas)


def tabela_rotas(runs):
    linhas = [
        "| Caso | Tipo | " + " | ".join(f"`{r.get('model')}`" for r in runs) + " |",
        "|---" * (len(runs) + 2) + "|",
    ]

    casos = OrderedDict()

    for run in runs:
        for resultado in run.get("resultados", []):
            casos.setdefault(resultado["case"], resultado.get("tipo", "?"))

    for caso, tipo in casos.items():
        celulas = []

        for run in runs:
            match = next(
                (r for r in run.get("resultados", []) if r["case"] == caso),
                None,
            )

            if match is None:
                celulas.append("-")
                continue

            rotas = [str(x) for x in match.get("rota", [])]
            celulas.append(" -> ".join(rotas) if rotas else "-")

        linhas.append(f"| {caso} | {tipo} | " + " | ".join(celulas) + " |")

    return "\n".join(linhas)


def main():
    runs = load_runs()

    if not runs:
        print(
            "Nenhum resultado em evals/results/.\n"
            "Rode antes:\n"
            "    python evals/run_legacy.py\n"
            "    python evals/run.py"
        )
        return 1

    sumarios = [summarize(run) for run in runs]
    pendentes = [s for s in sumarios if s["taxa"] is None]

    partes = [
        "# Comparativo antes x depois - ChargeGrid AI Sprint 03",
        "",
        "Gerado por `python evals/comparativo.py` a partir dos JSONs de "
        "`evals/results/`. Nenhum numero desta pagina foi digitado a mao.",
        "",
        f"- Casos por modelo: {sumarios[0]['casos']}",
        f"- Modelos comparados: {len(runs)}",
        "",
    ]

    if pendentes:
        partes += [
            "> **Avaliacao qualitativa pendente.** Os modelos "
            + ", ".join(f"`{s['model']}`" for s in pendentes)
            + " ainda estao com `adequado: null`. Preencha true/false em cada "
            "resultado e rode este script de novo para as taxas aparecerem.",
            "",
        ]

    partes += [
        "## 1. Visao geral",
        "",
        tabela_geral(sumarios),
        "",
        "## 2. Taxa de acerto por tipo de caso",
        "",
        tabela_por_tipo(runs),
        "",
        "## 3. Rota tomada por caso",
        "",
        "O baseline nao tem roteamento: toda pergunta passa pelo RAG "
        "(`rag_sempre`), inclusive as conversacionais. O agente escolhe o "
        "caminho por aresta condicional.",
        "",
        tabela_rotas(runs),
        "",
        "## 4. Observacoes de medicao",
        "",
        "- `latencia/turno` e tempo de parede, medido com `time.perf_counter()` "
        "em volta de cada turno, incluindo retrieval quando ele acontece.",
        "- Tokens dos dois lados sao medidos. No agente vem de "
        "`usage_metadata` da resposta do LangChain; no baseline, o harness "
        "intercepta o cliente Groq de `ai_service` e le o `usage` da resposta "
        "crua - o arquivo do baseline continua intacto.",
        "- Os tokens do agente contam a chamada do no `generate`. A chamada do "
        "no `router` NAO entra nessa conta: ela e curta (rotulo de uma "
        "palavra, `max_tokens=64`) e nao produz texto para o usuario.",
        "- `memoria` conta os casos M01-M03. O baseline da Sprint 2 tem "
        "memoria manual (history[-10:] vindo do SQLite), entao ele pode "
        "acertar esses casos - o comparativo aqui e memoria manual x memoria "
        "gerenciada pelo framework, nao ausencia x presenca.",
        "",
    ]

    destino = RESULTS_DIR / "comparativo.md"
    destino.write_text("\n".join(partes), encoding="utf-8")
    print(f"Comparativo gravado em {destino}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
