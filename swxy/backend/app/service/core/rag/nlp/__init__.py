#
#  Derived from InfiniFlow/RAGFlow under the Apache License, Version 2.0.
#  https://www.apache.org/licenses/LICENSE-2.0
#

"""Tokenization and 128-token target chunk helpers used by the naive parser."""

from __future__ import annotations

import copy
import logging
import re

import chardet
from PIL import Image

from service.core.rag.utils import num_tokens_from_string
from . import rag_tokenizer


def is_english(texts) -> bool:
    if not texts:
        return False
    english = sum(
        bool(re.match(r"[ `a-zA-Z.,':;/\"?<>!()\-]", text.strip()))
        for text in texts
    )
    return english / len(texts) > 0.8


def tokenize(document: dict, text: str, english: bool) -> None:
    del english
    document["content_with_weight"] = text
    plain_text = re.sub(
        r"</?(table|td|caption|tr|th)( [^<>]{0,12})?>", " ", text
    )
    document["content_ltks"] = rag_tokenizer.tokenize(plain_text)
    document["content_sm_ltks"] = rag_tokenizer.fine_grained_tokenize(
        document["content_ltks"]
    )


def concat_img(first, second):
    if first is None:
        return second
    if second is None:
        return first
    width = max(first.size[0], second.size[0])
    image = Image.new("RGB", (width, first.size[1] + second.size[1]))
    image.paste(first, (0, 0))
    image.paste(second, (0, first.size[1]))
    return image


def naive_merge_docx(sections, chunk_token_num: int = 128, delimiter: str = "\n。；！？"):
    del delimiter
    if not sections:
        return [], []
    chunks = [""]
    images = [None]
    token_counts = [0]
    for text, image in sections:
        token_count = num_tokens_from_string(text)
        if token_counts[-1] > chunk_token_num:
            chunks.append(text)
            images.append(image)
            token_counts.append(token_count)
        else:
            chunks[-1] += text
            images[-1] = concat_img(images[-1], image)
            token_counts[-1] += token_count
    return chunks, images


def naive_merge(sections, chunk_token_num: int = 128, delimiter: str = "\n。；！？"):
    del delimiter
    if not sections:
        return []
    if isinstance(sections[0], str):
        sections = [(section, "") for section in sections]
    chunks = [""]
    token_counts = [0]
    for text, position in sections:
        position = position or ""
        token_count = num_tokens_from_string(text)
        if token_count < 8:
            position = ""
        if position and position not in text:
            text += position
        if token_counts[-1] > chunk_token_num:
            chunks.append(text)
            token_counts.append(token_count)
        else:
            chunks[-1] += text
            token_counts[-1] += token_count
    return chunks


ALL_CODECS = (
    "utf-8",
    "gb18030",
    "gbk",
    "gb2312",
    "utf-8-sig",
    "utf-16",
    "big5",
    "latin-1",
)


def find_codec(blob: bytes) -> str:
    detected = chardet.detect(blob[:4096])
    if detected.get("encoding") and float(detected.get("confidence") or 0) > 0.5:
        return str(detected["encoding"])
    for codec in ALL_CODECS:
        try:
            blob.decode(codec)
            return codec
        except (UnicodeDecodeError, LookupError):
            continue
    return "utf-8"


def add_positions(document: dict, positions) -> None:
    if not positions:
        return
    document["page_num_int"] = [int(item[0] + 1) for item in positions]
    document["top_int"] = [int(item[3]) for item in positions]
    document["position_int"] = [
        (
            int(page + 1),
            int(left),
            int(right),
            int(top),
            int(bottom),
        )
        for page, left, right, top, bottom in positions
    ]


def tokenize_table(tables, document: dict, english: bool, batch_size: int = 10):
    results: list[dict] = []
    for (image, rows), positions in tables:
        if not rows:
            continue
        if isinstance(rows, str):
            item = copy.deepcopy(document)
            tokenize(item, rows, english)
            if image:
                item["image"] = image
            add_positions(item, positions)
            results.append(item)
            continue
        delimiter = "; " if english else "； "
        for start in range(0, len(rows), batch_size):
            item = copy.deepcopy(document)
            text = delimiter.join(rows[start : start + batch_size])
            tokenize(item, text, english)
            item["image"] = image
            add_positions(item, positions)
            results.append(item)
    return results


def tokenize_chunks_docx(chunks, document: dict, english: bool, images):
    results: list[dict] = []
    for chunk, image in zip(chunks, images):
        if not chunk.strip():
            continue
        item = copy.deepcopy(document)
        item["image"] = image
        tokenize(item, chunk, english)
        results.append(item)
    return results


def tokenize_chunks(chunks, document: dict, english: bool, pdf_parser=None):
    results: list[dict] = []
    for chunk in chunks:
        if not chunk.strip():
            continue
        logging.debug("Chunk: %s", chunk)
        item = copy.deepcopy(document)
        if pdf_parser:
            try:
                item["image"], positions = pdf_parser.crop(
                    chunk, need_position=True
                )
                add_positions(item, positions)
                chunk = pdf_parser.remove_tag(chunk)
            except NotImplementedError:
                pass
        tokenize(item, chunk, english)
        results.append(item)
    return results
