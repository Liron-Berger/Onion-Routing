#!/usr/bin/python

from common.util import DisconnectError
from async import pollable
from async import events
from common import constants

import errno
import socket


class BaseSocket(pollable.Pollable):
    """BaseSocket(socket, state, application_context) -> BaseSocket object.

    Inherits from pollable.
    creates a wrapper for socket.
    properties:
        socket - regular python socket used for sending and writing.
        state - (ACTIVE, LISTEN, CLOSE) for reading and writing in proxy.
        buffer - a buffer for storing recieved and sending data.
        partner - the partner of the socket (used only in case of a proxy)
            as a default partner is this BaseSocket (self).
        max_buffer_size - maximum size of buffer.

        application_context - dictionary that stores the important data for
            the application.
    """

    def __init__(
        self,
        socket,
        state,
        application_context,
        bind_address,
        bind_port,
    ):
        self._socket = socket
        self._state = state
        self._max_buffer_size = application_context["max_buffer_size"]
        self._application_context = application_context
        self._buffer = ""
        self._partner = self

        self._socket.setblocking(False)

        self._bind_address = bind_address
        self._bind_port = bind_port
        
        self._fileno = socket.fileno()

    def __repr__(self):
        return "BaseSocket object %s. address %s, port %s" % (
            self.fileno(),
            self._bind_address,
            self._bind_port,
        )

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
                raise DisconnectError()
            self._partner.buffer += data
            

    def write(self):
        """write() -> sends the buffer to socket.

        sends until buffer is empty.
        if not the whole buffer was sent, buffer = the remaining message.
        """

        while self._buffer:
            self._buffer = self._buffer[
                self._socket.send(
                    self._buffer
                ):
            ]

    def event(self):
        """event() -> returns the needed async event to async proxy.

        default is error.
        buffer is not full and state is ACTIVE - event is read.
        buffer is not empty - event is write.
        """

        event = events.BaseEvents.POLLERR
        if (
            self._state == constants.ACTIVE and
            not self.full_buffer()
        ):
            event |= events.BaseEvents.POLLIN
        if self._buffer:
            event |= events.BaseEvents.POLLOUT
        return event

    def fileno(self):
        """fileno() -> returns socket's fileno."""

        return self._fileno

    def close(self):
        """close() -> closing socket and empty buffer."""
        
        self._socket.close()
        self._buffer = ""

    def remove(self):
        """remove() -> returns whether socket should be removed."""

        return self._state == constants.CLOSING and not self._buffer

    def full_buffer(self):
        """full_buffer() -> return whether buffer is bigger
            than max_buffer_size.
        """

        return len(self._buffer) >= self._max_buffer_size
        
    def close_handler(self):
        self._state = constants.CLOSING
        self._buffer = ""
        
        if self != self._partner and self._partner.buffer != "" and self.partner._state != constants.CLOSING:
            self._partner.close_handler()
        
    @property
    def socket(self):
        return self._socket

    @socket.setter
    def socket(self, socket):
        self._socket = socket

    @property
    def state(self):
        return self._state

    @state.setter
    def state(self, state):
        self._state = state

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
