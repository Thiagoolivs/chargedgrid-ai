# Plano de 30 minutos — ordem por pontos

> **Atualizado em 21/09/2026, após a sessão de execução.** Os passos de
> execução estão todos fechados: bateria completa em 4 rodadas, 0 erros,
> relatórios com números medidos. **O que resta são 4 itens de decisão
> humana**, listados abaixo em ordem de ponto por minuto.

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

## O que falta — ordem por ponto por minuto

| # | Passo | Vale | Tempo | Quem |
|---|---|---|---|---|
| 1 | Turma + responsabilidade em `integrantes.txt` e seção 7.5 | **exigência formal**, sem isso perde ponto no item 8 e no 7.5 | 5 min | grupo |
| 2 | Assinar `evals/avaliacao.json` (campo `revisor`) e rodar `avaliar.py` + `comparativo.py` | valida blocos B, C e D | 10–20 min | Thiago |
| 3 | Exportar `docs/relatorio_evolucao.md` para PDF (máx. 5 páginas) | **20 pts** do bloco D | 5 min | grupo |
| 4 | Assinar os commits | item 8 | 3 min | Thiago |

**Se faltar tempo, corte de baixo para cima — exceto o item 3**, que é
entregável obrigatório.

### Passo 1 — integrantes (5 min)

```
docs/integrantes.txt           → coluna Turma e bloco RESPONSABILIDADES
docs/relatorio_evolucao.md     → seção 7.5, colunas Turma e Responsabilidade
```

Cinco nomes e RMs já estão lá. Falta turma e o que cada um fez.

### Passo 2 — assinar a avaliação (10–20 min)

`evals/avaliacao.json` já traz veredito e justificativa dos 68 resultados. Leia,
ajuste o que discordar, troque `"revisor"` pelo seu nome e RM, e rode:

```bash
python evals/avaliar.py
python evals/comparativo.py
```

**Ordem de conferência se faltar tempo:** os 9 casos marcados `false`
(baseline F01, F04, F06, M01, M03, S05, S06, S07, E01 e qwen S07). Os `true`
são os menos discutíveis.

### Passo 3 — PDF (5 min)

`docs/relatorio_evolucao.md` está completo e segue a numeração 7.1–7.5. O
anexo com os comandos de reprodução pode ser cortado se o arquivo passar de 5
páginas — os números não podem.

### Passo 4 — assinar os commits (3 min)

```bash
git rebase --exec 'git commit --amend --no-edit -S' 11e9be5
git push --force-with-lease origin sprint-03
```

Aceite: `git log --pretty='%h %G?'` mostra `G` em vez de `N`. Nunca use
`--no-gpg-sign`.

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
