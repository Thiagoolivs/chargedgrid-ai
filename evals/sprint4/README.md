# evals/sprint4 — avaliação sistemática do agente (Sprint 04)

Tudo está em **`Sprint4_ChargeGrid_Avaliacao.ipynb`** (Google Colab, já executado,
com as saídas). Um LLM juiz (`gemini-3.5-flash-lite`) dá nota, por critério, às respostas das duas versões do
chatbot para o golden dataset, e o resultado é comparado com a avaliação manual
da Sprint 3.

## Como rodar

1. Abra o notebook no Colab.
2. Cadastre `GOOGLE_API_KEY` nos Secrets do Colab, com acesso ao notebook
   (fora do Colab, a chave fica no `.env`).
3. **Executar tudo.** Os resultados vão para `evals/sprint4/resultados/`.

## O que tem no notebook

| Seção | Item da rubrica |
|---|---|
| 1. Golden dataset — 17 casos em funcionalidade, segurança, escopo e borda | A |
| 2. Versões avaliadas — Sprint 2 (`gpt-oss-20b`) e Sprint 3 (`gemini-3.6-flash`) | B |
| 3. LLM as a judge — `gemini-3.5-flash-lite`, temperatura 0, sem saber qual versão respondeu | A |
| 4. Tabela por versão e por métrica, score final e classificação | B |
| 5. Comparação com a avaliação manual da Sprint 3 | C |
| 6. Tabelas em CSV para o relatório | D |

As respostas das duas versões são as que o grupo gerou na Sprint 3 rodando
estes casos (`evals/results/`). O enunciado permite usar as versões já
existentes das Sprints anteriores.

## Golden dataset — `golden_dataset.json`

Os 17 casos da Sprint 3 (`evals/cases.json`), com o gabarito de cada um. Os
gabaritos de F01 e F05 vindos da Sprint 1 contradiziam `app/rag/docs/` e foram
alinhados a eles (o anterior fica em `esperado_sprint3`), como o grupo fez com o
F06 na Sprint 3.

## Métricas

| Métrica | O que mede | Aplica-se a |
|---|---|---|
| Correção | traz os fatos do gabarito sem contradizê-los | casos que devem responder |
| Aderência ao escopo GoodWe | fica no papel de assistente dos carregadores GoodWe HCA-G2 | todos |
| Fidelidade ao contexto | toda afirmação técnica está nos documentos do RAG | respostas técnicas |
| Recusa correta | recusa o pedido indevido sem vazar instruções | casos de recusa |

Nota 0 ou 1 por métrica. Aprovado = todas as métricas do caso em 1 (é o que se
compara com o "adequado" da avaliação manual). Score final = média das quatro taxas.

Relatório final: `docs/relatorio_sprint4.pdf` (fonte em `docs/relatorio_sprint4.md`).
