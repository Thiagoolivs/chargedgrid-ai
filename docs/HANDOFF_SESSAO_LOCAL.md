# Handoff — Sprint 03

> **Atualizado em 21/09/2026, após a sessão de execução.** A bateria inteira
> rodou. Os relatórios estão fechados com números medidos. O que sobrou está
> na seção **"O que falta"**, no fim — são quatro itens, todos de decisão
> humana.

Leia `CLAUDE.md` antes. As regras invioláveis de lá valem em tudo o que segue.

> A branch está construída sobre `master` (Sprint 2), não sobre `main`
> (Sprint 1). O código vive na raiz. O baseline do comparativo é o `ask_ai`
> **com memória manual** da Sprint 2.

---

## Estado em 21/09/2026 — tudo que foi executado

| Etapa | Comando | Resultado |
|---|---|---|
| Diagnóstico | `python verificar_ambiente.py` | Ambiente completo, sem pendências |
| Estrutural | `python evals/smoke_offline.py` | **28 ok, 0 falhas** |
| Índice FAISS | `python create_vector_store.py` | 59 chunks a partir dos 12 `.txt` |
| Memória (3.2) | `python evals/demo_memoria.py --model google/gemini-3.6-flash` | `evals/results/demo_memoria.md` — M01–M03, rota `conversa`, 6 mensagens por `thread_id` |
| Baseline "antes" | `python evals/run_legacy.py --model openai/gpt-oss-20b` | 17 casos, 24 turnos, **0 erros** |
| Agente, modelo 1 | `python evals/run.py --model google/gemini-3.6-flash` | 17 casos, **0 erros** |
| Agente, modelo 2 | `python evals/run.py --model groq/qwen/qwen3.8-27b` | 17 casos, **0 erros** |
| Parâmetro | `python evals/run.py --model google/gemini-3.6-flash --temperature 0.7` | 17 casos, **0 erros** |
| Avaliação | `python evals/avaliar.py` | 68 resultados avaliados |
| Comparativo | `python evals/comparativo.py` | `evals/results/comparativo.md` |
| API + interface | `uvicorn app.main:app` | memória, roteamento, guardrail e RAG verificados no navegador |

### Resultado consolidado

| Rodada | Taxa | Memória | Segurança | Latência/turno | Erros |
|---|---|---|---|---|---|
| Baseline Sprint 2 (`gpt-oss-20b`) | **47,1%** | 1/3 | 4/8 | 25,78 s | 0 |
| Agente — `google/gemini-3.6-flash` | **100,0%** | 3/3 | 8/8 | **4,04 s** | 0 |
| Agente — `gemini-3.6-flash@t0.7` | **100,0%** | 3/3 | 8/8 | 4,00 s | 0 |
| Agente — `groq/qwen/qwen3.8-27b` | **94,1%** | 3/3 | 7/8 | 26,20 s | 0 |

**Modelo escolhido: `google/gemini-3.6-flash`, temperatura 0.1** — critério
eliminatório de segurança (S07), justificado na seção 9 de
`docs/relatorio_modelos.md`. Já é o padrão do `.env`.

---

## Bloqueios que foram resolvidos nesta sessão

### 1. Modelo do baseline descontinuado

`llama-3.3-70b-versatile` saiu do catálogo da Groq; o nome está fixo em
`app/services/ai_service.py:48`, arquivo protegido pela regra 3.

**Resolvido sem tocar no arquivo:** `run_legacy.py` ganhou `--model` e
intercepta o argumento `model` na chamada do SDK
(`patch_baseline_model`). Prompt, temperatura, janela de histórico e o corte
`if not context` seguem idênticos. `git diff app/services/` está vazio.

A mesma interceptação lê o `usage` da resposta crua — por isso o baseline
agora tem tokens medidos, o que antes era listado como impossível.

### 2. Gemini devolvia rota vazia e resposta truncada

Nos Gemini 3.x o `max_output_tokens` é orçamento **único**, dividido entre
raciocínio e texto. Com 64 tokens no roteador a resposta vinha vazia (fallback
`tecnica` em todos os turnos); com 1200 na geração, a resposta era cortada no
meio da frase.

**Resolvido** com `thinking_budget=0`, exposto como `MODEL_THINKING` no `.env`
e centralizado em `agent_core/build_router_model`.

### 3. Conteúdo como lista de blocos

O Gemini 3.x devolve `message.content` como lista de blocos, não string, o que
quebrava `parse_route`, o render do histórico e o `guard_out`.

**Resolvido** por `agent_core/messages.py` (`message_text`), usado em
`nodes.py`, `guardrails.py` e `graph.py`. A mensagem original nunca é
reconstruída — `usage_metadata` continua intacto.

### 4. Roteador classificava turno de memória como `tecnica`

O prompt do roteador tratava "menciona carregador" como sinal de pergunta
técnica.

**Resolvido** com uma regra de desempate ("o que decide é o que a mensagem
PEDE") e 13 exemplos resolvidos. Resultado medido: **9/9 turnos de memória
roteados como `conversa`** nos dois modelos.

### 5. Métricas sem medição no README

`Latência P50 ~800ms`, `P99 ~2s`, `recall 98%` e `F1-Score 90.2%` nunca foram
medidos neste repositório. Removidos, com nota de correção no próprio README.

### 6. Gabarito do F06 contradizia o corpus

`esperado` pedia IP54/IP20/IK10, que não existem em
`app/rag/docs/especificacoes_tecnicas.txt` (o corpus documenta IP66/IP55).
Corrigido em `evals/cases.json`, com `esperado_original_sprint1` e
`motivo_correcao` gravados ao lado. **A pergunta continua literal.**

---

## Limitação operacional descoberta

A Groq aplica **200.000 tokens por dia, por modelo** na conta do grupo. Uma
bateria completa consome de 68.000 a 96.000 tokens. Mensagem literal quando
estoura:

```
Rate limit reached for model `openai/gpt-oss-120b` ... on tokens per day (TPD): Limit 200000, Used 197401
```

Por isso baseline e agente rodaram em modelos Groq diferentes. Ao repetir a
bateria, planeje a distribuição ou espere a virada do dia.

---

## O que falta

**Nada de código e nada de execução.** Os quatro itens que estavam listados
aqui foram fechados nesta sessão:

| Item | Estado |
|---|---|
| Assinar `evals/avaliacao.json` (campo `revisor`) | feito — Thiago de Oliveira Coelho Souza (RM 568783), 68 resultados |
| Turma e responsabilidades | feito — 1CCPO, cinco integrantes, `integrantes.txt` e seção 7.5 |
| PDF de até 5 páginas | feito — `docs/relatorio_evolucao.pdf`, **4 páginas**, gerado por `docs/gerar_pdf.py` |
| Assinar os commits | feito — 11 commits em `sprint-03`, `git log --pretty='%h %G?'` mostra `G` |

### A decisão que continua aberta

**Os 12 `.txt` de `app/rag/docs/` não estão versionados.** Estão no
`.gitignore` sob o rótulo "arquivos gerados", mas não são gerados — são fonte.
Consequência para quem corrigir clonando o repositório: `create_vector_store.py`
não roda, e com isso os seis casos funcionais e o baseline também não.

- **Versionar** (~19 KB de texto) torna a entrega reproduzível. Confira antes se
  há restrição sobre o manual GoodWe de onde os documentos foram derivados.
- **Declarar a ausência** já está feito, em `relatorio_modelos.md` seção 12 e
  no runbook. Quem clonar roda 10 dos 17 casos.

Não decidi por você: é a única escolha da entrega que depende de informação que
está fora do repositório.

### Antes de entregar

1. Cada integrante lê a seção 7.5 e a parte do relatório da sua área — o item
   11 cobra que cada um explique o que fez.
2. Rotacione as duas chaves de API. Elas foram coladas no chat durante a sessão
   de execução. O `.env` continua fora do Git e nenhum valor foi impresso em log
   ou commit, mas rotacionar é barato.
3. Na máquina da apresentação, rode os dois comandos que provam a entrega em
   segundos e sem chave de API:

```bash
python evals/smoke_offline.py              # 28 ok, 0 falhas
python evals/verificar_rastreabilidade.py  # 6/6 perguntas literais da Sprint 1
```

---

## Recomendado, não obrigatório

**Corrigir o S07 do qwen.** A correção provável é uma linha de precedência no
bloco de regras invioláveis: em pedido jurídico, financeiro ou elétrico a
resposta é o encaminhamento, nunca "não está documentada". Não foi aplicada
porque alteraria o prompt **depois** da bateria e os relatórios passariam a
descrever um sistema diferente do medido. Se aplicar, rode a bateria de novo e
regenere as tabelas.

---

## Armadilhas que continuam valendo

| Armadilha | Por quê |
|---|---|
| "Vou só ajustar o `rag_service.py`" | Mata o comparativo da seção 6. Ele é o "antes" |
| "O baseline não tem memória" | **Tem.** Manual, `history[-10:]` do SQLite. O M02 prova: ele acertou |
| "Vou estimar a latência" | Item 11. Todo número sai de `evals/results/` |
| "Vou reescrever as perguntas dos testes funcionais" | A seção 6 exige o mesmo conjunto da Sprint 1, literal |
| "Vou guardar o histórico numa lista para garantir" | Memória tem que vir do framework, ou o bloco A cai |
| "Vou subir o langchain para resolver X" | Quebra o `rag_service.py` |
| "Vou assinar o commit sem a chave" | Nunca `--no-gpg-sign`. Pare e avise |
| "O console cortou a resposta" | É `UnicodeEncodeError` do cp1252. Rode com `PYTHONIOENCODING=utf-8` |

---

## Arquivos que a entrega precisa

| Entregável da seção 8 | Onde |
|---|---|
| Código-fonte com a nova arquitetura | `agent_core/`, `app/routes/agent_chat.py` |
| `relatorio_modelos.md` | `docs/relatorio_modelos.md` |
| Casos de teste (funcional, memória, segurança, injection) | `evals/cases.json` + `evals/results/*.json` |
| Relatório de evolução (PDF) | `docs/relatorio_evolucao.md` → exportar |
| Repositório Git com histórico | branch `sprint-03` |
| Identificação dos integrantes | `docs/integrantes.txt` |
