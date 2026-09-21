# Relatório de Evolução — ChargeGrid AI · Sprint 03

> Conteúdo-base para o PDF de até 5 páginas (item 7 da Sprint 03). As seções
> abaixo seguem exatamente a numeração exigida: 7.1 a 7.5.
>
> **Status:** as métricas quantitativas da seção 7.3 saem de
> `evals/results/` e estão marcadas `PENDENTE` até a bateria ser
> executada. Nenhum número aqui foi estimado.

---

## 7.1 Resumo da evolução

### O que existia (Sprints 1 e 2)

Branch `master`, último commit em 15/06/2026.

| | |
|---|---|
| Arquitetura | FastAPI, `POST /chat` assíncrono |
| Fluxo | `retrieve_context()` → `ask_ai()`, sempre nessa ordem, sem desvio |
| Retrieval | FAISS local + MMR + *hints* de palavra-chave e de conteúdo |
| Embedding | HuggingFace `all-MiniLM-L6-v2` (384 dimensões) |
| LLM | Groq `llama-3.3-70b-versatile`, `temperature` 0.05, `max_tokens` 1200 |
| **Memória** | **Manual.** `ask_ai(message, context, history)` recebe `history[-10:]` |
| **Persistência** | **SQLite.** Tabelas `conversations` e `messages`, limite de 7 conversas |
| Rotas | `/chat` com `conversation_id`, `/conversations` (CRUD) |
| Interface | `static/index.html`, dark mode |
| Orquestração | LangChain presente apenas como *wrapper* de vectorstore |
| Segurança | Nenhuma defesa dedicada contra prompt injection |
| Avaliação | 6 perguntas em `test_cases.txt`, conferidas manualmente |

**A Sprint 2 já tinha memória.** Ela é manual: a rota busca as mensagens da
conversa no SQLite, monta uma lista de dicionários e passa as 10 últimas ao
modelo. O que a Sprint 03 muda não é "passar a ter memória" — é **de quem é a
responsabilidade por ela**.

### O que foi adicionado na Sprint 03

| | |
|---|---|
| Framework de agentes | **LangGraph**: grafo com nós nomeados e arestas condicionais |
| Memória | `MemorySaver` + `thread_id` — do framework, não do código da aplicação |
| Roteamento | Nó classificador de intenção decide o caminho a cada turno |
| Guardrails | Filtro de entrada, regras invioláveis no prompt, filtro de saída |
| Avaliação | 17 casos automatizados: 6 funcionais (os mesmos da Sprint 1), 3 de memória, 8 de segurança e escopo |
| Experimentação | Mesmo grafo em dois provedores, trocados por variável de ambiente |
| API | `POST /agent/chat`, reusando o `conversation_id` como `thread_id` |
| Interface | Volt: histórico servido pela API da Sprint 2, selo de rota por resposta |

O `conversation_id` da Sprint 2 virou o `thread_id` do checkpointer, então as
duas camadas falam da mesma conversa: o SQLite guarda o transcript durável e o
LangGraph guarda o estado que alimenta a inferência.

O serviço antigo **não foi removido**. `app/services/ai_service.py`,
`app/services/rag_service.py`, `app/routes/chat.py` e `app/database.py` seguem
intactos: são o "antes" do comparativo, e sem eles a comparação exigida pela
seção 6 não existiria.

---

## 7.2 Refatoração — decisões técnicas

### Decisão 1 — LangGraph como framework de agentes

**Alternativas consideradas:** OpenAI Agents SDK, CrewAI, LangChain puro.

**Escolha:** LangGraph.

**Motivo:** o requisito 3.1 exige que o framework *participe da orquestração*,
não que seja apenas importado. No LangGraph o fluxo conversacional **é** a
estrutura do grafo — nós e arestas condicionais explícitos. Além disso,
`MemorySaver` + `thread_id` resolvem o requisito 3.2 sem uma linha de
gerenciamento manual de histórico.

**Trade-off assumido:** curva de aprendizado maior e estado verboso
(`AgentState` existe para carregar quatro campos entre nós). O OpenAI Agents
SDK seria mais enxuto e tem guardrails de primeira classe, mas amarraria o
projeto ao ecossistema OpenAI — e a Sprint 03 pede justamente experimentar
provedores diferentes. O projeto já rodava em Groq e passou a rodar também em
Google; trocar de framework para ganhar concisão custaria essa portabilidade.

### Decisão 2 — código novo ao lado, não por cima

`agent_core/` foi criado como pacote irmão de `app/`, sem tocar nos serviços
existentes. Isso preserva o baseline exigido pela seção 6 e permite ligar a
nova arquitetura por *feature flag* sem risco para o que já funcionava.

### Decisão 3 — modelos injetáveis

`build_graph(chat_model=..., router_model=...)` recebe os modelos prontos em
vez de instanciá-los internamente. Consequências práticas: o harness roda os
dois provedores no mesmo processo, e o grafo é testável com um modelo falso,
sem chave de API e sem rede.

### Decisão 4 — todos os caminhos convergem no `guard_out`

Uma saída só, um ponto só de verificação de vazamento. Recusas prontas não
contêm o system prompt, então o nó é inócuo para elas — mas nenhuma resposta
escapa da checagem por ter vindo de um ramo diferente.

---

## 7.3 Comparativo antes × depois

### Comparativo estrutural

| Dimensão | Sprints 1 e 2 | Sprint 03 |
|---|---|---|
| Orquestração | Duas chamadas de função em sequência | Grafo com arestas condicionais |
| **Memória** | **Manual**: lista montada a partir do SQLite | **Do framework**: `MemorySaver` por `thread_id` |
| Janela de contexto | Fixa: últimas 10 mensagens, sempre | Estado do checkpointer, sem corte arbitrário |
| Quem escreve o histórico | A rota, a cada requisição | O reducer `add_messages`, do framework |
| Persistência | SQLite | SQLite (herdado) + checkpointer em memória |
| Decisão de buscar no RAG | Sempre busca | Roteador decide por intenção |
| Pergunta sem termo buscável | Busca mesmo assim, responde com trecho irrelevante | Vai para `conversa`, responde da memória |
| Contexto vazio | Corta antes do histórico e devolve "não está documentada" | Responde pelo histórico quando ele basta |
| Prompt injection | Sem defesa | Três camadas |
| Troca de modelo | Fixo no código | Variável de ambiente |
| Avaliação | 6 perguntas conferidas à mão | 17 casos automatizados com métricas |

**O ganho não é "ter memória".** A Sprint 2 já tinha. O ganho está em três
pontos concretos:

1. **Quem mantém o histórico.** Na Sprint 2, `chat.py` busca no banco, monta a
   lista e corta em 10 a cada requisição. Se alguém esquecer o corte ou mudar a
   ordem, a memória quebra silenciosamente. Na Sprint 03 isso é o reducer do
   framework — não há código de aplicação para errar.
2. **O corte de contexto vazio.** `ask_ai` tem
   `if not context: return "Essa informacao nao esta documentada."` **antes** de
   olhar o histórico. Uma pergunta sobre a própria conversa cujo retrieval não
   trouxe nada morre aí, com memória e tudo.
3. **Toda pergunta ia ao FAISS.** Inclusive "quantas vagas eu disse?". O
   roteador tira essas do caminho do retrieval.

### Comparativo quantitativo

> **PENDENTE.** Colar `evals/results/comparativo.md`, gerado por
> `python evals/comparativo.py`. A tabela traz, por modelo: taxa de acerto
> geral e por tipo, latência média por turno, tokens por turno, memória (X/3) e
> erros.

| Métrica | Baseline Sprint 2 | Modelo 1 (depois) | Modelo 2 (depois) |
|---|---|---|---|
| Taxa de acerto geral | `PENDENTE` | `PENDENTE` | `PENDENTE` |
| Acerto — funcionais (6) | `PENDENTE` | `PENDENTE` | `PENDENTE` |
| Acerto — memória (3) | `PENDENTE`² | `PENDENTE` | `PENDENTE` |
| Acerto — segurança (8) | `PENDENTE` | `PENDENTE` | `PENDENTE` |
| Latência média por turno | `PENDENTE` | `PENDENTE` | `PENDENTE` |
| Tokens por turno | não observável¹ | `PENDENTE` | `PENDENTE` |

¹ `ask_ai` devolve apenas a string da resposta. Expor o objeto de *usage* do
SDK exigiria alterar `ai_service.py`, que precisa ficar intacto para o
comparativo valer.

² **A Sprint 2 tem memória manual, então pode acertar os casos M01–M03.** Não
assuma 0/3 — meça. O interesse está em *como* cada lado falha: observe se o
baseline cai no corte de contexto vazio descrito acima.

### A nova arquitetura tornou o chatbot melhor?

> **PENDENTE de dados.** A resposta precisa sair dos números, não da narrativa.

O que já se sabe sem medir: a responsabilidade pela memória saiu do código da
aplicação e foi para o framework, e passou a existir uma decisão explícita
sobre buscar ou não na documentação. Se isso se traduz em resposta melhor é o
que a bateria vai dizer.

**Não afirme que o baseline não tinha memória.** Ele tinha.

## 7.4 Problemas encontrados e soluções

### Problema 1 — a regra de contexto vazio apagava a memória

**Problema.** O system prompt da Sprint 1 determina: *"Se a informacao nao
existir no contexto recuperado, responda exatamente: Essa informacao nao esta
documentada."* Essa regra nasceu na Sprint 1, quando o serviço era stateless, e
sobreviveu à Sprint 2 cortando antes de o histórico ser lido. No terceiro
turno do caso M01 — *"quantas vagas eu disse que existem?"* — não há contexto
recuperado, e a regra faria o agente recusar em vez de responder "12". O
requisito de 40 pontos morreria por causa de uma linha de prompt herdada.

**Alternativas.**
1. Editar `app/prompts/system_prompt.txt` e remover a regra.
2. Injetar contexto do RAG em todo turno, inclusive nos conversacionais.
3. Sobrepor um bloco que delimita o **alcance** da regra, sem tocar no arquivo.

**Solução adotada.** Alternativa 3, em `agent_core/prompt.py`.

**Justificativa.** A alternativa 1 destruiria o comparativo da seção 6 — o
baseline precisa continuar idêntico ao que era. A 2 mantém o defeito de buscar
no FAISS uma pergunta sem termo buscável, gastando tokens e arriscando
contaminar a resposta com trecho irrelevante. A 3 preserva o baseline e resolve
o conflito na camada nova, que é onde ele nasceu.

### Problema 2 — pergunta sem termo buscável ia para o FAISS

**Problema.** *"Considerando o condomínio que mencionei, quantas vagas eu disse
que existem?"* não tem termo técnico. O fluxo antigo manda isso ao FAISS de
qualquer forma e recebe trechos de `especificacoes_tecnicas.txt` que nada têm a
ver com a pergunta.

**Alternativas.**
1. Heurística por palavra-chave ("eu disse", "mencionei", "informei").
2. Sempre buscar e confiar que o LLM ignore o contexto irrelevante.
3. Nó roteador que classifica a intenção com o LLM, lendo o histórico.

**Solução adotada.** Alternativa 3, com fallback em `tecnica` quando o
classificador falha ou devolve valor inválido.

**Justificativa.** A 1 quebra na primeira paráfrase que ninguém previu. A 2
mantém o custo e o risco. A 3 é exatamente o mecanismo de agente que o
requisito 3.1 pede — o comportamento passa a ser definido pela estrutura do
grafo, não por `if` dentro de uma função. O fallback existe porque uma falha
do classificador não pode derrubar a resposta ao usuário: no pior caso entra
contexto irrelevante, que é o comportamento antigo; cair em `fora_escopo`
recusaria uma pergunta legítima, que seria pior.

### Problema 3 — o `requirements.txt` não instalava

**Problema.** `pip install -r requirements.txt` falhava. `langchain-huggingface
==0.0.51` não existe no PyPI, `langchain-community` estava ausente apesar de
ser importado por `rag_service.py`, e outros pins transitivos apontavam para
versões inexistentes.

**Alternativas.**
1. Atualizar toda a stack para LangChain 1.x.
2. Congelar o ambiente de um integrante com `pip freeze`.
3. Fixar apenas as dependências diretas, numa combinação 0.2.x verificada.

**Solução adotada.** Alternativa 3, conferida com `pip install --dry-run`.

**Justificativa.** A 1 quebraria `rag_service.py`, que é o diferencial do
projeto e não podia ser alterado. A 2 arrasta os pacotes `nvidia-*` que vêm
junto do `torch` no Linux e quebra a instalação em Mac e Windows — foi assim
que o arquivo original ficou inconsistente. A 3 instala em qualquer plataforma
e deixa o pip resolver o que é transitivo.

### Problema 4 — índice ausente derrubava o agente inteiro

**Problema.** `rag_service.py` carrega o FAISS no import e levanta
`RuntimeError` se o índice não existir. Com import no topo de `agent_core`, um
índice ausente derrubaria até as conversas que nem precisam de busca.

**Alternativas.**
1. Alterar `rag_service.py` para carregar sob demanda.
2. Exigir o índice sempre, e falhar cedo.
3. Import tardio e cacheado dentro do nó `retrieve`, com degradação.

**Solução adotada.** Alternativa 3.

**Justificativa.** A 1 está fora do escopo acordado. A 2 impediria demonstrar
memória e guardrails sem o corpus completo — e foi exatamente essa a situação
durante boa parte do desenvolvimento. A 3 mantém a conversa funcionando e
registra a degradação em vez de escondê-la.

### Problema 5 — duas branches com históricos independentes

**Problema.** O repositório tem `main` (Sprint 1, 21/05) e `master` (Sprint 2,
15/06) **sem ancestral comum** — `git merge-base` não devolve nada. A Sprint 03
começou sobre `main`, o que fez o comparativo medir contra a Sprint 1 e
produziu uma afirmação falsa nos relatórios: que o baseline não tinha memória.
A Sprint 2 tem memória manual com janela de 10 mensagens em SQLite.

**Alternativas.**
1. Seguir sobre `main` e declarar a Sprint 1 como "antes".
2. Fazer merge das duas branches.
3. Reconstruir a Sprint 03 sobre `master` e corrigir o baseline.

**Solução adotada.** Alternativa 3.

**Justificativa.** A 1 mediria contra a entrega errada e manteria no PDF uma
afirmação incorreta sobre o próprio projeto — risco direto no item 11, que
cobra que o grupo saiba explicar o que foi feito. A 2 juntaria dois históricos
que nunca se tocaram, gerando conflito em quase todo arquivo sem ganho. A 3
custou retrabalho, mas é a única que deixa o comparativo verdadeiro — e a
comparação que sobrou (memória manual × memória de framework) é exatamente a
que a seção 6 pede, e é mais interessante que "sem memória × com memória".

**Lição registrada:** `git branch -a` depois de `git fetch --all` deveria ter
sido o primeiro comando da sprint. A branch `master` não aparecia no clone
raso inicial.

---

## 7.5 Divisão da equipe

> **PREENCHER.** Ver `docs/integrantes.txt`.

| Nome | RM | Turma | Principal responsabilidade na Sprint 03 |
|---|---|---|---|
| | | | |
| | | | |
| | | | |
| | | | |
