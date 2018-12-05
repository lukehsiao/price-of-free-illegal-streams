import json
import psycopg2
import os
from psycopg2 import IntegrityError

GCSQL_PWD = os.environ["GCSQL_PWD"]


if __name__ == "__main__":

    third_parties = {}
    cookies = {}
    with open("third_parties.json", "r") as f:
        third_parties = json.load(f)

    with open("cookies.json", "r") as f:
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
        print(key)
        requests = value["total_requests"]
        trackers = value["total_trackers"]
        # percentage = trackers / requests

        cur.execute(get_agg_cmd, (key,))
        rows = cur.fetchall()
        aggregator = rows[0][0]
        print(aggregator)
        if aggregator not in all_aggs:
            all_aggs[aggregator] = (requests, trackers)
        else:
            all_aggs[aggregator] = (
                all_aggs[aggregator][0] + requests,
                all_aggs[aggregator][1] + trackers,
            )

    all_aggs_list = []
    print(all_aggs)
    for key in all_aggs:
        value = all_aggs[key]
        percentage = value[1] / value[0]
        all_aggs_list.append((key, value[0], value[1], percentage))

    all_aggs_list.sort(key=lambda x: x[3], reverse=True)
    for agg, d, t, p in all_aggs_list:  # [:num_rows]:
        print("{} & {} & {} & {} \\\\".format(agg, d, t, p))

    cur.close()
    conn.close()
