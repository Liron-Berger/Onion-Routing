#!/usr/bin/python

MAX_BUFFER_SIZE = 1024
MAX_LISTENER_CONNECTIONS = 10
POLL_TIMEOUT = 10000






VERSION = 0x05
RESERVED = 0x00

""" SOCKS 5 METHODS """
NO_AUTHENTICATION_REQUIRED = 0x00
GSSAPI = 0x01
USERNAME_PASSWORD = 0x02
IANA_ASSIGNED = range(0x03, 0x7F)
PRIVATE_METHODS = range(0x80, 0xFE)
NO_ACCEPTABLE_METHODS = 0xFF

SUPPORTED_METHODS = (
    NO_AUTHENTICATION_REQUIRED,
)

""" SOCKS 5 REPLY STATUS """
SUCCESS = 0x00
GENERAL_SERVER_FAILURE = 0x01
CONNECTION_RULESET_FAILURE = 0x02
NETWORK_UNREACHABLE = 0x03
HOST_UNREACHABLE = 0x04
CONNECTION_REFUSED = 0x05
TTL_EXPIRED = 0x06
UNSUPPORTED_COMMAND = 0x07
UNSUPPORTED_ADDRESS_TYPE = 0x08

""" SOCKS 5 COMMANDS """
CONNECT = 0x01
BIND = 0x02
UDP_ASSOCIATE = 0x03

SUPPORTED_COMMANDS = (
    CONNECT,
)

""" SOCKS 5 ADDRESS TYPE """
IP_4 = 0x01
DOMAINNAME = 0x03
IP_6 = 0x04

SUPPORTED_ADDRESS_TYPE = (
    IP_4,
)






""" HTTP CONSTANTS """

BLOCK_SIZE = 1024
CRLF = '\r\n'
CRLF_BIN = CRLF.encode('utf-8')
DEFAULT_HTTP_PORT = 80
HTTP_SIGNATURE = 'HTTP/1.1'
MAX_HEADER_LENGTH = 4096
MAX_NUMBER_OF_HEADERS = 100

ACCOUNT = {"liron": "123456"}

STATUSES = {'SUCCESS': '200 OK', 'Unauthorized': '401 Unauthorized', 'NotModified': '304 Not Modified', 'Redirect': '301 Moved Permanently'}
HEADERS =   {   'Cache-Control': 'Cache-Control: no-cache, no-store, must-revalidate', 
                'Pragma': 'Pragma: no-cache', 
                'Expires': 'Expires: 0', 
                'WWW-Authenticate':'WWW-Authenticate: Basic realm=\"myRealm\"' 
            }
                                
# vim: expandtab tabstop=4 shiftwidth=4


