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

from __future__ import annotations

import json
import logging
import os
import re

from nltk.corpus import wordnet

from service.core.api.utils.file_utils import get_project_base_directory


class Dealer:
    def __init__(self):
        path = os.path.join(get_project_base_directory(), "rag/res", "synonym.json")
        try:
            with open(path, encoding="utf-8") as source:
                self.dictionary = json.load(source)
        except (OSError, json.JSONDecodeError):
            logging.debug("No local synonym dictionary; WordNet remains available")
            self.dictionary = {}

    def lookup(self, token: str) -> list[str]:
        if re.fullmatch(r"[a-z]+", token):
            values = {
                re.sub("_", " ", synonym.name().split(".")[0])
                for synonym in wordnet.synsets(token)
            }
            return sorted(value for value in values if value and value != token)
        values = self.dictionary.get(re.sub(r"[ \t]+", " ", token.lower()), [])
        return [values] if isinstance(values, str) else list(values)
