#!/usr/bin/python
## @package onion_routing.onion.pollables.socks5_server
# Basic implementation of a server based on protocol socks5.
## @file socks5_server.py
# Implementation of @ref onion_routing.onion.pollables.socks5_server
#

import logging
import socket
import traceback

from common import constants
from common.async import event_object
from common.utilities import encryption_util
from common.utilities import socks5_util
from common.utilities import util
from common.pollables import tcp_socket
from common.pollables import proxy_socket


## Socks5 Server.
#
# Created for routing a message from a client to a wanted destination.
# Uses rfc 1928 - https://www.ietf.org/rfc/rfc1928.txt.
# Supports only part of the options available in the protocol which are
# used for the purpose of the project.
#
class Socks5Server(tcp_socket.TCPSocket):

    ## Constructor.
    # @param socket (socket) the wrapped socket.
    # @param state (int) state of Socks5Server.
    # @param app_context (dict) application context.
    # @param key (int) secret key of creating
    # @ref onion.pollables.onion_node.OnionNode._key.
    #
    # Creates a wrapper for the given @ref 
    # common.pollables.tcp_socket.TCPSocket._socket to be able to
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

        ## Decode dict.
        self._decode = {}

        ## Secret key for encryption.
        self._key = key

        ## Whether this is the last node.
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
    # @returns (bool) whether ready to next state.
    #
    # - Validate that recieved content is a socks5 greeting.
    # - Check whether special method is inside - special method is used for all
    # regular nodes, while in the greeting for the last one it is missing.
    # - Choose the right method from the recieved ones.
    #
    def _recv_greeting(self):
        if not self._decode:
            self._decode = socks5_util.GreetingRequest.decode(
                self._buffer,
            )

        if constants.MY_SOCKS_SIGNATURE in self._decode["methods"]:
            self._last_node = False
            self._decode["methods"].remove(
                constants.MY_SOCKS_SIGNATURE,
            )

        self._decode["method"] = constants.NO_ACCEPTABLE_METHODS
        for m in self._decode["methods"]:
            if m in constants.SUPPORTED_METHODS:
                self._decode["method"] = m
                break
        return True

    ## Send greeting state.
    # @returns (bool) whether ready to next state.
    #
    # - Build a greeting response to send back to the client.
    #
    def _send_greeting(self):
        self._buffer = socks5_util.GreetingResponse.encode(
            self._decode,
        )
        return True

    ## Recv connection request.
    # @returns (bool) whether ready to next state.
    #
    # - Validate that recieved content is a socks5 connection request.
    # - Run command procedure and save status.
    #
    def _recv_connection_request(self):
        if not self._decode:
            self._decode = socks5_util.Socks5Request.decode(
                self._buffer,
            )

        self._decode["reply"] = self._command_map[
            self._decode["command"]
        ]()
        return True

    ## Send connection request state.
    # @returns (bool) whether ready to next state.
    #
    # Build a connection response to send back to the client.
    #
    def _send_connection_request(self):
        self._buffer = socks5_util.Socks5Response.encode(
            self._decode,
        )
        return True

    ## Partner state.
    # Server serves as proxy between client and partner.
    # Encrypts all sent messages, unless:
    # - When state is PARTNER_STATE but not @ref _last_node.
    #
    def _partner_state(self):
        return True

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
                self._decode["address"],
                self._decode["port"],
            )
        except Exception:
            logging.error(traceback.format_exc())
            reply = constants.GENERAL_SERVER_FAILURE
        return reply

    ## Connect command utility.
    # @param address (str) connect address.
    # @param port (int) connect port.
    #
    # - Create a new partner socket - @ref common.pollables.proxy_socket.ProxySocket.
    # - Connect the partner to address:port which were recieved from
    # the client.
    # - set @ref common.pollables.tcp_socket.TCPSocket._partner = partner.
    # - set partner of partner to this.
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

            partner = proxy_socket.ProxySocket(
                socket.socket(socket.AF_INET, socket.SOCK_STREAM),
                constants.ACTIVE,
                self._request_context["app_context"],
            )

            util.connect(
                partner.socket,
                address,
                port,
            )

            self._partner = partner
            partner.partner = self
            self._request_context["app_context"][
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
    # Run the current state.
    #
    # @ref _last_node is False -> decrypt content with key unless
    # state is PARTNER_STATE.
    # @ref _last_node == True -> decrypt content with key at all times.
    #
    def on_read(self):
        data = util.recieve_buffer(
            self._socket,
            self._request_context[
                "app_context"
            ]["max_buffer_size"] - len(self._partner.buffer),
        )
        if(
            self._machine_current_state != constants.PARTNER_STATE or
            self._last_node
        ):
            data = encryption_util.decrypt(
                data,
                self._key,
            )
        self._partner.buffer += data

        if self._state_machine[self._machine_current_state]["method"]():
            self._machine_current_state = self._state_machine[
                self._machine_current_state
            ]["next"]

    ## On write event.
    # Run the current state.
    #
    # @ref _last_node is False -> encrypt content with key unless
    # state is PARTNER_STATE.
    # @ref _last_node == True -> encrypt content with key at all times.
    #
    def on_write(self):
        if self._state_machine[self._machine_current_state]["method"]():
            if(
                self._machine_current_state != constants.PARTNER_STATE or
                self._last_node
            ):
                self._write_encrypted()
            else:
                super(Socks5Server, self).on_write()

            self._decode = {}
            self._machine_current_state = self._state_machine[
                self._machine_current_state
            ]["next"]

    ## Get events for poller.
    # @returns (int) events to register for poller.
    #
    # On appropriate state:
    # - POLLIN when @ref _state is ACTIVE and @ref _buffer is not full.
    # - POLLOUT when @ref _buffer is not empty.
    #
    def get_events(self):
        event = event_object.BaseEvent.POLLERR
        if (
            (
                self._state == constants.ACTIVE and
                not len(self._buffer) >= self._request_context[
                    "app_context"
                ]["max_buffer_size"]
            ) and self._machine_current_state in (
                constants.PARTNER_STATE,
                constants.RECV_CONNECTION_REQUEST,
                constants.RECV_GREETING,
            )
        ):
            event |= event_object.BaseEvent.POLLIN
        if (
            self._buffer and self._machine_current_state in (
                constants.PARTNER_STATE,
                constants.SEND_CONNECTION_REQUEST,
                constants.SEND_GREETING,
            )
        ):
            event |= event_object.BaseEvent.POLLOUT
        return event

    ## String representation.
    def __repr__(self):
        return "Socks5Server object %s." % (
            self.fileno(),
        )
