import logging
import os

import psycopg2

GCSQL_PWD = os.environ["GCSQL_PWD"]
logger = logging.getLogger(__name__)


def get_channel_providers():
    """Return each distinct base_url and its corresponding IP address.

    Note that this IP address is from the most recent access only.

    :rtype: List of (base_url, ip address)
    """
    conn = psycopg2.connect(
        host="localhost",
        port="6543",
        dbname="postgres",
        user="postgres",
        password=GCSQL_PWD,
    )

    cur = conn.cursor()

    # Only grab the most recent access IP
    select_cmd = (
        "SELECT DISTINCT ON (base_url) base_url, ip FROM stream_urls "
        "ORDER BY base_url, last_access DESC"
    )
    cur.execute(select_cmd)
    result = cur.fetchall()
    logger.info("Total channel_providers: {}".format(len(result)))

    cur.close()
    conn.close()
    return result


def urls_per_channel_provider():
    """Return the number of streams from this channel provider.

    :rtype: dict
    """
    conn = psycopg2.connect(
        host="localhost",
        port="6543",
        dbname="postgres",
        user="postgres",
        password=GCSQL_PWD,
    )

    cur = conn.cursor()

    # Only grab the most recent access IP
    select_cmd = "SELECT base_url, count(url) FROM stream_urls GROUP BY base_url"
    cur.execute(select_cmd)
    rows = cur.fetchall()

    result = {}
    for base_url, count in rows:
        result[base_url] = count

    cur.close()
    conn.close()
    return result


def total_stream_urls():
    conn = psycopg2.connect(
        host="localhost",
        port="6543",
        dbname="postgres",
        user="postgres",
        password=GCSQL_PWD,
    )

    cur = conn.cursor()

    # Only grab the most recent access IP
    select_cmd = "SELECT count(url) FROM stream_urls"
    cur.execute(select_cmd)
    result = cur.fetchone()[0]

    cur.close()
    conn.close()
    return result
