from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from trend_banner_automation.config import Settings  # noqa: E402
from trend_banner_automation.emailer import send_report_email  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Resend an existing run by email.")
    parser.add_argument("run_dir", help="Path to outputs/<run_id>")
    parser.add_argument("--root", default=".", help="Project root directory")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    run_dir = Path(args.run_dir).resolve()
    settings = Settings.from_env(root)
    report_path = run_dir / "weekly_trend_report.md"
    source_path = run_dir / "source_brief.md"
    log_path = run_dir / "run_log.json"
    image_paths = sorted((run_dir / "images").glob("*.png"))

    body = report_path.read_text(encoding="utf-8")
    subject = f"{settings.email_subject_prefix} completed {run_dir.name}"
    status = send_report_email(settings, subject, body, [report_path, source_path, *image_paths])

    if log_path.exists():
        log = json.loads(log_path.read_text(encoding="utf-8"))
    else:
        log = {}
    log["image_count"] = len(image_paths)
    log["image_paths"] = [str(path) for path in image_paths]
    log["image_errors"] = []
    log["email_status"] = status
    log_path.write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")

    print(status)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

