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
        self._poll_object = application_context["poll_object"]
        self._poll_timeout = application_context["poll_timeout"]
        self._max_connections = application_context["max_connections"]
        self._application_context = application_context

        self._application_context["socket_data"] = self._socket_data
        self._application_context["async_server"] = self

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
        if entry.state == constants.LISTEN:
            entry.state = constants.CLOSING
        else:
            logging.debug(
                "closing socket - fd: %d closed, fd: %s %s" % (
                    entry.fileno(),
                    entry.partner.fileno() if entry.partner else "",
                    "closed" if entry.partner else "parter is None"
                ),
            )
            entry.state = constants.CLOSING
            if entry.partner is not None:
                entry.partner.state = constants.CLOSING
            entry.buffer = ""

    def _remove_socket(
        self,
        entry,
    ):
        logging.debug(
            "socket fd: %d removed from socket_data" % (
                entry.fileno(),
            ),
        )
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
        listener_type,
        bind_address,
        bind_port,
    ):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket_data[s.fileno()] = sockets.Listener(
            s,
            constants.LISTEN,
            bind_address,
            bind_port,
            self._application_context,
            listener_type,
        )
        logging.info(
            "New listener added: %s:%s. type: %s." % (
                bind_address,
                bind_port,
                listener_type,
            )
        )

    def add_node(
        self,
        name,
        bind_address,
        bind_port,
        is_first=False,
    ):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        node = sockets.Node(
            s,
            constants.LISTEN,
            bind_address,
            bind_port,
            self._application_context,
            is_first,
        )
        self._socket_data[s.fileno()] = node
        self._application_context["registry"][name] = {
            "address": bind_address,
            "port": bind_port,
            "key": node.key,
            "node": node,
        }
        logging.info(
            "New node added: %s" % (
                node,
            )
        )

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
                    for fd, event in self._create_poller().poll(
                        self._poll_timeout,
                    ):
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
