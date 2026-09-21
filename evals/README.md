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

## Ordem de execução

```bash
# 0. pré-requisitos: .env preenchido e índice FAISS gerado
python create_vector_store.py

# 1. validação estrutural — não usa chave de API nem índice
python evals/smoke_offline.py

# 1b. demonstração de memória (requisito 3.2) — só precisa da chave, não do índice
python evals/demo_memoria.py

# 2. baseline "antes" — Sprint 2: ask_ai com history + SQLite
python evals/run_legacy.py

# 3. agente novo, nos dois modelos do comparativo
python evals/run.py --list-google-models     # confirma o nome do Gemini
python evals/run.py

# 4. tabela antes x depois
python evals/comparativo.py
```

## Avaliação qualitativa

Os harnesses gravam `adequado: null` em cada resultado. Esse campo é
preenchido **manualmente** (`true`/`false`) antes de rodar `comparativo.py`.
Não há LLM-as-judge: seria mais um ponto de falha e a rubrica não pede.

Enquanto `adequado` estiver `null`, o comparativo mostra `pendente` em vez de
uma taxa — nenhum número é inventado.

## Arquivos

| Arquivo | Papel |
|---|---|
| `cases.json` | os 14 casos, com turnos e resultado esperado |
| `smoke_offline.py` | valida memória, roteamento e guardrails sem chave de API |
| `demo_memoria.py` | transcript de 3 turnos para o relatório (requisito 3.2) |
| `fake_model.py` | chat model falso que grava o que recebeu (usado pelo smoke) |
| `run.py` | roda o agente novo, um JSON por modelo |
| `run_legacy.py` | roda o baseline da Sprint 2 (memória manual + SQLite) |
| `comparativo.py` | gera `results/comparativo.md`; reexecutável |
| `common.py` | carregamento de casos, extração de tokens, retry de 429 |

## Notas de execução

- **Memória:** cada caso usa um `thread_id` novo (uuid4) e todos os turnos do
  caso compartilham esse mesmo id. É isso que exercita o checkpointer.
- **Gemini free tier** limita requisições por minuto. `run.py` espaça as
  chamadas (4 s por padrão no provedor `google`) e repete com backoff
  exponencial em 429. Ajuste com `--sleep`.
- **Tokens** não são medidos no baseline: `ask_ai` devolve só a string da
  resposta, e expor o objeto de usage exigiria alterar `ai_service.py`, que
  precisa ficar intacto para o comparativo valer.
- **O baseline tem memória.** A Sprint 2 usa `history[-10:]` a partir do
  SQLite. O comparativo é memória manual × memória de framework — não assuma
  que M01–M03 falham no "antes".
- **Experimento de parâmetro:** `python evals/run.py --model <vencedor> --temperature 0.5`
  grava um JSON separado, sem sobrescrever a rodada de 0.1.
