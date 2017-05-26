#!/usr/bin/python

import base64
import Cookie
import datetime
import os
import urlparse
import logging

from common import constants
from common.utilities import util
from registry_node.services import base_service


class UnregisterService(base_service.BaseService):
    NAME = "/unregister"

    def before_response_headers(self):
        qs = urlparse.parse_qs(self._request_context["parse"].query)
        
        self._unregister(
            qs["port"][0],
        )
        self._request_context["response"] = "unregistered"

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
        if name in self._request_context["app_context"]["registry"]:
            del self._request_context["app_context"]["registry"][name]
