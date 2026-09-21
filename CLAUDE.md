# ChargeGrid AI — contexto para sessões do Claude Code

Assistente técnico RAG para carregadores de veículos elétricos GoodWe HCA-G2.
Trabalho acadêmico (EV Challenge GoodWe, Sprint 03).

**Branches.** O repositório tem dois históricos **sem ancestral comum**:
`main` é a Sprint 1 (21/05) e **`master` é a Sprint 2 (15/06), a base real**.
A Sprint 03 é construída sobre `master`. Se algo referenciar
`chargegrid-ai/...`, é material da branch antiga — o código vive na raiz.

**Antes de começar qualquer coisa, leia `docs/HANDOFF_SESSAO_LOCAL.md`.** Ele
diz o que já está pronto, o que falta e em que ordem executar.

**Sob pressão de tempo, leia antes `docs/PLANO_30MIN.md`** — ordem por ponto
por minuto, o que cortar primeiro e onde está o gargalo real.

---

## Regras invioláveis

### 1. Commits

Autoria do Thiago, sempre:

```
Thiagoolivs <thiago.olivs.coelho@gmail.com>
```

**PROIBIDO em mensagem de commit:**
- `Co-Authored-By: Claude <...>` ou qualquer variação
- `🤖 Generated with Claude Code` ou qualquer rodapé equivalente
- Qualquer trailer, emoji ou assinatura que atribua autoria a ferramenta de IA

Motivo: o item 8 da Sprint avalia "commits dos integrantes do grupo" e o item
11 exige que o aluno explique o que foi feito. O uso de IA é permitido e
incentivado pelo enunciado — a **autoria do commit** é que é do aluno.

Commits devem ser assinados (`commit.gpgsign=true`, SSH). Se a assinatura
falhar: **pare e avise o Thiago.** Nunca use `--no-gpg-sign`, nunca desligue
`commit.gpgsign` para contornar erro.

Mensagens em português, no imperativo.

### 2. Credenciais

Nenhuma chave em código ou no histórico Git. Elas vivem no `.env`, que está no
`.gitignore`. O `.env.example` é o modelo. Nunca imprima o valor de uma chave —
nem em log, nem em diagnóstico.

### 3. Não quebrar o baseline

`app/services/rag_service.py` e `app/services/ai_service.py` **não são
alterados**. Eles são o "antes" que a seção 6 da Sprint exige comparar. Se
forem modificados, o comparativo perde a validade. Confira com
`git diff app/services/` — precisa sair vazio.

Código novo vai **ao lado**, não por cima. É por isso que `agent_core/` existe
como pacote irmão de `app/` e consome o RAG como está.

Quando o provedor retira um modelo fixo nesses arquivos, a saída é
interceptar no harness, não editar o arquivo. Ver
`evals/run_legacy.py:patch_baseline_model`.

### 4. Nenhuma métrica inventada

Todo número que aparece em relatório sai de `evals/results/`.
Se a medição não existe, escreva `PENDENTE` — não estime, não arredonde, não
cite benchmark de terceiros como se fosse deste sistema.

O campo `adequado` é julgamento **humano**, e vive em `evals/avaliacao.json`,
fora do código. `evals/avaliar.py` só transporta esse arquivo para dentro dos
resultados. **Não implemente LLM-as-judge:** é mais um ponto de falha e a
rubrica não pede. O campo `revisor` do arquivo é assinado pelo Thiago.

### 5. Não reduzir a bateria

`evals/cases.json` tem 17 casos. Os 6 funcionais são as 6 perguntas de
`test_cases.txt` copiadas **literalmente** — a seção 6 exige rodar o mesmo
conjunto de testes da Sprint anterior. Não reescreva essas perguntas.

---

## Mapa do projeto

```
app/                          # Sprint 2 — NÃO ALTERAR o que é baseline
├── main.py                   # rotas: / , /chat , /agent/chat , /conversations
├── database.py               # SQLite: conversations + messages (máx. 7)
├── routes/chat.py            # POST /chat — baseline, com history
├── routes/conversations.py   # CRUD de conversas
├── routes/agent_chat.py      # POST /agent/chat — Sprint 03
├── services/ai_service.py    # ask_ai(message, context, history) — baseline
├── services/rag_service.py   # retrieve_context(...) — o RAG, intocado
├── prompts/system_prompt.txt # lido, nunca editado
└── rag/docs/                 # 12 .txt — GITIGNORADOS, ausentes do repositório
agent_core/                   # Sprint 03
├── graph.py                  # monta e compila o grafo
├── nodes.py                  # router, retrieve, generate, refuse
├── guardrails.py             # guard_in, guard_out
├── prompt.py                 # system prompt + REGRAS INVIOLÁVEIS
├── state.py                  # AgentState
├── messages.py               # message_text: content como str ou lista de blocos
└── config.py                 # provedor/modelo por variável de ambiente
evals/                        # bateria e harness
static/index.html             # interface do Volt
docs/                         # relatórios, runbook, handoff
verificar_ambiente.py         # diagnóstico — RODE ISTO PRIMEIRO
```

## O baseline tem memória

**A Sprint 2 não é stateless.** `ask_ai(message, context, history)` recebe
`history[-10:]`, montado por `chat.py` a partir do SQLite. Nunca escreva em
relatório, comentário ou commit que o baseline não tinha memória.

O comparativo da Sprint 03 é **memória manual × memória gerenciada pelo
framework** — que é exatamente o que a seção 6 pede.

Detalhe que importa ao avaliar: `ask_ai` começa com
`if not context: return "Essa informacao nao esta documentada."`, **antes** de
olhar o histórico. Pergunta sobre a conversa cujo retrieval não trouxe nada
morre aí, com memória e tudo.

## Duas camadas de memória na Sprint 03

| Camada | Papel |
|---|---|
| `MemorySaver` (LangGraph) | Estado que alimenta a inferência. É o requisito 3.2 |
| SQLite (herdado) | Transcript durável e listagem de conversas na interface |

O `conversation_id` da Sprint 2 é usado como `thread_id`, então as duas falam
da mesma conversa. Depois de um restart, `agent_chat._rehydrate` repovoa o
checkpointer a partir do SQLite **uma vez**, com guarda contra duplicação.
Isso não é gerenciamento manual de histórico: nenhuma mensagem é montada à
mão para o LLM, o que se faz é repopular o estado do próprio framework.

## Arquitetura do agente

```
START → guard_in ─┬─ (bloqueado) ─────────────────────→ refuse ─┐
                  └─ (ok) → router ─┬─ tecnica → retrieve → generate ─┤
                                    ├─ conversa ────────→ generate ─┤
                                    └─ fora_escopo ─────→ refuse ───┤
                                                                     ▼
                                                        guard_out → END
```

- **Memória:** `MemorySaver` + `thread_id`, do LangGraph. **Nunca implemente
  gerenciamento manual de histórico** — se a memória não vier do framework, o
  bloco A (40 pontos) cai.
- **Roteador:** classifica intenção com o LLM, temperatura 0, lendo o
  histórico. Falha ou valor inválido → cai em `tecnica`.
- **`generate` com contexto vazio:** responde a partir do histórico. **Nunca**
  replique o `if not context: return "não documentada"` do `ask_ai`. Esse é o
  bug mais provável de reintroduzir.
- **Import do `rag_service` é tardio e cacheado.** Ele carrega o FAISS no
  import e levanta `RuntimeError` sem índice; no topo do módulo, derrubaria até
  as conversas que não precisam de busca.

## Comandos

```bash
python verificar_ambiente.py                 # o que está pronto e o que falta
python evals/smoke_offline.py                # 28 verificações, sem chave
python evals/verificar_rastreabilidade.py    # 6 casos funcionais = test_cases.txt
python evals/demo_memoria.py --model google/gemini-3.6-flash
python evals/run_legacy.py --model openai/gpt-oss-20b   # baseline (exige índice)
python evals/run.py --model google/gemini-3.6-flash --sleep 4
python evals/avaliar.py                      # aplica evals/avaliacao.json
python evals/comparativo.py                  # tabela antes × depois
uvicorn app.main:app --reload                # API + interface em /
```

No Windows, prefixe com `PYTHONIOENCODING=utf-8`.

`smoke_offline.py` deve dar **28 ok, 0 falhas**. Validado contra
`langgraph==1.2.0` e `langchain-core==1.4.0`, que são os pins da Sprint 2.

## Estado atual — 21/09/2026, após a sessão de execução

**A bateria inteira rodou. Não há bloqueio aberto.**

| Rodada | Taxa | Memória | Segurança | Latência/turno | Erros |
|---|---|---|---|---|---|
| Baseline Sprint 2 (`gpt-oss-20b`) | 47,1% | 1/3 | 4/8 | 25,78 s | 0 |
| Agente `google/gemini-3.6-flash` | **100,0%** | 3/3 | 8/8 | **4,04 s** | 0 |
| Agente `gemini-3.6-flash@t0.7` | 100,0% | 3/3 | 8/8 | 4,00 s | 0 |
| Agente `groq/qwen/qwen3.8-27b` | 94,1% | 3/3 | 7/8 | 26,20 s | 0 |

Modelo escolhido: **`google/gemini-3.6-flash`, temperatura 0.1** — já é o
padrão do `.env`. Justificativa na seção 9 de `docs/relatorio_modelos.md`.

**Os quatro itens que estavam pendentes foram fechados:** a avaliação está
assinada (Thiago, RM 568783), turma 1CCPO e responsabilidades preenchidas, o
PDF tem 4 páginas (limite 5) e os 11 commits da branch `sprint-03` estão
assinados com chave SSH (`%G?` = `G`).

Aberto, e é decisão do grupo: **os 12 `.txt` de `app/rag/docs/` não estão
versionados.** Quem clonar o repositório não roda os casos funcionais nem o
baseline. Ou entram no repositório, ou a ausência fica declarada na entrega.

### Nomes de modelo — o catálogo mudou durante a sprint

`llama-3.3-70b-versatile`, `llama-3.1-8b-instant` e `gemini-2.0-flash` **não
existem mais**. Groq hoje: `openai/gpt-oss-120b`, `openai/gpt-oss-20b`,
`qwen/qwen3.8-27b`, `groq/compound`, `groq/compound-mini`. Google: confirme com
`python evals/run.py --list-google-models`.

### Duas armadilhas de configuração já resolvidas — não reintroduza

- **Gemini 3.x divide `max_output_tokens` entre raciocínio e texto.** Sem
  `MODEL_THINKING=0`, o roteador devolve resposta vazia e a geração sai
  truncada. Está resolvido em `agent_core/config.py`.
- **Gemini 3.x devolve `content` como lista de blocos, não string.** Use
  `agent_core/messages.message_text` em qualquer ponto que leia conteúdo de
  mensagem — nunca `.content` direto.

### Cota da Groq

200.000 tokens por dia, **por modelo**. Uma bateria consome de 68.000 a 96.000.
Duas rodadas no mesmo modelo Groq não cabem no mesmo dia.

Os 12 `.txt` estão no `.gitignore` (`app/rag/docs/`), classificados como
"arquivos gerados". Não são gerados — são fonte. Estão na máquina do grupo.

Detalhes e critérios de aceite: `docs/HANDOFF_SESSAO_LOCAL.md`.
