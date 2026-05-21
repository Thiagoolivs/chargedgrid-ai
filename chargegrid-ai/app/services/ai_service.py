import os
from pathlib import Path

from dotenv import load_dotenv
from groq import Groq

BASE_DIR = Path(__file__).resolve().parents[1]
SYSTEM_PROMPT_PATH = BASE_DIR / "prompts" / "system_prompt.txt"

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))


def _load_system_prompt():
    return SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")


def ask_ai(message, context):
    system_prompt = _load_system_prompt()

    if not context:
        return "Essa informacao nao esta documentada."

    completion = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": f"""INSTRUCOES CRITICAS:
1. VOCE DEVE responder APENAS com base no CONTEXTO fornecido abaixo
2. Se a informacao NAO estiver NO CONTEXTO, voce DEVE dizer: \"Essa informacao nao esta documentada\"
3. NUNCA use conhecimento fora do contexto fornecido
4. Cite sempre os numeros de registro Modbus exactos quando aparecerem no contexto
5. Se nao conseguir responder com o contexto, PARE e indique claramente

CONTEXTO OFICIAL (fonte unica de verdade):
═══════════════════════════════════════════════════════════════════
{context}
═══════════════════════════════════════════════════════════════════

PERGUNTA DO USUARIO:
{message}

RESPONDA AGORA:""",
            },
        ],
        temperature=0.05,
        max_tokens=1200,
    )

    return completion.choices[0].message.content