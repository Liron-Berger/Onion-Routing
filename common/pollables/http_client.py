#!/usr/bin/python
## @package onion_routing.common.pollables.http_client
# Socket class for sending requests to http_server.
## @file http_client.py
# Implementation of @ref onion_routing.common.pollables.http_client
#

import ast
import errno
import logging

from common import constants
from common.async import event_object
from common.pollables import tcp_socket
from common.utilities import http_util
from common.utilities import util
from registry.services import base_service


## Http client socket.
#
# Created when a new node is opened.
# Sends register request to the registry.
# Once node is closed, sends an unregister request to the registry.
#
class HttpClient(tcp_socket.TCPSocket):

    ## Register request structure.
    # Missing the address and port fields
    # which are filled by each node saperately.
    #
    REGISTER_REQUEST = (
        "GET /register?address=%s&port=%s&key=%s HTTP/1.1\r\n\r\n"
    )

    ## Unregister request structure.
    # Missing the port field which is filled by each node saperately.
    #
    UNREGISTER_REQUEST = (
        "GET /unregister?port=%s HTTP/1.1\r\n\r\n"
    )

    NODES_REQUEST = (
        "GET /nodes HTTP/1.1\r\n\r\n"
    )

    ## Constructor.
    # @param socket (socket) the wrapped socket.
    # @param state (int) state of TCPSocket.
    # @param app_context (dict) application context.
    # @param connect_address (str) the address of the registry.
    # @param connect_port (int) the port of the registry.
    # @param node (node) node instance.
    #
    # Creates a state machine, which is responsible to send the proper requests
    # to the registry, until finally terminating itself.
    #
    def __init__(
        self,
        socket,
        state,
        app_context,
        connect_address,
        connect_port,
        node=None,
    ):
        super(HttpClient, self).__init__(
            socket,
            state,
            app_context,
        )

        util.connect(
            self._socket,
            connect_address,
            connect_port,
        )

        ## The state machine of the socket.
        self._state_machine = self._create_state_machine()

        ## Machine current state.
        self._machine_state = constants.SEND_REGISTER

        ## node instance that is registering.
        self._node = node            

    ## Create the state machine for socket.
    # @returns (dict) states to the thier methods.
    #
    def _create_state_machine(self):
        return {
            constants.SEND_REGISTER: {
                "method": self._send_register,
                "next": constants.RECV_REGISTER,
            },
            constants.RECV_REGISTER: {
                "method": self._recv_register,
                "next": None,
            },
            constants.SEND_UNREGISTER: {
                "method": self._send_unregister,
                "next": constants.RECV_UNREGISTER,
            },
            constants.RECV_UNREGISTER: {
                "method": self._recv_unregister,
                "next": constants.UNREGISTERED,
            },
            constants.UNREGISTERED: {
                "method": None,
                "next": None,
            },
            constants.SEND_NODES: {
                "method": self._send_nodes,
                "next": constants.RECV_NODES,
            },
            constants.RECV_NODES: {
                "method": self._recv_nodes,
                "next": None,
            },
        }

    ## Send register request.
    # Put the request into the buffer and send to registry.
    # @returns (bool) whether sending is finished.
    #
    def _send_register(self):
        self._buffer = HttpClient.REGISTER_REQUEST % (
            self._node.bind_address,
            self._node.bind_port,
            self._node.key,
        )
        super(HttpClient, self).on_write()
        return True

    ## Register response.
    # Whether the registry accepted the node or something failed.
    # - success: continue to sleeping state until unregister.
    # - fail: something went wrong, close this socket and @ref _node.
    # @returns (bool) whether message was recieved properly.
    #
    def _recv_register(self):
        if "success" in self._buffer:
            return True
        elif "fail" in self._buffer:
            logging.info("failed to registry: %s" % self._buffer)

            self._state = constants.CLOSING
            self._node.state = constants.CLOSING
        else:
            return False

    ## Send unregister request.
    # Sending unregister request for the @ref _node to Registry.
    # @returns (bool) whether sending is finished.
    #
    def _send_unregister(self):
        self._buffer = HttpClient.UNREGISTER_REQUEST % (
            self._node.bind_port,
        )
        super(HttpClient, self).on_write()
        return True

    ## Recv unregister request.
    # Sending unregister request for the @ref _node to Registry.
    # @returns (bool) whether unregister was performed cleanly.
    #
    def _recv_unregister(self):
        if "unregistered" in self._buffer:
            logging.info("node unregistered!")
            return True
        else:
            return False

    ## Send nodes request.
    # Sending nodes request to Registry to retrieve connected nodes.
    # @returns (bool) whether sending is finished.
    #
    def _send_nodes(self):
        self._buffer = HttpClient.NODES_REQUEST
        super(HttpClient, self).on_write()
        return True

    ## Recv nodes request.
    # Recieving dictionary of all nodes from registry and storing
    # it in app_context.
    # @returns (bool) whether nodes finished reading and converted
    # string to dict.
    #
    def _recv_nodes(self):
        line, updated_buffer = http_util.recv_line(self._buffer)
        if not line:
            return False
        if not ("200" in line.split() and "OK" in line.split()):
            return False
        status, updated_buffer = http_util.get_headers(
            updated_buffer,
            self._request_context,
            base_service.BaseService(self._request_context),
        )
        if(
            not status or
            constants.CONTENT_LENGTH not in self._request_context[
                "request_headers"
            ]
        ):
            return False

        length = int(
            self._request_context["request_headers"][constants.CONTENT_LENGTH]
        )
        self._request_context[
            "app_context"
        ]["registry"] = ast.literal_eval(updated_buffer[:length])
        self._buffer = self._buffer[self._buffer.find("/r/n/r/n") + 4:]
        return True

    ## Change @ref _machine_state to SEND_NODE.
    def get_nodes(self):
        self._machine_state = constants.SEND_NODES

    ## Change @ref _machine_state to SEND_UNREGISTER.
    def unregister(self):
        self._machine_state = constants.SEND_UNREGISTER        

    ## On read event.
    # Read from @ref _socket and enter the state function afterwards.
    # Change to the next state once operation is done.
    # If registry disconnected, closes both @ref _node and HttpClient.
    #
    def on_read(self):
        try:
            self._buffer += util.recieve_buffer(
                self._socket,
                self._request_context[
                    "app_context"
                ]["max_buffer_size"] - len(self._buffer),
            )
            if self._state_machine[self._machine_state]["method"]():
                self._machine_state = self._state_machine[
                    self._machine_state
                ]["next"]
        except Exception as e:
            if e.errno not in (errno.ECONNRESET, errno.ECONNABORTED):
                raise
            logging.error("Registry disconnected")
            self._machine_state = constants.UNREGISTERED
            self._node.on_close()
            self.on_close()

    ## On write event.
    # Enter the state function and change to the next state once done.
    # If registry disconnected, closes both @ref _node and HttpClient.
    #
    def on_write(self):
        try:
            if self._state_machine[self._machine_state]["method"]():
                self._machine_state = self._state_machine[
                    self._machine_state
                ]["next"]
        except Exception as e:
            if e.errno != errno.ENOTCONN:
                raise
            logging.error("Registry disconnected")
            self._machine_state = constants.UNREGISTERED
            self._node.on_close()
            self.on_close()

    ## Get events for poller.
    # @returns (int) events to register for poller.
    #
    # - POLLIN when @ref _machine_state is RECV_REGISTER.
    # - POLLOUT when @ref _machine_state is SEND_REGISTER or SEND_UNREGISTER.
    #
    def get_events(self):
        event = event_object.BaseEvent.POLLERR
        if self._machine_state in (
            constants.RECV_REGISTER,
            constants.RECV_UNREGISTER,
            constants.RECV_NODES,
        ):
            event |= event_object.BaseEvent.POLLIN
        if self._machine_state in (
            constants.SEND_REGISTER,
            constants.SEND_UNREGISTER,
            constants.SEND_NODES,
        ):
            event |= event_object.BaseEvent.POLLOUT
        return event

    ## On close event.
    # If node is unregistered call normal exit.
    # Else we are in the unregistering states.
    #
    def on_close(self):
        if self._machine_state == constants.UNREGISTERED:
            super(HttpClient, self).on_close()
        else:
            pass

    ## String representation.
    def __repr__(self):
        return "HttpClient object for %s:%s. fd: %s" % (
            self._node.bind_address,
            self._node.bind_port,
            self.fileno(),
        )
