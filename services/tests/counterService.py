#!/usr/bin/python

import base64
import Cookie
import datetime
import os
import urlparse

from common import constants
from common import util
from baseService import BaseService


class CounterService(BaseService):
    NAME = "/counter"

    def __init__(
        self,
        request_context,
        application_context,
        parse,
    ):
        super(CounterService, self).__init__(
            request_context,
            application_context,
            parse,
        )
        self._cookie = Cookie.SimpleCookie()

    def _headers(
        self,
    ):
        super(CounterService, self)._headers()
        cookie_title, cookie_content = self._cookie.output().split(":", 1)
        self._add_header(
            cookie_title.strip(),
            cookie_content.strip(),
        )
        self._add_cache()

    def _content(
        self,
    ):
        self._cookie.load(str(self._request_context["headers"].get("Cookie", "")))

        v = "0"
        if self._cookie.get("counter"):
            v = self._cookie.get("counter").value
            if v.isdigit():
                v = str(int(v) + 1)
        self._cookie["counter"] = v
        self._request_context["response"] = self._cookie["counter"].value
