#!/usr/bin/python

import errno
import traceback
import urlparse

from base_socket import BaseSocket
from common import constants
from services import BaseService
from services import GetFileService


class HttpServer(BaseSocket):
    NAME = "HttpServer"

    SERVICES = {
        service.NAME: {
            "service": service,
        } for service in BaseService.__subclasses__()
    }

    def __init__(self, socket, socket_data, application_context):
        super(HttpServer, self).__init__(
            socket,
            socket_data,
            application_context,
        )

        self._state = constants.RECV_STATUS
        self._service = {}
        self._service_class = None
        self._request_context = {
            "application_context": self._application_context,
            "accounts": {},
        }
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
            try:
                self._state_machine[self._state]()
            except IOError as e:
                traceback.print_exc()
                if self._state <= self._send_status:
                    self._state = constants.SEND_STATUS
                    if e.errno == errno.ENOENT:
                        self._send_error_message(
                            404,
                            "Not Found",
                            constants.MIME_MAPPING["txt"],
                            str(e),
                        )
                    else:
                        self._send_error_message(
                            500,
                            "Internal Error",
                            constants.MIME_MAPPING["txt"],
                            str(e),
                        )
            except Exception as e:
                traceback.print_exc()
                if self._state <= self._send_status:
                    self._state = constants.SEND_STATUS
                    self._send_error_message(
                        500,
                        "Internal Error",
                        constants.MIME_MAPPING["txt"],
                        str(e),
                    )
        self._reset()

    def _recv_status(self):
        valid_req, req_comps = self._http_request()
        if not valid_req:
            return

        method, uri, signature = req_comps
        parse = urlparse.urlparse(uri)

        self._service = self.SERVICES.get(parse.path, {})
        if self._service:
            self._service_class = self._service["service"](
                self._request_context,
                self._application_context,
                parse,
            )
        else:
            self._service_class = GetFileService(
                self._request_context,
                self._application_context,
                parse,
                uri,
            )
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
            self._request_context["headers"][x] = y.strip()
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
        self._service_class.run()

    def _send_status(self):
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
        for header, line in self._request_context["response_headers"].items():
            self._buffer += '%s: %s\r\n' % (header, line)
        self._buffer += '\r\n'
        super(HttpServer, self).write()
        self._state += 1

    def _send_content(self):
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

    def _send_error_message(
        self,
        code,
        status,
        type,
        error,
    ):
        self._request_context["code"] = code
        self._request_context["status"] = status
        self._request_context["response_headers"]["Content-Type"] = type
        self._request_context[
            "response_headers"
        ]["Content-Length"] = len(error)
        self._request_context[
            "response_headers"
        ]["Error"] = "%d %s" % (code, status)
        self._request_context["response"] = error

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
        self._request_context["response_headers"] = {}
        self._request_context["content"] = ""
        self._request_context["response"] = ""

        self._service = {}
        self._service_class = None
        self._state = constants.RECV_STATUS
