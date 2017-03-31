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
    ):
        super(DisconnectService, self).__init__(
            request_context,
            application_context,
        )

    def before_response_status(self):
        self._request_context["code"] = 301
        self._request_context["status"] = "Moved Permanently"

    def before_response_headers(self):
        qs = urlparse.parse_qs(self._request_context["parse"].query)
        entry = self._application_context["socket_data"].get(
            int(qs["connection"][0]),
        )
        if entry in self._application_context["connections"]:
            entry.state = constants.CLOSING
            entry.partner.state = constants.CLOSING
        self._request_context["response"] = '<a href="statistics">Back to Statistics</a>'

        self._request_context["response_headers"] = {
            'Cache-Control': 'no-cache, no-store, must-revalidate', 
            'Pragma': 'no-cache', 
            'Expires': '0',
            'Location': 'statistics',
        }
        super(DisconnectService, self).before_response_headers()
