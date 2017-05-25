#!/usr/bin/python
## @package onion_routing.common.async.async_server
# Server for handling asynchronous I/O.
#

import errno
import logging
import select
import traceback

from common.async import event_object
from common.utilities import util


## Async Server.
#
# Handles events of all participating sockets.
#
class AsyncServer(object):

    ## Whether to terminate the server.
    terminate = False
    ## Database of all participating sockets for handling requests.
    _socket_data = {}

    ## Constructor.
    # @param app_context (dict) application_context.
    #
    def __init__(
        self,
        app_context,
    ):
        self._poll_object = app_context["poll_object"]
        self._timeout = app_context["timeout"]
        self._app_context = app_context

        self._app_context["socket_data"] = self._socket_data

    ## Create new poller.
    # @returns (dict) key - socket fd, value - event.
    # Use event_object to create new poller and handle all events
    # of all sockets.
    #
    def _create_poller(self):
        poller = self._poll_object()
        for fd in self._socket_data:
            entry = self._socket_data[fd]
            poller.register(entry.socket, entry.get_events())
        return poller

    ## Remove socket.
    # @param entry (@ref common.pollables.pollable) wrapper of socket.
    # Close socket and remove it from socket data.
    #
    def _remove_socket(
        self,
        entry,
    ):
        logging.debug("remove %s" % entry)

        entry.on_close()
        del self._socket_data[entry.fileno()]
        entry.close()

    ## Terminate the server.
    # Enters common.pollables.pollable.Pollable.on_close()
    # state for all pollables in socket data.
    #
    def _terminate(self):
        logging.info("Terminating")
        for entry in self._socket_data.values():
            entry.on_close()

    ## Close server.
    def close_server(self):
        self.terminate = True

    ## Add listener to socket data.
    # @param listener_class (@ref common.pollables.listener_socket)
    # type of new listener.
    # @param bind_address (str) address to bind listener.
    # @param bind_port (int) port to bind listener.
    # @param listener_type (optional, @ref common.pollables.pollable) type of
    # sockets to listen to.
    #
    # @returns common.pollables.listener_socket new listener.
    #
    def add_listener(
        self,
        listener_class,
        bind_address,
        bind_port,
        listener_type=None,
    ):
        listener = listener_class(
            bind_address,
            bind_port,
            self._app_context,
            listener_type,
        )
        self._socket_data[listener.fileno()] = listener
        return listener

    ## Add @ref pollable to socket data.
    def add_socket(
        self,
        async_socket,
    ):
        self._socket_data[async_socket.fileno()] = async_socket

    ## Main loop - running server.
    def run(self):
        while self._socket_data:
            try:
                if self.terminate:
                    self._terminate()
                for entry in self._socket_data.values()[:]:
                    if entry.is_closing():
                        self._remove_socket(entry)
                try:
                    for fd, event in self._create_poller().poll(self._timeout):
                        entry = self._socket_data[fd]
                        logging.debug("event %d: %s" % (event, entry))
                        try:
                            if (
                                event &
                                (
                                    event_object.BaseEvent.POLLHUP |
                                    event_object.BaseEvent.POLLERR
                                )
                            ):
                                raise RuntimeError("socket connection broken")
                            if event & event_object.BaseEvent.POLLIN:
                                entry.on_read()
                            if event & event_object.BaseEvent.POLLOUT:
                                entry.on_write()
                        except util.DisconnectError:
                            entry.on_close()
                        except Exception as e:
                            logging.error(traceback.format_exc())
                            entry.on_close()
                except select.error as e:
                    if e[0] != errno.EINTR:
                        raise
            except Exception as e:
                logging.critical(traceback.format_exc())
                self._terminate()
