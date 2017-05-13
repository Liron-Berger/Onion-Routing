#!/usr/bin/python

from common.util import DisconnectError
from async import pollable
from async import events
from common import constants
from common import util
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
        'GET /unregister?name=%s HTTP/1.1\r\n'
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
        address,
        port,
        node,
    ):
        super(RegistrySocket, self).__init__(
            sock,
            state,
            application_context,
            address,
            port,
        )
        
        self._connect_to_registry(
            address,
            port,
        )
        
        self._state_machine = self._create_state_machine() 
        self._machine_state = constants.SEND_REGISTER
        self._node = node       
        node.registry_socket = self
        
    def _create_state_machine(self):
        return {
            constants.SEND_REGISTER: {
                "method": self._send_register,
                "next": constants.RECV_REGISTER,
            },
            constants.RECV_REGISTER: {
                "method": self._recv_register,
                "next": constants.WAITING,
            },
            constants.SEND_UNREGISTER: {
                "method": self._send_unregister,
                "next": constants.RECV_UNREGISTER,
            },
            constants.RECV_UNREGISTER: {
                "method": self._recv_unregister,
                "next": constants.UNREGISTERED,
            },
            constants.WAITING: {
                "method": self._wait,
                "next": constants.WAITING,
            },
            constants.UNREGISTERED: {
                "method": self._wait,
                "next": constants.UNREGISTERED,
            },
        }
        
    def _send_register(self):
        self._buffer = RegistrySocket.REGISTER_REQUEST % (
            self._node.name,
            self._node.address,
            self._node.port,
            self._node.key,
        )
        super(RegistrySocket, self).write()
        return True
        
    def _recv_register(self):
        if "success" in self._buffer:
            return True
        elif "fail" in self._buffer:
            self._state = constants.CLOSING
            self._node.state = constants.CLOSING
        else:
            return False
            
    def _send_unregister(self):
        self._buffer = RegistrySocket.UNREGISTER_REQUEST % (
            self._node.name,
        )
        super(RegistrySocket, self).write()
        self._state = constants.CLOSING
        self._node.state = constants.CLOSING
        return True
        
    def _recv_unregister(self):
        self._state = constants.CLOSING
        self._node.state = constants.CLOSING
        return True
       
    def _wait(self):
        pass
        
    def _connect_to_registry(
        self,
        address,
        port,
    ):
        try:
            self._socket.connect(
                (
                    address,
                    port,
                )
            )
        except socket.error as e:
            if e.errno not in (errno.EINPROGRESS, errno.EWOULDBLOCK):
                raise

    def __repr__(self):
        return "RegistrySocket object. address %s, port %s. fd: %s" % (
            self._bind_address,
            self._bind_port,
            self.fileno(),
        )
        
    def read(self):
        data = ""
        try:
            while not self.full_buffer():
                data = self._socket.recv(
                    self._max_buffer_size - len(self._buffer),
                )
                if not data:
                    break
                self._buffer += data
        except socket.error as e:
            if e.errno != errno.EWOULDBLOCK:
                raise
        if not self._buffer:
            self._machine_state = constants.UNREGISTERED
            raise util.DisconnectError()
        if self._machine_state in (
            constants.RECV_REGISTER,
            constants.RECV_UNREGISTER,
        ):
            if self._state_machine[self._machine_state]["method"]():
                self._machine_state = self._state_machine[
                    self._machine_state
                ]["next"]
            
    def write(self):
        if self._machine_state in (
            constants.SEND_REGISTER,
            constants.SEND_UNREGISTER,
        ):
            if self._state_machine[self._machine_state]["method"]():
                self._machine_state = self._state_machine[
                    self._machine_state
                ]["next"]
            
    def unregister(self):
        self._machine_state = constants.SEND_UNREGISTER
        
    def event(self):
        event = events.BaseEvents.POLLERR
        if self._machine_state in (
            constants.RECV_REGISTER,
            constants.RECV_UNREGISTER,
        ):
            event |= events.BaseEvents.POLLIN
        if self._machine_state in (
            constants.SEND_REGISTER,
            constants.SEND_UNREGISTER,        
        ):
            event |= events.BaseEvents.POLLOUT
        return event
        
    def remove(self):
        return self._state == constants.CLOSING and not self._buffer

        