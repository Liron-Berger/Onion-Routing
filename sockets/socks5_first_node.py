#!/usr/bin/python

import errno
import logging
import socket
import traceback

from common import constants
from common import util
from common import socks5_util

from base_socket import BaseSocket
from async import events


class Socks5FirstNode(BaseSocket):

    def __init__(
        self,
        sock,
        state,
        application_context,
        client_proxy=None,
        path=None,
        bind_address="0.0.0.0",
        bind_port=9999,
    ):
        super(Socks5FirstNode, self).__init__(
            sock,
            state,
            application_context,
            bind_address,
            bind_port
        )

        self._client_proxy = client_proxy
        self._path = path

        self._machine_current_state = constants.CLIENT_SEND_GREETING
        self._state_machine = self._create_state_machine()

        self._request_context = {}

        self._start_byte_counter()

        try:
            connect_address = self._application_context["registry"][path["2"]]["address"]
            connect_port = self._application_context["registry"][path["2"]]["port"]
            self._socket.connect(
                (
                    connect_address,
                    connect_port,
                )
            )
        except socket.error as e:
            if e.errno not in (errno.EINPROGRESS, errno.EWOULDBLOCK):
                raise

        self._connected_nodes = 2

    def __repr__(self):
        return "First node in onion chain. address %s, port %s" % (
            self._bind_address,
            self._bind_port,
        )

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
                "next": constants.PARTNER_STATE,
            },
            constants.PARTNER_STATE: {
                "method": self._partner_state,
                "next": constants.PARTNER_STATE,
            },
        }

    def _client_send_greeting(self):
        self._buffer = socks5_util.GreetingRequest.encode(
            constants.SOCKS5_VERSION,
            len(constants.SUPPORTED_METHODS),
            constants.SUPPORTED_METHODS,
        )
        
        super(Socks5FirstNode, self).write()

        self._machine_current_state = self._state_machine[
            self._machine_current_state
        ]["next"]

    def _client_recv_greeting(self):
        response = socks5_util.GreetingResponse.decode(self._buffer)
        if (
            response["version"] != constants.SOCKS5_VERSION or
            response["method"] == constants.NO_ACCEPTABLE_METHODS
        ):
            self._state = constants.CLOSING
        else:
            self._buffer = ""
            self._machine_current_state = self._state_machine[
                self._machine_current_state
            ]["next"]

    def _client_send_connection_request(self):
        address = self._application_context["registry"][self._path[str(self._connected_nodes + 1)]]["address"]
        port = self._application_context["registry"][self._path[str(self._connected_nodes + 1)]]["port"]

        self._buffer = socks5_util.Socks5Request.encode(
            constants.SOCKS5_VERSION,
            constants.CONNECT,
            constants.SOCKS5_RESERVED,
            constants.IP_4,
            address,
            port,
        )
        super(Socks5FirstNode, self).write()

        self._machine_current_state = self._state_machine[
            self._machine_current_state
        ]["next"]

    def _client_recv_connection_request(self):
        response = socks5_util.Socks5Response.decode(self._buffer)
        if not (
            response["version"] == constants.SOCKS5_VERSION and
            response["reply"] == constants.SUCCESS and
            response["reserved"] == constants.SOCKS5_RESERVED and
            response["address_type"] in constants.ADDRESS_TYPE
        ):
            self._state = constants.CLOSING
        else:
            self._buffer = ""

            self._connected_nodes += 1
            if self._connected_nodes == 4:
                self._partner = self._client_proxy

                self._application_context["socket_data"][
                    self._client_proxy.fileno()
                ] = self._client_proxy

                self._machine_current_state = self._state_machine[
                    self._machine_current_state
                ]["next"]
            else:
                self._machine_current_state = constants.CLIENT_SEND_GREETING

    def _partner_state(self):
        super(Socks5FirstNode, self).write()

    def _start_byte_counter(self):
        self._application_context["connections"][self] = {
            "in": {
                "bytes": 0,
                "fd": self.fileno(),
            },
            "out": {
                "bytes": None,
                "fd": None,
            },
        }

    def _update_byte_counter(
        self,
        bytes,
    ):
        type = "in"
        if self._partner != self:
            type = "out"
        self._application_context["connections"][self][type]["bytes"] += bytes

    def read(self):
        data = ""
        try:
            while not self._partner.full_buffer():
                data = self._socket.recv(
                    self._max_buffer_size - len(self._partner.buffer),
                )
                if not data:
                    raise util.DisconnectError()

                #self._update_byte_counter(len(data))
                self._partner.buffer += data
        except socket.error as e:
            if e.errno != errno.EWOULDBLOCK:
                raise
        if not self._partner.buffer:
            raise util.DisconnectError()
        try:
            if self._machine_current_state in (
                constants.CLIENT_RECV_GREETING,
                constants.CLIENT_RECV_CONNECTION_REQUEST,
                constants.PARTNER_STATE,
            ):
                self._state_machine[self._machine_current_state]["method"]()
        except util.Socks5Error as e:
            pass #self._http_error(e)

    def write(self):
        if self._machine_current_state in (
            constants.CLIENT_SEND_GREETING,
            constants.CLIENT_SEND_CONNECTION_REQUEST,
            constants.SEND_CONNECTION_REQUEST,
            constants.SEND_GREETING,
            constants.PARTNER_STATE,
        ):
            self._state_machine[self._machine_current_state]["method"]()

    def close(self):
        del self._application_context["connections"][self]
        super(Socks5FirstNode, self).close()

    def fileno(self):
        return self._socket.fileno()

    def event(self):
        event = events.BaseEvents.POLLERR
        if (
            self._state == constants.ACTIVE and
            not self.full_buffer()
        ):
            event |= events.BaseEvents.POLLIN
        if (self._machine_current_state in 
            (
                constants.CLIENT_SEND_GREETING,
                constants.CLIENT_SEND_CONNECTION_REQUEST,
                constants.SEND_GREETING,
                constants.SEND_CONNECTION_REQUEST,
            ) or (
                self._buffer and
                self._machine_current_state == constants.PARTNER_STATE
            )
        ):
            event |= events.BaseEvents.POLLOUT
        return event
