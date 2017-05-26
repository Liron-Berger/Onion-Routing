#!/usr/bin/python
## @package onion_routing.registry_node.services.disconnect_service
# Service for closing connections.
#

import urlparse

from registry_node.services import base_service


## Disconnect Service.
# Disconnect requested connection and close its sockets.
#
class DisconnectService(base_service.BaseService):

    ## Service name
    NAME = "/disconnect"

    ## Function called before sending HTTP status.
    # Status is redirect for redirecting to statistics page.
    #
    def before_response_status(self):
        self._request_context["code"] = 301
        self._request_context["status"] = "Moved Permanently"

    ## Function called before sending HTTP headers.
    # Closes the requested connection if exists.
    # Redirecting back to statistics page.
    #
    def before_response_headers(self):
        qs = urlparse.parse_qs(self._request_context["parse"].query)
        entry = self._request_context["app_context"]["socket_data"].get(
            int(qs["connection"][0]),
        )
        if entry in self._request_context["app_context"]["connections"]:
            entry.on_close()

        self._request_context["response_headers"] = {
            'Cache-Control': 'no-cache, no-store, must-revalidate',
            'Pragma': 'no-cache',
            'Expires': '0',
            'Location': 'statistics',
        }
        super(DisconnectService, self).before_response_headers()
