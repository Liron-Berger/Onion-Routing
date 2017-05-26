#!/usr/bin/python
## @package onion_routing.registry_node.services.unregister_service
# Service for unregistering new nodes.
#

import urlparse
import logging

from registry_node.services import base_service


## Unregister Service.
# Unregistering requested nodes and removes them from registry.
#
class UnregisterService(base_service.BaseService):

    ## Service name
    NAME = "/unregister"

    ## Function called before sending HTTP headers.
    # Removes the recieved node from the registry.
    #
    def before_response_headers(self):
        qs = urlparse.parse_qs(self._request_context["parse"].query)

        self._unregister(
            qs["port"][0],
        )
        self._request_context["response"] = "unregistered"

        super(UnregisterService, self).before_response_headers()

    ## Unregister node.
    # Check whether node is in the registry and remove it if it is.
    #
    def _unregister(
        self,
        name,
    ):
        logging.info(
            "unregistring %s" % (
                name,
            )
        )
        if name in self._request_context["app_context"]["registry"]:
            del self._request_context["app_context"]["registry"][name]
