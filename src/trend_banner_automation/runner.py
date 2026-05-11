from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .config import Settings
from .docx_writer import markdown_to_docx
from .emailer import send_report_email
from .executive_docx import markdown_to_executive_docx
from .executive_html import markdown_to_executive_html
from .free_report import build_free_report
from .full_report_html import markdown_to_full_report_html
from .openai_ops import generate_report
from .prompts import REPORT_PROMPT, VALIDATION_PROMPT
from .reporting import audit_banner_prompts, extract_image_prompts, write_markdown
from .sources import collect_sources, render_source_brief
from .validation import ValidationResult, validate_ad_rules, validate_report, validate_sources


def run_weekly(settings: Settings) -> dict[str, object]:
    started_at = datetime.now(resolve_timezone(settings.timezone))
    run_id = started_at.strftime("%Y%m%d_%H%M%S")
    run_dir = settings.output_dir / run_id
    report_path = run_dir / "weekly_trend_report.md"
    full_html_path = run_dir / "full_trend_report.html"
    docx_path = run_dir / "weekly_trend_report.docx"
    executive_docx_path = run_dir / "core_trend_top5_executive.docx"
    executive_html_path = run_dir / "core_trend_top5_executive.html"
    source_path = run_dir / "source_brief.md"
    log_path = run_dir / "run_log.json"

    run_dir.mkdir(parents=True, exist_ok=True)

    items, source_errors = collect_sources(settings)
    source_validation = validate_sources(items, source_errors)
    source_brief = render_source_brief(items, source_errors)
    write_markdown(source_path, source_brief)

    report_error: str | None = None
    if settings.enable_openai_report:
        try:
            report_markdown = generate_report(settings, REPORT_PROMPT, source_brief)
        except Exception as exc:  # noqa: BLE001 - keep the run auditable
            report_error = str(exc)
            report_markdown = build_free_report(
                items=items,
                source_errors=source_errors,
                source_brief=source_brief,
                started_at=started_at,
            )
    else:
        report_markdown = build_free_report(
            items=items,
            source_errors=source_errors,
            source_brief=source_brief,
            started_at=started_at,
        )

    write_markdown(report_path, report_markdown)

    html_error: str | None = None
    try:
        markdown_to_full_report_html(report_markdown, full_html_path)
    except Exception as exc:  # noqa: BLE001
        html_error = str(exc)

    if settings.generate_report_html:
        try:
            markdown_to_executive_html(report_markdown, executive_html_path)
        except Exception:
            executive_html_path = full_html_path

    if settings.generate_report_docx:
        markdown_to_docx(report_markdown, docx_path, title="Weekly Trend Report")
        try:
            markdown_to_executive_docx(report_markdown, executive_docx_path)
        except Exception:
            executive_docx_path = docx_path

    image_prompts = extract_image_prompts(report_markdown)
    compliance_issues = audit_banner_prompts(image_prompts)
    validation = build_validation(
        source_validation=source_validation,
        report_markdown=report_markdown,
        image_prompts=image_prompts,
        report_error=report_error,
        html_error=html_error,
        compliance_issues=compliance_issues,
    )
    if settings.enable_llm_validation and settings.enable_openai_report:
        validation.extend(
            run_llm_validation(
                settings=settings,
                source_brief=source_brief,
                report_markdown=report_markdown,
            )
        )

    subject = f"{settings.email_subject_prefix} {started_at.strftime('%Y-%m-%d')}"
    if settings.send_only_if_validation_passes and not validation.passed:
        email_status = "Email blocked because validation did not pass."
    else:
        main_report_attachment = full_html_path if full_html_path.exists() else report_path
        email_body = build_email_body(started_at, validation, main_report_attachment)
        attachments = [main_report_attachment, source_path]
        try:
            email_status = send_report_email(
                settings=settings,
                subject=subject,
                body_markdown=email_body,
                attachments=attachments,
            )
        except Exception as exc:  # noqa: BLE001
            email_status = f"Email failed: {exc}"

    log: dict[str, object] = {
        "run_id": run_id,
        "started_at": started_at.isoformat(),
        "free_mode": not settings.enable_openai_report,
        "source_count": len(items),
        "source_errors": source_errors,
        "report_error": report_error,
        "html_error": html_error,
        "report_path": str(report_path),
        "full_html_path": str(full_html_path) if full_html_path.exists() else None,
        "docx_path": str(docx_path) if docx_path.exists() else None,
        "executive_docx_path": str(executive_docx_path) if executive_docx_path.exists() else None,
        "executive_html_path": str(executive_html_path) if executive_html_path.exists() else None,
        "source_path": str(source_path),
        "image_generation_enabled": False,
        "image_count": 0,
        "image_paths": [],
        "final_banner_count": 0,
        "final_banner_paths": [],
        "manual_image_prompt_count": len(image_prompts),
        "banner_compliance_issues": compliance_issues,
        "validation_passed": validation.passed,
        "validation_issues": validation.issues,
        "email_status": email_status,
    }
    log_path.write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")
    return log


def build_validation(
    *,
    source_validation: ValidationResult,
    report_markdown: str,
    image_prompts: list,
    report_error: str | None,
    html_error: str | None,
    compliance_issues: list[str],
) -> ValidationResult:
    validation = ValidationResult(True, [])
    for item in (
        source_validation,
        validate_report(report_markdown, image_prompts),
        validate_ad_rules(image_prompts),
    ):
        validation.extend(item)
    if report_error:
        validation.issues.append(f"OpenAI report generation failed; free report was used: {report_error}")
    if html_error:
        validation.issues.append(f"HTML report generation failed: {html_error}")
        validation.passed = False
    if compliance_issues:
        validation.issues.extend(compliance_issues)
        validation.passed = False
    return validation


def run_llm_validation(
    *,
    settings: Settings,
    source_brief: str,
    report_markdown: str,
) -> ValidationResult:
    payload = (
        "# Source Brief\n"
        f"{source_brief[:12000]}\n\n"
        "# Report\n"
        f"{report_markdown[:18000]}"
    )
    try:
        raw = generate_report(settings, VALIDATION_PROMPT, payload)
        parsed = json.loads(raw.strip().strip("`"))
        issues = [str(issue) for issue in parsed.get("issues", [])]
        return ValidationResult(bool(parsed.get("passed", False)), issues)
    except Exception as exc:  # noqa: BLE001
        return ValidationResult(False, [f"LLM validation failed: {exc}"])


def resolve_timezone(timezone_name: str):
    try:
        return ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError:
        if timezone_name == "Asia/Seoul":
            return timezone(timedelta(hours=9), name="KST")
        return timezone.utc


def build_email_body(
    started_at: datetime,
    validation: ValidationResult,
    report_path: Path,
) -> str:
    status = "통과" if validation.passed else "확인 필요"
    lines = [
        "주간 트렌드 자동화 결과입니다.",
        "",
        f"- 실행일: {started_at.strftime('%Y-%m-%d %H:%M')}",
        f"- 검증 상태: {status}",
        f"- 리포트 파일: {report_path.name if report_path.exists() else '미생성'}",
        "- 이미지 생성 프롬프트: HTML 리포트 최하단에 포함",
    ]
    if validation.issues:
        lines.extend(["", "검증/수집 참고 사항:"])
        lines.extend(f"- {issue}" for issue in validation.issues)
    return "\n".join(lines)
