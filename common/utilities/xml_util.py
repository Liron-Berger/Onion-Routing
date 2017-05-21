#!/usr/bin/python
## @package onion_routing.common.utilities.xml_util
# utilities for handling the statistics xml file.
#

import logging
import os
import traceback

from common import constants


## Xml handler.
#
# Manages the contents of the xml statistics service.
#
class XmlHandler(object):

    ## Constructor.
    # @param path (str) path for the xml file.
    # @param connections (dict) data about all connections.
    #
    # Creates new xml file.
    #
    def __init__(
        self,
        path,
        connections,
    ):
        self._path = path
        self._fd = os.open(path, os.O_RDWR | os.O_CREAT, 0o666)
        self._connections = connections

    ## Close xml file.
    # deletes the existing file.
    #
    def close(self):
        os.close(self._fd)
        os.remove(self._path)

    ## Update xml.
    # Deletes previous contents of the file.
    # Goes over the connections and builds a new file.
    #
    def update(
        self,
    ):
        os.lseek(self._fd, 0, os.SEEK_SET)
        os.write(self._fd, " " * os.stat(self._path).st_size)
        os.lseek(self._fd, 0, os.SEEK_SET)

        connections = ""
        try:
            for c in self._connections:
                connections += constants.XML_CONNECTION_BLOCK_LAYOUT % (
                    c.fileno(),
                    self._connections[c]["in"]["fd"],
                    self._connections[c]["in"]["bytes"],
                    self._connections[c]["out"]["fd"],
                    self._connections[c]["out"]["bytes"],
                )
        except Exception:
            logging.error(traceback.format_exc())

        xml = constants.XML_LAYOUT % (
            len(self._connections),
            connections,
        )

        os.write(self._fd, xml)
