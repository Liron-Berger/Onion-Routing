#!/usr/bin/python

import base64
import Cookie
import datetime
import os
import urlparse

from common import constants
from common import util
from baseService import BaseService


class Secret1Service(BaseService):
    NAME = "/secret"

    def __init__(
        self,
        request_context,
        application_context,
        parse,
    ):
        super(SecretService, self).__init__(
            request_context,
            application_context,
            parse,
        )
        self._account = None

    def run(
        self,
    ):
        if "Authorization" in self._request_context["headers"]:
            type, authorization = self._request_context["headers"]["Authorization"].split(" ", 1)
            if type == "Basic":
                name, password = base64.b64decode(authorization).split(":", 1)
                if password == constants.ACCOUNTS.get(name):
                    self._account = name
        super(SecretService, self).run()

    def _status(
        self,
    ):
        if not self._account:
            self._request_context["code"] = 401
            self._request_context["status"] = "Unauthorized"
        else:
            super(SecretService, self)._status()

    def _headers(
        self,
    ):
        if not self._account:
            self._add_header(
                "WWW-Authenticate",
                constants.HEADERS["WWW-Authenticate"],
            )
            self._add_cache()
        else:
            super(SecretService, self)._headers()

    def _content(
        self,
    ):
        if self._account:
            self._request_context["response"] = "welcome %s!" % self._account
