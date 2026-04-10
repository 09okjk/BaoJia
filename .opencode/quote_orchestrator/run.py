from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from typing import Any

from jsonschema import ValidationError, validate


BASE_DIR = Path(__file__).resolve().parent
SKILLS_DIR = BASE_DIR.parent / "skills"
INPUT_SCHEMA_PATH = BASE_DIR / "schemas" / "input.schema.json"
OUTPUT_SCHEMA_PATH = BASE_DIR / "schemas" / "output.schema.json"


def _load_json(path: str | Path) -> dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Input JSON root must be object.")
    return data


def _dump_json(path: str | Path, payload: dict[str, Any]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _load_schema(path: str | Path) -> dict[str, Any]:
    return _load_json(path)


def _validate_payload(payload: dict[str, Any], schema_path: Path, label: str) -> None:
    schema = _load_schema(schema_path)
    try:
        validate(payload, schema)
    except ValidationError as exc:
        raise ValueError(f"{label} schema validation failed: {exc.message}") from exc


def _validate_quote_document(payload: dict[str, Any]) -> None:
    schema = _load_schema(BASE_DIR.parent / "quote-document-v1.1.schema.json")
    validate(payload.get("quote_document", {}), schema)


def _load_skill_module(skill_name: str):
    skill_path = SKILLS_DIR / skill_name / "skill.py"
    spec = importlib.util.spec_from_file_location(f"{skill_name}_module", skill_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load skill module: {skill_name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _default_pricing_rules(payload: dict[str, Any]) -> dict[str, Any]:
    business_context = payload.get("business_context")
    if not isinstance(business_context, dict):
        business_context = {}

    pricing_rules = business_context.get("pricing_rules")
    if isinstance(pricing_rules, dict):
        return pricing_rules

    customer_context = payload.get("customer_context")
    if not isinstance(customer_context, dict):
        customer_context = {}

    currency = (
        str(
            customer_context.get("currency")
            or customer_context.get("preferred_currency")
            or "USD"
        ).strip()
        or "USD"
    )
    return {
        "currency": currency,
        "service_rates": {
            "mechanical_supervisor_hourly": 55.0,
            "mechanical_technician_hourly": 35.0,
            "electrical_supervisor_hourly": 60.0,
            "electrical_assistant_hourly": 40.0,
            "service": 3500.0,
            "spare_parts": 800.0,
            "other": 300.0,
        },
        "lump_sum_overrides": {},
        "multi_option_mode": bool(business_context.get("multi_option")),
        "remark_hints": [],
        "default_discount_percentage": 5.0,
        "discount_overrides": {},
        "pricing_multipliers": {
            "spare_parts_oem": 1.25,
            "spare_parts_alternative": 1.5,
            "freight": 1.35,
            "delivery": 1.35,
            "third_party": 1.4,
            "dock_port_service": 1.3,
            "dockyard_management": 1.2,
            "boarding_travel": 1.2,
        },
        "charge_bases": {
            "third_party_base": 1200.0,
            "freight_base": 300.0,
            "delivery_base": 260.0,
            "transportation_base": 450.0,
            "accommodation_daily": 45.0,
            "port_service_base": 150.0,
            "maritime_reporting_base": 150.0,
            "dockyard_management_base": 200.0,
            "boarding_travel_base": 180.0,
        },
    }


def orchestrate_quote(payload: dict[str, Any]) -> dict[str, Any]:
    prepare_module = _load_skill_module("quote_request_prepare_skill")
    feasibility_module = _load_skill_module("quote_feasibility_check_skill")
    historical_module = _load_skill_module("historical_quote_reference_skill")
    pricing_module = _load_skill_module("quote_pricing_skill")
    review_module = _load_skill_module("quote_review_output_skill")

    prepare_result = prepare_module.prepare_quote_request(payload)
    quote_request = prepare_result["quote_request"]

    feasibility_result = feasibility_module.check_quote_feasibility(
        {"quote_request": quote_request}
    )
    historical_reference = historical_module.build_historical_reference(
        {
            "quote_request": quote_request,
            "quotable_items": feasibility_result.get("quotable_items", []),
        }
    )
    pricing_result = pricing_module.build_pricing_result(
        {
            "quote_request": quote_request,
            "feasibility_result": feasibility_result,
            "historical_reference": historical_reference,
            "pricing_rules": _default_pricing_rules(payload),
        }
    )
    review_output = review_module.build_quote_document(
        {
            "quote_request": quote_request,
            "feasibility_result": feasibility_result,
            "historical_reference": historical_reference,
            "pricing_result": pricing_result,
        }
    )
    return {
        "prepare_result": prepare_result,
        "feasibility_result": feasibility_result,
        "historical_reference": historical_reference,
        "pricing_result": pricing_result,
        "quote_document": review_output.get("quote_document", {}),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the full quote agent pipeline.")
    parser.add_argument("--input", required=True, help="Input JSON file path")
    parser.add_argument("--output", help="Output JSON file path")
    parser.add_argument(
        "--skip-schema-validation",
        action="store_true",
        help="Skip input/output JSON Schema validation.",
    )
    args = parser.parse_args()

    payload = _load_json(args.input)
    if not args.skip_schema_validation:
        _validate_payload(payload, INPUT_SCHEMA_PATH, "input")

    result = orchestrate_quote(payload)
    if not args.skip_schema_validation:
        _validate_payload(result, OUTPUT_SCHEMA_PATH, "output")
        _validate_quote_document(result)

    if args.output:
        _dump_json(args.output, result)
        print(f"Wrote output to {Path(args.output)}")
        return

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
