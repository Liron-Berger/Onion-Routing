#!/usr/bin/python
## @package onion_routing.registry.services.base_service
# Base class for all services.
#

from common import constants


## Base Service.
# Contains elementary functions for services to inherit and change.
#
class BaseService(object):

    ## Service name
    NAME = "/base"

    ## Constructor.
    # @param request_context (dict) request context.
    #
    def __init__(
        self,
        request_context,
    ):
        self._request_context = request_context

    ## Function called before receiving HTTP headers.
    def before_request_headers(self):
        pass

    ## Function called before receiving HTTP content.
    def before_request_content(self):
        self._request_context["content_length"] = int(
            self._request_context["request_headers"].get(
                constants.CONTENT_LENGTH,
                "0",
            )
        )

    ## Function called during receiving HTTP content.
    def handle_content(self):
        return False

    ## Function called before sending HTTP status.
    def before_response_status(self):
        pass

    ## Function called before sending HTTP headers.
    def before_response_headers(self):
        if constants.CONTENT_LENGTH not in self._request_context[
            "response_headers"
        ]:
            self._request_context[
                "response_headers"
            ][constants.CONTENT_LENGTH] = len(
                self._request_context["response"]
            )

    ## Function called before sending HTTP content.
    def before_response_content(self):
        pass

    ## Function called during sending HTTP content.
    # @returns (str) HTTP response by service.
    #
    def response(self):
        result = self._request_context.get("response")
        if result is not None:
            del self._request_context["response"]
        return result

    ## Function called before termination.
    def before_terminate(self):
        pass

    ## Wanted headers dictionary.
    # @returns (dict) dictionary of wanted headers to parse.
    #
    def wanted_headers(self):
        return {
            constants.CONTENT_LENGTH,
        }
