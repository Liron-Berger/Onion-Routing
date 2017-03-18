#!/usr/bin/python

class Pollable(object):
    """Pollable is an interface for async sockets async proxy can use.

    each method must be overriden in inheriting objects.
    """

    def read(self):
        pass

    def write(self):
        pass

    def event(self):
        pass

    def fileno(self):
        pass

    def close(self):
        pass

    def remove(self):
        pass