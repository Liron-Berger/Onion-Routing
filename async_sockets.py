#!/usr/bin/python

import errno
import logging
import socket
import traceback
import urlparse

import async
import constants
import services
import socks5_packets

from util import (
    DisconnectError,
    NotEnoughArguments,
)


class BaseSocket(object):
    NAME = "BaseSocket"

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
    NAME = "Socks5Server"

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


class Listener(BaseSocket):
    NAME = "Listener"

    def __init__(
        self,
        socket,
        bind_address,
        bind_port,
        max_conn,
        socket_data,
        server_type,
    ):
        super(Listener, self).__init__(socket, socket_data)

        self._socket.bind((bind_address, bind_port))
        self._socket.listen(max_conn)
        self._server_type = server_type

    def read(self):
        try:
            server = None

            s, addr = self._socket.accept()

            server = self._server_type(
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


class HttpServer(BaseSocket):
    NAME = "HttpServer"

    SERVICES = {
        service.NAME: {
            "service": service,
            "headers": service.HEADERS,
        } for service in services.BaseService.__subclasses__()
    }

    def __init__(self, socket, socket_data):
        super(HttpServer, self).__init__(socket, socket_data)

        self._state = constants.RECV_STATUS
        self._service = {}
        self._service_class = None
        self._request_context = {}
        self._state_machine = self._create_state_machine()

        self._reset()

    def _create_state_machine(self):
        return {
            constants.RECV_STATUS: self._recv_status,
            constants.RECV_HEADERS: self._recv_headers,
            constants.RECV_CONTENT: self._recv_content,
            constants.SEND_STATUS: self._send_status,
            constants.SEND_HEADERS: self._send_headers,
            constants.SEND_CONTENT: self._send_content,
        }

    def read(self):
        super(HttpServer, self).read(target=self)

    def write(self):
        while self._state <= constants.SEND_CONTENT:
            self._state_machine[self._state]()
        self._reset()

    def _recv_status(self):
        valid_req, req_comps = self._http_request()
        if not valid_req:
            return

        method, uri, signature = req_comps
        parse = urlparse.urlparse(uri)

        self._service = self.SERVICES.get(parse.path, {})
        if self._service:
            self._service_class = self._service["service"]()
        self._state += 1

    def _recv_headers(self):
        for i in range(constants.MAX_NUMBER_OF_HEADERS):
            line = self._recv_line()
            if line is None:
                break
            if not line:
                self._state += 1
                break
            x, y = line.split(":", 1)
            if x in self._service.get("headers", {}):
                self._request_context["service_headers"][x] = y
            self._request_context["headers"][x] = y
        else:
            raise RuntimeError('Too many headers')

    def _recv_content(self):
        if constants.CONTENT_LENGTH in self._request_context["headers"]:
            content_length = int(
                self._request_context["headers"][constants.CONTENT_LENGTH]
            )
            if len(self._buffer) > content_length:
                raise RuntimeError("Too much content")
            elif len(self._buffer) < content_length:
                return
            self._request_context["content"] = self._buffer
            self._buffer = ""
        self._state += 1

    def _send_status(self):
        self._service_class.status(self._request_context)
        self._buffer += (
            "%s %s %s\r\n"
        ) % (
            constants.HTTP_SIGNATURE,
            self._request_context["code"],
            self._request_context["status"]
        )
        super(HttpServer, self).write()
        self._state += 1

    def _send_headers(self):
        self._service_class.headers(self._request_context)
        for header, line in self._request_context["headers"].items():
            self._buffer += '%s: %s\r\n' % (header, line)
        self._buffer += '\r\n'
        print self._buffer
        super(HttpServer, self).write()
        self._state += 1

    def _send_content(self):
        self._service_class.content(self._request_context)
        self._buffer += self._request_context["response"]
        super(HttpServer, self).write()
        self._state += 1

    def _http_request(self):
        req = self._recv_line()
        if not req:
            return False, None

        req_comps = req.split(" ", 2)
        if len(req_comps) != 3:
            raise RuntimeError("Incomplete HTTP protocol")
        if req_comps[2] != constants.HTTP_SIGNATURE:
            raise RuntimeError("Not HTTP protocol")

        method, uri, signature = req_comps
        if method != 'GET':
            raise RuntimeError(
                "HTTP unsupported method '%s'" % method
            )
        if not uri or uri[0] != '/':
            raise RuntimeError("Invalid URI")

        return True, req_comps

    def _recv_line(self):
        n = self._buffer.find(constants.CRLF_BIN)

        if n == -1:
            return None

        line = self._buffer[:n].decode("utf-8")
        self._buffer = self._buffer[n + len(constants.CRLF_BIN):]
        return line

    def _reset(self):
        self._request_context["code"] = 200
        self._request_context["status"] = "OK"
        self._request_context["headers"] = {}
        self._request_context["service_headers"] = {}
        self._request_context["content"] = ""
        self._request_context["response"] = {}

        self._service = {}
        self._service_class = None
        self._state = constants.RECV_STATUS
