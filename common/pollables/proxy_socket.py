#!/usr/bin/python
## @package onion_routing.common.pollables.proxy_socket
# Class for creating a proxy connection between two ends.
#

from common.pollables import tcp_socket


## Proxy Socket.
class ProxySocket(tcp_socket.TCPSocket):

    ## String representation.
    def __repr__(self):
        return "ProxySocket object. fileno: %d." % (
            self.fileno(),
        )
