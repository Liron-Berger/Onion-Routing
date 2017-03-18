#!/usr/bin/python

import errno
import os
import signal


def daemonize(
    log_fd,
):
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


class DisconnectError(RuntimeError):
    def __init__(self):
        super(DisconnectError, self).__init__("Socket Disconnected")


class Socks5Error(RuntimeError):
    def __init__(self):
        super(Socks5Error, self).__init__("Socks5 Protocol Error")

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
