#!/usr/bin/python
## @package onion_routing.node_server.pollables.registry_socket
# Socket class for sending register and unregister requests for new nodes.
#

import logging

from common import constants
from common.async import event_object
from common.pollables import base_socket
from common.utilities import util


## Registring socket.
#
# Created when a new @ref node_server.pollables.server_node is opened.
# Sends register request to the registry.
# Once node is closed, sends an unregister request to the registry.
#
class RegistrySocket(base_socket.BaseSocket):

    ## Register request structure.
    # Missing the address and port fields
    # which are filled by each node saperately.
    #
    REGISTER_REQUEST = "GET /register?address=%s&port=%s&key=%s HTTP/1.1\r\n\r\n"

    ## Unregister request structure.
    # Missing the port field which is filled by each node saperately.
    #
    UNREGISTER_REQUEST = "GET /unregister?port=%s HTTP/1.1\r\n\r\n"

    ## Constructor.
    # @param socket (socket) the wrapped socket.
    # @param state (int) state of BaseSocket.
    # @param app_context (dict) application context.
    # @param connect_address (str) the address of the registry.
    # @param connect_port (int) the port of the registry.
    # @param node (@ref node_server.pollables.server_node) node instance.
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
        node,
    ):
        super(RegistrySocket, self).__init__(
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

        ## @ref node_server.pollables.server_node instance that is registering.
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
        }

    ## Send register request.
    # Put the request into the buffer and send to registry.
    # @returns (bool) whether sending is finished.
    #
    def _send_register(self):
        self._buffer = RegistrySocket.REGISTER_REQUEST % (
            self._node.bind_address,
            self._node.bind_port,
            self._node.key,
        )
        super(RegistrySocket, self).on_write()
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
            self._state = constants.CLOSING
            self._node.state = constants.CLOSING
        else:
            return False

    ## Send unregister request.
    # Sending unregister request for the @ref _node to Registry.
    # @returns (bool) whether sending is finished.
    #
    def _send_unregister(self):
        self._buffer = RegistrySocket.UNREGISTER_REQUEST % (
            self._node.bind_port,
        )
        super(RegistrySocket, self).on_write()
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

    ## Change @ref _machine_state to SEND_UNREGISTER.
    def unregister(self):
        self._machine_state = constants.SEND_UNREGISTER

    ## On read event.
    # Read from @ref _socket and enter the state function afterwards.
    # Change to the next state once operation is done.
    #
    def on_read(self):
        self._buffer += util.recieve_buffer(
            self._socket,
            self._app_context["max_buffer_size"] - len(self._buffer),
        )
        if self._state_machine[self._machine_state]["method"]():
            self._machine_state = self._state_machine[
                self._machine_state
            ]["next"]

    ## On write event.
    # Enter the state function and change to the next state once done.
    #
    def on_write(self):
        if self._state_machine[self._machine_state]["method"]():
            self._machine_state = self._state_machine[
                self._machine_state
            ]["next"]

    ## Get events for poller.
    # @retuns (int) events to register for poller.
    #
    # - POLLIN when @ref _machine_state is RECV_REGISTER.
    # - POLLOUT when @ref _machine_state is SEND_REGISTER or SEND_UNREGISTER.
    #
    def get_events(self):
        event = event_object.BaseEvent.POLLERR
        if self._machine_state in (
            constants.RECV_REGISTER,
            constants.RECV_UNREGISTER,
        ):
            event |= event_object.BaseEvent.POLLIN
        if self._machine_state in (
            constants.SEND_REGISTER,
            constants.SEND_UNREGISTER,
        ):
            event |= event_object.BaseEvent.POLLOUT
        return event

    ## On close event.
    # If node is unregistered call normal exit.
    # Else we are in the unregistering states.
    #
    def on_close(self):
        if self._machine_state == constants.UNREGISTERED:
            super(RegistrySocket, self).on_close()
        else:
            pass

    ## String representation.
    def __repr__(self):
        return "RegistrySocket object for %s:%s. fd: %s" % (
            self._node.bind_address,
            self._node.bind_port,
            self.fileno(),
        )
