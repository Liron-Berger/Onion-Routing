#!/usr/bin/python

import constants
import errno
import os
import signal


def daemonize(log_fd):
    child = os.fork()
    if child != 0:
        os._exit(0)

    import resource

    for i in range(3, resource.getrlimit(resource.RLIMIT_NOFILE)[1]):
        if i != log_fd:
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


def write_to_fd(
    fd,
    msg,
):
    while msg:
        msg = msg[os.write(fd, msg):]


def validate_ip(ip):
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


def recv_line(
    buf,
    max_length=constants.MAX_HEADER_LENGTH,
    block_size=constants.BLOCK_SIZE,
):
    while True:
        if len(buf) > max_length:
            raise RuntimeError('Exceeded maximum line length %s' % max_length)

        n = buf.find(constants.CRLF_BIN)
        if n != -1:
            break

    return buf[:n].decode('utf-8'), buf[n + len(constants.CRLF_BIN):]

def text_to_html(
    text,
):
    return ("<HTML>\r\n<BODY>\r\n%s\r\n</BODY>\r\n</HTML>" % text).decode('utf-8')
