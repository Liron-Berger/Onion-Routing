#!/usr/bin/python

import base64
import Cookie
import datetime
import os
import urlparse

from common import constants
from common.utilities import util
from registry_node.services import base_service


class DisconnectService(base_service.BaseService):
    NAME = "/disconnect"

    def before_response_status(self):
        self._request_context["code"] = 301
        self._request_context["status"] = "Moved Permanently"

    def before_response_headers(self):
        qs = urlparse.parse_qs(self._request_context["parse"].query)
        entry = self._request_context["app_context"]["socket_data"].get(
            int(qs["connection"][0]),
        )
        if entry in self._request_context["app_context"]["connections"]:
            entry.on_close()

        self._request_context["response_headers"] = {
            'Cache-Control': 'no-cache, no-store, must-revalidate', 
            'Pragma': 'no-cache', 
            'Expires': '0',
            'Location': 'statistics',
        }
        super(DisconnectService, self).before_response_headers()
