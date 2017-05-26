#!/usr/bin/python
## @package onion_routing.registry_node.services.menu_service
# Service for openening main menu when client connects.
#

import os

from common import constants
from common.utilities import http_util
from registry_node.services import base_service


## Menu Service.
# Contains the right procedure for opening homepage.html when / service
# is requested.
#
class MenuService(base_service.BaseService):

    ## Service name
    NAME = "/"

    ## Function called before receiving HTTP headers.
    # Open homepage.html and add needed headers.
    #
    def before_request_headers(self):
        try:
            file_name = os.path.normpath(
                '%s%s' % (
                    self._request_context["app_context"]["base"],
                    "/homepage.html",
                )
            )
            fd = os.open(file_name, os.O_RDONLY, 0o666)
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
