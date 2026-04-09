from __future__ import annotations

import argparse
import json
from pathlib import Path

from jsonschema import ValidationError, validate

from skill import dump_json, load_json, prepare_quote_request


BASE_DIR = Path(__file__).resolve().parent
INPUT_SCHEMA_PATH = BASE_DIR / "schemas" / "input.schema.json"
OUTPUT_SCHEMA_PATH = BASE_DIR / "schemas" / "output.schema.json"


def _load_schema(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _validate_payload(payload: dict, schema_path: Path, label: str) -> None:
    schema = _load_schema(schema_path)
    try:
        validate(payload, schema)
    except ValidationError as exc:
        raise ValueError(f"{label} schema validation failed: {exc.message}") from exc


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Prepare quote_request from assessment input."
    )
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

    result = prepare_quote_request(payload)
    if not args.skip_schema_validation:
        _validate_payload(result, OUTPUT_SCHEMA_PATH, "output")

    if args.output:
        dump_json(args.output, result)
        print(f"Wrote output to {Path(args.output)}")
        return

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
