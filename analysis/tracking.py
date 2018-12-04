#!/usr/bin/env python3

import sqlite3
import logging

from utils import EasyList

logging.basicConfig(
    format="[%(asctime)s][%(levelname)s] %(name)s - %(message)s",
    #  filename="tracking.log",
    level=logging.DEBUG,
)
logger = logging.getLogger(__name__)

DELIMITER = "~^~"


def get_third_parties(conn, easylist):

    third_parties = dict()
    c = conn.cursor()

    for row in c.execute(
        """
        SELECT
            s.visit_id,
            s.site_url,
            (
                SELECT group_concat(url, '{}')
                FROM http_requests AS r
                WHERE s.visit_id = r.visit_id AND r.is_third_party_channel = 1
            ) AS r_urls
        FROM site_visits AS s;
        """.format(
            DELIMITER
        )
    ):
        (visit_id, site_url, requests) = row

        if not requests:
            continue

        requests = requests.split(DELIMITER)

        logger.debug("{}: {}".format(site_url, requests))

        third_parties[site_url] = dict()
        third_parties[site_url]["total_domains"] = 0
        third_parties[site_url]["total_trackers"] = 0

        for request in requests:
            is_tracker = easylist.rules.should_block(request)
            third_parties[site_url][request] = is_tracker
            third_parties[site_url]["total_domains"] += 1
            if is_tracker:
                third_parties[site_url]["total_trackers"] += 1

    import pdb

    pdb.set_trace()
    return third_parties


def get_cookies(conn, easylist):

    cookies = dict()
    c = conn.cursor()

    for row in c.execute(
        """
        SELECT
            s.visit_id,
            s.site_url,
            (
                SELECT group_concat(baseDomain, '{}')
                FROM profile_cookies AS p
                WHERE s.visit_id = p.visit_id
            ) AS p_cookies
        FROM site_visits AS s;
        """.format(
            DELIMITER
        )
    ):
        (visit_id, site_url, cookie_domains) = row

        if not cookie_domains:
            continue

        cookie_domains = cookie_domains.split(DELIMITER)
        logger.debug("{}: {}".format(site_url, cookie_domains))

        cookies[site_url] = dict()
        cookies[site_url]["total_domains"] = 0
        cookies[site_url]["total_trackers"] = 0

        for cookie_domain in cookie_domains:
            is_tracker = easylist.rules.should_block(cookie_domain)
            cookies[site_url][cookie_domain] = is_tracker
            cookies[site_url]["total_domains"] += 1
            if is_tracker:
                cookies[site_url]["total_trackers"] += 1

    return cookies


def main():

    easylist = EasyList()
    conn = sqlite3.connect("../data/crawl-data.sqlite")

    cookies = get_cookies(conn, easylist)

    requests = get_third_parties(conn, easylist)

    #  import pdb
    #
    #  pdb.set_trace()

    # For each visited stream URL:
    #   Check associated cookies
    #   Compare against EasyPrivacy list
    #

    conn.close()


if __name__ == "__main__":
    main()
