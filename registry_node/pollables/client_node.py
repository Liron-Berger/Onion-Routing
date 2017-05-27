#!/usr/bin/python
## @package onion_routing.registry_node.pollables.client_node
# Client node which is used as the first node to which browser connects.
#

import logging
import random
import socket
import traceback

from common import constants
from common.pollables import tcp_socket
from common.pollables import listener_socket
from registry_node.pollables import socks5_client


## Client Node.
# Nodes responsibly is for opening new connections whenever a connections
# is recieved.
#
class ClientNode(listener_socket.Listener):

    ## Constructor.
    # @param bind_address (str) bind address of the node.
    # @param bind_port (int) bind port of the node.
    # @param app_context (dict) application context.
    # @listener_type (optional, @ref common.pollables.tcp_socket) not used.
    #
    # Adds itself to the registry menually (the only node to do so).
    #
    def __init__(
        self,
        bind_address,
        bind_port,
        app_context,
        listener_type=None,
    ):
        super(ClientNode, self).__init__(
            bind_address,
            bind_port,
            app_context,
            listener_type,
        )

    ## On read event.
    # - Accept new connection.
    # - Create new @ref common.pollables.tcp_socket from the accepted socket
    # as browser socket.
    # - Create new @ref registry_node.pollables.socks5_client for establishing
    # socks5 with other nodes as socks5_c.
    # - Get Nodes from registry and choose a random path for anonymization.
    # - Set browser_socket partner to socks5_c.
    # - Add socks5_c to @ref common.async.async_server._socket_data.
    #
    def on_read(self):
        try:
            browser_socket = None
            socks5_c = None

            client, addr = self._socket.accept()

            browser_socket = tcp_socket.TCPSocket(
                socket=client,
                state=constants.ACTIVE,
                app_context=self._app_context,
            )

            socks5_c = socks5_client.Socks5Client(
                socket=socket.socket(socket.AF_INET, socket.SOCK_STREAM),
                state=constants.ACTIVE,
                app_context=self._app_context,
                browser_socket=browser_socket,
                path=self._create_path(),
            )

            browser_socket.partner = socks5_c

            self._app_context["socket_data"][
                socks5_c.fileno()
            ] = socks5_c
        except Exception:
            logging.error(traceback.format_exc())
            if browser_socket:
                browser_socket.close()
            if socks5_c:
                socks5_c.close()

    ## Create path.
    # @returns (dict) Three random nodes from registry.
    # Chooses three random nodes from registry unless there aren't enough
    # nodes. In that case some nodes might repeat, or if there are nodes
    # an error is raised.
    #
    def _create_path(self):
        if not self._app_context["registry"]:
            raise RuntimeError(
                "Not Enough nodes registered, at least one is required",
            )

        chosen_nodes = random.sample(
            self._app_context["registry"].values(),
            min(
                len(self._app_context["registry"]),
                constants.OPTIMAL_NODES_IN_PATH,
            ),
        )

        while len(chosen_nodes) < constants.OPTIMAL_NODES_IN_PATH:
            chosen_nodes += random.sample(
                self._app_context["registry"].values(),
                min(
                    len(self._app_context["registry"]),
                    constants.OPTIMAL_NODES_IN_PATH - len(chosen_nodes),
                ),
            )

        path = {}
        for i in range(len(chosen_nodes)):
            path[str(i + 1)] = chosen_nodes[i]

        return path

    ## Retrive @ref _key.
    @property
    def key(self):
        return self._key

    ## String representation.
    def __repr__(self):
        return "ServerNode object. fd: %s" % (
            self.fileno(),
        )
