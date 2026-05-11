from __future__ import annotations

import html
from pathlib import Path

from .executive_docx import CoreTrend, parse_core_trends


def markdown_to_executive_html(markdown: str, output_path: Path) -> Path:
    trends = parse_core_trends(markdown)
    if not trends:
        raise ValueError("No Core Trend TOP 5 section could be parsed.")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    cards = "\n".join(_trend_card(trend) for trend in trends[:5])
    document = HTML_TEMPLATE.replace("{{CARDS}}", cards)
    output_path.write_text(document, encoding="utf-8")
    return output_path


def _trend_card(trend: CoreTrend) -> str:
    reasons = "".join(f"<li>{_e(reason)}</li>" for reason in trend.reasons[:3])
    implications = "".join(f"<li>{_e(item)}</li>" for item in trend.implications[:2])
    return f"""
    <article class="trend-card">
      <div class="trend-head">
        <span class="rank">{trend.rank}</span>
        <div>
          <h2>{_e(trend.title)}</h2>
          <p class="definition">{_e(trend.definition)}</p>
        </div>
      </div>

      <section class="block">
        <h3>왜 뜨는가</h3>
        <ol>{reasons}</ol>
      </section>

      <div class="two-col">
        <section class="block soft">
          <h3>등장 채널</h3>
          <p>{_e(trend.channels)}</p>
        </section>
        <section class="block soft">
          <h3>소비자 심리</h3>
          <p>{_e(trend.psychology)}</p>
        </section>
      </div>

      <section class="block">
        <h3>비즈니스 시사점</h3>
        <ul>{implications}</ul>
      </section>
    </article>
    """


def _e(value: str) -> str:
    return html.escape(value or "-")


HTML_TEMPLATE = """<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Core Trend TOP 5</title>
  <style>
    :root {
      --ink: #141414;
      --muted: #667085;
      --line: #e4e7ec;
      --paper: #ffffff;
      --bg: #f5f7fb;
      --blue: #1f5eff;
      --blue-deep: #173b82;
      --blue-soft: #eef4ff;
      --green-soft: #eefaf4;
      --shadow: 0 14px 40px rgba(15, 23, 42, 0.08);
    }

    * { box-sizing: border-box; }

    body {
      margin: 0;
      background: var(--bg);
      color: var(--ink);
      font-family: "Malgun Gothic", "Apple SD Gothic Neo", "Noto Sans KR", Arial, sans-serif;
      line-height: 1.68;
    }

    .page {
      max-width: 980px;
      margin: 0 auto;
      padding: 42px 28px 72px;
    }

    .hero {
      background: linear-gradient(135deg, #0f2f6f 0%, #1f5eff 58%, #5cc8ff 100%);
      color: #fff;
      border-radius: 28px;
      padding: 38px 42px;
      box-shadow: var(--shadow);
      margin-bottom: 26px;
      position: relative;
      overflow: hidden;
    }

    .hero::after {
      content: "";
      position: absolute;
      right: -90px;
      top: -110px;
      width: 280px;
      height: 280px;
      border-radius: 50%;
      background: rgba(255,255,255,0.18);
    }

    .eyebrow {
      font-size: 13px;
      letter-spacing: .08em;
      text-transform: uppercase;
      opacity: .82;
      font-weight: 700;
      margin-bottom: 8px;
    }

    h1 {
      margin: 0;
      font-size: 34px;
      line-height: 1.25;
      letter-spacing: 0;
    }

    .hero p {
      margin: 14px 0 0;
      max-width: 680px;
      color: rgba(255,255,255,0.86);
      font-size: 15px;
    }

    .summary-bar {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 14px;
      margin: 0 0 24px;
    }

    .metric {
      background: var(--paper);
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 16px 18px;
      box-shadow: 0 8px 24px rgba(15, 23, 42, 0.04);
    }

    .metric strong {
      display: block;
      font-size: 22px;
      color: var(--blue-deep);
      line-height: 1.2;
    }

    .metric span {
      display: block;
      color: var(--muted);
      font-size: 13px;
      margin-top: 4px;
    }

    .trend-card {
      background: var(--paper);
      border: 1px solid var(--line);
      border-radius: 24px;
      padding: 30px 32px;
      box-shadow: var(--shadow);
      margin-top: 22px;
    }

    .trend-head {
      display: grid;
      grid-template-columns: 54px 1fr;
      gap: 18px;
      align-items: start;
      padding-bottom: 20px;
      border-bottom: 1px solid var(--line);
    }

    .rank {
      width: 48px;
      height: 48px;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      border-radius: 16px;
      background: var(--blue);
      color: #fff;
      font-size: 22px;
      font-weight: 800;
    }

    h2 {
      margin: 2px 0 8px;
      font-size: 22px;
      line-height: 1.38;
      letter-spacing: 0;
    }

    .definition {
      margin: 0;
      font-size: 15px;
      color: #2f3542;
    }

    .block {
      margin-top: 22px;
    }

    .block h3 {
      margin: 0 0 10px;
      font-size: 15px;
      font-weight: 800;
      color: #000;
      display: inline-flex;
      align-items: center;
      gap: 8px;
    }

    .block h3::before {
      content: "";
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: var(--blue);
    }

    ol, ul {
      margin: 0;
      padding-left: 22px;
    }

    li {
      margin: 7px 0;
      font-size: 14.5px;
    }

    .two-col {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 14px;
      margin-top: 22px;
    }

    .soft {
      border-radius: 18px;
      background: var(--blue-soft);
      padding: 18px;
      margin-top: 0;
    }

    .soft:nth-child(2) {
      background: var(--green-soft);
    }

    .soft p {
      margin: 0;
      font-size: 14px;
      color: #344054;
    }

    @media print {
      body { background: #fff; }
      .page { max-width: none; padding: 0; }
      .trend-card, .hero, .metric { box-shadow: none; break-inside: avoid; }
      .trend-card { page-break-inside: avoid; }
    }

    @media (max-width: 720px) {
      .page { padding: 22px 14px 48px; }
      .hero { padding: 28px 24px; border-radius: 22px; }
      h1 { font-size: 27px; }
      .summary-bar, .two-col { grid-template-columns: 1fr; }
      .trend-card { padding: 24px 20px; border-radius: 20px; }
      .trend-head { grid-template-columns: 44px 1fr; gap: 14px; }
      .rank { width: 42px; height: 42px; font-size: 19px; }
    }
  </style>
</head>
<body>
  <main class="page">
    <section class="hero">
      <div class="eyebrow">Weekly Trend Report</div>
      <h1>Core Trend TOP 5</h1>
      <p>최근 7일 국내 트렌드 신호를 바탕으로 광고 제작과 자동차보험 메시지에 바로 연결할 수 있는 핵심 흐름만 정리했습니다.</p>
    </section>

    <section class="summary-bar" aria-label="report summary">
      <div class="metric"><strong>5</strong><span>핵심 트렌드</span></div>
      <div class="metric"><strong>7일</strong><span>분석 기준 기간</span></div>
      <div class="metric"><strong>SNS</strong><span>배너 제작 관점</span></div>
    </section>

    {{CARDS}}
  </main>
</body>
</html>
"""

