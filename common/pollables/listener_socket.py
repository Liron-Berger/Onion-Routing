#!/usr/bin/python
## @package onion_routing.common.pollables.listener_socket
# Base class for all listener sockets used for the poller.
#

import logging
import socket
import traceback

from common import constants
from common.async import event_object
from common.pollables import pollable


## Basic implementation of asynchronous TCP listener.
# Used by async_server to accept new connections for the poller.
#
class Listener(pollable.Pollable):

    ## Constructor.
    # @param bind_address (str) bind address for the listener.
    # @param bind_port (int) bind port for the listener.
    # @param app_context (dict) application context.
    # @param listener_type (optional, @ref common.pollables.tcp_socket)
    # type of socket to listen to.
    #
    # Creates a new socket and binds it to (bind_address, bind_port).
    # Starts in LISTEN state.
    #
    def __init__(
        self,
        bind_address,
        bind_port,
        app_context,
        listener_type=None,
    ):
        ## Socket used by the Listener.
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.bind((bind_address, bind_port))
        self._socket.listen(app_context["max_connections"])
        self._socket.setblocking(False)

        ## State of Listener.
        self._state = constants.LISTEN

        ## type of wrapper used by Listener for accepted sockets.
        self._type = listener_type

        ## Application context.
        self._app_context = app_context

    ## On read event.
    # Accept new connection.
    # Wrap client according to @ref _type.
    # Add socket to socket_data of @ref common.async.async_server.
    #
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

    ## On write event.
    def on_write(self):
        pass

    ## On close event.
    # Change @ref _state of socket to CLOSING.
    #
    def on_close(self):
        self._state = constants.CLOSING

    ## Is closing.
    # @returns (bool) True if ready for closing.
    #
    # Socket is ready for closing when @ref _state is CLOSING.
    #
    def is_closing(self):
        return self._state == constants.CLOSING

    ## Close Listener.
    # Closing @ref _socket.
    #
    def close(self):
        self._socket.close()

    ## Get events for poller.
    # @retuns (int) events to register for poller.
    #
    # POLLIN when @ref _state is LISTEN.
    #
    def get_events(self):
        event = event_object.BaseEvent.POLLERR
        if self._state == constants.LISTEN:
            event |= event_object.BaseEvent.POLLIN
        return event

    ## fileno of Listener.
    def fileno(self):
        return self._socket.fileno()

    ## Retrive @ref _socket.
    @property
    def socket(self):
        return self._socket

    ## String representation.
    def __repr__(self):
        return "Listener object of type %s. fileno: %d." % (
            self._type,
            self.fileno(),
        )
