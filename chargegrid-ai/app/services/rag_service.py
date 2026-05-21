from pathlib import Path

from langchain_core.documents import Document
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings

BASE_DIR = Path(__file__).resolve().parents[1]
DOCS_PATH = BASE_DIR / "rag" / "docs"
VECTOR_STORE_PATH = BASE_DIR / "rag" / "vector_store"
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
KEYWORD_SOURCE_HINTS = {
    "modbus": "modbus_reference.txt",
    "registro": "modbus_reference.txt",
    "registrador": "modbus_reference.txt",
    "rfid": "autenticacao.txt",
    "cartao": "autenticacao.txt",
    "cartoes": "autenticacao.txt",
    "rcbo": "seguranca.txt",
    "faturamento": "faturamento.txt",
    "fatura": "faturamento.txt",
    "reembolso": "faturamento.txt",
    "medidor": "faturamento.txt",
    "energia": "faturamento.txt",
    "consumo": "faturamento.txt",
    "troubleshooting": "troubleshooting_guide.txt",
    "problema": "troubleshooting_guide.txt",
    "erro": "troubleshooting_guide.txt",
    "falha": "troubleshooting_guide.txt",
    "led": "troubleshooting_guide.txt",
    "temperatura": "especificacoes_tecnicas.txt",
    "especificacao": "especificacoes_tecnicas.txt",
    "dimensao": "especificacoes_tecnicas.txt",
    "carregamento": "carregamento.txt",
    "potencia": "carregamento.txt",
    "modo": "carregamento.txt",
}

CONTENT_HINTS = {
    "liga": "10060",
    "ligar": "10060",
    "iniciar": "10060",
    "dynamic": "10025",
    "dinamico": "10025",
    "disjuntor": "10026",
    "rcbo": "RCBO",
    "rfid": "RFID",
    "cartao": "RFID",
    "vincular": "vincul",
    "vinculado": "vincul",
    "faturamento": "1006",
    "medidor": "1017",
    "consumo": "10061",
    "duracao": "10063",
    "acumulada": "10065",
    "leitura": "1017",
    "mid": "MID",
    "temperatura": "+50",
    "ip": "IP5",
    "aterramento": "aterramento",
    "protecao": "protecao",
    "seguranca": "seguranca",
}

embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)

if not VECTOR_STORE_PATH.exists():
    raise RuntimeError(
        f"Indice vetorial nao encontrado em {VECTOR_STORE_PATH}. "
        "Execute `python create_vector_store.py` antes de iniciar a API."
    )

vectorstore = FAISS.load_local(
    str(VECTOR_STORE_PATH),
    embeddings,
    allow_dangerous_deserialization=True,
)


def _format_source(metadata):
    source = Path(metadata.get("source", "documento")).name
    page = metadata.get("page")

    if page is None:
        return source

    return f"{source} p.{int(page) + 1}"


def _source_name(doc):
    return Path(doc.metadata.get("source", "documento")).name


def _prioritize_docs(question, docs):
    question_lower = question.lower()
    hinted_sources = {
        source
        for keyword, source in KEYWORD_SOURCE_HINTS.items()
        if keyword in question_lower
    }
    content_hints = [
        hint
        for keyword, hint in CONTENT_HINTS.items()
        if keyword in question_lower
    ]

    return sorted(
        enumerate(docs),
        key=lambda doc: (
            _source_name(doc[1]) not in hinted_sources,
            not any(hint.lower() in doc[1].page_content.lower() for hint in content_hints),
            doc[0],
        ),
    )


def _keyword_docs(content_hints):
    found_docs = []

    for file_path in sorted(DOCS_PATH.glob("*.txt")):
        text = file_path.read_text(encoding="utf-8")
        blocks = [block.strip() for block in text.split("\n\n") if block.strip()]
        best_block = None
        best_score = 0

        for block in blocks:
            if block.startswith("#"):
                continue

            block_lower = block.lower()
            score = sum(1 for hint in content_hints if hint.lower() in block_lower)
            if score > best_score:
                best_score = score
                best_block = block

        if best_block:
            found_docs.append(
                Document(
                    page_content=best_block,
                    metadata={"source": str(file_path)},
                )
            )

    return found_docs


def _dedupe_docs(docs):
    seen = set()
    unique_docs = []

    for doc in docs:
        key = (_source_name(doc), doc.page_content[:120])
        if key in seen:
            continue

        seen.add(key)
        unique_docs.append(doc)

    return unique_docs


def retrieve_context(question, k=10, fetch_k=50):
    question_lower = question.lower()
    content_hints = [
        hint
        for keyword, hint in CONTENT_HINTS.items()
        if keyword in question_lower
    ]
    docs = vectorstore.max_marginal_relevance_search(
        question,
        k=fetch_k,
        fetch_k=max(fetch_k, 60),
    )
    docs = _keyword_docs(content_hints) + docs
    docs = _dedupe_docs(docs)
    relevant_docs = [doc for _, doc in _prioritize_docs(question, docs)[:k]]

    if not relevant_docs:
        return {
            "context": "",
            "sources": [],
        }

    context_parts = []
    sources = []

    for index, doc in enumerate(relevant_docs, start=1):
        source = _format_source(doc.metadata)
        sources.append(
            {
                "source": source,
                "rank": index,
            }
        )
        context_parts.append(
            f"[Fonte {index}: {source}]\n"
            f"{doc.page_content.strip()}"
        )

    return {
        "context": "\n\n---\n\n".join(context_parts),
        "sources": sources,
    }


def search_context(question):
    return retrieve_context(question)["context"]