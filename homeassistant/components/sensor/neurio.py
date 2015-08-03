"""
homeassistant.components.sensor.neurio
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Gets the current power usage from a neurio sensor

Configuration:

To use the neurio sensor you will need to add something like the
following to your config/configuration.yaml

sensor:
  platform: neurio
  host: X.X.X.X

Variables:

host
*Required
The variable you wish to display. See the configuration example above for a
list of all available variables.
"""

from homeassistant.helpers.entity import Entity
import urllib
import logging

REQUIREMENTS = ['beautifulsoup4>=4.4.0']
_LOGGER = logging.getLogger(__name__)
OPTION_TYPES = {
    'host': 'Host'
""" Keeping this here for future use so that you can make a sensor per CT or perhaps extrapolate different data than just the current draw """
}


def setup_platform(hass, config, add_devices, discovery_info=None):
    """ Make sure beautifulsoup is installed """

    try:
        import bs4
    except ImportError:
        _LOGGER.error('Unable to import package bs4. Please install beautifulsoup4')
        return False

    soup = bs4.BeautifulSoup

    """ Make sure the host is defined. """
    dev = []
    if not config['host']:
        _LOGGER.error('No host specified in config')
    else:
        dev.append(NeurioPowerSensor(config['host'], soup))

    add_devices(dev)

# pylint: disable=too-few-public-methods
class NeurioPowerSensor(Entity):
    """ Implements a Neurio sensor. """

    def __init__(self, host, soup):
        self._name = 'Neurio Sensor'
        self._state = None
        self._host = host
        self._soup = soup
        self.update()

    @property
    def name(self):
        """ Returns the name of the device. """
        return self._name

    @property
    def state(self):
        """ Returns the state of the device. """
        return self._state

    def update(self):
        """ Gets the latest data and updates the states. """

        try: 
            html = urllib.request.urlopen('http://%s/both_tables.html' % self._host)
        except urllib.error.URLError as error:
            html = None
            _LOGGER.error(error)    

        parsed_data = self.parse_readings(html)
        current_total = self.get_total_draw(parsed_data)
        self._state = current_total

    def parse_readings(self, html):
        """ Parse the html returned by the page

        This may break if they structure of the page changes at any point.
        """
        bs = self._soup(html)
        parsed_tables = {}
        tables = bs.findAll('table')
        table_num = 0
        for table in tables:
            parsed_tables[table_num] = {}
            rows = table.findAll('tr')
            row_num = 0
            for row in rows:
                parsed_tables[table_num][row_num] = {}
                cols = row.findAll('td')
                col_num = 0
                for col in cols:
                    parsed_tables[table_num][row_num][col_num] = {}
                    value = col.text.replace('\n', '')
                    parsed_tables[table_num][row_num][col_num] = value
                    col_num += 1
                row_num += 1
            table_num += 1
        return parsed_tables    

    def get_total_draw(self, parsed_data):
        """ Get the raw measurements returned in a dictionary with channels
        """
        rm = parsed_data[0]
        raw_measurements = {}
        for index in [2, 3, 4, 5]:
            channel = rm[index][0]
            raw_measurements[channel] = {}
            for key, col_name in rm[1].items():
                raw_measurements[channel][col_name] = rm[index][key]
        total_draw = 0.0
        """ Add the useage for each CT to get the total value """
        for ct in raw_measurements:
            total_draw += float(raw_measurements[ct]['Power (W)'])
        total_draw = '%i' % int(total_draw) + 'W'
        return total_draw
