#!/usr/bin/env python3
"""Render repository Markdown reports as print-ready HTML for browser PDF export."""
from __future__ import annotations

import argparse
import html
import re
from pathlib import Path


def inline(value: str) -> str:
    value = html.escape(value, quote=False)
    value = re.sub(r"`([^`]+)`", r"<code>\1</code>", value)
    return re.sub(r"\[([^]]+)\]\(([^ )]+)(?:\s+&quot;[^)]*&quot;)?\)", r'<a href="\2">\1</a>', value)


def cells(line: str) -> list[str]:
    return [item.strip() for item in line.strip().strip("|").split("|")]


def table_rule(line: str) -> bool:
    return bool(cells(line)) and all(re.fullmatch(r":?-{3,}:?", cell) for cell in cells(line))


def render(markdown: str) -> str:
    lines, output, index = markdown.splitlines(), [], 0
    paragraphs, bullets = [], []

    def flush_paragraphs() -> None:
        nonlocal paragraphs
        if paragraphs:
            output.append("<p>" + " ".join(inline(value) for value in paragraphs) + "</p>")
            paragraphs = []

    def flush_bullets() -> None:
        nonlocal bullets
        if bullets:
            output.append("<ul>" + "".join(f"<li>{inline(value)}</li>" for value in bullets) + "</ul>")
            bullets = []

    while index < len(lines):
        line = lines[index]
        if line.startswith("|") and index + 1 < len(lines) and table_rule(lines[index + 1]):
            flush_paragraphs(); flush_bullets()
            headers, index, rows = cells(line), index + 2, []
            while index < len(lines) and lines[index].startswith("|"):
                rows.append(cells(lines[index])); index += 1
            output.append("<table><thead><tr>" + "".join(f"<th>{inline(value)}</th>" for value in headers) + "</tr></thead><tbody>")
            output.extend("<tr>" + "".join(f"<td>{inline(value)}</td>" for value in row) + "</tr>" for row in rows)
            output.append("</tbody></table>")
            continue
        heading = re.match(r"^(#{1,6})\s+(.+)$", line)
        if heading:
            flush_paragraphs(); flush_bullets()
            output.append(f"<h{len(heading.group(1))}>{inline(heading.group(2))}</h{len(heading.group(1))}>")
        elif re.match(r"^\s*-\s+", line):
            flush_paragraphs(); bullets.append(re.sub(r"^\s*-\s+", "", line))
        elif not line.strip():
            flush_paragraphs(); flush_bullets()
        else:
            flush_bullets(); paragraphs.append(line.strip())
        index += 1
    flush_paragraphs(); flush_bullets()
    return "\n".join(output)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path); parser.add_argument("output", type=Path)
    args = parser.parse_args()
    body = render(args.input.read_text(encoding="utf-8"))
    document = f'''<!doctype html><html lang="es"><head><meta charset="utf-8"><style>
@page {{ size: A4 landscape; margin: 13mm 11mm 15mm; }}
* {{ box-sizing: border-box; }} body {{ color:#172033; font:9.2pt/1.34 Arial,Helvetica,sans-serif; }}
h1 {{ color:#0b3a6d; font-size:21pt; margin:0 0 6mm; border-bottom:2px solid #1c75bc; padding-bottom:3mm; }}
h2 {{ color:#0b3a6d; font-size:14pt; margin:8mm 0 3mm; padding-bottom:1.5mm; border-bottom:1px solid #cbd5e1; break-after:avoid; }}
h3 {{ color:#164e7b; font-size:10.5pt; margin:5mm 0 2mm; break-after:avoid; }}
p {{ margin:0 0 3mm; }} ul {{ margin:0 0 3mm; padding-left:5mm; }} li {{ margin:1mm 0; }}
table {{ border-collapse:collapse; width:100%; table-layout:auto; margin:0 0 4mm; font-size:7.5pt; break-inside:auto; }}
thead {{ display:table-header-group; }} tr {{ break-inside:avoid; }} th {{ background:#0b3a6d; color:white; font-weight:bold; }}
th,td {{ border:.5px solid #b8c4d2; padding:1.25mm 1.5mm; vertical-align:top; overflow-wrap:anywhere; }}
tbody tr:nth-child(even) {{ background:#f5f8fb; }} a {{ color:#0c5ea8; text-decoration:none; }}
code {{ font:7.7pt 'Courier New',monospace; background:#eef2f7; border-radius:2px; padding:.2mm .6mm; }}
</style></head><body>{body}</body></html>'''
    args.output.write_text(document, encoding="utf-8")


if __name__ == "__main__":
    main()
