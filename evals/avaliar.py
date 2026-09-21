"""Aplica a avaliacao qualitativa aos JSONs de `evals/results/`.

    python evals/avaliar.py                 # aplica evals/avaliacao.json
    python evals/avaliar.py --status        # mostra o que falta avaliar

A secao 4 da Sprint exige, por teste de seguranca, "o resultado obtido e uma
breve analise indicando se o comportamento foi considerado adequado ou
inadequado". A secao 6 exige nota comparavel entre as arquiteturas. Os dois
dependem do campo `adequado`, que o harness grava como `null` de proposito.

O julgamento e HUMANO e fica fora do codigo, em `evals/avaliacao.json`. Este
script so transporta esse arquivo para dentro dos resultados. Nada aqui decide
se uma resposta esta certa - nao ha LLM-as-judge, e a rubrica nao pede um.

Formato de `evals/avaliacao.json`:

    {
      "criterios": { "<tipo>": "como um caso desse tipo e julgado" },
      "avaliacoes": {
        "<arquivo de resultado>.json": {
          "F01": {"adequado": true, "nota": "por que"},
          ...
        }
      }
    }

Reexecutavel: mudou o julgamento, edite o JSON e rode de novo.
"""

import argparse
import json

from common import EVALS_DIR, RESULTS_DIR, load_cases

AVALIACAO_PATH = EVALS_DIR / "avaliacao.json"


def esperados_atuais():
    """Criterio de acerto vigente, lido de `evals/cases.json`.

    O `esperado` e copiado para dentro do resultado no momento da rodada. Se o
    criterio for corrigido depois (foi o caso do F06, ver `motivo_correcao` no
    cases.json), o JSON antigo ficaria com o texto vencido e a leitura do
    relatorio nao bateria com a bateria. Aqui ele e ressincronizado.
    """
    return {case["id"]: case["esperado"] for case in load_cases()}


def carregar_avaliacao():
    if not AVALIACAO_PATH.exists():
        raise SystemExit(
            f"{AVALIACAO_PATH} nao existe. "
            "Crie o arquivo com os julgamentos antes de rodar."
        )

    return json.loads(AVALIACAO_PATH.read_text(encoding="utf-8"))


def aplicar(dry_run=False):
    avaliacao = carregar_avaliacao()
    por_arquivo = avaliacao.get("avaliacoes", {})
    revisor = avaliacao.get("revisor", "nao informado")
    data = avaliacao.get("data", "nao informada")
    esperados = esperados_atuais()

    total_aplicados = 0

    for nome, vereditos in sorted(por_arquivo.items()):
        caminho = RESULTS_DIR / nome

        if not caminho.exists():
            print(f"  aviso: {nome} nao existe em evals/results/ - ignorado")
            continue

        payload = json.loads(caminho.read_text(encoding="utf-8"))
        aplicados = 0
        faltando = []

        for resultado in payload.get("resultados", []):
            esperado = esperados.get(resultado["case"])

            if esperado is not None:
                resultado["esperado"] = esperado

            veredito = vereditos.get(resultado["case"])

            if veredito is None:
                faltando.append(resultado["case"])
                continue

            resultado["adequado"] = veredito["adequado"]
            resultado["nota"] = veredito.get("nota", "")
            resultado["avaliado_por"] = revisor
            resultado["avaliado_em"] = data
            aplicados += 1

        payload["avaliacao_revisor"] = revisor
        payload["avaliacao_data"] = data

        if not dry_run:
            caminho.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

        total_aplicados += aplicados
        marca = "(simulacao)" if dry_run else ""
        print(f"  {nome}: {aplicados} avaliados {marca}")

        if faltando:
            print(f"    sem veredito: {', '.join(faltando)}")

    print(f"\nTotal: {total_aplicados} resultados avaliados. Revisor: {revisor}.")
    return 0


def status():
    arquivos = sorted(RESULTS_DIR.glob("*.json"))

    if not arquivos:
        print("Nenhum resultado em evals/results/.")
        return 1

    for caminho in arquivos:
        payload = json.loads(caminho.read_text(encoding="utf-8"))
        resultados = payload.get("resultados", [])
        avaliados = [r for r in resultados if r.get("adequado") is not None]
        pendentes = [r["case"] for r in resultados if r.get("adequado") is None]

        print(f"  {caminho.name}: {len(avaliados)}/{len(resultados)} avaliados")

        if pendentes:
            print(f"    pendentes: {', '.join(pendentes)}")

    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--status",
        action="store_true",
        help="so mostra o que ja foi avaliado, sem escrever nada",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="mostra o que seria aplicado, sem gravar",
    )
    args = parser.parse_args()

    if args.status:
        return status()

    return aplicar(dry_run=args.dry_run)


if __name__ == "__main__":
    raise SystemExit(main())
