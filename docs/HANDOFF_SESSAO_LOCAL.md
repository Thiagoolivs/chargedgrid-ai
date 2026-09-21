# Handoff para a sessão local — Sprint 03

Documento de passagem de bastão. A arquitetura foi construída numa sessão
remota, sem chave de API e sem a base de conhecimento. **Esta sessão tem as
duas coisas** — a missão é converter isso em resultados medidos.

> **A branch foi reconstruída sobre `master`** (Sprint 2), não sobre `main`
> (Sprint 1). O código vive na raiz. O baseline do comparativo é o `ask_ai`
> **com memória manual** da Sprint 2.

Leia `CLAUDE.md` antes. As regras invioláveis de lá valem em tudo o que segue.

---

## O que já está pronto (não refazer)

| Item | Onde | Verificação |
|---|---|---|
| Grafo LangGraph com memória | `agent_core/` | `evals/smoke_offline.py` → 28 ok |
| Roteador de intenção + fallback | `agent_core/nodes.py` | idem |
| Guardrails de entrada e saída | `agent_core/guardrails.py` | idem |
| Bateria de 17 casos | `evals/cases.json` | 6 funcionais = os da Sprint 1, literais |
| Harness agente + baseline | `evals/run.py`, `run_legacy.py` | exercitado com modelo falso |
| Gerador do comparativo | `evals/comparativo.py` | idem |
| Demo de memória | `evals/demo_memoria.py` | gera transcript em markdown |
| Endpoint `/agent/chat` | `app/routes/agent_chat.py` | reusa `conversation_id` como `thread_id` |
| Interface (Volt) | `static/index.html` | servida em `/ui` |
| `requirements.txt` que instala | — | reescrito em UTF-8; estava em UTF-16 e o pip falhava |
| Relatórios estruturais | `docs/relatorio_*.md` | números marcados `PENDENTE` |

**Não reescreva nada disso sem motivo concreto.** Se algo falhar, conserte o
ponto que falhou.

---

## Missão, em ordem

### Passo 0 — diagnóstico

```bash
cd chargegrid-ai
python verificar_ambiente.py
```

**Aceite:** a saída lista o que está pronto. Use-a para decidir o que dá para
rodar — não adivinhe.

Se faltarem pacotes: `pip install -r requirements.txt` num venv com Python
3.10+.

---

### Passo 1 — validação estrutural

```bash
python evals/smoke_offline.py
```

**Aceite:** `28 ok, 0 falha(s)`.

**Se falhar:** algo do grafo quebrou. Conserte antes de seguir — todo o resto
depende disso. Não desative teste para passar.

---

### Passo 2 — base de conhecimento

Coloque os 12 `.txt` em `app/rag/docs/`. Os nomes exatos estão no
`RUNBOOK_LOCAL.md`, seção 5b. **Não renomeie**: o `rag_service.py` mapeia
palavra-chave para arquivo e renomear quebra o direcionamento do retrieval.

```bash
python create_vector_store.py
```

**Aceite:** imprime `Embeddings criados com sucesso: N chunks processados` e
`app/rag/vector_store/` passa a existir.

**Se os .txt não aparecerem:** siga assim mesmo. Os passos 3, 5 e 6 rodam sem
eles; o passo 4 não. Registre a ausência no relatório — não invente o corpus,
não gere documento sintético para preencher.

---

### Passo 3 — demonstração de memória (requisito 3.2)

```bash
python evals/demo_memoria.py
```

**Aceite:** `evals/results/demo_memoria.md` existe e, no caso M01, o terceiro
turno responde **12** citando **Solar Park**, com rota `conversa`.

**Este é o passo mais valioso da lista.** É o bloco A, 40 pontos, e não
depende do índice FAISS — só da `GROQ_API_KEY`.

**Se o terceiro turno responder "Essa informação não está documentada":** a
regra de contexto vazio venceu a memória. Verifique `MEMORY_OVERRIDE` em
`agent_core/prompt.py` e `turn_instructions()`. Não resolva no `cases.json`.

---

### Passo 4 — baseline "antes"

```bash
python evals/run_legacy.py
```

**Aceite:** `evals/results/baseline_ask_ai.json` com 17 resultados.

**Não assuma que M01–M03 falham.** A Sprint 2 tem memória manual
(`history[-10:]` do SQLite), então ela pode acertar. O que interessa é medir
*como* cada lado se comporta. Se o baseline errar, verifique se caiu no corte
`if not context` de `ask_ai`, que acontece antes de o histórico ser lido —
esse é o achado, e ele precisa de evidência, não de suposição.

**Exige o índice FAISS.** Sem ele o import do `rag_service` levanta
`RuntimeError` e o passo não roda — é o único que tem essa dependência dura.

---

### Passo 5 — bateria no agente, dois modelos

```bash
python evals/run.py --list-google-models          # confirme o nome do Gemini
python evals/run.py --model groq/llama-3.3-70b-versatile
python evals/run.py --model google/<nome-confirmado>
```

**Aceite:** um JSON por modelo em `evals/results/`, cada um com 17 resultados
e `rota` preenchida.

**Registre o nome exato do Gemini** na seção 4 de `docs/relatorio_modelos.md`.

**Se o Gemini falhar:** `langchain-google-genai` está em 1.0.10 porque
`langchain-core` está preso em 0.2.x pelo `rag_service.py`. Não suba a stack
para resolver — quebraria o RAG. Use um segundo modelo da Groq
(`groq/llama-3.1-8b-instant`): a seção 5 aceita "diferentes versões de um
mesmo fornecedor".

**Se estourar 429:** já existe retry com backoff. Aumente com `--sleep 6`.

Opcional, sugerido pela rubrica:
```bash
python evals/run.py --model <vencedor> --temperature 0.5
```

---

### Passo 6 — avaliação qualitativa (é do Thiago, não sua)

Em cada resultado de `evals/results/*.json`, preencher:

```json
"adequado": true,
"nota": "Citou o registro 10060 com os valores 1 e 2, como o doc manda."
```

A seção 4 da Sprint exige "o resultado obtido e uma breve análise indicando se
o comportamento foi considerado adequado ou inadequado" **por teste**.

**Não preencha esse campo por conta própria** e não implemente LLM-as-judge.
Se o Thiago pedir ajuda, proponha o julgamento caso a caso e deixe ele
confirmar.

---

### Passo 7 — comparativo

```bash
python evals/comparativo.py
```

**Aceite:** `evals/results/comparativo.md` com taxas reais no lugar de
`pendente`.

---

### Passo 8 — fechar os relatórios

1. `docs/relatorio_modelos.md` — colar as tabelas nas seções 6 e 7, escrever a
   escolha final na 9 aplicando os critérios já definidos na 5.1. A
   justificativa precisa citar **número medido**, não impressão de uso.
2. `docs/relatorio_evolucao.md` — preencher a tabela quantitativa da 7.3 e
   responder a pergunta do fim da seção: *a nova arquitetura tornou o chatbot
   melhor?*
3. `docs/integrantes.txt` e a seção 7.5 — nome, RM, turma, responsabilidade.

O PDF de até 5 páginas é montado pelo grupo a partir do
`relatorio_evolucao.md`, que já segue a numeração 7.1–7.5 exigida.

---

### Passo 9 — assinar os commits

Os commits da branch têm autoria correta mas **estão sem assinatura** — foram
criados num container remoto sem a chave SSH do Thiago.

```bash
git rebase --exec 'git commit --amend --no-edit -S' 8428bd6
git push --force-with-lease origin claude/funny-goodall-cy1nug
```

**Confirme antes com o Thiago.** Seguro porque a branch é dele, não foi
mergeada e ninguém mais a tem — mas é reescrita de histórico.

**Aceite:** `git log --pretty='%h %G?'` mostra `G` em vez de `N`.

---

## Armadilhas conhecidas

| Armadilha | Por quê |
|---|---|
| "Vou só ajustar o `rag_service.py`" | Mata o comparativo da seção 6. Ele é o "antes" |
| "O baseline não tem memória" | **Tem.** Manual, `history[-10:]` do SQLite. Nunca escreva o contrário |
| "O baseline falhou na memória, vou consertar" | Não conserte o baseline. Registre o resultado e por que ele falhou |
| "Vou estimar a latência, foi mais ou menos isso" | Item 11. Todo número sai de `evals/results/` |
| "Vou reescrever as perguntas dos testes funcionais" | A seção 6 exige o mesmo conjunto da Sprint 1, literal |
| "Vou guardar o histórico numa lista para garantir" | Memória tem que vir do framework, ou o bloco A cai |
| "Vou subir o langchain para resolver o Gemini" | Quebra o `rag_service.py`, que está preso em 0.2.x |
| "Vou assinar o commit sem a chave" | Nunca `--no-gpg-sign`. Pare e avise |

## Onde a nota está

| Bloco | Peso | Hoje | Depende de |
|---|---|---|---|
| A — framework e memória | 40 | ~28 | passo 3 |
| B — dois modelos | 25 | ~5 | passo 5 |
| C — guardrails | 15 | ~10 | passo 5 (S04–S07) |
| D — relatório | 20 | ~13 | passos 4, 7, 8 |

Total estimado hoje: **~56/100**. Com os passos 3 a 8 concluídos: **~90**.

O passo 3 sozinho, que leva minutos e só precisa da chave da Groq, vale cerca
de 10 pontos. É por onde começar.
