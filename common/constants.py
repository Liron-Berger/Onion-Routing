#!/usr/bin/python
## @package onion_routing.common.constants
# Constants used within the program.
#


## Package name.
PACKAGE_NAME = "onion_routing"
## Package version.
PACKAGE_VERSION = "0.0.0"


## Default timout.
DEFAULT_TIMEOUT = 0
## Default base directory of files.
DEFAULT_BASE_DIRECTORY = "files/"
## Default connection number for listeners.
DEFAULT_CONNECTIONS_NUMBER = 10
## Default maximum size of buffer.
DEFAULT_BUFFER_SIZE = 1024


## Path of registry config file.
REGISTRY_NODE_CONFIG = "registry/config.ini"
## Path of node server config file.
NODE_SERVER_CONFIG = "node_server/config.ini"
## Path of node client config file.
NODE_SERVER_CONFIG = "node_client/config.ini"

## The number of nodes in path to anonymize message.
OPTIMAL_NODES_IN_PATH = 3

## Time between every update of xml statistics file.
XML_TIME_UPDATE = 1


## Async server socket states for @ref common.async.async_server.
# - ACTIVE: Used for all active sockets that are ready for reading/writing.
# - LISTEN: Used for listeners for accepting new connections.
# - CLOSING: Used when socket is about to be closed.
#
ASYNC_SERVER_STATES = (
    ACTIVE,
    LISTEN,
    CLOSING,
) = range(3)


## Socks5 socket states for @ref node_client.pollables.socks5_client and
##      @ref node_server.pollables.socks5_server.
# - RECV_GREETING: Recieve socks5 greeting from client.
# - SEND_GREETING: Send response for socks5 greeting to client.
# - RECV_CONNECTION_REQUEST: Recieve socks5 connection request from client.
# - SEND_CONNECTION_REQUEST: Send socks5 connection response to client.
# - PARTNER_STATE: Partner state when socket is used as TCP proxy
#       after the end socks5 communication.
# - CLIENT_SEND_GREETING: Send socks5 greeting to server.
# - CLIENT_RECV_GREETING: Recieve socks5 greeting response from server.
# - CLIENT_SEND_CONNECTION_REQUEST: Send socks5 connection request to server.
# - CLIENT_RECV_CONNECTION_REQUEST: Recieve socks5 connection
#       response from server.
#
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


## HTTP socket states for @ref registry.pollables.http_socket.
# - RECV_STATUS: Recieve status of HTTP request.
# - RECV_HEADERS: Recv headers of HTTP request.
# - RECV_CONTENT: Recieve content of HTTP request.
# - SEND_STATUS: Send status of HTTP response.
# - SEND_HEADERS: Send headers of HTTP response.
# - SEND_CONTENT: Send content of HTTP response.
#
HTTP_STATES = (
    RECV_STATUS,
    RECV_HEADERS,
    RECV_CONTENT,
    SEND_STATUS,
    SEND_HEADERS,
    SEND_CONTENT,
) = range(6)


## Registry socket states for registering new
##     @ref node_server.pollables.socks5_server
##     for @ref node_server.pollables.registry_socket.
# - SEND_REGISTER: Sending registring request.
# - RECV_REGISTER: Recieving response for register request.
# - SEND_UNREGISTER: Sending unregistering request.
# - RECV_UNREGISTER: Recieving response for unregister request.
# - WAITING: Sleeping state.
# - UNREGISTERED: Node unregistered state.
# - SEND_NODES: Sending a request to get connect nodes to registry.
# - RECV_NODES: Recieving string representation of nodes dict.
#
REGISTRY_STATES = (
    SEND_REGISTER,
    RECV_REGISTER,
    SEND_UNREGISTER,
    RECV_UNREGISTER,
    WAITING,
    UNREGISTERED,
    SEND_NODES,
    RECV_NODES,
) = range(8)


## Socks5 supported version.
SOCKS5_VERSION = 0x05
## Socks5 reserved byte.
SOCKS5_RESERVED = 0x00

## Socks5 Supported methods.
# - NO_AUTH: No authentication.
# - NO_ACCEPTABLE_METHODS: No acceptable methods available.
#
SUPPORTED_METHODS = (
    NO_AUTH,
    NO_ACCEPTABLE_METHODS,
) = (
    0x00,
    0xff,
)
## Private method for socks5 protocol.
# Special self recognition method for deciding whether to decrypt recieved data
# in @ref node_server.pollables.socks5_server.
# Data should not be decrypted if node acts as proxy, unless its the last node.
# In case of the last node the missing signature is recognized and thus the
# server knows it should decrypt the encrypted messages.
#
MY_SOCKS_SIGNATURE = 0x80

## Socks5 Supported commands.
# - CONNECT: Establish a TCP/IP stream connection.
#
COMMANDS = (
    CONNECT,
) = (
    0x01,
)

## Socks5 Supported address types.
# - IP_4: IPv4 address.
#
ADDRESS_TYPE = (
    IP_4,
) = (
    0x01,
)

## Socks5 Replies used by server.
# - SUCCESS: request granted.
# - GENERAL_SERVER_FAILURE: general failure.
#
REPLY_STATUS = (
    SUCCESS,
    GENERAL_SERVER_FAILURE,
) = (
    0x00,
    0x01,
)


## HTTP signature.
HTTP_SIGNATURE = "HTTP/1.1"
## Carriage return representation.
CRLF = "\r\n"
## Binary carriage return.
CRLF_BIN = CRLF.encode("utf-8")

## Max number of headers in HTTP request.
MAX_NUMBER_OF_HEADERS = 100
## Content type header.
CONTENT_TYPE = "Content-Type"
## Content length header.
CONTENT_LENGTH = "Content-Length"
## Internal error header.
INTERNAL_ERROR = "Internal Error"

## Supported Multipurpose Interner Mail Extenstions.
MIME_MAPPING = {
    "html": "text/html",
    "png": "image/png",
    "txt": "text/plain",
    "css": "text/css",
}

## Paths of all special services for @ref registry.pollables.http_socket.
SERVICES = [
    "registry.services.register_service",
    "registry.services.register_service",
    "registry.services.unregister_service",
    "registry.services.menu_service",
    "registry.services.nodes_service",
]


## XML Connection type.
XML_CONNECTIONS = 0
## XML Nodes type.
XML_NODES = 1

## Basic layout for xml file.
XML_CONNECTION_LAYOUT = (
    "<Statistics>"
    "<connection_number>%s</connection_number>"
    "%s"
    "</Statistics>"
)

## Layout of every statistics block of each connection.
XML_CONNECTION_BLOCK_LAYOUT = (
    "<connection>"
    "<num>%s</num>"
    "<server>%s</server>"
    "<in>%s</in>"
    "<partner>%s</partner>"
    "<out>%s</out>"
    "</connection>"
)

## Basic layout for xml file.
XML_NODES_LAYOUT = (
    "<Statistics>"
    "<nodes_number>%s</nodes_number>"
    "%s"
    "</Statistics>"
)

## Layout of every statistics block of each connection.
XML_NODES_BLOCK_LAYOUT = (
    "<node>"
    "<address>%s</address>"
    "<port>%s</port>"
    "</node>"
)