from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib import error, request


DEFAULT_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
DEFAULT_MODEL = "text-embedding-v4"
DEFAULT_DIMENSIONS = 1024
DEFAULT_TIMEOUT_SECONDS = 30
MAX_BATCH_SIZE = 10
DEFAULT_ENV_PATH = Path(__file__).resolve().parents[2] / ".env"


@dataclass(frozen=True)
class EmbeddingConfig:
    api_key: str
    base_url: str
    model: str
    dimensions: int
    timeout_seconds: int


class EmbeddingProviderError(RuntimeError):
    pass


def load_config_from_env() -> EmbeddingConfig | None:
    _load_env_file(DEFAULT_ENV_PATH)

    api_key = str(os.getenv("DASHSCOPE_API_KEY") or "").strip()
    if not api_key:
        return None

    base_url = str(os.getenv("DASHSCOPE_BASE_URL") or DEFAULT_BASE_URL).strip()
    model = str(os.getenv("HIST_EMBED_MODEL") or DEFAULT_MODEL).strip()
    dimensions_raw = str(
        os.getenv("HIST_EMBED_DIMENSIONS") or DEFAULT_DIMENSIONS
    ).strip()
    timeout_raw = str(
        os.getenv("HIST_EMBED_TIMEOUT_SECONDS") or DEFAULT_TIMEOUT_SECONDS
    ).strip()

    try:
        dimensions = int(dimensions_raw)
    except ValueError as exc:
        raise EmbeddingProviderError(
            f"Invalid HIST_EMBED_DIMENSIONS value: {dimensions_raw}"
        ) from exc

    try:
        timeout_seconds = int(timeout_raw)
    except ValueError as exc:
        raise EmbeddingProviderError(
            f"Invalid HIST_EMBED_TIMEOUT_SECONDS value: {timeout_raw}"
        ) from exc

    return EmbeddingConfig(
        api_key=api_key,
        base_url=base_url.rstrip("/"),
        model=model,
        dimensions=dimensions,
        timeout_seconds=max(timeout_seconds, 1),
    )


def _load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        env_key = key.strip()
        if not env_key or env_key in os.environ:
            continue
        env_value = value.strip().strip('"').strip("'")
        os.environ[env_key] = env_value


def embed_texts(texts: list[str], config: EmbeddingConfig) -> list[list[float]]:
    if not texts:
        return []

    embeddings: list[list[float]] = []
    for start in range(0, len(texts), MAX_BATCH_SIZE):
        batch = texts[start : start + MAX_BATCH_SIZE]
        embeddings.extend(_embed_batch(batch, config))
    return embeddings


def _embed_batch(texts: list[str], config: EmbeddingConfig) -> list[list[float]]:
    payload = {
        "model": config.model,
        "input": texts,
        "dimensions": config.dimensions,
    }
    endpoint = f"{config.base_url}/embeddings"
    request_obj = request.Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {config.api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with request.urlopen(request_obj, timeout=config.timeout_seconds) as response:
            body = response.read().decode("utf-8")
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise EmbeddingProviderError(f"Embedding HTTP {exc.code}: {detail}") from exc
    except error.URLError as exc:
        raise EmbeddingProviderError(f"Embedding request failed: {exc.reason}") from exc

    try:
        data = json.loads(body)
    except json.JSONDecodeError as exc:
        raise EmbeddingProviderError("Embedding response is not valid JSON") from exc

    items = data.get("data")
    if not isinstance(items, list):
        raise EmbeddingProviderError("Embedding response missing 'data' array")

    embeddings: list[list[float]] = []
    for item in items:
        if not isinstance(item, dict):
            raise EmbeddingProviderError("Embedding response item is not an object")
        vector = item.get("embedding")
        if not isinstance(vector, list):
            raise EmbeddingProviderError("Embedding response missing embedding vector")
        embeddings.append([float(value) for value in vector])

    if len(embeddings) != len(texts):
        raise EmbeddingProviderError(
            f"Embedding count mismatch: expected {len(texts)}, got {len(embeddings)}"
        )
    return embeddings


def metadata(config: EmbeddingConfig) -> dict[str, Any]:
    return {
        "provider": "aliyun_openai_compatible",
        "model": config.model,
        "dimensions": config.dimensions,
        "base_url": config.base_url,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
