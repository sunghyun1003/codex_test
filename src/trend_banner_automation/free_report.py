from __future__ import annotations

import json
import math
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime

from .sources import SourceItem


STOPWORDS = {
    "그리고",
    "그러나",
    "대한",
    "관련",
    "이번",
    "최근",
    "오늘",
    "어제",
    "내일",
    "국내",
    "한국",
    "뉴스",
    "단독",
    "영상",
    "공개",
    "발표",
    "기자",
    "있다",
    "했다",
    "한다",
    "하는",
    "위해",
    "통해",
    "대해",
    "에서",
    "으로",
    "에게",
    "까지",
    "부터",
    "보다",
    "검색",
    "추이",
}

PRACTICAL_TERMS = {
    "자동차",
    "자동차보험",
    "운전",
    "차량",
    "안전",
    "생활",
    "소비",
    "가족",
    "여행",
    "출퇴근",
    "모바일",
    "AI",
    "체크",
    "관리",
    "초보운전",
}


@dataclass
class TrendCandidate:
    keyword: str
    count: int
    channels: set[str] = field(default_factory=set)
    related: Counter[str] = field(default_factory=Counter)
    examples: list[SourceItem] = field(default_factory=list)
    repetition: int = 0
    recency: int = 0
    diffusion: int = 0
    practicality: int = 0

    @property
    def total(self) -> int:
        return self.repetition + self.recency + self.diffusion + self.practicality

    @property
    def channel_label(self) -> str:
        labels = {
            "initial": "초기 신호",
            "diffusion": "확산 신호",
            "validation": "검증 신호",
        }
        return ", ".join(labels.get(channel, channel) for channel in sorted(self.channels))


def build_free_report(
    *,
    items: list[SourceItem],
    source_errors: list[str],
    source_brief: str,
    started_at: datetime,
) -> str:
    candidates = build_candidates(items)
    selected = candidates[:7]
    core = selected[:5]
    image_prompts = build_image_prompts(core)

    lines: list[str] = [
        "# Weekly Trend Report",
        "",
        f"> 기준 시각: {started_at.strftime('%Y-%m-%d %H:%M')} KST",
        "> 생성 방식: OpenAI API를 사용하지 않는 무료 규칙 기반 리포트",
        "",
        "## 1) Trend Discovery",
        "",
        "최근 7일 수집 데이터를 초기 신호, 확산 신호, 검증 신호로 나누어 반복 키워드를 추출했습니다.",
        "",
        "| 채널 | 수집 건수 | 주요 키워드 |",
        "|---|---:|---|",
    ]
    for channel, label in [
        ("initial", "초기 신호"),
        ("diffusion", "확산 신호"),
        ("validation", "검증 신호"),
    ]:
        channel_items = [item for item in items if item.channel == channel]
        keywords = top_keywords(channel_items, limit=12)
        lines.append(f"| {label} | {len(channel_items)} | {', '.join(keywords) or '-'} |")

    if source_errors:
        lines.extend(["", "### Source Access Notes", ""])
        lines.extend(f"- {error}" for error in source_errors)

    lines.extend(
        [
            "",
            "## 2) Trend Candidates",
            "",
            "| 후보 | 등장 채널 | 관련 키워드 | 설명 |",
            "|---|---|---|---|",
        ]
    )
    for candidate in candidates[:20]:
        related = ", ".join(keyword for keyword, _ in candidate.related.most_common(6))
        explanation = make_candidate_explanation(candidate)
        lines.append(
            f"| {candidate.keyword} | {candidate.channel_label} | {related or '-'} | {explanation} |"
        )

    lines.extend(
        [
            "",
            "## 3) Trend Scoring and Selection",
            "",
            "| 순위 | 트렌드 | 반복성 | 최신성 | 확산성 | 실무 활용성 | 총점 |",
            "|---:|---|---:|---:|---:|---:|---:|",
        ]
    )
    for rank, candidate in enumerate(selected, start=1):
        lines.append(
            "| "
            f"{rank} | {candidate.keyword} | {candidate.repetition} | {candidate.recency} | "
            f"{candidate.diffusion} | {candidate.practicality} | {candidate.total} |"
        )

    lines.extend(["", "## 4) Weekly Trend Report", "", "### Core Trend TOP 5", ""])
    for rank, candidate in enumerate(core, start=1):
        examples = candidate.examples[:3]
        lines.extend(
            [
                f"### Core {rank}) {trend_name(candidate)}",
                "",
                f"- **정의:** {candidate.keyword} 관련 신호가 여러 채널에서 반복되며 생활/소비/콘텐츠 소재로 확장되는 흐름입니다.",
                "- **왜 뜨는가:**",
                f"  1. 최근 7일 데이터에서 `{candidate.keyword}` 키워드가 {candidate.count}회 이상 반복 등장했습니다.",
                f"  2. 등장 채널이 {len(candidate.channels)}개로, 단일 뉴스보다 확산 가능성이 높습니다.",
                f"  3. {business_bridge(candidate)}",
                f"- **어디에 보이는가:** {candidate.channel_label}",
                "- **대표 출처:**",
            ]
        )
        if examples:
            for example in examples:
                lines.append(f"  - {example.source}: {example.title}")
        else:
            lines.append("  - 수집된 대표 출처가 부족합니다.")
        lines.extend(
            [
                "- **비즈니스 시사점:**",
                f"  - 자동차보험 광고에서는 `{candidate.keyword}`를 직접 판매 문구보다 생활 속 점검 맥락으로 연결하는 편이 자연스럽습니다.",
                "  - 모바일 배너는 한 문장 메시지, 체크리스트형 구성, 명확한 CTA로 전환 부담을 낮추는 방향이 적합합니다.",
                "",
                "---",
                "",
            ]
        )

    lines.extend(
        [
            "### 공통 패턴 3가지",
            "",
            "1. **변화 방향:** 단순 유행어보다 생활 루틴, 안전 확인, 빠른 의사결정처럼 바로 행동으로 옮길 수 있는 소재가 강합니다.",
            "2. **사용자 심리:** 사용자는 복잡한 설명보다 지금 내 상황에 맞는지 빠르게 확인하고 싶어합니다.",
            "3. **시장/콘텐츠 변화:** 숏폼과 검색 신호가 결합되면서 짧고 구체적인 문장이 광고 소재의 중심이 되고 있습니다.",
            "",
            "### 다음 주 전망",
            "",
            "- **확대 가능:** 생활 점검형 콘텐츠, AI/모바일 가이드형 콘텐츠, 운전 안전 루틴형 콘텐츠",
            "- **약화 가능:** 출처가 단일 채널에만 몰린 일회성 이슈, 설명이 길어 모바일 배너로 압축하기 어려운 소재",
            "",
            "### 콘텐츠 아이디어 3가지",
            "",
            "1. 운전 전 10초 체크리스트 카드뉴스",
            "2. 내 상황별 자동차보험 확인 루틴 숏폼",
            "3. 가족/출퇴근/초보운전 상황별 모바일 배너 시리즈",
            "",
            "### 비즈니스 기회 3가지",
            "",
            "1. 자동차보험 가입 전 확인할 항목을 체크리스트로 단순화",
            "2. 모바일 랜딩에서 운전자 상황별 추천 흐름 제공",
            "3. 광고 소재를 트렌드 키워드별로 빠르게 교체할 수 있는 주간 운영 체계 구축",
            "",
            "## 5) Direct Auto Insurance Ad Concepts",
            "",
            "| 트렌드 | 숨은 니즈 | 핵심 메시지 | 광고 콘셉트 | 타깃 |",
            "|---|---|---|---|---|",
        ]
    )
    for candidate in core:
        concept = ad_concept(candidate)
        lines.append(
            f"| {trend_name(candidate)} | {concept['need']} | {concept['message']} | "
            f"{concept['concept']} | {concept['target']} |"
        )

    lines.extend(["", "## 6) Banner Copywriting", ""])
    for index, candidate in enumerate(core, start=1):
        copy = banner_copy(candidate)
        lines.extend(
            [
                f"### Concept {index}) {trend_name(candidate)}",
                "",
                f"- **Main 1:** {copy['main'][0]}",
                f"- **Main 2:** {copy['main'][1]}",
                f"- **Main 3:** {copy['main'][2]}",
                f"- **Sub 1:** {copy['sub'][0]}",
                f"- **Sub 2:** {copy['sub'][1]}",
                f"- **CTA 1:** {copy['cta'][0]}",
                f"- **CTA 2:** {copy['cta'][1]}",
                "",
            ]
        )

    lines.extend(["## 7) Visual Direction", ""])
    for index, candidate in enumerate(core, start=1):
        lines.extend(
            [
                f"### Visual {index}) {trend_name(candidate)}",
                "",
                visual_direction(candidate),
                "",
            ]
        )

    lines.extend(
        [
            "## 8) Manual ChatGPT Image Prompts",
            "",
            "아래 프롬프트는 자동 실행에서 이미지를 만들지 않습니다. 필요할 때 ChatGPT 이미지 생성 화면에 직접 붙여 넣어 사용하세요.",
            "",
            "## IMAGE_PROMPTS_JSON",
            "```json",
            json.dumps(image_prompts, ensure_ascii=False, indent=2),
            "```",
            "",
            "## Appendix: Source Brief",
            "",
            "```text",
            source_brief[:12000],
            "```",
        ]
    )
    return "\n".join(lines)


def build_candidates(items: list[SourceItem]) -> list[TrendCandidate]:
    by_keyword: dict[str, TrendCandidate] = {}
    for item in items:
        tokens = extract_keywords(f"{item.title} {item.summary}")
        unique_tokens = list(dict.fromkeys(tokens))
        for token in unique_tokens:
            candidate = by_keyword.setdefault(token, TrendCandidate(keyword=token, count=0))
            candidate.count += tokens.count(token)
            candidate.channels.add(item.channel)
            if len(candidate.examples) < 5:
                candidate.examples.append(item)
            candidate.related.update(other for other in unique_tokens if other != token)

    candidates = list(by_keyword.values())
    for candidate in candidates:
        candidate.repetition = score(candidate.count, [2, 4, 7, 10, 14])
        candidate.recency = 5 if any(is_recent(item.published_at) for item in candidate.examples) else 3
        candidate.diffusion = min(5, len(candidate.channels) * 2 + (1 if "diffusion" in candidate.channels else 0))
        practical_hits = sum(1 for term in PRACTICAL_TERMS if term.lower() in candidate.keyword.lower())
        practical_hits += sum(1 for term, _ in candidate.related.most_common(10) if term in PRACTICAL_TERMS)
        candidate.practicality = min(5, 2 + practical_hits)

    candidates.sort(
        key=lambda item: (
            len(item.channels),
            item.total,
            item.count,
            "validation" in item.channels,
            "diffusion" in item.channels,
        ),
        reverse=True,
    )
    return candidates


def extract_keywords(text: str) -> list[str]:
    tokens = re.findall(r"[가-힣A-Za-z0-9]{2,}", text)
    cleaned: list[str] = []
    for token in tokens:
        value = token.strip()
        if len(value) < 2:
            continue
        if value in STOPWORDS:
            continue
        if value.isdigit():
            continue
        cleaned.append(value)
    return cleaned


def top_keywords(items: list[SourceItem], *, limit: int) -> list[str]:
    counter: Counter[str] = Counter()
    for item in items:
        counter.update(extract_keywords(f"{item.title} {item.summary}"))
    return [keyword for keyword, _ in counter.most_common(limit)]


def score(value: int, thresholds: list[int]) -> int:
    return sum(1 for threshold in thresholds if value >= threshold)


def is_recent(value: str | None) -> bool:
    if not value:
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return True
    now = datetime.now(parsed.tzinfo) if parsed.tzinfo else datetime.now()
    return (now - parsed).days <= 7


def trend_name(candidate: TrendCandidate) -> str:
    return f"{candidate.keyword} 기반 생활 점검 트렌드"


def make_candidate_explanation(candidate: TrendCandidate) -> str:
    return (
        f"`{candidate.keyword}`가 {candidate.channel_label}에서 반복 포착되어 "
        "콘텐츠와 광고 소재로 확장할 수 있는 후보입니다."
    )


def business_bridge(candidate: TrendCandidate) -> str:
    if any(term in candidate.keyword for term in ("운전", "차량", "자동차", "안전")):
        return "운전자 안전/차량 관리 메시지와 직접 연결됩니다."
    if any(term in candidate.keyword for term in ("AI", "모바일", "체크")):
        return "모바일에서 빠르게 확인하는 광고 흐름과 잘 맞습니다."
    return "일상 관심사를 자동차보험 확인 행동으로 자연스럽게 전환할 수 있습니다."


def ad_concept(candidate: TrendCandidate) -> dict[str, str]:
    return {
        "need": "복잡한 설명 없이 내 상황에 맞는 자동차보험 확인 포인트를 알고 싶다.",
        "message": f"{candidate.keyword} 흐름에 맞춰 자동차보험도 짧고 쉽게 확인.",
        "concept": "모바일 첫 화면에서 핵심 체크 항목을 보여주고 바로 확인 CTA로 연결.",
        "target": "모바일 검색과 숏폼에 익숙한 25-49세 운전자",
    }


def banner_copy(candidate: TrendCandidate) -> dict[str, list[str]]:
    keyword = compact_keyword(candidate.keyword)
    return {
        "main": [
            f"{keyword} 자동차보험",
            "자동차보험 지금 체크",
            "내 차 보험 확인 루틴",
        ],
        "sub": [
            "운전 전 한 번 더 확인",
            "모바일로 간단하게",
        ],
        "cta": [
            "자동차보험 확인",
            "바로 체크하기",
        ],
    }


def compact_keyword(keyword: str) -> str:
    keyword = re.sub(r"\s+", "", keyword)
    if len(keyword) <= 8:
        return keyword
    return keyword[:8]


def visual_direction(candidate: TrendCandidate) -> str:
    return (
        "9:16 모바일 SNS 배너 기준으로 상단에는 짧은 메인 카피 영역, 중앙에는 운전석/차량/체크리스트를 "
        "직관적으로 배치하고 하단에는 CTA 버튼이 들어갈 여백을 둡니다. 색상은 신뢰감을 주는 블루와 "
        "화이트를 기본으로 하되, 트렌드 키워드의 분위기에 맞춰 포인트 컬러를 한 가지만 사용합니다. "
        "돈다발, 코인, 현금, 가격표 이미지는 사용하지 않고 자동차보험이라는 문구가 선명하게 들어갈 수 "
        "있는 광고형 구도를 유지합니다."
    )


def build_image_prompts(candidates: list[TrendCandidate]) -> list[dict[str, str]]:
    prompts: list[dict[str, str]] = []
    for index, candidate in enumerate(candidates[:5], start=1):
        copy = banner_copy(candidate)
        prompts.append(
            {
                "concept": trend_name(candidate),
                "filename_slug": f"free-autoins-{index}",
                "main_copy": copy["main"][0],
                "sub_copy": copy["sub"][0],
                "cta": copy["cta"][0],
                "prompt": (
                    "Create a high-resolution vertical 9:16 Korean mobile SNS advertising banner background "
                    f"for direct auto insurance. Theme keyword: {candidate.keyword}. "
                    f"Place exact Korean headline text '{copy['main'][0]}' in the upper third, "
                    f"supporting text '{copy['sub'][0]}' near the middle, and CTA '{copy['cta'][0]}' "
                    "inside a button area near the bottom. Use a clean trustworthy automotive advertising style, "
                    "modern car or driver safety checklist objects, blue and white base colors with one accent color, "
                    "clear negative space for readable Korean text, polished mobile ad composition. "
                    "Do not include cash, coins, money bundles, gold, cryptocurrency, price tags, or the Korean word 보험료."
                ),
            }
        )
    while len(prompts) < 5:
        index = len(prompts) + 1
        prompts.append(
            {
                "concept": f"자동차보험 기본 점검 콘셉트 {index}",
                "filename_slug": f"free-autoins-default-{index}",
                "main_copy": "자동차보험 지금 체크",
                "sub_copy": "운전 전 한 번 더 확인",
                "cta": "자동차보험 확인",
                "prompt": (
                    "Create a high-resolution vertical 9:16 Korean mobile SNS advertising banner background "
                    "for direct auto insurance. Place exact Korean headline text '자동차보험 지금 체크', "
                    "supporting text '운전 전 한 번 더 확인', and CTA '자동차보험 확인'. "
                    "Use a clean trustworthy car insurance advertising style, blue and white colors, "
                    "driver safety checklist, car dashboard, and mobile UI elements. "
                    "Do not include cash, coins, money bundles, gold, cryptocurrency, price tags, or the Korean word 보험료."
                ),
            }
        )
    return prompts[:5]
