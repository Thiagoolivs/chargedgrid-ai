from fastapi import APIRouter

from app.models.schemas import ChatRequest
from app.services.ai_service import ask_ai
from app.services.rag_service import retrieve_context

router = APIRouter()


@router.post("/chat")
def chat(request: ChatRequest):
    retrieval = retrieve_context(request.message)
    response = ask_ai(
        message=request.message,
        context=retrieval["context"],
    )

    return {
        "response": response,
        "sources": retrieval["sources"],
    }