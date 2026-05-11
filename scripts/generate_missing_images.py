from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from trend_banner_automation.config import Settings  # noqa: E402
from trend_banner_automation.openai_ops import generate_image  # noqa: E402
from trend_banner_automation.reporting import extract_image_prompts  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate missing images for an existing report.")
    parser.add_argument("run_dir", help="Path to outputs/<run_id>")
    parser.add_argument("--root", default=".", help="Project root directory")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    run_dir = Path(args.run_dir).resolve()
    report_path = run_dir / "weekly_trend_report.md"
    image_dir = run_dir / "images"

    settings = Settings.from_env(root)
    report = report_path.read_text(encoding="utf-8")
    prompts = extract_image_prompts(report)
    created: list[str] = []

    for index, image_prompt in enumerate(prompts, start=1):
        output_path = image_dir / f"{index:02d}_{image_prompt.filename_slug}.png"
        if output_path.exists():
            continue
        generate_image(settings, image_prompt.prompt, output_path)
        created.append(str(output_path))

    print("\n".join(created) if created else "No missing images.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

