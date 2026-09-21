# evals — bateria de avaliação da Sprint 03

17 casos em `cases.json`, cobrindo os três tipos exigidos pelo item 8 da
Sprint 03: funcional (F01–F06), memória (M01–M03) e segurança (S01–S07, E01).

**Rastreabilidade com a Sprint 1.** A seção 6 exige rodar na nova arquitetura
*o mesmo conjunto de testes utilizado anteriormente*. Os seis casos funcionais
são as seis perguntas de `test_cases.txt`, copiadas **literalmente**; o campo
`origem` de cada caso aponta o teste de origem:

| Caso | `origem` | Pergunta |
|---|---|---|
| F01 | `sprint1_teste_1` | iniciar carregamento no GW7K via SolarGo |
| F02 | `sprint1_teste_2` | registro Modbus de liga/desliga e valores |
| F03 | `sprint1_teste_3` | vincular cartão RFID e limite de cartões |
| F04 | `sprint1_teste_4` | Dynamic Load Management no GW11K |
| F05 | `sprint1_teste_5` | LED vermelho fixo, primeira verificação |
| F06 | `sprint1_teste_6` | temperatura máxima e proteção IP do GW22K |

> **Correção de gabarito no F06.** O `esperado` vindo da Sprint 1 citava IP54,
> IP20 e IK10 — valores que **não existem** em
> `app/rag/docs/especificacoes_tecnicas.txt`, onde o corpus documenta IP66 no
> carregador, IP55 no plugue e faixa de −30 a +50 °C. Julgar contra o gabarito
> antigo reprovaria uma resposta corretamente ancorada na documentação. O
> critério foi corrigido; `esperado_original_sprint1` e `motivo_correcao` ficam
> gravados ao lado no `cases.json`. **A pergunta continua literal.**

## Ordem de execução

```bash
# 0. pré-requisitos: .env preenchido e índice FAISS gerado
python create_vector_store.py

# 1. validação estrutural — não usa chave de API nem índice
python evals/smoke_offline.py

# 1b. demonstração de memória (requisito 3.2) — só precisa da chave, não do índice
python evals/demo_memoria.py --model google/gemini-3.6-flash

# 2. baseline "antes" — Sprint 2: ask_ai com history + SQLite
#    --model substitui o modelo descontinuado SEM editar ai_service.py
python evals/run_legacy.py --model openai/gpt-oss-20b

# 3. agente novo, nos dois modelos do comparativo
python evals/run.py --list-google-models     # confirma o nome do Gemini
python evals/run.py --model google/gemini-3.6-flash --sleep 4
python evals/run.py --model groq/qwen/qwen3.8-27b

# 4. avaliação qualitativa + tabela antes x depois
python evals/avaliar.py
python evals/comparativo.py
```

## Avaliação qualitativa

Os harnesses gravam `adequado: null` em cada resultado. O julgamento é
**humano e vive fora do código**, em `evals/avaliacao.json`: um arquivo de
dados com o critério por tipo de caso, o veredito de cada caso por rodada e uma
nota justificando. `evals/avaliar.py` apenas transporta esse arquivo para
dentro dos resultados.

**Não há LLM-as-judge:** seria mais um ponto de falha e a rubrica não pede.

```bash
python evals/avaliar.py            # aplica os vereditos
python evals/avaliar.py --status   # mostra o que ainda está null
python evals/avaliar.py --dry-run  # simula, sem gravar
```

O campo `revisor` do arquivo precisa ser trocado pelo nome e RM de quem assinar
a revisão. Enquanto `adequado` estiver `null`, o comparativo mostra `pendente`
em vez de uma taxa — nenhum número é inventado.

## Arquivos

| Arquivo | Papel |
|---|---|
| `cases.json` | os 17 casos, com turnos e resultado esperado |
| `smoke_offline.py` | valida memória, roteamento e guardrails sem chave de API |
| `demo_memoria.py` | transcript de 3 turnos para o relatório (requisito 3.2) |
| `fake_model.py` | chat model falso que grava o que recebeu (usado pelo smoke) |
| `run.py` | roda o agente novo, um JSON por modelo |
| `run_legacy.py` | roda o baseline da Sprint 2 (memória manual + SQLite) |
| `avaliacao.json` | julgamento humano: critério por tipo + veredito por caso |
| `avaliar.py` | aplica `avaliacao.json` aos resultados; reexecutável |
| `comparativo.py` | gera `results/comparativo.md`; reexecutável |
| `common.py` | carregamento de casos, extração de tokens, retry de 429 |

## Notas de execução

- **Memória:** cada caso usa um `thread_id` novo (uuid4) e todos os turnos do
  caso compartilham esse mesmo id. É isso que exercita o checkpointer.
- **Gemini free tier** limita requisições por minuto. `run.py` espaça as
  chamadas (4 s por padrão no provedor `google`) e repete com backoff
  exponencial em 429. Ajuste com `--sleep`.
- **Tokens são medidos dos dois lados.** No agente vêm de `usage_metadata`;
  no baseline, `run_legacy.py` intercepta o cliente Groq de `ai_service` e lê o
  `usage` da resposta crua. O arquivo do baseline continua intacto — confira
  com `git diff app/services/`.
- **Cota da Groq:** 200.000 tokens por dia, **por modelo**. Uma bateria
  consome de 68.000 a 96.000, então duas rodadas no mesmo modelo Groq não cabem
  no mesmo dia.
- **Gemini 3.x:** `max_output_tokens` é orçamento único, dividido entre
  raciocínio e texto visível. Sem `MODEL_THINKING=0`, o roteador devolve
  resposta vazia e a geração sai truncada.
- **O baseline tem memória.** A Sprint 2 usa `history[-10:]` a partir do
  SQLite. O comparativo é memória manual × memória de framework — não assuma
  que M01–M03 falham no "antes".
- **Experimento de parâmetro:**
  `python evals/run.py --model google/gemini-3.6-flash --temperature 0.7`
  grava um JSON separado, sem sobrescrever a rodada de 0.1.
- **`results/arquivo/`** guarda rodadas superadas, fora do alcance do
  `comparativo.py` — ele só lê os JSONs da raiz de `results/`.
