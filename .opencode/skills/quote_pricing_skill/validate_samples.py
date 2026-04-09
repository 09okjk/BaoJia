from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator, RefResolver, validate


BASE_DIR = Path(__file__).resolve().parent
QUOTE_DOCUMENT_SCHEMA_PATH = BASE_DIR.parent.parent / "quote-document-v1.1.schema.json"


def _load_json(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"JSON root must be object: {path}")
    return data


def validate_input_sample() -> None:
    data = _load_json(BASE_DIR / "examples" / "input.sample.json")
    schema = _load_json(BASE_DIR / "schemas" / "input.schema.json")
    validate(data, schema)


def validate_output_sample() -> None:
    data = _load_json(BASE_DIR / "examples" / "output.sample.json")
    schema_path = BASE_DIR / "schemas" / "output.schema.json"
    schema = _load_json(schema_path)
    quote_document_schema = _load_json(QUOTE_DOCUMENT_SCHEMA_PATH)
    resolver = RefResolver(
        base_uri=schema_path.resolve().as_uri(),
        referrer=schema,
        store={
            quote_document_schema["$id"]: quote_document_schema,
            QUOTE_DOCUMENT_SCHEMA_PATH.resolve().as_uri(): quote_document_schema,
        },
    )
    Draft202012Validator(schema, resolver=resolver).validate(data)


def main() -> None:
    validate_input_sample()
    validate_output_sample()
    print("pricing sample contract check ok")


if __name__ == "__main__":
    main()
