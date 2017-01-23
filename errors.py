#!/usr/bin/python


class DisconnectError(RuntimeError):

    def __init__(self):
        super(DisconnectError, self).__init__("Socket Disconnected")


class ProtocolError(RuntimeError):

    def __init__(self):
        super(ProtocolError, self).__init__("protocol error")


class NotEnoughArguments(RuntimeError):

    def __init__(self):
        super(NotEnoughArguments, self).__init__("not enough arguments")
