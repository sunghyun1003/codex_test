from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from trend_banner_automation.cli import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())

