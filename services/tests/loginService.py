#!/usr/bin/python

import base64
import Cookie
import datetime
import os
import urlparse

from common import constants
from common import util
from baseService import BaseService


class LoginService(BaseService):
    NAME = "/login"

    def __init__(
        self,
        request_context,
        application_context,
        parse,
    ):
        super(LoginService, self).__init__(
            request_context,
            application_context,
            parse,
        )
        self._cookie = Cookie.SimpleCookie()
        self._login = False

    def _headers(
        self,
    ):
        super(LoginService, self)._headers()
        if self._login:
            cookie_title, cookie_content = self._cookie.output().split(":", 1)
            self._add_header(
                cookie_title.strip(),
                cookie_content.strip(),
            )
            self._add_cache()

    def _content(
        self,
    ):
        parameters = urlparse.parse_qs(self._parse.query)
        account = parameters["Account"][0]
        if constants.ACCOUNTS.get(account) == parameters["Password"][0]:
            self._login = True
            random_cookie = base64.b64encode(os.urandom(64))
            self._cookie["login"] = random_cookie
            self._request_context["accounts"].setdefault(
                "account_cookies",
                {},
            )[random_cookie] = account

            self._request_context["response"] = '<a href="secret2">LOGIN</a>'
        else:
            self._request_context["response"] = 'You''ve entered a wrong password<a href="login.html">please login</a>'
