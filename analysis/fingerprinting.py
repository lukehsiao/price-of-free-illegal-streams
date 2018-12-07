#!/usr/bin/env python3
import ast
import logging
import pickle
import sqlite3
from urllib.parse import urlparse

from tqdm import tqdm

logging.basicConfig(
    format="[%(asctime)s][%(levelname)s] %(name)s - %(message)s",
    filename="fingerprinting.log",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

DBNAME = "../data/crawl-data.sqlite"


def get_base_url(url):
    o = urlparse(url)
    return o.netloc


def query_javascript(conn, where):
    """Return visit_id, cp_url, script_url, symbol, operation, value, args."""
    c = conn.cursor()

    count = c.execute(
        f"""
        SELECT count(*)
        FROM site_visits AS s
        JOIN javascript as j ON s.visit_id = j.visit_id
        {where};
        """
    ).fetchone()[0]
    query = f"""
            SELECT
                    s.visit_id,
                    s.site_url,
                    j.script_url,
                    j.symbol,
                    j.operation,
                    j.value,
                    j.arguments
            FROM site_visits AS s
            JOIN javascript as j ON s.visit_id = j.visit_id
            {where};
            """
    logger.info(f"SQL Query: {query}")
    return (count, c.execute(query))


def get_font_fingerprinting():
    """Return javascript which calls `measureText` method at least 50 times.

    The `measureText` method should be called on the same text string.
    """

    try:
        with open("cache/font_fingerprinting.pkl", "rb") as f:
            fingerprinting = pickle.load(f)
            return fingerprinting
    except FileNotFoundError:
        conn = sqlite3.connect(DBNAME)
        temp = dict()
        fingerprinting = set()

        count, rows = query_javascript(
            conn,
            """WHERE j.symbol LIKE '%CanvasRenderingContext2D.font%'
                     OR j.symbol LIKE '%CanvasRenderingContext2D.measureText%'
               ORDER BY s.visit_id
            """,
        )
        with tqdm(total=count) as pbar:
            for row in rows:
                (visit_id, site_url, script_url, symbol, operation, value, args) = row
                pbar.update(1)

                if site_url not in temp:
                    temp[site_url] = dict()

                if "symbols" not in temp[site_url]:
                    temp[site_url]["symbols"] = dict()

                if symbol not in temp[site_url]["symbols"]:
                    temp[site_url]["symbols"][symbol] = dict()

                if operation not in temp[site_url]["symbols"][symbol]:
                    temp[site_url]["symbols"][symbol][operation] = []

                temp[site_url]["symbols"][symbol][operation].append((value, args))

        conn.close()

        for key, value in tqdm(temp.items()):
            base_url = get_base_url(key)

            if base_url in fingerprinting:
                continue

            # Check for fingerprinting. If yes, add to set
            calls = temp[key]["symbols"]

            try:
                if len(calls["CanvasRenderingContext2D.measureText"]["call"]) >= 50:
                    import pdb

                    pdb.set_trace()
            except KeyError:
                # no call to measureText
                continue

            fingerprinting.add(base_url)

        with open("cache/font_fingerprinting.pkl", "wb") as fp:
            pickle.dump(fingerprinting, fp)

        return fingerprinting


def get_canvas_fingerprinting():
    """Find channel providers that do canvas fingerprinting."""

    try:
        with open("cache/canvas_fingerprinting.pkl", "rb") as f:
            fingerprinting = pickle.load(f)
            return fingerprinting
    except FileNotFoundError:
        conn = sqlite3.connect(DBNAME)
        temp = dict()
        fingerprinting = set()

        count, rows = query_javascript(
            conn,
            """WHERE j.symbol LIKE '%HTMLCanvasElement%'
                     OR j.symbol LIKE '%CanvasRenderingContext2D%'
               ORDER BY s.visit_id
            """,
        )
        with tqdm(total=count) as pbar:
            for row in rows:
                (visit_id, site_url, script_url, symbol, operation, value, args) = row
                pbar.update(1)

                # Skip irrelevant symbols
                if not any(
                    s in symbol
                    for s in [
                        "font",
                        "fillText",
                        "fillStyle",
                        "height",
                        "width",
                        "toDataURL",
                        "getImageData",
                        "save",
                        "restore",
                        "addEventListener",
                    ]
                ):
                    continue

                if site_url not in temp:
                    temp[site_url] = dict()

                if "symbols" not in temp[site_url]:
                    temp[site_url]["symbols"] = dict()

                if symbol not in temp[site_url]["symbols"]:
                    temp[site_url]["symbols"][symbol] = dict()

                if operation not in temp[site_url]["symbols"][symbol]:
                    temp[site_url]["symbols"][symbol][operation] = []

                temp[site_url]["symbols"][symbol][operation].append((value, args))

        conn.close()

        for key, value in tqdm(temp.items()):
            base_url = get_base_url(key)

            if base_url in fingerprinting:
                continue

            # Check for fingerprinting. If yes, add to set

            # MUST NOT call any of these
            if any(
                s in temp[key]["symbols"].keys()
                for s in [
                    "CanvasRenderingContext2D.save",
                    "CanvasRenderingContext2D.restore",
                    "HTMLCanvasElement.addEventListener",
                ]
            ):
                continue

            # MUST call one of these
            if not any(
                s in temp[key]["symbols"].keys()
                for s in [
                    "CanvasRenderingContext2D.getImageData",
                    "HTMLCanvasElement.toDataURL",
                ]
            ):
                continue

            # MUST call one of these
            if not any(
                s in temp[key]["symbols"].keys()
                for s in [
                    "CanvasRenderingContext2D.fillStyle",
                    "CanvasRenderingContext2D.fillText",
                ]
            ):
                continue

            calls = temp[key]["symbols"]

            # MUST NOT have height and width below 16px
            try:
                if any(
                    int(val[0]) <= 16 for val in calls["HTMLCanvasElement.width"]["set"]
                ):
                    continue
                if any(
                    int(val[0]) <= 16
                    for val in calls["HTMLCanvasElement.height"]["set"]
                ):
                    continue
            except KeyError:
                # Assuming the default canvas sive of 300x150px
                pass

            # If using getImageData, must get image > 16 x 16
            try:
                dims = calls["CanvasRenderingContext2D.getImageData"]["call"]
                too_small = True
                for val, args in dims:
                    args = ast.literal_eval(args)
                    if args["2"] >= 16 and args["3"] >= 16:
                        too_small = False
                        break
                if too_small:
                    continue
            except KeyError:
                pass

            # Finally, must write text to canvas with two colors or 10+ chars
            too_small = True
            try:
                cs = calls["CanvasRenderingContext2D.fillText"]["call"]
                total_chars = 0
                for val, args in cs:
                    args = ast.literal_eval(args)
                    total_chars += len(args["0"])
                    if total_chars >= 10:
                        too_small = False
                        break
            except KeyError:
                pass
            try:
                if len(calls["CanvasRenderingContext2D.fillStyle"]["set"]) >= 2:
                    too_small = False
            except KeyError:
                pass

            if too_small:
                continue

            fingerprinting.add(base_url)

        with open("cache/canvas_fingerprinting.pkl", "wb") as fp:
            pickle.dump(fingerprinting, fp)

        return fingerprinting


def main():

    canvas = get_canvas_fingerprinting()
    print("Canvas Fingerprinting:")
    for site in canvas:
        print(f"{site}")

    print("\n")

    font = get_font_fingerprinting()
    print("Font Fingerprinting:")
    for site in font:
        print(f"{site}")


if __name__ == "__main__":
    main()
