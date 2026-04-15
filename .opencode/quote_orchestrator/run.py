from __future__ import annotations

import sys
from pathlib import Path


SKILLS_ROOT = Path(__file__).resolve().parents[1] / "skills"

if str(SKILLS_ROOT) not in sys.path:
    sys.path.insert(0, str(SKILLS_ROOT))

from quote_orchestration_skill.workflow.run import main, orchestrate_quote  # noqa: E402,F401


if __name__ == "__main__":
    main()
