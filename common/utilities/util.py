#!/usr/bin/python

import errno
import os
import signal
import socket
import time

from common import constants


def daemonize():
    child = os.fork()
    if child != 0:
        os._exit(0)

    import resource

    for i in range(3, resource.getrlimit(resource.RLIMIT_NOFILE)[1]):
        try:
            os.close(i)
        except OSError as e:
            if e.errno != errno.EBADF:
                raise

    signal.signal(signal.SIGHUP, signal.SIG_IGN)

    fd = os.open(os.devnull, os.O_RDWR, 0o666)
    for i in range(3):
        os.dup2(i, fd)
    os.close(fd)
    os.chdir('/')
    child = os.fork()
    if child != 0:
        os._exit(0)


def validate_ip(
    ip,
):
    a = ip.split('.')
    if len(a) != 4:
        return False
    for x in a:
        if not x.isdigit():
            return False
        i = int(x)
        if i < 0 or i > 255:
            return False
    return True


def text_to_html(
    text,
):
    return (
        "<HTML>\r\n<BODY>\r\n%s\r\n</BODY>\r\n</HTML>" % text
    ).decode('utf-8')


def create_table_from_sublists(
    table_data,
    title,
):
    table = ""
    table += '''<table border="1" width="100%">'''
    table += "<tr><th>%s</th></tr>" % title
    for row in table_data:
        table += "<tr>"
        for cell in row:
           table += "<td>%s</td>" % cell
        table += "</tr>"
    table += "</table>"
    return table


def registry_by_name(
    parent_cls,
):
    return {
        cls.NAME: cls for cls in parent_cls.__subclasses__()
    }


def encrypt_decrypt_key_xor(
    data,
    key,
):
    return "".join(chr(ord(a)^key) for a in data)
    
    
def read_file(
    fd,
    max_buffer_size=constants.DEFAULT_BUFFER_SIZE,
):
    file = ""
    while True:
        data = os.read(fd, max_buffer_size)
        if not data:
            return file
        file += data
    

class DisconnectError(RuntimeError):
    def __init__(self):
        super(DisconnectError, self).__init__("Socket Disconnected")

class HTTPError(RuntimeError):
    def __init__(
        self,
        code,
        status,
        message="",
    ):
        super(HTTPError, self).__init__(message)
        self.code = code
        self.status = status
        self.message = message
        

def recieve_buffer(
    s,
    free_buffer_size,
):
    buffer = ""
    try:
        while len(buffer) < free_buffer_size:
            data = s.recv(
                free_buffer_size,
            )
            if not data:
                raise DisconnectError()
            buffer += data
    except socket.error as e:
        if e.errno not in (errno.EAGAIN, errno.EWOULDBLOCK):
            raise
    return buffer

def send_buffer(
    s,
    buffer,
):
    try:
        while buffer:
            buffer = buffer[
                s.send(
                    buffer
                ):
            ]
    except socket.error as e:
        if e.errno != errno.EPIPE:
            raise
        return ""
    return buffer