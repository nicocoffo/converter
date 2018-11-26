import os
import logging

from transcoder.videoInfo import VideoInfo
from transcoder.jobs.split import Split
from transcoder.jobs.remux import Remux

logger = logging.getLogger("replicant.transcoder")

class Plan:
    """
    Given an input video file, determine the necessary conversions
    to schedule.
    """

    def __init__(self, source, target, encodings, finished, config):
        # Args
        self.source = source
        self.target = target
        self.desired = encodings
        self.finished = finished
        self.config = config

        # Source filename
        self.filename = os.path.basename(self.source)

        # State
        self.remaining_jobs = []

    def get_encodings(self):
        """
        Determine the necessary outputs for this file, given the
        the plan's desired encodings.
        """
        info = VideoInfo(self.source)

        encodings = []
        for enc in self.desired:
            output = enc(self.source, self.target, info, self.finished)
            (valid, msg) = output.validate()
            logger.debug("Checking encoding %s: %s", output, msg)
            if not valid:
                encodings.append(output)
            if not output.exceeded():
                break

        return encodings

    def get_jobs(self):
        """
        Generate the jackhammer jobs for the conversion.
        """
        jobs = []
        split = []

        # Check if any will be remuxed
        for enc in self.get_encodings():
            if enc.is_remuxable():
                jobs.append(Remux(enc, self.config['job']))
            else:
                split.append(enc)

        # The rest will undergo a split/convert/merge workflow
        if len(split) > 0:
            jobs.append(Split(split, self.config['job']))

        self.remaining_jobs = jobs
        return jobs

    def finished(self, encoding):
        """
        Callback to track finished jobs.
        """
        self.remaining_jobs.remove(encoding)
        if len(self.remaining_jobs) == 0:
            self.finished(self)

    def __repr__(self):
        return os.path.basename(self.source)
