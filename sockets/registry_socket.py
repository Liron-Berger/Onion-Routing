#!/usr/bin/python

from common.util import DisconnectError
from async import pollable
from async import events
from common import constants
from base_socket import BaseSocket

import errno
import socket


class RegistrySocket(BaseSocket):

    REGISTER_REQUEST = (
        'GET /register?name=%s&address=%s&port=%s&key=%s HTTP/1.1\r\n'
        'User-Agent: Mozilla/4.0 (compatible; MSIE5.01; Windows NT)\r\n'
        'Host: www.tutorialspoint.com\r\n'
        'Accept-Language: en-us\r\n'
        'Accept-Encoding: gzip, deflate\r\n'
        'Connection: Keep-Alive\r\n'
        '\r\n'
    )
    
    UNREGISTER_REQUEST = (
        'GET /register?name=%s&address=%s&port=%s&key=%s HTTP/1.1\r\n'
        'User-Agent: Mozilla/4.0 (compatible; MSIE5.01; Windows NT)\r\n'
        'Host: www.tutorialspoint.com\r\n'
        'Accept-Language: en-us\r\n'
        'Accept-Encoding: gzip, deflate\r\n'
        'Connection: Keep-Alive\r\n'
        '\r\n'
    )
    
    def __init__(
        self,
        sock,
        state,
        application_context,
        bind_address,
        bind_port,
        node,
    ):
        super(RegistrySocket, self).__init__(
            sock,
            state,
            application_context,
            bind_address,
            bind_port,
        )
        
        try:
            self._socket.connect(
                (
                    bind_address,
                    bind_port,
                )
            )
        except socket.error as e:
            if e.errno not in (errno.EINPROGRESS, errno.EWOULDBLOCK):
                raise

        self._buffer = RegistrySocket.REGISTER_REQUEST % (
            node.name,
            node.address,
            node.port,
            node.key,
        )
        
        self._node = node

    def __repr__(self):
        return "RegistrySocket object. address %s, port %s. fd: %s" % (
            self._bind_address,
            self._bind_port,
            self.fileno(),
        )
        
    def read(self):
        """read() -> reciving data from partner.

        recives data until disconnect or buffer is full.
        data is stored in the partner's buffer.
        """
        while not self._partner.full_buffer():
            data = self._socket.recv(
                self._max_buffer_size - len(self._partner.buffer),
            )
            if not data:
                raise DisconnectError()
            self._partner.buffer += data
            
            if "fail" in self._partner.buffer:
                self._node._state = constants.CLOSING
            self._partner.buffer = ""
                # self._partner.buffer = RegistrySocket.UNREGISTER_REQUEST % (
                    # self._node.name,
                    # self._node.address,
                    # self._node.port,
                    # self._node.key,
                # )
            

    def write(self):
        """write() -> sends the buffer to socket.

        sends until buffer is empty.
        if not the whole buffer was sent, buffer = the remaining message.
        """

        while self._buffer:
            self._buffer = self._buffer[
                self._socket.send(
                    self._buffer
                ):
            ]
        