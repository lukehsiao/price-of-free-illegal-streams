#!/usr/bin/env python3

import logging
import sqlite3
from pprint import pprint
from urllib.parse import urlparse

from tqdm import tqdm

logging.basicConfig(
    format="[%(asctime)s][%(levelname)s] %(name)s - %(message)s",
    filename="cookies.log",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def get_base_url(url):
    o = urlparse(url)
    return o.netloc


def get_font_fingerprinting(conn):
    """Return javascript which calls `measureText` method at least 50 times.

    The `measureText` method should be called on the same text string.
    """

    # Measure javascript which sets the `font` property to 50+ distinct values.
    # Measure which of those call `measureText` at least 50 times
    return


def main():

    conn = sqlite3.connect("../data/crawl-data.sqlite")

    get_font_fingerprinting(conn)

    conn.close()


if __name__ == "__main__":
    main()
