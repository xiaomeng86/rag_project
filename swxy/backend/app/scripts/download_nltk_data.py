"""Download only the NLTK corpora used by the tokenizer, with bounded retries."""

from __future__ import annotations

import sys
import time

from nltk.downloader import Downloader


DOWNLOAD_DIR = "/nltk_data"
PACKAGES = ("punkt", "punkt_tab", "wordnet")
MAX_ATTEMPTS = 3


def main() -> int:
    downloader = Downloader(download_dir=DOWNLOAD_DIR)
    for package in PACKAGES:
        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                if downloader.download(package, quiet=True, raise_on_error=True):
                    break
            except Exception as exc:  # Build output needs the concrete upstream error.
                if attempt == MAX_ATTEMPTS:
                    print(f"Failed to download NLTK package {package}: {exc}", file=sys.stderr)
                    return 1
                time.sleep(attempt * 2)
        else:
            print(f"Failed to download NLTK package {package}", file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
