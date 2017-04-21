#!/usr/bin/python

import base64
import Cookie
import datetime
import logging
import os
import urlparse

from common import constants
from common import util
from baseService import BaseService


class RegisterService(BaseService):
    NAME = "/register"

    def __init__(
        self,
        request_context,
        application_context,
    ):
        super(RegisterService, self).__init__(
            request_context,
            application_context,
        )

    def before_response_status(self):
        self._request_context["code"] = 301
        self._request_context["status"] = "Moved Permanently"

    def before_response_headers(self):
        qs = urlparse.parse_qs(self._request_context["parse"].query)
        
        self._register(
            qs["name"][0],
            qs["address"][0],
            int(qs["port"][0]),
        )

        self._request_context["response"] = '<a href="statistics">Back to Statistics</a>'

        self._request_context["response_headers"] = {
            'Cache-Control': 'no-cache, no-store, must-revalidate', 
            'Pragma': 'no-cache', 
            'Expires': '0',
            'Location': 'statistics',
        }
        super(RegisterService, self).before_response_headers()

    def _register(
        self,
        name,
        address,
        port,
    ):
        logging.info(
            "registring to %s on %s:%s" % (
                name,
                address,
                port,
            )
        )
        node = self._application_context["async_server"].add_node(
            name,
            address,
            port,
        )
