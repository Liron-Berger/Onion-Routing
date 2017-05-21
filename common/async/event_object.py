#!/usr/bin/python
## @package onion_routing.common.async.event_object
# Event objects for asynchronous I/O.
#

import os
import select


## Base Event.
#
# Abstruct class for events.
#
class BaseEvent(object):
    ## Events for all operating systems.
    POLLIN, POLLOUT, POLLERR, POLLHUP = (
        1, 4, 8, 16,
    ) if os.name == "nt" else (
        select.POLLIN, select.POLLOUT, select.POLLERR, select.POLLHUP,
    )

    ## Name of event.
    NAME = "base"

    ## Constructor.
    def __init__(self):
        pass

    ## Register new socket.
    # @param fd (int) socket file descriptor.
    # @param event (int) event.
    #
    def register(self, fd, event):
        raise NotImplementedError()

    ## Poll for events.
    # @param timeout (int) poll timeout.
    #
    def poll(self, timeout):
        raise NotImplementedError()


if os.name != "nt":
    ## Poll Event.
    #
    # Poll event created only on linux machines.
    #
    class PollEvent(BaseEvent):
        ## Name of event.
        NAME = "Poll"

        ## Constructor.
        def __init__(self):
            super(PollEvent, self).__init__()
            self._poller = select.poll()

        ## Register new socket.
        # @param fd (int) socket file descriptor.
        # @param event (int) event.
        #
        def register(self, fd, event):
            self._poller.register(fd, event)

        ## Poll for events.
        # @param timeout (int) poll timeout.
        # @returns poll dict (dict) poll dict.
        #
        def poll(self, timeout):
            return self._poller.poll(timeout)


## Select Event.
#
# Select event.
# Wrapping select so it behaves like poll object.
#
class SelectEvent(BaseEvent):
    ## Name of event.
    NAME = "Select"

    ## Constructor.
    def __init__(self):
        super(SelectEvent, self).__init__()
        self._fd_dict = {}

    ## Register new socket.
    # @param fd (int) socket file descriptor.
    # @param event (int) event.
    #
    def register(self, fd, event):
        self._fd_dict[fd] = event

    ## Poll for events.
    # @param timeout (int) poll timeout.
    # @returns poll dict (dict) poll dict.
    #
    # Using select lists to identify different events, and builds
    # a copy of poll dict.
    #
    def poll(self, timeout):
        rlist, wlist, xlist = [], [], []

        for fd in self._fd_dict:
            if self._fd_dict[fd] & SelectEvent.POLLERR:
                xlist.append(fd)
            if self._fd_dict[fd] & SelectEvent.POLLIN:
                rlist.append(fd)
            if self._fd_dict[fd] & SelectEvent.POLLOUT:
                wlist.append(fd)

        r, w, x = select.select(rlist, wlist, xlist, timeout)

        poll_dict = {}
        for s in r + w + x:
            if s in r:
                poll_dict[s.fileno()] = SelectEvent.POLLIN
            if s in w:
                poll_dict[s.fileno()] = SelectEvent.POLLOUT
            if s in x:
                poll_dict[s.fileno()] = SelectEvent.POLLERR
        return poll_dict.items()
