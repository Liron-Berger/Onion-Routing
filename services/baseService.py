#!/usr/bin/python

import base64
import Cookie
import datetime
import os
import urlparse

from common import constants
from common import util


class BaseService(object):
    NAME = "BaseService"

    def __init__(
        self,
        request_context,
        application_context,
        parse,
    ):
        self._request_context = request_context
        self._application_context = application_context
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
