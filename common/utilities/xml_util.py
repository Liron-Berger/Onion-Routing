#!/usr/bin/python
## @package onion_routing.common.utilities.xml_util
# utilities for handling the statistics xml file.
#

import logging
import os
import traceback

from common import constants
from common.utilities import util


## Xml handler.
#
# Manages the contents of the xml statistics service.
#
class XmlHandler(object):

    ## Constructor.
    # @param path (str) path for the xml file.
    # @param data (dict) dict with all data to store in xml.
    # @param type
    #
    # Creates new xml file.
    #
    def __init__(
        self,
        path,
        data,
        type,
    ):
        self._path = path
        self._fd = os.open(path, os.O_RDWR | os.O_CREAT, 0o666)
        self._data = data
        self._type = type

    ## Close xml file.
    # deletes the existing file.
    #
    def close(self):
        os.close(self._fd)
        os.remove(self._path)

    ## Update xml.
    # Deletes previous contents of the file.
    # Goes over the data and builds a new file.
    #
    def update(self):
        if self._type == constants.XML_CONNECTIONS:
            self._connections()
        elif self._type == constants.XML_NODES:
            self._nodes()
        else:
            raise RuntimeError("type not supprted, something wrong with xml.")

    ## Connections XML update.
    def _connections(self):
        os.lseek(self._fd, 0, os.SEEK_SET)
        util.write_file(
            self._fd,
            " " * os.stat(self._path).st_size,
        )
        os.lseek(self._fd, 0, os.SEEK_SET)

        connections = ""
        try:
            for c in self._data:
                connections += constants.XML_CONNECTION_BLOCK_LAYOUT % (
                    c.fileno(),
                    self._data[c]["in"]["fd"],
                    self._data[c]["in"]["bytes"],
                    self._data[c]["out"]["fd"],
                    self._data[c]["out"]["bytes"],
                )
        except Exception:
            logging.error(traceback.format_exc())

        xml = constants.XML_CONNECTION_LAYOUT % (
            len(self._data),
            connections,
        )

        util.write_file(
            self._fd,
            xml,
        )

    ## Nodes XML update.
    def _nodes(self):
        os.lseek(self._fd, 0, os.SEEK_SET)
        util.write_file(
            self._fd,
            " " * os.stat(self._path).st_size,
        )
        os.lseek(self._fd, 0, os.SEEK_SET)

        nodes = ""
        try:
            for port in self._data:
                nodes += constants.XML_NODES_BLOCK_LAYOUT % (
                    self._data[port],
                    port,
                )
        except Exception:
            logging.error(traceback.format_exc())

        xml = constants.XML_NODES_LAYOUT % (
            len(self._data),
            nodes,
        )

        util.write_file(
            self._fd,
            xml,
        )
