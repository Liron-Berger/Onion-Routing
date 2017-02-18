#!/usr/bin/python

import os
import select


class BaseEvents(object):
    POLLIN, POLLOUT, POLLERR, POLLHUP = (
        1, 4, 8, 16,
    ) if os.name == "nt" else (
        select.POLLIN, select.POLLOUT, select.POLLERR, select.POLLHUP,
    )

    NAME = "base"

    def __init__(self):
        pass

    def register(self, fd, event):
        pass

    def poll(self, timeout):
        raise NotImplementedError()

    def supported(self):
        pass


if os.name != "nt":
    class PollEvents(BaseEvents):
        NAME = "Poll"

        def __init__(self):
            super(PollEvents, self).__init__()
            self._poller = select.poll()

        def register(self, fd, event):
            self._poller.register(fd, event)

        def poll(self, timeout):
            return self._poller.poll(timeout)


class SelectEvents(BaseEvents):
    NAME = "Select"

    def __init__(self):
        super(SelectEvents, self).__init__()
        self._fd_dict = {}

    def register(self, fd, event):
        self._fd_dict[fd] = event

    def poll(self, timeout):
        rlist, wlist, xlist = [], [], []

        for fd in self._fd_dict:
            if self._fd_dict[fd] & SelectEvents.POLLERR:
                xlist.append(fd)
            if self._fd_dict[fd] & SelectEvents.POLLIN:
                rlist.append(fd)
            if self._fd_dict[fd] & SelectEvents.POLLOUT:
                wlist.append(fd)

        r, w, x = select.select(rlist, wlist, xlist, timeout)

        poll_dict = {}
        for s in r + w + x:
            if s in r:
                poll_dict[s.fileno()] = SelectEvents.POLLIN
            if s in w:
                poll_dict[s.fileno()] = SelectEvents.POLLOUT
            if s in x:
                poll_dict[s.fileno()] = SelectEvents.POLLERR
        return poll_dict.items()
