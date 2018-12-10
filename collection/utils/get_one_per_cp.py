import calendar
import psycopg2
import logging
from tqdm import tqdm
import os
import time

GCSQL_PWD = os.environ["GCSQL_PWD"]

logger = logging.getLogger(__name__)


def get_last_inspect(inspector="OpenWPM"):
    """Get the last time urls were scanned by OpenWPM

    Because we are using Google CloudSQL, in order for this to work,
    you must first run "./cloud_sql_proxy \
    -instances=sports-streaming-security:us-west1:cs356-streams=tcp:6543 \
    -credential_file=sports-streaming-security-64e6f13735d5.json" in another
    terminal to set up port forwarding as required. Note that the second argument
    in this command is the authentication file containing the private key for the
    GCP instance, which you must get from Hudson.
    More information can be found in db_setup.txt, in this directory.


    :param inspector: The name of the inspector scanning these urls
    :rtype: int
    """

    # TODO: Return errors if this fails
    conn = psycopg2.connect(
        host="localhost",
        port="6543",
        dbname="postgres",
        user="postgres",
        password=GCSQL_PWD,
    )
    cur = conn.cursor()
    select_cmd = (
        "SELECT scanned FROM last_inspect WHERE inspector = '" + inspector + "'"
    )
    cur.execute(select_cmd)
    rows = cur.fetchall()
    last_time = rows[0][0]
    cur.close()
    conn.close()
    logger.info(last_time)
    return calendar.timegm(last_time.timetuple())


def update_last_scanned(scan_time, inspector="OpenWPM"):
    """Save the last time urls were added to the postgres database.

    Because we are using Google CloudSQL, in order for this to work,
    you must first run "./cloud_sql_proxy \
    -instances=sports-streaming-security:us-west1:cs356-streams=tcp:6543 \
    -credential_file=sports-streaming-security-64e6f13735d5.json" in another
    terminal to set up port forwarding as required. Note that the second argument
    in this command is the authentication file containing the private key for the
    GCP instance, which you must get from Hudson.
    More information can be found in db_setup.txt, in this directory.

    This function returns positive on success, negative on failure

    :param inspector: The name of the inspector that scanned
    :param time: Unix timestamp of the last scan
    :rtype: int
    """

    # TODO: Return errors if this fails
    conn = psycopg2.connect(
        host="localhost",
        port="6543",
        dbname="postgres",
        user="postgres",
        password=GCSQL_PWD,
    )
    cur = conn.cursor()
    update_cmd = (
        "UPDATE last_inspect SET "
        "(scanned)"
        "= (%s) WHERE inspector = '" + inspector + "'"
    )
    cur.execute(update_cmd, (psycopg2.TimestampFromTicks(scan_time),))
    conn.commit()
    cur.close()
    conn.close()
    return 0


def get_urls_few_per_cp(inspector="OpenWPM"):
    """Get all new URLS since the last successful inspection

    :rtype: List of Strings
    """

    last_inspect_time = get_last_inspect(inspector=inspector)
    last_inspect_time = 0
    conn = psycopg2.connect(
        host="localhost",
        port="6543",
        dbname="postgres",
        user="postgres",
        password=GCSQL_PWD,
    )
    cur = conn.cursor()
    get_base_urls_cmd = "SELECT distinct base_url FROM stream_urls"
    cur.execute(get_base_urls_cmd)
    base_urls = [x[0] for x in cur.fetchall()]

    sites = []
    for base_url in tqdm(base_urls):
        get_urls_cmd = (
            "SELECT url, base_url, aggregator, created_on FROM stream_urls WHERE (last_access) > (%s) AND base_url = (%s) ORDER BY last_access DESC LIMIT 10"
        )
        cur.execute(get_urls_cmd, (psycopg2.TimestampFromTicks(last_inspect_time), base_url))
        rows = cur.fetchall()
        sites_by_cp = {}
        for row in rows:
            if row[2] == "reddit":
                # For reddit gathered streams we can use whether the stream was posted
                # between 1 hour and 3 hours ago as a proxy for the stream being live
                posted = calendar.timegm(row[3].timetuple())
                utcnow = int(time.time())
                # Only visit websites created between 1 and 5 hours ago
                if not (utcnow - posted > 3600 and utcnow - posted < 18000):
                    #continue
                    pass

            sites.append(row[0])
        logger.info(f"{last_inspect_time}")
        logger.info(f"{base_url} num_urls:{len(sites)}")

    return sites

if __name__=="__main__":
    get_urls_to_inspect()
