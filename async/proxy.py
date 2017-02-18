#!/usr/bin/python

import errno
import logging
import select
import socket
import traceback

from sockets.listener import Listener
from common import constants
from common import util

from events import (
    BaseEvents,
    SelectEvents,
)


class Proxy(object):

    _close_proxy = False
    _socket_data = {}

    def __init__(
        self,
        poll_timeout=10000,
        block_size=1024,
        poll_object=SelectEvents,
        application_context={},
    ):
        self._poll_timeout = poll_timeout
        self._block_size = block_size

        self._poll_object = poll_object

        self._application_context = application_context
        self._application_context["socket_data"] = self._socket_data

    def close_proxy(self):
        self._close_proxy = True

    def add_listener(
        self,
        bind_address,
        bind_port,
        server_type,
        connect_address=None,
        connect_port=None,
        max_conn=constants.MAX_LISTENER_CONNECTIONS,
    ):
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket_data[listener.fileno()] = {
            "async_socket": Listener(
                listener,
                bind_address,
                bind_port,
                max_conn,
                self._socket_data,
                server_type,
                self._application_context,
            ),
            "state": constants.PROXY_LISTEN,
        }

    def run(self):
        while self._socket_data:
            try:
                if self._close_proxy:
                    self._terminate()
                for fd in self._socket_data.keys()[:]:
                    entry = self._socket_data[fd]
                    if (
                        entry["state"] == constants.PROXY_CLOSING and
                        not entry["async_socket"].buffer
                    ):
                        self._remove_socket(entry["async_socket"])
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
                                    entry["async_socket"].read()
                                except socket.error as e:
                                    if e.errno != errno.EWOULDBLOCK:
                                        raise
                            if event & BaseEvents.POLLOUT:
                                try:
                                    entry["async_socket"].write()
                                except socket.error as e:
                                    if e.errno != errno.EWOULDBLOCK:
                                        raise
                        except util.DisconnectError:
                            self._close_connection(
                                entry,
                                entry["async_socket"].partner,
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
                                entry["async_socket"].partner,
                            )
                except select.error as e:
                    if e[0] != errno.EINTR:
                        raise
            except Exception as e:
                logging.critical(traceback.format_exc())
                self._terminate()

    def _create_poller(self):
        poller = self._poll_object()
        for fd in self._socket_data:
            entry = self._socket_data[fd]
            event = BaseEvents.POLLERR
            if (
                entry["state"] == constants.PROXY_LISTEN or
                (
                    entry["state"] == constants.PROXY_ACTIVE and
                    len(
                        entry["async_socket"].buffer
                    ) < self._block_size
                )
            ):
                event |= BaseEvents.POLLIN
            if entry["async_socket"].buffer:
                event |= BaseEvents.POLLOUT
            poller.register(entry["async_socket"].socket, event)
        return poller

    def _close_connection(self, entry, partner):
        entry["state"] = constants.PROXY_CLOSING
        if partner is not None:
            self._socket_data[
                partner.socket.fileno()
            ]["state"] = constants.PROXY_CLOSING
        entry["async_socket"].buffer = ""

    def _remove_socket(self, async_socket):
        try:
            del self._socket_data[async_socket.socket.fileno()]
            async_socket.close()
        except Exception:
            print traceback.format_exc()
            import sys
            sys.exit(0)

    def _terminate(self):
        for x in self._socket_data:
            self._socket_data[x]["state"] = constants.PROXY_CLOSING
