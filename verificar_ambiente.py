"""Diagnostico de ambiente local. Rode antes da bateria.

    python verificar_ambiente.py

Diz exatamente o que esta pronto, o que falta e o que ja da para rodar mesmo
com o que falta. Nao imprime nenhuma chave - so informa se ela existe.
"""

import importlib
import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
OK, FALTA, AVISO = "  [OK]   ", "  [FALTA]", "  [AVISO]"

# grupo: "grafo" e o minimo para o grafo rodar, "rag" so importa para
# retrieval, "api" so para subir o servidor. Um pacote de RAG faltando nao
# impede validar memoria e guardrails.
PACOTES = [
    ("langgraph", "framework de agentes", "grafo"),
    ("langchain_core", "base do LangChain", "grafo"),
    ("dotenv", "leitura do .env", "grafo"),
    ("sqlite3", "persistencia de conversas (Sprint 2)", "grafo"),
    ("langchain_groq", "modelo 1 (Groq)", "llm"),
    ("langchain_google_genai", "modelo 2 (Gemini) - opcional", "opcional"),
    ("langchain_community", "FAISS vectorstore", "rag"),
    ("langchain_huggingface", "embeddings", "rag"),
    ("faiss", "indice vetorial", "rag"),
    ("sentence_transformers", "modelo de embedding", "rag"),
    ("fastapi", "API", "api"),
]


def main():
    problemas = []
    print("=" * 66)
    print("DIAGNOSTICO DE AMBIENTE - ChargeGrid AI Sprint 03")
    print("=" * 66)

    # --- Python ---
    print("\nPython")
    versao = sys.version_info
    if versao >= (3, 10):
        print(f"{OK} {versao.major}.{versao.minor}.{versao.micro}")
    else:
        print(f"{FALTA} {versao.major}.{versao.minor} - use 3.10 ou superior")
        problemas.append("python")

    # --- pacotes ---
    print("\nPacotes")
    faltando = set()
    for modulo, papel, grupo in PACOTES:
        try:
            importlib.import_module(modulo)
            print(f"{OK} {modulo:<26} {papel}")
        except ImportError:
            print(f"{AVISO if grupo == 'opcional' else FALTA} {modulo:<26} {papel}")
            if grupo != "opcional":
                faltando.add(grupo)
    if faltando:
        problemas.extend(faltando)
        print("\n       -> pip install -r requirements.txt")

    # --- chaves ---
    print("\nChaves de API (valores nunca sao impressos)")
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

    groq = bool(os.getenv("GROQ_API_KEY"))
    google = bool(os.getenv("GOOGLE_API_KEY"))
    print(f"{OK if groq else FALTA} GROQ_API_KEY{'   definida' if groq else '   ausente'}")
    print(f"{OK if google else AVISO} GOOGLE_API_KEY{' definida' if google else ' ausente (opcional)'}")
    if not groq:
        problemas.append("groq")
        print("\n       -> copie .env.example para .env e preencha GROQ_API_KEY")

    if not (BASE_DIR / ".env").exists():
        print(f"{AVISO} arquivo .env nao encontrado em {BASE_DIR}")

    # --- base de conhecimento ---
    print("\nBase de conhecimento (RAG)")
    docs = BASE_DIR / "app" / "rag" / "docs"
    store = BASE_DIR / "app" / "rag" / "vector_store"

    txts = sorted(docs.glob("*.txt")) if docs.exists() else []
    if txts:
        print(f"{OK} {len(txts)} documentos em app/rag/docs/")
    else:
        print(f"{FALTA} nenhum .txt em app/rag/docs/")
        problemas.append("docs")

    if store.exists() and any(store.iterdir()):
        print(f"{OK} indice FAISS presente")
    else:
        print(f"{FALTA} indice FAISS ausente")
        if txts:
            print("       -> python create_vector_store.py")
        problemas.append("indice")

    # --- veredito ---
    print("\n" + "=" * 66)
    print("O QUE DA PARA RODAR AGORA")
    print("=" * 66)

    pode_offline = not {"grafo", "python"} & set(problemas)
    pode_llm = pode_offline and not {"llm", "groq"} & set(problemas)
    pode_rag = pode_llm and not {"rag", "docs", "indice"} & set(problemas)
    pode_api = pode_llm and "api" not in problemas

    linha = lambda ok, cmd, nota: print(f"{OK if ok else FALTA} {cmd}\n{' ' * 11}{nota}")

    linha(pode_offline, "python evals/smoke_offline.py",
          "28 verificacoes de memoria, roteamento e guardrails. Sem chave.")
    linha(pode_llm, "python evals/demo_memoria.py",
          "Transcript de 3 turnos (requisito 3.2). So precisa da GROQ_API_KEY.")
    linha(pode_llm, "python evals/run.py --model groq/llama-3.3-70b-versatile",
          "Bateria no agente. Sem indice, os casos funcionais rodam sem contexto.")
    linha(pode_rag, "python evals/run_legacy.py",
          "Baseline Sprint 2 (memoria manual). EXIGE o indice FAISS.")
    linha(pode_offline, "python evals/comparativo.py",
          "Tabela antes x depois, depois de preencher 'adequado' nos JSONs.")
    linha(pode_api, "uvicorn app.main:app --reload",
          "API + interface do Volt em http://localhost:8000/")

    if not problemas:
        print("\nAmbiente completo. Pode rodar a bateria inteira.")
        return 0

    print(f"\nPendencias: {', '.join(sorted(set(problemas)))}")
    if "docs" in problemas:
        print(
            "\nNOTA: sem app/rag/docs/ voce ainda fecha o bloco A (memoria) e boa\n"
            "parte do C (guardrails). O que fica de fora e o baseline e os casos\n"
            "funcionais com contexto real."
        )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
