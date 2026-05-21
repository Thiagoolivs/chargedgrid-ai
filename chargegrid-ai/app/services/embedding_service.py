from pathlib import Path

from langchain_community.document_loaders import TextLoader
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

BASE_DIR = Path(__file__).resolve().parents[1]
DOCS_PATH = BASE_DIR / "rag" / "docs"
VECTOR_STORE_PATH = BASE_DIR / "rag" / "vector_store"
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


def _load_documents():
    documents = []

    for file_path in sorted(DOCS_PATH.iterdir()):
        if not file_path.is_file():
            continue

        if file_path.suffix.lower() != ".txt":
            continue

        loader = TextLoader(str(file_path), encoding="utf-8")
        documents.extend(loader.load())

    return documents


def create_embeddings():
    documents = _load_documents()

    if not documents:
        raise RuntimeError(f"Nenhum documento encontrado em {DOCS_PATH}")

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=900,
        chunk_overlap=180,
        separators=[
            "\n## ",
            "\n### ",
            "\n\n",
            "\n",
            ". ",
            " ",
        ],
    )

    chunks = splitter.split_documents(documents)

    embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
    vectorstore = FAISS.from_documents(chunks, embeddings)
    vectorstore.save_local(str(VECTOR_STORE_PATH))

    print(f"Embeddings criados com sucesso: {len(chunks)} chunks processados")