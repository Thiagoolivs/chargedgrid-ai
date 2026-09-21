from typing import Optional

from pydantic import BaseModel


class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None


class ConversationCreate(BaseModel):
    title: str


class AgentChatRequest(BaseModel):
    """Contrato de POST /agent/chat (Sprint 03).

    Reaproveita o `conversation_id` da Sprint 2: ele vira o `thread_id` do
    checkpointer do LangGraph, entao a conversa e a mesma nas duas camadas de
    memoria. Omitir o campo cria uma conversa nova.
    """

    message: str
    conversation_id: Optional[str] = None
