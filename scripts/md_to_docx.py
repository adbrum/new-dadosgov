#!/usr/bin/env python3
"""Lightweight Markdown -> .docx converter (no pandoc needed).

Handles: ATX headings, paragraphs, bold (**), inline code (`), bullet lists,
blockquotes, fenced code blocks and GitHub pipe tables. Built for the
dados.gov.pt technical docs; not a full CommonMark implementation.
"""
import re
import sys

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt, RGBColor


INLINE_RE = re.compile(r"(\*\*.+?\*\*|`.+?`)")


def add_runs(paragraph, text):
    """Render inline **bold** and `code` spans into a paragraph."""
    for part in INLINE_RE.split(text):
        if not part:
            continue
        if part.startswith("**") and part.endswith("**"):
            run = paragraph.add_run(part[2:-2])
            run.bold = True
        elif part.startswith("`") and part.endswith("`"):
            run = paragraph.add_run(part[1:-1])
            run.font.name = "Consolas"
            run.font.color.rgb = RGBColor(0xC0, 0x34, 0x21)
        else:
            paragraph.add_run(part)


def split_row(line):
    cells = line.strip().strip("|").split("|")
    return [c.strip() for c in cells]


def is_separator(line):
    return bool(re.match(r"^\s*\|?[\s:|-]+\|?\s*$", line)) and "-" in line


def convert(md_path, docx_path):
    with open(md_path, encoding="utf-8") as fh:
        lines = fh.read().splitlines()

    doc = Document()
    doc.styles["Normal"].font.name = "Calibri"
    doc.styles["Normal"].font.size = Pt(11)

    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]

        # Fenced code block
        if line.lstrip().startswith("```"):
            i += 1
            buf = []
            while i < n and not lines[i].lstrip().startswith("```"):
                buf.append(lines[i])
                i += 1
            i += 1  # closing fence
            p = doc.add_paragraph()
            run = p.add_run("\n".join(buf))
            run.font.name = "Consolas"
            run.font.size = Pt(9)
            continue

        # Table (header row + separator)
        if line.strip().startswith("|") and i + 1 < n and is_separator(lines[i + 1]):
            header = split_row(line)
            i += 2
            rows = []
            while i < n and lines[i].strip().startswith("|"):
                rows.append(split_row(lines[i]))
                i += 1
            table = doc.add_table(rows=1, cols=len(header))
            table.style = "Light Grid Accent 1"
            for idx, htext in enumerate(header):
                cell = table.rows[0].cells[idx]
                cell.paragraphs[0].clear()
                add_runs(cell.paragraphs[0], htext)
                for r in cell.paragraphs[0].runs:
                    r.bold = True
            for row in rows:
                cells = table.add_row().cells
                for idx in range(len(header)):
                    text = row[idx] if idx < len(row) else ""
                    cells[idx].paragraphs[0].clear()
                    add_runs(cells[idx].paragraphs[0], text)
            doc.add_paragraph()
            continue

        # Headings
        m = re.match(r"^(#{1,6})\s+(.*)$", line)
        if m:
            level = len(m.group(1))
            text = m.group(2).strip()
            if level == 1:
                h = doc.add_heading("", level=0)
                add_runs(h, text)
            else:
                h = doc.add_heading("", level=min(level - 1, 4))
                add_runs(h, text)
            i += 1
            continue

        # Horizontal rule
        if re.match(r"^\s*---+\s*$", line):
            i += 1
            continue

        # Blockquote
        if line.lstrip().startswith(">"):
            text = line.lstrip()[1:].strip()
            p = doc.add_paragraph(style="Intense Quote")
            add_runs(p, text)
            i += 1
            continue

        # Bullet list
        m = re.match(r"^(\s*)[-*]\s+(.*)$", line)
        if m:
            p = doc.add_paragraph(style="List Bullet")
            add_runs(p, m.group(2))
            i += 1
            continue

        # Numbered list
        m = re.match(r"^(\s*)\d+\.\s+(.*)$", line)
        if m:
            p = doc.add_paragraph(style="List Number")
            add_runs(p, m.group(2))
            i += 1
            continue

        # Blank line
        if not line.strip():
            i += 1
            continue

        # Paragraph
        p = doc.add_paragraph()
        add_runs(p, line)
        i += 1

    doc.save(docx_path)
    print(f"Wrote {docx_path}")


if __name__ == "__main__":
    src = sys.argv[1]
    dst = sys.argv[2] if len(sys.argv) > 2 else src.rsplit(".", 1)[0] + ".docx"
    convert(src, dst)
