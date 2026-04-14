from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from embedding_provider import embed_texts, load_config_from_env, metadata
from skill import DEFAULT_HISTORY_PATH, _record_text_blob


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_CACHE_PATH = BASE_DIR / "data" / "historical_embeddings.cache.json"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build embedding cache for historical quote records."
    )
    parser.add_argument(
        "--output",
        default=str(DEFAULT_CACHE_PATH),
        help="Output cache JSON file path",
    )
    args = parser.parse_args()

    config = load_config_from_env()
    if config is None:
        raise RuntimeError("DASHSCOPE_API_KEY is required to build embedding cache.")

    records = _load_history_records()
    texts = [_record_text_blob(record) for record in records]
    embeddings = embed_texts(texts, config)

    payload = {
        "metadata": metadata(config),
        "records": [
            {
                "quote_id": str(record.get("quote_id") or ""),
                "content_hash": _content_hash(text),
                "text": text,
                "embedding": embedding,
            }
            for record, text, embedding in zip(records, texts, embeddings, strict=False)
        ],
    }

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"Wrote embedding cache to {output_path}")


def _load_history_records() -> list[dict[str, Any]]:
    data = json.loads(DEFAULT_HISTORY_PATH.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("Historical record file must be a JSON array.")
    return [item for item in data if isinstance(item, dict)]


def _content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


if __name__ == "__main__":
    main()
