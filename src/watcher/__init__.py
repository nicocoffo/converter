import os
import time
import traceback
import logging
import gzip
from threading import Thread, Event
from queue import Queue

from watcher.server import run_server, stop_server

logger = logging.getLogger("replicant.watcher")


class Watcher(Thread):
    """
    Walk a folder structure and identify 'new' files.
    Files are pushed to a queue.
    Files can be marked as done via the finished queue.
    These files are stashed to remained marked as finished across 
    executions.
    """

    def __init__(self, config):
        super().__init__()
        self.name = "replicant.watcher"
        self.exception = None
        self.shutdown_flag = Event()
        self.server = None

        # Args
        self.config = config

        # Sets
        self.seen_set = {}
        self.finished_set = {}

        # Queues
        self.new = Queue()
        self.finished = Queue()
        self.command_queue = Queue()

    def shutdown(self):
        """
        Shutdown the watcher.
        """
        self.shutdown_flag.set()

    def run(self):
        """
        Thread entry point.
        Launch the watcher loop, capturing exceptions and stashing the
        completed files on termination.
        """
        logger.info("Watcher Launch: %s", self)
        try:
            # Load processed files
            self.restore_finished()

            # Launch the HTTP server
            self.server = run_server(self.config['port'], self.command_queue)

            # Begin running
            while not self.shutdown_flag.is_set():
                self.watcher_loop()
        except Exception as e:
            logger.error("Watcher Failure: %s", str(e))
            logger.error(traceback.format_exc())
            self.exception = e

        # Cleanup
        if self.server:
            stop_server(self.server)
        self.collect_finished()
        self.backup_finished()

        logger.info("Watcher Shutdown: %s", self)

    def watcher_loop(self):
        """
        Watch the root directory, collecting any new files.
        Then delays, collecting files promoted to finished.
        """
        count = self.walk_directory(self.config['root'])
        logger.info("Watcher finished, %d new files found", count)

        start = time.time()
        while time.time() - start < self.config['loopDelay']:
            if not self.command_queue.empty():
                cmd = self.command_queue.get()
                if cmd and 'path' in cmd:
                    reattempt = 'cmd' in cmd and cmd['cmd'] == 'reattempt'
                    count = self.walk_directory(cmd['path'], not reattempt)
                    logger.info("Request finished, %d new files found", count)
            self.collect_finished()
            time.sleep(1)
            if self.shutdown_flag.is_set():
                return

    def walk_directory(self, directory, skip_finished=True):
        """
        Walk the directory, collecting any new files.
        """
        count = 0
        for root, dirs, files in os.walk(directory):
            for filename in files:
                source = os.path.join(root, filename)
                if skip_finished and source in self.finished_set:
                    logger.debug("Ignoring finished file: %s", filename)
                elif source in self.seen_set:
                    logger.debug("Ignoring seen file: %s", filename)
                else:
                    logger.debug("Adding file: %s", filename)
                    self.new.put(source)
                    self.seen_set[source] = True
                    count += 1
            if self.shutdown_flag.is_set():
                return count
        return count

    def collect_finished(self):
        """
        Poll the finished files to clean up any that have finished.
        """
        while not self.finished.empty():
            source = self.finished.get()
            logger.debug("Finished file: %s", source)
            self.finished_set[source] = True
            self.seen_set.pop(source)

    def backup_finished(self):
        """
        Save the files to a gzipped backup.
        """
        with gzip.open(self.config['backupPath'], 'wt') as f:
            f.writelines([k + '\n' for k, v in self.finished_set.items()])

    def restore_finished(self):
        """
        Read the gzipped backup.
        """
        if not os.path.isfile(self.config['backupPath']):
            return
        with gzip.open(self.config['backupPath'], 'rt') as f:
            self.finished_set = {l.strip(): True for l in f.readlines()}

    def __repr__(self):
        return self.name
