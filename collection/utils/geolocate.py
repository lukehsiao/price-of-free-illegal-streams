import os
import geoip2.database
import logging

logger = logging.getLogger(__name__)


class GeoLocate:
    def __init__(self):
        """Setup geolocation."""
        self.reader = geoip2.database.Reader(
            os.path.dirname(os.path.realpath(__file__)) + "GeoLite2-City.mmdb"
        )

    def locate(self, ip):
        """Return country, iso_code for the given IP."""
        try:
            response = self.reader.country(ip)
        except geoip2.errors.AddressNotFoundError:
            logger.debug("Could not locate {}".format(ip))
            return None, None
        return response.country.name, response.country.iso_code

    def close(self):
        self.reader.close()
