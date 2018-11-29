import time
import traceback
import logging
import os
from threading import Thread, Event
from transcoder.encoding import LowBitRate, HighBitRate
from transcoder.plan import Plan

logger = logging.getLogger("replicant.transcoder")

class Transcoder(Thread):

    def __init__(self, incoming_files, finished_files, add_jobs, noti, config):
        super().__init__()
        self.name = "replicant.transcoder"
        self.exception = None
        self.shutdown_flag = Event()
        self.notifications = noti

        # Args
        self.incoming_files = incoming_files
        self.finished_files = finished_files
        self.add_jobs = add_jobs
        self.config = config
        self.encodings = []
        if "720p" in config['encodings']:
            self.encodings.append(lambda s, t, i, f: LowBitRate(s,t,i,f,noti,config))
        if "1080p" in config['encodings']:
            self.encodings.append(lambda s, t, i, f: HighBitRate(s,t,i,f,noti,config))

    def shutdown(self):
        """
        Shutdown the transcoder.
        """
        self.shutdown_flag.set()

    def run(self):
        """
        Thread entry point.
        """
        logger.info("Transcoder Launch: %s", self)
        try:
            self.transcoder_loop()
        except Exception as e:
            logger.error("Transcoder Failure: %s", str(e))
            logger.error(traceback.format_exc())
            self.exception = e

        logger.info("Transcoder Shutdown: %s", self)

    def transcoder_loop(self):
        """
        Watch the incoming files queue, creating plans to transcode the
        result and launch corresponding jobs.
        """
        while not self.shutdown_flag.is_set():
            if not self.incoming_files.empty():
                source = self.incoming_files.get()
                self.add_plan(source)
            else:
                time.sleep(2)

    def add_plan(self, source):
        """
        """
        target = source.replace(self.config['src'], self.config['dst'], 1) 
        target = os.path.dirname(target)

        try:
            plan = Plan(source, target, self.encodings, self.finish_plan, self.config)
            jobs = plan.get_jobs()
            for job in jobs:
                logger.info("Scheduling job: %s", job)
                self.add_jobs.enqueue(job)
            if len(jobs) == 0:
                self.finish_plan(plan)
        except Exception as e:
            logger.error("Failed to add job: %s %s", source, str(e))
            logger.error(traceback.format_exc())
            self.notifications.send_exception(e)
            self.finished_files.put(source)

    def finish_plan(self, plan):
        """
        Callback for a plan, called when it is finished.
        """
        logger.info("Finishing trancoder plan: %s", plan)
        self.finished_files.put(plan.source)

    def __repr__(self):
        return self.name
