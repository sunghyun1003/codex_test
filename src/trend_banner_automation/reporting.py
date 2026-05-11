from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ImagePrompt:
    concept: str
    filename_slug: str
    main_copy: str
    sub_copy: str
    cta: str
    prompt: str


def extract_image_prompts(report_markdown: str) -> list[ImagePrompt]:
    section_match = re.search(
        r"## IMAGE_PROMPTS_JSON\s*```json\s*(.*?)\s*```",
        report_markdown,
        flags=re.DOTALL | re.IGNORECASE,
    )
    if not section_match:
        return []

    try:
        raw_items = json.loads(section_match.group(1))
    except json.JSONDecodeError:
        return []

    prompts: list[ImagePrompt] = []
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        concept = str(item.get("concept", "")).strip()
        slug = safe_slug(str(item.get("filename_slug", concept)).strip())
        prompt = str(item.get("prompt", "")).strip()
        if concept and slug and prompt:
            prompts.append(
                ImagePrompt(
                    concept=concept,
                    filename_slug=slug,
                    main_copy=str(item.get("main_copy", "")).strip(),
                    sub_copy=str(item.get("sub_copy", "")).strip(),
                    cta=str(item.get("cta", "")).strip(),
                    prompt=prompt,
                )
            )
    return prompts[:5]


def safe_slug(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_-]+", "-", value.lower()).strip("-")
    return cleaned or "banner"


def write_markdown(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def audit_banner_prompts(prompts: list[ImagePrompt]) -> list[str]:
    issues: list[str] = []
    forbidden_terms = [
        "보험료",
        "돈다발",
        "현금",
        "코인",
        "금화",
        "암호화폐",
        "cash pile",
        "cash bundles",
        "money bundle",
        "coins",
        "gold coins",
        "cryptocurrency",
        "crypto",
    ]

    for item in prompts:
        banner_text = f"{item.concept} {item.main_copy} {item.sub_copy} {item.cta}"
        prompt_text = f"{banner_text} {item.prompt}"
        if "자동차보험" not in banner_text:
            issues.append(f"{item.concept}: banner copy set does not include 자동차보험.")
        for term in forbidden_terms:
            if term.lower() in prompt_text.lower():
                allowed_instruction = "Do not include" in item.prompt or "사용하지" in item.prompt
                if not allowed_instruction:
                    issues.append(f"{item.concept}: forbidden term or imagery found: {term}")
    return issues
