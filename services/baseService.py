#!/usr/bin/python
import logging

from common import constants

class BaseService(object):
    NAME = "/base"

    def __init__(
        self,
        request_context,
        application_context,
    ):
        self._request_context = request_context
        self._application_context = application_context

    def before_request_headers(self):
        pass

    def before_request_content(self):
        self._request_context["content_length"] = int(
            self._request_context["request_headers"].get(constants.CONTENT_LENGTH, "0")
        )

    def handle_content(self):
        return False

    def before_response_status(self):
        pass

    def before_response_headers(self):
        if constants.CONTENT_LENGTH not in self._request_context["response_headers"]:
            self._request_context["response_headers"][constants.CONTENT_LENGTH] = len(
                    self._request_context["response"]
                )

    def before_response_content(self):
        pass

    def response(self):
        result = self._request_context.get("response")
        if result is not None:
            del self._request_context["response"]
        return result

    def before_terminate(self):
        pass
