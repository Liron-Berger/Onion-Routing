#!/usr/bin/python

import base64
import Cookie
import datetime
import os
import urlparse

from common import constants
from common.utilities import util
from common.utilities import http_util
from registry_node.services import base_service


class MenuService(base_service.BaseService):
    NAME = "/"

    def before_request_headers(self):
        try:
            file_name = os.path.normpath(
                '%s%s' % (
                    self._application_context["base"],
                    "/homepage.html",
                )
            )
            fd = os.open(file_name, os.O_RDONLY, 0o666)
            self._request_context["response_headers"][constants.CONTENT_LENGTH] = os.fstat(fd).st_size
            self._request_context["response_headers"][constants.CONTENT_TYPE] = constants.MIME_MAPPING.get(
                    os.path.splitext(
                        file_name
                    )[1].lstrip('.'),
                    'application/octet-stream',
                )
            self._request_context["fd"] = fd
        except Exception as e:
            raise http_util.HTTPError(
                code=500,
                status="Internal Error",
                message=str(e),
            )

    def response(self):
        data = os.read(self._request_context["fd"], 100000 - len(self._request_context["response"]))
        if not data:
            return None
        return data