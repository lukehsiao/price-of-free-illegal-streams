import csv
import logging
from pprint import pprint
from subprocess import DEVNULL, run

import matplotlib
import matplotlib.pyplot as plt
import pandas as pd
import requests
import seaborn as sns
from bs4 import BeautifulSoup
from ipwhois import IPWhois
from matplotlib.backends.backend_pdf import PdfPages

matplotlib.rcParams["text.usetex"] = True

sns.set(style="whitegrid")
sns.set_context("paper", font_scale=1.7)
logger = logging.getLogger(__name__)


def get_alexa_rank(base_url):
    """Return the alexa global rank as an integer."""
    # Ignore SSL errors
    alexa_url = "https://www.alexa.com/siteinfo/" + base_url

    page = requests.get(alexa_url)
    soup = BeautifulSoup(page.text, "html.parser")
    try:
        globalrank = int(
            soup.find("strong", {"class": "metrics-data align-vmiddle"})
            .text.strip()
            .replace(",", "")
        )
    except ValueError:
        globalrank = 999999999
    except AttributeError:
        import pdb

        pdb.set_trace()
    return globalrank


def plot_alexa_distribution():
    """Plot the alexa distribution."""
    fig, ax = plt.subplots(figsize=(6, 3))

    df = pd.read_csv("out.csv", sep=",")

    import pdb

    pdb.set_trace()
    # Set up the matplotlib figure
    sns.despine(left=True)

    # Plot a simple histogram with binsize determined automatically
    plot = sns.distplot(
        df["globalrank"],
        kde=False,
        bins=[0, 1e5, 2e5, 3e5, 4e5, 6e5, 7e5, 8e5, 9e5, 10e5],
        ax=ax,
    )
    plot.set(ylabel=r"\# Channel Providers")
    plot.set(xlabel=r"Alexa Global Rank")
    plot.set_xticklabels(["0", "0", "200K", "400K", "600K", "800K", "1M"])

    outfile = "out.pdf"
    pp = PdfPages(outfile)
    pp.savefig(plot.get_figure().tight_layout())
    pp.close()
    run(["pdfcrop", outfile, outfile], stdout=DEVNULL, check=True)


def get_csv():
    """Add location and alexa rank information for a base_url."""
    url_map = {}
    with open("snapshot.csv", "r") as csvfile:
        reader = csv.reader(csvfile)

        for row in reader:
            (
                url,
                base_url,
                aggregator,
                subreddit,
                reddit_user,
                mobile_compat,
                upvotes,
                created_on,
                last_access,
                access_count,
                ip,
                country,
            ) = row

            if base_url in url_map.keys():
                continue

            if ip:
                obj = IPWhois(ip)
                results = obj.lookup_rdap(depth=1)

                asn = results["asn"]
                asn_country = results["asn_country_code"]
                host_country = results["network"]["country"]
                host = results["network"]["name"]

                url_map[base_url] = [
                    base_url,
                    asn,
                    asn_country,
                    host_country,
                    host,
                    get_alexa_rank(base_url),
                ]

    pprint(url_map)
    pprint("Channel Providers: {}".format(len(url_map.keys())))

    with open("out.csv", "w") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(
            ["base_url", "asn_num", "asn_country", "host_country", "host", "globalrank"]
        )
        for key, value in url_map.items():
            writer.writerow(value)


def main():
    plot_alexa_distribution()
    #  get_csv()


if __name__ == "__main__":
    main()
