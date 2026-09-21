"""Nucleo conversacional da Sprint 03.

Construido ao lado de `app/`, nao por cima: `app/services/ai_service.py` segue
intacto como baseline "antes" do comparativo, e `app/services/rag_service.py` e
consumido como esta, sem alteracao.
"""

from agent_core.graph import answer, build_graph, get_graph

__all__ = ["answer", "build_graph", "get_graph"]
