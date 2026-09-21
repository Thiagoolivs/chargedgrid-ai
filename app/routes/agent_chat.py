"""Endpoint do agente da Sprint 03: POST /agent/chat.

Rota nova, ao lado de /chat. O endpoint antigo nao muda: ele continua sendo o
baseline "antes" do comparativo.

Duas camadas de memoria, com papeis diferentes:

- **Framework (LangGraph).** O `MemorySaver` guarda o estado da conversa em
  memoria do processo, indexado por `thread_id`. E dele que sai o historico
  usado na inferencia - e o requisito 3.2.
- **SQLite (herdado da Sprint 2).** Guarda o transcript de forma duravel, e e
  o que alimenta a listagem de conversas da interface.

O `conversation_id` da Sprint 2 e usado como `thread_id`, entao as duas
camadas falam da mesma conversa. Quando o processo reinicia, o SQLite
sobrevive e o `MemorySaver` nao; nesse caso o transcript e reinjetado no
checkpointer uma unica vez (ver `_rehydrate`). Isso NAO e gerenciamento manual
de historico: nenhuma mensagem e montada a mao para o LLM, o que se faz e
repopular o estado do proprio framework a partir do armazenamento duravel. A
inferencia continua lendo o historico do checkpointer.
"""

import logging
import sys
from pathlib import Path

from fastapi import APIRouter, HTTPException

from app import database
from app.models.schemas import AgentChatRequest

# agent_core vive na raiz do projeto, ao lado de app/.
BASE_DIR = Path(__file__).resolve().parents[2]

if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

logger = logging.getLogger(__name__)
router = APIRouter()


def _rehydrate(graph, conversation_id):
    """Repovoa o checkpointer com o transcript do SQLite, se preciso.

    So age quando o thread esta vazio e o banco tem mensagens - ou seja,
    depois de um restart do processo. Sem essa guarda, cada requisicao
    duplicaria o historico.
    """
    config = {"configurable": {"thread_id": conversation_id}}

    try:
        state = graph.get_state(config)
        if state.values.get("messages"):
            return
    except Exception:
        return

    stored = database.get_messages(conversation_id)

    if not stored:
        return

    restored = [
        ("user" if m["role"] == "user" else "assistant", m["content"])
        for m in stored
        if m.get("content")
    ]

    if restored:
        graph.update_state(config, {"messages": restored})
        logger.info(
            "Conversa %s reidratada com %d mensagens do SQLite",
            conversation_id,
            len(restored),
        )


@router.post("/agent/chat")
def agent_chat(request: AgentChatRequest):
    from agent_core.graph import answer, get_graph

    if not request.message.strip():
        raise HTTPException(status_code=422, detail="message nao pode ser vazio")

    conversation_id = request.conversation_id

    if conversation_id:
        if not database.conversation_exists(conversation_id):
            raise HTTPException(status_code=404, detail="Conversa nao encontrada")
    else:
        titulo = request.message.strip()[:60]
        conversation_id = database.create_conversation(titulo)["id"]

    try:
        graph = get_graph()
        _rehydrate(graph, conversation_id)
        result = answer(conversation_id, request.message, graph=graph)
    except RuntimeError as exc:
        # Chave de API ausente e o caso comum. 503 com o motivo e mais util
        # que um stack trace de 500.
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception:
        logger.exception("Erro ao processar /agent/chat")
        raise HTTPException(status_code=503, detail="Servico temporariamente indisponivel")

    database.add_message(conversation_id, "user", request.message)
    database.add_message(
        conversation_id, "assistant", result["response"], result["sources"]
    )

    return {
        "conversation_id": conversation_id,
        "response": result["response"],
        "route": result["route"],
        "sources": result["sources"],
        "blocked_reason": result["blocked_reason"],
    }
