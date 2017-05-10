#!/usr/bin/python

import argparse
import ConfigParser
import logging
import signal

import async
import sockets

from common import util
from common import constants

poll_events = util.registry_by_name(
    async.BaseEvents,
)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--node",
        help="node for Onion Routing. format is [name:address:port]",
    )
    parser.add_argument(
        '--event-type',
        choices=poll_events.keys(),
        default=sorted(poll_events.keys())[0],
        help='async event type, default: %(default)s, choices: %(choices)s',
    )
    parser.add_argument(
        '--log-file',
        default=None,
        help='name of log file, default is standard output',
    )
    parser.add_argument(
        '--daemon',
        default=False,
        type=bool,
        help='process becomes daemon, default: %(default)s',
    )
    parser.add_argument(
        '--poll-timeout',
        default=10000,
        type=int,
        help='poll timeout, default: %(default)s',
    )
    parser.add_argument(
        '--max-connections',
        default=10,
        type=int,
        help='max number of connections per listener, default: %(default)s',
    )
    parser.add_argument(
        '--max-buffer-size',
        default=1024,
        type=int,
        help='max size of buffer in async_socket, default: %(default)s',
    )
    parser.add_argument(
        "--first-node",
        default=False,
        type=bool,
        help="wheter the program is the first or regular node",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Set the logging level",
    )
    parser.add_argument(
        "--base",
        default=constants.BASE,
        help="base location of files",
    )

    args = parser.parse_args()
    args.poll_object = poll_events[args.event_type]
    return args


def init_application_context(args):
    return {
        "log_file": args.log_file,
        "poll_object": args.poll_object,
        "poll_timeout": args.poll_timeout,
        "max_connections": args.max_connections,
        "max_buffer_size": args.max_buffer_size,
        "base": args.base,
        
        "registry": {},
        "connections": {},
    }
    
def init_xml(config, application_context):
    return util.XML(
        config.get("xmlFile", "path"),
        application_context["connections"],
    )
    
    
def init_first_node(
    server,
    config,
    args,
):
    server.add_listener(
        sockets.Listener,
        config.get("HttpServer", "bind.address"),
        config.getint("HttpServer", "bind.port"),
        sockets.HttpServer,
    )
    
    add_node(
        server,
        config,
        config.get("FirstSocks5Node", "name"),
        config.get("FirstSocks5Node", "bind.address"),
        config.getint("FirstSocks5Node", "bind.port"),
        args.first_node,
    )
    
def init_node(
    server,
    config,
    args,
):
    (
        name,
        bind_address,
        bind_port,
    ) = args.node.split(':')
    
    add_node(
        server,
        config,
        name,
        bind_address,
        int(bind_port),
        args.first_node,
    )
    

def add_node(
    server,
    config,
    name,
    bind_address,
    bind_port,
    is_first,
):
    node = server.add_listener(
        sockets.Node,
        bind_address,
        bind_port,
        name,
        is_first,
    )
    server.add_socket(
        sockets.RegistrySocket,
        config.get("HttpServer", "bind.address"),
        config.getint("HttpServer", "bind.port"),
        node,
    )


def main():
    args = parse_args()

    config = ConfigParser.ConfigParser()
    config.read(constants.CONFIG_NAME)

    logging.basicConfig(filename=args.log_file, level=getattr(logging, args.log_level))

    logging.info(
        "Welcome to the Onion Routing project.\n"
    )

    if args.daemon:
        util.daemonize()

    def exit_handler(signal, frame):
        server.close_server()

    signal.signal(signal.SIGINT, exit_handler)
    signal.signal(signal.SIGTERM, exit_handler)
    
    application_context = init_application_context(args)
    application_context["xml"] = init_xml(
        config,
        application_context,
    )
    
    server = async.AsyncServer(
        application_context,
    )
    
    if args.first_node:
        init_first_node(
            server,
            config,
            args,
        )
    else:
        init_node(
            server,
            config,
            args,
        )

    logging.info("Starting the async server...")

    server.run()

    logging.info(
        "Thank you for using Onion Routing project!"
    )


if __name__ == '__main__':
    main()
