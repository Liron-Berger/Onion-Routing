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

    def before_response_headers(self):
        try:
            qs = urlparse.parse_qs(self._request_context["parse"].query)
            result = int(qs['a'][0]) * int(qs['b'][0])
            message = util.text_to_html(
                "The result is %s" % (result)
            )
        except Exception as e:
            self._request_context["code"] = 500
            self._request_context["status"] = constants.INTERNAL_ERROR
            message = util.text_to_html(str(e))
        finally:
            self._request_context["response"] = message
            super(MulService, self).before_response_headers()