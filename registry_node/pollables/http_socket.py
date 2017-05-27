#!/usr/bin/python
## @package onion_routing.registry_node.pollables.http_socket
# Implementation of HTTP server which supports certain
# @ref node_server.services.
#

import logging
import importlib

from common import constants
from common.async import event_object
from common.pollables import tcp_socket
from common.utilities import http_util
from registry_node.services import base_service
from registry_node.services import file_service


## Http Server.
class HttpSocket(tcp_socket.TCPSocket):

    ## Request context.
    _request_context = {}

    ## Constructor.
    # @param socket (socket) the wrapped socket.
    # @param state (int) state of HttpSocket.
    # @param app_context (dict) application context.
    #
    # Creates a wrapper for the given @ref _socket to be able to
    # read and write from it asynchronously while handling HTTP requests.
    #
    def __init__(
        self,
        socket,
        state,
        app_context,
    ):
        super(HttpSocket, self).__init__(
            socket,
            state,
            app_context,
        )

        ## The state machine of the socket.
        self._state_machine = self._create_state_machine()

        ## Machine current state.
        self._machine_state = constants.RECV_STATUS

        ## Service class of the current request.
        self._service_class = None

        for service in constants.SERVICES:
            importlib.import_module(service)

        ## SERVICES dict for all supported services.
        self.SERVICES = {
            s.NAME: s for s in base_service.BaseService.__subclasses__()
        }

        self._reset()

    ## Create the state machine for socket.
    # @returns (dict) states to the thier methods.
    #
    def _create_state_machine(
        self,
    ):
        return {
            constants.RECV_STATUS: {
                "method": self._recv_status,
                "next": constants.RECV_HEADERS,
            },
            constants.RECV_HEADERS: {
                "method": self._recv_headers,
                "next": constants.RECV_CONTENT,
            },
            constants.RECV_CONTENT: {
                "method": self._recv_content,
                "next": constants.SEND_STATUS,
            },
            constants.SEND_STATUS: {
                "method": self._send_status,
                "next": constants.SEND_HEADERS,
            },
            constants.SEND_HEADERS: {
                "method": self._send_headers,
                "next": constants.SEND_CONTENT,
            },
            constants.SEND_CONTENT: {
                "method": self._send_content,
                "next": constants.RECV_STATUS,
            },
        }

    ## Recv status state.
    # returns (bool) whether state is finished.
    #
    # - If request is HTTP, try to open requested service.
    # - If no request is supported, try to use
    # @ref registry_node.services.file_service.
    # - Call @ref common.services.base_service.before_request_headers().
    #
    # In case of error raise HTTPError.
    #
    def _recv_status(self):
        status, self._buffer = http_util.get_first_line(
            self._buffer,
            self._request_context,
        )
        if not status:
            return False

        try:
            self._service_class = self.SERVICES.get(
                self._request_context["parse"].path,
                file_service.FileService,
            )(
                self._request_context,
            )
            logging.info("service %s requested" % (self._service_class.NAME))
        except KeyError:
            raise http_util.HTTPError(
                code=500,
                status="Internal Error",
                message="service not supported",
            )
        self._service_class.before_request_headers()
        return True

    ## Recieve headers state.
    # returns (bool) whether state is finished.
    #
    # Get all headers from request.
    # Call @ref common.services.base_service.before_response_content().
    #
    def _recv_headers(self):
        status, self._buffer = http_util.get_headers(
            self._buffer,
            self._request_context,
            self._service_class,
        )
        if status:
            self._service_class.before_response_content()
            return True
        else:
            self._service_class.before_response_content()
            return False

    ## Recieve content state.
    # returns (bool) whether state is finished.
    #
    # Get content from request.
    # - Call @ref common.services.base_service.handle_content().
    # - After handle_content:
    # Call @ref common.services.base_service.before_response_status().
    #
    def _recv_content(self):
        http_util.get_content(
            self._buffer,
            self._request_context,
        )
        while self._service_class.handle_content():
            pass
        if "content_length" not in self._request_context:
            self._service_class.before_response_status()
            return True
        elif not self._buffer:
            return False

    ## Send status state.
    # returns (bool) whether state is finished.
    #
    # - Update @ref _buffer to appropriate HTTP status.
    # - Call @ref common.services.base_service.before_response_headers().
    #
    def _send_status(self):
        self._buffer = (
            "%s %s %s\r\n"
        ) % (
            constants.HTTP_SIGNATURE,
            self._request_context["code"],
            self._request_context["status"]
        )
        self._service_class.before_response_headers()
        return True

    ## Send headers state.
    # returns (bool) whether state is finished.
    #
    # - Set headers for HTTP response according to _service_class.
    # - Call @ref common.services.base_service.before_response_content().
    #
    def _send_headers(self):
        status, self._buffer = http_util.set_headers(
            self._buffer,
            self._request_context,
        )
        if status:
            self._service_class.before_response_content()
            return True
        else:
            self._service_class.before_response_content()
            return False

    ## Send content state.
    # returns (bool) whether state is finished.
    #
    # Add content from _service_class.response() to _buffer and
    # send the whole HTTP response it to client.
    # On end of content: @ref common.services.base_service.before_terminate().
    #
    def _send_content(self):
        content = None
        content = self._service_class.response()
        if content is None:
            self._service_class.before_terminate()
            self._reset()
            return True
        else:
            self._buffer += content
            super(HttpSocket, self).on_write()
            return False

    ## Reset __request_context.
    # Empty all request fields of previous request.
    # Empty _buffer.
    # Empty _service_class.
    #
    def _reset(self):
        self._request_context["uri"] = ""
        self._request_context["parse"] = ""
        self._request_context["code"] = 200
        self._request_context["status"] = "OK"
        self._request_context["request_headers"] = {}
        self._request_context["response_headers"] = {}
        self._request_context["response"] = ""
        self._request_context["content"] = ""

        self._buffer = ""
        self._service_class = None

    ## HTTP error handler.
    # @param e (HTTPError) the HTTPError which was caught.
    # Fills @ref _request_context with error response status, headers, content.
    #
    def _http_error(self, e):
        self._request_context["code"] = e.code
        self._request_context["status"] = e.status
        self._request_context["response"] = e.message
        self._request_context[
            "response_headers"
        ]["Content-Length"] = len(self._request_context["response"])
        self._request_context[
            "response_headers"
        ]["Content-Type"] = "text/plain"
        self._service_class = base_service.BaseService(
            self._request_context,
        )
        self._machine_state = constants.SEND_STATUS

    ## On read event.
    # Read from @ref _partner until maximum size of @ref _buffer is recived.
    #
    # Enter the appropriate state in _state_machine.
    # Once state is finished, go to the next state.
    # On HTTPError: call @ref _http_error().
    #
    def on_read(self):
        super(HttpSocket, self).on_read()
        try:
            while self._machine_state <= constants.RECV_CONTENT:
                if self._state_machine[self._machine_state]["method"]():
                    self._machine_state = self._state_machine[
                        self._machine_state
                    ]["next"]
        except http_util.HTTPError as e:
            self._http_error(e)

    ## On write event.
    # Write everything stored and @ref _buffer.
    #
    # Enter the appropriate state in _state_machine.
    # Once state is finished, go to the next state.
    # On HTTPError: call @ref _http_error().
    #
    def on_write(self):
        try:
            while(
                self._machine_state >= constants.SEND_STATUS and
                self._machine_state <= constants.SEND_CONTENT
            ):
                if self._state_machine[self._machine_state]["method"]():
                    self._machine_state = self._state_machine[
                        self._machine_state
                    ]["next"]
        except http_util.HTTPError as e:
            self._http_error(e)

    ## Get events for poller.
    # @retuns (int) events to register for poller.
    #
    # POLLIN when:
    # - @ref _state is ACTIVE.
    # - @ref _buffer is not full.
    # - @ref _machine_state is less then RECV_CONTENT.
    # POLLOUT when:
    # - @ref _buffer is not empty.
    # - SEND_STATUS <= @ref _machine_state <= SEND_CONTENT
    #
    def get_events(self):
        event = event_object.BaseEvent.POLLERR
        if (
            self._state == constants.ACTIVE and
            not len(self._buffer) >= self._request_context["app_context"]["max_buffer_size"] and
            self._machine_state <= constants.RECV_CONTENT
        ):
            event |= event_object.BaseEvent.POLLIN
        if(
            self._machine_state >= constants.SEND_STATUS and
            self._machine_state <= constants.SEND_CONTENT
        ):
            event |= event_object.BaseEvent.POLLOUT
        return event

    ## String representation.
    def __repr__(self):
        return "HttpSocket object. fd: %s" % (
            self.fileno(),
        )
