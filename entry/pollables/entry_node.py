#!/usr/bin/python
## @package onion_routing.entry.pollables.entry_node
# Entry node which is used as the first node to which browser connects.
## @file entry_node.py
# Implementation of @ref onion_routing.entry.pollables.entry_node
#

import logging
import random
import socket
import traceback

from common import constants
from common.pollables import proxy_socket
from common.pollables import listener_socket
from common.pollables import http_client
from entry.pollables import socks5_client


## Entry Node.
# Nodes responsibly is for opening new connections whenever a connections
# is recieved.
#
class EntryNode(listener_socket.Listener):

    ## Constructor.
    # @param bind_address (str) bind address of the node.
    # @param bind_port (int) bind port of the node.
    # @param app_context (dict) application context.
    # @param listener_type (optional,
    # @ref onion_routing.common.pollables.tcp_socket) not used.
    #
    # Gets Nodes from the Regsitry.
    #
    def __init__(
        self,
        bind_address,
        bind_port,
        app_context,
        listener_type=None,
    ):
        super(EntryNode, self).__init__(
            bind_address,
            bind_port,
            app_context,
            listener_type,
        )

        ## Bind address of node.
        self.bind_address = bind_address

        ## Bind port of node.
        self.bind_port = bind_port

        ## Secret key for encryption.
        self._key = random.randint(0, 255)

        ## http client, for registering and unregistring to the registry.
        self.http_client = http_client.HttpClient(
            socket=socket.socket(socket.AF_INET, socket.SOCK_STREAM),
            state=constants.ACTIVE,
            app_context=app_context,
            connect_address=app_context["http_address"],
            connect_port=app_context["http_port"],
            node=self,
        )
        self.http_client.get_nodes()

    ## On read event.
    # - Gets connected nodes from registry.
    # - Accept new connection.
    # - Create new @ref common.pollables.proxy_socket from the accepted socket
    # as browser socket.
    # - Create new @ref entry.pollables.socks5_client for establishing
    # socks5 with other nodes as socks5_c.
    # - Get Nodes from registry and choose a random path for anonymization.
    # - Set browser_socket partner to socks5_c.
    # - Add socks5_c to @ref common.async.async_server.AsyncServer._socket_data.
    #
    def on_read(self):
        self.http_client.get_nodes()
        try:
            browser_socket = None
            socks5_c = None

            client, addr = self._socket.accept()

            browser_socket = proxy_socket.ProxySocket(
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
    # nodes. In that case some nodes might repeat, or if there are no nodes
    # an error is raised.
    #
    def _create_path(self):
        available_nodes = []
        for name in self._app_context["registry"]:
            if self._app_context[
                "registry"
            ][name]["name"] != str(self.bind_port):
                available_nodes.append(self._app_context["registry"][name])

        if not available_nodes:
            raise RuntimeError(
                "Not Enough nodes registered, at least one more is required",
            )

        if len(available_nodes) >= constants.OPTIMAL_NODES_IN_PATH:
            chosen_nodes = random.sample(
                available_nodes,
                constants.OPTIMAL_NODES_IN_PATH,
            )

        else:
            chosen_nodes = random.sample(
                available_nodes,
                len(available_nodes),
            )

            while len(chosen_nodes) < constants.OPTIMAL_NODES_IN_PATH:
                chosen_nodes += random.sample(
                    available_nodes,
                    min(
                        len(available_nodes),
                        constants.OPTIMAL_NODES_IN_PATH - len(chosen_nodes),
                    ),
                )

        path = {}
        for i in range(len(chosen_nodes)):
            path[str(i + 1)] = chosen_nodes[i]
            
        for x in path.values():
            x["address"] = socket.gethostbyname(x["address"])
        return path

    ## Close Node.
    # Closing @ref onion_routing.
    # common.pollables.listener_socket.Listener._socket.
    # Entering unregister state in @ref http_client.
    #
    def close(self):
        self._socket.close()
        self.http_client._machine_state = constants.UNREGISTERED

    ## Retrive @ref _key.
    @property
    def key(self):
        return self._key

    ## String representation.
    def __repr__(self):
        return "EntryNode object. address %s, port %s. fd: %s" % (
            self.bind_address,
            self.bind_port,
            self.fileno(),
        )
