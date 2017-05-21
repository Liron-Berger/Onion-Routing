#!/usr/bin/python

import errno
import logging
import socket
import traceback

from common import constants
from common.async import event_object
from common.pollables import base_socket
from common.utilities import util
from common.utilities import socks5_util


class Socks5Client(base_socket.BaseSocket):

    def __init__(
        self,
        socket,
        state,
        app_context,
        client_proxy,
        path,
    ):
        super(Socks5Client, self).__init__(
            socket,
            state,
            app_context,
        )

        self._client_proxy = client_proxy
        self._path = path

        self._machine_current_state = constants.CLIENT_SEND_GREETING
        self._state_machine = self._create_state_machine()

        self._request_context = {}

        self._start_byte_counter()
        self._connected_nodes = 2

        self._connect()

    def _connect(self):
        try:
            connect_address = self._path[str(self._connected_nodes)]["address"]
            connect_port = self._path[str(self._connected_nodes)]["port"]
            self._socket.connect(
                (
                    connect_address,
                    connect_port,
                )
            )
        except socket.error as e:
            if e.errno not in (errno.EINPROGRESS, errno.EWOULDBLOCK):
                raise

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

    def on_read(self):
        data = util.recieve_buffer(
            self._socket,
            self._app_context["max_buffer_size"] - len(self._partner.buffer),
        )
        self._partner.buffer += data
        self._update_byte_counter(len(data))

        # data = ""
        # try:
            # while not self._partner.full_buffer():
                # data = self._socket.recv(
                    # self._max_buffer_size - len(self._partner.buffer),
                # )
                # if not data:
                    # raise util.DisconnectError()
                    
                # self._update_byte_counter(len(data))
                # self._partner.buffer += data
        # except socket.error as e:
            # if e.errno not in (errno.EWOULDBLOCK, errno.EPIPE, errno.ECONNRESET, errno.ECONNABORTED):
                # raise
            # if e.errno != errno.EWOULDBLOCK:
                # self.close_handler()
        # if not self._partner.buffer:
            # raise util.DisconnectError()
        try:
            if self._machine_current_state in (
                constants.CLIENT_RECV_GREETING,
                constants.CLIENT_RECV_CONNECTION_REQUEST,
                constants.PARTNER_STATE,
            ):
                if self._state_machine[self._machine_current_state]["method"]():
                    self._buffer = ""
                    
                    self._machine_current_state = self._state_machine[
                        self._machine_current_state
                    ]["next"]
        except socks5_util.Socks5Error as e:
            pass

    def on_write(self):
        if self._machine_current_state in (
            constants.CLIENT_SEND_GREETING,
            constants.CLIENT_SEND_CONNECTION_REQUEST,
            constants.PARTNER_STATE,
        ):
            if self._state_machine[self._machine_current_state]["method"]():
                self._buffer = util.encrypt_decrypt_key_xor(
                    util.send_buffer(
                        self._socket,
                        util.encrypt_decrypt_key_xor(
                            self._buffer,
                            self._path[str(self._connected_nodes)]["key"],
                        ),
                    ),
                    self._path[str(self._connected_nodes)]["key"],
                )

                self._machine_current_state = self._state_machine[
                    self._machine_current_state
                ]["next"]

    def _client_send_greeting(self):
        try:
            if not self._connected_nodes == constants.OPTIMAL_NODES_IN_PATH + 1:
                self._buffer = socks5_util.GreetingRequest.encode(
                    {
                        "version": constants.SOCKS5_VERSION,
                        "number_methods": len(constants.SUPPORTED_METHODS_X),
                        "methods": constants.SUPPORTED_METHODS_X,
                    },
                )
            else:
                self._buffer = socks5_util.GreetingRequest.encode(
                    {
                        "version": constants.SOCKS5_VERSION,
                        "number_methods": len(constants.SUPPORTED_METHODS),
                        "methods": constants.SUPPORTED_METHODS,
                    },
                )
            return True
        except Exception:
            return False

    def _client_recv_greeting(self):
        response = socks5_util.GreetingResponse.decode(self._buffer)
        if (
            response["version"] != constants.SOCKS5_VERSION or
            response["method"] == constants.NO_ACCEPTABLE_METHODS
        ):
            self._state = constants.CLOSING
            return False
        else:
            return True
        

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
            return False

    def _client_recv_connection_request(self):
        response = socks5_util.Socks5Response.decode(self._buffer)
        if not (
            response["version"] == constants.SOCKS5_VERSION and
            response["reply"] == constants.SUCCESS and
            response["reserved"] == constants.SOCKS5_RESERVED and
            response["address_type"] in constants.ADDRESS_TYPE
        ):
            self._state = constants.CLOSING
            return False
        else:
            self._connected_nodes += 1
            if self._connected_nodes == constants.OPTIMAL_NODES_IN_PATH + 1:
                self._state_machine[self._machine_current_state]["next"] = constants.PARTNER_STATE
                self._partner = self._client_proxy

                self._app_context["socket_data"][
                    self._client_proxy.fileno()
                ] = self._client_proxy

                self._app_context["connections"][
                    self
                ]["in"] = {
                    "bytes": 0,
                    "fd": self._partner.fileno(),
                }
                
            return True

    def _partner_state(self):
        return True

    def _start_byte_counter(self):
        self._app_context["connections"][self] = {
            "in": {
                "bytes": None,
                "fd": None,
            },
            "out": {
                "bytes": 0,
                "fd": self.fileno(),
            },
        }

    def _update_byte_counter(
        self,
        bytes,
    ):
        type = "out"
        if self._partner != self:
            type = "in"

        self._app_context["connections"][self][type]["bytes"] += bytes

    def on_close(self):
        super(Socks5Client, self).on_close()
        
        if self._partner != self._client_proxy:
            self._client_proxy.on_close()
        
    def close(self):
        del self._app_context["connections"][self]
        super(Socks5Client, self).close()

    def get_events(self):
        event = event_object.BaseEvent.POLLERR
        if (
            self._state == constants.ACTIVE and
            not len(self._buffer) >= self._app_context["max_buffer_size"]
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

    # def __repr__(self):
        # return "First node in onion chain."
