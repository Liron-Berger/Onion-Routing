#!/usr/bin/python
## @package onion_routing.registry_node.pollables.socks5_client
# Socks5 client socket, responsible for establishing connections to all other
# nodes, and later serves as proxy for encrypting all communication with
# the browser.
#

from common import constants
from common.async import event_object
from common.pollables import tcp_socket
from common.utilities import encryption_util
from common.utilities import util
from common.utilities import socks5_util


## Socks 5 Client.
#
# Created for routing a message from a the client (browser) to destination.
# Uses rfc 1928 - https://www.ietf.org/rfc/rfc1928.txt.
# Establishes Socks5 with all other nodes in order to redirect the
# messages from the browser to the last node which will finally
# redirect it to the destination.
#
class Socks5Client(tcp_socket.TCPSocket):

    ## Request context.
    _request_context = {}

    ## Currently connected nodes from the path.
    _connected_nodes = 1

    ## Constructor.
    # @param socket (socket) the wrapped socket.
    # @param state (int) state of Socks5Server.
    # @param app_context (dict) application context.
    # @param browser_socket (socket) @ref common.pollables.tcp_socket object
    #   for redirecting from the client to @ref_partner after socks5
    #   is established.
    # @param path (dict) the nodes and their order.
    #
    # Creates a wrapper for the given @ref _socket to be able to
    # read and write from it asynchronously using the right procedure for
    # socks5 protocol as a client, sending socks5 request to a
    # veriety of servers.
    #
    def __init__(
        self,
        socket,
        state,
        app_context,
        browser_socket,
        path,
    ):
        super(Socks5Client, self).__init__(
            socket,
            state,
            app_context,
        )

        ## Broser socket - the client.
        self._browser_socket = browser_socket

        ## Path - nodes and the order in which connection to them is done.
        self._path = path

        ## The state machine of the socket.
        self._state_machine = self._create_state_machine()

        ## Machine current state.
        self._machine_current_state = constants.CLIENT_SEND_GREETING

        self._start_byte_counter()

        util.connect(
            self._socket,
            self._path[str(self._connected_nodes)]["address"],
            self._path[str(self._connected_nodes)]["port"],
        )

    ## Create the state machine for socket.
    # @returns (dict) states to the thier methods.
    #
    def _create_state_machine(self):
        return {
            constants.CLIENT_SEND_GREETING: {
                "method": self._client_send_greeting,
                "next": constants.CLIENT_RECV_GREETING,
            },
            constants.CLIENT_RECV_GREETING: {
                "method": self._client_recv_greeting,
                "next": constants.CLIENT_SEND_CONNECTION_REQUEST,
            },
            constants.CLIENT_SEND_CONNECTION_REQUEST: {
                "method": self._client_send_connection_request,
                "next": constants.CLIENT_RECV_CONNECTION_REQUEST,
            },
            constants.CLIENT_RECV_CONNECTION_REQUEST: {
                "method": self._client_recv_connection_request,
                "next": constants.CLIENT_SEND_GREETING,
            },
            constants.PARTNER_STATE: {
                "method": self._partner_state,
                "next": constants.PARTNER_STATE,
            },
        }

    ## Send greeting request state.
    # @returns (bool) whether state is finished.
    #
    # Build a request with all supported method.
    # When establishing socks with the last node, add MY_SOCKS_SIGNATURE,
    #   to inform the node its the last.
    #
    def _client_send_greeting(self):
        try:
            methods = list(constants.SUPPORTED_METHODS)
            if not self._connected_nodes == constants.OPTIMAL_NODES_IN_PATH:
                methods.append(constants.MY_SOCKS_SIGNATURE)
            self._buffer = socks5_util.GreetingRequest.encode(
                {
                    "version": constants.SOCKS5_VERSION,
                    "number_methods": len(methods),
                    "methods": methods,
                },
            )
            return True
        except Exception:
            self.on_close()
            return False

    ## Recieve greeting response state.
    # @returns (bool) whether state is finished.
    #
    # Decodes the buffer to for content of response.
    # Continue when response is positive and supported.
    #
    def _client_recv_greeting(self):
        response = socks5_util.GreetingResponse.decode(self._buffer)
        if (
            response["version"] != constants.SOCKS5_VERSION or
            response["method"] == constants.NO_ACCEPTABLE_METHODS
        ):
            self.on_close()
            return False
        else:
            return True

    ## Send connection request state.
    # @returns (bool) whether state is finished.
    #
    # Encodes a connection request with the address and port of the next node.
    #
    def _client_send_connection_request(self):
        try:
            address = self._path[str(self._connected_nodes + 1)]["address"]
            port = self._path[str(self._connected_nodes + 1)]["port"]

            self._buffer = socks5_util.Socks5Request.encode(
                {
                    "version": constants.SOCKS5_VERSION,
                    "command": constants.CONNECT,
                    "reserved": constants.SOCKS5_RESERVED,
                    "address_type": constants.IP_4,
                    "address": address,
                    "port": port,
                },
            )
            return True
        except Exception:
            self.on_close()
            return False

    ## Recieve connection response state.
    # @returns (bool) whether state is finished.
    #
    # Decodes the buffer to for content of response.
    # When response is positive update @ref _connected_nodes to the next node.
    # Before establishing connection with the last node:
    # - make @ref _partner to @ref _browser_socket in order to
    # create a proxy between the last node and browser.
    # Next state:
    # - SEND_GREETING: establishing new connection with regular nodes.
    # - PARTNER_STATE: become a proxy - last node connection.
    # Continue when response is positive and supported.
    #
    def _client_recv_connection_request(self):
        response = socks5_util.Socks5Response.decode(self._buffer)
        if not (
            response["version"] == constants.SOCKS5_VERSION and
            response["reply"] == constants.SUCCESS and
            response["reserved"] == constants.SOCKS5_RESERVED and
            response["address_type"] in constants.ADDRESS_TYPE
        ):
            self.on_close()
            return False
        else:
            self._connected_nodes += 1
            if self._connected_nodes == constants.OPTIMAL_NODES_IN_PATH:
                self._state_machine[
                    self._machine_current_state
                ]["next"] = constants.PARTNER_STATE
                self._partner = self._browser_socket

                self._request_context["app_context"]["socket_data"][
                    self._browser_socket.fileno()
                ] = self._browser_socket

                self._request_context["app_context"]["connections"][
                    self
                ]["in"] = {
                    "bytes": 0,
                    "fd": self._partner.fileno(),
                }
            return True

    ## Partner state.
    # @returns (bool) True.
    # Client is used as a proxy between browser and last connected node.
    #
    def _partner_state(self):
        return True

    ## Start byte counter.
    # Fill @ref _app_context ["connections"] with new connection to
    # save bytes recieved and sent for statistics.
    #
    def _start_byte_counter(self):
        self._request_context["app_context"]["connections"][self] = {
            "in": {
                "bytes": None,
                "fd": None,
            },
            "out": {
                "bytes": 0,
                "fd": self.fileno(),
            },
        }

    ## Update byte counter.
    # @param bytes (int) number of bytes sent.
    # According to the type of connection now (in/out) - update bytes.
    #
    def _update_byte_counter(
        self,
        bytes,
    ):
        type = "out"
        if self._partner != self:
            type = "in"

        self._request_context["app_context"]["connections"][self][type]["bytes"] += bytes

    ## On read event.
    # Read from @ref _partner until maximum size of @ref _buffer is recived.
    # Decrypt content with secret key of current node.
    #
    # Update statistics.
    # Run the current state.
    # Update state.
    #
    def on_read(self):
        data = encryption_util.decrypt(
            util.recieve_buffer(
                self._socket,
                self._request_context["app_context"][
                    "max_buffer_size"
                ] - len(self._partner.buffer),
            ),
            self._path[str(self._connected_nodes)]["key"],
        )

        self._partner.buffer += data
        self._update_byte_counter(len(data))

        try:
            if self._machine_current_state in (
                constants.CLIENT_RECV_GREETING,
                constants.CLIENT_RECV_CONNECTION_REQUEST,
                constants.PARTNER_STATE,
            ):
                if self._state_machine[
                    self._machine_current_state
                ]["method"]():
                    self._buffer = ""

                    self._machine_current_state = self._state_machine[
                        self._machine_current_state
                    ]["next"]
        except socks5_util.Socks5Error as e:
            raise e

    ## On write event.
    # Run the current state.
    #
    # Encrypt content with secret key of current node.
    # Update state.
    #
    def on_write(self):
        if self._machine_current_state in (
            constants.CLIENT_SEND_GREETING,
            constants.CLIENT_SEND_CONNECTION_REQUEST,
            constants.PARTNER_STATE,
        ):
            if self._state_machine[self._machine_current_state]["method"]():
                self._buffer = encryption_util.decrypt(
                    util.send_buffer(
                        self._socket,
                        encryption_util.encrypt(
                            self._buffer,
                            self._path[str(self._connected_nodes)]["key"],
                        ),
                    ),
                    self._path[str(self._connected_nodes)]["key"],
                )

                self._machine_current_state = self._state_machine[
                    self._machine_current_state
                ]["next"]

    ## On close event.
    # Change @ref _state of socket to CLOSING and empty @ref _buffer.
    # If TCPSocket is proxy run on_close on @ref _partner.
    # If browser was not closed, change it state to CLOSING
    #
    def on_close(self):
        super(Socks5Client, self).on_close()

        if self._partner != self._browser_socket:
            self._browser_socket.state = constants.CLOSING

    ## Close TCPSocket.
    # Closing @ref _socket.
    # Remove this connection from statistics.
    # If browser was not closed, close it.
    #
    def close(self):
        del self._request_context["app_context"]["connections"][self]
        super(Socks5Client, self).close()

        if self._partner != self._browser_socket:
            self._browser_socket.close()

    ## Get events for poller.
    # @retuns (int) events to register for poller.
    #
    # On appropriate state:
    # - POLLIN when @ref _state is ACTIVE and @ref _buffer is not full.
    # - POLLOUT when @ref _buffer is not empty.
    #
    def get_events(self):
        event = event_object.BaseEvent.POLLERR
        if (
            self._state == constants.ACTIVE and
            not len(self._buffer) >= self._request_context["app_context"]["max_buffer_size"] and
            self._machine_current_state in (
                constants.CLIENT_RECV_GREETING,
                constants.CLIENT_RECV_CONNECTION_REQUEST,
                constants.PARTNER_STATE,
            )
        ):
            event |= event_object.BaseEvent.POLLIN
        if (
            self._machine_current_state in
            (
                constants.CLIENT_SEND_GREETING,
                constants.CLIENT_SEND_CONNECTION_REQUEST,
            ) or (
                self._buffer and
                self._machine_current_state == constants.PARTNER_STATE
            )
        ):
            event |= event_object.BaseEvent.POLLOUT
        return event

    ## String representation.
    def __repr__(self):
        return "Socks5 Client. fd %s" % (
            self.fileno(),
        )
