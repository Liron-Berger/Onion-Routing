#!/usr/bin/python

import logging
import random
import socket
import traceback

import base_socket
import listener
import socks5_first_node
import socks5_server

from common import constants


class Node(listener.Listener):

    def __init__(
        self,
        sock,
        state,
        bind_address,
        bind_port,
        application_context,
        name="",
        is_first=False,
    ):
        super(Node, self).__init__(
            sock,
            state,
            bind_address,
            bind_port,
            application_context,
            listener_type=socks5_server.Socks5Server,
        )

        self._is_first = is_first
        self._key = random.randint(0, 256)
        self._name = name

    def __repr__(self):
        return "Node object. address %s, port %s" % (
            self._bind_address,
            self._bind_port,
        )

    def read(self):
        if not self._is_first:
            self._regular_node()
        else:
            self._first_node()
            
    def _regular_node(self):
        try:
            server = None

            s, addr = self._socket.accept()

            server = self._listener_type(
                s,
                constants.ACTIVE,
                self._application_context,
                self._bind_address,
                self._bind_port,
                self._key,
            )

            self._application_context["socket_data"][
                server.fileno()
            ] = server

        except Exception:
            logging.error(traceback.format_exc())
            if server:
                server.close()

    def _first_node(self):
        try:
            client_proxy = None
            socks5_node = None

            s, addr = self._socket.accept()

            client_proxy = base_socket.BaseSocket(
                s,
                constants.ACTIVE,
                self._application_context,
                self._bind_address,
                self._bind_port,
            )

            socks5_node = socks5_first_node.Socks5FirstNode(
                socket.socket(socket.AF_INET, socket.SOCK_STREAM),
                constants.ACTIVE,
                self._application_context,
                bind_address=self._bind_address,
                bind_port=self._bind_port,
                client_proxy=client_proxy,
                path=self._find_nodes(),
            )

            client_proxy.partner = socks5_node

            self._application_context["socket_data"][
                socks5_node.fileno()
            ] = socks5_node
        except Exception:
            logging.error(traceback.format_exc())
            if client_proxy:
                client_proxy.close()
            if socks5_node:
                socks5_node.close()

    def _find_nodes(self):
        path = {}

        counter = 1

        available_nodes = []
        for name in self._application_context["registry"]:
            if self._application_context["registry"][name]["name"] != self._name:
                available_nodes.append(self._application_context["registry"][name])
            else:
                path[str(counter)] = self._application_context["registry"][name]
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

        for node in chosen_nodes:
            path[str(counter)] = node
            counter += 1

        return path
       
    def close_handler(self):
        self.state = constants.CLOSING
        
    @property
    def registry_socket(self):
        return self._registry_socket
        
    @registry_socket.setter
    def registry_socket(self, sock):
        self._registry_socket = sock
        
    def close(self):
        """close() -> close the socket."""

        self._socket.close()
        
    @property
    def key(self):
        return self._key
        
    @property
    def address(self):
        return self._bind_address
        
    @property
    def port(self):
        return self._bind_port
        
    @property
    def name(self):
        return self._name
        
    @property
    def state(self):
        return self._state

    @state.setter
    def state(self, state):
        self._state = state
        if self._state == constants.CLOSING:
            self._registry_socket.unregister()
