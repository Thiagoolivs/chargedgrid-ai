# Plano de 30 minutos — ordem por pontos

> **Atualizado em 21/09/2026, com a entrega fechada.** Bateria completa em 4
> rodadas, 0 erros, relatórios com números medidos, PDF gerado, avaliação
> assinada e commits assinados. **Resta uma decisão** — os 12 `.txt` do RAG —
> e a preparação da apresentação.

## O que já está feito

| Passo | Vale | Estado |
|---|---|---|
| Ambiente, índice FAISS (59 chunks) | — | feito |
| `evals/smoke_offline.py` | validação estrutural | **28 ok, 0 falhas** |
| `evals/demo_memoria.py` | ~10 pts (bloco A) | feito, M01–M03 com rota `conversa` |
| `evals/run.py` em 2 modelos | ~20 pts (bloco B + C) | feito, 0 erros nos dois |
| `evals/run_legacy.py` | ~5 pts (bloco D) | feito, 0 erros |
| Experimento de temperatura | opcional | feito (t = 0.7) |
| `evals/comparativo.py` | ~8 pts | feito |
| Relatórios com números reais | bloco D | feitos |
| API + interface verificadas | bloco A | feitas |

Resultado: baseline **47,1%** × agente **100,0%**, com latência caindo de
25,78 s para 4,04 s por turno.

---

## O que falta

**Nada de execução.** Os quatro passos que estavam aqui foram fechados:

| Passo | Estado |
|---|---|
| Assinar `evals/avaliacao.json` e rodar `avaliar.py` + `comparativo.py` | feito — revisor: Thiago, RM 568783 |
| Turma e responsabilidade em `integrantes.txt` e na 7.5 | feito — 1CCPO, cinco integrantes |
| PDF de até 5 páginas | feito — `docs/relatorio_evolucao.pdf`, 4 páginas |
| Assinar os commits | feito — 11 commits, `%G?` = `G` |

### A única decisão aberta

**Os 12 `.txt` de `app/rag/docs/` não estão versionados** (estão no
`.gitignore` como "arquivos gerados", mas são fonte). Consequência: quem clonar
o repositório não consegue rodar `create_vector_store.py`, os seis casos
funcionais nem o baseline.

Duas saídas, ambas defensáveis — escolha antes de entregar:

- **Versionar.** ~19 KB de texto. Torna a entrega reproduzível por quem corrige.
  Verifique antes se há restrição de direito autoral sobre o manual GoodWe de
  onde os documentos foram derivados.
- **Declarar a ausência.** Já está registrado em `relatorio_modelos.md` seção 12
  e no runbook. Custa zero minuto, mas quem clonar roda só 10 dos 17 casos.

### Antes da apresentação

1. Cada integrante lê a seção 7.5 e a parte do relatório da sua área (item 11).
2. `python evals/smoke_offline.py` na máquina da apresentação — 28 ok, sem
   chave de API, em segundos.
3. `python evals/verificar_rastreabilidade.py` — prova que as 6 perguntas
   funcionais são as da Sprint 1, caractere a caractere.

---

## Se precisar rodar a bateria de novo

```bash
PYTHONIOENCODING=utf-8 python evals/run.py --model google/gemini-3.6-flash --sleep 4
```

**Cota:** a Groq limita a 200.000 tokens por dia **por modelo**. Uma bateria
consome de 68.000 a 96.000. Duas rodadas no mesmo modelo Groq não cabem no
mesmo dia. O Gemini não tem esse teto diário, só limite por minuto — por isso
o `--sleep 4`.

**Nomes de modelo válidos em 21/09/2026.** `llama-3.3-70b-versatile`,
`llama-3.1-8b-instant` e `gemini-2.0-flash` **não existem mais**. Confirme
antes de rodar:

```bash
python evals/run.py --list-google-models
```

Groq, na chave atual: `openai/gpt-oss-120b`, `openai/gpt-oss-20b`,
`qwen/qwen3.8-27b`, `groq/compound`, `groq/compound-mini`.

No Windows, prefixe com `PYTHONIOENCODING=utf-8` — sem isso o console cp1252
derruba a execução com `UnicodeEncodeError`.
