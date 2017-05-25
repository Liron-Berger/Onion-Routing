#!/usr/bin/python
## @package onion_routing.common.utilities.util
# General utilities for the project.
#

import errno
import os
import signal
import socket

from common import constants


## Error used for handling disconnecting sockets.
class DisconnectError(RuntimeError):
    def __init__(self):
        super(DisconnectError, self).__init__("Socket Disconnected")


## Recieve message from socket.
# @param sock (socket) the socket to recieve data from.
# @param max_buffer_size (int) max size of bytes to read.
# @returns (str) recieved data.
#
# Reads as much as possible from socket until maximum size is reached.
#
def recieve_buffer(
    sock,
    max_buffer_size,
):
    buffer = ""
    try:
        while len(buffer) < max_buffer_size:
            data = sock.recv(
                max_buffer_size,
            )
            if not data:
                raise DisconnectError()
            buffer += data
    except socket.error as e:
        if e.errno not in (errno.EAGAIN, errno.EWOULDBLOCK):
            raise
    return buffer


## Sending message to socket.
# @param sock (socket) the socket to send data to.
# @param buffer (str) buffer to send.
# @returns (str) the remaining buffer.
#
# Sends to socket as much as possible.
#
def send_buffer(
    sock,
    buffer,
):
    try:
        while buffer:
            buffer = buffer[
                sock.send(
                    buffer
                ):
            ]
    except socket.error as e:
        if e.errno != errno.EPIPE:
            raise
        return ""
    return buffer


## Reading data from file.
# @param fd (int) file descriptor of file.
# @param max_buffer_size (int) max size of bytes to read.
# @returns (str) content of file.
#
def read_file(
    fd,
    max_buffer_size=constants.DEFAULT_BUFFER_SIZE,
):
    buffer = ""
    while True:
        data = os.read(fd, max_buffer_size)
        if not data:
            return buffer
        buffer += data


## Write data to file.
# @param fd (int) file descriptor of file.
# @param buffer (str) buffer to write.
#
def write_file(
    fd,
    buffer,
):
    while buffer:
        buffer = buffer[
            os.write(
                fd,
                buffer,
            ):
        ]


## Connect to socket asynchronously.
def connect(
    sock,
    address,
    port,
):
    try:
        sock.connect(
            (
                address,
                port,
            )
        )
    except socket.error as e:
        if e.errno not in (errno.EINPROGRESS, errno.EWOULDBLOCK):
            raise


## Damonize process.
#
# 1. Forking process and closing parent.
# 2. In child closing all inherited opened file descriptors with resource lib.
# 3. Redirect standard input, standard output and standard error to /dev/null.
# 4. Change working directory to /.
# 5. Fork and exit parent to move child as child of init.
#
def daemonize():
    if os.name == "nt":
        raise RuntimeError("Daemon not available on Windows...")

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
