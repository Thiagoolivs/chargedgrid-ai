import logging

from fastapi import APIRouter, HTTPException

from app import database
from app.models.schemas import ChatRequest
from app.services.ai_service import ask_ai
from app.services.rag_service import retrieve_context

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/chat")
async def chat(request: ChatRequest):
    try:
        if request.conversation_id and not database.conversation_exists(request.conversation_id):
            raise HTTPException(status_code=404, detail="Conversa não encontrada")

        history = []
        if request.conversation_id:
            msgs = database.get_messages(request.conversation_id)
            history = [{"role": m["role"], "content": m["content"]} for m in msgs]

        retrieval = retrieve_context(request.message)
        response = await ask_ai(
            message=request.message,
            context=retrieval["context"],
            history=history,
        )

        if request.conversation_id:
            database.add_message(request.conversation_id, "user", request.message)
            database.add_message(
                request.conversation_id, "assistant", response, retrieval["sources"]
            )

        return {"response": response, "sources": retrieval["sources"]}

    except HTTPException:
        raise
    except Exception:
        logger.exception("Erro ao processar /chat")
        raise HTTPException(status_code=503, detail="Serviço temporariamente indisponível")
