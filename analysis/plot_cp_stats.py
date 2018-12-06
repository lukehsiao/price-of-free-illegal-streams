import logging
from subprocess import DEVNULL, run

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import requests
import seaborn as sns
from bs4 import BeautifulSoup
from ipwhois import IPWhois
from matplotlib.backends.backend_pdf import PdfPages
from tqdm import tqdm

from utils import get_channel_providers, total_stream_urls, urls_per_channel_provider

logging.basicConfig(
    format="[%(asctime)s][%(levelname)s] %(name)s - %(message)s",
    filename="alexa.log",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


matplotlib.rcParams["text.usetex"] = True

sns.set(style="whitegrid")
sns.set_context("paper", font_scale=1.7)


def get_alexa_rank(base_url):
    """Return the alexa global rank as an integer.

    If unranked, return a very large integer
    """
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
        logger.error("Unable to find alexa rank on for {}".format(alexa_url))
        globalrank = 11e5
    except AttributeError:
        logger.error("Unable to find alexa rank on for {}".format(alexa_url))
        globalrank = 11e5

    return globalrank


def plot_alexa_distribution(data):
    """Plot the alexa distribution."""
    fig, ax = plt.subplots(figsize=(6, 4))

    df = data

    # Set up the matplotlib figure
    sns.despine()
    bins = np.arange(0, 12e5, 1e5)

    # Plot a histogram with all those ranked 1M+ grouped in a single bin
    plot = sns.distplot(
        np.clip(df["globalrank"], bins[0], bins[-1]),
        kde=False,
        hist=True,
        bins=bins,
        ax=ax,
    )
    plot.set(ylabel=r"\# Channel Providers")
    plot.set(xlabel=r"Alexa Global Rank")
    plt.xlim([0, 11e5])
    plt.xticks([0, 2e5, 4e5, 6e5, 8e5, 1e6, 1.1e6])
    plot.set_xticklabels(["0", "200K", "400K", "600K", "800K", "1M", "1M+"])

    outfile = "out.pdf"
    pp = PdfPages(outfile)
    pp.savefig(plot.get_figure().tight_layout())
    pp.close()
    run(["pdfcrop", outfile, outfile], stdout=DEVNULL, check=True)

    logger.info(
        "{}/{} channel providers NOT in the top million.".format(
            len(df[df["globalrank"] >= 1e6]), len(df["globalrank"])
        )
    )


def sanatize_data(data):
    """Merge the HOSTs which really are the same company."""

    # Remove the Nulls
    data.loc[data["host"].isnull(), "host"] = "N/A"

    data.loc[data["host"].str.contains("SC-QUASI"), "host"] = "SC-QUASI"

    data.loc[data["host"].str.contains("AMAZON"), "host"] = "AMAZON"

    data.loc[data["host"].str.contains("SERVERIUS"), "host"] = "NL_SERVERIUS"

    data.loc[data["host"].str.contains("GOOGLE"), "host"] = "GOOGLE"

    data.loc[data["host"].str.contains("AMANAH"), "host"] = "AMANAH"

    data.loc[data["host"].str.contains("DADDY"), "host"] = "GODADDY"

    data.loc[data["host"].str.contains("CLIENTID"), "host"] = "PRIVATELAYER"

    data.loc[data["host"].str.contains("PIHLTD"), "host"] = "PrivateInternetHosting"

    data.loc[data["host"].str.contains("HostPalace"), "host"] = "HOSTPALACE"
    data.loc[data["host"].str.contains("HOSTPALACE"), "host"] = "HOSTPALACE"

    data.loc[data["host"].str.contains("MAROSNET"), "host"] = "MAROSNET"

    data.loc[data["host"].str.contains("NAMEC"), "host"] = "NAMECHEAP"
    data.loc[data["host"].str.contains("NCNET"), "host"] = "NAMECHEAP"

    data.loc[data["host"].str.contains("IFASTNET"), "host"] = "IFASTNET"

    data.loc[data["host"].str.contains("HETZNER"), "host"] = "HETZNER"

    data.loc[data["host"].str.contains("DO-13"), "host"] = "DIGITALOCEAN"
    data.loc[data["host"].str.contains("DIGITALOCEAN-23"), "host"] = "DIGITALOCEAN"

    data.loc[data["host"].str.contains("OVH"), "host"] = "OVH"


def print_host_table(data, num_rows=10):
    """Output the LaTeX table corresponding to a summary of CP hosts.

    Hosting Company
    Host Country
    AS #
    # CP
    % Streams

    Example:
      Cloudflare     & US & 13335  & 77 & 49.5  \\
      Google         & US & 15169  & 37 & 1.03  \\
      HostPalace     & NL & 134512 & 9  & 0.664 \\
      Quasi Networks & SC & 29073  & 8  & 25.9  \\
      BlueAngelHost  & BG & 206349 & 7  & 0.255 \\
      Marosnet       & RU & 48666  & 6  & 0.470 \\
      Namecheap      & US & 22612  & 6  & 0.068 \\
      Lala Bhoola    & GB & 49453  & 4  & 0.399 \\

    :param num_rows: The number of rows to show.
    """
    sanatize_data(data)

    stats = {}
    for idx, row in data.iterrows():
        if row["host"] == "N/A":
            continue
        if row["host"] in stats:
            stats[row["host"]]["num_cps"] += 1
            stats[row["host"]]["cps"].add(row["base_url"])

            # check for inconsistencies
            if (
                row["host_country"]
                and stats[row["host"]]["country"] != row["host_country"]
            ):
                if not stats[row["host"]]["country"]:
                    stats[row["host"]]["country"] = row["host_country"]
                else:
                    logger.warning("{} != {}".format(stats[row["host"]], row))
        else:
            stats[row["host"]] = {
                "country": row["host_country"]
                if row["host_country"]
                else row["asn_country"],
                "as": row["asn_num"],
                "num_cps": 1,
                "cps": {row["base_url"]},
            }

    # Yes, there may be a slight change in total number in between these
    # queries, but that change is likely extremely small.
    stream_counts = urls_per_channel_provider()
    total = total_stream_urls()

    results = []
    # Calculate the stream percentages
    for key, value in stats.items():
        host_streams = 0
        for cp in value["cps"]:
            host_streams += stream_counts[cp]

        stats[key]["streams"] = host_streams

        results.append(
            (
                key,
                value["country"],
                value["as"],
                value["num_cps"],
                100 * host_streams / total,
            )
        )

    results.sort(key=lambda x: x[3], reverse=True)

    for host, country, asn, num_cps, percentage in results[:num_rows]:
        print(
            "{} & {} & {} & {} & {} \\\\".format(
                host, country, asn, num_cps, percentage
            )
        )


def fetch_channel_provider_data():
    """Add location and alexa rank information for a base_url.

    :rtype: Dataframe containing base_url, asn_num, asn_country, host_country,
        host, globalrank.
    """
    try:
        data = pd.read_pickle("cache/cp_data.pkl")
    except FileNotFoundError:
        url_map = {}
        for base_url, ip in tqdm(get_channel_providers()):
            try:
                logger.info("{}: {}".format(base_url, ip))
                obj = IPWhois(ip)
                results = obj.lookup_rdap(depth=1)
            except Exception:
                logger.warning("Skipping {}: {}".format(base_url, ip))
                continue

            asn = results["asn"]
            asn_country = results["asn_country_code"]
            host_country = results["network"]["country"]
            host = results["network"]["name"]

            new_entry = [
                base_url,
                asn,
                asn_country,
                host_country,
                host,
                get_alexa_rank(base_url),
            ]

            url_map[base_url] = new_entry

        # Make dataframe for plotting
        data = pd.DataFrame(
            list(url_map.values()),
            columns=[
                "base_url",
                "asn_num",
                "asn_country",
                "host_country",
                "host",
                "globalrank",
            ],
        )
        data.to_pickle("cache/cp_data.pkl")
    return data


def main():
    data = fetch_channel_provider_data()
    plot_alexa_distribution(data)
    print_host_table(data)


if __name__ == "__main__":
    main()
