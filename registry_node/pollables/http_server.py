#!/usr/bin/python

import errno
import logging
import urlparse
import socket
import importlib


from common import constants
from common.async import event_object
from common.pollables import base_socket
from common.utilities import http_util
from common.utilities import util
from registry_node.services import base_service
from registry_node.services import file_service


class HttpServer(base_socket.BaseSocket):

    request_context = {}

    def __init__(
        self,
        socket,
        state,
        app_context,
    ):
        super(HttpServer, self).__init__(
            socket,
            state,
            app_context,
        )

        self._state_machine = self._create_state_machine()
        self._machine_state = constants.RECV_STATUS

        self._service_class = None

        self._reset()

        for service in constants.SERVICES:
            importlib.import_module(service)

        self.SERVICES = {
            service.NAME: service for service in base_service.BaseService.__subclasses__()
        }
    def _create_state_machine(
        self,
    ):
        return {
            constants.RECV_STATUS: {
                "method": self._recv_status,
                "next": constants.RECV_HEADERS,
            },
            constants.RECV_HEADERS: {
                "method": self._recv_headers,
                "next": constants.RECV_CONTENT,
            },
            constants.RECV_CONTENT: {
                "method": self._recv_content,
                "next": constants.SEND_STATUS,
            },
            constants.SEND_STATUS: {
                "method": self._send_status,
                "next": constants.SEND_HEADERS,
            },
            constants.SEND_HEADERS: {
                "method": self._send_headers,
                "next": constants.SEND_CONTENT,
            },
            constants.SEND_CONTENT: {
                "method": self._send_content,
                "next": constants.RECV_STATUS,
            },
        }

    def on_read(self):
        super(HttpServer, self).on_read()
        try:
            while self._machine_state <= constants.RECV_CONTENT:
                if self._state_machine[self._machine_state]["method"]():
                    self._machine_state = self._state_machine[
                        self._machine_state
                    ]["next"]
        except http_util.HTTPError as e:
            self._http_error(e)

    def on_write(self):
        try:
            while self._machine_state >= constants.SEND_STATUS and self._machine_state <= constants.SEND_CONTENT:
                if self._state_machine[self._machine_state]["method"]():
                    self._machine_state = self._state_machine[
                        self._machine_state
                    ]["next"]
        except http_util.HTTPError as e:
            self._http_error(e)

    def _recv_status(self):
        if not self._http_request():
            return False

        try:
            self._service_class = self.SERVICES.get(
                self.request_context["parse"].path,
                file_service.FileService,
            )(
                self.request_context,
                self._app_context,
            )
            logging.info("service %s was requested" % (self._service_class.NAME))
        except KeyError:
            raise http_util.HTTPError(
                code=500,
                status="Internal Error",
                message="service not supported",
            )
        self._service_class.before_request_headers()
        return True

    def _recv_headers(self):
        if self._get_headers():
            self._service_class.before_response_content()
            return True
        else:
            self._service_class.before_response_content()
            return False

    def _recv_content(self):
        self._get_content()
        while self._service_class.handle_content():
            pass
        if "content_length" not in self.request_context:
            self._service_class.before_response_status()
            return True
        elif not self._buffer:
            return False

    def _send_status(self):
        self._buffer = (
            "%s %s %s\r\n"
        ) % (
            constants.HTTP_SIGNATURE,
            self.request_context["code"],
            self.request_context["status"]
        )
        self._service_class.before_response_headers()
        return True

    def _send_headers(self):
        if self._set_headers():
            self._service_class.before_response_content()
            return True
        else:
            self._service_class.before_response_content()
            return False

    def _send_content(self):
        content = None
        content = self._service_class.response()
        if content is None:
            self._service_class.before_terminate()
            self._reset()
            return True
        else:
            self._buffer += content
            while self._buffer:
                self._buffer = self._buffer[
                    self._socket.send(
                        self._buffer
                    ):
                ]
            return False

    def get_events(self):
        event = event_object.BaseEvent.POLLERR
        if (
            self._state == constants.ACTIVE and
            not len(self._buffer) >= self._app_context["max_buffer_size"] and
            self._machine_state <= constants.RECV_CONTENT
        ):
            event |= event_object.BaseEvent.POLLIN
        if self._machine_state >= constants.SEND_STATUS and self._machine_state <= constants.SEND_CONTENT:
            event |= event_object.BaseEvent.POLLOUT
        return event

    def _reset(self):
        self.request_context = {
            "uri": "",
            "parse": "",
            "code": 200,
            "status": "OK",
            "request_headers": {},
            "response_headers": {},
            "response": "",
        }
        self._buffer = ""
        self._service_class = None

    def _http_request(self):
        req = self._recv_line()

        if not req:
            return False

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

        self.request_context["uri"] = uri
        self.request_context["parse"] = urlparse.urlparse(uri)

        return True

    def _get_headers(self):
        finished = False
        for i in range(constants.MAX_NUMBER_OF_HEADERS):
            line = self._recv_line()
            if line is None:
                break
            if line == "":
                finished = True
                break
            line = self._parse_header(line)
            if line[0] in self._service_class.wanted_headers():
                self.request_context["request_headers"][line[0]] = line[1]
        else:
            raise RuntimeError("Exceeded max number of headers")
        return finished

    def _get_content(self):
        if "content_length" in self.request_context:
            content = self._buffer[:min(
                self.request_context["content_length"],
                self._max_buffer_size - len(self.request_context["content"]),
            )]
            self.request_context["content"] += content
            self.request_context["content_length"] -= len(content)
            self._buffer = self._buffer[len(content):]

    def _set_headers(self):
        for key, value in self.request_context["response_headers"].iteritems():
            self._buffer += (
                "%s: %s\r\n" % (key, value)
            )
        self._buffer += ("\r\n")
        return True

    def _recv_line(self):
        n = self._buffer.find(constants.CRLF_BIN)

        if n == -1:
            return None

        line = self._buffer[:n].decode("utf-8")
        self._buffer = self._buffer[n + len(constants.CRLF_BIN):]
        return line

    def _parse_header(self, line):
        SEP = ':'
        n = line.find(SEP)
        if n == -1:
            raise RuntimeError('Invalid header received')
        return line[:n].rstrip(), line[n + len(SEP):].lstrip()

    def _http_error(self, e):
        self.request_context["code"] = e.code
        self.request_context["status"] = e.status
        self.request_context["response"] = e.message
        self.request_context[
            "response_headers"
        ]["Content-Length"] = len(self.request_context["response"])
        self.request_context[
            "response_headers"
        ]["Content-Type"] = "text/plain"
        self._service_class = base_service.BaseService(
            self.request_context,
            self._app_context,
        )
        self._machine_state = constants.SEND_STATUS

    # def __repr__(self):
        # return "HttpServer object. address %s, port %s" % (
            # self._bind_address,
            # self._bind_port,
        # )