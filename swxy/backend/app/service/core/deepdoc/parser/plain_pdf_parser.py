#
#  Copyright 2025 The InfiniFlow Authors. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#

from __future__ import annotations

from io import BytesIO
import logging

from pypdf import PdfReader


class PlainParser:
    """Lightweight text-only PDF parser that does not initialize DeepDoc models."""

    def __call__(self, filename, from_page=0, to_page=100000, **_kwargs):
        self.outlines: list[tuple[str, int]] = []
        lines: list[str] = []
        try:
            self.pdf = PdfReader(
                filename if isinstance(filename, str) else BytesIO(filename)
            )
            for page in self.pdf.pages[from_page:to_page]:
                try:
                    text = page.extract_text(extraction_mode="layout") or ""
                except TypeError:  # compatibility with older pypdf releases
                    text = page.extract_text() or ""
                lines.extend(text.split("\n"))

            def collect(items, depth: int) -> None:
                for item in items:
                    if isinstance(item, dict):
                        self.outlines.append((item["/Title"], depth))
                    else:
                        collect(item, depth + 1)

            collect(self.pdf.outline, 0)
        except Exception:
            logging.exception("PDF text/outlines extraction failed")
        if not self.outlines:
            logging.debug("PDF has no outlines")
        return [(line, "") for line in lines if line], []

    def crop(self, _chunk, need_position):
        del need_position
        raise NotImplementedError

    @staticmethod
    def remove_tag(_text):
        raise NotImplementedError
