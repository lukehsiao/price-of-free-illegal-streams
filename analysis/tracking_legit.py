#!/usr/bin/env python3

'''
This script is very similar to tracking.py, but works on the database of legimiate websites. Other than accessing different
files, it also eschews logic for grabbing the base_url, because for the legitimate websites the base url is often not even
directly associated with streaming, but with news etc.
'''

import logging
import json
import sqlite3
from pprint import pprint
from urllib.parse import urlparse

from utils import EasyList

logging.basicConfig(
    format="[%(asctime)s][%(levelname)s] %(name)s - %(message)s",
    filename="tracking.log",
    level=logging.DEBUG,
)
logger = logging.getLogger(__name__)

DELIMITER = "~^~"

DBNAME = "../data_real_sites/crawl-data.sqlite"


def get_base_url(url):
    o = urlparse(url)
    return o.netloc + o.path


def get_third_parties(easylist):

    try:
        with open("cache/thid_parties_real.json") as handle:
            third_parties = json.loads(handle.read())
            return third_parties
    except FileNotFoundError:
        conn = sqlite3.connect(DBNAME)
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

            base_url = get_base_url(site_url)

            requests = requests.split(DELIMITER)


            logger.debug("{}: {} requests".format(site_url, len(requests)))

            if base_url not in third_parties:
                third_parties[base_url] = dict()

            if "total_requests" not in third_parties[base_url]:
                third_parties[base_url]["requests"] = dict()
                third_parties[base_url]["total_requests"] = 0
                third_parties[base_url]["total_trackers"] = 0

            for request in requests:
                is_tracker = easylist.rules.should_block(request)
                third_parties[base_url]["requests"][request] = is_tracker
                third_parties[base_url]["total_requests"] += 1
                if is_tracker:
                    third_parties[base_url]["total_trackers"] += 1

        conn.close()
        with open("cache/thid_parties_real.json", "w") as fp:
            json.dump(third_parties, fp)
        return third_parties


def get_cookies(easylist):

    try:
        with open("cache/cookies_real.json") as handle:
            cookies = json.loads(handle.read())
            return cookies
    except FileNotFoundError:
        conn = sqlite3.connect(DBNAME)
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

            base_url = get_base_url(site_url)

            cookie_domains = cookie_domains.split(DELIMITER)
            logger.debug("{}: {} cookies".format(site_url, len(cookie_domains)))

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

        conn.close()
        with open("cache/cookies_real.json", "w") as fp:
            json.dump(cookies, fp)
    return cookies


def latex_cookies(cookies, num_rows=10):
    all_cps = []
    for key, value in cookies.items():
        domains = value["total_domains"]
        trackers = value["total_trackers"]
        percentage = (trackers / domains) * 100
        all_cps.append((key, domains, trackers, percentage))

    # sort by percentage
    all_cps.sort(key=lambda x: x[3], reverse=True)

    for cp, d, t, p in all_cps[:num_rows]:
        print("\\url{{{}}} & {} & {} & {:.2f} \\\\".format(cp, d, t, p))


def latex_third_parties(third_parties, num_rows=10):
    all_cps = []
    for key, value in third_parties.items():
        requests = value["total_requests"]
        trackers = value["total_trackers"]
        percentage = (trackers / requests) * 100
        all_cps.append((key, requests, trackers, percentage))

    # sort by percentage
    all_cps.sort(key=lambda x: x[3], reverse=True)

    for cp, d, t, p in all_cps[:num_rows]:
        print("\\url{{{}}} & {} & {} & {:.2f} \\\\".format(cp, d, t, p))


def latex_most_common_trackers(third_parties, num_rows=10):
    all_trackers = dict()
    total_tracking_domains = 0
    for key, value in third_parties.items():
        for domain, is_tracker in value["requests"].items():
            base_url = get_base_url(domain)
            if base_url not in all_trackers:
                all_trackers[base_url] = 0

            all_trackers[base_url] += 1
            total_tracking_domains += 1

    top_trackers = []
    for key, value in all_trackers.items():
        top_trackers.append((key, value, (value / total_tracking_domains) * 100))

    # sort by percentage
    top_trackers.sort(key=lambda x: x[2], reverse=True)

    for d, v, p in top_trackers[:num_rows]:
        print("\\url{{{}}} & {} & {:.2f} \\\\".format(d, v, p))


def main():

    easylist = EasyList()

    cookies = get_cookies(easylist)
    latex_cookies(cookies)

    third_parties = get_third_parties(easylist)
    print()
    latex_third_parties(third_parties)
    print()
    latex_most_common_trackers(third_parties)


if __name__ == "__main__":
    main()
