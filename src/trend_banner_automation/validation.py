from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .reporting import ImagePrompt
from .sources import SourceItem


@dataclass
class ValidationResult:
    passed: bool
    issues: list[str] = field(default_factory=list)

    def extend(self, other: "ValidationResult") -> None:
        self.issues.extend(other.issues)
        self.passed = self.passed and other.passed


def validate_sources(items: list[SourceItem], source_errors: list[str]) -> ValidationResult:
    issues: list[str] = []
    if len(items) < 12:
        issues.append(f"Too few source items collected: {len(items)}")
    channels = {item.channel for item in items}
    if "diffusion" not in channels:
        issues.append("Missing diffusion source channel.")
    if "validation" not in channels:
        issues.append("Missing validation source channel.")
    if source_errors and len(items) < 20:
        issues.extend(f"Source access issue: {error}" for error in source_errors)
    return ValidationResult(not issues, issues)


def validate_report(report_markdown: str, prompts: list[ImagePrompt]) -> ValidationResult:
    issues: list[str] = []
    required_sections = [
        "Trend Discovery",
        "Trend Candidates",
        "Trend Scoring",
        "Core Trend TOP 5",
        "Direct Auto Insurance Ad Concepts",
        "IMAGE_PROMPTS_JSON",
    ]
    for section in required_sections:
        if section not in report_markdown:
            issues.append(f"Report missing expected section: {section}")
    if "자동차보험" not in report_markdown:
        issues.append("Report must include 자동차보험 ad linkage.")
    if len(prompts) != 5:
        issues.append(f"Expected exactly 5 image prompts, found {len(prompts)}")
    return ValidationResult(not issues, issues)


def validate_ad_rules(prompts: list[ImagePrompt]) -> ValidationResult:
    issues: list[str] = []
    forbidden = [
        "보험료",
        "돈다발",
        "현금",
        "코인",
        "금화",
        "암호화폐",
        "cash",
        "coin",
        "crypto",
        "money bundle",
        "gold",
    ]
    for prompt in prompts:
        banner_text = f"{prompt.concept} {prompt.main_copy} {prompt.sub_copy} {prompt.cta}"
        prompt_text = f"{banner_text} {prompt.prompt}"
        if "자동차보험" not in banner_text:
            issues.append(f"{prompt.concept}: banner-facing copy must include 자동차보험.")
        for term in forbidden:
            if term.lower() in prompt_text.lower():
                allowed_instruction = "Do not include" in prompt.prompt or "사용하지" in prompt.prompt
                if not allowed_instruction:
                    issues.append(f"{prompt.concept}: forbidden term or imagery found: {term}")
    return ValidationResult(not issues, issues)


def validate_images(
    image_paths: list[Path],
    final_banner_paths: list[Path],
    prompts: list[ImagePrompt],
) -> ValidationResult:
    issues: list[str] = []
    if len(image_paths) != 5:
        issues.append(f"Expected 5 generated background images, found {len(image_paths)}")
    if len(final_banner_paths) != 5:
        issues.append(f"Expected 5 final composed banner images, found {len(final_banner_paths)}")
    for path in [*image_paths, *final_banner_paths]:
        if not path.exists() or path.stat().st_size < 10_000:
            issues.append(f"Image file is missing or suspiciously small: {path}")
    if prompts and len(final_banner_paths) == 5:
        for prompt in prompts:
            if "자동차보험" not in f"{prompt.main_copy} {prompt.sub_copy} {prompt.cta}":
                issues.append(f"{prompt.concept}: final banner text data does not include 자동차보험.")
    return ValidationResult(not issues, issues)
