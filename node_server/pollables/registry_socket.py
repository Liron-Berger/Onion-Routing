#!/usr/bin/python

import errno
import socket

from common import constants
from common.async import event_object
from common.pollables import base_socket
from common.utilities import util


class RegistrySocket(base_socket.BaseSocket):

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
        socket,
        state,
        app_context,
        connect_address,
        connect_port,
        node,
        node_address,
        node_port,
    ):
        super(RegistrySocket, self).__init__(
            socket,
            state,
            app_context,
        )
        
        self._connect_to_registry(
            connect_address,
            connect_port,
        )
        
        self._state_machine = self._create_state_machine() 
        self._machine_state = constants.SEND_REGISTER
        self._node = node
        self._node_address = node_address
        self._node_port = node_port
        
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
            self._node_port,
            self._node_address,
            self._node_port,
            self._node.key,
        )
        super(RegistrySocket, self).on_write()
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
        super(RegistrySocket, self).on_write()
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

    def on_read(self):
        self._buffer += util.recieve_buffer(
            self._socket,
            self._app_context["max_buffer_size"] - len(self._buffer),
        )
        if self._machine_state in (
            constants.RECV_REGISTER,
            constants.RECV_UNREGISTER,
        ):
            if self._state_machine[self._machine_state]["method"]():
                self._machine_state = self._state_machine[
                    self._machine_state
                ]["next"]
            
    def on_write(self):
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
        
    def get_events(self):
        event = event_object.BaseEvent.POLLERR
        if self._machine_state in (
            constants.RECV_REGISTER,
            constants.RECV_UNREGISTER,
        ):
            event |= event_object.BaseEvent.POLLIN
        if self._machine_state in (
            constants.SEND_REGISTER,
            constants.SEND_UNREGISTER,        
        ):
            event |= event_object.BaseEvent.POLLOUT
        return event

    # def __repr__(self):
        # return "RegistrySocket object. address %s, port %s. fd: %s" % (
            # self._bind_address,
            # self._bind_port,
            # self.fileno(),
        # )

        