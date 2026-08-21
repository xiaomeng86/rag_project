#
#  Copyright 2025 The InfiniFlow Authors. All Rights Reserved.
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

"""Elasticsearch adapter for the retained Bulk and hybrid-search path."""

from __future__ import annotations

import copy
import json
import logging
import os
import re

from elasticsearch import Elasticsearch, NotFoundError
from elasticsearch_dsl import Q, Search

from config import ES_HOST, ES_PASSWORD, ES_USER
from service.core.api.utils.file_utils import get_project_base_directory
from service.core.rag.nlp import is_english
from service.core.rag.utils import singleton
from service.core.rag.utils.doc_store_conn import (
    FusionExpr,
    MatchDenseExpr,
    MatchExpr,
    MatchTextExpr,
    OrderByExpr,
)


ATTEMPT_TIME = 2
logger = logging.getLogger("ragflow.es_conn")


@singleton
class ESConnection:
    def __init__(self):
        logger.info("Connecting to Elasticsearch at %s", ES_HOST)
        self.es = Elasticsearch(
            [ES_HOST],
            basic_auth=(ES_USER, ES_PASSWORD) if ES_USER else None,
            verify_certs=False,
            request_timeout=600,
        )
        mapping_path = os.path.join(
            get_project_base_directory(), "conf", "mapping.json"
        )
        with open(mapping_path, encoding="utf-8") as mapping_file:
            self.mapping = json.load(mapping_file)

    @staticmethod
    def index_name(user_id: int | str) -> str:
        return f"gsk-user-{user_id}"

    def health(self) -> bool:
        return bool(self.es.ping())

    def ensure_index(self, index_name: str) -> None:
        if not self.es.indices.exists(index=index_name):
            self.es.indices.create(index=index_name, **self.mapping)

    def getTotal(self, result) -> int:
        total = result["hits"]["total"]
        return int(total["value"] if isinstance(total, dict) else total)

    def getChunkIds(self, result) -> list[str]:
        return [str(hit["_id"]) for hit in result["hits"]["hits"]]

    def getHighlight(
        self,
        result,
        keywords: list[str],
        field_name: str,
    ) -> dict[str, str]:
        highlights: dict[str, str] = {}
        for hit in result["hits"]["hits"]:
            values = hit.get("highlight")
            if not values:
                continue
            text = "...".join(next(iter(values.values())))
            if not is_english(text.split()):
                highlights[str(hit["_id"])] = text
                continue
            text = re.sub(
                r"[\r\n]",
                " ",
                str(hit["_source"].get(field_name, "")),
                flags=re.IGNORECASE | re.MULTILINE,
            )
            excerpts: list[str] = []
            for sentence in re.split(r"[.?!;\n]", text):
                for word in keywords:
                    sentence = re.sub(
                        r"(^|[ .?/'\"()!,:;-])(%s)([ .?/'\"()!,:;-])"
                        % re.escape(word),
                        r"\1<em>\2</em>\3",
                        sentence,
                        flags=re.IGNORECASE | re.MULTILINE,
                    )
                if re.search(r"<em>[^<>]+</em>", sentence):
                    excerpts.append(sentence)
            highlights[str(hit["_id"])] = "...".join(excerpts) or text
        return highlights

    def getAggregation(self, result, field_name: str) -> list[tuple[str, int]]:
        aggregation_name = f"aggs_{field_name}"
        buckets = result.get("aggregations", {}).get(aggregation_name, {}).get(
            "buckets", []
        )
        return [(bucket["key"], bucket["doc_count"]) for bucket in buckets]

    def getFields(self, result, fields: list[str]) -> dict[str, dict]:
        selected: dict[str, dict] = {}
        if not fields:
            return selected
        for hit in result["hits"]["hits"]:
            source = hit.get("_source", {})
            values = {
                name: source[name]
                for name in fields
                if source.get(name) is not None
            }
            for name, value in values.items():
                if not isinstance(value, (str, list, dict)):
                    values[name] = str(value)
            if values:
                selected[str(hit["_id"])] = values
        return selected

    def insert(
        self,
        documents: list[dict],
        indexName: str,
        knowledgebaseId: str | None = None,
    ) -> list[str]:
        del knowledgebaseId
        operations: list[dict] = []
        for document in documents:
            if "id" not in document or "_id" in document:
                raise ValueError("Bulk 文档必须包含 id 且不能包含 _id")
            source = copy.deepcopy(document)
            document_id = source.pop("id")
            operations.extend(
                ({"index": {"_index": indexName, "_id": document_id}}, source)
            )

        self.ensure_index(indexName)
        response = self.es.bulk(
            operations=operations,
            refresh="wait_for",
            request_timeout=60,
        )
        failures: list[str] = []
        inserted_ids: list[str] = []
        for item in response.get("items", []):
            action = next(iter(item.values()))
            item_id = str(action.get("_id", "unknown"))
            if action.get("error") or int(action.get("status", 500)) >= 300:
                failures.append(
                    f"{item_id}: {action.get('error', action.get('status'))}"
                )
            else:
                inserted_ids.append(item_id)
        if response.get("errors") or failures:
            raise RuntimeError(
                "Elasticsearch Bulk 入库失败: " + "; ".join(failures[:5])
            )
        if len(inserted_ids) != len(documents):
            raise RuntimeError(
                f"Elasticsearch Bulk 返回数量异常: {len(inserted_ids)}/{len(documents)}"
            )
        return inserted_ids

    def search(
        self,
        selectFields: list[str],
        highlightFields: list[str],
        condition: dict,
        matchExprs: list[MatchExpr],
        orderBy: OrderByExpr,
        offset: int,
        limit: int,
        indexNames: str | list[str],
        knowledgebaseIds: list[str],
        aggFields: list[str] | None = None,
    ):
        index_names = indexNames.split(",") if isinstance(indexNames, str) else indexNames
        if not index_names:
            raise ValueError("Elasticsearch 索引不能为空")

        filters = {**condition, "kb_id": knowledgebaseIds}
        boolean_query = Q("bool", must=[])
        for field, value in filters.items():
            if field == "available_int":
                if value == 0:
                    boolean_query.filter.append(Q("range", available_int={"lt": 1}))
                else:
                    boolean_query.filter.append(
                        Q("bool", must_not=Q("range", available_int={"lt": 1}))
                    )
                continue
            if not value:
                continue
            if isinstance(value, list):
                boolean_query.filter.append(Q("terms", **{field: value}))
            elif isinstance(value, (str, int)):
                boolean_query.filter.append(Q("term", **{field: value}))
            else:
                raise TypeError(f"不支持的 Elasticsearch 过滤值: {field}={value!r}")

        search = Search()
        vector_weight = 0.5
        fusion = next(
            (
                expression
                for expression in matchExprs
                if isinstance(expression, FusionExpr)
                and expression.method == "weighted_sum"
            ),
            None,
        )
        if fusion and fusion.fusion_params.get("weights"):
            vector_weight = float(fusion.fusion_params["weights"].split(",")[1])

        for expression in matchExprs:
            if isinstance(expression, MatchTextExpr):
                minimum_match = expression.extra_options.get(
                    "minimum_should_match", 0.0
                )
                if isinstance(minimum_match, float):
                    minimum_match = f"{int(minimum_match * 100)}%"
                boolean_query.must.append(
                    Q(
                        "query_string",
                        fields=expression.fields,
                        type="best_fields",
                        query=expression.matching_text,
                        minimum_should_match=minimum_match,
                        boost=1,
                    )
                )
                boolean_query.boost = 1.0 - vector_weight
            elif isinstance(expression, MatchDenseExpr):
                search = search.knn(
                    expression.vector_column_name,
                    expression.topn,
                    expression.topn * 2,
                    query_vector=list(expression.embedding_data),
                    filter=boolean_query.to_dict(),
                    similarity=expression.extra_options.get("similarity", 0.0),
                    boost=vector_weight,
                )

        search = search.query(boolean_query)
        for field in highlightFields:
            search = search.highlight(field)
        if orderBy and orderBy.fields:
            orders: list[dict] = []
            for field, direction in orderBy.fields:
                order = "asc" if direction == 0 else "desc"
                if field in {"page_num_int", "top_int"}:
                    options = {
                        "order": order,
                        "unmapped_type": "float",
                        "mode": "avg",
                        "numeric_type": "double",
                    }
                elif field.endswith(("_int", "_flt")):
                    options = {"order": order, "unmapped_type": "float"}
                else:
                    options = {"order": order, "unmapped_type": "text"}
                orders.append({field: options})
            search = search.sort(*orders)
        for field in aggFields or []:
            search.aggs.bucket(f"aggs_{field}", "terms", field=field, size=1000000)
        if limit > 0:
            search = search[offset : offset + limit]

        query_body = search.to_dict()
        logger.debug("ES query for %s: %s", index_names, json.dumps(query_body))
        for attempt in range(ATTEMPT_TIME):
            try:
                result = self.es.search(
                    index=index_names,
                    body=query_body,
                    timeout="600s",
                    track_total_hits=True,
                    _source=True,
                )
                if str(result.get("timed_out", "")).lower() == "true":
                    raise TimeoutError("Elasticsearch 查询超时")
                return result
            except Exception as exc:
                if "timeout" in str(exc).lower() and attempt + 1 < ATTEMPT_TIME:
                    continue
                raise
        raise TimeoutError("Elasticsearch 查询超时")

    def delete_by_document(self, index_name: str, document_id: str) -> int:
        try:
            response = self.es.delete_by_query(
                index=index_name,
                body={"query": {"term": {"kb_id": document_id}}},
                refresh=True,
                conflicts="proceed",
            )
            return int(response.get("deleted", 0))
        except NotFoundError:
            return 0
