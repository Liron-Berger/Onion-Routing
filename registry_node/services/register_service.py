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


class RegisterService(base_service.BaseService):
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
        try:
            qs = urlparse.parse_qs(self._request_context["parse"].query)
            
            self._register(
                qs["address"][0],
                qs["port"][0],
                int(qs["key"][0]),
            )

            self._request_context["response"] = "success"
        except Exception:
            self._request_context["response"] = "fail"
            
        self._request_context["response_headers"] = {
            'Cache-Control': 'no-cache, no-store, must-revalidate', 
            'Pragma': 'no-cache', 
            'Expires': '0',
            'Location': 'statistics',
        }
        super(RegisterService, self).before_response_headers()

    def _register(
        self,
        address,
        port,
        key,
    ):
        logging.info(
            "registring %s:%s" % (
                address,
                port,
            )
        )
        self._application_context["registry"][port] = {
            "name": port,
            "address": address,
            "port": int(port),
            "key": key,
        }
        logging.info(
            "New node added: address %s, port %s" % (
                address,
                port,
            )
        )
