#!/usr/bin/env python3

from __future__ import absolute_import

import os
import time
import logging

from six.moves import range

from automation import CommandSequence, TaskManager
from utils import get_urls_to_inspect, update_last_scanned

logging.basicConfig(
    format="[%(asctime)s][%(levelname)s] %(name)s - %(message)s",
    filename="inspect_streams.log",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def main():
    # The list of sites that we wish to crawl
    # days_ago_3 = int(time.time()) - 86400*3
    # update_last_scanned(days_ago_3)
    NUM_BROWSERS = 3
    before_scan_time = int(time.time())
    sites = get_urls_to_inspect(inspector="OpenWPM")

    # Loads the manager preference and 3 copies of the default browser dictionaries
    manager_params, browser_params = TaskManager.load_default_params(NUM_BROWSERS)

    # Update browser configuration (use this for per-browser settings)
    for i in range(NUM_BROWSERS):
        # Record HTTP Requests and Responses
        browser_params[i]["http_instrument"] = True
        # Enable flash for all three browsers
        browser_params[i]["disable_flash"] = False
        # Record js
        browser_params[i]["js_instrument"] = True
        browser_params[i]["headless"] = True

    # Update TaskManager configuration (use this for crawl-wide settings)
    dir_path = os.path.dirname(os.path.realpath(__file__)) + "/../data/"
    manager_params["data_directory"] = dir_path
    manager_params["log_directory"] = dir_path

    # Instantiates the measurement platform
    # Commands time out by default after 60 seconds
    manager = TaskManager.TaskManager(manager_params, browser_params)

    logger.info("Initialized browsers.")

    # Visits the sites with all browsers simultaneously
    for idx, site in enumerate(sites):
        logger.info("  {}...".format(site))
        command_sequence = CommandSequence.CommandSequence(site)

        # Start by visiting the page and sleeping for `sleep` seconds
        command_sequence.get(sleep=20, timeout=60)

        # Save screenshot
        command_sequence.save_screenshot(str(idx), timeout=60)

        # Save source
        command_sequence.dump_page_source(str(idx), timeout=60)

        # dump_profile_cookies/dump_flash_cookies closes the current tab.
        command_sequence.dump_profile_cookies(120)

        # index='**' synchronizes visits between the three browsers
        manager.execute_command_sequence(command_sequence, index="**")

    # Shuts down the browsers and waits for the data to finish logging
    manager.close()

    # TODO: Some check that inspection was successful
    if False:
        logger.info("Updating last_scanned time...")
        update_last_scanned(before_scan_time, inspector="OpenWPM")


if __name__ == "__main__":
    main()
