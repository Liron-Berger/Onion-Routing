#!/usr/bin/python

import base64
import Cookie
import logging
import os
import tempfile
import time
import urlparse

import constants
import util
import datetime

class BaseService(object):
    NAME = "BaseService"

    HEADERS = {}

    def __init__(
        self,
    ):
        pass

    def run(
        self,
        request_context,
    ):
        if constants.CONTENT_LENGTH not in request_context["headers"]:
            request_context["headers"][constants.CONTENT_LENGTH] = len(
                request_context["response"]
            )


class ClockService(BaseService):
    NAME = "/clock"

    def __init__(
        self,
    ):
        super(ClockService, self).__init__()

    def status(
        self,
        request_context,
    ):
        request_context["code"] = 200
        request_context["status"] = "OK"

    def headers(
        self,
        request_context,
    ):
        request_context["response"] = util.text_to_html(
            datetime.datetime.now().strftime('%d-%m-%Y %H:%M:%S'),
        )
        request_context["headers"] = {}
        request_context["headers"][constants.CONTENT_TYPE] = constants.MIME_MAPPING["html"]
        request_context["headers"][constants.CONTENT_LENGTH] = len(request_context["response"])

    def content(
        self,
        request_context,
    ):
        pass
