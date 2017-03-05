#!/usr/bin/python

import argparse
import logging
import signal

import async
import sockets

from common import util


listener_types = {
    "socks5": sockets.Socks5Server,
    "http": sockets.HttpServer,
}
poll_events = util.registry_by_name(
    async.BaseEvents,
)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--listener",
        action="append",
        help="listener proxy, format of listener is: [[%s:]%s:]%s" % (
            'bind_address',
            'bind_port',
            'listener_type',
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

    args = parser.parse_args()
    args.poll_object = poll_events[args.event_type]
    return args


def main():
    args = parse_args()

    logging.basicConfig(filename=args.log_file, level=logging.DEBUG)

    if args.daemon:
        util.daemonize(args.log_file)

    def exit_handler(signal, frame):
        proxy.close_proxy()

    signal.signal(signal.SIGINT, exit_handler)
    signal.signal(signal.SIGTERM, exit_handler)

    application_context = {
        "log": args.log_file,
        "poll_object": args.poll_object,
        "poll_timeout": args.poll_timeout,
        "max_connections": args.max_connections,
        "max_buffer_size": args.max_buffer_size,

        "connections": {},
    }

    proxy = async.Proxy(
        application_context,
    )

    for l in args.listener:
        (
            bind_address,
            bind_port,
            type,
        ) = l.split(':')
        logging.debug(
            "new listener added: %s:%s. type: %s." % (
                bind_address,
                bind_port,
                type,
            )
        )
        proxy.add_listener(
            listener_types[type],
            bind_address,
            int(bind_port),
        )

    logging.debug("starting proxy...")
    proxy.run()


if __name__ == '__main__':
    main()
