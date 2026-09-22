# Base de conhecimento do RAG — proveniência

Os 12 `.txt` deste diretório são a **fonte** do RAG. Não são gerados: o que é
gerado é `app/rag/vector_store/`, o índice FAISS que
`python create_vector_store.py` produz a partir daqui (59 chunks).

## De onde vêm

Derivados dos PDFs técnicos fornecidos pela **GoodWe** para o EV Challenge —
documentação dos carregadores da linha HCA-G2 (GW7K, GW11K e GW22K), com
referência ao Manual Oficial GoodWe HCA-G2 V1.5 (2025-11-11).

O conteúdo foi reorganizado por assunto em texto simples para alimentar o
retrieval. Os PDFs originais **não são redistribuídos** aqui: ficam em
`app/rag/source_pdfs/`, que está no `.gitignore`.

## Por que estão versionados

Sem eles, quem clonar o repositório não consegue rodar `create_vector_store.py`
e, por consequência, não roda os seis casos funcionais (F01–F06) nem a bateria
do baseline — ou seja, não reproduz os números dos relatórios. São 60 KB de
texto; a reprodutibilidade da entrega vale mais que o espaço.

## Os nomes importam

`app/services/rag_service.py` mapeia palavra-chave para arquivo
(`KEYWORD_SOURCE_HINTS`). **Renomear qualquer um destes arquivos quebra o
direcionamento do retrieval.**

| Arquivo | Assunto |
|---|---|
| `autenticacao.txt` | RFID, AUTO Start, acesso por aplicativo |
| `carregamento.txt` | Modos de carga, iniciar e parar, agendamento |
| `comunicacao.txt` | Modbus TCP e RS485, topologias |
| `conectividade.txt` | SolarGo, SEMS Portal, Bluetooth, Wi-Fi |
| `eficiencia_energetica.txt` | Dynamic Load Control, prioridade PV |
| `especificacoes_tecnicas.txt` | Potência, temperatura, grau de proteção IP |
| `faturamento.txt` | Medição e custeio por sessão |
| `manutencao.txt` | Inspeção periódica e cuidados |
| `modbus_reference.txt` | Tabela de registros Modbus |
| `monitoramento.txt` | Telemetria e status de operação |
| `seguranca.txt` | RCBO, aterramento, proteções |
| `troubleshooting_guide.txt` | Diagnóstico por LED e códigos de falha |

## Como regerar o índice

```bash
python create_vector_store.py
```

Saída esperada: `Embeddings criados com sucesso: 59 chunks processados`.
