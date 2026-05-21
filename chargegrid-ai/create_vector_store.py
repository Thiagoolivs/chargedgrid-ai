from pathlib import Path
from app.services.embedding_service import create_embeddings

if __name__ == "__main__":
    print("Iniciando criacao de embeddings...")
    create_embeddings()
    print("Pronto! Execute: uvicorn app.main:app --reload")