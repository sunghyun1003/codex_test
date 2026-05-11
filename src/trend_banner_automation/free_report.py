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

NOISE_TOKENS = {
    "nbsp",
    "amp",
    "quot",
    "apos",
    "com",
    "net",
    "www",
    "http",
    "https",
    "daum",
    "naver",
    "nate",
    "news",
    "newsis",
    "네이트",
    "다음",
    "브런치",
    "한국경제",
    "뉴시스",
    "트렌드",
    "소비",
    "시장",
    "시대",
    "확산",
    "확대",
    "전략",
    "글로벌",
    "개최",
    "기념",
    "하나",
    "방법",
    "관련",
    "최근",
    "단독",
    "기자",
    "영상",
    "공개",
    "발표",
    "오늘",
    "내일",
    "이번",
    "대한",
    "위한",
    "통한",
    "있는",
    "없는",
    "한다",
    "했다",
    "하는",
    "ratio",
    "keywords",
    "latest",
    "seven",
    "day",
    "꾸준히",
    "전하는",
    "열렸다",
    "카카오까지",
    "2026년",
    "보험료",
}

DOMAIN_CONTEXT_TOKENS = {
    "자동차",
    "자동차보험",
    "다이렉트",
    "운전",
}

BANNER_REFERENCE_CUES = (
    "Use the quality direction of Korean auto-insurance SNS banner references: square feed composition, "
    "large bold Korean headline, clear two-step hierarchy, strong CTA bar or rounded button near the bottom, "
    "simple benefit-oriented layout, crisp object focus, and generous negative space around copy. "
    "Vary the execution by concept rather than using one uniform blue-and-white template."
)


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
            "아래 프롬프트를 ChatGPT 이미지 생성 화면에 붙여 넣어 배너 이미지 제작에 활용하세요.",
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
            item.total,
            len(item.channels),
            item.count,
            "validation" in item.channels,
            "diffusion" in item.channels,
        ),
        reverse=True,
    )
    return candidates


def extract_keywords(text: str) -> list[str]:
    text = re.sub(r"&(?:nbsp|amp|quot|apos);", " ", text, flags=re.IGNORECASE)
    tokens = re.findall(r"[가-힣A-Za-z0-9]{2,}", text)
    cleaned: list[str] = []
    for token in tokens:
        value = token.strip()
        if len(value) < 2:
            continue
        if value in STOPWORDS or is_noise_keyword(value):
            continue
        if value.isdigit():
            continue
        cleaned.append(value)
    return cleaned


def is_noise_keyword(value: str) -> bool:
    lowered = value.lower()
    if lowered in NOISE_TOKENS:
        return True
    if lowered.endswith((".com", ".net", ".co")):
        return True
    if re.search(r"^(뉴스|신문|일보|방송|경제|미디어)$", value):
        return True
    if re.search(r"^\d{4}년?$", value):
        return True
    if len(value) <= 2 and value not in {"AI", "숏폼", "릴스", "쇼츠", "운전", "안전"}:
        return True
    return False


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
    keyword = candidate.keyword
    related = {term for term, _ in candidate.related.most_common(12)}
    title_map = {
        "숏폼": "숏폼 콘텐츠 소비 확대",
        "안전": "참여형 안전 콘텐츠 확산",
        "초보운전": "초보운전 차량관리 루틴",
        "가성비": "가성비 소비 재부상",
        "소비트렌드": "가성비 소비 트렌드",
        "AI": "AI 기반 콘텐츠 제작 확산",
        "디지털": "디지털 콘텐츠 제작 지원 확대",
    }
    if keyword in title_map:
        return title_map[keyword]
    if keyword == "자동차보험":
        if "다이렉트" in related:
            return "다이렉트 자동차보험 확인 수요"
        return "자동차보험 정보 탐색 증가"
    if keyword == "자동차":
        if "장기렌트" in related or "팰리세이드" in related:
            return "차량 구매·렌트 비교 관심"
        return "차량 관리 관심 증가"
    if keyword == "다이렉트":
        return "다이렉트 가입 정보 탐색 증가"
    if keyword == "운전":
        return "운전 안전·관리 루틴 관심"
    return f"{keyword} 관심 증가"


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
    keyword = compact_keyword(ad_copy_keyword(candidate))
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


def ad_copy_keyword(candidate: TrendCandidate) -> str:
    if candidate.keyword == "자동차보험":
        return "내 차"
    if candidate.keyword == "자동차":
        return "내 차"
    if candidate.keyword == "다이렉트":
        return "다이렉트"
    return candidate.keyword


def compact_keyword(keyword: str) -> str:
    keyword = re.sub(r"\s+", "", keyword)
    if len(keyword) <= 8:
        return keyword
    return keyword[:8]


def visual_direction(candidate: TrendCandidate) -> str:
    style = creative_direction(candidate, 1)
    return (
        "1:1 정방형 SNS 배너 기준으로 메인 카피는 상단 또는 좌상단에 크게 배치하고, 중앙에는 콘셉트에 맞는 "
        f"{style['visual_style']} 비주얼을 사용합니다. 핵심 오브젝트는 {style['objects']}이며, "
        f"톤앤매너는 {style['mood']}로 잡습니다. 색상은 {style['colors']}를 중심으로 구성하고, "
        "하단에는 CTA 버튼이 들어갈 충분한 여백을 둡니다. 돈다발, 코인, 현금, 가격표 이미지는 사용하지 않고 "
        "자동차보험 문구가 선명하게 보이는 광고형 구도를 유지합니다."
    )


def creative_direction(candidate: TrendCandidate, index: int) -> dict[str, str]:
    keyword = candidate.keyword
    title = trend_name(candidate)
    related = {term for term, _ in candidate.related.most_common(12)}

    if keyword in {"자동차보험", "다이렉트"}:
        return {
            "visual_style": "프리미엄 실사 라이프스타일 사진",
            "objects": "스마트폰 보험 확인 화면, 자동차 키, 깔끔한 차량 실내 디테일",
            "mood": "신뢰감 있고 차분한 금융 서비스 광고 톤",
            "colors": "딥블루, 화이트, 라이트그레이, 작은 민트 포인트",
            "composition": "square crop, close-up foreground object, big headline block on the upper left, CTA bar at the bottom",
            "reference_cue": "similar to polished Korean insurer feed banners with a strong headline, product cue, and clear lower CTA",
        }
    if keyword in {"자동차", "운전"} or "장기렌트" in related:
        return {
            "visual_style": "자연광 실사 자동차 라이프스타일 사진",
            "objects": "도심 도로의 차량, 운전석 손, 대시보드, 내비게이션 UI",
            "mood": "현실적이고 바로 행동하게 만드는 모빌리티 광고 톤",
            "colors": "네이비, 스카이블루, 화이트, 차콜",
            "composition": "square social ad, vehicle or dashboard as hero object, oversized headline over a clean sky or road area, CTA band at bottom",
            "reference_cue": "similar to Korean car-insurance banners that use real vehicle photography and high-contrast headline typography",
        }
    if keyword in {"안전", "초보운전"}:
        return {
            "visual_style": "친근한 2D 일러스트레이션",
            "objects": "초보운전 표식, 체크리스트, 안전벨트, 작은 자동차 아이콘",
            "mood": "부담 없고 안심되는 교육형 서비스 광고 톤",
            "colors": "소프트블루, 세이지그린, 아이보리, 따뜻한 옐로 포인트",
            "composition": "square layout, friendly character or checklist scene in the center, headline at top, rounded CTA at bottom",
            "reference_cue": "similar to character-based Korean insurance banners with warm expressions and simple explanatory copy",
        }
    if keyword in {"숏폼", "AI", "디지털"} or "숏폼" in title:
        return {
            "visual_style": "에너지 있는 3D/디지털 일러스트",
            "objects": "세로형 숏폼 카드, 스마트폰, 알림 버블, 자동차 아이콘, AI 가이드 UI",
            "mood": "빠르고 경쾌한 모바일 콘텐츠 광고 톤",
            "colors": "일렉트릭블루, 코발트, 화이트, 라임 포인트",
            "composition": "square dynamic composition, floating UI cards, bold headline in the center-left, CTA button below",
            "reference_cue": "similar to modern Korean app-service banners with mascot-like UI elements and sharp digital depth",
        }
    if keyword in {"가성비", "소비트렌드"}:
        return {
            "visual_style": "깔끔한 에디토리얼 콜라주 일러스트",
            "objects": "체크 카드형 UI, 비교 리스트, 자동차 실루엣, 생활 소품",
            "mood": "똑똑하고 실용적인 소비 정보 광고 톤",
            "colors": "화이트, 잉크블루, 코랄, 라이트민트",
            "composition": "square editorial grid, modular cards, large numeric or checklist-like visual rhythm without price claims, CTA strip at bottom",
            "reference_cue": "similar to Korean comparison banners with bold headline contrast and neatly separated information blocks",
        }

    style_cycle = [
        {
            "visual_style": "모던 실사 광고 사진",
            "objects": "스마트폰, 자동차 키, 차량 실내",
            "mood": "정돈되고 신뢰감 있는 서비스 광고 톤",
            "colors": "블루, 화이트, 그레이",
            "composition": "square balanced layout with copy-safe negative space",
            "reference_cue": "similar to clean Korean insurance service banners with strong typography and bottom CTA",
        },
        {
            "visual_style": "부드러운 2D 일러스트레이션",
            "objects": "체크리스트, 자동차 아이콘, 운전자 캐릭터",
            "mood": "친근하고 이해하기 쉬운 안내형 광고 톤",
            "colors": "소프트블루, 그린, 아이보리",
            "composition": "square centered illustration with headline area",
            "reference_cue": "similar to friendly Korean character banners for insurance guidance",
        },
        {
            "visual_style": "밝은 카툰형 광고 일러스트",
            "objects": "웃는 운전자 캐릭터, 작은 자동차, 말풍선 CTA",
            "mood": "가볍고 클릭을 유도하는 SNS 광고 톤",
            "colors": "스카이블루, 화이트, 옐로, 코랄",
            "composition": "square cartoon poster, bold headline, clear CTA button",
            "reference_cue": "similar to humorous problem-solution cartoon banners with bold Korean copy",
        },
    ]
    return style_cycle[(index - 1) % len(style_cycle)]


def build_image_prompts(candidates: list[TrendCandidate]) -> list[dict[str, str]]:
    prompts: list[dict[str, str]] = []
    for index, candidate in enumerate(candidates[:5], start=1):
        copy = banner_copy(candidate)
        style = creative_direction(candidate, index)
        prompts.append(
            {
                "concept": trend_name(candidate),
                "filename_slug": f"free-autoins-{index}",
                "aspect_ratio": "1:1",
                "visual_style": style["visual_style"],
                "main_copy": copy["main"][0],
                "sub_copy": copy["sub"][0],
                "cta": copy["cta"][0],
                "prompt": (
                    "Create a high-resolution square 1:1 Korean SNS advertising banner for direct auto insurance, "
                    "optimized for a 1080x1080 feed image. "
                    f"Concept: {trend_name(candidate)}. Theme keyword: {candidate.keyword}. "
                    f"Visual style: {style['visual_style']}. Key objects: {style['objects']}. "
                    f"Mood: {style['mood']}. Color palette: {style['colors']}. "
                    f"Composition: {style['composition']}. "
                    f"Reference quality cues: {BANNER_REFERENCE_CUES} {style['reference_cue']}. "
                    f"Place exact Korean headline text '{copy['main'][0]}' in a large readable type area, "
                    f"supporting text '{copy['sub'][0]}' as a smaller secondary line, and CTA '{copy['cta'][0]}' "
                    "inside a clear button near the lower edge. Ensure the Korean text is crisp, correctly spelled, "
                    "and does not overlap important objects. Keep the ad polished, brand-safe, and suitable for "
                    "auto-insurance acquisition. Do not include cash, coins, money bundles, gold, cryptocurrency, "
                    "price tags, discount labels, or premium-price wording."
                ),
            }
        )
    while len(prompts) < 5:
        index = len(prompts) + 1
        style = creative_direction(TrendCandidate(keyword="자동차보험", count=1), index)
        prompts.append(
            {
                "concept": f"자동차보험 기본 점검 콘셉트 {index}",
                "filename_slug": f"free-autoins-default-{index}",
                "aspect_ratio": "1:1",
                "visual_style": style["visual_style"],
                "main_copy": "자동차보험 지금 체크",
                "sub_copy": "운전 전 한 번 더 확인",
                "cta": "자동차보험 확인",
                "prompt": (
                    "Create a high-resolution square 1:1 Korean SNS advertising banner for direct auto insurance, "
                    "optimized for a 1080x1080 feed image. "
                    f"Visual style: {style['visual_style']}. Key objects: {style['objects']}. "
                    f"Mood: {style['mood']}. Color palette: {style['colors']}. "
                    f"Reference quality cues: {BANNER_REFERENCE_CUES} {style['reference_cue']}. "
                    "Place exact Korean headline text '자동차보험 지금 체크', supporting text '운전 전 한 번 더 확인', "
                    "and CTA '자동차보험 확인'. Ensure the Korean text is crisp, correctly spelled, and readable. "
                    "Do not include cash, coins, money bundles, gold, cryptocurrency, price tags, discount labels, "
                    "or premium-price wording."
                ),
            }
        )
    return prompts[:5]
