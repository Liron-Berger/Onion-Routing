#!/usr/bin/python

import base64
import Cookie
import datetime
import os
import urlparse

from common import constants
from common import util
from baseService import BaseService

class Secret2Service(BaseService):
    NAME = "/secret2"

    def __init__(
        self,
        request_context,
        application_context,
        parse,
    ):
        super(Secret2Service, self).__init__(
            request_context,
            application_context,
            parse,
        )
        self._cookie = Cookie.SimpleCookie()
        self._account = ""

    def run(
        self,
    ):
        if "Cookie" in self._request_context["headers"].keys():
            self._cookie.load(str(self._request_context["headers"]["Cookie"]))

        v = self._cookie.get("login")
        if v:
            self._account = self._request_context["accounts"].get("account_cookies", {}).get(v.value)

        super(Secret2Service, self).run()

    def _status(
        self,
    ):
        if self._account:
            super(Secret2Service, self)._status()
        else:
            self._request_context["code"] = 301
            self._request_context["status"] = "Moved Permanently"

    def _headers(
        self,
    ):
        if self._account:
            super(Secret2Service, self)._headers()
        else:
            self._add_header("Location", "login.html")

    def _content(
        self,
    ):
        if self._account:
            self._request_context["response"] = "welcome %s" % self._account
