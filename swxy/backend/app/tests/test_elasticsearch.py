from __future__ import annotations

import json

import pytest

from service.core.rag.utils.doc_store_conn import (
    FusionExpr,
    MatchDenseExpr,
    MatchTextExpr,
    OrderByExpr,
)
from service.core.rag.utils.es_conn import ESConnection


class FakeIndices:
    def __init__(self):
        self.created = []

    def exists(self, index):
        return bool(self.created)

    def create(self, index, **mapping):
        self.created.append((index, mapping))


class FakeElasticsearch:
    def __init__(self, bulk_response=None):
        self.indices = FakeIndices()
        self.bulk_response = bulk_response
        self.bulk_operations = None
        self.search_body = None

    def bulk(self, operations, **_kwargs):
        self.bulk_operations = operations
        return self.bulk_response

    def search(self, **kwargs):
        self.search_body = kwargs["body"]
        return {"hits": {"total": {"value": 0}, "hits": []}}


def _connection(fake: FakeElasticsearch):
    connection = ESConnection()
    connection.es = fake
    return connection


def test_explicit_vector_mapping_and_successful_bulk():
    fake = FakeElasticsearch(
        {"errors": False, "items": [{"index": {"_id": "chunk-1", "status": 201}}]}
    )
    connection = _connection(fake)
    inserted = connection.insert(
        [{"id": "chunk-1", "q_1024_vec": [0.0] * 1024}], "gsk-user-1"
    )
    assert inserted == ["chunk-1"]
    assert fake.indices.created[0][1]["mappings"]["properties"]["q_1024_vec"] == {
        "type": "dense_vector",
        "index": True,
        "similarity": "cosine",
        "dims": 1024,
    }


def test_bulk_item_error_is_propagated():
    fake = FakeElasticsearch(
        {
            "errors": True,
            "items": [
                {"index": {"_id": "chunk-1", "status": 400, "error": {"type": "mapper"}}}
            ],
        }
    )
    with pytest.raises(RuntimeError, match="Bulk"):
        _connection(fake).insert([{"id": "chunk-1"}], "gsk-user-1")


def test_keyword_and_dense_queries_are_both_sent_to_elasticsearch():
    fake = FakeElasticsearch()
    connection = _connection(fake)
    connection.search(
        ["content_ltks", "q_1024_vec"],
        [],
        {"available_int": 1},
        [
            MatchTextExpr(["content_ltks"], "enterprise RAG", 128, {"minimum_should_match": 0.3}),
            MatchDenseExpr("q_1024_vec", [0.0] * 1024, "float", "cosine", 128, {"similarity": 0.1}),
            FusionExpr("weighted_sum", 128, {"weights": "0.4, 0.6"}),
        ],
        OrderByExpr(),
        0,
        128,
        "gsk-user-1",
        ["document-1"],
    )
    query = json.dumps(fake.search_body)
    assert "query_string" in query
    assert "q_1024_vec" in query
    assert '"boost": 0.4' in query
    assert '"boost": 0.6' in query
