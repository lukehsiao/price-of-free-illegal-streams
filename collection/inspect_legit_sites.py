#!/usr/bin/env python3

from __future__ import absolute_import

import os
import time
import logging
import json

from six.moves import range

from automation import CommandSequence, TaskManager
from utils import get_urls_to_inspect, update_last_scanned, GeoLocate
from selenium.webdriver.common.action_chains import ActionChains

logger = logging.getLogger(__name__)

linked_urls = {}


def click_on_page(num_clicks, **kwargs):
    """ Click all over the visited page and
        a) record additional sites visited as a result
        b) save downloads that occur in response
    """
    # Recover linked URLs from file
    global linked_urls
    try:
        with open("linked_urls_legit.txt", "r") as f:
            linked_urls_json = json.load(f)
            for key in linked_urls_json:
                linked_urls[key] = set(linked_urls_json[key])
    except OSError as e:
        # File doesn't exist - hasn't been created yet
        pass
    driver = kwargs['driver']
    driver.set_page_load_timeout(200) # This function can take awhile
    print("num_clicks requested:" + str(num_clicks))
    original_url = driver.current_url
    if original_url not in linked_urls:
        linked_urls[original_url] = set() # No duplicates
    time.sleep(5)
    while(num_clicks > 0):
        driver.find_element_by_tag_name('body').click()
        num_clicks -= 1
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
                    driver.maximize_window()
                    break
            time.sleep(5)
            print("Hidden redirect detected! URL: " + driver.current_url)
            linked_urls[original_url].add(driver.current_url)
            #Insert analysis of extra site here?
            driver.close()
            if len(driver.window_handles) > 1:
                print("ERROR closing tab")
                driver.close()
            driver.switch_to.window(driver.window_handles[0])
            time.sleep(5)
        else:
            print("No full screen redirect to new tab found.")
            # Now, check if click navigated me to a new website
            if driver.current_url != original_url:
                print("Direct redirect due to click")
                linked_urls[original_url].add(driver.current_url)
                # Now, go back to original page
                driver.get(original_url)

            break

    link_urls = [
        x for x in (
            element.get_attribute("href")
            for element in driver.find_elements_by_tag_name('a')
        )
    ]
    linked_urls[original_url].update(link_urls)
    #print("Directly linked urls:" + str(link_urls))
    print("linked urls dict: " + str(linked_urls))

    # Store updated JSON of linked_urls
    # First, must convert all sets to lists
    linked_url_json = {}
    if linked_urls:
        for key in linked_urls:
            linked_url_json[key] = list(linked_urls[key])
        with open('linked_urls_legit.txt', 'w+') as f:
            json.dump(linked_url_json, f)



def main():
    # First, load JSON of linked_urls from the past so we can update them.

    geo = GeoLocate()
    # The list of sites that we wish to crawl
    # The sites below have direct links to pages that stream video, where nothing changes based on auth
    # other than whether the video plays.
    # The NHL link is transient and must be updated pre-run
    # Other common sports streaming options such as nba league pass, nfl gamepass, etc. require a user
    # be authenticated to access the actual streaming page, so we do not consider those.
    sites = ['http://www.espn.com/watch/',
             'https://www.foxsportsgo.com/',
             'https://www.cbssports.com/live/',
             'https://www.tntdrama.com/watchtnt/east',
             'http://www.nba.com/nbatv',
             'https://www.willow.tv/',
             'https://www.nhl.com/tv/2018020458/221-2001288/63128703#']

    NUM_BROWSERS = 3

    # Loads the manager preference and 3 copies of the default browser dictionaries
    manager_params, browser_params = TaskManager.load_default_params(NUM_BROWSERS)

    # Update browser configuration (use this for per-browser settings)
    for i in range(NUM_BROWSERS):
        # Record HTTP Requests and Responses
        browser_params[i]["http_instrument"] = True
        browser_params[i]["cookie_instrument"] = True
        # Enable flash for all three browsers
        browser_params[i]["disable_flash"] = False
        # Record js
        browser_params[i]["js_instrument"] = True
        browser_params[i]["headless"] = True

    # Update TaskManager configuration (use this for crawl-wide settings)
    dir_path = os.path.dirname(os.path.realpath(__file__)) + "/../data_real_sites/"
    manager_params["data_directory"] = dir_path
    manager_params["log_directory"] = dir_path

    # Instantiates the measurement platform
    # Commands time out by default after 60 seconds
    manager = TaskManager.TaskManager(manager_params, browser_params)

    # Visits the sites with all browsers simultaneously
    for idx, site in enumerate(sites):
        command_sequence = CommandSequence.CommandSequence(site)

        # Start by visiting the page and sleeping for `sleep` seconds
        command_sequence.get(sleep=5, timeout=100)

        # Save screenshot
        command_sequence.save_screenshot(str(idx), timeout=100)

        # Save source
        command_sequence.dump_page_source(str(idx), timeout=100)

        # Click on links on page and record external links
        command_sequence.run_custom_function(click_on_page, (2,), 120)

        # dump_profile_cookies/dump_flash_cookies closes the current tab.
        command_sequence.dump_profile_cookies(120)

        # index='**' synchronizes visits between the three browsers
        manager.execute_command_sequence(command_sequence, index="**")

    # Now, visit all externally referenced URLs from the original websites w/o custom functions
    '''
    for url_set in linked_urls:
        for idx, site in enumerate(url_set):
            idx_real = idx + len(sites) # Offset index from prior loop
            command_sequence = CommandSequence.CommandSequence(site)

            # Start by visiting the page and sleeping for `sleep` seconds
            command_sequence.get(sleep=10, timeout=200)

            # dump_profile_cookies/dump_flash_cookies closes the current tab.
            command_sequence.dump_profile_cookies(120)

            # index='**' synchronizes visits between the three browsers
            manager.execute_command_sequence(command_sequence, index="**")
    '''

    # Shuts down the browsers and waits for the data to finish logging
    manager.close()
    geo.close()
    print("Finished scanning  legit sites.")


if __name__ == "__main__":
    main()
