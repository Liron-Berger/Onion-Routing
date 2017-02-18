#!/usr/bin/python

import base64
import Cookie
import datetime
import os
import urlparse

from common import constants
from common import util
from baseService import BaseService


class MulService(BaseService):
    NAME = "/mul"

    def _content(
        self,
    ):
        parameters = urlparse.parse_qs(self._parse.query)
        self._request_context["response"] = str(int(parameters['a'][0]) * int(parameters['b'][0]))
