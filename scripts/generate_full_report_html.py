from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from trend_banner_automation.full_report_html import markdown_to_full_report_html  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a full visual HTML report from Markdown.")
    parser.add_argument("markdown_path")
    parser.add_argument("output_path")
    args = parser.parse_args()

    markdown = Path(args.markdown_path).read_text(encoding="utf-8")
    output = markdown_to_full_report_html(markdown, Path(args.output_path))
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

