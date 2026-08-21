from __future__ import annotations

import hashlib
import math
import re
from http import HTTPStatus
from typing import List

import numpy as np
from openai import OpenAI

from config import DASHSCOPE_API_KEY, DASHSCOPE_BASE_URL, MODEL_PROVIDER


def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9_]+|[\u4e00-\u9fff]", text.lower())


def _mock_embedding(text: str, dimensions: int) -> list[float]:
    vector = [0.0] * dimensions
    for token in _tokens(text):
        digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
        index = int.from_bytes(digest[:4], "big") % dimensions
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        vector[index] += sign
    norm = math.sqrt(sum(value * value for value in vector)) or 1.0
    return [value / norm for value in vector]


def rerank_similarity(query: str, texts: list[str]):
    if not texts:
        return np.array([], dtype=float), None
    if MODEL_PROVIDER == "mock":
        query_tokens = set(_tokens(query))
        scores = []
        for text in texts:
            text_tokens = set(_tokens(text))
            denominator = len(query_tokens | text_tokens) or 1
            scores.append(len(query_tokens & text_tokens) / denominator)
        return np.array(scores, dtype=float), None

    if not DASHSCOPE_API_KEY:
        raise RuntimeError("DASHSCOPE_API_KEY 未配置")
    from dashscope import TextReRank

    response = TextReRank.call(
        api_key=DASHSCOPE_API_KEY,
        model="gte-rerank-v2",
        query=query,
        documents=texts,
        top_n=len(texts),
        return_documents=False,
    )
    if response.status_code != HTTPStatus.OK:
        raise RuntimeError(f"DashScope Rerank 失败: {response.code} {response.message}")
    scores = np.zeros(len(texts), dtype=float)
    for result in response.output.results:
        index = result.get("index") if isinstance(result, dict) else result.index
        score = (
            result.get("relevance_score", 0.0)
            if isinstance(result, dict)
            else result.relevance_score
        )
        scores[int(index)] = float(score)
    return scores, None


def generate_embedding(
    text: str | List[str],
    api_key: str | None = None,
    base_url: str | None = None,
    model_name: str = "text-embedding-v3",
    dimensions: int = 1024,
    encoding_format: str = "float",
    max_batch_size: int = 10,
):
    values = [text] if isinstance(text, str) else text
    if not isinstance(values, list):
        raise TypeError("text 必须是字符串或字符串列表")
    if MODEL_PROVIDER == "mock":
        embeddings = [_mock_embedding(value, dimensions) for value in values]
        return embeddings[0] if isinstance(text, str) else embeddings

    resolved_key = api_key or DASHSCOPE_API_KEY
    resolved_url = base_url or DASHSCOPE_BASE_URL
    if not resolved_key:
        raise RuntimeError("DASHSCOPE_API_KEY 未配置")
    client = OpenAI(api_key=resolved_key, base_url=resolved_url)
    embeddings: list[list[float]] = []
    for start in range(0, len(values), max_batch_size):
        batch = values[start : start + max_batch_size]
        completion = client.embeddings.create(
            model=model_name,
            input=batch,
            dimensions=dimensions,
            encoding_format=encoding_format,
        )
        batch_embeddings = [item.embedding for item in completion.data]
        if len(batch_embeddings) != len(batch):
            raise RuntimeError("Embedding 返回数量与请求数量不一致")
        embeddings.extend(batch_embeddings)
    return embeddings[0] if isinstance(text, str) else embeddings
