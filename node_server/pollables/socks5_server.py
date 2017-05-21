#!/usr/bin/python

import errno
import logging
import socket
import traceback

from common import constants
from common.utilities import util

from common.pollables import base_socket


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

    def __init__(
        self,
        socket,
        state,
        app_context,
        key=0,
    ):
        super(Socks5Server, self).__init__(
            socket,
            state,
            app_context,
        )
        self._machine_current_state = constants.RECV_GREETING
        self._state_machine = self._create_state_machine()
        self._command_map = self._create_command_map()
        self._request_context = {}

        self._key = key
        self._last_node = True

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

    def _create_command_map(self):
        return {
            constants.CONNECT: self._connect_command,
        }

    def _recv_greeting(self):
        if not self._request_context:
            self._get_socks5_greeting()
            
        if constants.MY_SOCKS_SIGNATURE in self._request_context["methods"]:
            self._last_node = False
            self._request_context["methods"].remove(constants.MY_SOCKS_SIGNATURE)
 
        method = constants.NO_ACCEPTABLE_METHODS
        for m in self._request_context["methods"]:
            if m in constants.SUPPORTED_METHODS:
                method = m
                break

        self._buffer = "%s%s" % (
            chr(self._request_context["version"]),
            chr(method),
        )
        self._machine_current_state = self._state_machine[
            self._machine_current_state
        ]["next"]

    def _send_greeting(self):
        super(Socks5Server, self).on_write()
        self._request_context = {}
        self._machine_current_state = self._state_machine[
            self._machine_current_state
        ]["next"]

    def _recv_connection_request(self):
        if not self._request_context:
            self._get_socks5_connection_request()
        reply = self._command_map[self._request_context["command"]]()

        self._buffer = "%s%s%s%s%s%s" % (
            chr(self._request_context["version"]),
            chr(reply),
            chr(self._request_context["reserved"]),
            chr(self._request_context["address_type"]),
            ''.join(
                chr(int(x))
                for x in self._request_context["address"].split('.')
            ),
            (
                chr(self._request_context["port"] / 256) +
                chr(self._request_context["port"] % 256)
            ),
        )
        self._machine_current_state = self._state_machine[
            self._machine_current_state
        ]["next"]

    def _send_connection_request(self):
        super(Socks5Server, self).on_write()
        self._request_context = {}
        self._machine_current_state = self._state_machine[
            self._machine_current_state
        ]["next"]

    def _partner_state(self):
        super(Socks5Server, self).on_write()

    def _get_socks5_greeting(self):
        if len(self._buffer) < 3:
            return
        data = [ord(a) for a in self._buffer]
        (
            version,
            number_methods,
            methods,
        ) = (
            data[0],
            data[1],
            data[2:],
        )

        if version == constants.SOCKS5_VERSION:
            if len(methods) < number_methods:
                return
            elif len(methods) > number_methods:
                raise socks5_util.Socks5Error()
            self._request_context = {
                "version": version,
                "number_methods": number_methods,
                "methods": methods,
            }
        else:
            raise socks5_util.Socks5Error()

    def _get_socks5_connection_request(self):
        if len(self._buffer) < 4:
            return
        data = [ord(a) for a in self._buffer]
        (
            version,
            command,
            reserved,
            address_type,
        ) = (
            data[0],
            data[1],
            data[2],
            data[3],
        )
        if (
            version == constants.SOCKS5_VERSION and
            reserved == constants.SOCKS5_RESERVED and 
            command in constants.COMMANDS and
            address_type == constants.IP_4
        ):
            if len(data[4:]) < 6:
                return
            address, port = (
                '.'.join(str(n) for n in data[4:len(data)-2]),
                256*data[-2] + data[-1],
            )
            if not util.validate_ip(address):
                raise socks5_util.Socks5Error()
            self._request_context = {
                "version": version,
                "command": command,
                "reserved": reserved,
                "address_type": address_type,
                "address": address,
                "port": port,
            }
        else:
            raise socks5_util.Socks5Error()

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
            try:
                partner.socket.connect(
                    (
                        address,
                        port,
                    )
                )
            except socket.error as e:
                if e.errno not in (errno.EINPROGRESS, errno.EWOULDBLOCK):
                    raise
            self._partner = partner
            partner.partner = self
            self._app_context[
                "socket_data"
            ][partner.fileno()] = partner
        except Exception:
            if partner:
                partner.socket.close()
            raise

    def on_read(self):
        data = util.recieve_buffer(
            self._socket,
            self._app_context["max_buffer_size"] - len(self._partner.buffer),
        )
        if self._machine_current_state != constants.PARTNER_STATE or self._last_node:
            data = util.encrypt_decrypt_key_xor(
                data,
                self._key,
            )
        self._partner.buffer += data

    def on_write(self):
        self._state_machine[self._machine_current_state]["method"]()

   # def __repr__(self):
        # return "Socks5Server object %s. address %s, port %s %s" % (
            # self.fileno(),
            # self._bind_address,
            # self._bind_port,
            # self._last_node,
        # )
