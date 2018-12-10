#!/usr/bin/env python3
import ast
import logging
import pickle
import sqlite3
from urllib.parse import urlparse

from tqdm import tqdm

logging.basicConfig(
    format="[%(asctime)s][%(levelname)s] %(name)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

DBNAME = "../data/crawl-data.sqlite"


def get_base_url(url):
    o = urlparse(url)
    return o.netloc


def get_all_sites(conn):
    c = conn.cursor()

    count = c.execute(
        f"""
        SELECT count(*)
        FROM site_visits
        """
    ).fetchone()[0]
    query = f"""
            SELECT site_url FROM site_visits
            """
    logger.info(f"SQL Query: {query}")
    return (count, c.execute(query))


def count_cps():
    """Find channel providers that do canvas fingerprinting."""

    all_cps = set()
    conn = sqlite3.connect(DBNAME)
    count, rows = get_all_sites(conn)
    with tqdm(total=count) as pbar:
        for row in rows:
            pbar.update(1)
            (site_url,) = row
            all_cps.add(get_base_url(site_url))

    conn.close()

    print(f"Total CPs: {len(all_cps)}")


def main():

    count_cps()


if __name__ == "__main__":
    main()
