#!/usr/bin/python

import base64
import Cookie
import datetime
import os
import urlparse

from common import constants
from common import util
from baseService import BaseService


class DisconnectService(BaseService):
    NAME = "/disconnect"

    def __init__(
        self,
        request_context,
        application_context,
        parse,
    ):
        super(DisconnectService, self).__init__(
            request_context,
            application_context,
            parse,
        )

    def _content(
        self,
    ):
        parameters = urlparse.parse_qs(self._parse.query)
        connection = int(parameters["connection"][0])
        if connection in self._application_context["connections"]:
            entry = self._application_context["socket_data"][connection]
            entry["state"] = constants.PROXY_CLOSING
            self._application_context["socket_data"][entry["async_socket"].partner.socket.fileno()]["state"] = constants.PROXY_CLOSING

        self._request_context["response"] = '<a href="statistics">Back to Statistics</a>'
