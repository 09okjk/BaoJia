from __future__ import annotations

import argparse
import json
from pathlib import Path

from jsonschema import Draft202012Validator, RefResolver, ValidationError, validate

from skill import build_pricing_result, dump_json, load_json


BASE_DIR = Path(__file__).resolve().parent
INPUT_SCHEMA_PATH = BASE_DIR / "schemas" / "input.schema.json"
OUTPUT_SCHEMA_PATH = BASE_DIR / "schemas" / "output.schema.json"
QUOTE_DOCUMENT_SCHEMA_PATH = BASE_DIR.parent.parent / "quote-document-v1.1.schema.json"


def _load_schema(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _validate_input(payload: dict) -> None:
    validate(payload, _load_schema(INPUT_SCHEMA_PATH))


def _validate_output(payload: dict) -> None:
    schema = _load_schema(OUTPUT_SCHEMA_PATH)
    quote_document_schema = _load_schema(QUOTE_DOCUMENT_SCHEMA_PATH)
    resolver = RefResolver(
        base_uri=OUTPUT_SCHEMA_PATH.resolve().as_uri(),
        referrer=schema,
        store={
            quote_document_schema["$id"]: quote_document_schema,
            QUOTE_DOCUMENT_SCHEMA_PATH.resolve().as_uri(): quote_document_schema,
        },
    )
    try:
        Draft202012Validator(schema, resolver=resolver).validate(payload)
    except ValidationError as exc:
        raise ValueError(f"output schema validation failed: {exc.message}") from exc


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build quotation options from pricing input."
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
        _validate_input(payload)

    result = build_pricing_result(payload)
    if not args.skip_schema_validation:
        _validate_output(result)

    if args.output:
        dump_json(args.output, result)
        print(f"Wrote output to {Path(args.output)}")
        return

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
