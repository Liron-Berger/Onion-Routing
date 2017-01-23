#!/usr/bin/python

import errno
import logging
import socket
import traceback

import async
import constants
import socks5_packets

from errors import (
    DisconnectError,
    NotEnoughArguments,
)


class BaseSocket(object):

    def __init__(
        self,
        socket,
        socket_data,
    ):
        self._socket = socket
        self._socket.setblocking(False)

        self._buffer = ""
        self._partner = None

        self._socket_data = socket_data

    def read(self, target=None, max_size=constants.MAX_BUFFER_SIZE):
        if not target:
            target = self._partner
        while len(target.buffer) < max_size:
            data = self._socket.recv(
                max_size - len(target.buffer),
            )
            if not data:
                raise DisconnectError()
            target.buffer += data

    def write(self):
        while self._buffer:
            self._buffer = self._buffer[
                self._socket.send(
                    self._buffer
                ):
            ]

    def close(self):
        self._socket.close()
        self._buffer = ""

    @property
    def socket(self):
        return self._socket

    @socket.setter
    def socket(self, socket):
        self._socket = socket

    @property
    def buffer(self):
        return self._buffer

    @buffer.setter
    def buffer(self, buffer):
        self._buffer = buffer

    @property
    def partner(self):
        return self._partner

    @partner.setter
    def partner(self, partner):
        self._partner = partner


class Socks5Server(BaseSocket):

    def _greeting_request(self):
        try:
            request = socks5_packets.GreetingRequest.decode(self._buffer)
        except NotEnoughArguments:
            logging.error(traceback.format_exc())

        method = constants.NO_ACCEPTABLE_METHODS
        for m in request["methods"]:
            if m in constants.SUPPORTED_METHODS:
                method = m
                break
        self._buffer = socks5_packets.GreetingResponse.encode(
            {
                "version": request["version"],
                "method": method,
            },
        )

    def _socks5_request(self):
        try:
            request = socks5_packets.Socks5Request.decode(self._buffer)
        except NotEnoughArguments:
            logging.warning(traceback.format_exc())
            return

        if request["command"] not in constants.SUPPORTED_COMMANDS:
            raise NotImplementedError()

        if request["command"] == constants.CONNECT:
            reply = self.create_connection(
                request["dst_address"],
                request["dst_port"],
            )
        self._buffer = socks5_packets.Socks5Response.encode(
            {
                "version": request["version"],
                "reply": reply,
                "reserved": constants.RESERVED,
                "address_type": request["address_type"],
                "dst_address": request["dst_address"],
                "dst_port": request["dst_port"],
            },
        )

    STATES = (
        GREETING_REQUEST,
        SOCKS5_REQUEST,
        ACTIVE,
    ) = range(3)

    MAP = {
        GREETING_REQUEST: {
            "method": _greeting_request,
            "next": SOCKS5_REQUEST,
        },
        SOCKS5_REQUEST: {
            "method": _socks5_request,
            "next": ACTIVE,
        },
    }

    def __init__(
        self,
        socket,
        socket_data,
    ):
        super(Socks5Server, self).__init__(socket, socket_data)
        self._state = self.GREETING_REQUEST

    def read(self, max_size=constants.MAX_BUFFER_SIZE):
        if self._state == Socks5Server.ACTIVE:
            super(Socks5Server, self).read()
        else:
            super(Socks5Server, self).read(target=self)

    def write(self):
        if self._state != Socks5Server.ACTIVE:
            self.MAP[self._state]["method"](self)
            self._state = self.MAP[self._state]["next"]
        super(Socks5Server, self).write()

    def create_connection(self, addr, port):
        reply = constants.SUCCESS
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
                "state": async.Proxy.ACTIVE,
            }
        except socket.error as e:
            if e.errno not in (errno.EINPROGRESS, errno.EWOULDBLOCK):
                logging.error(traceback.format_exc())
                reply = constants.CONNECTION_REFUSED
        except Exception as e:
            logging.error(traceback.format_exc())
            reply = constants.GENERAL_SERVER_FAILURE
        return reply


class BaseListener(BaseSocket):

    NAME = "Base"

    def __init__(
        self,
        socket,
        bind_address,
        bind_port,
        max_conn,
        socket_data,
    ):
        super(BaseListener, self).__init__(socket, socket_data)

        self._socket.bind((bind_address, bind_port))
        self._socket.listen(max_conn)

    def read(self):
        try:
            server = None

            s, addr = self._socket.accept()

            server = BaseSocket(
                s,
                self._socket_data,
            )

            self._socket_data[
                server.socket.fileno()
            ] = {
                "async_socket": server,
                "state": async.Proxy.ACTIVE,
            }
        except Exception:
            logging.error(traceback.format_exc())
            if server:
                server.socket.close()


class Socks5Listener(BaseListener):

    def read(self):
        try:
            server = None

            s, addr = self._socket.accept()

            server = Socks5Server(
                s,
                self._socket_data,
            )

            self._socket_data[
                server.socket.fileno()
            ] = {
                "async_socket": server,
                "state": async.Proxy.ACTIVE,
            }
        except Exception:
            logging.error(traceback.format_exc())
            if server:
                server.socket.close()


class HttpListener(BaseListener):

    def read(self):
        try:
            server = None

            s, addr = self._socket.accept()

            server = HttpServer(
                s,
                self._socket_data,
            )

            self._socket_data[
                server.socket.fileno()
            ] = {
                "async_socket": server,
                "state": async.Proxy.ACTIVE,
            }
        except Exception:
            logging.error(traceback.format_exc())
            if server:
                server.socket.close()

'''
class HttpServer(BaseSocket):

    STATES = (
        GREETING_REQUEST,
        SOCKS5_REQUEST,
        ACTIVE,
    ) = range(3)

    MAP = {
        GREETING_REQUEST: {
            "method": _greeting_request,
            "next": SOCKS5_REQUEST,
        },
        SOCKS5_REQUEST: {
            "method": _socks5_request,
            "next": ACTIVE,
        },
    }

    def __init__(
        self,
        socket,
        socket_data,
    ):
        super(Socks5Server, self).__init__(socket, socket_data)
        self._state = self.GREETING_REQUEST

    def read(self, max_size=constants.MAX_BUFFER_SIZE):
        if self._state == Socks5Server.ACTIVE:
            super(Socks5Server, self).read()
        else:
            super(Socks5Server, self).read(target=self)

    def write(self):
        if self._state != Socks5Server.ACTIVE:
            self.MAP[self._state]["method"](self)
            self._state = self.MAP[self._state]["next"]
        super(Socks5Server, self).write()
'''