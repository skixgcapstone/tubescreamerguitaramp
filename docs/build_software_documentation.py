from __future__ import annotations

import html
import re
import sys
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    BaseDocTemplate,
    Flowable,
    Frame,
    HRFlowable,
    KeepTogether,
    ListFlowable,
    ListItem,
    LongTable,
    PageBreak,
    PageTemplate,
    Paragraph,
    Preformatted,
    Spacer,
    TableStyle,
)
from reportlab.platypus.tableofcontents import TableOfContents

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs" / "SOFTWARE_DOCUMENTATION_V2.md"
OUTPUT = ROOT / "output" / "pdf" / "Tube_Screamer_Software_Documentation_Rev_2_3.pdf"
PAGE_WIDTH, PAGE_HEIGHT = letter


class SoftwareDocument(BaseDocTemplate):
    def __init__(self, filename: str, **kwargs: object) -> None:
        super().__init__(filename, **kwargs)
        frame = Frame(
            self.leftMargin,
            self.bottomMargin,
            self.width,
            self.height,
            id="content",
        )
        self.addPageTemplates(
            [
                PageTemplate(id="report", frames=[frame], onPage=self._draw_page),
            ]
        )

    def _draw_page(self, canvas: object, doc: object) -> None:
        canvas.saveState()
        canvas.setFillColor(colors.black)
        canvas.setFont("Times-Roman", 8)
        if doc.page > 1:
            header = (
                "Tube Screamer Guitar Amplifier    Sponsor: Dr. Logan Porter    "
                "Rev 2.3    September 8, 2026"
            )
            canvas.drawString(self.leftMargin, PAGE_HEIGHT - 0.43 * inch, header)
            canvas.setStrokeColor(colors.HexColor("#808080"))
            canvas.setLineWidth(0.4)
            canvas.line(
                self.leftMargin,
                PAGE_HEIGHT - 0.49 * inch,
                PAGE_WIDTH - self.rightMargin,
                PAGE_HEIGHT - 0.49 * inch,
            )
        canvas.drawCentredString(PAGE_WIDTH / 2, 0.38 * inch, str(doc.page))
        canvas.restoreState()

    def afterFlowable(self, flowable: Flowable) -> None:
        if not isinstance(flowable, Paragraph):
            return
        level = getattr(flowable, "toc_level", None)
        if level is None:
            return
        text = flowable.getPlainText()
        key = f"heading-{self.seq.nextf('heading')}"
        self.canv.bookmarkPage(key)
        self.canv.addOutlineEntry(text, key, level=level, closed=False)
        self.notify("TOCEntry", (level, text, self.page, key))


class FlowDiagram(Flowable):
    def __init__(self, key: str, width: float) -> None:
        self.key = key
        self.width = width
        self.height = {
            "product-signal-flow": 1.15 * inch,
            "startup-flow": 2.55 * inch,
            "module-architecture": 2.6 * inch,
            "dsp-flow": 1.15 * inch,
            "thread-communication": 2.75 * inch,
            "fault-flow": 2.65 * inch,
        }[key]

    def draw(self) -> None:
        if self.key == "product-signal-flow":
            self._horizontal(
                ["Guitar\nInput", "Preamp /\nBuffer", "Tube\nStages", "Protected\nInterface", "ADC", "Pi 5\nDSP", "DAC", "Audio\nOutput"]
            )
        elif self.key == "dsp-flow":
            self._horizontal(
                ["Input", "5-Band\nEQ", "Chorus", "Delay", "Echo", "Reverb", "POC Digital\nLevel", "Limiter"]
            )
        elif self.key == "startup-flow":
            self._vertical(
                ["Application Start", "Create Touchscreen", "Initialize Controls and DSP", "Muted Idle State", "Open Codec Zero Stream", "Process Live Audio"]
            )
        elif self.key == "fault-flow":
            self._vertical(
                ["Live Audio Running", "Callback Error Detected", "Write Silence", "Latch Error Status", "Close Stream on Main Thread", "Wait for Operator Restart"],
                fault_index=1,
            )
        elif self.key == "module-architecture":
            self._modules()
        else:
            self._sequence()

    def _box(self, x: float, y: float, w: float, h: float, label: str, fill: colors.Color = colors.white) -> None:
        c = self.canv
        c.setFillColor(fill)
        c.setStrokeColor(colors.HexColor("#303030"))
        c.setLineWidth(0.7)
        c.roundRect(x, y, w, h, 5, fill=1, stroke=1)
        c.setFillColor(colors.black)
        c.setFont("Helvetica", 6.7)
        lines = label.split("\n")
        start = y + h / 2 + (len(lines) - 1) * 3.8
        for index, line in enumerate(lines):
            c.drawCentredString(x + w / 2, start - index * 8, line)

    def _arrow(self, x1: float, y1: float, x2: float, y2: float) -> None:
        c = self.canv
        c.setStrokeColor(colors.HexColor("#355E3B"))
        c.setFillColor(colors.HexColor("#355E3B"))
        c.setLineWidth(1.0)
        c.line(x1, y1, x2, y2)
        if abs(x2 - x1) >= abs(y2 - y1):
            direction = 1 if x2 > x1 else -1
            points = [(x2, y2), (x2 - 5 * direction, y2 + 3), (x2 - 5 * direction, y2 - 3)]
        else:
            direction = 1 if y2 > y1 else -1
            points = [(x2, y2), (x2 - 3, y2 - 5 * direction), (x2 + 3, y2 - 5 * direction)]
        path = c.beginPath()
        path.moveTo(*points[0])
        path.lineTo(*points[1])
        path.lineTo(*points[2])
        path.close()
        c.drawPath(path, fill=1, stroke=0)

    def _horizontal(self, labels: list[str]) -> None:
        gap = 7
        w = (self.width - gap * (len(labels) - 1)) / len(labels)
        h = 38
        y = (self.height - h) / 2
        for index, label in enumerate(labels):
            x = index * (w + gap)
            fill = colors.HexColor("#EAF2EA") if "DSP" in label or "Limiter" in label else colors.white
            self._box(x, y, w, h, label, fill)
            if index:
                self._arrow(x - gap + 1, y + h / 2, x - 1, y + h / 2)

    def _vertical(self, labels: list[str], fault_index: int | None = None) -> None:
        w = 2.75 * inch
        h = 27
        x = (self.width - w) / 2
        gap = (self.height - h * len(labels)) / (len(labels) - 1)
        for index, label in enumerate(labels):
            y = self.height - h - index * (h + gap)
            fill = colors.HexColor("#F6E5E5") if index == fault_index else colors.white
            self._box(x, y, w, h, label, fill)
            if index:
                previous_y = self.height - h - (index - 1) * (h + gap)
                self._arrow(x + w / 2, previous_y - 1, x + w / 2, y + h + 1)

    def _modules(self) -> None:
        positions = {
            "Touchscreen UI\nmain.py": (2.25, 2.0),
            "Audio Engine\naudio_engine.py": (2.25, 1.15),
            "Live Input\nDeviceInputSource": (0.0, 0.2),
            "Real-Time DSP\ndsp.py": (2.25, 0.2),
            "Codec Zero\nALSA / PortAudio": (4.5, 0.2),
            "Performance\nMonitor": (4.5, 1.15),
        }
        w, h = 1.45 * inch, 0.48 * inch
        scale = inch
        for label, (x, y) in positions.items():
            self._box(x * scale, y * scale, w, h, label, colors.HexColor("#EAF2EA") if "DSP" in label else colors.white)
        self._arrow(2.25 * scale + w / 2, 2.0 * scale, 2.25 * scale + w / 2, 1.15 * scale + h)
        self._arrow(2.25 * scale, 1.15 * scale + h / 2, 0.0 * scale + w, 0.2 * scale + h / 2)
        self._arrow(2.25 * scale + w / 2, 1.15 * scale, 2.25 * scale + w / 2, 0.2 * scale + h)
        self._arrow(2.25 * scale + w, 1.15 * scale + h / 2, 4.5 * scale, 0.2 * scale + h / 2)
        self._arrow(4.5 * scale + w / 2, 1.15 * scale, 4.5 * scale + w / 2, 0.2 * scale + h)

    def _sequence(self) -> None:
        labels = ["User", "Tkinter", "Audio Callback", "Codec Zero", "Monitor"]
        xs = [self.width * i / (len(labels) - 1) for i in range(len(labels))]
        top = self.height - 30
        for x, label in zip(xs, labels, strict=True):
            self._box(max(0, x - 34), top, 68, 24, label, colors.HexColor("#EAF2EA") if label == "Audio Callback" else colors.white)
            self.canv.setDash(2, 2)
            self.canv.setStrokeColor(colors.HexColor("#808080"))
            self.canv.line(x, top, x, 12)
            self.canv.setDash()
        messages = [
            (0, 1, "Start / controls"),
            (1, 2, "ControlState"),
            (3, 2, "512 input frames"),
            (2, 3, "limited output"),
            (2, 1, "AudioSnapshot"),
            (2, 4, "timing / counters"),
        ]
        y = top - 22
        for source, target, label in messages:
            self._arrow(xs[source], y, xs[target], y)
            self.canv.setFillColor(colors.black)
            self.canv.setFont("Helvetica", 6.5)
            self.canv.drawCentredString((xs[source] + xs[target]) / 2, y + 4, label)
            y -= 22


def styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "body": ParagraphStyle(
            "Body",
            parent=base["BodyText"],
            fontName="Times-Roman",
            fontSize=10.5,
            leading=14.2,
            spaceAfter=7,
            alignment=TA_LEFT,
            firstLineIndent=0.28 * inch,
        ),
        "bullet": ParagraphStyle(
            "Bullet",
            parent=base["BodyText"],
            fontName="Times-Roman",
            fontSize=10.3,
            leading=13.4,
            leftIndent=0,
        ),
        "h1": ParagraphStyle(
            "Section",
            parent=base["Heading1"],
            fontName="Times-Bold",
            fontSize=14,
            leading=17,
            textColor=colors.black,
            alignment=TA_CENTER,
            spaceBefore=10,
            spaceAfter=5,
            keepWithNext=True,
        ),
        "h2": ParagraphStyle(
            "Subsection",
            parent=base["Heading2"],
            fontName="Times-Bold",
            fontSize=12,
            leading=15,
            textColor=colors.black,
            spaceBefore=10,
            spaceAfter=5,
            keepWithNext=True,
        ),
        "h3": ParagraphStyle(
            "Topic",
            parent=base["Heading3"],
            fontName="Times-Bold",
            fontSize=10.8,
            leading=14,
            textColor=colors.black,
            spaceBefore=8,
            spaceAfter=3,
            keepWithNext=True,
        ),
        "caption": ParagraphStyle(
            "Caption",
            parent=base["BodyText"],
            fontName="Times-Italic",
            fontSize=9.5,
            leading=12,
            alignment=TA_CENTER,
            spaceAfter=10,
        ),
        "code": ParagraphStyle(
            "Code",
            parent=base["Code"],
            fontName="Courier",
            fontSize=7.8,
            leading=10,
            leftIndent=0.12 * inch,
            rightIndent=0.12 * inch,
            borderColor=colors.HexColor("#D0D0D0"),
            borderWidth=0.5,
            borderPadding=7,
            backColor=colors.HexColor("#F5F5F5"),
            spaceBefore=4,
            spaceAfter=8,
        ),
        "table": ParagraphStyle(
            "TableText",
            parent=base["BodyText"],
            fontName="Times-Roman",
            fontSize=7.8,
            leading=9.5,
        ),
        "table_header": ParagraphStyle(
            "TableHeader",
            parent=base["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=7.5,
            leading=9,
            textColor=colors.white,
            alignment=TA_CENTER,
        ),
    }


def inline_markup(text: str) -> str:
    escaped = html.escape(text.strip())
    escaped = re.sub(r"`([^`]+)`", r'<font name="Courier">\1</font>', escaped)
    escaped = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", escaped)
    escaped = re.sub(r"\*([^*]+)\*", r"<i>\1</i>", escaped)
    return escaped


def add_heading(story: list[Flowable], text: str, level: int, style_map: dict[str, ParagraphStyle]) -> None:
    paragraph = Paragraph(inline_markup(text), style_map[f"h{level}"])
    paragraph.toc_level = level - 1
    story.append(paragraph)
    if level == 1:
        story.append(HRFlowable(width="100%", thickness=0.6, color=colors.black, spaceAfter=8))


def add_table(story: list[Flowable], rows: list[list[str]], style_map: dict[str, ParagraphStyle], width: float) -> None:
    if not rows:
        return
    count = len(rows[0])
    if count == 5 and rows[0][0].strip() == "Test ID":
        weights = [11, 25, 25, 25, 14]
    else:
        lengths = [max(6, max(len(row[i]) if i < len(row) else 0 for row in rows)) for i in range(count)]
        weights = [min(value, 55) for value in lengths]
    total = sum(weights)
    col_widths = [width * value / total for value in weights]
    data = []
    for row_index, row in enumerate(rows):
        current = []
        for value in row:
            style = style_map["table_header"] if row_index == 0 else style_map["table"]
            current.append(Paragraph(inline_markup(value), style))
        data.append(current)
    table = LongTable(data, colWidths=col_widths, repeatRows=1, hAlign="LEFT")
    commands = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#355E3B")),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#B8B8B8")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
    for row_index in range(1, len(data)):
        if row_index % 2 == 0:
            commands.append(("BACKGROUND", (0, row_index), (-1, row_index), colors.HexColor("#F2F5F2")))
    table.setStyle(TableStyle(commands))
    story.extend([table, Spacer(1, 8)])


def parse_body(lines: list[str], style_map: dict[str, ParagraphStyle], width: float) -> list[Flowable]:
    story: list[Flowable] = []
    index = 0
    while index < len(lines):
        line = lines[index].rstrip()
        if not line:
            index += 1
            continue
        if line.startswith("<!-- pdf-figure:"):
            key = line.split(":", 1)[1].split("-->", 1)[0].strip()
            index += 1
            if index < len(lines) and lines[index].startswith("```mermaid"):
                index += 1
                while index < len(lines) and not lines[index].startswith("```"):
                    index += 1
                index += 1
            while index < len(lines) and not lines[index].strip():
                index += 1
            caption = ""
            if index < len(lines) and lines[index].strip().startswith("*Figure"):
                caption = lines[index].strip().strip("*")
                index += 1
            story.append(KeepTogether([FlowDiagram(key, width), Spacer(1, 4), Paragraph(inline_markup(f"*{caption}*"), style_map["caption"])]))
            continue
        if line.startswith("## "):
            add_heading(story, line[3:], 1, style_map)
            index += 1
            continue
        if line.startswith("### "):
            add_heading(story, line[4:], 2, style_map)
            index += 1
            continue
        if line.startswith("#### "):
            add_heading(story, line[5:], 3, style_map)
            index += 1
            continue
        if line.startswith("```"):
            index += 1
            code: list[str] = []
            while index < len(lines) and not lines[index].startswith("```"):
                code.append(lines[index].rstrip())
                index += 1
            index += 1
            story.append(Preformatted("\n".join(code), style_map["code"] , maxLineLength=100))
            continue
        if line.startswith("|"):
            raw_rows: list[list[str]] = []
            while index < len(lines) and lines[index].strip().startswith("|"):
                cells = [cell.strip() for cell in lines[index].strip().strip("|").split("|")]
                raw_rows.append(cells)
                index += 1
            if len(raw_rows) > 1 and all(re.fullmatch(r":?-{3,}:?", cell) for cell in raw_rows[1]):
                raw_rows.pop(1)
            add_table(story, raw_rows, style_map, width)
            continue
        if re.match(r"^(?:- |\d+\. )", line):
            ordered = bool(re.match(r"^\d+\. ", line))
            items: list[ListItem] = []
            while index < len(lines) and re.match(r"^(?:- |\d+\. )", lines[index].strip()):
                value = re.sub(r"^(?:- |\d+\. )", "", lines[index].strip())
                items.append(ListItem(Paragraph(inline_markup(value), style_map["bullet"]), leftIndent=12))
                index += 1
            story.append(ListFlowable(items, bulletType="1" if ordered else "bullet", leftIndent=24, bulletFontName="Times-Roman", bulletFontSize=9, spaceAfter=7))
            continue
        paragraph_lines = [line.strip()]
        index += 1
        while index < len(lines):
            candidate = lines[index].rstrip()
            if not candidate or candidate.startswith(("## ", "### ", "#### ", "```", "|", "<!-- pdf-figure:")) or re.match(r"^(?:- |\d+\. )", candidate.strip()):
                break
            paragraph_lines.append(candidate.strip())
            index += 1
        story.append(Paragraph(inline_markup(" ".join(paragraph_lines)), style_map["body"]))
    return story


def build() -> None:
    source_lines = SOURCE.read_text(encoding="utf-8").splitlines()
    style_map = styles()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    doc = SoftwareDocument(
        str(OUTPUT),
        pagesize=letter,
        leftMargin=0.82 * inch,
        rightMargin=0.82 * inch,
        topMargin=0.66 * inch,
        bottomMargin=0.62 * inch,
        title="Tube Screamer Guitar Amplifier Software Documentation",
        author="SKIXG Engineering",
        subject="Raspberry Pi amplifier control and digital signal processing software",
    )

    story: list[Flowable] = [Spacer(1, 1.25 * inch)]
    story.append(Paragraph("Tube Screamer Guitar Amplifier", ParagraphStyle("CoverTitle", fontName="Times-Bold", fontSize=25, leading=30, alignment=TA_CENTER, textColor=colors.black, spaceAfter=14)))
    story.append(Paragraph("Software Documentation", ParagraphStyle("CoverSub", fontName="Times-Bold", fontSize=19, leading=23, alignment=TA_CENTER, textColor=colors.black, spaceAfter=0)))
    story.append(Spacer(1, 1.2 * inch))
    story.append(FlowDiagram("product-signal-flow", doc.width))
    story.append(Spacer(1, 1.0 * inch))
    cover_style = ParagraphStyle("Cover", fontName="Times-Roman", fontSize=13, leading=19, alignment=TA_CENTER, textColor=colors.black)
    story.append(Paragraph("Sponsor: Dr. Logan Porter, ESET Department<br/>Technical Advisor: Dr. Lee Hudson<br/>Team: SKIXG Engineering<br/>Revision 2.3<br/>September 8, 2026", cover_style))
    story.append(Spacer(1, 0.65 * inch))
    member_style = ParagraphStyle("Members", fontName="Times-Roman", fontSize=10.5, leading=14, alignment=TA_CENTER, textColor=colors.black)
    story.append(Paragraph("Sudharshan Srikanth | Gaurav Dama | Chikelo Akamelu<br/>Ian Ngetich | Xander Mann-Cooper", member_style))
    story.append(PageBreak())

    story.append(Paragraph("Table of Contents", style_map["h1"]))
    story.append(HRFlowable(width="100%", thickness=0.6, color=colors.black, spaceAfter=10))
    toc = TableOfContents()
    toc.levelStyles = [
        ParagraphStyle("TOC1", fontName="Times-Bold", fontSize=10.5, leading=14, leftIndent=0, firstLineIndent=0, spaceBefore=3),
        ParagraphStyle("TOC2", fontName="Times-Roman", fontSize=9.5, leading=12, leftIndent=18, firstLineIndent=0),
        ParagraphStyle("TOC3", fontName="Times-Roman", fontSize=9, leading=11, leftIndent=36, firstLineIndent=0),
    ]
    story.append(toc)
    story.append(PageBreak())

    body_start = next(i for i, line in enumerate(source_lines) if line.startswith("## 1. Introduction"))
    story.extend(parse_body(source_lines[body_start:], style_map, doc.width))
    doc.multiBuild(story)
    print(OUTPUT)


if __name__ == "__main__":
    try:
        build()
    except Exception as error:
        print(f"documentation build failed: {error}", file=sys.stderr)
        raise
