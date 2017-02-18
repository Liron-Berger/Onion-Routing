#!/usr/bin/python

import logging
import traceback

from base_socket import BaseSocket
from common import constants


class Listener(BaseSocket):
    NAME = "Listener"

    def __init__(
        self,
        socket,
        bind_address,
        bind_port,
        max_conn,
        socket_data,
        server_type,
        application_context,
    ):
        super(Listener, self).__init__(
            socket,
            socket_data,
            application_context,
        )

        self._socket.bind((bind_address, bind_port))
        self._socket.listen(max_conn)
        self._server_type = server_type

    def read(self):
        try:
            server = None

            s, addr = self._socket.accept()

            server = self._server_type(
                s,
                self._socket_data,
                self._application_context,
            )

            self._socket_data[
                server.socket.fileno()
            ] = {
                "async_socket": server,
                "state": constants.PROXY_ACTIVE,
            }
        except Exception:
            logging.error(traceback.format_exc())
            if server:
                server.socket.close()
