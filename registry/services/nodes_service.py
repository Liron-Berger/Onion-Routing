#!/usr/bin/python
## @package onion_routing.registry.services.nodes_service
# Service for registering new nodes.
## @file nodes_service.py
# Implementation of @ref onion_routing.registry.services.nodes_service
#

from common.utilities import http_util
from registry.services import base_service


## Nodes Service.
# Sending all connected nodes to the requesting client.
#
class NodesService(base_service.BaseService):

    ## Service name.
    NAME = "/nodes"

    ## Function called before sending HTTP headers.
    # Send string representation of registry.
    #
    def before_response_headers(self):
        try:
            self._request_context["response"] = str(
                self._request_context["app_context"]["registry"],
            )
        except Exception as e:
            raise http_util.HTTPError(
                code=500,
                status="Internal Error",
                message="fail: " + str(e),
            )

        super(NodesService, self).before_response_headers()
