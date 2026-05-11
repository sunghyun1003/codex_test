from __future__ import annotations

import html
import re
import zipfile
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class CoreTrend:
    rank: int
    title: str
    definition: str = ""
    reasons: list[str] = field(default_factory=list)
    channels: str = ""
    psychology: str = ""
    implications: list[str] = field(default_factory=list)


def markdown_to_executive_docx(markdown: str, output_path: Path) -> Path:
    trends = parse_core_trends(markdown)
    if not trends:
        raise ValueError("No Core Trend TOP 5 section could be parsed.")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    body = [
        _p([_r("Core Trend TOP 5", bold=True)], style="DocTitle"),
        _p([_r("최근 7일 국내 트렌드 기반 핵심 요약 리포트")], style="DocSubtitle"),
    ]

    for index, trend in enumerate(trends[:5]):
        if index:
            body.append(_divider())
        body.append(_p([_r(f"{trend.rank}) {trend.title}", bold=True)], style="TrendTitle"))
        if trend.definition:
            body.append(_p(_inline(trend.definition), style="Body"))
        if trend.reasons:
            body.append(_p([_r("왜 뜨는가", bold=True)], style="SectionLabel"))
            for number, reason in enumerate(trend.reasons, start=1):
                body.append(_p([_r(f"{number}. ", bold=True), *_inline(reason)], style="Numbered"))
        if trend.channels:
            body.append(_p([_r("등장 채널", bold=True)], style="SectionLabel"))
            body.append(_p(_inline(trend.channels), style="Body"))
        if trend.psychology:
            body.append(_p([_r("소비자 심리", bold=True)], style="SectionLabel"))
            body.append(_p(_inline(trend.psychology), style="Body"))
        if trend.implications:
            body.append(_p([_r("비즈니스 시사점", bold=True)], style="SectionLabel"))
            for implication in trend.implications:
                body.append(_p([_r("• ", bold=True), *_inline(implication)], style="Bullet"))

    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as package:
        package.writestr("[Content_Types].xml", CONTENT_TYPES)
        package.writestr("_rels/.rels", RELS)
        package.writestr("word/document.xml", _document_xml("".join(body)))
        package.writestr("word/styles.xml", STYLES)
        package.writestr("word/_rels/document.xml.rels", DOCUMENT_RELS)
    return output_path


def parse_core_trends(markdown: str) -> list[CoreTrend]:
    start = markdown.find("### Core 1")
    end = markdown.find("## 5)", start)
    if start == -1:
        return []
    section = markdown[start : end if end != -1 else len(markdown)]
    chunks = re.split(r"\n---\s*\n", section)
    trends: list[CoreTrend] = []

    for chunk in chunks:
        header = re.search(r"###\s*Core\s*(\d+)\)\s*(.+)", chunk)
        if not header:
            continue
        trend = CoreTrend(rank=int(header.group(1)), title=_strip_inline(header.group(2)))
        trend.definition = _field(chunk, "정의")
        trend.reasons = _numbered_after_label(chunk, "왜 오르나")
        trend.channels = _field(chunk, "어디서 보이나")
        trend.psychology = _field(chunk, "소비자 심리")
        trend.implications = _bullets_after_label(chunk, "비즈니스/광고 시사점")
        trends.append(trend)
    return trends


def _field(chunk: str, label: str) -> str:
    pattern = rf"- \*\*{re.escape(label)}(?:\([^)]*\))?:\*\*\s*(.+)"
    match = re.search(pattern, chunk)
    return _strip_inline(match.group(1)) if match else ""


def _numbered_after_label(chunk: str, label: str) -> list[str]:
    block = _block_after_label(chunk, label)
    return [_strip_inline(item) for item in re.findall(r"^\s*\d+\)\s*(.+)", block, flags=re.MULTILINE)]


def _bullets_after_label(chunk: str, label: str) -> list[str]:
    block = _block_after_label(chunk, label)
    return [_strip_inline(item) for item in re.findall(r"^\s*-\s+(.+)", block, flags=re.MULTILINE)]


def _block_after_label(chunk: str, label: str) -> str:
    pattern = rf"- \*\*{re.escape(label)}(?:\([^)]*\))?:\*\*:?([\s\S]*?)(?=\n- \*\*|\n---|\Z)"
    match = re.search(pattern, chunk)
    return match.group(1) if match else ""


def _strip_inline(text: str) -> str:
    text = text.replace("  ", " ")
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    return text.strip()


def _inline(text: str) -> list[dict[str, object]]:
    runs: list[dict[str, object]] = []
    cursor = 0
    for match in re.finditer(r"\*\*(.*?)\*\*", text):
        if match.start() > cursor:
            runs.append(_r(text[cursor : match.start()]))
        runs.append(_r(match.group(1), bold=True))
        cursor = match.end()
    if cursor < len(text):
        runs.append(_r(text[cursor:]))
    return runs or [_r("")]


def _r(text: str, *, bold: bool = False) -> dict[str, object]:
    return {"text": text, "bold": bold}


def _p(runs: list[dict[str, object]], style: str) -> str:
    return (
        "<w:p>"
        f'<w:pPr><w:pStyle w:val="{style}"/></w:pPr>'
        f"{''.join(_run(run) for run in runs)}"
        "</w:p>"
    )


def _run(run: dict[str, object]) -> str:
    bold_xml = "<w:b/>" if run.get("bold") else ""
    return (
        "<w:r>"
        f"<w:rPr>{bold_xml}</w:rPr>"
        f"<w:t xml:space=\"preserve\">{html.escape(str(run.get('text', '')))}</w:t>"
        "</w:r>"
    )


def _divider() -> str:
    return (
        "<w:p><w:pPr><w:spacing w:before=\"260\" w:after=\"220\"/>"
        "<w:pBdr>"
        '<w:bottom w:val="single" w:sz="6" w:space="1" w:color="D9D9D9"/>'
        "</w:pBdr></w:pPr></w:p>"
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
    <w:pPr><w:spacing w:after="115" w:line="330" w:lineRule="auto"/></w:pPr>
    <w:rPr><w:rFonts w:ascii="Malgun Gothic" w:hAnsi="Malgun Gothic" w:eastAsia="Malgun Gothic"/><w:sz w:val="22"/><w:color w:val="111111"/></w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Normal"><w:name w:val="Normal"/><w:basedOn w:val="Body"/></w:style>
  <w:style w:type="paragraph" w:styleId="DocTitle">
    <w:name w:val="Doc Title"/>
    <w:pPr><w:spacing w:after="220"/></w:pPr>
    <w:rPr><w:rFonts w:ascii="Malgun Gothic" w:hAnsi="Malgun Gothic" w:eastAsia="Malgun Gothic"/><w:b/><w:sz w:val="31"/><w:color w:val="000000"/></w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="DocSubtitle">
    <w:name w:val="Doc Subtitle"/>
    <w:pPr><w:spacing w:after="340"/></w:pPr>
    <w:rPr><w:rFonts w:ascii="Malgun Gothic" w:hAnsi="Malgun Gothic" w:eastAsia="Malgun Gothic"/><w:sz w:val="19"/><w:color w:val="666666"/></w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="TrendTitle">
    <w:name w:val="Trend Title"/>
    <w:pPr><w:spacing w:before="130" w:after="135"/></w:pPr>
    <w:rPr><w:rFonts w:ascii="Malgun Gothic" w:hAnsi="Malgun Gothic" w:eastAsia="Malgun Gothic"/><w:b/><w:sz w:val="24"/><w:color w:val="000000"/></w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="SectionLabel">
    <w:name w:val="Section Label"/>
    <w:pPr><w:spacing w:before="190" w:after="85"/></w:pPr>
    <w:rPr><w:rFonts w:ascii="Malgun Gothic" w:hAnsi="Malgun Gothic" w:eastAsia="Malgun Gothic"/><w:b/><w:sz w:val="20"/><w:color w:val="000000"/></w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Numbered">
    <w:name w:val="Numbered"/>
    <w:pPr><w:ind w:left="260" w:hanging="240"/><w:spacing w:after="55" w:line="310" w:lineRule="auto"/></w:pPr>
    <w:rPr><w:rFonts w:ascii="Malgun Gothic" w:hAnsi="Malgun Gothic" w:eastAsia="Malgun Gothic"/><w:sz w:val="21"/><w:color w:val="111111"/></w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Bullet">
    <w:name w:val="Bullet"/>
    <w:pPr><w:ind w:left="310" w:hanging="220"/><w:spacing w:after="65" w:line="310" w:lineRule="auto"/></w:pPr>
    <w:rPr><w:rFonts w:ascii="Malgun Gothic" w:hAnsi="Malgun Gothic" w:eastAsia="Malgun Gothic"/><w:sz w:val="21"/><w:color w:val="111111"/></w:rPr>
  </w:style>
</w:styles>
"""

