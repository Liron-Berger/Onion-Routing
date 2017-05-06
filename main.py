#!/usr/bin/python

import argparse
import logging
import signal

import async
import sockets

from common import util


poll_events = util.registry_by_name(
    async.BaseEvents,
)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--http-listener-address",
        default="0.0.0.0",
        help="http server bind address"
    )
    parser.add_argument(
        "--http-listener-port",
        default=8080,
        type=int,
        help="http server bind port"
    )
    parser.add_argument(
        "--socks5-first-node-address",
        default="0.0.0.0",
        help="address of the first node in all onion chains",
    )
    parser.add_argument(
        "--socks5-first-node-port",
        default=1080,
        type=int,
        help="port of the first node in all onion chains",
    )
    parser.add_argument(
        "--socks5-first-node-name",
        default="first node",
        help="the name of the first node in all onion chains",
    )
    parser.add_argument(
        "--node",
        action="append",
        help="socks5 node, format of listener is: [[%s:]%s:]%s" % (
            'name',
            'bind_address',
            'bind_port',
        )
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
        "--debug",
        default=False,
        help="whether to pring debug messages",
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
        "--xml-file",
        default="files/statistics.xml",
    )

    args = parser.parse_args()
    args.poll_object = poll_events[args.event_type]
    return args


def main():
    args = parse_args()

    if args.debug:
        log_level = logging.DEBUG
    else:
        log_level = logging.INFO
    logging.basicConfig(filename=args.log_file, level=log_level)

    logging.info(
        "Welcome to the Onion Routing project.\n"
    )

    if args.daemon:
        util.daemonize(args.log_file)

    def exit_handler(signal, frame):
        server.close_server()

    signal.signal(signal.SIGINT, exit_handler)
    signal.signal(signal.SIGTERM, exit_handler)
    
    connections = {}
    xml = util.XML(
        args.xml_file,
        connections,
    )

    application_context = {
        "log": args.log_file,
        "poll_object": args.poll_object,
        "poll_timeout": args.poll_timeout,
        "max_connections": args.max_connections,
        "max_buffer_size": args.max_buffer_size,

        "connections": connections,
        "registry": {},
        "xml": xml,
    }
    
    server = async.AsyncServer(
        application_context,
    )

    server.add_listener(
        sockets.HttpServer,
        args.http_listener_address,
        args.http_listener_port,
    )
    server.add_node(
        args.socks5_first_node_name,
        args.socks5_first_node_address,
        args.socks5_first_node_port,
        is_first=True,
    )

    if args.node:
        for node in args.node:
            (
                name,
                bind_address,
                bind_port,
            ) = node.split(':')
            server.add_node(
                name,
                bind_address,
                int(bind_port),
            )

    logging.info("Starting the async server...")

    server.run()

    logging.info(
        "Thank you for using Onion Routing project! hope you had a great time Mr. anonymous!"
    )


if __name__ == '__main__':
    main()
