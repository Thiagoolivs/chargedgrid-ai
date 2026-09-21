"""Normalizacao do conteudo de uma mensagem para texto puro.

Existe por causa do comparativo entre provedores. A Groq devolve
`message.content` como `str`; o Gemini 3.x devolve uma LISTA de blocos
(`[{"type": "text", "text": "...", "extras": {...}}]`), porque carrega
assinatura de raciocinio junto. Sem esta normalizacao o mesmo grafo quebra ao
trocar de provedor: `parse_route`, o render do historico e o guardrail de saida
chamam `.strip()`/`.lower()` sobre o conteudo.

A mensagem original NUNCA e reconstruida - so o texto e extraido. Isso preserva
`usage_metadata`, que o harness le para contar tokens, e preserva os blocos de
assinatura que o proprio provedor exige de volta no turno seguinte.
"""


def message_text(message):
    """Devolve o texto de uma mensagem LangChain, seja qual for o provedor."""
    if message is None:
        return ""

    # langchain-core expoe `.text`, que ja concatena os blocos de texto e
    # ignora blocos nao textuais (assinatura, thinking, imagem). Em 1.x e uma
    # propriedade str; em 0.3 era metodo. Os dois casos sao aceitos aqui para
    # que o pacote nao fique preso a uma versao do LangChain.
    text = getattr(message, "text", None)

    if isinstance(text, str):
        if text:
            return text
    elif callable(text):
        try:
            value = text()
        except Exception:
            value = None

        if isinstance(value, str) and value:
            return value

    return content_text(getattr(message, "content", ""))


def content_text(content):
    """Mesma extracao, partindo do valor bruto de `content`."""
    if content is None:
        return ""

    if isinstance(content, str):
        return content

    if isinstance(content, list):
        partes = []

        for bloco in content:
            if isinstance(bloco, str):
                partes.append(bloco)
            elif isinstance(bloco, dict) and isinstance(bloco.get("text"), str):
                partes.append(bloco["text"])

        return "".join(partes)

    return str(content)
