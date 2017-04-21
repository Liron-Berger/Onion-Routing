#!/usr/bin/python

import errno
import logging
import socket
import traceback
from async import events

from common import constants
from common import util

from base_socket import BaseSocket


class Socks5Server(BaseSocket):

    def __init__(
        self,
        socket,
        state,
        application_context,
        partner,
    ):
        super(Socks5Server, self).__init__(
            socket,
            state,
            application_context,
        )
        self._machine_current_state = constants.RECV_GREETING
        self._state_machine = self._create_state_machine()
        self._command_map = self._create_command_map()
        self._request_context = {}

        self._start_byte_counter()

        self._partner = partner
        self._server = None

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

    def write_partner(self):
        while self._buffer:
            self._buffer = self._buffer[
                self.partner.socket.send(
                    self._buffer
                ):
            ]

    def _recv_greeting(self):
        if not self._request_context:
            self._get_socks5_greeting()
 
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
        self.write_partner()
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
        self.write_partner()
        self._request_context = {}
        self._machine_current_state = self._state_machine[
            self._machine_current_state
        ]["next"]

    def _partner_state(self):
        super(Socks5Server, self).write()

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
                raise util.Socks5Error()
            self._request_context = {
                "version": version,
                "number_methods": number_methods,
                "methods": methods,
            }
        else:
            raise util.Socks5Error()

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
                raise util.Socks5Error()
            self._request_context = {
                "version": version,
                "command": command,
                "reserved": reserved,
                "address_type": address_type,
                "address": address,
                "port": port,
            }
        else:
            raise util.Socks5Error()

    def _connect_command(self):
        reply = constants.SUCCESS
        try:
            self._connect(
                self._request_context["address"],
                self._request_context["port"],
            )
            self._application_context["connections"][
                self
            ]["out"] = {
                "bytes": 0,
                "fd": self._partner.fileno(),
            }
        except Exception:
            logging.error(traceback.format_exc())
            reply = GENERAL_SERVER_FAILURE
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
            try:
                self.socket.connect(
                    (
                        address,
                        port,
                    )
                )
            except socket.error as e:
                if e.errno not in (errno.EINPROGRESS, errno.EWOULDBLOCK):
                    raise
        except Exception:
            if server:
                server.socket.close()
            raise

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
        while not self._partner.full_buffer():
            data = self._socket.recv(
                self._max_buffer_size - len(self._partner.buffer),
            )
            if not data:
                raise util.DisconnectError()

            self._update_byte_counter(len(data))
            self._partner.buffer += data

    def write(self):
        self._state_machine[self._machine_current_state]["method"]()

    def close(self):
        del self._application_context["connections"][self]
        super(Socks5Server, self).close()

    def fileno(self):
        return self._socket.fileno()
