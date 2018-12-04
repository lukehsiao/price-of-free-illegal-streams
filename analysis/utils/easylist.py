"""Utilities for checking if a URL is on a blocklist."""

import os

from adblockparser import AdblockRules


class EasyList:
    def _read_raw_rules(self):
        """Read in the EasyList and EasyPrivacy."""
        path = os.path.dirname(os.path.realpath(__file__)) + "/easyprivacy.txt"

        with open(path) as f:
            raw_lines = f.read().splitlines()

            rules = AdblockRules(raw_lines)

            return rules

    def __init__(self):
        self.rules = self._read_raw_rules()
