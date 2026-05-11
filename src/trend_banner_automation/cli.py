from __future__ import annotations

import argparse
import json
from pathlib import Path

from .config import Settings
from .runner import run_weekly


def main() -> int:
    parser = argparse.ArgumentParser(description="Run weekly trend banner automation.")
    parser.add_argument("--root", default=".", help="Project root directory")
    args = parser.parse_args()

    settings = Settings.from_env(Path(args.root).resolve())
    log = run_weekly(settings)
    print(json.dumps(log, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

