#!/usr/bin/python

import errno
import logging
import socket
import traceback

from common import constants
from common import util

from base_socket import BaseSocket
from async import events


class Socks5Node(BaseSocket):

    def __init__(
        self,
        sock,
        state,
        application_context,
    ):
        super(Socks5Node, self).__init__(
            sock,
            state,
            application_context,
        )

        self._machine_current_state = constants.RECV_GREETING

        self._state_machine = self._create_state_machine()

        self._command_map = self._create_command_map()
        self._request_context = {}

        self._start_byte_counter()

        if path:
            try:
                connect_address = path["2"][0]
                connect_port = path["2"][1]
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
        if self._is_first:
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
                    "next": constants.RECV_GREETING,
                },
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

    def _client_send_greeting(self):
        self._buffer = "%s%s%s" % (
            chr(0x05),
            chr(0x01),
            chr(0x00),
        )
        super(Socks5Node, self).write()

        self._machine_current_state = self._state_machine[
            self._machine_current_state
        ]["next"]

    def _client_recv_greeting(self):
        self._buffer = ""
        self._machine_current_state = self._state_machine[
            self._machine_current_state
        ]["next"]

    def _client_send_connection_request(self):
        self._buffer = "%s%s%s%s%s%s" % (
            chr(constants.SOCKS5_VERSION),
            chr(constants.CONNECT),
            chr(constants.SOCKS5_RESERVED),
            chr(constants.IP_4),
            ''.join(
                chr(int(x))
                for x in "0.0.0.0".split('.')
            ),
            (
                chr(3080 / 256) +
                chr(3080 % 256)
            ),
        )
        super(Socks5Node, self).write()

        self._machine_current_state = self._state_machine[
            self._machine_current_state
        ]["next"]

    def _client_recv_connection_request(self):
        self._buffer = ""

        if self._is_first:
            self._partner = self._client_socket

            self._application_context["socket_data"][
                self._partner.socket.fileno()
            ] = self._partner

        self._machine_current_state = self._state_machine[
            self._machine_current_state
        ]["next"]

    def _create_command_map(self):
        return {
            constants.CONNECT: self._connect_command,
        }

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
        super(Socks5Node, self).write()
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
        super(Socks5Node, self).write()
        self._request_context = {}
        self._machine_current_state = self._state_machine[
            self._machine_current_state
        ]["next"]

    def _partner_state(self):
        super(Socks5Node, self).write()

    def _get_socks5_greeting(self):
        """_get_socks5_greeting() -> fills request_context with
        the client's greeting.

        checks whether the whole message from client was recieved,
        and then checks whether it's a valid greeting.
        raises an error in case of wrong recieved arguments.
        """

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
        """_get_socks5_connection_request() -> fills request_context with
        the client's request.

        checks whether the whole message from client was recieved,
        and then checks whether it's a valid request.
        raises an error in case of wrong recieved arguments.
        """

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
        """_connect_command() -> connect command for the client's request.

        if connect is received from client, tries to connect
        to the given (address, port).
        returns socks5 status of connect - success/failure.
        """

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
            partner = BaseSocket(
                socket.socket(socket.AF_INET, socket.SOCK_STREAM),
                constants.ACTIVE,
                self._application_context,
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
            self._application_context[
                "socket_data"
            ][partner.fileno()] = partner
        except Exception:
            if partner:
                partner.socket.close()
            raise

    def _start_byte_counter(self):
        """_start_byte_counter() -> adds a new key + value to the connections dict.

        once server is started, there is an "in" state, when server is
        communicating with client, and "out" state, when server is used as
        a proxy.
        for each state the number of bytes sent/recieved is saved.
        """

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
        """_update_byte_counter(bytes) -> decides on the type of the connection,
        and adds the given length bytes to the right connection in application_context.
        """

        type = "in"
        if self._partner != self:
            type = "out"
        self._application_context["connections"][self][type]["bytes"] += bytes

    def read(self):
        """read() -> reciving data from partner.

        recives data until disconnect or buffer is full.
        data is stored in the partner's buffer.
        """

        data = ""
        try:
            while not self._partner.full_buffer():
                data = self._socket.recv(
                    self._max_buffer_size - len(self._partner.buffer),
                )
                if not data:
                    raise util.DisconnectError()


                # if self._machine_current_state == constants.PARTNER_STATE:
                    # print self.fileno(), [ord(a) for a in data]

                self._update_byte_counter(len(data))
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
                constants.RECV_CONNECTION_REQUEST,
                constants.RECV_GREETING,
                constants.PARTNER_STATE,
            ):
                self._state_machine[self._machine_current_state]["method"]()
        except util.Socks5Error as e:
            pass #self._http_error(e)

    def write(self):
        """write() -> runs the current state in state machine."""

        if self._machine_current_state in (
            constants.CLIENT_SEND_GREETING,
            constants.CLIENT_SEND_CONNECTION_REQUEST,
            constants.SEND_CONNECTION_REQUEST,
            constants.SEND_GREETING,
            constants.PARTNER_STATE,
        ):
            self._state_machine[self._machine_current_state]["method"]()

    def close(self):
        """close() -> deletes the connection from application_context
        and closes the the server.
        """

        del self._application_context["connections"][self]
        super(Socks5Node, self).close()

    def fileno(self):
        return self._socket.fileno()

    def event(self):
        #if self._is_first:
        event = events.BaseEvents.POLLERR
        if (
            self._state == constants.ACTIVE and
            not self.full_buffer() and 
            self._machine_current_state in (
                constants.CLIENT_RECV_GREETING,
                constants.CLIENT_RECV_CONNECTION_REQUEST,
                constants.RECV_GREETING,
                constants.RECV_CONNECTION_REQUEST,
                constants.PARTNER_STATE,
            )
        ):
            event |= events.BaseEvents.POLLIN
        if (self._machine_current_state in 
            (
                constants.CLIENT_SEND_GREETING,
                constants.CLIENT_SEND_CONNECTION_REQUEST,
                constants.SEND_GREETING,
                constants.SEND_CONNECTION_REQUEST,
                constants.PARTNER_STATE,
            )
        ):
            event |= events.BaseEvents.POLLOUT
        return event
        # else:
            # return super(Socks5Node, self).event()
