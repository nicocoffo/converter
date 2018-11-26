#!/usr/bin/env python3

import sys
import logging
import signal
import argparse
import notifications
import uuid

from jackhammer import Scheduler
from jackhammer.cloud import GCP
from watcher import Watcher
from transcoder import Transcoder
from notifications import Notifications
from config import parse_config

shutdown_flag = False

def main(config):
    # Create threads
    uid = str(uuid.uuid4())
    notifications = Notifications(config['notifications'])
    jackhammer = Scheduler(lambda: GCP(uid, config['cloud']), config['scheduler'])
    watcher = Watcher(config['watcher'])
    transcoder = Transcoder(watcher.new, watcher.finished, jackhammer.pending, notifications, config['transcoder'])
    threads = [jackhammer, watcher, transcoder]

    # Setup the signal handler for shutdown
    def shutdown():
        global shutdown_flag
        if not shutdown_flag:
            [t.shutdown() for t in threads]
            shutdown_flag = True
    signal.signal(signal.SIGTERM, lambda s, f: shutdown())
    signal.signal(signal.SIGINT, lambda s, f: shutdown())

    # Launch and join
    [t.start() for t in threads]
    while True in [t.is_alive() for t in threads]:
        [t.join(timeout=1) for t in threads]
        [shutdown() for t in threads if not t.is_alive()]

    # Manage any exceptions
    exception = None
    for t in threads:
        if t.exception:
            exception = t.exception
            notifications.send_exception(exception)
    if exception:
        raise exception

if __name__ == '__main__':
    # Parse arguments
    parser = argparse.ArgumentParser(description='Convert media on cloud instances.')
    parser.add_argument('--verbose', '-v', action='store_true')
    parser.add_argument('--config', '-c', action='store', default='config.yaml')
    args = parser.parse_args(sys.argv[1:])

    # Parse config
    config = parse_config(args.config)

    # Configure logging
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=level, format=config['logFormat'])
    logging.getLogger("paramiko").setLevel(logging.CRITICAL)
    logging.getLogger("urllib3").setLevel(logging.CRITICAL)

    main(config)
