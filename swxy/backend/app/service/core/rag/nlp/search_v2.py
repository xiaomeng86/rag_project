#
#  Copyright 2024 The InfiniFlow Authors. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#

"""Keyword/vector retrieval and model reranking used by the chat service."""

from __future__ import annotations

from dataclasses import dataclass
import logging

import numpy as np

from service.core.rag.nlp import query, rag_tokenizer
from service.core.rag.nlp.model import generate_embedding, rerank_similarity
from service.core.rag.utils.doc_store_conn import (
    DocStoreConnection,
    FusionExpr,
    MatchDenseExpr,
    OrderByExpr,
)


def index_name(user_id: int | str) -> str:
    return f"gsk-user-{user_id}"


class Dealer:
    RERANK_PAGE_LIMIT = 3

    def __init__(self, dataStore: DocStoreConnection):
        self.qryr = query.FulltextQueryer()
        self.dataStore = dataStore

    @dataclass
    class SearchResult:
        total: int
        ids: list[str]
        query_vector: list[float]
        field: dict[str, dict]
        highlight: dict[str, str]
        aggregation: list
        keywords: list[str]

    def get_vector(self, text: str, topk: int = 10, similarity: float = 0.1):
        vector = generate_embedding(text)
        if np.asarray(vector).ndim != 1:
            raise RuntimeError("Query Embedding 必须是一维向量")
        values = [float(value) for value in vector]
        return MatchDenseExpr(
            f"q_{len(values)}_vec",
            values,
            "float",
            "cosine",
            topk,
            {"similarity": similarity},
        )

    @staticmethod
    def get_filters(request: dict) -> dict:
        filters: dict = {}
        for key, field in {"kb_ids": "kb_id", "doc_ids": "doc_id"}.items():
            if request.get(key) is not None:
                filters[field] = request[key]
        if request.get("available_int") is not None:
            filters["available_int"] = request["available_int"]
        return filters

    def search(
        self,
        request: dict,
        index_names: str | list[str],
        knowledgebase_ids: list[str],
        highlight: bool = False,
    ) -> SearchResult:
        page = int(request.get("page", 1)) - 1
        topk = int(request.get("topk", 1024))
        page_size = int(request.get("size", topk))
        offset = page * page_size
        fields = list(
            request.get(
                "fields",
                [
                    "docnm_kwd",
                    "content_ltks",
                    "kb_id",
                    "title_tks",
                    "important_kwd",
                    "position_int",
                    "doc_id",
                    "page_num_int",
                    "top_int",
                    "question_tks",
                    "available_int",
                    "content_with_weight",
                ],
            )
        )
        question = str(request.get("question", "")).strip()
        if not question:
            raise ValueError("检索问题不能为空")

        filters = self.get_filters(request)
        keyword_match, keywords = self.qryr.question(question, min_match=0.3)
        dense_match = self.get_vector(
            question,
            topk,
            float(request.get("similarity", 0.1)),
        )
        query_vector = list(dense_match.embedding_data)
        vector_field = dense_match.vector_column_name
        fields.append(vector_field)
        vector_weight = float(request.get("vector_similarity_weight", 0.6))
        fusion = FusionExpr(
            "weighted_sum",
            topk,
            {"weights": f"{1 - vector_weight}, {vector_weight}"},
        )
        expressions = [item for item in (keyword_match, dense_match, fusion) if item]
        highlights = ["content_ltks", "title_tks"] if highlight else []
        result = self.dataStore.search(
            fields,
            highlights,
            filters,
            expressions,
            OrderByExpr(),
            offset,
            page_size,
            index_names,
            knowledgebase_ids,
        )
        total = self.dataStore.getTotal(result)

        if total == 0:
            relaxed_keyword_match, _ = self.qryr.question(question, min_match=0.1)
            dense_match.extra_options["similarity"] = 0.05
            relaxed_expressions = [
                item for item in (relaxed_keyword_match, dense_match, fusion) if item
            ]
            result = self.dataStore.search(
                fields,
                highlights,
                filters,
                relaxed_expressions,
                OrderByExpr(),
                offset,
                page_size,
                index_names,
                knowledgebase_ids,
            )
            total = self.dataStore.getTotal(result)

        expanded_keywords = set(keywords)
        for keyword in keywords:
            expanded_keywords.update(
                token
                for token in rag_tokenizer.fine_grained_tokenize(keyword).split()
                if len(token) >= 2
            )
        keyword_list = list(expanded_keywords)
        logging.debug("Hybrid retrieval total: %s", total)
        return self.SearchResult(
            total=total,
            ids=self.dataStore.getChunkIds(result),
            query_vector=query_vector,
            field=self.dataStore.getFields(result, fields),
            highlight=self.dataStore.getHighlight(
                result, keyword_list, "content_with_weight"
            ),
            aggregation=self.dataStore.getAggregation(result, "docnm_kwd"),
            keywords=keyword_list,
        )

    def rerank_by_model(
        self,
        search_result: SearchResult,
        question: str,
        keyword_weight: float,
        vector_weight: float,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        _, keywords = self.qryr.question(question)
        tokenized_chunks: list[list[str]] = []
        original_chunks: list[str] = []
        for chunk_id in search_result.ids:
            chunk = search_result.field[chunk_id]
            content_tokens = str(chunk.get("content_ltks", "")).split()
            title_tokens = str(chunk.get("title_tks", "")).split()
            important = chunk.get("important_kwd", [])
            if isinstance(important, str):
                important = [important]
            tokenized_chunks.append(content_tokens + title_tokens + important)
            original_chunks.append(str(chunk.get("content_with_weight", "")))

        term_scores = np.asarray(
            self.qryr.token_similarity(keywords, tokenized_chunks), dtype=float
        )
        rerank_scores, _ = rerank_similarity(question, original_chunks)
        combined = keyword_weight * term_scores + vector_weight * rerank_scores
        return combined, term_scores, rerank_scores

    def retrieval(
        self,
        question: str,
        tenant_ids: list[str] | str,
        kb_ids: list[str],
        page: int,
        page_size: int,
        similarity_threshold: float = 0.1,
        vector_similarity_weight: float = 0.6,
        top: int = 1024,
        doc_ids: list[str] | None = None,
        highlight: bool = False,
    ) -> dict:
        request = {
            "kb_ids": kb_ids,
            "doc_ids": doc_ids,
            "size": max(page_size * self.RERANK_PAGE_LIMIT, 128),
            "question": question,
            "topk": top,
            "similarity": similarity_threshold,
            "available_int": 1,
            "vector_similarity_weight": vector_similarity_weight,
        }
        if page > self.RERANK_PAGE_LIMIT:
            request["page"] = page
            request["size"] = page_size
        if isinstance(tenant_ids, str):
            tenant_ids = tenant_ids.split(",")

        search_result = self.search(
            request,
            [index_name(tenant_id) for tenant_id in tenant_ids],
            kb_ids,
            highlight,
        )
        if search_result.total and page <= self.RERANK_PAGE_LIMIT:
            similarity, term_similarity, vector_similarity = self.rerank_by_model(
                search_result,
                question,
                1 - vector_similarity_weight,
                vector_similarity_weight,
            )
            indices = np.argsort(-similarity)[
                (page - 1) * page_size : page * page_size
            ]
        elif search_result.total:
            similarity = term_similarity = vector_similarity = np.ones(
                len(search_result.ids), dtype=float
            )
            indices = np.arange(len(search_result.ids))
        else:
            similarity = term_similarity = vector_similarity = np.array([], dtype=float)
            indices = np.array([], dtype=int)

        vector_field = f"q_{len(search_result.query_vector)}_vec"
        zero_vector = [0.0] * len(search_result.query_vector)
        chunks: list[dict] = []
        document_counts: dict[str, dict] = {}
        for index in indices:
            if float(similarity[index]) < similarity_threshold:
                break
            chunk_id = search_result.ids[int(index)]
            chunk = search_result.field[chunk_id]
            document_name = str(chunk.get("docnm_kwd", ""))
            document_id = str(chunk.get("doc_id", ""))
            item = {
                "chunk_id": chunk_id,
                "content_ltks": chunk.get("content_ltks", ""),
                "content_with_weight": chunk.get("content_with_weight", ""),
                "doc_id": document_id,
                "docnm_kwd": document_name,
                "kb_id": chunk.get("kb_id", ""),
                "important_kwd": chunk.get("important_kwd", []),
                "similarity": float(similarity[index]),
                "vector_similarity": float(vector_similarity[index]),
                "term_similarity": float(term_similarity[index]),
                "vector": chunk.get(vector_field, zero_vector),
                "positions": chunk.get("position_int", []),
            }
            if highlight:
                item["highlight"] = search_result.highlight.get(
                    chunk_id, item["content_with_weight"]
                )
            chunks.append(item)
            aggregate = document_counts.setdefault(
                document_name,
                {"doc_id": document_id, "count": 0},
            )
            aggregate["count"] += 1

        document_aggregations = [
            {"doc_name": name, **value}
            for name, value in sorted(
                document_counts.items(),
                key=lambda item: -item[1]["count"],
            )
        ]
        return {
            "total": search_result.total,
            "chunks": chunks[:page_size],
            "doc_aggs": document_aggregations,
        }
