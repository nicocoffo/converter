#!/usr/bin/env python3

import logging
import signal
import ntpath
import os

from jackhammer import Scheduler, Job, Script
from jackhammer.cloud_providers import GCP

# Constants
PROJECT = os.environ.get('GCP_PROJECT')
ZONE = os.environ.get('GCP_ZONE')
INSTALL_SCRIPT = "scripts/install.sh"
CONFIGURE_SCRIPT = "scripts/configure.sh"
CONVERT_SCRIPT = "scripts/convert.sh"
DST_BASE = "optimised/"
LOG_FORMAT= '%(asctime)s - %(threadName)s - %(name)-12s - %(levelname)-5s - %(message)s'

logger = logging.getLogger("converter")

class ConverterJob(Job):
    def __init__(self, post, index):
        Job.__init__(self, post, index)

        if 'episodeFile' in self.payload:
            path = self.payload['episodeFile']['path']
            src, name = ntpath.split(self.path)
        elif 'src' in self.payload:
            src = self.payload['src']
            name = self.payload['name']
        else:
            raise Exception("Invalid converter job")

        dst = DST_BASE + os.path.sep + src
        self.scripts = [Script(INSTALL_SCRIPT), Script(CONFIGURE_SCRIPT),
                Script(CONVERT_SCRIPT, args=[name, src, dst])]

if __name__ == '__main__':
    # Configure logging
    logging.basicConfig(level=logging.DEBUG,format=LOG_FORMAT)
    logging.getLogger('googleapiclient.discovery').setLevel(logging.CRITICAL)
    logging.getLogger("paramiko").setLevel(logging.CRITICAL)
    logging.getLogger("google_auth_httplib2").setLevel(logging.CRITICAL)

    # Create the jackhammer
    provider = GCP(PROJECT, ZONE)
    jackhammer = Scheduler(provider, ConverterJob)

    # Setup the signal handler for shutdown
    def signal_handler(sig, frame):
        logger.info("Signal received, shutting down")
        jackhammer.shutdown()
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    # Launch the jackhammer
    jackhammer.run()
