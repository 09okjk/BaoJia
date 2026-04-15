from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
RUN_PATH = BASE_DIR / "run.py"
INPUT_SAMPLE_PATH = BASE_DIR / "samples" / "sample-input.json"
OUTPUT_SAMPLE_PATH = BASE_DIR / "samples" / "sample-output.json"
PYTHON = Path(sys.executable)


def main() -> None:
    actual_output_path = (
        Path(tempfile.mkdtemp(prefix="quote-pdf-render-validate-"))
        / "output.actual.json"
    )
    command = [
        str(PYTHON),
        str(RUN_PATH),
        "--input",
        str(INPUT_SAMPLE_PATH),
        "--output",
        str(actual_output_path),
    ]
    proc = subprocess.run(command, check=False)
    if proc.returncode != 0:
        raise SystemExit(proc.returncode)

    actual = json.loads(actual_output_path.read_text(encoding="utf-8"))
    outputs = (
        actual.get("render_result", {}).get("outputs", [])
        if isinstance(actual, dict)
        else []
    )
    if not isinstance(outputs, list) or not outputs:
        raise SystemExit(f"No render outputs found in {actual_output_path}")

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
    print(f"Actual output: {actual_output_path}")


if __name__ == "__main__":
    main()
