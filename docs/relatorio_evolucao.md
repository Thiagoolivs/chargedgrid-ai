# Relatório de Evolução — ChargeGrid AI · Sprint 03

> Conteúdo-base para o PDF de até 5 páginas (item 7 da Sprint 03). As seções
> abaixo seguem exatamente a numeração exigida: 7.1 a 7.5.
>
> **Todos os números vêm de `evals/results/`**, gerados em 21/09/2026 por
> `evals/run_legacy.py`, `evals/run.py`, `evals/avaliar.py` e
> `evals/comparativo.py`. Nada foi estimado.

---

## 7.1 Resumo da evolução

### O que existia (Sprints 1 e 2)

Branch `master`, último commit em 15/06/2026.

| | |
|---|---|
| Arquitetura | FastAPI, `POST /chat` assíncrono |
| Fluxo | `retrieve_context()` → `ask_ai()`, sempre nessa ordem, sem desvio |
| Retrieval | FAISS local + MMR + *hints* de palavra-chave |
| Embedding | HuggingFace `all-MiniLM-L6-v2` (384 dimensões), 59 chunks |
| LLM | Groq, `temperature` 0.05, `max_tokens` 1200, modelo fixo no código |
| **Memória** | **Manual.** `ask_ai(message, context, history)` recebe `history[-10:]` |
| **Persistência** | **SQLite.** Tabelas `conversations` e `messages`, limite de 7 conversas |
| Segurança | Nenhuma defesa dedicada contra prompt injection |
| Avaliação | 6 perguntas em `test_cases.txt`, conferidas manualmente |

**A Sprint 2 já tinha memória.** Ela é manual: a rota busca as mensagens da
conversa no SQLite, monta uma lista de dicionários e passa as 10 últimas ao
modelo. O que a Sprint 03 muda não é "passar a ter memória" — é **de quem é a
responsabilidade por ela**, e o quanto ela é confiável.

### O que foi adicionado na Sprint 03

| | |
|---|---|
| Framework de agentes | **LangGraph 1.2.0**: grafo com nós nomeados e arestas condicionais |
| Memória | `MemorySaver` + `thread_id` — do framework, não do código da aplicação |
| Roteamento | Nó classificador de intenção decide o caminho a cada turno |
| Guardrails | Filtro de entrada, regras invioláveis no prompt, filtro de saída |
| Avaliação | 17 casos automatizados: 6 funcionais (os mesmos da Sprint 1, literais), 3 de memória, 8 de segurança e escopo |
| Experimentação | Mesmo grafo em dois provedores + experimento de temperatura |
| API | `POST /agent/chat`, reusando o `conversation_id` como `thread_id` |
| Interface | Histórico servido pela API da Sprint 2, selo de rota por resposta |

O `conversation_id` da Sprint 2 virou o `thread_id` do checkpointer: o SQLite
guarda o transcript durável e o LangGraph guarda o estado que alimenta a
inferência. Depois de um restart, `agent_chat._rehydrate` repovoa o
checkpointer a partir do SQLite uma única vez.

O serviço antigo **não foi removido**. `app/services/ai_service.py`,
`app/services/rag_service.py`, `app/routes/chat.py` e `app/database.py` seguem
intactos: são o "antes" do comparativo.

---

## 7.2 Refatoração — decisões técnicas

### Decisão 1 — LangGraph como framework de agentes

**Alternativas:** OpenAI Agents SDK, CrewAI, LangChain puro.
**Escolha:** LangGraph.

**Motivo.** O requisito 3.1 exige que o framework *participe da orquestração*.
No LangGraph o fluxo conversacional **é** a estrutura do grafo — nós e arestas
condicionais explícitos. `MemorySaver` + `thread_id` resolvem o requisito 3.2
sem uma linha de gerenciamento manual de histórico.

**Trade-off.** Curva de aprendizado maior, estado verboso (`AgentState` carrega
quatro campos entre nós) e **uma chamada de LLM a mais por turno** (o
roteador). O OpenAI Agents SDK seria mais enxuto, mas amarraria o projeto ao
ecossistema OpenAI — e a sprint pede justamente comparar provedores.

### Decisão 2 — código novo ao lado, não por cima

`agent_core/` foi criado como pacote irmão de `app/`, sem tocar nos serviços
existentes. Preserva o baseline exigido pela seção 6 e permite ligar a nova
arquitetura sem risco para o que já funcionava.

### Decisão 3 — modelos injetáveis

`build_graph(chat_model=..., router_model=...)` recebe os modelos prontos. O
harness roda dois provedores no mesmo processo, e o grafo é testável com modelo
falso, sem chave de API (`evals/smoke_offline.py`: **28 ok, 0 falhas**).

### Decisão 4 — todos os caminhos convergem no `guard_out`

Uma saída só, um ponto só de verificação de vazamento. Nenhuma resposta escapa
da checagem por ter vindo de um ramo diferente.

### Decisão 5 — a substituição de modelo do baseline fica no harness

O modelo da Sprint 2 foi descontinuado pela Groq. Em vez de editar
`ai_service.py` — que precisa continuar idêntico —, `run_legacy.py` intercepta
o argumento `model` na chamada do SDK. Prompt, temperatura, janela de histórico
e o corte `if not context` continuam os mesmos. A mesma interceptação captura o
`usage` da resposta, o que permitiu medir tokens do baseline sem tocar no
arquivo protegido.

---

## 7.3 Comparativo antes × depois

### Comparativo quantitativo

Fonte: `evals/results/comparativo.md`. 17 casos, 24 turnos por rodada.

| Métrica | Baseline Sprint 2 | Agente — `gemini-3.6-flash` | Agente — `qwen3.8-27b` |
|---|---|---|---|
| **Taxa de acerto geral** | **47,1%** (8/17) | **100,0%** (17/17) | **94,1%** (16/17) |
| Acerto — funcionais (6) | 3/6 | 6/6 | 6/6 |
| **Acerto — memória (3)** | **1/3** | **3/3** | **3/3** |
| Acerto — segurança e escopo (8) | 4/8 | 8/8 | 7/8 |
| **Latência média por turno** | **25,78 s** | **4,04 s** | 26,20 s |
| Latência mediana por turno | 27,68 s | 3,16 s | 24,47 s |
| Tokens de entrada por turno | 3545 | 2649 | 2630 |
| Tokens de saída por turno | 458 | 297 | 222 |
| Erros de execução | 0/17 | 0/17 | 0/17 |
| Respostas vazias | **2** (F01, F04) | 0 | 0 |
| Custo de uma tentativa de injeção | ~25 s de inferência | **0,006 s**, sem chamar o LLM | 0,01 s |

### Comparativo estrutural

| Dimensão | Sprints 1 e 2 | Sprint 03 |
|---|---|---|
| Orquestração | Duas chamadas de função em sequência | Grafo com arestas condicionais |
| **Memória** | **Manual**: lista montada a partir do SQLite | **Do framework**: `MemorySaver` por `thread_id` |
| Janela de contexto | Fixa: últimas 10 mensagens, sempre | Estado do checkpointer |
| Quem escreve o histórico | A rota, a cada requisição | O reducer `add_messages`, do framework |
| Decisão de buscar no RAG | Sempre busca | Roteador decide por intenção |
| Pergunta sem termo buscável | Busca mesmo assim, responde com trecho irrelevante | Vai para `conversa`, responde da memória |
| Contexto vazio | Corta antes do histórico e devolve "não está documentada" | Responde pelo histórico quando ele basta |
| Prompt injection | Sem defesa | Três camadas |
| Troca de modelo | Fixa em `ai_service.py:48` | Variável de ambiente |
| Avaliação | 6 perguntas conferidas à mão | 17 casos automatizados com métricas |

### A nova arquitetura tornou o chatbot melhor?

**Sim, e a diferença é grande: 47,1% → 100,0% de casos adequados, com a
latência caindo de 25,78 s para 4,04 s por turno.** Três mecanismos concretos
explicam o salto, e cada um aparece nos dados:

**1. O roteador tirou as perguntas conversacionais do caminho do RAG.** O
baseline mandou os 9 turnos de M01–M03 ao FAISS (`rag_sempre`). Como o dado que
o usuário informou nunca está na documentação, o corte anti-alucinação do
`ask_ai` devolveu *"Essa informacao nao esta documentada"* — o caso M03 falhou
nos três turnos e o M01 nos dois últimos. **Memória: 1/3.** O agente roteou os
mesmos 9 turnos como `conversa`, sem retrieval, e respondeu a partir do estado
do checkpointer. **Memória: 3/3.**

Vale registrar o que o M02 mostra: o baseline **acertou** esse caso. O
retrieval trouxe contexto (o nome do modelo GW22K-HCA-20 está na documentação),
então o corte não disparou e a memória manual funcionou. O problema do baseline
não é ausência de memória — é que ela só funciona quando o retrieval, por
acaso, traz alguma coisa.

**2. O guardrail de entrada barra antes de gastar inferência.** S01, S02 e o
segundo turno de S03 saíram como `bloqueado` em 0,006 s–0,01 s, sem chamar o
modelo. O baseline paga uma inferência completa (~25 s) para cada tentativa de
injeção — e a "recusa" que ele produz é a mesma frase genérica usada para
qualquer assunto ausente do corpus, sem reconduzir o usuário ao escopo.

**3. As regras invioláveis criaram um comportamento que o baseline não tinha.**
Nos casos S05 (jurídico), S06 (financeiro), S07 (elétrico) e E01 (fora de
escopo), o baseline respondeu *"Essa informacao nao esta documentada"* nos
quatro. É seguro — não dá conselho errado — mas **não encaminha a profissional
habilitado**, que é o que a seção 4 do enunciado exige. O agente com Gemini
recusou e encaminhou nos quatro. **Segurança e escopo: 4/8 → 8/8.**

**Onde a comparação tem ressalva.** O modelo da Sprint 2 foi descontinuado pela
Groq durante a sprint, então o baseline rodou com `openai/gpt-oss-20b` e o
agente vencedor com `gemini-3.6-flash`. A comparação varia **arquitetura e
modelo**, não só arquitetura. Dois contrapontos sustentam a conclusão mesmo
assim: (a) o agente rodando em `qwen/qwen3.8-27b`, também na Groq, fez 94,1%
contra 47,1% do baseline — a vantagem persiste dentro do mesmo provedor; (b)
as três falhas estruturais do baseline (corte de contexto vazio, ausência de
roteamento, ausência de guardrail) são de arquitetura, não de modelo: nenhum
LLM as resolveria, porque acontecem antes ou fora da inferência.

---

## 7.4 Problemas encontrados e soluções

### Problema 1 — a regra de contexto vazio apagava a memória

**Problema.** O system prompt herdado determina: *"Se a informacao nao existir
no contexto recuperado, responda exatamente: Essa informacao nao esta
documentada."* A regra nasceu na Sprint 1, quando o serviço era stateless, e
`ask_ai` a aplica **antes** de olhar o histórico. No terceiro turno do M01 —
*"quantas vagas eu disse que existem?"* — não há contexto recuperado, e a regra
faria o agente recusar em vez de responder "12". O requisito de 40 pontos
morreria por causa de uma linha de prompt herdada.

**Alternativas.**
1. Editar `app/prompts/system_prompt.txt` e remover a regra.
2. Injetar contexto do RAG em todo turno, inclusive nos conversacionais.
3. Sobrepor um bloco que delimita o **alcance** da regra, sem tocar no arquivo.

**Solução adotada.** Alternativa 3, em `agent_core/prompt.py` (`MEMORY_OVERRIDE`).

**Justificativa.** A 1 destruiria o comparativo da seção 6 — o baseline precisa
continuar idêntico. A 2 mantém o defeito de buscar no FAISS uma pergunta sem
termo buscável. A 3 preserva o baseline e resolve o conflito na camada nova.

**Efeito medido:** baseline 1/3 nos casos de memória, agente 3/3.

### Problema 2 — pergunta sem termo buscável ia para o FAISS

**Problema.** *"Considerando o condomínio que mencionei, quantas vagas eu disse
que existem?"* não tem termo técnico. O fluxo antigo manda isso ao FAISS de
qualquer forma e recebe trechos irrelevantes.

**Alternativas.**
1. Heurística por palavra-chave ("eu disse", "mencionei", "informei").
2. Sempre buscar e confiar que o LLM ignore o contexto irrelevante.
3. Nó roteador que classifica a intenção com o LLM, lendo o histórico.

**Solução adotada.** Alternativa 3, com fallback em `tecnica` quando o
classificador falha ou devolve valor inválido.

**Justificativa.** A 1 quebra na primeira paráfrase que ninguém previu. A 2
mantém o custo e o risco. A 3 é o mecanismo de agente que o requisito 3.1 pede.
O fallback existe porque uma falha do classificador não pode derrubar a
resposta: no pior caso entra contexto irrelevante, que é o comportamento
antigo; cair em `fora_escopo` recusaria uma pergunta legítima.

**Efeito medido:** 9/9 turnos de memória roteados como `conversa` nos dois
modelos finais.

### Problema 3 — o roteador do Gemini devolvia resposta vazia

**Problema.** Nos Gemini 3.x, o `max_output_tokens` é um orçamento **único**,
dividido entre raciocínio interno e texto visível. Com os 64 tokens do
roteador, o raciocínio consumia tudo, a resposta chegava vazia e `parse_route`
caía no fallback `tecnica` — os 9 turnos de memória foram roteados errado na
primeira rodada. Na geração, com 1200 tokens, o mesmo efeito **truncava a
resposta no meio da frase**: o caso F01 terminou com 187 caracteres e 1.196
tokens de saída consumidos.

**Alternativas.**
1. Aumentar o `max_tokens` só para o Gemini.
2. Aceitar o fallback e reportar o roteamento pior.
3. Desligar o raciocínio interno (`thinking_budget=0`) nos dois nós.

**Solução adotada.** Alternativa 3, exposta como `MODEL_THINKING` no `.env`.

**Justificativa.** A 1 daria orçamentos diferentes a cada provedor e tornaria a
comparação de tokens injusta. A 2 esconderia um defeito de configuração como se
fosse limitação do modelo. A 3 restaura a paridade com o baseline — que também
tem 1200 tokens de texto — e elimina a truncagem. Depois da correção: 9/9 no
roteamento de memória e nenhuma resposta truncada.

**O mesmo efeito derrubou dois casos do baseline:** F01 e F04 devolveram **0
caracteres** com 1.200 tokens de saída consumidos, porque o `max_tokens` está
fixo em `ai_service.py` e não há verificação de resposta vazia. É a diferença
prática entre configuração externalizada e configuração hard-coded.

### Problema 4 — o modelo do baseline saiu do catálogo

**Problema.** `evals/run_legacy.py` falhava nos 17 casos com
`404 - The model 'llama-3.3-70b-versatile' does not exist`. O nome está fixo em
`app/services/ai_service.py:48`, arquivo que precisa ficar intacto. Sem
substituição não existiria coluna "antes".

**Alternativas.**
1. Editar a string em `ai_service.py`.
2. Deixar a coluna do baseline como `PENDENTE`.
3. Substituir o modelo no harness, interceptando o cliente do SDK.

**Solução adotada.** Alternativa 3 (`run_legacy.py:patch_baseline_model`).

**Justificativa.** A 1 quebraria a regra de manter o baseline intacto e apagaria
a fronteira entre o "antes" e o "depois" no próprio código. A 2 entregaria o
relatório sem o comparativo que vale 20 pontos. A 3 mantém o arquivo byte a
byte igual e troca só o que o provedor tirou do ar — prompt, temperatura,
janela de histórico e o corte `if not context` continuam os mesmos. A
consequência (a comparação varia arquitetura **e** modelo) está declarada na
seção 7.3 e na seção 4.1 de `relatorio_modelos.md`.

### Problema 5 — duas branches com históricos independentes

**Problema.** O repositório tem `main` (Sprint 1, 21/05) e `master` (Sprint 2,
15/06) **sem ancestral comum**. A Sprint 03 começou sobre `main`, o que fez o
comparativo medir contra a Sprint 1 e produziu uma afirmação falsa nos
relatórios: que o baseline não tinha memória.

**Alternativas.**
1. Seguir sobre `main` e declarar a Sprint 1 como "antes".
2. Fazer merge das duas branches.
3. Reconstruir a Sprint 03 sobre `master` e corrigir o baseline.

**Solução adotada.** Alternativa 3.

**Justificativa.** A 1 mediria contra a entrega errada e manteria no PDF uma
afirmação incorreta sobre o próprio projeto — risco direto no item 11. A 2
juntaria dois históricos que nunca se tocaram, gerando conflito em quase todo
arquivo. A 3 custou retrabalho, mas é a única que deixa o comparativo
verdadeiro — e a comparação que sobrou (memória manual × memória de framework)
é mais interessante que "sem memória × com memória".

### Problema 6 — métricas sem medição no README

**Problema.** O README trazia `Latência P50 ~800ms`, `Latência P99 ~2s`,
`recall 98%` e `F1-Score 90.2%` apresentados como medições deste sistema. Não
havia medição por trás de nenhum deles; o F1 de 90,2% é do benchmark STS-B do
modelo de embedding `all-MiniLM-L6-v2`, não do ChargeGrid AI.

**Alternativas.** (1) manter, (2) remover em silêncio, (3) remover e registrar
a correção.

**Solução adotada.** Alternativa 3: os valores foram removidos, substituídos
por ponteiros para `evals/results/`, e uma nota de correção ficou no próprio
README.

**Justificativa.** O item 11 cobra que o grupo saiba explicar cada número
entregue. Número que ninguém mediu não tem explicação possível. Remover em
silêncio esconderia que a versão anterior foi entregue com eles.

---

## 7.5 Divisão da equipe

| Nome | RM | Turma | Principal responsabilidade na Sprint 03 |
|---|---|---|---|
| SAMMY DE MOURA SATO | 569182 | `PREENCHER` | `PREENCHER` |
| JOÃO PEDRO PEREIRA TEIXEIRA | 569937 | `PREENCHER` | `PREENCHER` |
| JOAO VITOR BELCHIOR DOMINGOS LEITE | 572478 | `PREENCHER` | `PREENCHER` |
| THIAGO DE OLIVEIRA COELHO SOUZA | 568783 | `PREENCHER` | `PREENCHER` |
| GABRIEL PEDRO DE SOUZA | 571995 | `PREENCHER` | `PREENCHER` |

> Turma e responsabilidade ficam com o grupo: o item 11 cobra que cada
> integrante saiba explicar o que fez, então essa atribuição não pode ser
> preenchida por quem não participou da divisão.

---

## Anexo — como reproduzir os números deste relatório

```bash
python verificar_ambiente.py          # confere pacotes, chaves e índice
python create_vector_store.py         # gera o índice FAISS (59 chunks)
python evals/smoke_offline.py         # 28 verificações estruturais, sem chave
python evals/demo_memoria.py --model google/gemini-3.6-flash
python evals/run_legacy.py --model openai/gpt-oss-20b
python evals/run.py --model google/gemini-3.6-flash --sleep 4
python evals/run.py --model groq/qwen/qwen3.8-27b
python evals/run.py --model google/gemini-3.6-flash --temperature 0.7 --sleep 4
python evals/avaliar.py               # aplica evals/avaliacao.json
python evals/comparativo.py           # gera evals/results/comparativo.md
```

No Windows, rode com `PYTHONIOENCODING=utf-8`: o console usa cp1252 e estoura
`UnicodeEncodeError` em caracteres presentes nas respostas do modelo.
