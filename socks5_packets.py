#!/usr/bin/python

import constants
import util

from errors import ProtocolError
from errors import NotEnoughArguments


class Packet(object):

    @staticmethod
    def encode(self, properties):
        pass

    @staticmethod
    def decode(self, data):
        pass


class GreetingRequest(Packet):
    '''
                   +----+----------+----------+
                   |VER | NMETHODS | METHODS  |
                   +----+----------+----------+
                   | 1  |    1     | 1 to 255 |
                   +----+----------+----------+
    '''

    @staticmethod
    def decode(data):
        try:
            version = ord(data[0])
            number_methods = ord(data[1])
            methods = [ord(i) for i in data[2:2+number_methods]]
        except IndexError:
            raise NotEnoughArguments()
        if version != constants.VERSION:
            raise NotImplementedError("socks %s not supported" % version)
        if number_methods < 1 or number_methods > 255:
            raise ProtocolError()

        return {
            "version": version,
            "number_methods": number_methods,
            "methods": methods,
        }


class GreetingResponse(Packet):
    '''
                        +----+--------+
                        |VER | METHOD |
                        +----+--------+
                        | 1  |   1    |
                        +----+--------+
    '''

    @staticmethod
    def encode(properties):
        try:
            response = "%s%s" % (
                chr(properties["version"]),
                chr(properties["method"]),
            )
        except Exception:
            raise ProtocolError()
        return response


class Socks5Request(Packet):
    '''
        +----+-----+-------+------+----------+----------+
        |VER | CMD |  RSV  | ATYP | DST.ADDR | DST.PORT |
        +----+-----+-------+------+----------+----------+
        | 1  |  1  | X'00' |  1   | Variable |    2     |
        +----+-----+-------+------+----------+----------+
    '''

    @staticmethod
    def decode(data):
        try:
            request = {
                "version":              ord(data[0]),
                "command":              ord(data[1]),
                "reserved":             ord(data[2]),
                "address_type":         ord(data[3]),
                "dst_address":          '.'.join(
                                            str(i) for i in map(
                                                ord, data[4:len(data)-2]
                                            )
                                        ),
                "dst_port":             256*ord(data[-2]) + ord(data[-1]),
            }
        except IndexError:
            raise NotEnoughArguments()

        if (
            request["version"] != constants.VERSION or
            request["command"] not in constants.SUPPORTED_COMMANDS or
            request["address_type"] not in constants.SUPPORTED_ADDRESS_TYPE
        ):
            raise NotImplementedError()
        if (
            request["reserved"] != 0 or
            not util.validate_ip(request["dst_address"])
        ):
            raise ProtocolError()

        return request


class Socks5Response(Packet):
    '''
        +----+-----+-------+------+----------+----------+
        |VER | REP |  RSV  | ATYP | BND.ADDR | BND.PORT |
        +----+-----+-------+------+----------+----------+
        | 1  |  1  | X'00' |  1   | Variable |    2     |
        +----+-----+-------+------+----------+----------+
    '''

    @staticmethod
    def encode(properties):
        if properties["version"] != constants.VERSION:
            raise ProtocolError()

        try:
            response = "%s%s%s%s%s%s" % (
                chr(properties["version"]),
                chr(properties["reply"]),
                chr(properties["reserved"]),
                chr(properties["address_type"]),
                ''.join(
                    chr(int(x))
                    for x in properties["dst_address"].split('.')
                ),
                (
                    chr(properties["dst_port"] / 256) +
                    chr(properties["dst_port"] % 256)
                ),
            )
        except Exception:
            raise
        return response
