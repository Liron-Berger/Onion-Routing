#!/usr/bin/python
## @package onion_routing.registry_node.services.file_service
# Service for openening a requested file.
#

import os

from common import constants
from common.utilities import http_util
from registry_node.services import base_service


## File Service.
# Contains the right procedure for opening certain file when no other service
# was recieved.
#
class FileService(base_service.BaseService):

    ## Service name
    NAME = "/"

    ## Function called before receiving HTTP headers.
    # Opens requested file and add needed headers.
    #
    def before_request_headers(self):
        try:
            file_name = os.path.normpath(
                '%s%s' % (
                    self._request_context["app_context"]["base"],
                    os.path.normpath(self._request_context["uri"]),
                )
            )
            fd = os.open(file_name, os.O_RDONLY)
            self._request_context[
                "response_headers"
            ][constants.CONTENT_LENGTH] = os.fstat(fd).st_size
            self._request_context[
                "response_headers"
            ][constants.CONTENT_TYPE] = constants.MIME_MAPPING.get(
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

    ## Function called during sending HTTP content.
    # @returns (str) Content of file.
    #
    def response(self):
        data = os.read(
            self._request_context["fd"],
            self._request_context[
                "app_context"
            ]["max_buffer_size"] - len(self._request_context["response"]),
        )
        if not data:
            return None
        return data
