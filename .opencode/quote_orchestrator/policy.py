from __future__ import annotations

"""Deprecated compatibility wrapper.

The maintained policy implementation now lives in:
`.opencode/skills/quote_orchestration_skill/workflow/policy.py`

Do not add new logic here.
"""

import sys
from pathlib import Path


SKILLS_ROOT = Path(__file__).resolve().parents[1] / "skills"

if str(SKILLS_ROOT) not in sys.path:
    sys.path.insert(0, str(SKILLS_ROOT))

from quote_orchestration_skill.workflow.policy import *  # noqa: F401,F403,E402
