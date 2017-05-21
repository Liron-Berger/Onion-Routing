#!/usr/bin/python

import base64
import Cookie
import datetime
import os
import urlparse

from common import constants
from common.utilities import util
from registry_node.services import base_service

class FileService(base_service.BaseService):
    NAME = '/GET'

    def __init__(
        self,
        request_context,
        application_context,
    ):
        super(FileService, self).__init__(
            request_context,
            application_context,
        )

    def before_request_headers(self):
        try:
            file_name = os.path.normpath(
                '%s%s' % (
                    self._application_context["base"],
                    os.path.normpath(self._request_context["uri"]),
                )
            )
            fd = os.open(file_name, os.O_RDONLY)
            self._request_context["response_headers"][constants.CONTENT_LENGTH] = os.fstat(fd).st_size
            self._request_context["response_headers"][constants.CONTENT_TYPE] = constants.MIME_MAPPING.get(
                    os.path.splitext(
                        file_name
                    )[1].lstrip('.'),
                    'application/octet-stream',
                )
            self._request_context["fd"] = fd
        except Exception as e:
            raise util.HTTPError(500, "Internal Error", str(e))

    def response(self):
        data = os.read(self._request_context["fd"], 100000 - len(self._request_context["response"]))
        if not data:
            return None
        return data