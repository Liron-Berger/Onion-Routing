#!/usr/bin/python
## @package onion_routing.registry.services.unregister_service
# Service for unregistering new nodes.
#

import urlparse
import logging

from registry.services import base_service


## Unregister Service.
# Unregistering requested nodes and removes them from registry.
#
class UnregisterService(base_service.BaseService):

    ## Service name
    NAME = "/unregister"

    ## Function called before sending HTTP status.
    # Changes status to redirect to go back to previous page.
    #
    def before_response_status(self):
        self._request_context["code"] = 301
        self._request_context["status"] = "Moved Permanently"


    ## Function called before sending HTTP headers.
    # Removes the recieved node from the registry.
    #
    def before_response_headers(self):
        qs = urlparse.parse_qs(self._request_context["parse"].query)

        self._unregister(
            qs["port"][0],
        )
        self._request_context["response"] = "unregistered"

        self._request_context["response_headers"] = {
            'Cache-Control': 'no-cache, no-store, must-revalidate', 
            'Pragma': 'no-cache', 
            'Expires': '0',
            'Location': 'nodes.html',
        }

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

            del self._request_context["app_context"]["nodes"][name]
            self._request_context["app_context"]["xml"].update()
        else:
            logging.info("node was not in registry...")

