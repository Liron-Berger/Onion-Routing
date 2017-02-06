#!/usr/bin/python

import base64
import Cookie
import datetime
import os
import urlparse

import constants
import util


class BaseService(object):
    NAME = "BaseService"

    def __init__(
        self,
        request_context,
        parse,
    ):
        self._request_context = request_context
        self._parse = parse

    def run(
        self,
    ):
        self._status()
        self._content()
        self._headers()

    def _status(
        self,
    ):
        self._request_context["code"] = 200
        self._request_context["status"] = "OK"

    def _headers(
        self,
    ):
        self._add_header(
            constants.CONTENT_TYPE,
            constants.MIME_MAPPING["html"],
        )
        self._add_header(
            constants.CONTENT_LENGTH,
            len(self._request_context["response"]),
        )

    def _content(
        self,
    ):
        pass

    def _add_header(
        self,
        header_title,
        header_content,
    ):
        self._request_context["response_headers"][header_title] = header_content

    def _add_cache(
        self,
    ):
        self._add_header(
            "Cache-Control",
            constants.HEADERS["Cache-Control"],
        )
        self._add_header(
            "Pragma",
            constants.HEADERS["Pragma"],
        )
        self._add_header(
            "Expires",
            constants.HEADERS["Expires"],
        )


class GetFileService(BaseService):
    NAME = "/GET"

    def __init__(
        self,
        request_context,
        parse,
        uri,
    ):
        super(GetFileService, self).__init__(
            request_context,
            parse,
        )

        file_name = os.path.normpath(
            os.path.join(
                '.',
                uri[1:],
            )
        )
        # I Should check this thing...
        if file_name[:len('.')+1] == '.' + '\\':
            raise RuntimeError("Malicious URI '%s'" % uri)
        
        self._file_name = file_name
    
    def _status(
        self,
    ):
        self._request_context["code"] = 200
        self._request_context["status"] = "OK"

    def _headers(
        self,
    ):
        with open(self._file_name, 'rb') as f:
            self._add_header(
                constants.CONTENT_TYPE,
                constants.MIME_MAPPING.get(
                    os.path.splitext(
                        self._file_name
                    )[1].lstrip('.'),
                    'application/octet-stream',
                )
            )
            self._add_header(
                constants.CONTENT_LENGTH,
                os.fstat(f.fileno()).st_size,
            )

    def _content(
        self,
    ):
        with open(self._file_name, 'rb') as f:
            while True:
                buf = f.read(constants.MAX_BUFFER_SIZE)
                if not buf:
                    break
                self._request_context["response"] += buf


class ClockService(BaseService):
    NAME = "/clock"

    def _content(
        self,
    ):
        self._request_context["response"] = util.text_to_html(
            datetime.datetime.now().strftime('%d-%m-%Y %H:%M:%S'),
        )


class MulService(BaseService):
    NAME = "/mul"

    def _content(
        self,
    ):
        parameters = urlparse.parse_qs(self._parse.query)
        self._request_context["response"] = str(int(parameters['a'][0]) * int(parameters['b'][0]))


class SecretService(BaseService):
    NAME = "/secret"

    def __init__(
        self,
        request_context,
        parse,
    ):
        super(SecretService, self).__init__(
            request_context,
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
        

class CounterService(BaseService):
    NAME = "/counter"

    def __init__(
        self,
        request_context,
        parse,
    ):
        super(CounterService, self).__init__(
            request_context,
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


class LoginService(BaseService):
    NAME = "/login"

    def __init__(
        self,
        request_context,
        parse,
    ):
        super(LoginService, self).__init__(
            request_context,
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
        

class Secret2Service(BaseService):
    NAME = "/secret2"

    def __init__(
        self,
        request_context,
        parse,
    ):
        super(Secret2Service, self).__init__(
            request_context,
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


class StaticsticsService(BaseService):
    NAME = "/statistics"

    def __init__(
        self,
        request_context,
        parse,
    ):
        super(StaticsticsService, self).__init__(
            request_context,
            parse,
        )

    def _content(
        self,
    ):
        if self._account:
            self._request_context["response"] = "welcome %s" % self._account
    
