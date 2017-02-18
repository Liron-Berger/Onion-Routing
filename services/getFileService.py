#!/usr/bin/python

import base64
import Cookie
import datetime
import os
import urlparse

from common import constants
from common import util
from baseService import BaseService


class GetFileService(BaseService):
    NAME = "/GET"

    def __init__(
        self,
        request_context,
        application_context,
        parse,
        uri,
    ):
        super(GetFileService, self).__init__(
            request_context,
            application_context,
            parse,
        )

        file_name = os.path.normpath(
            os.path.join(
                '.',
                uri[1:],
            )
        )
        # TODO: I Should check this thing...
        if file_name[:len('.')+1] == '.' + '\\':
            raise RuntimeError("Malicious URI '%s'" % uri)
        
        self._file_name = file_name
    
    def _status(
        self,
    ):
        self._request_context["code"] = 200
        self._request_context["status"] = "OK"

    def _headers(
        self,
    ):
        with open(self._file_name, 'rb') as f:
            self._add_header(
                constants.CONTENT_TYPE,
                constants.MIME_MAPPING.get(
                    os.path.splitext(
                        self._file_name
                    )[1].lstrip('.'),
                    'application/octet-stream',
                )
            )
            self._add_header(
                constants.CONTENT_LENGTH,
                os.fstat(f.fileno()).st_size,
            )

    def _content(
        self,
    ):
        with open(self._file_name, 'rb') as f:
            while True:
                buf = f.read(constants.MAX_BUFFER_SIZE)
                if not buf:
                    break
                self._request_context["response"] += buf
