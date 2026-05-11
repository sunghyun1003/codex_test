from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def load_env_file(path: Path) -> None:
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


@dataclass(frozen=True)
class Settings:
    root_dir: Path
    output_dir: Path
    source_config: Path
    timezone: str
    openai_api_key: str | None
    enable_openai_report: bool
    openai_text_model: str
    openai_image_model: str
    openai_image_size: str
    generate_images: bool
    compose_final_banners: bool
    generate_report_docx: bool
    generate_report_html: bool
    send_only_if_validation_passes: bool
    enable_llm_validation: bool
    youtube_api_key: str | None
    enable_youtube: bool
    naver_client_id: str | None
    naver_client_secret: str | None
    enable_naver_datalab: bool
    send_email: bool
    email_dry_run: bool
    smtp_host: str
    smtp_port: int
    smtp_username: str | None
    smtp_password: str | None
    email_from: str | None
    email_to: list[str]
    email_subject_prefix: str
    max_items_per_source: int
    fetch_timeout_seconds: int

    @classmethod
    def from_env(cls, root_dir: Path | None = None) -> "Settings":
        root = root_dir or Path.cwd()
        load_env_file(root / ".env")

        output_dir = root / os.getenv("OUTPUT_DIR", "outputs")
        source_config = root / os.getenv("SOURCE_CONFIG", "config/sources.json")
        email_to = [
            item.strip()
            for item in os.getenv("EMAIL_TO", "").replace(";", ",").split(",")
            if item.strip()
        ]

        return cls(
            root_dir=root,
            output_dir=output_dir,
            source_config=source_config,
            timezone=os.getenv("TIMEZONE", "Asia/Seoul"),
            openai_api_key=os.getenv("OPENAI_API_KEY") or None,
            enable_openai_report=env_bool("ENABLE_OPENAI_REPORT", False),
            openai_text_model=os.getenv("OPENAI_TEXT_MODEL", "gpt-5.2"),
            openai_image_model=os.getenv("OPENAI_IMAGE_MODEL", "gpt-image-1.5"),
            openai_image_size=os.getenv("OPENAI_IMAGE_SIZE", "1024x1536"),
            generate_images=env_bool("GENERATE_IMAGES", False),
            compose_final_banners=env_bool("COMPOSE_FINAL_BANNERS", False),
            generate_report_docx=env_bool("GENERATE_REPORT_DOCX", True),
            generate_report_html=env_bool("GENERATE_REPORT_HTML", True),
            send_only_if_validation_passes=env_bool("SEND_ONLY_IF_VALIDATION_PASSES", True),
            enable_llm_validation=env_bool("ENABLE_LLM_VALIDATION", False),
            youtube_api_key=os.getenv("YOUTUBE_API_KEY") or None,
            enable_youtube=env_bool("ENABLE_YOUTUBE", True),
            naver_client_id=os.getenv("NAVER_CLIENT_ID") or None,
            naver_client_secret=os.getenv("NAVER_CLIENT_SECRET") or None,
            enable_naver_datalab=env_bool("ENABLE_NAVER_DATALAB", True),
            send_email=env_bool("SEND_EMAIL", False),
            email_dry_run=env_bool("EMAIL_DRY_RUN", True),
            smtp_host=os.getenv("SMTP_HOST", "smtp.gmail.com"),
            smtp_port=int(os.getenv("SMTP_PORT", "587")),
            smtp_username=os.getenv("SMTP_USERNAME") or None,
            smtp_password=os.getenv("SMTP_PASSWORD") or None,
            email_from=os.getenv("EMAIL_FROM") or None,
            email_to=email_to,
            email_subject_prefix=os.getenv("EMAIL_SUBJECT_PREFIX", "[Weekly Trend]"),
            max_items_per_source=int(os.getenv("MAX_ITEMS_PER_SOURCE", "12")),
            fetch_timeout_seconds=int(os.getenv("FETCH_TIMEOUT_SECONDS", "12")),
        )
