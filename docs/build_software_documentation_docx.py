from __future__ import annotations

import re
from pathlib import Path

from docx import Document
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.table import WD_ALIGN_VERTICAL, WD_TABLE_ALIGNMENT
from docx.enum.text import (
    WD_ALIGN_PARAGRAPH,
    WD_LINE_SPACING,
    WD_TAB_ALIGNMENT,
    WD_TAB_LEADER,
)
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs" / "SOFTWARE_DOCUMENTATION_V2_8.md"
OUTPUT = ROOT / "output" / "docx" / "Tube_Screamer_Software_Documentation_Rev_2_8.docx"
ASSET_DIR = ROOT / "tmp" / "docx-assets"

GREEN = "355E3B"
PALE_GREEN = "EAF2EA"
PALE_GRAY = "F2F5F2"
GRID = "D9D9D9"

TOC_PAGE_MAP = {
    "1. Introduction": 3,
    "2. Logic Flow": 4,
    "2.1 Product Signal Flow": 4,
    "2.2 Application Logic Flow": 4,
    "3. System Documentation": 6,
    "3.1 System Overview": 6,
    "3.2 System Architecture": 6,
    "3.3 Software Interfaces": 7,
    "Engineering Report Files": 7,
    "3.4 Hardware Interfaces": 7,
    "Raspberry Pi 5": 7,
    "Raspberry Pi Codec Zero": 7,
    "Waveshare Touchscreen": 7,
    "Tube Amplifier": 7,
    "3.5 Audio Processing": 8,
    "3.6 Data Structures": 8,
    "ControlState": 8,
    "AudioSnapshot": 8,
    "Audio Block and DSP State": 8,
    "3.7 Thread and Device Communication": 9,
    "3.8 Error Handling": 10,
    "3.9 Current Integration Status": 11,
    "4. Source Code Documentation": 12,
    "4.1 Source File Structure": 12,
    "4.2 main.py": 12,
    "4.3 audio_engine.py": 12,
    "4.4 audio_sources.py": 12,
    "4.5 dsp.py": 12,
    "4.6 performance.py": 13,
    "4.7 simulation.py": 13,
    "4.8 deploy/tube-screamer.service": 13,
    "5. Build and Use Information": 14,
    "5.1 Required Software": 14,
    "5.2 Raspberry Pi Installation": 14,
    "5.3 Codec Zero Setup": 15,
    "5.4 Starting the Application": 15,
    "5.5 Operating Instructions": 15,
    "Start Live Audio": 15,
    "Adjust the Sound": 15,
    "Stop and Shut Down": 15,
    "5.6 Software Unit Tests": 16,
}


def set_cell_shading(cell: object, fill: str) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    shading = tc_pr.find(qn("w:shd"))
    if shading is None:
        shading = OxmlElement("w:shd")
        tc_pr.append(shading)
    shading.set(qn("w:fill"), fill)


def set_cell_margins(cell: object, top: int = 90, start: int = 100, bottom: int = 90, end: int = 100) -> None:
    tc = cell._tc
    tc_pr = tc.get_or_add_tcPr()
    margins = tc_pr.first_child_found_in("w:tcMar")
    if margins is None:
        margins = OxmlElement("w:tcMar")
        tc_pr.append(margins)
    for name, value in (("top", top), ("start", start), ("bottom", bottom), ("end", end)):
        node = margins.find(qn(f"w:{name}"))
        if node is None:
            node = OxmlElement(f"w:{name}")
            margins.append(node)
        node.set(qn("w:w"), str(value))
        node.set(qn("w:type"), "dxa")


def set_repeat_table_header(row: object) -> None:
    tr_pr = row._tr.get_or_add_trPr()
    repeat = OxmlElement("w:tblHeader")
    repeat.set(qn("w:val"), "true")
    tr_pr.append(repeat)


def apply_cell_borders(cell: object) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    borders = tc_pr.first_child_found_in("w:tcBorders")
    if borders is None:
        borders = OxmlElement("w:tcBorders")
        tc_pr.append(borders)
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        element = borders.find(qn(f"w:{edge}"))
        if element is None:
            element = OxmlElement(f"w:{edge}")
            borders.append(element)
        element.set(qn("w:val"), "single")
        element.set(qn("w:sz"), "4")
        element.set(qn("w:color"), GRID)


def set_paragraph_shading(paragraph: object, fill: str) -> None:
    p_pr = paragraph._p.get_or_add_pPr()
    shading = OxmlElement("w:shd")
    shading.set(qn("w:fill"), fill)
    p_pr.append(shading)


def add_page_number(paragraph: object) -> None:
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = paragraph.add_run()
    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")
    instruction = OxmlElement("w:instrText")
    instruction.set(qn("xml:space"), "preserve")
    instruction.text = " PAGE "
    separate = OxmlElement("w:fldChar")
    separate.set(qn("w:fldCharType"), "separate")
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    run._r.extend((begin, instruction, separate, end))


def configure_document(document: Document) -> None:
    section = document.sections[0]
    section.page_width = Inches(8.5)
    section.page_height = Inches(11)
    section.top_margin = Inches(0.7)
    section.bottom_margin = Inches(0.65)
    section.left_margin = Inches(0.82)
    section.right_margin = Inches(0.82)
    section.different_first_page_header_footer = True

    normal = document.styles["Normal"]
    normal.font.name = "Times New Roman"
    normal.font.size = Pt(10.5)
    normal.font.color.rgb = RGBColor(0, 0, 0)
    normal.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    normal.paragraph_format.line_spacing_rule = WD_LINE_SPACING.SINGLE
    normal.paragraph_format.space_after = Pt(6)

    title = document.styles.add_style("Cover Title", WD_STYLE_TYPE.PARAGRAPH)
    title.base_style = normal
    title.font.name = "Times New Roman"
    title.font.size = Pt(25)
    title.font.bold = True
    title.font.color.rgb = RGBColor(0, 0, 0)
    title.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title.paragraph_format.space_after = Pt(10)

    for name, size, align, before, after in (
        ("Heading 1", 17, WD_ALIGN_PARAGRAPH.CENTER, 12, 8),
        ("Heading 2", 14, WD_ALIGN_PARAGRAPH.LEFT, 10, 5),
        ("Heading 3", 11, WD_ALIGN_PARAGRAPH.LEFT, 8, 4),
    ):
        style = document.styles[name]
        style.font.name = "Times New Roman"
        style.font.size = Pt(size)
        style.font.bold = name != "Heading 3"
        style.font.color.rgb = RGBColor(0, 0, 0)
        style.paragraph_format.alignment = align
        style.paragraph_format.space_before = Pt(before)
        style.paragraph_format.space_after = Pt(after)
        style.paragraph_format.keep_with_next = True
    document.styles["Heading 1"].paragraph_format.page_break_before = True

    code = document.styles.add_style("Code Block", WD_STYLE_TYPE.PARAGRAPH)
    code.font.name = "Courier New"
    code.font.size = Pt(8)
    code.paragraph_format.left_indent = Inches(0.18)
    code.paragraph_format.right_indent = Inches(0.18)
    code.paragraph_format.space_before = Pt(3)
    code.paragraph_format.space_after = Pt(7)

    header = section.header.paragraphs[0]
    header.text = "Tube Screamer Guitar Amplifier    Sponsor: Dr. Logan Porter    Rev 2.8    September 8, 2026"
    header.style = document.styles["Header"]
    header.runs[0].font.name = "Times New Roman"
    header.runs[0].font.size = Pt(8)
    add_page_number(section.footer.paragraphs[0])

    settings = document.settings._element
    update_fields = OxmlElement("w:updateFields")
    update_fields.set(qn("w:val"), "true")
    settings.append(update_fields)


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    base = "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf"
    return ImageFont.truetype(base, size)


def draw_box(draw: ImageDraw.ImageDraw, xy: tuple[int, int, int, int], label: str, highlighted: bool = False) -> None:
    draw.rounded_rectangle(xy, radius=14, fill="#EAF2EA" if highlighted else "white", outline="#303030", width=3)
    lines = label.split("\n")
    face = font(24, True)
    bounds = [draw.textbbox((0, 0), line, font=face) for line in lines]
    total_height = sum(box[3] - box[1] for box in bounds) + 7 * (len(lines) - 1)
    y = (xy[1] + xy[3] - total_height) / 2
    for line, box in zip(lines, bounds, strict=True):
        width = box[2] - box[0]
        draw.text(((xy[0] + xy[2] - width) / 2, y), line, fill="black", font=face)
        y += box[3] - box[1] + 7


def draw_arrow(draw: ImageDraw.ImageDraw, start: tuple[int, int], end: tuple[int, int]) -> None:
    draw.line((start, end), fill="#355E3B", width=5)
    x, y = end
    if abs(end[0] - start[0]) >= abs(end[1] - start[1]):
        direction = 1 if end[0] >= start[0] else -1
        base = x - direction * 15
        draw.polygon(((x, y), (base, y - 9), (base, y + 9)), fill="#355E3B")
    else:
        direction = 1 if end[1] >= start[1] else -1
        base = y - direction * 15
        draw.polygon(((x, y), (x - 9, base), (x + 9, base)), fill="#355E3B")


def horizontal_figure(labels: list[str], path: Path) -> None:
    image = Image.new("RGB", (1800, 310), "white")
    draw = ImageDraw.Draw(image)
    gap = 18
    width = (1700 - gap * (len(labels) - 1)) // len(labels)
    y1, y2 = 90, 220
    for index, label in enumerate(labels):
        x1 = 50 + index * (width + gap)
        x2 = x1 + width
        draw_box(draw, (x1, y1, x2, y2), label, "DSP" in label or "Limiter" in label)
        if index:
            draw_arrow(draw, (x1 - gap + 2, 155), (x1 - 2, 155))
    image.save(path, dpi=(180, 180))


def startup_figure(path: Path) -> None:
    image = Image.new("RGB", (1200, 900), "white")
    draw = ImageDraw.Draw(image)
    labels = [
        "Application Start",
        "Create Touchscreen and DSP",
        "Muted - Wait for Start",
        "Open Codec Zero Stream",
        "Process Live Audio",
        "Stop Command or Fault",
    ]
    positions = [35, 170, 305, 440, 575, 710]
    for index, (label, y1) in enumerate(zip(labels, positions, strict=True)):
        draw_box(draw, (280, y1, 920, y1 + 82), label, index == 2)
        if index:
            draw_arrow(draw, (600, positions[index - 1] + 82), (600, y1))
    draw.line((920, 751, 1050, 751, 1050, 346), fill="#355E3B", width=5)
    draw_arrow(draw, (1050, 346), (920, 346))
    image.save(path, dpi=(180, 180))


def module_figure(path: Path) -> None:
    image = Image.new("RGB", (1500, 850), "white")
    draw = ImageDraw.Draw(image)
    boxes = {
        "Touchscreen UI\nmain.py": (510, 40, 990, 145),
        "Status Snapshot\nAudioSnapshot": (40, 265, 430, 370),
        "Audio Engine\naudio_engine.py": (510, 265, 990, 370),
        "Inactive Display\nsimulation.py": (40, 445, 430, 550),
        "Live Codec Input\naudio_sources.py": (40, 625, 430, 730),
        "Real-Time DSP\ndsp.py": (555, 625, 945, 730),
        "Codec Zero\nALSA and PortAudio": (1070, 625, 1460, 730),
        "Resource Monitor\nperformance.py": (1070, 265, 1460, 370),
    }
    for label, box in boxes.items():
        draw_box(draw, box, label, "DSP" in label)
    draw_arrow(draw, (750, 145), (750, 265))
    draw_arrow(draw, (510, 320), (430, 320))
    draw.line((235, 265, 235, 92), fill="#355E3B", width=5)
    draw_arrow(draw, (235, 92), (510, 92))
    draw.line((40, 497, 18, 497, 18, 118), fill="#355E3B", width=5)
    draw_arrow(draw, (18, 118), (510, 118))
    draw_arrow(draw, (990, 320), (1070, 320))
    draw_arrow(draw, (510, 320), (430, 675))
    draw_arrow(draw, (750, 370), (750, 625))
    draw_arrow(draw, (990, 320), (1070, 675))
    image.save(path, dpi=(180, 180))


def sequence_figure(path: Path) -> None:
    image = Image.new("RGB", (1700, 880), "white")
    draw = ImageDraw.Draw(image)
    labels = ["User", "Tkinter", "Audio Callback", "Codec Zero", "Monitor"]
    centers = [120, 480, 850, 1220, 1580]
    for x, label in zip(centers, labels, strict=True):
        draw_box(draw, (x - 110, 40, x + 110, 130), label, label == "Audio Callback")
        draw.line((x, 130, x, 830), fill="#888888", width=2)
    messages = [
        (0, 1, "Change control"),
        (1, 2, "Publish ControlState"),
        (3, 2, "Deliver 512 samples"),
        (2, 3, "Write limited output"),
        (2, 1, "Publish AudioSnapshot"),
        (2, 4, "Publish snapshot and counters"),
    ]
    label_font = font(22)
    for row, (source, target, label) in enumerate(messages):
        y = 220 + row * 95
        draw_arrow(draw, (centers[source], y), (centers[target], y))
        box = draw.textbbox((0, 0), label, font=label_font)
        draw.text(((centers[source] + centers[target] - (box[2] - box[0])) / 2, y - 33), label, fill="black", font=label_font)
    image.save(path, dpi=(180, 180))


def fault_figure(path: Path) -> None:
    image = Image.new("RGB", (1200, 900), "white")
    draw = ImageDraw.Draw(image)
    draw_box(draw, (280, 35, 920, 117), "Live Audio Running")
    diamond = ((600, 155), (850, 225), (600, 295), (350, 225))
    draw.polygon(diamond, fill="#EAF2EA", outline="#303030")
    label = "Callback Successful?"
    face = font(23, True)
    bounds = draw.textbbox((0, 0), label, font=face)
    draw.text((600 - (bounds[2] - bounds[0]) / 2, 212), label, fill="black", font=face)
    draw_arrow(draw, (600, 117), (600, 155))
    draw_arrow(draw, (850, 225), (920, 225))
    draw_box(draw, (920, 180, 1170, 270), "Write Processed\nOutput")
    draw.line((1045, 180, 1045, 76), fill="#355E3B", width=5)
    draw_arrow(draw, (1045, 76), (920, 76))
    draw.text((864, 190), "Yes", fill="black", font=font(20, True))
    draw.text((620, 303), "No", fill="black", font=font(20, True))
    boxes = [
        ("Write Silence", 345),
        ("Latch Error Status", 485),
        ("Close Stream on Main Thread", 625),
        ("Wait for Operator Restart", 765),
    ]
    previous_y = 295
    for box_label, y1 in boxes:
        draw_arrow(draw, (600, previous_y), (600, y1))
        draw_box(draw, (280, y1, 920, y1 + 82), box_label)
        previous_y = y1 + 82
    image.save(path, dpi=(180, 180))


def make_figures() -> dict[str, Path]:
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    figures = {name: ASSET_DIR / f"{name}.png" for name in (
        "product-signal-flow", "startup-flow", "module-architecture", "dsp-flow", "thread-communication", "fault-flow"
    )}
    horizontal_figure(["Guitar\nInput", "Preamp and\nBuffer", "Tube\nStages", "Protected\nInterface", "ADC", "Pi 5\nDSP", "DAC", "Line\nOutput"], figures["product-signal-flow"])
    startup_figure(figures["startup-flow"])
    module_figure(figures["module-architecture"])
    horizontal_figure(["Input", "5-Band\nEQ", "Chorus", "Delay", "Echo", "Reverb", "Digital Output\nLevel", "Limiter"], figures["dsp-flow"])
    sequence_figure(figures["thread-communication"])
    fault_figure(figures["fault-flow"])
    return figures


def add_inline(paragraph: object, text: str) -> None:
    text = re.sub(r"\[([^]]+)\]\([^)]+\)", r"\1", text)
    tokens = re.split(r"(`[^`]+`|\*\*[^*]+\*\*|\*[^*]+\*)", text)
    for token in tokens:
        if not token:
            continue
        if token.startswith("`") and token.endswith("`"):
            run = paragraph.add_run(token[1:-1])
            run.font.name = "Courier New"
            run.font.size = Pt(9)
        elif token.startswith("**") and token.endswith("**"):
            paragraph.add_run(token[2:-2]).bold = True
        elif token.startswith("*") and token.endswith("*"):
            paragraph.add_run(token[1:-1]).italic = True
        else:
            paragraph.add_run(token)


def add_manual_toc(document: Document, page_map: dict[str, int]) -> None:
    for line in SOURCE.read_text(encoding="utf-8").splitlines():
        match = re.match(r"^(#{2,4})\s+(.+)$", line)
        if not match or match.group(2) == "Table of Contents":
            continue
        level = len(match.group(1)) - 1
        heading = match.group(2)
        paragraph = document.add_paragraph()
        paragraph.paragraph_format.left_indent = Inches(0.18 * (level - 1))
        paragraph.paragraph_format.space_after = Pt(1.5)
        paragraph.paragraph_format.tab_stops.add_tab_stop(
            Inches(6.5), WD_TAB_ALIGNMENT.RIGHT, WD_TAB_LEADER.DOTS
        )
        run = paragraph.add_run(heading)
        run.font.name = "Times New Roman"
        run.font.size = Pt(10 if level == 1 else 9 if level == 2 else 8.5)
        run.bold = level == 1
        page_run = paragraph.add_run(f"\t{page_map.get(heading, 0):02d}")
        page_run.font.name = "Times New Roman"
        page_run.font.size = run.font.size


def table_weights(rows: list[list[str]]) -> list[float]:
    count = len(rows[0])
    header = rows[0][0].strip()
    if count == 5 and header == "Test ID":
        return [0.10, 0.22, 0.24, 0.28, 0.16]
    if count == 4 and header == "Priority":
        return [0.10, 0.15, 0.35, 0.40]
    if count == 2:
        return [0.24, 0.76]
    lengths = [max(7, max(len(row[index]) for row in rows)) for index in range(count)]
    capped = [min(value, 60) for value in lengths]
    total = sum(capped)
    return [value / total for value in capped]


def add_table(document: Document, rows: list[list[str]]) -> None:
    table = document.add_table(rows=len(rows), cols=len(rows[0]))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    available = 6.86
    weights = table_weights(rows)
    for row_index, values in enumerate(rows):
        for column_index, value in enumerate(values):
            cell = table.cell(row_index, column_index)
            cell.width = Inches(available * weights[column_index])
            cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
            set_cell_margins(cell)
            apply_cell_borders(cell)
            if row_index == 0:
                set_cell_shading(cell, GREEN)
            elif row_index % 2 == 0:
                set_cell_shading(cell, PALE_GRAY)
            paragraph = cell.paragraphs[0]
            paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER if row_index == 0 else WD_ALIGN_PARAGRAPH.LEFT
            paragraph.paragraph_format.space_after = Pt(0)
            add_inline(paragraph, value)
            for run in paragraph.runs:
                run.font.name = "Arial"
                run.font.size = Pt(8.3)
                if row_index == 0:
                    run.font.color.rgb = RGBColor(255, 255, 255)
                    run.bold = True
    set_repeat_table_header(table.rows[0])
    document.add_paragraph().paragraph_format.space_after = Pt(1)


def parse_markdown(document: Document, figures: dict[str, Path]) -> None:
    lines = SOURCE.read_text(encoding="utf-8").splitlines()
    start = next(index for index, line in enumerate(lines) if line.startswith("## 1. Introduction"))
    index = start
    pending_figure: str | None = None
    while index < len(lines):
        line = lines[index].rstrip()
        if not line:
            index += 1
            continue
        if line.startswith("<!-- pdf-figure:"):
            pending_figure = line.split(":", 1)[1].split("-->", 1)[0].strip()
            index += 1
            continue
        if line.startswith("```mermaid"):
            index += 1
            while index < len(lines) and not lines[index].startswith("```"):
                index += 1
            index += 1
            if pending_figure:
                paragraph = document.add_paragraph()
                paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
                paragraph.add_run().add_picture(str(figures[pending_figure]), width=Inches(6.65))
                pending_figure = None
            continue
        if line.startswith("```"):
            code_lines = []
            index += 1
            while index < len(lines) and not lines[index].startswith("```"):
                code_lines.append(lines[index])
                index += 1
            index += 1
            paragraph = document.add_paragraph(style="Code Block")
            set_paragraph_shading(paragraph, "F3F3F3")
            paragraph.add_run("\n".join(code_lines))
            continue
        if line.startswith("|"):
            table_lines = []
            while index < len(lines) and lines[index].strip().startswith("|"):
                table_lines.append(lines[index].strip())
                index += 1
            parsed = [[cell.strip() for cell in row.strip("|").split("|")] for row in table_lines]
            rows = [row for row in parsed if not all(re.fullmatch(r":?-{3,}:?", cell) for cell in row)]
            add_table(document, rows)
            continue
        heading = re.match(r"^(#{2,4})\s+(.+)$", line)
        if heading:
            level = len(heading.group(1)) - 1
            document.add_heading(heading.group(2), level=level)
            index += 1
            continue
        if re.match(r"^\d+\.\s+", line):
            paragraph = document.add_paragraph()
            paragraph.paragraph_format.left_indent = Inches(0.25)
            paragraph.paragraph_format.first_line_indent = Inches(-0.2)
            add_inline(paragraph, line)
            index += 1
            continue
        if line.startswith("- "):
            paragraph = document.add_paragraph(style="List Bullet")
            add_inline(paragraph, line[2:])
            index += 1
            continue
        paragraph = document.add_paragraph()
        add_inline(paragraph, line)
        index += 1


def build() -> Path:
    figures = make_figures()
    document = Document()
    configure_document(document)

    document.add_paragraph().paragraph_format.space_after = Pt(54)
    document.add_paragraph("Tube Screamer Guitar Amplifier", style="Cover Title")
    subtitle = document.add_paragraph("Software Documentation")
    subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
    subtitle.runs[0].font.name = "Times New Roman"
    subtitle.runs[0].font.size = Pt(19)
    subtitle.runs[0].bold = True
    image_paragraph = document.add_paragraph()
    image_paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    image_paragraph.add_run().add_picture(str(figures["product-signal-flow"]), width=Inches(6.55))
    metadata = document.add_paragraph()
    metadata.alignment = WD_ALIGN_PARAGRAPH.CENTER
    metadata.paragraph_format.space_before = Pt(32)
    add_inline(metadata, "Sponsor: Dr. Logan Porter, ESET Department\nTechnical Advisor: Dr. Lee Hudson\nTeam: SKIXG Engineering\nRevision 2.8\nSeptember 8, 2026")
    members = document.add_paragraph("Sudharshan Srikanth | Gaurav Dama | Chikelo Akamelu\nIan Ngetich | Xander Mann-Cooper")
    members.alignment = WD_ALIGN_PARAGRAPH.CENTER
    members.paragraph_format.space_before = Pt(22)
    document.add_page_break()

    toc_heading = document.add_paragraph("Table of Contents", style="Cover Title")
    toc_heading.runs[0].font.size = Pt(18)
    add_manual_toc(document, TOC_PAGE_MAP)
    parse_markdown(document, figures)

    core = document.core_properties
    core.title = "Tube Screamer Guitar Amplifier Software Documentation"
    core.subject = "Raspberry Pi amplifier control and digital signal processing software"
    core.author = "SKIXG Engineering"
    core.comments = "Revision 2.8"
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    document.save(OUTPUT)
    return OUTPUT


if __name__ == "__main__":
    print(build())
