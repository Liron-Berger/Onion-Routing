#!/usr/bin/python
## @package onion_routing.common.pollables.pollable
# Base class for all objects used for the poller.
## @file pollable.py
# Implementation of @ref onion_routing.common.pollables.pollable
#


## Pollable is an interface for async sockets async proxy can use.
# each method must be overriden in inheriting objects.
#
class Pollable(object):

    ## On read event.
    def on_read(self):
        pass

    ## On write event.
    def on_write(self):
        pass

    ## On close event.
    def on_close(self):
        pass

    ## Is closing. Whether the socket is ready for closing.
    def is_closing(self):
        return False

    ## Close the Pollable.
    def close(self):
        pass

    ## Get events for poller.
    def get_events(self):
        pass

    ## fileno of Pollable.
    def fileno(self):
        pass
