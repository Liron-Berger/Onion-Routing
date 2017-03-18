#!/usr/bin/python
import time

from common import constants
from common import util
from baseService import BaseService

class ClockService(BaseService):
    NAME = "/clock"

    def __init__(
        self,
        request_context,
        application_context,
    ):
        super(ClockService, self).__init__(
            request_context,
            application_context,
        )

    def before_response_headers(self):
        message = util.text_to_html(
            time.strftime("%H:%M:%S", time.localtime())
        )
        self._request_context["response"] = message
        self._request_context["response_headers"][constants.CONTENT_TYPE] = "text/html"
        super(ClockService, self).before_response_headers()
