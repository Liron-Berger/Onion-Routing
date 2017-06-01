#!/usr/bin/python
## @package onion_routing.registry.services.register_service
# Service for registering new nodes.
## @file register_service.py
# Implementation of @ref onion_routing.registry.services.register_service
#

import logging
import urlparse

from common.utilities import http_util
from registry.services import base_service


## Register Service.
# Registering new nodes and adds them to registry on request.
#
class RegisterService(base_service.BaseService):

    ## Service name
    NAME = "/register"

    ## Function called before sending HTTP headers.
    # Adds the recieved node to the registry.
    # On success: returns success response.
    # If failed: returns fail response.
    #
    def before_response_headers(self):
        try:
            qs = urlparse.parse_qs(self._request_context["parse"].query)

            self._register(
                qs["address"][0],
                qs["port"][0],
                int(qs["key"][0]),
            )

            self._request_context["response"] = "success"
        except Exception as e:
            raise http_util.HTTPError(
                code=500,
                status="Internal Error",
                message="fail: " + str(e),
            )

        super(RegisterService, self).before_response_headers()

    ## Register node.
    # If node with the same port exists -> return fail message.
    # Add the address, port and key of node to registry.
    #
    def _register(
        self,
        address,
        port,
        key,
    ):
        if port in self._request_context["app_context"]["registry"]:
            logging.info(
                "failed to add node %s:%s" % (
                    address,
                    port,
                )
            )
            raise RuntimeError("Node with the same address already registered.")
        self._request_context["app_context"]["registry"][address] = {
            "name": address,
            "address": address,
            "port": int(port),
            "key": key,
        }
        logging.info(
            "New node added: address %s, port %s" % (
                address,
                port,
            )
        )
        self._request_context["app_context"]["nodes"][address] = port
        self._request_context["app_context"]["xml"].update()
