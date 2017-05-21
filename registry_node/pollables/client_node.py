#!/usr/bin/python

import logging
import random
import socket
import traceback

from common import constants
from common.pollables import base_socket
from common.pollables import listener_socket
from registry_node.pollables import socks5_client


class Node(listener_socket.Listener):

    def __init__(
        self,
        bind_address,
        bind_port,
        app_context,
        listener_type=None,
    ):
        super(Node, self).__init__(
            bind_address,
            bind_port,
            app_context,
            listener_type,
        )

        self._name = str(bind_port)
        self._key = random.randint(0, 256)

        self._app_context["registry"][bind_port] = {
            "name": str(bind_port),
            "address": bind_address,
            "port": bind_port,
            "key": self._key,
        }

    def on_read(self):
        try:
            client_proxy = None
            socks5_node = None

            client, addr = self._socket.accept()

            client_proxy = base_socket.BaseSocket(
                socket=client,
                state=constants.ACTIVE,
                app_context=self._app_context,
            )

            socks5_node = socks5_client.Socks5Client(
                socket=socket.socket(socket.AF_INET, socket.SOCK_STREAM),
                state=constants.ACTIVE,
                app_context=self._app_context,
                client_proxy=client_proxy,
                path=self._find_nodes(),
            )

            client_proxy.partner = socks5_node

            self._app_context["socket_data"][
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
        for name in self._app_context["registry"]:
            if self._app_context["registry"][name]["name"] != self._name:
                available_nodes.append(self._app_context["registry"][name])
            else:
                path[str(counter)] = self._app_context["registry"][name]
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
        
    @property
    def key(self):
        return self._key

    def __repr__(self):
        return "Node object. address %s, port %s"
