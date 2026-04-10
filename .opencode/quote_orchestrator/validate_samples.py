from __future__ import annotations

import json
from pathlib import Path

from jsonschema import validate


BASE_DIR = Path(__file__).resolve().parent
OPENCODE_DIR = BASE_DIR.parent


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
    schema = _load_json(BASE_DIR / "schemas" / "output.schema.json")
    quote_document_schema = _load_json(OPENCODE_DIR / "quote-document-v1.1.schema.json")
    validate(data, schema)
    validate(data["quote_document"], quote_document_schema)


def main() -> None:
    validate_input_sample()
    validate_output_sample()
    print("orchestrator sample contract check ok")


if __name__ == "__main__":
    main()
