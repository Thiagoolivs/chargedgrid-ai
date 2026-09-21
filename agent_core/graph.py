"""Montagem do grafo LangGraph e ponto de entrada do agente.

    START -> guard_in -+- (bloqueado) ----------------------> refuse -+
                       |                                              |
                       +- (ok) -> router -+- tecnica -> retrieve -+   |
                                          |                       |   |
                                          +- conversa ------------+-> generate -+
                                          |                                     |
                                          +- fora_escopo --------> refuse ------+
                                                                                |
                                                          guard_out <-----------+
                                                              |
                                                             END

Todos os caminhos passam por `guard_out` antes do END: uma saida so, um ponto
so de verificacao de vazamento.

A memoria vem do checkpointer do proprio framework. Cada sessao e um
`thread_id`; o `MessagesState` acumula o historico entre as chamadas. Nao
existe gerenciamento manual de historico em lugar nenhum deste pacote.
"""

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from agent_core.config import build_chat_model, ROUTER_MAX_TOKENS, ROUTER_TEMPERATURE
from agent_core.guardrails import guard_in, guard_out
from agent_core.nodes import (
    ROUTE_CONVERSATION,
    ROUTE_OUT_OF_SCOPE,
    ROUTE_TECHNICAL,
    make_generate_node,
    make_router_node,
    refuse,
)
from agent_core.state import AgentState


def _after_guard_in(state):
    """Aresta condicional: guardrail de entrada bloqueou?"""
    if state.get("blocked_reason"):
        return "refuse"

    return "router"


def _after_router(state):
    """Aresta condicional: a rota classificada define o caminho."""
    route = state.get("route")

    if route == ROUTE_OUT_OF_SCOPE:
        return "refuse"

    if route == ROUTE_CONVERSATION:
        return "generate"

    # tecnica e qualquer valor inesperado caem na busca documental.
    return "retrieve"


def build_graph(chat_model=None, router_model=None, checkpointer=None):
    """Monta e compila o grafo.

    Os modelos sao injetaveis para que o harness rode varios provedores no
    mesmo processo e para que os testes rodem sem chave de API.
    """
    if chat_model is None:
        chat_model = build_chat_model()

    if router_model is None:
        # O roteador usa o mesmo provedor, mas deterministico e curto: ele so
        # devolve um rotulo, nao texto para o usuario.
        router_model = build_chat_model(
            temperature=ROUTER_TEMPERATURE,
            max_tokens=ROUTER_MAX_TOKENS,
        )

    if checkpointer is None:
        checkpointer = MemorySaver()

    builder = StateGraph(AgentState)

    builder.add_node("guard_in", guard_in)
    builder.add_node("router", make_router_node(router_model))
    builder.add_node("retrieve", _retrieve_node)
    builder.add_node("generate", make_generate_node(chat_model))
    builder.add_node("refuse", refuse)
    builder.add_node("guard_out", guard_out)

    builder.add_edge(START, "guard_in")
    builder.add_conditional_edges(
        "guard_in",
        _after_guard_in,
        {"refuse": "refuse", "router": "router"},
    )
    builder.add_conditional_edges(
        "router",
        _after_router,
        {
            "retrieve": "retrieve",
            "generate": "generate",
            "refuse": "refuse",
        },
    )
    builder.add_edge("retrieve", "generate")
    builder.add_edge("generate", "guard_out")
    builder.add_edge("refuse", "guard_out")
    builder.add_edge("guard_out", END)

    return builder.compile(checkpointer=checkpointer)


def _retrieve_node(state):
    # Indirecao para manter o import do rag_service tardio (ver nodes.py).
    from agent_core.nodes import retrieve

    return retrieve(state)


_default_graph = None


def get_graph():
    """Grafo unico do processo.

    Precisa ser singleton: o `MemorySaver` guarda o historico em memoria do
    processo, entao recompilar o grafo a cada requisicao apagaria a memoria de
    todas as sessoes.
    """
    global _default_graph

    if _default_graph is None:
        _default_graph = build_graph()

    return _default_graph


def answer(session_id, message, graph=None):
    """Roda um turno da conversa e devolve a resposta com os metadados.

    `session_id` vira o `thread_id` do checkpointer: e o que separa a memoria
    de um usuario da de outro.
    """
    graph = graph or get_graph()
    config = {"configurable": {"thread_id": str(session_id)}}

    result = graph.invoke({"messages": [("user", message)]}, config)
    last_message = result["messages"][-1]

    return {
        "response": last_message.content,
        "route": result.get("route"),
        "sources": result.get("sources") or [],
        "blocked_reason": result.get("blocked_reason"),
        "message": last_message,
    }
