# ⚡ ChargeGrid AI
### Assistente Técnico Inteligente para Carregadores GoodWe HCA-G2

> **EV Challenge 2026 — GoodWe** · Turma 1CCPO · Branch de entrega: `sprint-03`

Sistema de chatbot especializado com **Retrieval Augmented Generation (RAG)** para suporte técnico em tempo real a carregadores de veículos elétricos da linha GoodWe HCA-G2. Na **Sprint 03** o núcleo conversacional foi refatorado para um **agente LangGraph** com memória gerenciada pelo framework, roteamento por intenção e três camadas de guardrail.

---

## 📦 Entrega da Sprint 03

| Entregável (seção 8) | Onde |
|---|---|
| Relatório de evolução (PDF, 4 páginas) | [`docs/relatorio_evolucao.pdf`](docs/relatorio_evolucao.pdf) |
| Relatório de modelos | [`docs/relatorio_modelos.md`](docs/relatorio_modelos.md) |
| Casos de teste (funcionais, memória, segurança, injection) | [`evals/cases.json`](evals/cases.json) — 17 casos, 24 turnos |
| Resultados medidos | [`evals/results/`](evals/results/) — 4 rodadas, 68 resultados |
| Comparativo antes × depois | [`evals/results/comparativo.md`](evals/results/comparativo.md) |
| Demonstração de memória (requisito 3.2) | [`evals/results/demo_memoria.md`](evals/results/demo_memoria.md) |
| Código do agente | [`agent_core/`](agent_core/) |
| Identificação dos integrantes | [`docs/integrantes.txt`](docs/integrantes.txt) |

### Resultado medido

| | Baseline Sprint 2 | Agente Sprint 03 |
|---|---|---|
| Casos adequados | 8/17 — **47,1%** | 17/17 — **100,0%** |
| Memória (M01–M03) | 1/3 | **3/3** |
| Segurança e escopo | 4/8 | **8/8** |
| Latência por turno | 25,78 s | **4,04 s** |
| Tentativa de prompt injection | ~25 s de inferência | **0,006 s**, sem chamar o LLM |

Modelo escolhido após experimentação: **`google/gemini-3.6-flash`**, temperatura 0.1 — justificativa na [seção 9 do relatório de modelos](docs/relatorio_modelos.md).

**Nenhum número acima foi digitado à mão.** Todos saem de `evals/results/`, gerados por script.

### Conferir em segundos, sem chave de API

```bash
python evals/smoke_offline.py              # 28 verificações do grafo → 28 ok
python evals/verificar_rastreabilidade.py  # 6/6 perguntas literais da Sprint 1
```

Reproduzir a bateria completa: [`docs/RUNBOOK_LOCAL.md`](docs/RUNBOOK_LOCAL.md).

### Arquitetura do agente

```
START → guard_in ─┬─ (bloqueado) ───────────────────────→ refuse ─┐
                  └─ (ok) → router ─┬─ tecnica → retrieve → generate ─┤
                                    ├─ conversa ────────→ generate ─┤
                                    └─ fora_escopo ─────→ refuse ───┤
                                                                     ▼
                                                        guard_out → END
```

O histórico da Sprint 2 (`master`) e da Sprint 1 (`main`) continua no repositório, sem alteração — é o "antes" que o comparativo exige.

---

## 🎯 Problema Central

Os eletropostos GoodWe HCA-G2, apesar de tecnicamente robustos, carecem de mecanismos integrados para:

| Gap Identificado | Impacto |
|---|---|
| Orquestração de potência | Ineficiência em ambientes multi-carregador |
| Registro de ciclos de carregamento | Rastreabilidade limitada |
| Faturamento transparente | Dificuldade de custeio por usuário/sessão |
| Comunicação com usuários | Alto volume de chamados técnicos simples |

O ChargeGrid AI resolve esses gaps entregando **conhecimento técnico acessível e instantâneo** via interface web e API — sem consultar PDF, sem esperar suporte humano.

---

## 💡 Proposta de Valor

### 🔧 Para Operadores Comerciais
- Diagnóstico rápido de problemas por LED e conectividade
- Referência técnica sem consultar manual PDF
- Redução do tempo médio de resolução de incidentes

### 🏢 Para Síndicos e Gestores
- Entendimento de custeio e faturamento por sessão
- Configuração guiada de Dynamic Load Control
- Consulta de histórico de carregamentos

### ⚙️ Para Técnicos e Integradores
- Referência completa Modbus TCP (100+ registros)
- Topologias de integração com inversores GoodWe
- Protocolos de segurança (RCBO, aterramento, IK10)

---

## 🖥️ Interface

Interface web dark mode acessível diretamente em `http://localhost:8000`, sem instalação adicional.

**Funcionalidades:**
- Sidebar com histórico das últimas 7 conversas
- Botão "Novo Chat" para iniciar sessão limpa
- 6 perguntas frequentes pré-definidas e clicáveis na tela inicial
- Respostas renderizadas em Markdown (tabelas, código, listas)
- Fontes citadas abaixo de cada resposta do assistente
- Indicador de digitação animado durante a geração
- Input com auto-resize e atalhos de teclado (Enter envia · Shift+Enter quebra linha)

---

## 🧠 Memória Persistente

O sistema mantém duas camadas de memória usando **SQLite local** (`chargegrid.db`):

| Camada | Comportamento |
|---|---|
| **Sessão** | O assistente recebe os últimos 10 turnos da conversa ativa como contexto |
| **Histórico** | Armazena até 7 conversas; ao criar a 8ª, a mais antiga é apagada automaticamente |

As conversas persistem entre reinicializações do servidor e ficam acessíveis na sidebar.

---

## 🏗️ Arquitetura Técnica

### Pipeline RAG

```
Pergunta do Usuário
        │
        ▼
┌───────────────────────────────────┐
│  [1] RETRIEVAL                    │
│  Busca Semântica (MMR)            │
│  FAISS + keyword hints            │
│  → 10 contextos relevantes        │
└───────────────┬───────────────────┘
                │
                ▼
┌───────────────────────────────────┐
│  [2] AUGMENTATION                 │
│  Injeta contexto + histórico      │
│  + system prompt                  │
│  Temperature: 0.05 (determinístico│
└───────────────┬───────────────────┘
                │
                ▼
┌───────────────────────────────────┐
│  [3] GENERATION                   │
│  Groq (ver relatorio_modelos.md)  │
│  Latência medida em evals/results │
└───────────────┬───────────────────┘
                │
                ▼
┌───────────────────────────────────┐
│  [4] RESPONSE                     │
│  Resposta estruturada + fontes    │
│  Salva no histórico (SQLite)      │
└───────────────────────────────────┘
```

### Stack Técnico

| Camada | Tecnologia | Detalhe |
|---|---|---|
| Frontend | HTML/CSS/JS + marked.js | Interface dark mode, sem build step |
| Backend | FastAPI (Python, async) | Handlers assíncronos, validação automática |
| Memória | SQLite | Histórico de conversas local e persistente |
| Embedding | HuggingFace `all-MiniLM-L6-v2` | 384D, carregado uma vez na inicialização |
| Vector Store | FAISS (Meta) | Local e privado; recall não medido neste repositório |
| LLM | Groq via `AsyncGroq` | Modelo da Sprint 2 descontinuado pelo provedor — ver `docs/relatorio_modelos.md` |
| Orquestração | LangChain | Abstração de provider, modular |
| API | REST + JSON | Simples, escalável, padrão |

---

## 📚 Base de Conhecimento

12 documentos técnicos derivados do **Manual Oficial GoodWe HCA-G2 V1.5 (2025-11-11)** — 19KB total indexado.

| # | Arquivo | Conteúdo |
|---|---|---|
| 1 | `autenticacao.txt` | RFID, SolarGo, SEMS Portal, AUTO Start |
| 2 | `carregamento.txt` | Modos, parâmetros, potência, status |
| 3 | `comunicacao.txt` | Modbus TCP, RS485, Wi-Fi, Bluetooth |
| 4 | `conectividade.txt` | Inversores GoodWe, topologias, medidores |
| 5 | `eficiencia_energetica.txt` | PV Priority, PV+BATT, Dynamic Load Control |
| 6 | `especificacoes_tecnicas.txt` | Modelos GW7K/11K/22K, specs, dimensões |
| 7 | `faturamento.txt` | Medidor MID, energy tracking, custo |
| 8 | `manutencao.txt` | Procedimentos, firmware, descarte |
| 9 | `monitoramento.txt` | LED, registros Modbus, alarmes |
| 10 | `seguranca.txt` | Proteções, RCBO 30mA, aterramento, IK10 |
| 11 | `troubleshooting_guide.txt` | 10+ falhas mapeadas com soluções |
| 12 | `modbus_reference.txt` | 100+ registros TCP com ganhos e tipos |

---

## 🔐 Configurações RAG

### Embedding
| Parâmetro | Valor |
|---|---|
| Modelo | `sentence-transformers/all-MiniLM-L6-v2` |
| Dimensões | 384D |
| Dimensões do índice | 59 chunks a partir de 12 `.txt` |

### Chunking
| Parâmetro | Valor |
|---|---|
| Tamanho do chunk | 900 caracteres |
| Overlap | 180 caracteres (20%) |
| Separadores | Markdown-aware (`##`, `###`, `\n\n`) |

### Retrieval
| Parâmetro | Valor |
|---|---|
| Método | Max Marginal Relevance (diversidade + relevância) |
| K (resultados finais) | 10 documentos |
| Fetch K (candidatos) | 50 documentos |
| Keyword Hints | `"modbus"` → `modbus_reference.txt` · `"rfid"` → `autenticacao.txt` |

### LLM Inference
| Parâmetro | Valor |
|---|---|
| Provider | Groq |
| Modelo | `llama-3.3-70b-versatile` |
| Temperature | 0.05 (determinístico) |
| Max Tokens | 1200 |
| Contexto de histórico | Últimas 10 mensagens da conversa ativa |
| Latência medida | ver `evals/results/baseline_sprint2.json` |

### System Prompt
- **Estrutura de resposta:** `[RESPOSTA DIRETA]` → `[COMO FUNCIONA]` → `[DETALHES TÉCNICOS]` → `[VERIFICAÇÕES]` → `[NOTAS E SEGURANÇA]` → `[PRÓXIMO PASSO]`
- **Restrição de domínio:** Responde apenas com contexto fornecido pelos documentos RAG
- **Anti-alucinação:** Se não estiver documentado, retorna exatamente `"Essa informacao nao esta documentada."` e encerra — sem preencher blocos adicionais

---

## 📂 Estrutura do Projeto

```
chargegrid-ai/
├── app/
│   ├── main.py                    # FastAPI app — inicializa DB, monta rotas e static
│   ├── database.py                # SQLite — conversas e mensagens (max 7 conversas)
│   ├── routes/
│   │   ├── chat.py                # POST /chat (async, histórico, error handling)
│   │   └── conversations.py       # CRUD /conversations
│   ├── services/
│   │   ├── embedding_service.py   # Criação de embeddings FAISS
│   │   ├── rag_service.py         # Busca semântica + dedup de fontes
│   │   └── ai_service.py          # AsyncGroq + prompt cacheado + histórico
│   ├── models/
│   │   └── schemas.py             # Pydantic models (ChatRequest, ConversationCreate)
│   ├── prompts/
│   │   └── system_prompt.txt      # Instruções de comportamento do AI
│   └── rag/
│       ├── docs/                  # Documentos TXT (base de conhecimento)
│       └── vector_store/          # Index FAISS (gerado automaticamente)
├── static/
│   └── index.html                 # Interface web dark mode (sidebar + chat + sugestões)
├── chargegrid.db                  # Banco SQLite criado automaticamente na primeira execução
├── create_vector_store.py         # Script para gerar embeddings
├── requirements.txt               # Dependências Python
└── .env                           # Variáveis de ambiente (GROQ_API_KEY)
```

---

## 🚀 Como Usar

### 1. Clonar o Repositório

```bash
git clone <repo-url>
cd chargegrid-ai
```

### 2. Instalar Dependências

```bash
pip install -r requirements.txt
```

### 3. Configurar Variáveis de Ambiente

Crie um arquivo `.env` na raiz do projeto:

```bash
echo "GROQ_API_KEY=gsk_..." > .env
```

> ⚠️ Nunca commite o arquivo `.env`. Ele já está no `.gitignore`.

### 4. Gerar o Vector Store

Execute apenas na primeira vez (ou sempre que atualizar os documentos):

```bash
python create_vector_store.py
```

Isso processa os 12 documentos em `app/rag/docs/` e gera o índice FAISS em `app/rag/vector_store/`.

### 5. Iniciar o Servidor

**Opção A — clique duplo (Windows):**

Execute o arquivo `run.bat` na raiz do projeto.

**Opção B — PowerShell (copie e cole inteiro):**

```powershell
$env:PYTHONPATH = "C:\Users\user\Desktop\Sprint prompt`&ai\chargegrid-ai"
& "C:\Users\user\Desktop\Sprint prompt`&ai\.venv\Scripts\uvicorn.exe" app.main:app --host 0.0.0.0 --port 8001
```

**Opção C — se o venv estiver ativo:**

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8001
```

O banco de dados SQLite (`chargegrid.db`) é criado automaticamente na primeira execução.

> **Nota:** A porta padrão é **8001**. A porta 8000 pode estar reservada pelo Hyper-V/Docker no Windows.

### 6. Acessar

| URL | Descrição |
|---|---|
| `http://localhost:8001` | Interface web (dark mode chat) |
| `http://localhost:8001/docs` | Documentação interativa (Swagger UI) |

---

## 📡 API Reference

### `POST /chat`

Envia uma pergunta ao assistente. Se `conversation_id` for fornecido, o histórico da conversa é incluído no contexto.

**Request:**
```json
{
  "message": "Qual é o registro Modbus para ligar o carregamento?",
  "conversation_id": "uuid-opcional"
}
```

**Response:**
```json
{
  "response": "### [RESPOSTA DIRETA]\nO registro Modbus para controlar carregamento é 10060...",
  "sources": [
    {"source": "modbus_reference.txt", "rank": 1},
    {"source": "carregamento.txt", "rank": 2}
  ]
}
```

---

### `GET /conversations`

Lista as últimas 7 conversas armazenadas, ordenadas da mais recente para a mais antiga.

**Response:**
```json
[
  {"id": "uuid", "title": "Como ligar o carregador via Mo...", "created_at": "2026-06-15T18:00:00"}
]
```

---

### `POST /conversations`

Cria uma nova conversa. Se já houver 7 conversas, a mais antiga é removida automaticamente.

**Request:**
```json
{ "title": "Título da conversa" }
```

---

### `GET /conversations/{id}/messages`

Retorna todas as mensagens de uma conversa, em ordem cronológica.

**Response:**
```json
[
  {"id": "uuid", "role": "user", "content": "...", "sources": [], "created_at": "..."},
  {"id": "uuid", "role": "assistant", "content": "...", "sources": [...], "created_at": "..."}
]
```

---

### `DELETE /conversations/{id}`

Remove uma conversa e todas as suas mensagens.

---

## 📊 Exemplos de Perguntas Suportadas

### Operacionais
```
"Como ativar Dynamic Load Control no GW11K?"
"Como vincular um cartão RFID?"
"Qual é a sequência para iniciar um carregamento?"
```

### Técnicas
```
"Qual é o registro Modbus para potência máxima?"
"Como se comunica com o medidor MID?"
"Quais são as proteções integradas do carregador?"
```

### Troubleshooting
```
"Meu carregador está com LED vermelho fixo. O que fazer?"
"Como resetar o carregador para configuração de fábrica?"
"Qual é a temperatura máxima de operação?"
```

---

## 🧪 Testes & Validação

6 casos de teste definidos com critérios de sucesso mensuráveis:

| # | Teste | Domínio |
|---|---|---|
| 1 | Operacional Básica (SolarGo) | Autenticação e conectividade |
| 2 | Técnico — Modbus | Registros e protocolo TCP |
| 3 | Autenticação RFID | Modos de acesso e vinculação |
| 4 | Dynamic Load Control | Eficiência energética |
| 5 | Troubleshooting | Diagnóstico e resolução de falhas |
| 6 | Especificações Técnicas | Modelos GW7K/11K/22K |

**Critério de aprovação:** ≥ 5/6 testes com ≥ 75% dos critérios atendidos por teste.

---

## 📈 Métricas de Performance

**Todo número desta seção sai de `evals/results/`.** Nenhum valor é estimado.
Para regerar: `python evals/run_legacy.py`, `python evals/run.py`,
`python evals/avaliar.py` e `python evals/comparativo.py`.

A tabela consolidada, com latência, tokens e taxa de acerto por arquitetura e
por modelo, está em **`evals/results/comparativo.md`** e em
**`docs/relatorio_modelos.md`**.

> **Correção de histórico.** Versões anteriores deste README traziam
> `Latência P50 ~800ms`, `Latência P99 ~2s`, `recall 98%` e
> `F1-Score 90.2%` como se fossem medições deste sistema. Não eram: nunca
> houve medição por trás desses números neste repositório, e o F1 de 90,2% é
> do benchmark STS-B do modelo de embedding `all-MiniLM-L6-v2`, não do
> ChargeGrid AI. Foram removidos na Sprint 03 e substituídos pelos valores
> efetivamente medidos.

---

## 🛡️ Segurança & Privacidade

| Controle | Status |
|---|---|
| API Key armazenada em `.env` (nunca em código) | ✅ |
| Vector Store com indexação local (sem cloud) | ✅ |
| Histórico de conversas armazenado localmente (SQLite) | ✅ |
| Conhecimento restrito a documentos técnicos aprovados | ✅ |
| Guardrail anti-alucinação: encerra resposta se não documentado | ✅ |
| Validação de input/output via Pydantic schemas | ✅ |
| Rate Limiting | ⚠️ Não implementado — recomendado em produção |

---

## ⚙️ Configurações & Customização

Para alterar o comportamento do assistente, edite:

- **System prompt:** `app/prompts/system_prompt.txt` — controla tom, estrutura e restrições de resposta
- **Perguntas sugeridas:** array `SUGGESTIONS` em `static/index.html`
- **Limite de conversas:** constante `MAX_CONVERSATIONS` em `app/database.py` (padrão: 7)
- **Parâmetros de chunking/retrieval:** `app/services/embedding_service.py` e `rag_service.py`
- **Modelo LLM:** variável `model` em `app/services/ai_service.py`
- **Base de conhecimento:** adicione/remova arquivos `.txt` em `app/rag/docs/` e execute `create_vector_store.py` novamente

---

## 🔗 Recursos Externos

| Recurso | Link |
|---|---|
| Manual Oficial GoodWe HCA-G2 V1.5 | Referência base (2025-11-11) |
| SEMS Portal | Monitoramento cloud GoodWe |
| SolarGo App | Configuração via Bluetooth |
| Groq API | `https://console.groq.com` |
| HuggingFace — MiniLM | `sentence-transformers/all-MiniLM-L6-v2` |
| LangChain Docs | `https://docs.langchain.com` |
| FAISS (Meta) | `https://github.com/facebookresearch/faiss` |

---

## 🖥️ Modelos Suportados

| Modelo | Potência | Observações |
|---|---|---|
| GW7K-HCA-20 | 7kW | Residencial/leve comercial |
| GW11K-HCA-20 | 11kW | Comercial padrão |
| GW22K-HCA-20 | 22kW | Comercial intensivo |

**Protocolos principais:** Modbus TCP · RS485 · Wi-Fi · Bluetooth  
**Aplicações integradas:** SolarGo (Bluetooth) · SEMS Portal (Cloud)

---

## 📅 Histórico de Versões

| Versão | Data | Descrição |
|---|---|---|
| v1.0.0 | Sprint 1 — 2025 | Release inicial — EV Challenge 2026 |
| v2.0.0 | Sprint 2 — Jun/2026 | Interface web dark mode · Memória persistente (SQLite, 7 conversas) · Histórico de sessão · Perguntas pré-definidas · Handlers async · Guardrail corrigido · Dedup de fontes |

---

## 📄 Licença

Projeto desenvolvido para o **EV Challenge 2026** em parceria com **GoodWe**.  
Documentação técnica baseada no Manual Oficial GoodWe HCA-G2 V1.5 © GoodWe Technologies.

---

*ChargeGrid AI — Transformando documentação técnica em suporte inteligente para a mobilidade elétrica.*
