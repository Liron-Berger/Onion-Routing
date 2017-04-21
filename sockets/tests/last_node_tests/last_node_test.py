#!/usr/bin/python

import logging
import traceback
import socket

from base_socket import BaseSocket
from common import constants
from async import events
from async import pollable
from socks5_last_node_test import Socks5Server

import random


class Node(pollable.Pollable):

    def __init__(
        self,
        socket,
        state,
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
        self._application_context = application_context

    def read(self):
        try:
            server = None

            s, addr = self._socket.accept()

            server = BaseSocket(
                s,
                constants.ACTIVE,
                self._application_context,
            )

            socks5_server = Socks5Server(
                socket.socket(socket.AF_INET, socket.SOCK_STREAM),
                constants.ACTIVE,
                self._application_context,
                server,
            )

            server.partner = socks5_server

            self._application_context["socket_data"][
                server.fileno()
            ] = server

            self._application_context["socket_data"][
                socks5_server.fileno()
            ] = socks5_server

        except Exception:
            logging.error(traceback.format_exc())
            if server:
                server.socket.close()

    def event(self):
        event = events.BaseEvents.POLLERR
        if self._state == constants.LISTEN:
            event |= events.BaseEvents.POLLIN
        return event

    def fileno(self):
        return self._socket.fileno()

    def close(self):
        self._socket.close()

    def remove(self):
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