from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from jsonschema import ValidationError, validate

from skill import build_render_result, dump_json, load_json


BASE_DIR = Path(__file__).resolve().parent
INPUT_SCHEMA_PATH = BASE_DIR / "schemas" / "input.schema.json"
OUTPUT_SCHEMA_PATH = BASE_DIR / "schemas" / "output.schema.json"
QUOTE_DOCUMENT_SCHEMA_PATH = BASE_DIR.parent.parent / "quote-document-v1.1.schema.json"


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


def _inline_quote_document_schema(schema: Any, quote_document_schema: dict) -> Any:
    if isinstance(schema, dict):
        if schema.get("$ref") == "../../../quote-document-v1.1.schema.json":
            return quote_document_schema
        return {
            key: _inline_quote_document_schema(value, quote_document_schema)
            for key, value in schema.items()
        }
    if isinstance(schema, list):
        return [
            _inline_quote_document_schema(item, quote_document_schema)
            for item in schema
        ]
    return schema


def _validate_input(payload: dict) -> None:
    schema = _load_schema(INPUT_SCHEMA_PATH)
    quote_document_schema = _load_schema(QUOTE_DOCUMENT_SCHEMA_PATH)
    try:
        validate(payload, _inline_quote_document_schema(schema, quote_document_schema))
    except ValidationError as exc:
        raise ValueError(f"input schema validation failed: {exc.message}") from exc


def _validate_output(payload: dict) -> None:
    validate(payload, _load_schema(OUTPUT_SCHEMA_PATH))


def main() -> None:
    parser = argparse.ArgumentParser(description="Render quotation HTML/PDF files.")
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

    result = build_render_result(payload)
    if not args.skip_schema_validation:
        _validate_output(result)

    if args.output:
        dump_json(args.output, result)
        print(f"Wrote output to {Path(args.output)}")
        return

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
