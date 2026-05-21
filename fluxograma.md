# ChargeGrid AI - Fluxograma de Funcionamento

## Arquitetura do Sistema RAG

```
┌─────────────────────────────────────────────────────────────────┐
│                    USUÁRIO / FRONTEND                            │
│                                                                   │
│          "Como ativar Dynamic Load Control?"                    │
└──────────────────────────┬──────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                   API FastAPI /chat                              │
│         POST /chat { "message": "pergunta" }                    │
│                      routes/chat.py                             │
└──────────────────────────┬──────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│              1. RETRIEVAL - Busca Semântica (RAG_SERVICE)        │
│                                                                   │
│  • Converte pergunta em embedding 384D (sentence-transformers)  │
│  • Busca FAISS: Max Marginal Relevance (k=8, fetch_k=30)       │
│  • Aplica keyword hints (ex: "dynamic" → modbus_reference.txt) │
│  • Prioriza documentos relevantes                               │
│  • Retorna: 8 chunks contextualizados com fonte                │
│                                                                   │
│  ✓ Entrada: pergunta do usuário                                 │
│  ✓ Saída: context = "Fonte 1: ...\n---\nFonte 2: ..."         │
└──────────────────────────┬──────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│              2. AUGMENTATION - Context Injection (AI_SERVICE)    │
│                                                                   │
│  • Carrega system_prompt.txt (instruções do ChargeGrid AI)      │
│  • Constrói mensagem:                                           │
│    1. [SYSTEM]: system_prompt.txt                               │
│    2. [USER]: "Use SOMENTE o contexto:\n{context}\nPergunta: X" │
│                                                                   │
│  ✓ Grounding: força LLM a usar APENAS docs fornecidas          │
│  ✓ Controle: previne alucinações genéricas                      │
└──────────────────────────┬──────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│              3. GENERATION - LLM Inference (AI_SERVICE)          │
│                                                                   │
│  Provider:  Groq (llama-3.3-70b-versatile)                      │
│  Temperature: 0.05 (determinístico, preciso)                    │
│  Max tokens: 1200 (resposta concisa)                            │
│                                                                   │
│  Modelos alternativos suportados:                               │
│  • llama-3.1-405b (mais preciso, mais lento)                   │
│  • mixtral-8x7b (mais rápido, menos preciso)                   │
│                                                                   │
│  ✓ Saída: resposta técnica estruturada                          │
└──────────────────────────┬──────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│              4. RESPONSE - Formatação & Entrega                  │
│                                                                   │
│  Estrutura esperada (conforme system_prompt.txt):               │
│                                                                   │
│  [VISÃO GERAL]                                                  │
│  2-3 linhas explicando o conceito                               │
│                                                                   │
│  [COMO FUNCIONA]                                                │
│  Passos ou procedimento lógico                                  │
│                                                                   │
│  [DETALHES TÉCNICOS]                                            │
│  Registros Modbus, valores, unidades                            │
│                                                                   │
│  [NOTAS/AVISOS]                                                 │
│  Segurança ou limitações                                        │
│                                                                   │
│  [PRÓXIMOS PASSOS]                                              │
│  Ação recomendada                                               │
│                                                                   │
│  ✓ Saída: JSON { "response": "...", "sources": [...] }        │
└──────────────────────────┬──────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                   USUÁRIO / FRONTEND                             │
│                                                                   │
│          ✓ Resposta precisa, técnica, rastreável                │
└─────────────────────────────────────────────────────────────────┘
```

---

## Componentes do Sistema

### 📚 BASE DE CONHECIMENTO (app/rag/docs/)

```
12 arquivos TXT
│
├── autenticacao.txt ..................... RFID, SolarGo, SEMS, AUTO Start
├── carregamento.txt ..................... Modos, parâmetros, status
├── comunicacao.txt ....................... Modbus TCP, RS485, Wi-Fi, BT
├── conectividade.txt .................... Inversores, topologias, medidores
├── eficiencia_energetica.txt ........... PV Priority, PV+BAT, DLC
├── especificacoes_tecnicas.txt ........ Dados elétricos, físicos, ambientais
├── faturamento.txt ...................... MID, medição, custo por sessão
├── manutencao.txt ....................... Procedimentos, atualizações
├── monitoramento.txt .................... LED, registros, alarmes
├── seguranca.txt ........................ RCBO, aterramento, proteções
├── troubleshooting_guide.txt ........... Diagnóstico de problemas
└── modbus_reference.txt ................. 100+ registros TCP com ganhos
```

**Total:** ~50KB de documentação técnica oficial GoodWe

---

### 🔗 PIPELINE DE EMBEDDING

```
Documentos TXT
    │
    ▼ (TextLoader - UTF-8)
Documentos carregados
    │
    ▼ (RecursiveCharacterTextSplitter)
    ├─ Chunk size: 900 caracteres
    ├─ Overlap: 180 caracteres
    └─ Separadores: markdown aware
    │
    ▼ (~400-500 chunks gerados)
Chunks processados
    │
    ▼ (HuggingFaceEmbeddings - all-MiniLM-L6-v2)
    ├─ Modelo: 384 dimensões
    ├─ Velocidade: ~5ms por chunk
    └─ Precisão: excelente para PT-BR
    │
    ▼
FAISS Index (vector_store/)
    ├─ Tipo: Flat (indexação bruta, melhor recall)
    ├─ Distância: L2 (euclidiana)
    └─ Persistência: binário local (~15MB)
```

---

### ⚙️ FLUXO DE BUSCA (RETRIEVAL)

```
Pergunta: "Como ativar Dynamic Load Control?"
    │
    ▼ (1. Análise de Keywords)
    ├─ Keywords encontradas: ["dynamic", "load", "control"]
    ├─ Hints ativados: modbus_reference.txt, conectividade.txt
    └─ Dica de conteúdo: "10025", "10026"
    │
    ▼ (2. Embedding da Pergunta)
    └─ Vetor 384D gerado
    │
    ▼ (3. Busca FAISS - MMR)
    ├─ fetch_k=30 (busca ampla primeiro)
    ├─ k=8 (filtra os 8 melhores)
    ├─ Diversidade + Relevância balanceados
    └─ Tempo: <50ms
    │
    ▼ (4. Priorização)
    ├─ Reordena por fonte (modbus_reference primeiro)
    ├─ Reordena por conteúdo (chunks com "10025")
    └─ Remove duplicatas
    │
    ▼ (5. Formatação Final)
    ├─ Fonte 1: modbus_reference.txt (registro 10025)
    ├─ Fonte 2: conectividade.txt (topologias)
    ├─ Fonte 3: seguranca.txt (avisos)
    ├─ Fonte 4-8: contexto suplementar
    └─ Total: ~3000-4000 caracteres contextualizados
```

---

## Estados Possíveis do Sistema

### ✅ SUCESSO
```
Pergunta → Embedding → Busca FAISS → Ranking → LLM → Resposta Coerente
```
**Exemplo:** "Como vincular RFID?" → Encontra autenticacao.txt + SolarGo steps → Resposta passo-a-passo

### ⚠️ CONTEXTO PARCIAL
```
Pergunta → Embedding → Busca encontra algo → LLM diz "Parcialmente documentado"
```
**Exemplo:** "Qual é a taxa de carregamento em Celsius por minuto?" → Encontra especificacoes, menciona +50°C mas sem taxa

### ❌ FORA DO ESCOPO
```
Pergunta → Embedding → Nenhum resultado relevante → LLM retorna padrão
```
**Exemplo:** "Como programar um Smart TV?" → Sem documentação → "Essa informação não está documentada."

---

## Fluxo de Integração com Frontend (Exemplo)

```python
# Frontend faz:
POST /chat HTTP/1.1
Content-Type: application/json

{
  "message": "Qual é a potência máxima do GW7K?"
}

# Backend:
1. Recebe em routes/chat.py
2. Chama rag_service.retrieve_context(message)
3. Chama ai_service.ask_ai(message, context)
4. Retorna:

{
  "response": "O GW7K-HCA-20 tem potência nominal de 7 kW (monofásico)...",
  "sources": [
    {"source": "especificacoes_tecnicas.txt", "rank": 1},
    {"source": "modbus_reference.txt", "rank": 2}
  ]
}

# Frontend renderiza resposta + cita fontes
```

---

## Validação de Qualidade (Test Loop)

```
┌─ Pergunta de Teste
│  (ex: "10060?")
│
▼
Resposta RAG Gerada
│
▼
Comparar com Esperado
│ ┌─ ✓ Correto?
│ │  └─ Documentar ✓
│ │
│ └─ ✗ Incorreto?
│    ├─ Aumentar k (mais contexto)?
│    ├─ Ajustar system_prompt?
│    ├─ Adicionar doc detalhado?
│    └─ Regenerar embeddings
│
▼
Resultado: Score (0-100%)
```

---

## Métricas de Monitoramento

| Métrica | Alvo | Ferramenta |
|---------|------|----------|
| Latência P50 | <1s | Logs timestamp |
| Latência P99 | <3s | APM (se integrado) |
| Acurácia | >85% | Manual review |
| Cobertura tópicos | >95% | Test suite |
| Taxa erro | <5% | Exception logs |
| Uptime API | >99% | Health check /health |

---

## Próximos Passos (Sprint 2)

```
Sprint 1 (Atual)        Sprint 2 (Próximo)
│                       │
├─ ✓ RAG setup          ├─ [] UI/Frontend
├─ ✓ Documentação       ├─ [] WebSocket streaming
├─ ✓ System Prompt      ├─ [] Cache de respostas
├─ ✓ Test cases         ├─ [] Fine-tuning modelo
└─ ✓ Deploy docs        ├─ [] Feedback loop
                        └─ [] Analytics
```