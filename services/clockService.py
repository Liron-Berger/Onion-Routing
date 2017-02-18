#!/usr/bin/python

import base64
import Cookie
import datetime
import os
import urlparse

from common import constants
from common import util
from baseService import BaseService


class ClockService(BaseService):
    NAME = "/clock"

    def _content(
        self,
    ):
        self._request_context["response"] = util.text_to_html(
            datetime.datetime.now().strftime('%d-%m-%Y %H:%M:%S'),
        )
