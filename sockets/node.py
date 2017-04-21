#!/usr/bin/python

import logging
import traceback

from base_socket import BaseSocket
from socks5_node import Socks5Node
from common import constants
from async import events
from async import pollable
import socket
from socks5_first_node import Socks5FirstNode
from socks5_server import Socks5Server
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
        is_first=False,
    ):
        self._socket = socket
        self._socket.setblocking(False)
        self._socket.bind((bind_address, bind_port))
        self._socket.listen(max_connections)

        self._state = state
        self._application_context = application_context

        self._bind_address = bind_address
        self._bind_port = bind_port
        self._is_first = is_first

        self._key = random.randint(0, 256)

    def read(self):
        try:
            server = None
            if self._is_first:
                self._first_node()
            else:
                s, addr = self._socket.accept()

                server = Socks5Server(
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

    def _first_node(self):
        client_proxy = None

        s, addr = self._socket.accept()

        client_proxy = BaseSocket(
            s,
            constants.ACTIVE,
            self._application_context,
            self._bind_address,
            self._bind_port,
        )

        socks5_node = Socks5FirstNode(
            socket.socket(socket.AF_INET, socket.SOCK_STREAM),
            constants.ACTIVE,
            self._application_context,
            client_proxy,
            path=self._find_nodes(),
            bind_address=self._bind_address,
            bind_port=self._bind_port,
        )

        client_proxy.partner = socks5_node

        self._application_context["socket_data"][
            socks5_node.fileno()
        ] = socks5_node

    def _find_nodes(self):
        path = {}

        counter = 1

        available_nodes = []
        for name in self._application_context["registry"]:
            if self._application_context["registry"][name]["node"] != self:
                available_nodes.append(name)
            else:
                path[str(counter)] = name
                # path[str(counter)] = [
                    # name,
                    # self._application_context["registry"][name]["address"],
                    # self._application_context["registry"][name]["port"],
                # ]
                counter += 1

        if not available_nodes:
            raise RuntimeError("Not Enough nodes registered, at least one more is required")
        
        if len(available_nodes) >= constants.OPTIMAL_NODES_IN_PATH:
            chosen_nodes = random.sample(available_nodes, constants.OPTIMAL_NODES_IN_PATH)

        else:
            chosen_nodes = random.sample(available_nodes, len(available_nodes))

            while len(chosen_nodes) < constants.OPTIMAL_NODES_IN_PATH:
                chosen_nodes += random.sample(
                    available_nodes,
                    min(len(available_nodes), constants.OPTIMAL_NODES_IN_PATH - len(chosen_nodes))
                )

        for name in chosen_nodes:
            path[str(counter)] = name
            # path[str(counter)] = [
                # self._application_context["registry"][name]["address"],
                # self._application_context["registry"][name]["port"],
            # ]
            counter += 1
        return path

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

    @property
    def key(self):
        return self._key
