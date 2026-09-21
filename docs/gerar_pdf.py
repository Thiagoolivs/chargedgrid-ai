"""Converte docs/relatorio_evolucao.md em PDF, respeitando o limite de 5 paginas."""

import html
import re
import sys
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable,
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

BASE = Path(sys.argv[1] if len(sys.argv) > 1 else "docs/relatorio_evolucao.md")
OUT = Path(sys.argv[2] if len(sys.argv) > 2 else "docs/relatorio_evolucao.pdf")

ACCENT = colors.HexColor("#0B5C3B")
GREY = colors.HexColor("#5A5A5A")
RULE = colors.HexColor("#D4D4D4")
ZEBRA = colors.HexColor("#F4F6F5")

styles = getSampleStyleSheet()

S_TITLE = ParagraphStyle(
    "t", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=17,
    leading=20, textColor=ACCENT, spaceAfter=2, alignment=0,
)
S_SUB = ParagraphStyle(
    "sub", parent=styles["Normal"], fontName="Helvetica", fontSize=8.4,
    leading=11, textColor=GREY, spaceAfter=5,
)
S_H2 = ParagraphStyle(
    "h2", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=11.8,
    leading=14, textColor=ACCENT, spaceBefore=8, spaceAfter=3,
)
S_H3 = ParagraphStyle(
    "h3", parent=styles["Heading3"], fontName="Helvetica-Bold", fontSize=9.6,
    leading=11.5, textColor=colors.HexColor("#222222"), spaceBefore=5,
    spaceAfter=2,
)
S_BODY = ParagraphStyle(
    "b", parent=styles["Normal"], fontName="Helvetica", fontSize=8.9,
    leading=11.2, alignment=TA_JUSTIFY, spaceAfter=3.5,
)
S_QUOTE = ParagraphStyle(
    "q", parent=S_BODY, fontSize=8.1, leading=10.2, textColor=GREY,
    leftIndent=6, borderPadding=0, spaceAfter=4,
)
S_CODE = ParagraphStyle(
    "c", parent=styles["Normal"], fontName="Courier", fontSize=6.8,
    leading=8.1, textColor=colors.HexColor("#1A3A2A"), spaceAfter=4,
)
S_TH = ParagraphStyle(
    "th", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=7.4,
    leading=9, textColor=colors.white,
)
S_TD = ParagraphStyle(
    "td", parent=styles["Normal"], fontName="Helvetica", fontSize=7.4,
    leading=9,
)


def inline(text):
    """Markdown inline -> markup do reportlab."""
    text = html.escape(text, quote=False)
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"(?<!\*)\*([^*]+?)\*(?!\*)", r"<i>\1</i>", text)
    text = re.sub(
        r"`([^`]+?)`",
        r'<font face="Courier" size="8" color="#1A3A2A">\1</font>',
        text,
    )
    return text


def parse(md):
    """Percorre o markdown e devolve os flowables na ordem."""
    linhas = md.split("\n")
    flow = []
    i = 0
    paragrafo = []
    citacao = []

    def fecha_paragrafo():
        if paragrafo:
            flow.append(Paragraph(inline(" ".join(paragrafo)), S_BODY))
            paragrafo.clear()

    def fecha_citacao():
        if citacao:
            flow.append(Paragraph(inline(" ".join(citacao)), S_QUOTE))
            citacao.clear()

    while i < len(linhas):
        ln = linhas[i]
        strip = ln.strip()

        if strip.startswith("```"):
            fecha_paragrafo()
            fecha_citacao()
            i += 1
            bloco = []
            while i < len(linhas) and not linhas[i].strip().startswith("```"):
                bloco.append(linhas[i])
                i += 1
            texto = "<br/>".join(
                html.escape(l, quote=False).replace(" ", "&nbsp;") for l in bloco
            )
            flow.append(Paragraph(texto, S_CODE))
            i += 1
            continue

        if strip.startswith("|"):
            fecha_paragrafo()
            fecha_citacao()
            linhas_tab = []
            while i < len(linhas) and linhas[i].strip().startswith("|"):
                linhas_tab.append(linhas[i].strip())
                i += 1
            flow.append(monta_tabela(linhas_tab))
            continue

        if not strip:
            fecha_paragrafo()
            fecha_citacao()
            i += 1
            continue

        if strip.startswith("> "):
            fecha_paragrafo()
            citacao.append(strip[2:])
            i += 1
            continue

        if strip.startswith("### "):
            fecha_paragrafo()
            fecha_citacao()
            flow.append(Paragraph(inline(strip[4:]), S_H3))
            i += 1
            continue

        if strip.startswith("## "):
            fecha_paragrafo()
            fecha_citacao()
            flow.append(Paragraph(inline(strip[3:]), S_H2))
            i += 1
            continue

        if strip.startswith("# "):
            fecha_paragrafo()
            fecha_citacao()
            flow.append(Paragraph(inline(strip[2:]), S_TITLE))
            i += 1
            continue

        if strip.startswith("---"):
            fecha_paragrafo()
            fecha_citacao()
            flow.append(Spacer(1, 1.5))
            flow.append(HRFlowable(width="100%", thickness=0.4, color=RULE))
            flow.append(Spacer(1, 1.5))
            i += 1
            continue

        paragrafo.append(strip)
        i += 1

    fecha_paragrafo()
    fecha_citacao()
    return flow


def celulas(linha):
    return [c.strip() for c in linha.strip().strip("|").split("|")]


def monta_tabela(linhas_tab):
    if len(linhas_tab) >= 2 and set(linhas_tab[1].replace("|", "").strip()) <= set("-: "):
        cab = celulas(linhas_tab[0])
        corpo = [celulas(l) for l in linhas_tab[2:]]
    else:
        cab = None
        corpo = [celulas(l) for l in linhas_tab]

    n = max(len(r) for r in ([cab] if cab else []) + corpo)
    dados = []

    if cab:
        dados.append([Paragraph(inline(c), S_TH) for c in cab + [""] * (n - len(cab))])

    for r in corpo:
        dados.append([Paragraph(inline(c), S_TD) for c in r + [""] * (n - len(r))])

    largura_util = A4[0] - 30 * mm

    # Primeira coluna mais larga: ela costuma carregar o rotulo da linha.
    if n == 1:
        larguras = [largura_util]
    else:
        primeira = largura_util * (0.30 if n > 2 else 0.34)
        resto = (largura_util - primeira) / (n - 1)
        larguras = [primeira] + [resto] * (n - 1)

    estilo = [
        ("GRID", (0, 0), (-1, -1), 0.3, RULE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]

    inicio = 0

    if cab:
        estilo.append(("BACKGROUND", (0, 0), (-1, 0), ACCENT))
        inicio = 1

    for idx in range(inicio, len(dados)):
        if (idx - inicio) % 2 == 1:
            estilo.append(("BACKGROUND", (0, idx), (-1, idx), ZEBRA))

    t = Table(dados, colWidths=larguras, repeatRows=1 if cab else 0)
    t.setStyle(TableStyle(estilo))
    return KeepTogether([Spacer(1, 1), t, Spacer(1, 4)])


def rodape(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 6.4)
    canvas.setFillColor(GREY)
    canvas.drawString(
        15 * mm, 10 * mm,
        "ChargeGrid AI - Sprint 03 - EV Challenge GoodWe - Turma 1CCPO",
    )
    canvas.drawRightString(A4[0] - 15 * mm, 10 * mm, f"Pagina {doc.page}")
    canvas.restoreState()


def main():
    md = BASE.read_text(encoding="utf-8")
    doc = SimpleDocTemplate(
        str(OUT),
        pagesize=A4,
        leftMargin=15 * mm,
        rightMargin=15 * mm,
        topMargin=13 * mm,
        bottomMargin=15 * mm,
        title="Relatorio de Evolucao - ChargeGrid AI Sprint 03",
        author="Grupo ChargeGrid AI - Turma 1CCPO",
    )
    doc.build(parse(md), onFirstPage=rodape, onLaterPages=rodape)

    from pypdf import PdfReader

    paginas = len(PdfReader(str(OUT)).pages)
    print(f"{OUT} gerado: {paginas} pagina(s)")
    return 0 if paginas <= 5 else 1


if __name__ == "__main__":
    raise SystemExit(main())
