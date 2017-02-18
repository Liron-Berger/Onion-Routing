#!/usr/bin/python

import argparse
import logging
import signal

from common import util
from sockets.base_socket import BaseSocket

from async.proxy import Proxy
from async.events import BaseEvents

server_map = util.registry_by_name(
    BaseSocket,
)
event_map = util.registry_by_name(
    BaseEvents,
)

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--proxy',
        action='append',
        help='proxy server, format of proxy is: [[%s:]%s:]%s' % (
            'bind_address',
            'bind_port',
            'protocol',
        )
    )
    parser.add_argument(
        '--event-type',
        choices=event_map.keys(),
        default=sorted(event_map.keys())[0],
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
        '--block-size',
        default=1024,
        type=int,
        help='block size, default: %(default)s',
    )

    args = parser.parse_args()
    args.event_type_class = event_map[args.event_type]
    return args


def main():
    args = parse_args()

    logging.basicConfig(filename=args.log_file, level=logging.DEBUG)

    if args.daemon:
        util.daemonize(args.log_file)

    application_context = {
        "connections": {},
        "accounts": {},
    }

    proxy = Proxy(
        args.poll_timeout,
        args.block_size,
        args.event_type_class,
        application_context,
    )

    def exit_handler(signal, frame):
        proxy.close_proxy()

    signal.signal(signal.SIGINT, exit_handler)
    signal.signal(signal.SIGTERM, exit_handler)

    for x in args.proxy:
        (
            bind_address,
            bind_port,
            protocol,
        ) = x.split(':')
        proxy.add_listener(
            bind_address,
            int(bind_port),
            server_map[protocol],
        )

    proxy.run()


if __name__ == '__main__':
    main()
