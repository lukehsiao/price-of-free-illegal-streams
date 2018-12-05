#!/usr/bin/env python3

import logging
import sqlite3
from pprint import pprint
from urllib.parse import urlparse

from tqdm import tqdm

from utils import EasyList

logging.basicConfig(
    format="[%(asctime)s][%(levelname)s] %(name)s - %(message)s",
    filename="tracking.log",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

DELIMITER = "~^~"


def get_base_url(url):
    o = urlparse(url)
    return o.netloc


def get_third_parties(conn, easylist):

    third_parties = dict()
    c = conn.cursor()

    for row in tqdm(
        list(
            c.execute(
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
            )
        )
    ):
        (visit_id, site_url, requests) = row

        if not requests:
            continue

        base_url = get_base_url(site_url)

        requests = requests.split(DELIMITER)

        logger.debug("{}: {}".format(site_url, requests))

        if base_url not in third_parties:
            third_parties[base_url] = dict()

        if "total_domains" not in third_parties[base_url]:
            third_parties[base_url]["requests"] = dict()
            third_parties[base_url]["total_requests"] = 0
            third_parties[base_url]["total_trackers"] = 0

        for request in requests:
            is_tracker = easylist.rules.should_block(request)
            third_parties[base_url]["requests"][request] = is_tracker
            third_parties[base_url]["total_requests"] += 1
            if is_tracker:
                third_parties[base_url]["total_trackers"] += 1

    return third_parties


def get_cookies(conn, easylist):

    cookies = dict()
    c = conn.cursor()

    for row in tqdm(
        list(
            c.execute(
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
            )
        )
    ):
        (visit_id, site_url, cookie_domains) = row

        if not cookie_domains:
            continue

        base_url = get_base_url(site_url)

        cookie_domains = cookie_domains.split(DELIMITER)
        logger.debug("{}: {}".format(site_url, cookie_domains))

        if base_url not in cookies:
            cookies[base_url] = dict()

        if "total_domains" not in cookies[base_url]:
            cookies[base_url]["domains"] = dict()
            cookies[base_url]["total_domains"] = 0
            cookies[base_url]["total_trackers"] = 0

        for cookie_domain in cookie_domains:
            is_tracker = easylist.rules.should_block(cookie_domain)
            cookies[base_url]["domains"][cookie_domain] = is_tracker
            cookies[base_url]["total_domains"] += 1
            if is_tracker:
                cookies[base_url]["total_trackers"] += 1

    return cookies


def latex_cookies(cookies, num_rows=10):
    all_cps = []
    for key, value in cookies.items():
        domains = value["total_domains"]
        trackers = value["total_trackers"]
        percentage = trackers / domains
        all_cps.append((key, domains, trackers, percentage))

    # sort by percentage
    all_cps.sort(key=lambda x: x[3], reverse=True)

    for cp, d, t, p in all_cps[:num_rows]:
        print("{} & {} & {} & {} \\\\".format(cp, d, t, p))


def latex_third_parties(third_parties, num_rows=10):
    all_cps = []
    for key, value in third_parties.items():
        domains = value["total_domains"]
        trackers = value["total_trackers"]
        percentage = trackers / domains
        all_cps.append((key, domains, trackers, percentage))

    # sort by percentage
    all_cps.sort(key=lambda x: x[3], reverse=True)

    for cp, d, t, p in all_cps[:num_rows]:
        print("{} & {} & {} & {} \\\\".format(cp, d, t, p))


def main():

    easylist = EasyList()
    conn = sqlite3.connect("../data/crawl-data.sqlite")

    cookies = get_cookies(conn, easylist)
    third_parties = get_third_parties(conn, easylist)

    latex_cookies(cookies)
    latex_third_parties(third_parties)

    conn.close()

    #  pprint(cookies)
    #  pprint(third_parties)


if __name__ == "__main__":
    main()
