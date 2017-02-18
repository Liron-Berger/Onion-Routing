#!/usr/bin/python

import errno
import logging
import socket
import traceback

from common import constants
from common import util

from common.util import NotEnoughArguments

from base_socket import BaseSocket

SOCKS5_VERSION = 0x05
RESERVED = 0x00
SUPPORTED_METHODS = (
    0x00,
)
COMMANDS = (
    CONNECT,
) = (
    0x01,
)
ADDRESS_TYPE = (
    IP_4,
) = (
    0x01,
)

REPLY_STATUS = (
    SUCCESS,
    GENERAL_SERVER_FAILURE,
) = (
    0x00,
    0x01,
)

class Socks5Server(BaseSocket):
    NAME = "Socks5Server"

    NEW_STATES = (
        RECV_GREETING,
        SEND_GREETING,
        RECV_CONNECTION_REQUEST,
        SEND_CONNECTION_REQUEST,
        ACTIVE,
    ) = range(5)

    def __init__(
        self,
        socket,
        socket_data,
        application_context,
    ):
        super(Socks5Server, self).__init__(
            socket,
            socket_data,
            application_context,
        )
        self._state = self.RECV_GREETING
        self._state_machine = self._create_state_machine()
        self._command_map = self._create_command_map()
        self._request_context = {}

        self._application_context["connections"][
            self._socket.fileno()
        ] = {
            "in": {
                "bytes": 0,
                "fd": self._socket.fileno(),
            },
            "out": {
                "bytes": None,
                "fd": None,
            },
            "async_socket": self,
        }

    def _create_state_machine(
        self,
    ):
        return {
            self.RECV_GREETING: self._recv_greeting,
            self.SEND_GREETING: self._send_greeting,
            self.RECV_CONNECTION_REQUEST: self._recv_connection_request,
            self.SEND_CONNECTION_REQUEST: self._send_connection_request,
            self.ACTIVE: self._active,
        }

    def _create_command_map(
        self,
    ):
        return {
            CONNECT: self._connect_command,
        }

    def read(self, max_size=constants.MAX_BUFFER_SIZE):
        if not self._partner:
            target = self
            x = "in"
        else:
            target = self._partner
            x = "out"
        while len(target.buffer) < max_size:
            data = self._socket.recv(
                max_size - len(target.buffer),
            )
            if not data:
                raise util.DisconnectError()
            self._application_context["connections"][
                self._socket.fileno()
            ][x]["bytes"] += len(data)
            target.buffer += data

    def write(self):
        self._state_machine[self._state]()

    def close(
        self,
    ):
        del self._application_context["connections"][self._socket.fileno()]
        super(Socks5Server, self).close()

    def _recv_greeting(
        self,
    ):
        """
           +----+----------+----------+
           |VER | NMETHODS | METHODS  |
           +----+----------+----------+
           | 1  |    1     | 1 to 255 |
           +----+----------+----------+
        """
        if not self._request_context:
            self._get_socks5_greeting()
        method = constants.NO_ACCEPTABLE_METHODS
        for m in self._request_context["methods"]:
            if m in SUPPORTED_METHODS:
                method = m
                break
        self._buffer = "%s%s" % (
            chr(self._request_context["version"]),
            chr(method),
        )
        self._state = self.SEND_GREETING

    def _send_greeting(
        self,
    ):
        """
            +----+--------+
            |VER | METHOD |
            +----+--------+
            | 1  |   1    |
            +----+--------+
        """
        super(Socks5Server, self).write()
        self._request_context = {}
        self._state = self.RECV_CONNECTION_REQUEST

    def _recv_connection_request(
        self,
    ):
        """
            +----+-----+-------+------+----------+----------+
            |VER | CMD |  RSV  | ATYP | DST.ADDR | DST.PORT |
            +----+-----+-------+------+----------+----------+
            | 1  |  1  | X'00' |  1   | Variable |    2     |
            +----+-----+-------+------+----------+----------+
        """
        if not self._request_context:
            self._get_connection_request()
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
        self._state = self.SEND_CONNECTION_REQUEST

    def _send_connection_request(
        self,
    ):
        """
            +----+-----+-------+------+----------+----------+
            |VER | REP |  RSV  | ATYP | BND.ADDR | BND.PORT |
            +----+-----+-------+------+----------+----------+
            | 1  |  1  | X'00' |  1   | Variable |    2     |
            +----+-----+-------+------+----------+----------+
        """
        super(Socks5Server, self).write()
        self._request_context = {}
        self._state = self.ACTIVE

    def _active(
        self,
    ):
        super(Socks5Server, self).write()

    def _get_connection_request(
        self,
    ):
        if len(self._buffer) < 4:
            return
        data = [ord(a) for a in self._buffer]
        version, command, reserved, address_type = (
            data[0],
            data[1],
            data[2],
            data[3],
        )
        if version != SOCKS5_VERSION:
            raise NotImplementedError("socks version not supported")
        if command not in COMMANDS:
            raise RuntimeError("command not supported")
        if reserved != RESERVED:
            raise RuntimeError("wrong reserved parameter")
        if address_type not in ADDRESS_TYPE:
            raise RuntimeError("address_type not supported")
        if address_type == IP_4:
            if len(data[4:]) < 6:
                return
            address, port = (
                '.'.join(str(n) for n in data[4:len(data)-2]),
                256*data[-2] + data[-1],
            )
            if not util.validate_ip(address):
                raise RuntimeError("wrong address")
        self._request_context = {
            "version": version,
            "command": command,
            "reserved": reserved,
            "address_type": address_type,
            "address": address,
            "port": port,
        }

    def _get_socks5_greeting(
        self,
    ):
        if len(self._buffer) < 3:
            return
        data = [ord(a) for a in self._buffer]
        version, number_methods, methods = data[0], data[1], data[2:]
        if version != SOCKS5_VERSION:
            raise NotImplementedError("socks version not supported")
        if len(methods) < number_methods:
            return
        elif len(methods) > number_methods:
            raise RuntimeError("too much methods")
        self._request_context = {
            "version": version,
            "number_methods": number_methods,
            "methods": methods,
        }

    def _connect_command(
        self,
    ):
        reply = SUCCESS
        try:
            self._connect(
                self._request_context["address"],
                self._request_context["port"],
            )
            self._application_context["connections"][
                self._socket.fileno()
            ]["out"] = {
                "bytes": 0,
                "fd": self._partner.socket.fileno(),
            }
        except Exception:
            logging.error(traceback.format_exc())
            reply = GENERAL_SERVER_FAILURE
        return reply

    def _connect(
        self,
        addr,
        port,
    ):
        logging.info(
            "connecting to: %s %s" %
            (
                addr,
                port,
            ),
        )
        try:
            new_socket = None
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

            new_socket = BaseSocket(
                s,
                self._socket_data,
                self._application_context,
            )

            try:
                s.connect(
                    (
                        addr,
                        port,
                    )
                )
            except socket.error as e:
                if e.errno not in (errno.EINPROGRESS, errno.EWOULDBLOCK):
                    raise

            self._partner = new_socket
            new_socket.partner = self

            self._socket_data[s.fileno()] = {
                "async_socket": new_socket,
                "state": constants.PROXY_ACTIVE,
            }
        except Exception:
            if new_socket:
                new_socket.socket.close()
            raise
