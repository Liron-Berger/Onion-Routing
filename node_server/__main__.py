#!/usr/bin/python
## @package onion_routing.node_server.__main__
# The main module for the node server.
#

import argparse
import ConfigParser
import logging
import signal

from common import constants
from common.async import async_server
from common.async import event_object
from common.utilities import util
from node_server.pollables import server_node


## Dictionary off all possible events for poller.
poll_events = {
    event.NAME: event for event in event_object.BaseEvent.__subclasses__()
}


## Parse program argument.
# @returns (dict) program arguments.
#
def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--bind-address",
        default="0.0.0.0",
        help="bind address of node, default: %(default)s",
    )
    parser.add_argument(
        "--bind-port",
        required=True,
        type=int,
        help="bind port of node, default: %(default)s",
    )
    parser.add_argument(
        "--event-type",
        choices=poll_events.keys(),
        default=sorted(poll_events.keys())[0],
        help="async event type, default: %(default)s, choices: %(choices)s",
    )
    parser.add_argument(
        "--log-file",
        default=None,
        help="Optional file for log",
    )
    parser.add_argument(
        "--base",
        default=constants.DEFAULT_BASE_DIRECTORY,
        help="base location of files",
    )
    parser.add_argument(
        "--daemon",
        default=False,
        type=bool,
        help="Process becomes daemon, default: %(default)s",
    )
    parser.add_argument(
        "--timeout",
        default=constants.DEFAULT_TIMEOUT,
        type=int,
        help="timeout, default: %(default)s",
    )
    parser.add_argument(
        "--max-connections",
        default=constants.DEFAULT_CONNECTIONS_NUMBER,
        type=int,
        help="Number of connections the server accepts, default: %(default)s",
    )
    parser.add_argument(
        "--max-buffer-size",
        default=constants.DEFAULT_BUFFER_SIZE,
        type=int,
        help="Max size of reading buffer, default: %(default)s",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Logging level, default: %(default)s",
    )
    args = parser.parse_args()
    args.poll_object = poll_events[args.event_type]
    return args


## Main implementation.
def __main__():
    args = parse_args()
    logging.basicConfig(
        filename=args.log_file,
        level=getattr(logging, args.log_level),
    )

    config = ConfigParser.ConfigParser()
    config.read(constants.REGISTRY_NODE_CONFIG)

    logging.info("Welcome to the Onion Routing project.\n")

    if args.daemon:
        util.daemonize()

    def exit_handler(signal, frame):
        server.close_server()

    signal.signal(signal.SIGINT, exit_handler)
    signal.signal(signal.SIGTERM, exit_handler)

    app_context = {
        "log_file": args.log_file,
        "poll_object": args.poll_object,
        "timeout": args.timeout,
        "max_connections": args.max_connections,
        "max_buffer_size": args.max_buffer_size,
        "base": args.base,

        "http_address": config.get("HttpSocket", "bind.address"),
        "http_port": config.getint("HttpSocket", "bind.port"),
    }

    server = async_server.AsyncServer(
        app_context,
    )

    node = server.add_listener(
        server_node.ServerNode,
        args.bind_address,
        args.bind_port,
    )
    server.add_socket(node.http_client)

    logging.info("Starting the async server...")

    server.run()

    logging.info(
        "Thank you for using Onion Routing project!"
    )


if __name__ == '__main__':
    __main__()
