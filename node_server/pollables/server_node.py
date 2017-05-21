#!/usr/bin/python

import logging
import random
import socket
import traceback

from common import constants
from common.pollables import base_socket
from common.pollables import listener_socket
from node_server.pollables import registry_socket
from node_server.pollables import socks5_server


class ServerNode(listener_socket.Listener):

    def __init__(
        self,
        bind_address,
        bind_port,
        app_context,
        listener_type=None,
    ):
        super(ServerNode, self).__init__(
            bind_address,
            bind_port,
            app_context,
        )

        self._key = random.randint(0, 256)
        self.registry_socket = registry_socket.RegistrySocket(
            socket=socket.socket(socket.AF_INET, socket.SOCK_STREAM),
            state=constants.ACTIVE,
            app_context=app_context,
            connect_address=app_context["http_address"],
            connect_port=app_context["http_port"],
            node=self,
            node_address=bind_address,
            node_port=bind_port,
        )

    def on_read(self):
        try:
            server = None

            s, addr = self._socket.accept()

            server = socks5_server.Socks5Server(
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
        
    @property
    def key(self):
        return self._key

    # def __repr__(self):
        # return "Node object. address %s, port %s" % (
            # self._bind_address,
            # self._bind_port,
        # )
