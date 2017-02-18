#!/usr/bin/python

import logging

from common import constants

from common.util import DisconnectError


class BaseSocket(object):
    NAME = "BaseSocket"

    def __init__(
        self,
        socket,
        socket_data,
        application_context,
    ):
        self._socket = socket
        self._socket.setblocking(False)

        self._buffer = ""
        self._partner = None

        self._socket_data = socket_data
        self._application_context = application_context

    def read(
        self,
        target=None,
        max_size=constants.MAX_BUFFER_SIZE,
    ):
        if not target:
            target = self._partner
        while len(target.buffer) < max_size:
            data = self._socket.recv(
                max_size - len(target.buffer),
            )
            if not data:
                raise DisconnectError()
            target.buffer += data

    def write(
        self,
    ):
        while self._buffer:
            self._buffer = self._buffer[
                self._socket.send(
                    self._buffer
                ):
            ]

    def close(
        self,
    ):
        logging.info(
            "socket fd: %d closed" % (
                self._socket.fileno(),
            ),
        )
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
