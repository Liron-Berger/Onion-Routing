#!/usr/bin/python

import errno
import logging
import select
import socket
import traceback

from common import constants
from common import util
from events import BaseEvents
from sockets import Listener


class Proxy(object):

    _close_proxy = False
    _socket_data = {}

    def __init__(
        self,
        application_context,
    ):
        self._poll_object = application_context["poll_object"]
        self._poll_timeout = application_context["poll_timeout"]
        self._max_connections = application_context["max_connections"]
        self._max_buffer_size = application_context["max_buffer_size"]
        self._application_context = application_context

        self._application_context["socket_data"] = self._socket_data

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
        entry.state = constants.CLOSING
        if entry.partner is not None:
            entry.partner.state = constants.CLOSING
        entry.buffer = ""

    def _remove_socket(
        self,
        entry,
    ):
        logging.info(
            "socket fd: %d closed" % (
                entry.socket.fileno(),
            ),
        )
        del self._socket_data[entry.socket.fileno()]
        entry.close()

    def _terminate(self):
        for entry in self._socket_data.values():
            entry.state = constants.CLOSING

    def close_proxy(self):
        self._close_proxy = True

    def add_listener(
        self,
        listener_type,
        bind_address,
        bind_port,
    ):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket_data[s.fileno()] = Listener(
            s,
            constants.LISTEN,
            listener_type,
            bind_address,
            bind_port,
            self._max_connections,
            self._application_context,
        )

    def run(self):
        while self._socket_data:
            try:
                if self._close_proxy:
                    self._terminate()
                for fd in self._socket_data.keys()[:]:
                    entry = self._socket_data[fd]
                    if entry.remove():
                        self._remove_socket(entry)
                try:
                    for fd, event in self._create_poller().poll(
                        self._poll_timeout,
                    ):
                        logging.info(
                            "event: %d, socket fd: %d" % (
                                event,
                                fd,
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
                                "socket fd: %d, Exception: \n%s" % (
                                    fd,
                                    traceback.format_exc(),
                                ),
                            )
                            self._close_connection(
                                entry,
                            )
                except select.error as e:
                    if e[0] != errno.EINTR:
                        raise
            except Exception as e:
                logging.critical(traceback.format_exc())
                self._terminate()
