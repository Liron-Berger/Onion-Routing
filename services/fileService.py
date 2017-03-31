#!/usr/bin/python
import os

from common import constants
from common import util
from baseService import BaseService

class FileService(BaseService):
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
                    "./",
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
        data = os.read(self._request_context["fd"], constants.MAX_BUFFER_SIZE - len(self._request_context["response"]))
        if not data:
            return None
        return data