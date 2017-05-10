#!/usr/bin/python

CONFIG_NAME = "config.ini"
MAX_BUFFER_SIZE = 1024
BASE = "files/"

OPTIMAL_NODES_IN_PATH = 3

PROXY_STATES = (
    ACTIVE,
    LISTEN,
    CLOSING,
) = range(3)

SOCKS5_STATES = (
    RECV_GREETING,
    SEND_GREETING,
    RECV_CONNECTION_REQUEST,
    SEND_CONNECTION_REQUEST,
    PARTNER_STATE,
    CLIENT_SEND_GREETING,
    CLIENT_RECV_GREETING,
    CLIENT_SEND_CONNECTION_REQUEST,
    CLIENT_RECV_CONNECTION_REQUEST,
) = range(9)

HTTP_STATES = (
    RECV_STATUS,
    RECV_HEADERS,
    RECV_CONTENT,
    SEND_STATUS,
    SEND_HEADERS,
    SEND_CONTENT,
) = range(6)


SOCKS5_VERSION = 0x05
SOCKS5_RESERVED = 0x00

SUPPORTED_METHODS = (
    NO_AUTH,
    NO_ACCEPTABLE_METHODS,
) = (
    0x00,
    0xff,
)
COMMANDS = (
    CONNECT,
) = (
    0x01,
)
ADDRESS_TYPE = (
    IP_4,
) = (
    0x01,
)
REPLY_STATUS = (
    SUCCESS,
    GENERAL_SERVER_FAILURE,
) = (
    0x00,
    0x01,
)

HTTP_SIGNATURE = "HTTP/1.1"
CRLF = "\r\n"
CRLF_BIN = CRLF.encode("utf-8")
MAX_NUMBER_OF_HEADERS = 100
CONTENT_TYPE = "Content-Type"
CONTENT_LENGTH = "Content-Length"
INTERNAL_ERROR = "Internal Error"
AUTHORIZATION = "Authorization"
UNATHORIZED = "Unathorized"

HEADERS = {
    "Cache-Control": "no-cache, no-store, must-revalidate", 
    "Pragma": "no-cache", 
    "Expires": "0", 
    "WWW-Authenticate": "Basic realm=\"myRealm\"" 
}
MIME_MAPPING = {
    'html': 'text/html',
    'png': 'image/png',
    'txt': 'text/plain',
    'css': 'text/css',
}

ACCOUNTS = {
    "Liron": "Berger",
}
