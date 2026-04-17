from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from jsonschema import ValidationError, validate

from skill import build_feedback_reference_result, dump_json, load_json


BASE_DIR = Path(__file__).resolve().parent
INPUT_SCHEMA_PATH = BASE_DIR / "schemas" / "input.schema.json"
OUTPUT_SCHEMA_PATH = BASE_DIR / "schemas" / "output.schema.json"


def _load_schema(path: Path) -> dict:
    return _resolve_local_refs(
        json.loads(path.read_text(encoding="utf-8")), path.parent
    )


def _resolve_local_refs(value: Any, base_dir: Path) -> Any:
    if isinstance(value, dict):
        ref = value.get("$ref")
        if isinstance(ref, str) and (ref.startswith("../") or ref.startswith("./")):
            ref_path = (base_dir / ref).resolve()
            return _resolve_local_refs(
                json.loads(ref_path.read_text(encoding="utf-8")), ref_path.parent
            )
        return {key: _resolve_local_refs(item, base_dir) for key, item in value.items()}
    if isinstance(value, list):
        return [_resolve_local_refs(item, base_dir) for item in value]
    return value


def _validate_payload(payload: dict, schema_path: Path, label: str) -> None:
    try:
        validate(payload, _load_schema(schema_path))
    except ValidationError as exc:
        raise ValueError(f"{label} schema validation failed: {exc.message}") from exc


def main() -> None:
    parser = argparse.ArgumentParser(description="Retrieve quote feedback references.")
    parser.add_argument("--input", required=True, help="Input JSON file path")
    parser.add_argument("--output", help="Output JSON file path")
    parser.add_argument(
        "--skip-schema-validation",
        action="store_true",
        help="Skip input/output JSON Schema validation.",
    )
    args = parser.parse_args()

    payload = load_json(args.input)
    if not args.skip_schema_validation:
        _validate_payload(payload, INPUT_SCHEMA_PATH, "input")

    result = build_feedback_reference_result(payload)
    if not args.skip_schema_validation:
        _validate_payload(result, OUTPUT_SCHEMA_PATH, "output")

    if args.output:
        dump_json(args.output, result)
        print(f"Wrote output to {Path(args.output)}")
        return

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
