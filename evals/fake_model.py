"""Chat model falso para validar o grafo sem chave de API.

Serve a dois propositos:

1. Provar que a memoria e real. O modelo falso registra a lista de mensagens
   recebida em cada chamada, entao da para afirmar - com evidencia, nao com
   confianca - que no terceiro turno o conteudo dos dois primeiros chegou ao
   modelo.
2. Exercitar guardrails e roteamento de ponta a ponta em ambiente sem rede.

E uma classe simples de proposito: os nos do grafo so chamam `.invoke(mensagens)`,
entao nao ha motivo para herdar de `BaseChatModel` e ficar preso ao modelo de
dados (pydantic v1 ou v2) da versao do langchain-core instalada.
"""

from langchain_core.messages import AIMessage


class RecordingFakeChatModel:
    """Modelo falso que grava o que recebeu e responde via callable."""

    def __init__(self, responder=None, name="fake"):
        self.responder = responder
        self.name = name
        self.calls = []

    def invoke(self, messages, **kwargs):
        self.calls.append(list(messages))

        text = self.responder(messages) if self.responder else "ok"

        message = AIMessage(content=text)

        # usage_metadata so existe em versoes recentes do langchain-core; o
        # harness ja trata ausencia, entao aqui a falta tambem e tolerada.
        try:
            message.usage_metadata = {
                "input_tokens": sum(
                    len(str(m.content).split()) for m in messages
                ),
                "output_tokens": len(text.split()),
                "total_tokens": 0,
            }
        except Exception:
            pass

        return message

    def last_conversation_text(self):
        """Texto corrido da ultima chamada. Usado nas asserts dos testes."""
        if not self.calls:
            return ""

        return "\n".join(str(m.content) for m in self.calls[-1])
