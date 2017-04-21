#!/usr/bin/python

import logging
import traceback

from base_socket import BaseSocket
from common import constants
from async import events
from async import pollable


class Listener(pollable.Pollable):
    """Listener(
        socket,
        state,
        listener_type,
        bind_address,
        bind_port,
        max_connections,
        application_context
    ) -> Listener object.

    inherits from pollable.
    creates a wrapper for socket that is used for creating new connections
    in async proxy.
    properties:
        socket - regular python socket used for accepting new connections.
        state - (ACTIVE, LISTEN, CLOSE) for reading and writing in proxy.
        listener_type - the type of async socket (pollable object) that should 
            be created when a new connections is accepted.

        application_context - dictionary that stores the important data for
            the application.
    """

    def __init__(
        self,
        socket,
        state,
        listener_type,
        bind_address,
        bind_port,
        max_connections,
        application_context,
    ):
        self._socket = socket
        self._socket.setblocking(False)
        self._socket.bind((bind_address, bind_port))
        self._socket.listen(max_connections)

        self._state = state
        self._listener_type = listener_type
        self._application_context = application_context

        self._bind_address = bind_address
        self._bind_port = bind_port

    def read(self):
        """read() -> accept new connection.

        when read event is received, accepts the new connection.
        for the new received socket creates an async socket of type listener_type.
        adds the new socket to socket_data in application_context.
        """

        try:
            server = None

            s, addr = self._socket.accept()

            server = self._listener_type(
                s,
                constants.ACTIVE,
                self._application_context,
                self._bind_address,
                self._bind_port,
            )

            self._application_context["socket_data"][
                server.socket.fileno()
            ] = server

        except Exception:
            logging.error(traceback.format_exc())
            if server:
                server.socket.close()

    def event(self):
        """event() -> returns the needed async event to async proxy.

        default is error.
        state is LISTEN - event is read.
        """

        event = events.BaseEvents.POLLERR
        if self._state == constants.LISTEN:
            event |= events.BaseEvents.POLLIN
        return event

    def fileno(self):
        """fileno() -> returns socket's fileno."""

        return self._socket.fileno()

    def close(self):
        """close() -> close the socket."""

        self._socket.close()

    def remove(self):
        """remove() -> returns whether socket should be removed."""

        return self._state == constants.CLOSING

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
