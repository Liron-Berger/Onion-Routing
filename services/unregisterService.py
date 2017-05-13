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


class UnregisterService(BaseService):
    NAME = "/unregister"

    def __init__(
        self,
        request_context,
        application_context,
    ):
        super(UnregisterService, self).__init__(
            request_context,
            application_context,
        )

    def before_response_status(self):
        self._request_context["code"] = 301
        self._request_context["status"] = "Moved Permanently"

    def before_response_headers(self):
        qs = urlparse.parse_qs(self._request_context["parse"].query)
        
        self._unregister(
            qs["name"][0],
        )

        self._request_context["response_headers"] = {
            'Cache-Control': 'no-cache, no-store, must-revalidate', 
            'Pragma': 'no-cache', 
            'Expires': '0',
            'Location': 'statistics',
        }
        super(UnregisterService, self).before_response_headers()

    def _unregister(
        self,
        name,
    ):
        logging.info(
            "unregistring %s" % (
                name,
            )
        )
        del self._application_context["registry"][name]
