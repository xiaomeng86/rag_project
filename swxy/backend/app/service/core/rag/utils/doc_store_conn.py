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

"""Query expressions used by the retained keyword/vector retrieval path."""

from __future__ import annotations

from typing import Protocol


class MatchTextExpr:
    def __init__(
        self,
        fields: list[str],
        matching_text: str,
        topn: int,
        extra_options: dict | None = None,
    ):
        self.fields = fields
        self.matching_text = matching_text
        self.topn = topn
        self.extra_options = extra_options or {}


class MatchDenseExpr:
    def __init__(
        self,
        vector_column_name: str,
        embedding_data: list[float],
        embedding_data_type: str,
        distance_type: str,
        topn: int = 10,
        extra_options: dict | None = None,
    ):
        self.vector_column_name = vector_column_name
        self.embedding_data = embedding_data
        self.embedding_data_type = embedding_data_type
        self.distance_type = distance_type
        self.topn = topn
        self.extra_options = extra_options or {}


class FusionExpr:
    def __init__(
        self,
        method: str,
        topn: int,
        fusion_params: dict | None = None,
    ):
        self.method = method
        self.topn = topn
        self.fusion_params = fusion_params or {}


MatchExpr = MatchTextExpr | MatchDenseExpr | FusionExpr


class OrderByExpr:
    def __init__(self):
        self.fields: list[tuple[str, int]] = []

    def asc(self, field: str):
        self.fields.append((field, 0))
        return self

    def desc(self, field: str):
        self.fields.append((field, 1))
        return self


class DocStoreConnection(Protocol):
    def search(self, *args, **kwargs): ...

    def getTotal(self, result) -> int: ...

    def getChunkIds(self, result) -> list[str]: ...

    def getFields(self, result, fields: list[str]) -> dict[str, dict]: ...

    def getHighlight(self, result, keywords: list[str], field_name: str) -> dict: ...

    def getAggregation(self, result, field_name: str) -> list: ...
