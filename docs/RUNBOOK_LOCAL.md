# Runbook — rodar a Sprint 03 na máquina local

Objetivo: sair do clone e chegar às métricas do relatório. Tempo estimado com
a chave em mãos: **15 a 25 minutos**, a maior parte esperando o `pip install`
do `torch`.

---

## 1. Clonar e entrar na branch

```bash
git clone https://github.com/Thiagoolivs/chargedgrid-ai.git
cd chargedgrid-ai
git fetch --all
git checkout claude/funny-goodall-cy1nug
```

> **A branch foi reconstruída sobre `master`** (Sprint 2), não sobre `main`
> (Sprint 1). Se você já tinha essa branch local, o `git pull` vai recusar —
> use `git fetch origin && git reset --hard origin/claude/funny-goodall-cy1nug`.
> O código agora vive na **raiz**, não em `chargegrid-ai/`.

Se você já tem o repositório clonado:

```bash
cd chargedgrid-ai
git fetch origin
git checkout claude/funny-goodall-cy1nug
git pull origin claude/funny-goodall-cy1nug
```

## 2. Ambiente Python

**Windows (PowerShell)**
```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

**macOS / Linux**
```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

> Demora. `torch` e `sentence-transformers` somam alguns GB.

## 3. Chaves

```bash
cp .env.example .env      # Windows: copy .env.example .env
```

Abra o `.env` e preencha:

```
GROQ_API_KEY=gsk_...
GOOGLE_API_KEY=            # opcional, ver seção 6
```

O `.env` está no `.gitignore`. **Não comite.**

## 4. Diagnóstico

```bash
python verificar_ambiente.py
```

Ele lista o que está pronto, o que falta e **quais comandos já dão para rodar
agora**. Use a saída dele para decidir a ordem.

## 5. Ordem de execução

```bash
# 5.1 — estrutural, sem chave e sem índice. Deve dar 28/28.
python evals/smoke_offline.py

# 5.2 — DEMONSTRAÇÃO DE MEMÓRIA (requisito 3.2). Só precisa da GROQ_API_KEY.
#        Gera evals/results/demo_memoria.md, pronto para colar no PDF.
python evals/demo_memoria.py

# 5.3 — índice FAISS, se os 12 .txt estiverem em app/rag/docs/
python create_vector_store.py

# 5.4 — baseline "antes" (EXIGE o índice)
python evals/run_legacy.py

# 5.5 — bateria no agente, dois modelos
python evals/run.py --model groq/llama-3.3-70b-versatile
python evals/run.py --model groq/llama-3.1-8b-instant

# 5.6 — preencher 'adequado' (true/false) nos JSONs de evals/results/
#        e então gerar a tabela
python evals/comparativo.py
```

## 5b. Os 12 documentos do RAG

Eles estão **no `.gitignore`** da branch `master`, linha 26, sob o cabeçalho
"RAG: arquivos gerados (não versionar)". Não são gerados — são fonte. Por isso
não existem em commit nenhum. Coloque-os em `app/rag/docs/`.

**Os nomes importam.** `rag_service.py` mapeia palavra-chave para arquivo
(`KEYWORD_SOURCE_HINTS`), então renomear quebra o direcionamento do retrieval.
A lista exata, conforme o system prompt da Sprint 1:

```
app/rag/docs/
├── autenticacao.txt
├── carregamento.txt
├── comunicacao.txt
├── conectividade.txt
├── eficiencia_energetica.txt
├── especificacoes_tecnicas.txt
├── faturamento.txt
├── manutencao.txt
├── monitoramento.txt
├── seguranca.txt
├── troubleshooting_guide.txt
└── modbus_reference.txt
```

Depois de colocá-los:

```bash
python create_vector_store.py
python verificar_ambiente.py     # deve ficar tudo OK
```

> **Decidam se o corpus entra no repositório.** São arquivos-fonte, não
> gerados — diferente do `vector_store/`, que está no `.gitignore` de
> propósito. Sem eles versionados, ninguém consegue reproduzir a entrega.

---

## 6. Sobre o segundo modelo

A seção 5 da Sprint aceita **"diferentes versões de um mesmo fornecedor"**.
Dois modelos da Groq satisfazem o bloco B inteiro — a chave do Google é
opcional.

### Usando o Gemini

```bash
python evals/run.py --list-google-models          # confirma o nome exato
python evals/run.py --model google/<nome-exato>
```

Registre o nome usado na seção 4 de `docs/relatorio_modelos.md`.

> A Sprint 2 já roda LangChain 1.x (`langchain-core==1.4.0`), então
> `langchain-google-genai==4.2.5` entra sem conflito — resolvido e verificado
> com `pip install --dry-run`. Ainda assim, **confirme o nome do modelo com
> `--list-google-models`** antes de rodar a bateria inteira: nome de modelo
> muda.
>
> Se o Gemini falhar por qualquer motivo, o bloco B não fica em risco:
> `run.py` trata a falha de um modelo sem derrubar o outro, e a seção 5 aceita
> "diferentes versões de um mesmo fornecedor".

**Experimento de parâmetro** (sugerido pela Sprint):

```bash
python evals/run.py --model groq/llama-3.3-70b-versatile --temperature 0.5
```

Grava um JSON separado, sem sobrescrever a rodada de 0.1.

## 7. Interface

```bash
uvicorn app.main:app --reload
```

- `http://localhost:8000/` — chat (o Volt)
- `http://localhost:8000/docs` — Swagger
- `POST /agent/chat` com `{"conversation_id": null, "message": "..."}`

## 8. Preencher o campo `adequado`

Os harnesses gravam `adequado: null`. A avaliação é manual — a seção 4 exige
*"o resultado obtido e uma breve análise indicando se o comportamento foi
considerado adequado ou inadequado"*.

Em cada resultado de `evals/results/*.json`:

```json
"adequado": true,
"nota": "Citou o registro 10060 com os valores 1 e 2, como o doc manda."
```

Depois rode `python evals/comparativo.py` de novo. Enquanto houver `null`, a
tabela mostra `pendente` em vez de taxa.

## 9. Assinar os commits

Os commits da branch estão com autoria correta mas **sem assinatura** — foram
criados num container remoto, sem a chave SSH. Na sua máquina, com a chave no
`ssh-agent`:

```bash
git rebase --exec 'git commit --amend --no-edit -S' 8428bd6
git push --force-with-lease origin claude/funny-goodall-cy1nug
```

Seguro: a branch é sua, não foi mergeada e ninguém mais a tem.

## 10. Problemas comuns

| Sintoma | Causa | Saída |
|---|---|---|
| `RuntimeError: Indice vetorial nao encontrado` | índice não gerado | `python create_vector_store.py`, ou pule o `run_legacy.py` |
| `pip` falha lendo o requirements | arquivo estava em UTF-16 | já corrigido nesta branch; use o desta branch |
| `Nenhum documento encontrado em .../rag/docs` | os 12 `.txt` não estão no repositório | recupere com o grupo; sem eles, rode só 5.1, 5.2 e 5.5 |
| `RuntimeError: GROQ_API_KEY nao esta definida` | `.env` ausente ou vazio | seção 3 |
| 429 no meio da bateria | limite por minuto | já há retry com backoff; aumente com `--sleep 6` |
| `503` em `/agent/chat` | chave ausente no processo do uvicorn | reinicie o servidor depois de editar o `.env` |
| Interface carrega mas erro ao enviar | backend fora do ar | a própria bolha de erro mostra o comando |
