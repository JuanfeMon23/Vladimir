"""Constructor (SOLO desarrollo) de los PDFs de los documentos a firmar.

No se usa en ejecucion ni agrega dependencias al proyecto: reportlab se
instala efimero con uv. Desde `backend/`:

    uv run --no-project --with reportlab python app/core/db/seeds/demo/build_consent_pdfs.py

Lee `consent_texts.py` (fuente unica), escribe `consent_files/*.pdf` y
`consent_files/manifest.json` (nombre, SHA-256 del PDF y del texto fuente,
paginas). El PDF es reproducible (`invariant`): el mismo texto da los mismos
bytes. Los PDFs y el manifest se versionan en el repo.
"""

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas as pdf_canvas
from reportlab.platypus import (
    KeepTogether,
    ListFlowable,
    ListItem,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

HERE = Path(__file__).resolve().parent
OUT_DIR = HERE / "consent_files"
MANIFEST = OUT_DIR / "manifest.json"

INK = colors.HexColor("#1f2933")
ACCENT = colors.HexColor("#1f4e79")
MUTED = colors.HexColor("#616e7c")

BODY = ParagraphStyle(
    "body", fontName="Helvetica", fontSize=10.5, leading=15, textColor=INK,
    alignment=TA_JUSTIFY, spaceAfter=6,
)  # fmt: skip
TITLE = ParagraphStyle(
    "title", parent=BODY, fontName="Helvetica-Bold", fontSize=17, leading=21,
    textColor=ACCENT, alignment=0, spaceAfter=10,
)  # fmt: skip
HEADING = ParagraphStyle(
    "heading", parent=BODY, fontName="Helvetica-Bold", fontSize=11.5, leading=15,
    textColor=ACCENT, alignment=0, spaceBefore=10, spaceAfter=4, keepWithNext=1,
)  # fmt: skip
LABEL = ParagraphStyle("label", parent=BODY, alignment=0, spaceAfter=0)
NOTE = ParagraphStyle(
    "note", parent=BODY, fontName="Helvetica-Oblique", fontSize=9, textColor=MUTED,
    alignment=0, spaceBefore=14,
)  # fmt: skip


def load_texts():
    """Carga `consent_texts.py` por ruta (solo biblioteca estandar)."""
    path = HERE / "consent_texts.py"
    spec = importlib.util.spec_from_file_location("consent_texts", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules["consent_texts"] = module  # NamedTuple/dataclass lo necesitan
    spec.loader.exec_module(module)
    return module


def numbered_canvas(code: str, version: int, title: str):
    """Canvas con encabezado y pie "CODIGO · Version N · pagina X de Y"."""

    class NumberedCanvas(pdf_canvas.Canvas):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._saved: list[dict] = []

        def showPage(self):
            self._saved.append(dict(self.__dict__))
            self._startPage()

        def save(self):
            total = len(self._saved)
            for state in self._saved:
                self.__dict__.update(state)
                self._decorate(total)
                super().showPage()
            super().save()

        def _decorate(self, total: int) -> None:
            width, height = A4
            self.setStrokeColor(ACCENT)
            self.setLineWidth(0.8)
            self.setFillColor(MUTED)
            self.setFont("Helvetica", 8.5)
            self.drawString(2 * cm, height - 1.3 * cm, title)
            self.line(2 * cm, height - 1.5 * cm, width - 2 * cm, height - 1.5 * cm)
            self.line(2 * cm, 1.6 * cm, width - 2 * cm, 1.6 * cm)
            self.drawRightString(
                width - 2 * cm,
                1.1 * cm,
                f"{code} · Versión {version} · página {self._pageNumber} de {total}",
            )

    return NumberedCanvas


def flowables(texts, doc) -> list:
    story: list = [Paragraph(doc.title, TITLE)]
    for block in doc.blocks:
        match block:
            case texts.Heading(text):
                story.append(Paragraph(text, HEADING))
            case texts.Paragraph(text):
                story.append(Paragraph(text, BODY))
            case texts.Bullets(items):
                story.append(
                    ListFlowable(
                        [ListItem(Paragraph(i, BODY), leftIndent=14) for i in items],
                        bulletType="bullet",
                        start="•",
                        leftIndent=14,
                        bulletFontSize=9,
                    )
                )
            case texts.Fields(labels):
                rows = [[Paragraph(f"{label}:", LABEL), ""] for label in labels]
                table = Table(rows, colWidths=[7.2 * cm, 9.2 * cm], hAlign="LEFT")
                table.setStyle(
                    TableStyle(
                        [
                            ("VALIGN", (0, 0), (-1, -1), "BOTTOM"),
                            ("LINEBELOW", (1, 0), (1, -1), 0.6, MUTED),
                            ("LEFTPADDING", (0, 0), (-1, -1), 0),
                            ("TOPPADDING", (0, 0), (-1, -1), 11),
                            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                        ]
                    )
                )
                story.append(table)
                story.append(Spacer(1, 6))
            case texts.Note(text):
                story.append(Paragraph(text, NOTE))
    # La firma no se parte entre paginas: titulo + renglones juntos.
    return keep_headings_with_fields(texts, story)


def keep_headings_with_fields(texts, story: list) -> list:
    """Une cada encabezado de firma con los renglones que le siguen."""
    result: list = []
    index = 0
    while index < len(story):
        item = story[index]
        nxt = story[index + 1] if index + 1 < len(story) else None
        is_heading = isinstance(item, Paragraph) and item.style is HEADING
        if is_heading and isinstance(nxt, Table):
            result.append(KeepTogether([item, nxt, story[index + 2]]))
            index += 3
        else:
            result.append(item)
            index += 1
    return result


def build_pdf(texts, doc, path: Path) -> None:
    template = SimpleDocTemplate(
        str(path),
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2.2 * cm,
        bottomMargin=2.2 * cm,
        title=doc.title,
        author="Vladimir",
        subject=f"{doc.code} - Versión {doc.version}",
        invariant=True,
    )
    template.build(
        flowables(texts, doc),
        canvasmaker=numbered_canvas(doc.code, doc.version, doc.title),
    )


def main() -> None:
    texts = load_texts()
    OUT_DIR.mkdir(exist_ok=True)
    entries = []
    for doc in texts.DOCUMENTS:
        path = OUT_DIR / doc.pdf_name
        build_pdf(texts, doc, path)
        data = path.read_bytes()
        entries.append(
            {
                "code": doc.code,
                "name": doc.name,
                "version": doc.version,
                "file": doc.pdf_name,
                "pdf_sha256": hashlib.sha256(data).hexdigest(),
                "pdf_size_bytes": len(data),
                "source_sha256": texts.source_sha256(doc),
            }
        )
        print(f"{doc.pdf_name}: {len(data)} bytes")
    MANIFEST.write_text(
        json.dumps({"files": entries}, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"manifest: {MANIFEST}")


if __name__ == "__main__":
    main()
