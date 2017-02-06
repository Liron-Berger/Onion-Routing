#!/usr/bin/python

import errno
import logging
import os
import select
import socket
import traceback

import async_sockets
import constants
import util


class BaseEvents(object):
    POLLIN, POLLOUT, POLLERR, POLLHUP = (
        1, 4, 8, 16,
    ) if os.name == "nt" else (
        select.POLLIN, select.POLLOUT, select.POLLERR, select.POLLHUP,
    )

    NAME = "base"

    def __init__(self):
        pass

    def register(self, fd, event):
        pass

    def poll(self, timeout):
        raise NotImplementedError()

    def supported(self):
        pass


if os.name != "nt":
    class PollEvents(BaseEvents):
        NAME = "Poll"

        def __init__(self):
            super(PollEvents, self).__init__()
            self._poller = select.poll()

        def register(self, fd, event):
            self._poller.register(fd, event)

        def poll(self, timeout):
            return self._poller.poll(timeout)


class SelectEvents(BaseEvents):
    NAME = "Select"

    def __init__(self):
        super(SelectEvents, self).__init__()
        self._fd_dict = {}

    def register(self, fd, event):
        self._fd_dict[fd] = event

    def poll(self, timeout):
        rlist, wlist, xlist = [], [], []

        for fd in self._fd_dict:
            if self._fd_dict[fd] & SelectEvents.POLLERR:
                xlist.append(fd)
            if self._fd_dict[fd] & SelectEvents.POLLIN:
                rlist.append(fd)
            if self._fd_dict[fd] & SelectEvents.POLLOUT:
                wlist.append(fd)

        r, w, x = select.select(rlist, wlist, xlist, timeout)

        poll_dict = {}
        for s in r + w + x:
            if s in r:
                poll_dict[s.fileno()] = SelectEvents.POLLIN
            if s in w:
                poll_dict[s.fileno()] = SelectEvents.POLLOUT
            if s in x:
                poll_dict[s.fileno()] = SelectEvents.POLLERR
        return poll_dict.items()


class Proxy(object):

    CLOSING, LISTEN, ACTIVE = range(3)

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
            "async_socket": async_sockets.Listener(
                listener,
                bind_address,
                bind_port,
                max_conn,
                self._socket_data,
                server_type,
                self._application_context,
            ),
            "state": Proxy.LISTEN,
        }

    def run(self):
        while self._socket_data:
            try:
                if self._close_proxy:
                    self._terminate()
                for fd in self._socket_data.keys()[:]:
                    entry = self._socket_data[fd]
                    if (
                        entry["state"] == Proxy.CLOSING and
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
                entry["state"] == Proxy.LISTEN or
                (
                    entry["state"] == Proxy.ACTIVE and
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
        entry["state"] = Proxy.CLOSING
        if partner is not None:
            self._socket_data[partner.socket.fileno()] = Proxy.CLOSING
        entry["async_socket"].buffer = ""        

    def _remove_socket(self, async_socket):
        del self._socket_data[async_socket.socket.fileno()]
        async_socket.close()

    def _terminate(self):
        for x in self._socket_data:
            self._socket_data[x]["state"] = Proxy.CLOSING
