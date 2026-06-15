from fastapi import APIRouter, HTTPException

from app import database
from app.models.schemas import ConversationCreate

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.get("")
def list_conversations():
    return database.list_conversations()


@router.post("", status_code=201)
def create_conversation(body: ConversationCreate):
    return database.create_conversation(body.title)


@router.get("/{conversation_id}/messages")
def get_messages(conversation_id: str):
    if not database.conversation_exists(conversation_id):
        raise HTTPException(status_code=404, detail="Conversa não encontrada")
    return database.get_messages(conversation_id)


@router.delete("/{conversation_id}")
def delete_conversation(conversation_id: str):
    if not database.conversation_exists(conversation_id):
        raise HTTPException(status_code=404, detail="Conversa não encontrada")
    database.delete_conversation(conversation_id)
    return {"ok": True}
