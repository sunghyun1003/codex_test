from __future__ import annotations

import html
import json
import re
from pathlib import Path


def markdown_to_full_report_html(markdown: str, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    image_prompts = _extract_image_prompts(markdown)
    report_markdown = re.split(r"\n## IMAGE_PROMPTS_JSON\b", markdown, maxsplit=1)[0]
    content = _markdown_body_to_html(report_markdown)
    prompts = _image_prompt_cards(image_prompts)
    document = HTML_TEMPLATE.replace("{{REPORT_CONTENT}}", content).replace("{{IMAGE_PROMPTS}}", prompts)
    output_path.write_text(document, encoding="utf-8")
    return output_path


def _markdown_body_to_html(markdown: str) -> str:
    lines = markdown.splitlines()
    parts: list[str] = []
    index = 0

    while index < len(lines):
        line = lines[index].rstrip()
        stripped = line.strip()
        if not stripped:
            index += 1
            continue
        if stripped.startswith("```"):
            index = _skip_code_block(lines, index)
            continue
        if stripped == "---":
            parts.append("<hr />")
            index += 1
            continue
        if stripped.startswith("|") and index + 1 < len(lines) and lines[index + 1].strip().startswith("|"):
            table_lines: list[str] = []
            while index < len(lines) and lines[index].strip().startswith("|"):
                table_lines.append(lines[index].strip())
                index += 1
            parts.append(_table_to_html(table_lines))
            continue
        if stripped.startswith("#"):
            level = min(len(stripped) - len(stripped.lstrip("#")), 4)
            text = stripped.lstrip("#").strip()
            parts.append(f'<h{level}>{_inline(text)}</h{level}>')
            index += 1
            continue
        if stripped.startswith(">"):
            parts.append(f'<blockquote>{_inline(stripped.lstrip("> ").strip())}</blockquote>')
            index += 1
            continue
        if stripped.startswith("- "):
            bullets: list[str] = []
            while index < len(lines) and lines[index].strip().startswith("- "):
                bullets.append(lines[index].strip()[2:].strip())
                index += 1
            parts.append("<ul>" + "".join(f"<li>{_inline(item)}</li>" for item in bullets) + "</ul>")
            continue
        if re.match(r"^\d+[.)]\s+", stripped):
            nums: list[str] = []
            while index < len(lines) and re.match(r"^\d+[.)]\s+", lines[index].strip()):
                nums.append(re.sub(r"^\d+[.)]\s+", "", lines[index].strip()))
                index += 1
            parts.append("<ol>" + "".join(f"<li>{_inline(item)}</li>" for item in nums) + "</ol>")
            continue

        parts.append(f"<p>{_inline(stripped)}</p>")
        index += 1

    return "\n".join(parts)


def _skip_code_block(lines: list[str], index: int) -> int:
    index += 1
    while index < len(lines) and not lines[index].startswith("```"):
        index += 1
    return index + 1


def _table_to_html(lines: list[str]) -> str:
    rows = []
    for line in lines:
        if re.match(r"^\|\s*-", line):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        tag = "th" if not rows else "td"
        rows.append("<tr>" + "".join(f"<{tag}>{_inline(cell)}</{tag}>" for cell in cells) + "</tr>")
    return '<div class="table-wrap"><table>' + "".join(rows) + "</table></div>"


def _extract_image_prompts(markdown: str) -> list[dict[str, str]]:
    match = re.search(
        r"## IMAGE_PROMPTS_JSON\s*```json\s*(.*?)\s*```",
        markdown,
        flags=re.DOTALL | re.IGNORECASE,
    )
    if not match:
        return []
    try:
        raw = json.loads(match.group(1))
    except json.JSONDecodeError:
        return []
    return [item for item in raw if isinstance(item, dict)]


def _image_prompt_cards(prompts: list[dict[str, str]]) -> str:
    if not prompts:
        return '<p class="empty">이미지 생성 프롬프트가 없습니다.</p>'
    cards = []
    for index, item in enumerate(prompts, start=1):
        concept = html.escape(str(item.get("concept", f"Concept {index}")))
        main_copy = html.escape(str(item.get("main_copy", "")))
        sub_copy = html.escape(str(item.get("sub_copy", "")))
        cta = html.escape(str(item.get("cta", "")))
        prompt = html.escape(str(item.get("prompt", "")))
        cards.append(
            f"""
            <article class="prompt-card">
              <div class="prompt-meta">Prompt {index}</div>
              <h3>{concept}</h3>
              <div class="copy-grid">
                <div><span>Main</span><strong>{main_copy}</strong></div>
                <div><span>Sub</span><strong>{sub_copy or "-"}</strong></div>
                <div><span>CTA</span><strong>{cta}</strong></div>
              </div>
              <pre>{prompt}</pre>
            </article>
            """
        )
    return "\n".join(cards)


def _inline(text: str) -> str:
    escaped = html.escape(text)
    escaped = re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", escaped)
    escaped = re.sub(r"`([^`]+)`", r"<code>\1</code>", escaped)
    return escaped


HTML_TEMPLATE = """<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Weekly Trend Full Report</title>
  <style>
    :root {
      --bg: #f4f7fb;
      --paper: #ffffff;
      --ink: #111827;
      --muted: #667085;
      --line: #e4e7ec;
      --blue: #2563eb;
      --blue-deep: #0f2f63;
      --blue-soft: #eef4ff;
      --green-soft: #ecfdf3;
      --yellow-soft: #fffaeb;
      --shadow: 0 16px 42px rgba(15, 23, 42, 0.08);
    }

    * { box-sizing: border-box; }
    body {
      margin: 0;
      background: var(--bg);
      color: var(--ink);
      font-family: "Malgun Gothic", "Apple SD Gothic Neo", "Noto Sans KR", Arial, sans-serif;
      line-height: 1.72;
    }
    .page {
      max-width: 1120px;
      margin: 0 auto;
      padding: 42px 28px 76px;
    }
    .hero {
      background: linear-gradient(135deg, #0f2f63 0%, #2563eb 62%, #14b8a6 100%);
      color: white;
      border-radius: 28px;
      padding: 42px;
      box-shadow: var(--shadow);
    }
    .eyebrow {
      font-size: 13px;
      letter-spacing: .08em;
      text-transform: uppercase;
      font-weight: 800;
      opacity: .84;
    }
    h1 {
      margin: 10px 0 12px;
      font-size: 36px;
      line-height: 1.25;
      letter-spacing: 0;
    }
    .hero p {
      margin: 0;
      max-width: 760px;
      color: rgba(255,255,255,.9);
      font-size: 15px;
    }
    .summary-bar {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 14px;
      margin: 22px 0;
    }
    .metric {
      background: var(--paper);
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 16px 18px;
      box-shadow: 0 8px 24px rgba(15,23,42,.045);
    }
    .metric strong {
      display: block;
      color: var(--blue-deep);
      font-size: 22px;
      line-height: 1.2;
    }
    .metric span {
      display: block;
      color: var(--muted);
      font-size: 13px;
      margin-top: 4px;
    }
    .content, .manual-prompts {
      background: var(--paper);
      border: 1px solid var(--line);
      border-radius: 24px;
      box-shadow: var(--shadow);
      padding: 34px 38px;
      margin-top: 22px;
    }
    h2 {
      margin: 34px 0 14px;
      font-size: 24px;
      line-height: 1.35;
      color: #000;
      border-top: 1px solid var(--line);
      padding-top: 28px;
    }
    h2:first-child {
      border-top: 0;
      padding-top: 0;
      margin-top: 0;
    }
    h3 {
      margin: 24px 0 10px;
      font-size: 18px;
      line-height: 1.45;
      color: #101828;
    }
    h4 {
      margin: 20px 0 8px;
      font-size: 15px;
      color: #101828;
    }
    p { margin: 9px 0; }
    strong { font-weight: 800; }
    code {
      background: var(--blue-soft);
      border-radius: 6px;
      padding: 1px 5px;
      font-family: inherit;
      color: var(--blue-deep);
    }
    blockquote {
      margin: 18px 0;
      padding: 16px 18px;
      border-left: 5px solid var(--blue);
      background: var(--blue-soft);
      border-radius: 14px;
      color: #344054;
    }
    ul, ol {
      margin: 8px 0 16px;
      padding-left: 23px;
    }
    li { margin: 6px 0; }
    hr {
      border: 0;
      border-top: 1px solid var(--line);
      margin: 28px 0;
    }
    .table-wrap {
      overflow-x: auto;
      border: 1px solid var(--line);
      border-radius: 16px;
      margin: 16px 0 24px;
    }
    table {
      width: 100%;
      border-collapse: collapse;
      min-width: 760px;
      font-size: 13px;
      background: white;
    }
    th, td {
      border-bottom: 1px solid var(--line);
      border-right: 1px solid var(--line);
      padding: 10px 12px;
      vertical-align: top;
      text-align: left;
    }
    th {
      background: var(--blue-soft);
      color: var(--blue-deep);
      font-weight: 800;
    }
    tr:last-child td { border-bottom: 0; }
    th:last-child, td:last-child { border-right: 0; }
    .manual-prompts { background: #fbfcff; }
    .manual-prompts > h2 {
      border-top: 0;
      padding-top: 0;
      margin-top: 0;
    }
    .prompt-card {
      border: 1px solid var(--line);
      border-radius: 20px;
      background: white;
      padding: 22px;
      margin-top: 18px;
    }
    .prompt-meta {
      display: inline-flex;
      align-items: center;
      height: 26px;
      border-radius: 999px;
      padding: 0 10px;
      background: var(--green-soft);
      color: #027a48;
      font-size: 12px;
      font-weight: 800;
    }
    .copy-grid {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 10px;
      margin: 14px 0;
    }
    .copy-grid div {
      border-radius: 14px;
      background: var(--yellow-soft);
      padding: 12px;
    }
    .copy-grid span {
      display: block;
      font-size: 11px;
      color: var(--muted);
      text-transform: uppercase;
      font-weight: 800;
      margin-bottom: 4px;
    }
    .copy-grid strong { font-size: 14px; }
    pre {
      white-space: pre-wrap;
      word-break: break-word;
      margin: 14px 0 0;
      padding: 16px;
      background: #0b1220;
      color: #e5e7eb;
      border-radius: 16px;
      font-family: Consolas, "Courier New", monospace;
      font-size: 12.5px;
      line-height: 1.6;
    }
    .empty { color: var(--muted); }
    @media (max-width: 820px) {
      .page { padding: 20px 14px 48px; }
      .hero, .content, .manual-prompts { border-radius: 22px; padding: 24px 20px; }
      h1 { font-size: 28px; }
      .summary-bar, .copy-grid { grid-template-columns: 1fr; }
      table { min-width: 680px; }
    }
    @media print {
      body { background: white; }
      .page { max-width: none; padding: 0; }
      .hero, .metric, .content, .manual-prompts, .prompt-card { box-shadow: none; }
      .prompt-card, h2, h3 { break-inside: avoid; }
    }
  </style>
</head>
<body>
  <main class="page">
    <section class="hero">
      <div class="eyebrow">Weekly Trend Report</div>
      <h1>전체 트렌드 리포트</h1>
      <p>최근 7일 국내 트렌드 신호를 수집하고, 자동차보험 광고 콘셉트와 이미지 생성 프롬프트까지 정리한 HTML 리포트입니다.</p>
    </section>

    <section class="summary-bar" aria-label="report summary">
      <div class="metric"><strong>7일</strong><span>분석 기준 기간</span></div>
      <div class="metric"><strong>TOP 7</strong><span>트렌드 후보 선정</span></div>
      <div class="metric"><strong>5개</strong><span>광고 콘셉트</span></div>
      <div class="metric"><strong>프롬프트</strong><span>배너 제작 참고</span></div>
    </section>

    <section class="content">
      {{REPORT_CONTENT}}
    </section>

    <section class="manual-prompts">
      <h2>수동 이미지 생성 프롬프트</h2>
      <p>아래 프롬프트를 ChatGPT 이미지 생성 화면에 붙여 넣어 배너 이미지 제작에 활용하세요.</p>
      {{IMAGE_PROMPTS}}
    </section>
  </main>
</body>
</html>
"""
