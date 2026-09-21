"""Confere que os casos funcionais sao as perguntas da Sprint 1, literais.

    python evals/verificar_rastreabilidade.py

A secao 6 da Sprint 03 exige rodar na nova arquitetura *o mesmo conjunto de
testes utilizado anteriormente*. Afirmar isso num relatorio e barato; este
script torna a afirmacao verificavel: compara caractere a caractere o campo
`turns[0]` de cada caso funcional de `evals/cases.json` com a pergunta
correspondente de `test_cases.txt`, o arquivo da Sprint 1.

Sai com 0 quando as seis batem e 1 quando qualquer uma divergir - entao serve
em CI ou como passo de conferencia antes da entrega.
"""

import json
import re
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
TEST_CASES = BASE_DIR / "test_cases.txt"
CASES = BASE_DIR / "evals" / "cases.json"

# As perguntas aparecem em test_cases.txt sempre no mesmo formato:
#     **PERGUNTA:**
#     "texto da pergunta"
PADRAO_PERGUNTA = re.compile(r'\*\*PERGUNTA:\*\*\s*\n"(.+?)"')


def main():
    if not TEST_CASES.exists():
        print(f"FALHA: {TEST_CASES.name} nao encontrado na raiz do projeto.")
        print("Ele e o arquivo de testes da Sprint 1 e precisa estar versionado")
        print("para que a rastreabilidade exigida pela secao 6 seja conferivel.")
        return 1

    perguntas = PADRAO_PERGUNTA.findall(TEST_CASES.read_text(encoding="utf-8"))
    casos = [
        c
        for c in json.loads(CASES.read_text(encoding="utf-8"))
        if c["tipo"] == "funcional"
    ]

    print(f"{'=' * 68}")
    print("RASTREABILIDADE - casos funcionais x test_cases.txt da Sprint 1")
    print(f"{'=' * 68}")
    print(f"perguntas em test_cases.txt : {len(perguntas)}")
    print(f"casos funcionais em cases.json: {len(casos)}\n")

    falhas = 0

    if len(perguntas) != len(casos):
        print(
            f"FALHA: contagem diferente "
            f"({len(perguntas)} perguntas x {len(casos)} casos)."
        )
        falhas += 1

    for caso, pergunta in zip(casos, perguntas):
        if caso["turns"][0] == pergunta:
            print(f"  [OK]    {caso['id']}  {caso['turns'][0][:58]}")
        else:
            falhas += 1
            print(f"  [FALHA] {caso['id']}")
            print(f"          cases.json    : {caso['turns'][0]}")
            print(f"          test_cases.txt: {pergunta}")

    print(f"\n{'=' * 68}")

    if falhas:
        print(f"RESULTADO: {falhas} divergencia(s). As perguntas NAO sao literais.")
        return 1

    print(f"RESULTADO: {len(casos)}/{len(casos)} literais. Rastreabilidade ok.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
