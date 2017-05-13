#!/usr/bin/python

import errno
import logging
import select
import socket
import traceback

import sockets

from common import constants
from common import util
from events import BaseEvents

class AsyncServer(object):

    _close_server = False
    _socket_data = {}

    def __init__(
        self,
        application_context,
    ):
        self._application_context = application_context
        self._application_context["socket_data"] = self._socket_data

        self._poll_object = application_context["poll_object"]
        self._poll_timeout = application_context["poll_timeout"]
        self._max_connections = application_context["max_connections"]
        self._xml = application_context["xml"]

        
    def _create_poller(self):
        poller = self._poll_object()
        for fd in self._socket_data:
            entry = self._socket_data[fd]
            poller.register(entry.socket, entry.event())
        return poller

    def _close_connection(
        self,
        entry,
    ):
        if entry.state != constants.LISTEN:
            logging.debug(
                "closing socket - fd: %d closed, fd: %s %s" % (
                    entry.fileno(),
                    entry.partner.fileno() if entry.partner else "",
                    "closed" if entry.partner else "parter is None"
                ),
            )
        entry.close_handler()

    def _remove_socket(
        self,
        entry,
    ):
        logging.debug(
            "socket fd: %d removed from socket_data" % (
                entry.fileno(),
            ),
        )
        entry.close_handler()
        del self._socket_data[entry.fileno()]
        entry.close()

    def _terminate(self):
        logging.info(
            "Terminating the server"
        )
        for entry in self._socket_data.values():
            entry.state = constants.CLOSING

    def close_server(self):
        self._close_server = True
        
    def add_listener(
        self,
        listener_class,
        bind_address,
        bind_port,
        *args
    ):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listener = listener_class(
            s,
            constants.LISTEN,
            bind_address,
            bind_port,
            self._application_context,
            *args
        )
        self._socket_data[s.fileno()] = listener
        logging.info("New %s added." % listener)
        return listener
        
    def add_socket(
        self,
        socket_class,
        address,
        port,
        *args
    ):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        async_socket = socket_class(
            s,
            constants.ACTIVE,
            self._application_context,
            address,
            port,
            *args
        )
        self._socket_data[s.fileno()] = async_socket
        logging.info("New %s added." % async_socket)
        return async_socket
        
    def run(self):
        while self._socket_data:
            try:                    
                if self._close_server:
                    self._terminate()
                for fd in self._socket_data.keys()[:]:
                    entry = self._socket_data[fd]
                    if entry.remove():
                        self._remove_socket(entry)
                try:
                    update_statistics = False
                    for fd, event in self._create_poller().poll(
                        self._poll_timeout,
                    ):
                        update_statistics = True
                        logging.debug(
                            "event: %d, socket fd: %d. %s" % (
                                event,
                                fd,
                                entry,
                            ),
                        )
                        entry = self._socket_data[fd]
                        try:
                            if (
                                event &
                                (
                                    BaseEvents.POLLHUP |
                                    BaseEvents.POLLERR
                                )
                            ):
                                raise RuntimeError("socket connection broken")
                            if event & BaseEvents.POLLIN:
                                try:
                                    entry.read()
                                except socket.error as e:
                                    if e.errno != errno.EWOULDBLOCK:
                                        raise
                            if event & BaseEvents.POLLOUT:
                                try:
                                    entry.write()
                                except socket.error as e:
                                    if e.errno != errno.EWOULDBLOCK:
                                        raise
                        except util.DisconnectError:
                            self._close_connection(
                                entry,
                            )
                        except Exception as e:
                            logging.error(
                                "socket fd: %d, Exception: \n%s. socket: %s" % (
                                    fd,
                                    traceback.format_exc(),
                                    self._socket_data[fd],
                                ),
                            )
                            self._close_connection(
                                entry,
                            )
                    if update_statistics:
                        self._xml.update()
                except select.error as e:
                    if e[0] != errno.EINTR:
                        raise
            except Exception as e:
                logging.critical(traceback.format_exc())
                self._terminate()
                