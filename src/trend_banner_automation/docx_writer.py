from __future__ import annotations

import html
import re
import zipfile
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Run:
    text: str
    bold: bool = False


def markdown_to_docx(markdown: str, output_path: Path, title: str = "Weekly Trend Report") -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    clean_markdown = _remove_machine_sections(markdown)
    body = [
        _paragraph([Run(title)], style="Title"),
        _paragraph([Run("최근 7일 국내 트렌드 기반 주간 리포트")], style="Subtitle"),
    ]

    lines = clean_markdown.splitlines()
    index = 0
    while index < len(lines):
        raw = lines[index].rstrip()
        line = raw.strip()
        if not line:
            index += 1
            continue
        if line.startswith("```"):
            index = _skip_code_block(lines, index)
            continue
        if line == "---":
            body.append(_horizontal_rule())
            index += 1
            continue
        if line.startswith("|") and index + 1 < len(lines) and lines[index + 1].strip().startswith("|"):
            table_lines: list[str] = []
            while index < len(lines) and lines[index].strip().startswith("|"):
                table_lines.append(lines[index].strip())
                index += 1
            body.append(_table(table_lines))
            continue

        body.append(_format_line(line))
        index += 1

    document_xml = _document_xml("".join(body))
    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as package:
        package.writestr("[Content_Types].xml", CONTENT_TYPES)
        package.writestr("_rels/.rels", RELS)
        package.writestr("word/document.xml", document_xml)
        package.writestr("word/styles.xml", STYLES)
        package.writestr("word/_rels/document.xml.rels", DOCUMENT_RELS)
    return output_path


def _remove_machine_sections(markdown: str) -> str:
    return re.split(r"\n## IMAGE_PROMPTS_JSON\b", markdown, maxsplit=1)[0]


def _skip_code_block(lines: list[str], index: int) -> int:
    index += 1
    while index < len(lines) and not lines[index].startswith("```"):
        index += 1
    return index + 1


def _format_line(line: str) -> str:
    heading_match = re.match(r"^(#{1,6})\s+(.+)$", line)
    if heading_match:
        level = len(heading_match.group(1))
        text = _clean_heading(heading_match.group(2))
        if _is_trend_title(text):
            return _paragraph(_parse_inline(text), style="TrendTitle", before_rule=True)
        style = "Heading1" if level <= 2 else "Heading2"
        return _paragraph(_parse_inline(text), style=style)

    numbered = re.match(r"^(\d+)[.)]\s+(.+)$", line)
    if numbered:
        return _paragraph(
            [Run(f"{numbered.group(1)}. ", bold=True), *_parse_inline(numbered.group(2))],
            style="Numbered",
        )

    if line.startswith("- "):
        text = line[2:].strip()
        if _looks_like_label_bullet(text):
            return _label_paragraph(text)
        return _paragraph([Run("• ", bold=True), *_parse_inline(text)], style="Bullet")

    if line.startswith(">"):
        return _paragraph(_parse_inline(line.lstrip("> ").strip()), style="Quote")

    if _looks_like_label(line):
        return _paragraph(_parse_inline(line), style="Label")

    return _paragraph(_parse_inline(line), style="Body")


def _is_trend_title(text: str) -> bool:
    return bool(
        re.search(r"(Core\s*\d+|컨셉\s*\d+|Trend\s*\d+|^\d+\)\s*)", text, re.IGNORECASE)
    )


def _looks_like_label(text: str) -> bool:
    labels = (
        "왜 뜨는가",
        "등장 채널",
        "비즈니스 시사점",
        "소비자 심리",
        "광고 활용 포인트",
        "상승 이유",
        "공통 준수",
    )
    return text.rstrip(":") in labels


def _looks_like_label_bullet(text: str) -> bool:
    return bool(re.match(r"^\*\*[^*]{1,24}:\*\*", text))


def _label_paragraph(text: str) -> str:
    return _paragraph(_parse_inline(text), style="Body")


def _clean_heading(text: str) -> str:
    return text.replace("(Workflow Step 1)", "").replace("(Workflow Step 2)", "").strip()


def _parse_inline(text: str) -> list[Run]:
    text = re.sub(r"`([^`]+)`", r"\1", text)
    runs: list[Run] = []
    cursor = 0
    for match in re.finditer(r"\*\*(.*?)\*\*", text):
        if match.start() > cursor:
            runs.append(Run(text[cursor : match.start()]))
        runs.append(Run(match.group(1), bold=True))
        cursor = match.end()
    if cursor < len(text):
        runs.append(Run(text[cursor:]))
    return runs or [Run("")]


def _paragraph(runs: list[Run], style: str = "Body", before_rule: bool = False) -> str:
    style_xml = f'<w:pStyle w:val="{style}"/>'
    rule_xml = (
        '<w:pBdr><w:top w:val="single" w:sz="4" w:space="10" w:color="D9DDE5"/></w:pBdr>'
        if before_rule
        else ""
    )
    return (
        "<w:p>"
        f"<w:pPr>{style_xml}{rule_xml}</w:pPr>"
        f"{''.join(_run(run) for run in runs)}"
        "</w:p>"
    )


def _run(run: Run) -> str:
    bold_xml = "<w:b/>" if run.bold else ""
    return (
        "<w:r>"
        f"<w:rPr>{bold_xml}</w:rPr>"
        f"<w:t xml:space=\"preserve\">{html.escape(run.text)}</w:t>"
        "</w:r>"
    )


def _horizontal_rule() -> str:
    return (
        "<w:p><w:pPr><w:pBdr>"
        '<w:bottom w:val="single" w:sz="4" w:space="8" w:color="D9DDE5"/>'
        "</w:pBdr></w:pPr></w:p>"
    )


def _table(lines: list[str]) -> str:
    rows = []
    row_index = 0
    for line in lines:
        if re.match(r"^\|\s*-", line):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        cell_xml = ""
        for cell in cells:
            fill = '<w:shd w:fill="EEF4FF"/>' if row_index == 0 else ""
            cell_xml += (
                "<w:tc><w:tcPr>"
                '<w:tcW w:w="2400" w:type="dxa"/>'
                f"{fill}"
                "</w:tcPr>"
                f"{_paragraph(_parse_inline(cell), style='TableHeader' if row_index == 0 else 'TableCell')}"
                "</w:tc>"
            )
        rows.append(f"<w:tr>{cell_xml}</w:tr>")
        row_index += 1
    if not rows:
        return ""
    return (
        "<w:tbl>"
        "<w:tblPr>"
        '<w:tblStyle w:val="TableGrid"/>'
        '<w:tblW w:w="0" w:type="auto"/>'
        '<w:tblCellMar><w:top w:w="80" w:type="dxa"/><w:left w:w="80" w:type="dxa"/>'
        '<w:bottom w:w="80" w:type="dxa"/><w:right w:w="80" w:type="dxa"/></w:tblCellMar>'
        "</w:tblPr>"
        f"{''.join(rows)}"
        "</w:tbl>"
    )


def _document_xml(body: str) -> str:
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    {body}
    <w:sectPr>
      <w:pgSz w:w="11906" w:h="16838"/>
      <w:pgMar w:top="850" w:right="900" w:bottom="850" w:left="900" w:header="450" w:footer="450" w:gutter="0"/>
    </w:sectPr>
  </w:body>
</w:document>
"""


CONTENT_TYPES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
  <Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
</Types>
"""

RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>
"""

DOCUMENT_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"/>
"""

STYLES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:style w:type="paragraph" w:default="1" w:styleId="Body">
    <w:name w:val="Body"/>
    <w:pPr><w:spacing w:after="90" w:line="310" w:lineRule="auto"/></w:pPr>
    <w:rPr><w:rFonts w:ascii="Malgun Gothic" w:hAnsi="Malgun Gothic" w:eastAsia="Malgun Gothic"/><w:sz w:val="21"/><w:color w:val="111827"/></w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Normal">
    <w:name w:val="Normal"/>
    <w:basedOn w:val="Body"/>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Title">
    <w:name w:val="Title"/>
    <w:pPr><w:spacing w:after="80"/></w:pPr>
    <w:rPr><w:rFonts w:ascii="Malgun Gothic" w:hAnsi="Malgun Gothic" w:eastAsia="Malgun Gothic"/><w:b/><w:sz w:val="34"/><w:color w:val="0B1F3A"/></w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Subtitle">
    <w:name w:val="Subtitle"/>
    <w:pPr><w:spacing w:after="300"/></w:pPr>
    <w:rPr><w:rFonts w:ascii="Malgun Gothic" w:hAnsi="Malgun Gothic" w:eastAsia="Malgun Gothic"/><w:sz w:val="19"/><w:color w:val="6B7280"/></w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Heading1">
    <w:name w:val="Heading 1"/>
    <w:pPr><w:spacing w:before="280" w:after="150"/></w:pPr>
    <w:rPr><w:rFonts w:ascii="Malgun Gothic" w:hAnsi="Malgun Gothic" w:eastAsia="Malgun Gothic"/><w:b/><w:sz w:val="27"/><w:color w:val="0B1F3A"/></w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Heading2">
    <w:name w:val="Heading 2"/>
    <w:pPr><w:spacing w:before="220" w:after="110"/></w:pPr>
    <w:rPr><w:rFonts w:ascii="Malgun Gothic" w:hAnsi="Malgun Gothic" w:eastAsia="Malgun Gothic"/><w:b/><w:sz w:val="23"/><w:color w:val="111827"/></w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="TrendTitle">
    <w:name w:val="Trend Title"/>
    <w:pPr><w:spacing w:before="260" w:after="130"/></w:pPr>
    <w:rPr><w:rFonts w:ascii="Malgun Gothic" w:hAnsi="Malgun Gothic" w:eastAsia="Malgun Gothic"/><w:b/><w:sz w:val="23"/><w:color w:val="000000"/></w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Label">
    <w:name w:val="Label"/>
    <w:pPr><w:spacing w:before="150" w:after="70"/></w:pPr>
    <w:rPr><w:rFonts w:ascii="Malgun Gothic" w:hAnsi="Malgun Gothic" w:eastAsia="Malgun Gothic"/><w:b/><w:sz w:val="20"/><w:color w:val="000000"/></w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Bullet">
    <w:name w:val="Bullet"/>
    <w:pPr><w:ind w:left="360" w:hanging="220"/><w:spacing w:after="70" w:line="300" w:lineRule="auto"/></w:pPr>
    <w:rPr><w:rFonts w:ascii="Malgun Gothic" w:hAnsi="Malgun Gothic" w:eastAsia="Malgun Gothic"/><w:sz w:val="21"/><w:color w:val="111827"/></w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Numbered">
    <w:name w:val="Numbered"/>
    <w:pPr><w:ind w:left="360" w:hanging="260"/><w:spacing w:after="60" w:line="300" w:lineRule="auto"/></w:pPr>
    <w:rPr><w:rFonts w:ascii="Malgun Gothic" w:hAnsi="Malgun Gothic" w:eastAsia="Malgun Gothic"/><w:sz w:val="21"/><w:color w:val="111827"/></w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Quote">
    <w:name w:val="Quote"/>
    <w:pPr><w:ind w:left="260"/><w:spacing w:before="80" w:after="100"/></w:pPr>
    <w:rPr><w:rFonts w:ascii="Malgun Gothic" w:hAnsi="Malgun Gothic" w:eastAsia="Malgun Gothic"/><w:i/><w:sz w:val="20"/><w:color w:val="4B5563"/></w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="TableHeader">
    <w:name w:val="Table Header"/>
    <w:pPr><w:spacing w:after="40"/></w:pPr>
    <w:rPr><w:rFonts w:ascii="Malgun Gothic" w:hAnsi="Malgun Gothic" w:eastAsia="Malgun Gothic"/><w:b/><w:sz w:val="17"/><w:color w:val="0B1F3A"/></w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="TableCell">
    <w:name w:val="Table Cell"/>
    <w:pPr><w:spacing w:after="30"/></w:pPr>
    <w:rPr><w:rFonts w:ascii="Malgun Gothic" w:hAnsi="Malgun Gothic" w:eastAsia="Malgun Gothic"/><w:sz w:val="16"/><w:color w:val="111827"/></w:rPr>
  </w:style>
</w:styles>
"""

