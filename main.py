#!/usr/bin/python

import argparse
import logging
import signal

import util

from async import (
    Proxy,
    BaseEvents,
)


def parse_args():
    event_map = {
        event.NAME: event for event in BaseEvents.__subclasses__()
    }

    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--proxy',
        action='append',
        help='proxy server, format of proxy is: [%s:]%s' % (
            'bind_address',
            'bind_port',
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
        help='foreground, default: %(default)s',
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

    proxy = Proxy(
        args.poll_timeout,
        args.block_size,
        args.event_type_class,
    )

    def exit_handler(signal, frame):
        proxy.close_proxy()

    signal.signal(signal.SIGINT, exit_handler)
    signal.signal(signal.SIGTERM, exit_handler)

    for x in args.proxy:
        (
            bind_address,
            bind_port,
        ) = x.split(':')
        proxy.add_listener(
            bind_address,
            int(bind_port),
        )

    proxy.run()


if __name__ == '__main__':
    main()
