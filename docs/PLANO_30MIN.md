# Plano de 30 minutos — ordem por pontos

Prioridade sob pressão de tempo. Se algo tiver que cair, cai de baixo para
cima. O critério é ponto por minuto gasto.

## Regra zero

**`pip install -r requirements.txt` começa no minuto 0**, num terminal
separado, antes de tudo. `torch` e `sentence-transformers` somam alguns GB e é
o único passo que não dá para acelerar. Tudo que não depende dele acontece
enquanto ele roda.

## Ordem por retorno

| # | Passo | Vale | Depende de |
|---|---|---|---|
| 1 | `evals/demo_memoria.py` | **~10 pts** (bloco A) | só a `GROQ_API_KEY` |
| 2 | `evals/run.py` nos 2 modelos | **~20 pts** (bloco B + C) | chaves |
| 3 | `evals/run_legacy.py` | ~5 pts (bloco D) | índice FAISS |
| 4 | Preencher `adequado` | destrava 1–3 | julgamento do Thiago |
| 5 | `evals/comparativo.py` + colar tabelas | ~8 pts | passo 4 |
| 6 | `integrantes.txt` + seção 7.5 | exigência formal | ninguém além do grupo |
| 7 | Assinar os commits | item 8 | chave SSH do Thiago |
| — | `--temperature 0.5` | opcional | **CORTE ISTO PRIMEIRO** |

## O gargalo real

O passo 4 é o que estoura o relógio, não os comandos. São 17 casos × 3
execuções = até 51 respostas para julgar como adequado/inadequado, e a seção 4
da Sprint exige "o resultado obtido e uma breve análise" por teste.

**Sob pressão de tempo, a sessão local pode propor o julgamento caso a caso e
o Thiago confirma em bloco** — lendo a proposta, não a resposta bruta. O
julgamento continua sendo dele. O que não pode é a sessão preencher sozinha e
seguir adiante: o item 11 cobra que o aluno explique os resultados.

Ordem de julgamento, se faltar tempo: **M01–M03 primeiro** (bloco A, 40 pts),
depois S01–S07 e E01 (bloco C), por último F01–F06.

## Se os 12 `.txt` não aparecerem

Não trava a entrega. Sem eles:

- **roda:** M01–M03, S01–S03, S05–S07, E01 — 10 dos 17 casos, com sentido
- **degrada:** F01–F06 e S04 respondem sem contexto documental
- **não roda:** `run_legacy.py`, porque `rag_service` levanta `RuntimeError` no
  import sem o índice — e sem ele não há coluna "antes" na tabela 7.3

Nesse cenário, registre a ausência no relatório e siga. Não gere documento
sintético para preencher o buraco.

## Se o Gemini falhar

Não perca tempo depurando. A seção 5 aceita "diferentes versões de um mesmo
fornecedor":

```bash
python evals/run.py --model groq/llama-3.1-8b-instant
```

Bloco B fechado do mesmo jeito.
