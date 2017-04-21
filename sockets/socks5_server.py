#!/usr/bin/python

import errno
import logging
import socket
import traceback

from common import constants
from common import util

from base_socket import BaseSocket


class Socks5Server(BaseSocket):
    """Socks5Server(socket, state, application_context) -> Socks5Server object.

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
        application_context,
        bind_address,
        bind_port=9999,
        key=0,
    ):
        super(Socks5Server, self).__init__(
            socket,
            state,
            application_context,
            bind_address,
            bind_port,
        )
        self._machine_current_state = constants.RECV_GREETING
        self._state_machine = self._create_state_machine()
        self._command_map = self._create_command_map()
        self._request_context = {}

        self._start_byte_counter()

        self._key = key

    def __repr__(self):
        return "Socks5Server object. address %s, port %s" % (
            self._bind_address,
            self._bind_port,
        )

    def _create_state_machine(self):
        """_create_state_machine() -> returns a dict the states socks5 server is using.

        for each part of socks communication a state is created.
        dictionary is - [constant for state : method for state.
        """

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
        """_create_command_map() -> returns a dict with all commands.

        command is sent by the client, and dict stores only the supported commands
        by the server.
        dictionary is - [constant for command : method for command].
        """

        return {
            constants.CONNECT: self._connect_command,
        }

    def _recv_greeting(self):
        """_recv_greeting() -> the first state in the state machine.

        gets the message from the client, and if found valid saves a
        response in the buffer. request structure:
            +----+----------+----------+
            |VER | NMETHODS | METHODS  |
            +----+----------+----------+
            | 1  |    1     | 1 to 255 |
            +----+----------+----------+
        when complete - state is SEND_GREETING.
        """

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
        """_send_greeting() -> the second state in the state machine.

        sends the socks5 response to the client. response structure:
            +----+--------+
            |VER | METHOD |
            +----+--------+
            | 1  |   1    |
            +----+--------+
        once sending is complete - state is RECV_CONNECTION_REQUEST.
        """

        super(Socks5Server, self).write()
        self._request_context = {}
        self._machine_current_state = self._state_machine[
            self._machine_current_state
        ]["next"]

    def _recv_connection_request(self):
        """_recv_connection_request() -> the third state.

        gets the next message from client, containing the wanted action
        (called command) the client asks for, and the address + port the client
        wants to establish connection with. 
        when recieved, checks if message is valid and builds the response.
        when command is recieved, if supported -> runs the action.
        request structure:
            +----+-----+-------+------+----------+----------+
            |VER | CMD |  RSV  | ATYP | DST.ADDR | DST.PORT |
            +----+-----+-------+------+----------+----------+
            | 1  |  1  | X'00' |  1   | Variable |    2     |
            +----+-----+-------+------+----------+----------+
        when comlete - state is SEND_CONNECTION_REQUEST. 
        """

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
        """_send_connection_request() -> the forth state.

        the last part of the socks5 communication.
        sends the client the address + port he was connected to,
        and the status of the action asked by the client.
        response structure:
            +----+-----+-------+------+----------+----------+
            |VER | REP |  RSV  | ATYP | BND.ADDR | BND.PORT |
            +----+-----+-------+------+----------+----------+
            | 1  |  1  | X'00' |  1   | Variable |    2     |
            +----+-----+-------+------+----------+----------+
        when complete - state is PARTNER_STATE.
        """

        super(Socks5Server, self).write()
        self._request_context = {}
        self._machine_current_state = self._state_machine[
            self._machine_current_state
        ]["next"]

    def _partner_state(self):
        """_partner_state() -> state where server serves as a proxy
        for regular TCP communication between the client and the
        address + port he was connected to by this server.
        """
        
        super(Socks5Server, self).write()

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
        """_connect(address, port) -> make this server a proxy between client
        and (address, port).

        creates a new BaseSocket and socket that connects to (address, port).
        partner now is the new BaseSocket.
        new BaseSocket partner is self.
        """

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
                self._bind_address,
                self._bind_port,
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

        while not self._partner.full_buffer():
            data = self._socket.recv(
                self._max_buffer_size - len(self._partner.buffer),
            )
            if not data:
                raise util.DisconnectError()

            self._update_byte_counter(len(data))
            self._partner.buffer += data

    def write(self):
        """write() -> runs the current state in state machine."""

        self._state_machine[self._machine_current_state]["method"]()

    def close(self):
        """close() -> deletes the connection from application_context
        and closes the the server.
        """

        del self._application_context["connections"][self]
        super(Socks5Server, self).close()

    def fileno(self):
        return self._socket.fileno()
