#!/usr/bin/python
## @package onion_routing.onion.pollables.onion_node
# Regular nodes used for anonymizing communications.
## @file onion_node.py
# Implementation of @ref onion_routing.onion.pollables.onion_node
#

import logging
import random
import socket
import traceback

from common import constants
from common.pollables import listener_socket
from common.pollables import http_client
from onion.pollables import socks5_server


## Server Node.
# Nodes responsibly is for opening new connections whenever a connections
# is recieved.
# Each node has a secret key used for encypting all communication.
#
class OnionNode(listener_socket.Listener):

    ## Constructor.
    # @param bind_address (str) bind address of the node.
    # @param bind_port (int) bind port of the node.
    # @param app_context (dict) application context.
    # @param listener_type (optional, @ref common.pollables.tcp_socket) not used.
    #
    def __init__(
        self,
        bind_address,
        bind_port,
        app_context,
        listener_type=socks5_server.Socks5Server,
    ):
        super(OnionNode, self).__init__(
            bind_address,
            bind_port,
            app_context,
            socks5_server.Socks5Server,
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

    ## On read event.
    # Accept new connection.
    # Create a new @ref onion.pollables.socks5_server with
    # the secret key of this node.
    # Add socket to socket_data of @ref common.async.async_server.
    #
    def on_read(self):
        try:
            server = None

            s, addr = self._socket.accept()

            server = self._type(
                s,
                constants.ACTIVE,
                self._app_context,
                self._key,
            )

            self._app_context["socket_data"][
                server.fileno()
            ] = server

        except Exception:
            logging.error(traceback.format_exc())
            if server:
                server.close()

    ## Close Node.
    # Closing @ref common.pollables.listener_socket.Listener._socket.
    # Entering unregister state in @ref http_client.
    #
    def close(self):
        self._socket.close()
        self.http_client.unregister()

    ## Retrive @ref _key.
    @property
    def key(self):
        return self._key

    ## String representation.
    def __repr__(self):
        return "OnionNode object. address %s, port %s. fd: %s" % (
            self.bind_address,
            self.bind_port,
            self.fileno(),
        )
