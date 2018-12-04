#!/usr/bin/env python3

from __future__ import absolute_import

import os
import time
import logging

from six.moves import range

from automation import CommandSequence, TaskManager
from utils import get_urls_to_inspect, update_last_scanned, GeoLocate
from selenium.webdriver.common.action_chains import ActionChains

logger = logging.getLogger(__name__)


def click_on_page(num_clicks, **kwargs):
    """ Click all over the visited page and
        a) record additional sites visited as a result
        b) save downloads that occur in response
    """
    driver = kwargs['driver']
    print("num_clicks requested:" + str(num_clicks))
    original_url = driver.current_url
    time.sleep(5)
    while(True):
        driver.find_element_by_tag_name('body').click()
        #ids = driver.find_elements_by_xpath('//*[@id]')
        '''
        for id in ids:
            print("clicking")
            id.click()
            time.sleep(2)
            #break
        '''
        time.sleep(5)
        og_window = driver.current_window_handle
        if len(driver.window_handles) > 1:
            for window in driver.window_handles:
                driver.switch_to.window(window)
                if driver.current_url != original_url:
                    print("hudson you suck")
                    driver.maximize_window()
                    break
            #new_window = [window for window in driver.window_handles if window != og_window][0]
            #driver.switch_to.window(new_window)
            #driver.maximize_window()
            time.sleep(5)
            print("Hidden redirect detected! URL: " + driver.current_url)
            #Insert analysis of extra site here?
            driver.close()
            driver.switch_to.window(og_window)
            time.sleep(5)
        else:
            print("No redirect found.")
            break

    link_urls = [
        x for x in (
            element.get_attribute("href")
            for element in driver.find_elements_by_tag_name('a')
        )
    ]
    print("Directly linked urls:" + str(link_urls))



def main():
    geo = GeoLocate()
    # The list of sites that we wish to crawl
    # days_ago_3 = int(time.time()) - 86400*3
    # update_last_scanned(days_ago_3)
    NUM_BROWSERS = 1
    before_scan_time = int(time.time())
    #sites = get_urls_to_inspect()
    #sites = sites[:5]
    # print(sites)
    sites = ['https://www.ibrod.tv/stream/ibrodtv46.html']
    #         'http://www.princeton.edu',
    #         'http://citp.princeton.edu/']

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
        browser_params[i]["headless"] = False

    # Update TaskManager configuration (use this for crawl-wide settings)
    dir_path = os.path.dirname(os.path.realpath(__file__)) + "/../data/"
    manager_params["data_directory"] = dir_path
    manager_params["log_directory"] = dir_path

    # Instantiates the measurement platform
    # Commands time out by default after 60 seconds
    manager = TaskManager.TaskManager(manager_params, browser_params)

    # Visits the sites with all browsers simultaneously
    for idx, site in enumerate(sites):
        command_sequence = CommandSequence.CommandSequence(site)

        # Start by visiting the page and sleeping for `sleep` seconds
        command_sequence.get(sleep=10, timeout=60)

        # Save screenshot
        command_sequence.save_screenshot(str(idx), timeout=60)

        # Save source
        command_sequence.dump_page_source(str(idx), timeout=60)
        command_sequence.run_custom_function(click_on_page, (2,))

        # dump_profile_cookies/dump_flash_cookies closes the current tab.
        command_sequence.dump_profile_cookies(120)

        # index='**' synchronizes visits between the three browsers
        manager.execute_command_sequence(command_sequence, index="**")

    # Shuts down the browsers and waits for the data to finish logging
    manager.close()
    geo.close()

    # TODO: Some check that inspection was successful
    if False:
        update_last_scanned(before_scan_time)


if __name__ == "__main__":
    main()
