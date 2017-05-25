#!/usr/bin/python
## @package onion_routing.node_server.pollables.socks5_server
# Basic implementation of a server based on protocol socks5.
#

import errno
import logging
import socket
import traceback

from common import constants
from common.utilities import encryption_util
from common.utilities import socks5_util
from common.utilities import util

from common.pollables import base_socket


## Socks5 Server.
#
# Created for routing a message from a client to a wanted destination.
# Uses rfc 1928 - https://www.ietf.org/rfc/rfc1928.txt.
# Supports only part of the options available in the protocol which are
# used for the purpose of the project.
#
class Socks5Server(base_socket.BaseSocket):
    """Socks5Server(socket, state, app_context) -> Socks5Server object.

    Inherits BaseSocket and wraps socket to act as a socks5 server.
    properties (additional to BaseSocket):
        machine_current_state - the state of message in the socks5 communication.
        state_machine - dictionary that stores [socks5 states : methods].
        command_map - dictionaty that stores [socks5 supported commands : methods].
        
        request_context - dictionary that stores the values recieved and decoded 
            from client data for sending a response in the next state.
    """

    ## Constructor.
    # @param socket (socket) the wrapped socket.
    # @param state (int) state of Socks5Server.
    # @param app_context (dict) application context.
    # @param key (int) secret key of creating @ref node_server.pollables.node.
    #
    # Creates a wrapper for the given @ref _socket to be able to
    # read and write from it asynchronously using the right procedure for
    # socks5 protocol.
    #
    def __init__(
        self,
        socket,
        state,
        app_context,
        key,
    ):
        super(Socks5Server, self).__init__(
            socket,
            state,
            app_context,
        )

        ## The state machine of the socket.
        self._state_machine = self._create_state_machine()

        ## Machine current state.
        self._machine_current_state = constants.RECV_GREETING

        ## Dictionary for linking supported commands to their procedure.
        self._command_map = self._create_command_map()

        ## Request context.
        self._request_context = {}

        ## Secret key for encryption.
        self._key = key

        ## Whether this is the last node 
        # Server acts differently in @ref _partner_state() when last.
        #
        self._last_node = True

    ## Create the state machine for socket.
    # @returns (dict) states to the thier methods.
    #
    def _create_state_machine(self):
        return {
            constants.RECV_GREETING: {
                "method": self._recv_greeting,
                "next": constants.SEND_GREETING,
            },
            constants.SEND_GREETING: {
                "method": self._send_greeting,
                "next": constants.RECV_CONNECTION_REQUEST,
            },
            constants.RECV_CONNECTION_REQUEST: {
                "method": self._recv_connection_request,
                "next": constants.SEND_CONNECTION_REQUEST,
            },
            constants.SEND_CONNECTION_REQUEST: {
                "method": self._send_connection_request,
                "next": constants.PARTNER_STATE,
            },
            constants.PARTNER_STATE: {
                "method": self._partner_state,
                "next": constants.PARTNER_STATE,
            },
        }

    ## Create command map.
    # @returns (dict) set @ref _command_map.
    #
    def _create_command_map(self):
        return {
            constants.CONNECT: self._connect_command,
        }

    ## Recv greeting state.
    #
    # - Validate that recieved content is a socks5 greeting.
    # - Check whether special method is inside - special method is used for all
    # regular nodes, while in the greeting for the last one it is missing.
    # - Choose the right method from the recieved ones.
    # - Build a greeting response to send back to the client.
    # - Update the state to SEND_GREETING.
    #
    def _recv_greeting(self):
        if not self._request_context:
            self._request_context = socks5_util.GreetingRequest.decode(self._buffer)
            
        if constants.MY_SOCKS_SIGNATURE in self._request_context["methods"]:
            self._last_node = False
            self._request_context["methods"].remove(constants.MY_SOCKS_SIGNATURE)
 
        method = constants.NO_ACCEPTABLE_METHODS
        for m in self._request_context["methods"]:
            if m in constants.SUPPORTED_METHODS:
                method = m
                break

        self._buffer = socks5_util.GreetingResponse.encode(
            {
                "version": self._request_context["version"],
                "method": method,
            }
        )

        self._machine_current_state = self._state_machine[
            self._machine_current_state
        ]["next"]

    ## Send greeting state.
    # - Send the response.
    # - Empty request context.
    # - Update the state to RECV_CONNECTION_REQUEST.
    #
    def _send_greeting(self):
        self._write_encrypted()#super(Socks5Server, self).on_write()
        self._request_context = {}
        self._machine_current_state = self._state_machine[
            self._machine_current_state
        ]["next"]

    ## Recv connection request.
    #
    # - Validate that recieved content is a socks5 connection request.
    # - Run command procedure and save status.
    # - Build a connection response to send back to the client.
    # - Update the state to SEND_CONNECTION_REQUEST.
    #
    def _recv_connection_request(self):
        if not self._request_context:
            self._request_context = socks5_util.Socks5Request.decode(self._buffer)

        reply = self._command_map[self._request_context["command"]]()

        self._buffer = socks5_util.Socks5Response.encode(
            {
                "version": self._request_context["version"],
                "reply": reply,
                "reserved": self._request_context["reserved"],
                "address_type": self._request_context["address_type"],
                "address": self._request_context["address"],
                "port": self._request_context["port"],
            },
        )

        self._machine_current_state = self._state_machine[
            self._machine_current_state
        ]["next"]

    ## Send connection request state.
    # - Send the response.
    # - Empty request context.
    # - Update the state to PARTNER_STATE.
    #
    def _send_connection_request(self):
        self._write_encrypted()#super(Socks5Server, self).on_write()
        self._request_context = {}
        self._machine_current_state = self._state_machine[
            self._machine_current_state
        ]["next"]

    ## Partner state.
    # Server serves as proxy between client and partner.
    # Encrypts all sent messages, unless:
    # - When state is PARTNER_STATE but not @ref _last_node.
    #
    def _partner_state(self):
        if self._machine_current_state != constants.PARTNER_STATE or self._last_node:
            self._write_encrypted()
        else:
            super(Socks5Server, self).on_write()

    ## Connect command.
    # @returns (int) reply - status of command.
    #
    # Connect to the desired destination and try to create a partner.
    # - Successful connection - reply is SUCCESS.
    # - Unsuccessful connection - reply is GENERAL_SERVER_FAILURE.
    #
    def _connect_command(self):
        reply = constants.SUCCESS
        try:
            self._connect(
                self._request_context["address"],
                self._request_context["port"],
            )            
        except Exception:
            logging.error(traceback.format_exc())
            reply = constants.GENERAL_SERVER_FAILURE
        return reply

    ## Connect command utility.
    # @param address (str) connect address.
    # @param port (int) connect port.
    #
    # - Create a new partner socket - @ref common.pollables.BaseSocket.
    # - Connect the partner to address:port which were recieved from the client.
    # - set @ref _partner = partner. 
    # - set @ref partner of partner to this.
    #
    # In case of exception: close the opened socket if already created and
    # return error response.
    #
    def _connect(
        self,
        address,
        port,
    ):
        logging.info(
            "connecting to: %s %s" %
            (
                address,
                port,
            ),
        )
        try:
            partner = None

            partner = base_socket.BaseSocket(
                socket.socket(socket.AF_INET, socket.SOCK_STREAM),
                constants.ACTIVE,
                self._app_context,
            )

            util.connect(
                partner.socket,
                address,
                port,
            )

            self._partner = partner
            partner.partner = self
            self._app_context[
                "socket_data"
            ][partner.fileno()] = partner
        except Exception:
            if partner:
                partner.socket.close()
            raise

    ## Write write encrypted message.
    def _write_encrypted(self):
        self._buffer = encryption_util.decrypt(
            util.send_buffer(
                self._socket,
                encryption_util.encrypt(
                    self._buffer,
                    self._key,
                ),
            ),
            self._key,
        )

    ## On read event.
    # Read from @ref _partner until maximum size of @ref _buffer is recived.
    #
    # @ref _last_node is False -> decrypt content with key unless
    # state is PARTNER_STATE. 
    # @ref _last_node == True -> decrypt content with key at all times.
    #
    def on_read(self):
        data = util.recieve_buffer(
            self._socket,
            self._app_context["max_buffer_size"] - len(self._partner.buffer),
        )
        if self._machine_current_state != constants.PARTNER_STATE or self._last_node:
            data = encryption_util.decrypt(
                data,
                self._key,
            )
        self._partner.buffer += data

    ## On write event.
    # Run the current state.
    #
    def on_write(self):
        self._state_machine[self._machine_current_state]["method"]()

    ## String representation.
    def __repr__(self):
        return "Socks5Server object %s." % (
            self.fileno(),
        )
