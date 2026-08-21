from __future__ import annotations

import numpy as np

from service.chat_service import _number_citations, build_prompt
from service.core.rag.nlp.model import rerank_similarity
from service.core.rag.nlp.search_v2 import Dealer
from service.core.rag.utils.doc_store_conn import MatchDenseExpr, MatchTextExpr


class EmptyStore:
    def __init__(self):
        self.similarities = []

    def search(self, _fields, _highlights, _filters, matches, *_args, **_kwargs):
        dense = next(item for item in matches if isinstance(item, MatchDenseExpr))
        self.similarities.append(dense.extra_options["similarity"])
        return {}

    def getTotal(self, _result):
        return 0

    def getChunkIds(self, _result):
        return []

    def getHighlight(self, *_args):
        return {}

    def getAggregation(self, *_args):
        return []

    def getFields(self, *_args):
        return {}


class QueryStub:
    def question(self, _question, min_match=0.3):
        return MatchTextExpr(["content_ltks"], "query", 128, {"minimum_should_match": min_match}), ["query"]


def test_empty_recall_retry_lowers_similarity_threshold(monkeypatch):
    store = EmptyStore()
    dealer = Dealer(dataStore=store)
    dealer.qryr = QueryStub()
    monkeypatch.setattr(
        dealer,
        "get_vector",
        lambda *_args, **_kwargs: MatchDenseExpr(
            "q_1024_vec", [0.0] * 1024, "float", "cosine", 1024, {"similarity": 0.1}
        ),
    )
    dealer.search(
        {"page": 1, "size": 128, "topk": 1024, "question": "query", "vector": True, "similarity": 0.1},
        ["gsk-user-1"],
        ["document-1"],
    )
    assert store.similarities == [0.1, 0.05]


def test_mock_reranker_scores_more_relevant_chunks_higher():
    scores, _ = rerank_similarity(
        "enterprise RAG evidence",
        ["unrelated cooking recipe", "enterprise RAG evidence and citations"],
    )
    assert isinstance(scores, np.ndarray)
    assert scores[1] > scores[0]


def test_citations_start_at_one_and_prompt_contains_all_metadata():
    citations = _number_citations(
        [
            {
                "chunk_id": "chunk-a",
                "document_id": "doc-a",
                "document_name": "evidence.pdf",
                "content": "verifiable text",
                "score": 0.9,
                "positions": [[1, 0, 1, 0, 1]],
            }
        ]
    )
    assert citations[0]["citation_id"] == 1
    prompt = build_prompt("What is supported?", citations)
    assert "[1]" in prompt
    assert "chunk_id=chunk-a" in prompt
    assert "document_id=doc-a" in prompt
    assert "document_name=evidence.pdf" in prompt
