import json
import os
from subprocess import DEVNULL, run

import matplotlib
import matplotlib.pyplot as plt
import pandas as pd
import psycopg2
import seaborn as sns
from matplotlib.backends.backend_pdf import PdfPages

matplotlib.rcParams["text.usetex"] = True
sns.set(style="whitegrid")
sns.set_context("paper", font_scale=1.7)
sns.set_palette(sns.color_palette("colorblind"))

GCSQL_PWD = os.environ["GCSQL_PWD"]


def fetch_agg_data(http=True):
    """Return aggregator tracking data

    :rtype: Dataframe containing aggregator, base_url, tracking.
    """
    entries = []
    cache = {}
    if http:
        with open("cache/third_parties.json", "r") as f:
            cache = json.load(f)
    else:
        with open("cache/cookies.json", "r") as f:
            cache = json.load(f)

    # Init db connection
    conn = psycopg2.connect(
        host="localhost",
        port="6543",
        dbname="postgres",
        user="postgres",
        password=GCSQL_PWD,
    )
    cur = conn.cursor()
    get_agg_cmd = "SELECT DISTINCT(aggregator) FROM stream_urls WHERE base_url = (%s)"

    for key, value in cache.items():
        trackers = value["total_trackers"]
        times_visited = value["times_visited"]

        cur.execute(get_agg_cmd, (key,))

        # Give each aggregator credit if they have the same CP
        aggregators = [_[0] for _ in cur.fetchall()]
        for aggregator in aggregators:

            new_entry = [aggregator, key, trackers / times_visited]

            entries.append(new_entry)

    #  entries = entries.sort(key=lambda x: x[2])
    # Make dataframe for plotting
    data = pd.DataFrame(entries, columns=["aggregator", "base_url", "ave_tracking"])
    return data.sort_values(["aggregator"], ascending=[True])


def gen_boxplots(data, http=True):
    """Routine for generating boxplots for each aggregator."""
    fig, ax = plt.subplots(figsize=(6, 4))

    df = data

    # Set up the matplotlib figure
    plot = sns.boxplot(x="ave_tracking", y="aggregator", orient="h", data=df)
    sns.despine(left=True, bottom=True, trim=True)

    plot.set(xlabel=r"Ave. \# Tracking")
    plot.set(ylabel=r"")
    #  plt.xticks(rotation="vertical")

    if http:
        outfile = "agg_track.pdf"
    else:
        outfile = "agg_cookies.pdf"
    pp = PdfPages(outfile)
    pp.savefig(plot.get_figure().tight_layout())
    pp.close()
    run(["pdfcrop", outfile, outfile], stdout=DEVNULL, check=True)
    return


def main():
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
    for agg, d, t, p, ttp in all_aggs_list[:num_rows]:
        print("{} & {:.2f} & {:.2f} \\\\".format(agg, p, ttp))
    print()

    all_aggs2 = {}
    for key, value in cookies.items():
        domains = value["total_domains"]
        trackers = value["total_trackers"]
        times_visited = value["times_visited"]

        cur.execute(get_agg_cmd, (key,))
        rows = cur.fetchall()
        aggregator = rows[0][0]
        if aggregator not in all_aggs2:
            all_aggs2[aggregator] = (domains, trackers, times_visited)
        else:
            all_aggs2[aggregator] = (
                all_aggs2[aggregator][0] + domains,
                all_aggs2[aggregator][1] + trackers,
                all_aggs2[aggregator][2] + times_visited,
            )

    all_aggs2_list = []
    for key in all_aggs2:
        value = all_aggs2[key]
        percentage = value[1] / value[0]
        trackers_per_page = value[1] / value[2]
        all_aggs2_list.append((key, value[0], value[1], percentage, trackers_per_page))

    all_aggs2_list.sort(key=lambda x: x[4], reverse=True)
    print("Cookie table for aggregators")
    for agg, d, t, p, ttp in all_aggs2_list[:num_rows]:  # [:num_rows]:
        print("{} & {:.2f} & {:.2f} \\\\".format(agg, p, ttp))

    cur.close()
    conn.close()


if __name__ == "__main__":
    data = fetch_agg_data(http=True)
    gen_boxplots(data, http=True)
    data = fetch_agg_data(http=False)
    gen_boxplots(data, http=False)
