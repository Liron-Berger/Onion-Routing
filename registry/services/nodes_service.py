#!/usr/bin/python
## @package onion_routing.registry.services.register_service
# Service for registering new nodes.
#

import urlparse
import logging

from common.utilities import http_util
from registry.services import base_service


## Register Service.
# Registering new nodes and adds them to registry on request.
#
class NodesService(base_service.BaseService):

    ## Service name
    NAME = "/nodes"

    ## Function called before sending HTTP headers.
    # Adds the recieved node to the registry.
    # On success: returns success response.
    # If failed: returns fail response.
    #
    def before_response_headers(self):
        try:
            self._request_context["response"] = str(self._request_context["app_context"]["registry"]) + "finished"
        except Exception as e:
            raise http_util.HTTPError(
                code=500,
                status="Internal Error",
                message="fail: " + str(e),
            )

        super(NodesService, self).before_response_headers()
