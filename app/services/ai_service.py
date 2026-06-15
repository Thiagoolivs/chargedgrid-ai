import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from groq import AsyncGroq

BASE_DIR = Path(__file__).resolve().parents[1]
SYSTEM_PROMPT_PATH = BASE_DIR / "prompts" / "system_prompt.txt"

load_dotenv()

logger = logging.getLogger(__name__)
client = AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))

_SYSTEM_PROMPT = SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")


async def ask_ai(message: str, context: str, history: list | None = None) -> str:
    if not context:
        return "Essa informacao nao esta documentada."

    messages = [{"role": "system", "content": _SYSTEM_PROMPT}]

    if history:
        messages.extend(history[-10:])

    messages.append({
        "role": "user",
        "content": f"""INSTRUCOES CRITICAS:
1. VOCE DEVE responder APENAS com base no CONTEXTO fornecido abaixo
2. Se a informacao NAO estiver NO CONTEXTO: escreva SOMENTE "Essa informacao nao esta documentada." e ENCERRE a resposta. NAO preencha nenhum outro bloco.
3. NUNCA use conhecimento fora do contexto fornecido
4. Cite sempre os numeros de registro Modbus exatos quando aparecerem no contexto

CONTEXTO OFICIAL (fonte unica de verdade):
═══════════════════════════════════════════════════════════════════
{context}
═══════════════════════════════════════════════════════════════════

PERGUNTA DO USUARIO:
{message}

RESPONDA AGORA:""",
    })

    completion = await client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=messages,
        temperature=0.05,
        max_tokens=1200,
    )

    return completion.choices[0].message.content
