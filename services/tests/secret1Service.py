#!/usr/bin/python

import base64
import logging

from common import constants
from baseService import BaseService


class Secret1Service(BaseService):
    NAME = "/secret"

    def __init__(
        self,
        request_context,
        application_context,
    ):
        super(Secret1Service, self).__init__(
            request_context,
            application_context,
        )
        self._account = None

    def before_response_status(self):
        if constants.AUTHORIZATION in self._request_context["request_headers"]:
            type, authorization = self._request_context[
                "request_headers"
            ][constants.AUTHORIZATION].split(" ", 1)
            if type == "Basic":
                name, password = base64.b64decode(authorization).split(":", 1)
                if password == constants.ACCOUNTS.get(name):
                    self._account = name
        if not self._account:
            self._request_context["code"] = 401
            self._request_context["status"] = "Unauthorized"

    def before_response_headers(self):
        if not self._account:
            self._request_context["response_headers"] = {
                "WWW-Authenticate": "Basic",
            }
        else:
            self._request_context["response"] = "welcome %s!" % self._account
        super(Secret1Service, self).before_response_headers()

    def wanted_headers(self):
        return {
            constants.AUTHORIZATION,
        }
