from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import validate


BASE_DIR = Path(__file__).resolve().parent


def _load_json(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"JSON root must be object: {path}")
    return data


def _load_schema(path: Path) -> dict:
    return _resolve_local_refs(_load_json(path), path.parent)


def _resolve_local_refs(value: Any, base_dir: Path) -> Any:
    if isinstance(value, dict):
        ref = value.get("$ref")
        if isinstance(ref, str) and (ref.startswith("../") or ref.startswith("./")):
            ref_path = (base_dir / ref).resolve()
            return _resolve_local_refs(_load_json(ref_path), ref_path.parent)
        return {key: _resolve_local_refs(item, base_dir) for key, item in value.items()}
    if isinstance(value, list):
        return [_resolve_local_refs(item, base_dir) for item in value]
    return value


def validate_input_sample() -> None:
    data = _load_json(BASE_DIR / "samples" / "sample-input.json")
    schema = _load_schema(
        BASE_DIR / "references" / "quote-feedback-capture-input.schema.json"
    )
    validate(data, schema)


def validate_output_sample() -> None:
    data = _load_json(BASE_DIR / "samples" / "sample-output.json")
    schema = _load_schema(
        BASE_DIR / "references" / "quote-feedback-capture-output.schema.json"
    )
    validate(data, schema)


def main() -> None:
    validate_input_sample()
    validate_output_sample()
    print("feedback capture sample contract check ok")


if __name__ == "__main__":
    main()
