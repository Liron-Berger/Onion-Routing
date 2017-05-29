#!/usr/bin/python
## @package onion_routing.common.utilities.socks5_util
# utilities for handling socks5 protocol rfc 1928.
## @file socks5_util.py
# Implementation of @ref onion_routing.common.utilities.socks5_util
#

from common import constants


## Error used for handling errors in socks5 protocol.
class Socks5Error(RuntimeError):
    def __init__(self):
        super(Socks5Error, self).__init__("Socks5 Protocol Error")


## Base Socks5 Packet class.
class Socks5Packet(object):

    ## Encode packet message.
    # @param properties (dict) parameters for encoding message.
    #
    @staticmethod
    def encode(self, properties):
        pass

    ## Decode packet message.
    # @param data (str) encoded message.
    #
    @staticmethod
    def decode(self, data):
        pass


## Greeting Request Packet.
# @param version (int) socks version.
# @param number methods (int) number of methods.
# @param methods (list) available methods.
#
# | version | number methods | methods  |
# | :-----: | :------------: | :------: |
# | 1       | 1              | 1 to 255 |
#
class GreetingRequest(Socks5Packet):

    ## Encode packet message.
    # @param properties (dict) parameters for encoding message.
    # @returns (str) socks5 message.
    #
    @staticmethod
    def encode(properties):
        try:
            return "%s%s%s" % (
                chr(properties["version"]),
                chr(properties["number_methods"]),
                "".join(chr(m) for m in properties["methods"]),
            )
        except Exception:
            raise

    ## Decode packet message.
    # @param buffer (str) encoded message.
    # @returns (dict) decoded request.
    #
    @staticmethod
    def decode(buffer):
        if len(buffer) < 3:
            return
        data = [ord(a) for a in buffer]
        (
            version,
            number_methods,
            methods,
        ) = (
            data[0],
            data[1],
            data[2:],
        )

        if version == constants.SOCKS5_VERSION:
            if len(methods) < number_methods:
                return
            elif len(methods) > number_methods:
                raise Socks5Error()
            return {
                "version": version,
                "number_methods": number_methods,
                "methods": methods,
            }
        else:
            raise Socks5Error()

        # try:
            # version = ord(data[0])
            # number_methods = ord(data[1])
            # methods = [ord(i) for i in data[2:2 + number_methods]]
        # except IndexError:
            # raise Socks5Error()
        # if version != constants.VERSION:
            # raise NotImplementedError("socks %s not supported" % version)
        # if number_methods < 1 or number_methods > 255:
            # raise Socks5Error()

        # return {
            # "version": version,
            # "number_methods": number_methods,
            # "methods": methods,
        # }


## Greeting Response Packet.
# @param version (int) socks version.
# @param method (int) chosen method by server.
#
# | version | method |
# | :-----: | :----: |
# | 1       | 1      |
#
class GreetingResponse(Socks5Packet):

    ## Encode packet message.
    # @param properties (dict) parameters for encoding message.
    # @returns (str) socks5 message.
    #
    @staticmethod
    def encode(properties):
        try:
            response = "%s%s" % (
                chr(properties["version"]),
                chr(properties["method"]),
            )
        except Exception:
            raise Socks5Error()
        return response

    ## Decode packet message.
    # @param data (str) encoded message.
    # @returns (dict) decoded response.
    #
    @staticmethod
    def decode(data):
        try:
            return {
                "version": ord(data[0]),
                "method": ord(data[1]),
            }
        except Exception:
            raise


## Socks5 Request Packet.
# @param version (int) socks version.
# @param command (int) request command by client.
# @param reserved (int) reserved is 0.
# @param address type (int) address type requested.
# @param destination address (bytes) address.
# @param destination port (bytes) port.
#
# | version | command | reserved | address type | dst address | dst port |
# | :-----: | :-----: | :------: | :----------: | :---------: | :------: |
# | 1       | 1       | "0x00"   | 1            | veriable    | 2        |
#
class Socks5Request(Socks5Packet):

    ## Encode packet message.
    # @param properties (dict) parameters for encoding message.
    # @returns (str) socks5 message.
    #
    @staticmethod
    def encode(properties):
        try:
            return "%s%s%s%s%s%s" % (
                chr(properties["version"]),
                chr(properties["command"]),
                chr(properties["reserved"]),
                chr(properties["address_type"]),
                ''.join(
                    chr(int(x))
                    for x in properties["address"].split('.')
                ),
                (
                    chr(properties["port"] / 256) +
                    chr(properties["port"] % 256)
                ),
            )
        except Exception:
            raise

    ## Decode packet message.
    # @param buffer (str) encoded message.
    # @returns (dict) decoded request.
    #
    @staticmethod
    def decode(buffer):
        if len(buffer) < 4:
            return
        data = [ord(a) for a in buffer]
        (
            version,
            command,
            reserved,
            address_type,
        ) = (
            data[0],
            data[1],
            data[2],
            data[3],
        )
        if (
            version == constants.SOCKS5_VERSION and
            reserved == constants.SOCKS5_RESERVED and
            command in constants.COMMANDS and
            address_type == constants.IP_4
        ):
            if len(data[4:]) < 6:
                return
            address, port = (
                '.'.join(str(n) for n in data[4:len(data) - 2]),
                256 * data[-2] + data[-1],
            )
            if not validate_ip(address):
                raise Socks5Error()
            return {
                "version": version,
                "command": command,
                "reserved": reserved,
                "address_type": address_type,
                "address": address,
                "port": port,
            }
        else:
            raise Socks5Error()


## Socks5 Request Packet.
# @param version (int) socks version.
# @param reply (int) status by server.
# @param reserved (int) reserved is 0.
# @param address type (int) address type requested.
# @param bind address (bytes) bind address.
# @param bind port (bytes) bind port.
#
# | version | reply | reserved | address type | bind address | bind port |
# | :-----: | :---: | :------: | :----------: | :----------: | :-------: |
# | 1       | 1     | "0x00"   | 1            | veriable     | 2         |
#
class Socks5Response(Socks5Packet):

    ## Encode packet message.
    # @param properties (dict) parameters for encoding message.
    # @returns (str) socks5 message.
    #
    @staticmethod
    def encode(properties):
        if properties["version"] != constants.SOCKS5_VERSION:
            raise Socks5Error()

        try:
            response = "%s%s%s%s%s%s" % (
                chr(properties["version"]),
                chr(properties["reply"]),
                chr(properties["reserved"]),
                chr(properties["address_type"]),
                ''.join(
                    chr(int(x))
                    for x in properties["address"].split('.')
                ),
                (
                    chr(properties["port"] / 256) +
                    chr(properties["port"] % 256)
                ),
            )
        except Exception:
            raise
        return response

    ## Decode packet message.
    # @param data (str) encoded message.
    # @returns (dict) decoded response.
    #
    @staticmethod
    def decode(data):
        try:
            return {
                "version": ord(data[0]),
                "reply": ord(data[1]),
                "reserved": ord(data[2]),
                "address_type": ord(data[3]),
                "bind_address": '.'.join(
                    str(i) for i in map(
                        ord, data[4:len(data) - 2]
                    )
                ),
                "bind_port": 256 * ord(data[-2]) + ord(data[-1]),
            }
        except Exception:
            raise


## Validate ip address.
# @param ip (str) address for validation.
# @returns (bool) True if address is IP4.
#
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
