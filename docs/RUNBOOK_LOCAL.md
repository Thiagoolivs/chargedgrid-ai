# Runbook — rodar a Sprint 03 na máquina local

Objetivo: sair do clone e chegar às métricas do relatório. Tempo estimado com
a chave em mãos: **15 a 25 minutos**, a maior parte esperando o `pip install`
do `torch`.

> **Atualizado em 21/09/2026, após a sessão de execução.** Tudo o que este
> runbook manda rodar já rodou nesta máquina, **incluindo o baseline**: a
> retirada do `llama-3.3-70b-versatile` do catálogo da Groq foi contornada no
> harness, sem tocar em `ai_service.py` (seção 6.1). Resultados em
> `evals/results/`, pendências em `docs/HANDOFF_SESSAO_LOCAL.md`.

---

## 1. Clonar e entrar na branch

```bash
git clone https://github.com/Thiagoolivs/chargedgrid-ai.git
cd chargedgrid-ai
git fetch --all
git checkout sprint-03
```

> **A branch foi reconstruída sobre `master`** (Sprint 2), não sobre `main`
> (Sprint 1). Se você já tinha essa branch local, o `git pull` vai recusar —
> use `git fetch origin && git reset --hard origin/sprint-03`.
> O código agora vive na **raiz**, não em `chargegrid-ai/`.

Se você já tem o repositório clonado:

```bash
cd chargedgrid-ai
git fetch origin
git checkout sprint-03
git pull origin sprint-03
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

No Windows, prefixe cada comando com `PYTHONIOENCODING=utf-8`: o console usa
cp1252 e as respostas do modelo trazem caracteres (hífen não separável, por
exemplo) que derrubam a execução com `UnicodeEncodeError`.

```bash
# 5.1 — estrutural, sem chave e sem índice. Deve dar 28/28.
python evals/smoke_offline.py

# 5.2 — DEMONSTRAÇÃO DE MEMÓRIA (requisito 3.2). Só precisa da chave.
#        Gera evals/results/demo_memoria.md, pronto para colar no PDF.
python evals/demo_memoria.py --model google/gemini-3.6-flash

# 5.3 — índice FAISS, se os 12 .txt estiverem em app/rag/docs/
python create_vector_store.py

# 5.4 — baseline "antes" (EXIGE o índice)
#        --model substitui o modelo descontinuado SEM editar ai_service.py
python evals/run_legacy.py --model openai/gpt-oss-20b

# 5.5 — bateria no agente, dois modelos
python evals/run.py --model google/gemini-3.6-flash --sleep 4
python evals/run.py --model groq/qwen/qwen3.8-27b

# 5.6 — avaliação qualitativa: editar evals/avaliacao.json, aplicar e comparar
python evals/avaliar.py
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

## 6.1 Modelos válidos hoje na Groq

O catálogo mudou desde a Sprint 2. `llama-3.3-70b-versatile` e
`llama-3.1-8b-instant` **não existem mais** — qualquer comando com esses nomes
retorna:

```
404 - The model `llama-3.3-70b-versatile` does not exist or you do not have access to it
```

Modelos de chat que a chave atual enxerga: `openai/gpt-oss-120b`,
`openai/gpt-oss-20b`, `qwen/qwen3.8-27b`, `groq/compound` e
`groq/compound-mini`. Para conferir a lista você mesmo, consulte
`GET https://api.groq.com/openai/v1/models` com a sua chave.

O agente contorna isso pela linha de comando (`--model groq/qwen/qwen3.8-27b`;
o *spec* quebra no primeiro `/`).

**O baseline também contorna, sem editar o arquivo protegido.** O modelo está
fixo em `app/services/ai_service.py:48`, que a regra 3 do `CLAUDE.md` manda não
alterar. `run_legacy.py --model <id>` intercepta o argumento `model` na chamada
do SDK (`patch_baseline_model`): prompt, temperatura, janela de histórico e o
corte `if not context` continuam idênticos, e `git diff app/services/` fica
vazio. A substituição está declarada na seção 4.2 de `docs/relatorio_modelos.md`.

**Cota diária:** a Groq limita a **200.000 tokens por dia, por modelo**. Uma
bateria consome de 68.000 a 96.000 tokens, então duas rodadas no mesmo modelo
Groq não cabem no mesmo dia. Foi por isso que o baseline rodou em
`openai/gpt-oss-20b` e o agente em `qwen/qwen3.8-27b`.

## 6. Sobre o segundo modelo

A seção 5 da Sprint aceita **"diferentes versões de um mesmo fornecedor"**.
Dois modelos da Groq satisfazem o bloco B inteiro — a chave do Google é
opcional.

### Usando o Gemini

```bash
python evals/run.py --list-google-models          # confirma o nome exato
python evals/run.py --model google/gemini-3.6-flash --sleep 4
```

O `gemini-2.0-flash` previsto no planejamento **não é mais servido a chaves
novas**: a própria API responde
`404 NOT_FOUND ... Please update your code to use models/gemini-3.6-flash`.

**Atenção aos Gemini 3.x:** `max_output_tokens` é um orçamento único, dividido
entre raciocínio interno e texto visível. Sem `MODEL_THINKING=0` no `.env`, o
roteador devolve resposta vazia (64 tokens gastos em raciocínio) e a geração
sai truncada no meio da frase. Ver seção 7.5 de `docs/relatorio_modelos.md`.

> A Sprint 2 já roda LangChain 1.x (`langchain-core==1.4.0`), então
> `langchain-google-genai==4.2.5` entra sem conflito — resolvido e verificado
> com `pip install --dry-run`. Ainda assim, **confirme o nome do modelo com
> `--list-google-models`** antes de rodar a bateria inteira: nome de modelo
> muda.
>
> Se o Gemini falhar por qualquer motivo, o bloco B não fica em risco:
> `run.py` trata a falha de um modelo sem derrubar o outro, e a seção 5 aceita
> "diferentes versões de um mesmo fornecedor".

**Experimento de parâmetro** (sugerido pela Sprint, já executado):

```bash
python evals/run.py --model google/gemini-3.6-flash --temperature 0.7 --sleep 4
```

Grava um JSON separado, sem sobrescrever a rodada de 0.1. Resultado em
`evals/results/agent_google_gemini_3_6_flash_t0_7.json` e na seção 6.5 de
`docs/relatorio_modelos.md`.

## 7. Interface

```bash
uvicorn app.main:app --reload
```

- `http://localhost:8000/` — chat (o Volt)
- `http://localhost:8000/docs` — Swagger
- `POST /agent/chat` com `{"conversation_id": null, "message": "..."}`

## 8. Avaliação qualitativa — `evals/avaliacao.json`

Os harnesses gravam `adequado: null`. A avaliação é manual — a seção 4 exige
*"o resultado obtido e uma breve análise indicando se o comportamento foi
considerado adequado ou inadequado"* por teste.

O julgamento **não vive no código**: fica em `evals/avaliacao.json`, um arquivo
de dados com o critério por tipo de caso e o veredito de cada caso, por rodada:

```json
"agent_google_gemini_3_6_flash.json": {
  "F02": {"adequado": true, "nota": "Citou 10060, tipo RW U16 e os valores 1 e 2."}
}
```

Aplique e regere as tabelas:

```bash
python evals/avaliar.py            # transporta os vereditos para os JSONs
python evals/avaliar.py --status   # mostra o que ainda está null
python evals/comparativo.py
```

**Não há LLM-as-judge.** O veredito é texto escrito à mão; `avaliar.py` só o
transporta. O campo `revisor` do arquivo precisa ser trocado pelo nome e RM de
quem assinar a revisão antes da entrega.

## 9. Assinar os commits

Os commits da branch estão com autoria correta mas **sem assinatura** — foram
criados num container remoto, sem a chave SSH. Na sua máquina, com a chave no
`ssh-agent`:

```bash
git rebase --exec 'git commit --amend --no-edit -S' 11e9be5
git push --force-with-lease origin sprint-03
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
| `404 ... model_not_found` | nome de modelo descontinuado pelo provedor | seção 6.1 |
| `UnicodeEncodeError: 'charmap' codec can't encode` | console do Windows em cp1252 | rode com `PYTHONIOENCODING=utf-8` |
