import json
import psycopg2
import os
from psycopg2 import IntegrityError

GCSQL_PWD = os.environ["GCSQL_PWD"]


if __name__ == "__main__":

    num_rows = 10

    third_parties = {}
    cookies = {}
    with open("cache/third_parties.json", "r") as f:
        third_parties = json.load(f)

    with open("cache/cookies.json", "r") as f:
        cookies = json.load(f)

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
    for key, value in third_parties.items():
        requests = value["total_requests"]
        trackers = value["total_trackers"]
        times_visited = value["times_visited"]

        cur.execute(get_agg_cmd, (key,))
        rows = cur.fetchall()
        aggregator = rows[0][0]
        if aggregator not in all_aggs:
            all_aggs[aggregator] = (requests, trackers, times_visited)
        else:
            all_aggs[aggregator] = (
                all_aggs[aggregator][0] + requests,
                all_aggs[aggregator][1] + trackers,
                all_aggs[aggregator][2] + times_visited,
            )

    all_aggs_list = []
    #   print(all_aggs)
    for key in all_aggs:
        value = all_aggs[key]
        percentage = value[1] / value[0]
        trackers_per_page = value[1] / value[2]
        all_aggs_list.append((key, value[0], value[1], percentage, trackers_per_page))

    all_aggs_list.sort(key=lambda x: x[4], reverse=True)
    print("HTTP Request Table for aggregators")
    for agg, d, t, p, ttp in all_aggs_list[:num_rows]:  # [:num_rows]:
        print("{} & {:.2f} & {:.2f} \\\\".format(agg, p, ttp))
    print()

    all_aggs2 = {}
    for key, value in cookies.items():
        requests = value["total_domains"]
        trackers = value["total_trackers"]
        times_visited = value["times_visited"]
        # percentage = trackers / requests

        cur.execute(get_agg_cmd, (key,))
        rows = cur.fetchall()
        aggregator = rows[0][0]
        if aggregator not in all_aggs2:
            all_aggs2[aggregator] = (requests, trackers, times_visited)
        else:
            all_aggs2[aggregator] = (
                all_aggs2[aggregator][0] + requests,
                all_aggs2[aggregator][1] + trackers,
                all_aggs2[aggregator][2] + times_visited,
            )

    all_aggs2_list = []
    # print(all_aggs2)
    for key in all_aggs2:
        value = all_aggs2[key]
        percentage = value[1] / value[0]
        trackers_per_page = value[1] / value[2]
        all_aggs2_list.append((key, value[0], value[1], percentage, times_visited))

    all_aggs2_list.sort(key=lambda x: x[4], reverse=True)
    print("Cookie table for aggregators")
    for agg, d, t, p, ttp in all_aggs2_list[:num_rows]:  # [:num_rows]:
        print("{} & {:.2f} & {:.2f} \\\\".format(agg, p, ttp))

    cur.close()
    conn.close()
