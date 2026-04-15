from __future__ import annotations

import runpy
import sys
from pathlib import Path


if __name__ == "__main__":
    skill_dir = Path(__file__).resolve().parents[1]
    if str(skill_dir) not in sys.path:
        sys.path.insert(0, str(skill_dir))
    runpy.run_path(str(skill_dir / "run.py"), run_name="__main__")
