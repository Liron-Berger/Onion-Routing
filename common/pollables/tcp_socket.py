#!/usr/bin/python
## @package onion_routing.common.pollables.tcp_socket
# Base class for all sockets used for sending and reciving data.
#

from common import constants
from common.utilities import util
from common.pollables import pollable
from common.async import event_object


## Basic implementation of asynchronous TCP socket.
# Used by async_server to read and write data from client.
# Can be used as a proxy between two ends.
#
class TCPSocket(pollable.Pollable):

    # Request context.
    _request_context = {}

    ## Constructor.
    # @param socket (socket) the wrapped socket.
    # @param state (int) state of TCPSocket.
    # @param app_context (dict) application context.
    #
    # Creates a wrapper for the given @ref _socket to be able to
    # read and write from it asynchronously.
    #
    def __init__(
        self,
        socket,
        state,
        app_context,
    ):
        ## Socket used by the Listener.
        self._socket = socket
        self._socket.setblocking(False)

        ## State of TCPSocket.
        self._state = state

        ## Buffer in which messages for reading/writing are stored.
        self._buffer = ""

        ## Partner of socket.
        # Initialized as self to read and write to client.
        # If changed TCPSocket will act as proxy between client and partner.
        #
        self._partner = self

        self._request_context["app_context"] = app_context

    ## On read event.
    # Read from @ref _partner until maximum size of @ref _buffer is recived.
    #
    def on_read(self):
        self._partner.buffer += util.recieve_buffer(
            self._socket,
            self._request_context["app_context"]["max_buffer_size"] - len(self._partner.buffer),
        )

    ## On write event.
    # Write everything stored and @ref _buffer.
    #
    def on_write(self):
        self._buffer = util.send_buffer(
            self._socket,
            self._buffer,
        )

    ## On close event.
    # Change @ref _state of socket to CLOSING and empty @ref _buffer.
    # If TCPSocket is proxy run on_close on @ref _partner.
    #
    def on_close(self):
        self._state = constants.CLOSING
        self._buffer = ""

        if (
            self != self._partner and
            not self._partner.state == constants.CLOSING
        ):
            self._partner.on_close()

    ## Is closing.
    # @returns (bool) True if ready for closing.
    #
    # Socket is ready for closing when @ref _state is CLOSING and
    # @ref _buffer is empty.
    #
    def is_closing(self):
        return self._state == constants.CLOSING and not self._buffer

    ## Close TCPSocket.
    # Closing @ref _socket.
    #
    def close(self):
        self._socket.close()

    ## Get events for poller.
    # @retuns (int) events to register for poller.
    #
    # - POLLIN when @ref _state is ACTIVE and @ref _buffer is not full.
    # - POLLOUT when @ref _buffer is not empty.
    #
    def get_events(self):
        event = event_object.BaseEvent.POLLERR
        if (
            self._state == constants.ACTIVE and
            not len(self._buffer) >= self._request_context["app_context"]["max_buffer_size"]
        ):
            event |= event_object.BaseEvent.POLLIN
        if self._buffer:
            event |= event_object.BaseEvent.POLLOUT
        return event

    ## fileno of TCPSocket.
    def fileno(self):
        return self._socket.fileno()

    ## Retrive @ref _socket.
    @property
    def socket(self):
        return self._socket

    ## Set @ref _socket.
    @socket.setter
    def socket(self, socket):
        self._socket = socket

    ## Retrive @ref _state.
    @property
    def state(self):
        return self._state

    ## Set @ref _state.
    @state.setter
    def state(self, state):
        self._state = state

    ## Retrive @ref _buffer.
    @property
    def buffer(self):
        return self._buffer

    ## Set @ref _buffer.
    @buffer.setter
    def buffer(self, buffer):
        self._buffer = buffer

    ## Retrive @ref _partner.
    @property
    def partner(self):
        return self._partner

    ## Set @ref _partner.
    @partner.setter
    def partner(self, partner):
        self._partner = partner

    ## String representation.
    def __repr__(self):
        return "TCPSocket object. fileno: %d." % (
            self.fileno(),
        )
