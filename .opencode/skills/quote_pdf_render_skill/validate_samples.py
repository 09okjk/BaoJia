from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
RUN_PATH = BASE_DIR / "run.py"
INPUT_SAMPLE_PATH = BASE_DIR / "examples" / "input.sample.json"
OUTPUT_SAMPLE_PATH = BASE_DIR / "examples" / "output.sample.json"
OUTPUT_ACTUAL_PATH = BASE_DIR / "examples" / "output.actual.json"
PYTHON = Path(sys.executable)


def main() -> None:
    command = [
        str(PYTHON),
        str(RUN_PATH),
        "--input",
        str(INPUT_SAMPLE_PATH),
        "--output",
        str(OUTPUT_ACTUAL_PATH),
    ]
    proc = subprocess.run(command, check=False)
    if proc.returncode != 0:
        raise SystemExit(proc.returncode)

    actual = json.loads(OUTPUT_ACTUAL_PATH.read_text(encoding="utf-8"))
    outputs = (
        actual.get("render_result", {}).get("outputs", [])
        if isinstance(actual, dict)
        else []
    )
    if not isinstance(outputs, list) or not outputs:
        raise SystemExit("No render outputs found in output.actual.json")

    failures = [
        item
        for item in outputs
        if not isinstance(item, dict) or item.get("status") != "success"
    ]
    if failures:
        raise SystemExit(
            f"Sample validation failed, unsuccessful outputs: {json.dumps(failures, ensure_ascii=False)}"
        )

    print(f"Validated sample input via {RUN_PATH.name}")
    print(f"Reference expected output: {OUTPUT_SAMPLE_PATH}")
    print(f"Actual output: {OUTPUT_ACTUAL_PATH}")


if __name__ == "__main__":
    main()
