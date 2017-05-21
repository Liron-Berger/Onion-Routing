#!/usr/bin/python

import errno
import socket

from common import constants
from common.utilities import util
from common.pollables import pollable
from common.async import event_object


class BaseSocket(pollable.Pollable):

    def __init__(
        self,
        socket,
        state,
        app_context,
    ):
        self._socket = socket
        self._socket.setblocking(False)

        self._state = state
        self._buffer = ""
        self._partner = self

        self._app_context = app_context
        self._partner = self


    def on_read(self):
        self._partner.buffer += util.recieve_buffer(
            self._socket,
            self._app_context["max_buffer_size"] - len(self._partner.buffer),
        )

    def on_write(self):
        self._buffer = util.send_buffer(
            self._socket,
            self._buffer,
        )

    def on_close(self):
        self._state = constants.CLOSING
        self._buffer = ""
        
        if self != self._partner and not (self._partner.state == constants.CLOSING and self._partner.buffer == ""):
            self._partner.on_close()

    def is_closing(self):
        return self._state == constants.CLOSING and not self._buffer

    def close(self):       
        self._socket.close()

    def get_events(self):
        event = event_object.BaseEvent.POLLERR
        if (
            self._state == constants.ACTIVE and
            not len(self._buffer) >= self._app_context["max_buffer_size"]
        ):
            event |= event_object.BaseEvent.POLLIN
        if self._buffer:
            event |= event_object.BaseEvent.POLLOUT
        return event

    def fileno(self):
        return self._socket.fileno()    
        
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


    def __repr__(self):
        return "BaseSocket object %s" % (
            self.fileno(),
        )
