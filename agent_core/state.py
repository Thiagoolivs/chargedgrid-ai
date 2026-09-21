"""Estado compartilhado entre os nos do grafo.

`MessagesState` ja traz o campo `messages` com o reducer `add_messages`. E ele
que acumula o historico da conversa a cada turno: o agente nao mantem lista de
mensagens propria em lugar nenhum, a memoria vem do framework.
"""

from typing import Optional

from langgraph.graph import MessagesState


class AgentState(MessagesState):
    # Trecho recuperado do RAG nesta rodada. Vazio quando o turno nao precisa
    # de documentacao (pergunta conversacional) ou quando nada foi encontrado.
    context: str

    # Fontes do RAG, no formato devolvido por rag_service.retrieve_context.
    sources: list

    # Preenchido pelo guard_in/guard_out quando a mensagem ou a resposta e
    # barrada. `None` significa caminho livre.
    blocked_reason: Optional[str]

    # Rota escolhida pelo no `router`: tecnica | conversa | fora_escopo.
    # Registrada nos resultados dos experimentos para analise no relatorio.
    route: Optional[str]
