#!/usr/bin/env python3
import os
import numpy as np
import psycopg2
import pickle
import logging
import json
import sqlite3
import matplotlib.pyplot as plt
from pprint import pprint
from urllib.parse import urlparse

from utils import EasyList

GCSQL_PWD = os.environ["GCSQL_PWD"]

logging.basicConfig(
    format="[%(asctime)s][%(levelname)s] %(name)s - %(message)s",
    filename="tracking.log",
    level=logging.DEBUG,
)
logger = logging.getLogger(__name__)

DELIMITER = "~^~"

DBNAME = "../data/crawl-data.sqlite"


def get_base_url(url):
    o = urlparse(url)
    return o.netloc


def get_third_parties(easylist):

    try:
        with open("cache/thid_parties.json") as handle:
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
                third_parties[base_url]["times_visited"] = 0

            third_parties[base_url]["times_visited"] += 1

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
        with open("cache/thid_parties.json", "w") as fp:
            json.dump(third_parties, fp)
        return third_parties


def get_cookies(easylist):

    try:
        with open("cache/cookies.json") as handle:
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
                cookies[base_url]["times_visited"] = 0

            cookies[base_url]["times_visited"] += 1

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
        with open("cache/cookies.json", "w") as fp:
            json.dump(cookies, fp)
    return cookies


def latex_cookies(cookies, num_rows=10):
    all_cps = []
    for key, value in cookies.items():
        domains = value["total_domains"]
        trackers = value["total_trackers"]
        trackers_per_page = trackers / value["times_visited"]
        percentage = (trackers / domains) * 100
        all_cps.append((key, domains, trackers, trackers_per_page, percentage))

    # sort by percentage
    all_cps.sort(key=lambda x: x[3], reverse=True)

    for cp, d, t, ttp, p in all_cps[:num_rows]:
        print("\\url{{{}}} & {} & {} & {:.2f} & {:.2f} \\\\".format(cp, d, t, ttp, p))

    return all_cps


def latex_third_parties(third_parties, num_rows=10):
    all_cps = []
    for key, value in third_parties.items():
        requests = value["total_requests"]
        trackers = value["total_trackers"]
        trackers_per_page = trackers / value["times_visited"]
        percentage = (trackers / requests) * 100
        all_cps.append((key, requests, trackers, trackers_per_page, percentage))

    # sort by percentage
    all_cps.sort(key=lambda x: x[4], reverse=True)

    for cp, d, t, ttp, p in all_cps[:num_rows]:
        print("\\url{{{}}} & {} & {} & {:.2f} & {:.2f} \\\\".format(cp, d, t, ttp, p))
    return all_cps


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


def calc_privacy_score(tp_list, cookie_list, num_rows=10):
    # First, import the fingerprinting data from the cache
    try:
        with open("cache/canvas_fingerprinting.pkl", "rb") as f:
            canvas_fingerprinting = pickle.load(f)

        with open("cache/webrtc_fingerprinting.pkl", "rb") as f:
            webrtc_fingerprinting = pickle.load(f)

        with open("cache/font_fingerprinting.pkl", "rb") as f:
            font_fingerprinting = pickle.load(f)

        scores = {}
        for cp, requests, trackers, trackers_per_page, percentage in tp_list:
            scores[cp] = 0.5 * trackers_per_page

        for cp, d, t, cookies_per_page, p in cookie_list:
            if cp in scores:
                scores[cp] += 3*cookies_per_page
            else:
                scores[cp] = 3*cookies_per_page

        cf = 0
        ff = 0
        wf = 0
        for key in scores:
            if key in canvas_fingerprinting:
                cf += 1
                scores[key] += 5
            if key in font_fingerprinting:
                ff += 1
                scores[key] += 5
            if key in webrtc_fingerprinting:
                wf += 1
                scores[key] += 5
        if cf != len(canvas_fingerprinting):
            print(f"Missing canvas fingerprint match! {len(canvas_fingerprinting) - cf} more than expected")

        if ff != len(font_fingerprinting):
            print(f"Missing font fingerprint match! {len(font_fingerprinting) - ff} more than expected")

        if wf != len(webrtc_fingerprinting):
            print(f"Missing webrt fingerprint match! {len(webrtc_fingerprinting) - wf} more than expected")

        return scores

    except FileNotFoundError:
        print("Please run fingerprinting.py prior to calculating the privacy score.")

        return {}


def agg_privacy_scores(scores):
    # Init db connection
    conn = psycopg2.connect(
        host="localhost",
        port="6543",
        dbname="postgres",
        user="postgres",
        password=GCSQL_PWD,
    )
    cur = conn.cursor()
    get_agg_cmd = "SELECT aggregator FROM stream_urls WHERE base_url = (%s)"
    all_aggs = {}
    for key in scores:
        cur.execute(get_agg_cmd, (key,))
        rows = cur.fetchall()
        aggregator = rows[0][0]
        if aggregator not in all_aggs:
            all_aggs[aggregator] = (scores[key], 1)
        else:
            all_aggs[aggregator] = (
                all_aggs[aggregator][0] + scores[key],
                all_aggs[aggregator][1] + 1,
            )
    agg_score_dict = {}
    for key in all_aggs:
        agg_score_dict[key] = all_aggs[key][0] / all_aggs[key][1]
    return agg_score_dict


def latex_privacy_scores(scores):
    all_cp_scores = []
    for key in scores:
        all_cp_scores.append((key, scores[key]))
    all_cp_scores.sort(key=lambda x: x[1], reverse=True)
    for key, value in all_cp_scores:
        print("\\url{{{}}} & {:.2f} \\\\".format(key, value))


def privacy_vs_upvotes(scores):
    # Init db connection
    conn = psycopg2.connect(
        host="localhost",
        port="6543",
        dbname="postgres",
        user="postgres",
        password=GCSQL_PWD,
    )
    cur = conn.cursor()
    get_votes_cmd = "SELECT AVG(upvotes) FROM stream_urls WHERE aggregator = 'reddit' AND base_url = (%s)"
    all_cps = {}
    for key in scores:
        cur.execute(get_votes_cmd, (key,))
        rows = cur.fetchall()
        if not rows[0][0]:
            # Stream not from reddit!
            continue
        avg_upvotes = rows[0][0]
        all_cps[key] = (avg_upvotes, scores[key])

    return all_cps


def latex_privacy_upvotes(scores):
    all_cp_scores = []
    for key in scores:
        all_cp_scores.append((key, scores[key][0], scores[key][1]))
    all_cp_scores.sort(key=lambda x: x[1], reverse=True)
    for key, votes, score in all_cp_scores:
        print("{:.2f} {:.2f} \\\\".format(votes, score))


    # Now, plot this data:
    colors = (0,0,0)
    y = [float(x[1]) for x in all_cp_scores]
    x = [float(x[2]) for x in all_cp_scores]
    plt.scatter(x, y, c=colors, alpha=0.5)
    z = np.polyfit(x, y, 1)
    p = np.poly1d(z)
    plt.plot(x, p(x), "r--")
    plt.title('Upvotes vs. Privacy Score')
    plt.ylabel('Average Upvotes')
    plt.xlabel('Privacy Score')
    plt.show()



def main():

    easylist = EasyList()

    cookies = get_cookies(easylist)
    print("Tracking Cookies per CP: ")
    all_cps_cook = latex_cookies(cookies)
    print()

    third_parties = get_third_parties(easylist)

    print("Tracking HTTP Requests per CP: ")
    all_cps_tp = latex_third_parties(third_parties)
    print()
    print("Most common trackers accessed: ")
    latex_most_common_trackers(third_parties)
    print()

    scores = calc_privacy_score(all_cps_tp, all_cps_cook)

    print("Top 10 CPs by privacy score:")
    latex_privacy_scores(scores)
    print()

    agg_scores = agg_privacy_scores(scores)

    print("Top 10 aggs by privacy score:")
    latex_privacy_scores(agg_scores)
    print()

    vote_scores = privacy_vs_upvotes(scores)
    print("Privacy score vs. upvotes:")
    latex_privacy_upvotes(vote_scores)


if __name__ == "__main__":
    main()
