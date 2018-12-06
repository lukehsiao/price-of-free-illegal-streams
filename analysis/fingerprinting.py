#!/usr/bin/env python3
import logging
import json
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

DBNAME = "../data/crawl-data.sqlite"


def get_base_url(url):
    o = urlparse(url)
    return o.netloc


def query_javascript_symbol(conn, symbol):
    """Return visit_id, cp_url, script_url, symbol, operation, value, args."""
    c = conn.cursor()

    count = c.execute(
        f"""
        SELECT count(*)
        FROM site_visits AS s
        JOIN javascript as j ON s.visit_id = j.visit_id
        WHERE j.symbol like '%{symbol}%';
        """
    ).fetchone()[0]
    return (
        count,
        c.execute(
            f"""
            SELECT
                    s.visit_id,
                    s.site_url,
                    j.script_url,
                    j.symbol,
                    j.operation,
                    j.value,
                    j.arguments
            FROM site_visits AS s
            JOIN javascript as j ON s.visit_id = j.visit_id
            WHERE j.symbol like '%{symbol}%';
            """
        ),
    )


def get_font_fingerprinting():
    """Return javascript which calls `measureText` method at least 50 times.

    The `measureText` method should be called on the same text string.
    """

    try:
        with open("cache/font_fingerprinting.json") as handle:
            fingerprinting = json.loads(handle.read())
            return fingerprinting
    except FileNotFoundError:
        conn = sqlite3.connect(DBNAME)
        fingerprinting = dict()

        count, rows = query_javascript_symbol(conn, "window.navigator.userAgent")
        with tqdm(total=count) as pbar:
            for row in rows:
                (
                    visit_id,
                    site_url,
                    script_url,
                    symbol,
                    operation,
                    value,
                    arguments,
                ) = row

                base_url = get_base_url(site_url)
                pbar.update(1)

        conn.close()
        with open("cache/font_fingerprinting.json", "w") as fp:
            json.dump(fingerprinting, fp)

        return fingerprinting


def main():

    get_font_fingerprinting()


if __name__ == "__main__":
    main()
