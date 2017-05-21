#!/usr/bin/python

import logging
import socket
import traceback

from common import constants
from common.async import event_object
from common.pollables import pollable


class Listener(pollable.Pollable):

    def __init__(
        self,
        bind_address,
        bind_port,
        app_context,
        listener_type=None,
    ):
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.bind((bind_address, bind_port))
        self._socket.listen(app_context["max_connections"])
        self._socket.setblocking(False)

        self._state = constants.LISTEN
        
        self._type = listener_type
        self._app_context = app_context

    def on_read(self):
        try:
            server = None

            client, addr = self._socket.accept()

            server = self._type(
                socket=client,
                state=constants.ACTIVE,
                app_context=self._app_context,
            )

            self._app_context["socket_data"][server.fileno()] = server

        except Exception:
            logging.error(traceback.format_exc())
            if server:
                server.close()
        
    def on_close(self):
        self._state = constants.CLOSING

    def is_closing(self):
        return self._state == constants.CLOSING

    def close(self):
        self._socket.close()

    def get_events(self):
        event = event_object.BaseEvent.POLLERR
        if self._state == constants.LISTEN:
            event |= event_object.BaseEvent.POLLIN
        return event

    def fileno(self):
        return self._socket.fileno()

    @property
    def socket(self):
        return self._socket

    def __repr__(self):
        return "Listener object of type %s" % (
            self._type,
        )
