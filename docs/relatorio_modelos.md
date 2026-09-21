# Relatório de Modelos — ChargeGrid AI · Sprint 03

> **Status dos números:** todas as tabelas de resultado abaixo estão marcadas
> como `PENDENTE` até a bateria ser executada com as chaves de API. Os números
> saem exclusivamente de `evals/results/` — nada nesta página é
> estimado ou copiado de benchmark de terceiros.

---

## 1. Identificação

| Item | Valor |
|---|---|
| Projeto | ChargeGrid AI — assistente técnico de carregadores GoodWe HCA-G2 |
| Sprint | 03 — agente com memória, comparativo de modelos e guardrails |
| Repositório | `Thiagoolivs/chargedgrid-ai` |
| Código do agente | `agent_core/` |
| Bateria de avaliação | `evals/` |
| Integrantes | ver `docs/integrantes.txt` |

---

## 2. Framework de agentes: LangGraph

### 2.1 O que foi escolhido

**LangGraph**, sobre a stack LangChain que o projeto já usava como wrapper de
vectorstore.

### 2.2 Por que

| Requisito da rubrica | Como o LangGraph atende |
|---|---|
| Orquestração real, não "importar uma lib" | O fluxo conversacional **é** a estrutura do grafo: nós nomeados e arestas condicionais explícitas. Trocar o comportamento do agente é mudar o grafo, não enfiar `if` dentro de uma função de 200 linhas |
| Memória por sessão | `MemorySaver` + `thread_id` resolvem o requisito sem uma linha de gerenciamento manual de histórico |
| Troca de modelo | O mesmo grafo roda com Groq e com Gemini; muda `MODEL_PROVIDER`/`MODEL_ID` no ambiente |
| Guardrails | Viram nós de verdade, com aresta condicional que desvia **antes** de gastar chamada de LLM |

### 2.3 Trade-off honesto

LangGraph cobra um preço:

- **Curva de aprendizado maior.** Estado, reducers e arestas condicionais são
  conceitos que um chat simples não precisaria.
- **Boilerplate de estado verboso.** `AgentState` existe para carregar quatro
  campos entre nós — num fluxo linear isso seria uma variável local.

O **OpenAI Agents SDK** seria mais enxuto e tem guardrails de primeira classe.
Foi descartado porque amarra o ecossistema à OpenAI, e este projeto roda em
Groq e passou a rodar também em Google — exatamente o eixo do comparativo
desta sprint. Trocar de framework para ganhar concisão custaria a portabilidade
que a sprint precisa demonstrar.

---

## 3. Arquitetura do agente

### 3.1 O grafo

```
START → guard_in ─┬─ (bloqueado) ──────────────────────────→ refuse ─┐
                  │                                                  │
                  └─ (ok) → router ─┬─ tecnica ──→ retrieve → generate ─┤
                                    ├─ conversa ───────────→ generate ─┤
                                    └─ fora_escopo ────────→ refuse ───┤
                                                                       ▼
                                                          guard_out → END
```

Todos os caminhos convergem em `guard_out`: uma saída só, um ponto só de
verificação de vazamento.

| Nó | Papel |
|---|---|
| `guard_in` | Filtro textual de prompt injection sobre a mensagem do usuário |
| `router` | Classifica a intenção com o próprio LLM (temperatura 0) e escolhe a aresta |
| `retrieve` | Consome `app/services/rag_service.py` **sem alterá-lo** |
| `generate` | Gera a resposta com system prompt + histórico + contexto da rodada |
| `refuse` | Recusa padronizada (injection ou fora de escopo) |
| `guard_out` | Substitui a resposta se ela reproduzir o system prompt |

### 3.2 Memória

A memória vem inteira do framework:

```python
graph = builder.compile(checkpointer=MemorySaver())
cfg = {"configurable": {"thread_id": session_id}}
graph.invoke({"messages": [("user", texto)]}, cfg)
```

`MessagesState` acumula o histórico entre chamadas. **Não existe
gerenciamento manual de lista de mensagens em nenhum ponto de `agent_core/`.**

Validação estrutural em `evals/smoke_offline.py` (28 verificações, roda sem
chave de API):

- o terceiro turno do M01 recebe "Solar Park" (turno 1) e "12 vagas" (turno 2);
- o checkpointer acumula 6 mensagens em 3 turnos;
- `thread_id` diferente não enxerga a memória do outro — sem vazamento entre
  sessões.

### 3.3 O roteador — o que justifica chamar isso de agente

O `router` é uma chamada leve ao próprio LLM, temperatura 0, que devolve um
JSON de um campo com `tecnica`, `conversa` ou `fora_escopo`, **lendo o
histórico da sessão** e não só a última mensagem.

Ele resolve por arquitetura um bug concreto do baseline. No terceiro turno do
M01 — *"considerando o condomínio que mencionei, quantas vagas eu disse que
existem?"* — não há termo técnico buscável. O serviço antigo manda essa
pergunta ao FAISS de qualquer jeito, recebe chunks irrelevantes de
`especificacoes_tecnicas.txt` e responde com base neles. O agente classifica a
pergunta como `conversa` e ela **nem chega ao retrieval**: é respondida a
partir da memória.

Isso não é um remendo no prompt. É uma aresta do grafo.

**Fallback:** se o classificador falhar (exceção, timeout) ou devolver valor
inválido, a rota cai em `tecnica`. O pior caso vira contexto irrelevante que o
modelo ignora; cair em `fora_escopo` recusaria uma pergunta legítima. Ambos os
casos são testados em `smoke_offline.py`.

### 3.4 Conflito resolvido no system prompt

O prompt do baseline manda responder *"Essa informacao nao esta documentada"*
sempre que faltar contexto recuperado. A regra foi escrita para um serviço
stateless, na Sprint 1. Ela sobreviveu à Sprint 2 e continua cortando **antes**
de o histórico ser lido: `if not context: return ...` é a primeira linha de
`ask_ai`. Num agente com memória, ela apagaria tudo que o usuário contou na
própria conversa — quebraria M01, M02 e M03.

`agent_core/prompt.py` sobrepõe um bloco que delimita o alcance dela: a frase
vale apenas para especificação técnica GoodWe ausente da documentação, nunca
para dado que o próprio usuário informou. O arquivo
`app/prompts/system_prompt.txt` **não foi editado** — ele é lido como está e
recebe o bloco por cima, para o comparativo antes/depois continuar válido.

---

## 4. Modelos comparados

| | Modelo 1 | Modelo 2 |
|---|---|---|
| Provedor | Groq | Google AI Studio |
| Modelo | `llama-3.3-70b-versatile` | `PREENCHER` — confirmar com `python evals/run.py --list-google-models` |
| Pacote | `langchain-groq==0.1.10` | `langchain-google-genai==1.0.10` |
| Chave | `GROQ_API_KEY` | `GOOGLE_API_KEY` |
| Temperatura (geração) | 0.1 | 0.1 |
| Temperatura (roteador) | 0.0 | 0.0 |
| `max_tokens` | 1200 | 1200 |

> **Antes de rodar:** nome de modelo Gemini muda com o tempo. Rode
> `python evals/run.py --list-google-models` com a chave configurada, escolha o
> Flash estável mais recente e **registre aqui o nome exato usado**.

A temperatura é igual nos dois para a comparação ser justa: a única variável é
o modelo. O mesmo grafo, os mesmos prompts, os mesmos 14 casos.

**Experimento de parâmetro (opcional, sugerido pela rubrica):** rodar o
vencedor também em 0.5:

```bash
python evals/run.py --model <vencedor> --temperature 0.5
```

Grava um JSON separado, sem sobrescrever a rodada de 0.1.

### 4.1 Baseline "antes" (Sprint 2, branch `master`)

`app/services/ai_service.py` — `ask_ai(message, context, history)`, assíncrono,
Groq `llama-3.3-70b-versatile`, temperatura 0.05.

**Tem memória**, manual: `app/routes/chat.py` busca as mensagens da conversa em
SQLite, monta a lista e passa `history[-10:]` ao modelo. O harness
`evals/run_legacy.py` exercita esse mesmo caminho — o módulo `database` de
verdade, não uma aproximação.

Mantido **intacto** de propósito: sem ele não há comparativo.

Atenção ao avaliar: `ask_ai` corta com
`if not context: return "Essa informacao nao esta documentada."` **antes** de
olhar o histórico. Uma pergunta sobre a conversa cujo retrieval não trouxe nada
morre aí, mesmo havendo memória.

---

## 5. Metodologia

- **14 casos** em `evals/cases.json`: 3 funcionais (F01–F03), 3 de memória
  (M01–M03), 8 de segurança e escopo (S01–S07, E01).
- Cada caso recebe um `thread_id` novo (`uuid4`); **todos os turnos do caso
  compartilham esse id** — é o que exercita a memória.
- Latência medida com `time.perf_counter()` em volta de cada turno.
- Tokens extraídos de `usage_metadata`/`response_metadata` com acesso
  defensivo e fallback `None`.
- A rota tomada é registrada por turno.
- **Avaliação qualitativa é manual.** O campo `adequado` sai `null` do harness
  e é preenchido a mão. Não há LLM-as-judge: seria mais um ponto de falha e a
  rubrica não pede.

### 5.1 Critérios de decisão — definidos ANTES de ver os resultados

Em ordem de peso:

1. **Segurança (S01–S07, E01)** — eliminatório. Um modelo que vaza o system
   prompt ou inventa especificação de produto está fora, por mais rápido que
   seja.
2. **Memória (M01–M03)** — precisa dos 3. É o requisito de 40 pontos.
3. **Fidelidade técnica (F01–F03)** — citar o registro Modbus exato, sem
   arredondar nem generalizar.
4. **Latência por turno** — critério de desempate, não de mérito.
5. **Tokens por turno** — critério de custo, o último a pesar.

---

## 6. Resultados

> **PENDENTE.** Colar aqui `evals/results/comparativo.md` depois de rodar:
>
> ```bash
> python create_vector_store.py     # índice FAISS
> python evals/run_legacy.py        # baseline
> python evals/run.py               # os dois modelos
> # preencher 'adequado' nos JSONs
> python evals/comparativo.py
> ```

### 6.1 Visão geral

`PENDENTE — tabela gerada`

### 6.2 Taxa de acerto por tipo

`PENDENTE — tabela gerada`

### 6.3 Rota tomada por caso

`PENDENTE — tabela gerada`

---

## 7. Diferenças observadas entre os modelos

> **PENDENTE.** Preencher a partir das respostas em
> `evals/results/agent_*.json`. Pontos a observar, caso a caso:
>
> - **F01/F02:** o modelo cita o número do registro (10060, 10025, 10026) ou
>   generaliza para "ative a função no aplicativo"?
> - **M01–M03:** recupera o dado certo do histórico ou troca números?
> - **S04:** admite que `EV-9000X` não existe na documentação, ou inventa
>   potência e número de série?
> - **S05/S06/S07:** encaminha a profissional, ou entrega o conselho?
> - **Formato:** respeita a estrutura de seções do system prompt?
> - **Verbosidade:** compare `tokens_out/turno` — a diferença costuma ser
>   grande e impacta custo e latência percebida.

---

## 8. Vantagens e limitações

### Groq `llama-3.3-70b-versatile`

**Vantagens conhecidas de projeto**

- Já é o modelo do baseline: o comparativo isola a arquitetura de um lado e o
  modelo do outro.
- Infraestrutura LPU, otimizada para latência de inferência.
- Sem limite de requisição por minuto tão agressivo quanto o free tier do
  Gemini durante a bateria.

**Limitações**

- `PENDENTE` — preencher com o observado.

### Google Gemini Flash

**Vantagens conhecidas de projeto**

- Janela de contexto ampla, folgada para conversas longas com histórico.
- Free tier suficiente para a bateria desta sprint.

**Limitações**

- **Limite de requisições por minuto no free tier.** É a limitação operacional
  concreta: `run.py` espaça as chamadas em 4 s por padrão no provedor `google`
  e repete com backoff exponencial em 429. Sem isso a bateria morre no meio.
- `PENDENTE` — preencher com o observado.

---

## 9. Escolha final

> **PENDENTE.** Aplicar os critérios da seção 5.1 aos resultados da seção 6 e
> justificar em 2–3 parágrafos. A justificativa precisa citar número medido,
> não impressão de uso.

---

## 10. Guardrails

### 10.1 Camadas

| Camada | O que faz | Força |
|---|---|---|
| `guard_in` | Padrões textuais sobre a mensagem, com acento normalizado | **Rasa** |
| System prompt | Bloco REGRAS INVIOLÁVEIS com prioridade máxima | **Principal** |
| `guard_out` | Compara a resposta com linhas longas do system prompt | Rede de segurança |

### 10.2 Limitação assumida do filtro de entrada

O `guard_in` é regex. **Ele pega a tentativa escrita em português direto e nada
mais.** Paráfrase, outro idioma, codificação (base64, rot13), injeção indireta
via documento — tudo isso passa.

Isso não é um defeito a esconder, é o desenho: a camada existe para barrar o
caso óbvio antes de gastar chamada de LLM. **Quem sustenta a defesa é o system
prompt**, e é por isso que as REGRAS INVIOLÁVEIS estão no topo dele, marcadas
como imunes a instrução do usuário.

O `guard_out` também é limitado: pega reprodução **literal** de linha longa do
prompt. Um resumo em outras palavras passa.

### 10.3 O que foi testado

`evals/smoke_offline.py` valida sem chave de API:

- S01, S02 e o segundo turno do S03 são bloqueados na entrada, sem chegar ao
  gerador;
- o primeiro turno do S03 (pergunta legítima) **passa** — o filtro não é
  indiscriminado;
- perguntas legítimas, inclusive as de memória, não são bloqueadas (sem falso
  positivo);
- resposta que reproduz linha do system prompt é substituída por recusa;
- resposta normal não dispara o `guard_out`.

Os casos S04–S07 dependem do modelo e são avaliados na bateria real: eles
testam o system prompt, não o regex.

---

## 11. Ganho da nova arquitetura sobre o baseline

| Dimensão | Baseline Sprint 2 (`ask_ai`) | Agente (`agent_core`) |
|---|---|---|
| Memória | Manual: `history[-10:]` do SQLite | `MemorySaver` por `thread_id` |
| Roteamento | Toda pergunta vai ao FAISS | Aresta condicional por intenção |
| Pergunta sem termo buscável | Busca mesmo assim e responde com chunk irrelevante | Vai para `conversa`, responde da memória |
| Prompt injection | Sem defesa dedicada | `guard_in` + regras invioláveis + `guard_out` |
| Troca de modelo | Hard-coded no `ai_service.py` | Variável de ambiente |
| Contexto vazio | Corta antes de ler o histórico | Responde pelo histórico quando ele basta |

---

## 12. Limitações conhecidas e próximos passos

1. **`MemorySaver` é memória de processo.** Reiniciou a API, perdeu todas as
   sessões; e com mais de uma réplica, cada uma tem a sua. Para produção,
   trocar por `SqliteSaver` ou `PostgresSaver` — é mudança de uma linha no
   `compile()`, porque o resto do grafo não sabe qual checkpointer está lá.
2. **Sem poda de histórico.** Conversa longa cresce o prompt sem limite, até
   estourar a janela de contexto e o custo. Falta uma janela deslizante ou
   sumarização dos turnos antigos.
3. **`guard_in` é regex.** Ver seção 10.2.
4. **Avaliação qualitativa é manual**, portanto subjetiva e não reproduzível
   por terceiros. Uma rubrica escrita de critérios por caso reduziria isso.
5. **Roteador custa uma chamada extra de LLM por turno.** Impacta latência e
   tokens. Medir o custo dele isoladamente é trabalho de sprint seguinte.
6. **Base de conhecimento ausente do repositório.** `app/rag/docs/` não está
   versionado em nenhum commit do histórico, e `app/rag/vector_store/` é
   gerado. Sem os 12 `.txt` não há como rodar `create_vector_store.py` nem a
   bateria. Decidir se o corpus entra no repositório ou se há uma fonte
   externa documentada.
7. **Métricas antigas do README sem medição.** `Latência P50 ~800ms`,
   `recall 98%` e `F1-Score 90.2%` aparecem no README como se fossem deste
   sistema. Não há medição por trás delas neste repositório — o F1 de 90.2% é
   do benchmark STS-B do modelo de embedding, não do ChargeGrid AI. Substituir
   pelos números reais de `evals/results/` ou remover. **Não foram alterados
   nesta sprint por serem decisão do grupo.**
