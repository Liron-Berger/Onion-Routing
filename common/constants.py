#!/usr/bin/python
## @package onion_routing.common.constants
# Constants used within the program.
#

## Default timout.
DEFAULT_TIMEOUT = 0

##Default base directory of files.
DEFAULT_BASE_DIRECTORY = "files/"

##Default connection number for listeners.
DEFAULT_CONNECTIONS_NUMBER = 10

##Default maximum size of buffer.
DEFAULT_BUFFER_SIZE = 1024

REGISTRY_NODE_CONFIG = "registry_node/config.ini"
NODE_SERVER_CONFIG = "node_server/config.ini"

CONFIG_NAME = "config.ini"
MAX_BUFFER_SIZE = 1024





XML_TIME_UPDATE = 1
XML_LAYOUT = (
    '<Statistics>'
        '<connection_number>%s</connection_number>'
        '%s'
    '</Statistics>'
)

XML_CONNECTION_BLOCK_LAYOUT = (
    '<connection>'
        '<num>%s</num>'
        '<server>%s</server>'
        '<in>%s</in>'
        '<partner>%s</partner>'
        '<out>%s</out>'
    '</connection>'
)







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

MY_SOCKS_SIGNATURE = 0xaa #special self recognition method, for knowing whether its my socks or the clients.


SUPPORTED_METHODS = (
    NO_AUTH,
    NO_ACCEPTABLE_METHODS,
) = (
    0x00,
    0xff,
)

SUPPORTED_METHODS_X = (
    NO_AUTH,
    NO_ACCEPTABLE_METHODS,
    MY_SOCKS_SIGNATURE,
) = (
    0x00,
    0xff,
    0xaa,
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









REGISTRY_STATES = (
    SEND_REGISTER,
    RECV_REGISTER,
    SEND_UNREGISTER,
    RECV_UNREGISTER,
    WAITING,
    UNREGISTERED,
) = range(6)

SERVICES = [
    "registry_node.services.disconnect_service",
    "registry_node.services.register_service",
    "registry_node.services.statistics_service",
    "registry_node.services.register_service",
    "registry_node.services.unregister_service",
]




