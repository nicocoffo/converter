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
        self.callback = finished
        self.config = config

        # Source filename
        self.filename = os.path.basename(self.source)

        # State
        self.remaining_encodings = []

    def get_encodings(self):
        """
        Determine the necessary outputs for this file, given the
        the plan's desired encodings.
        """
        # Ignore .srt files
        if self.source[-3:] == ".srt":
            return []

        try:
            info = VideoInfo(self.source)
        except Exception as e:
            logger.warning("Failed to get video info for %s: %s", self.filename, str(e))
            raise e

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

        self.remaining_encodings = self.get_encodings()

        # Check if any will be remuxed
        for enc in self.remaining_encodings:
            if enc.is_remuxable():
                jobs.append(Remux(enc, self.config['job']))
            else:
                split.append(enc)

        # The rest will undergo a split/convert/merge workflow
        if len(split) > 0:
            jobs.append(Split(split, self.config['job']))
        return jobs

    def finished(self, encoding):
        """
        Callback to track finished jobs.
        """
        if not encoding in self.remaining_encodings:
            logger.warning("Attempt to finish unknown encoding: %s", encoding)
            return
        logger.debug("Finishing encoding %s, %d remaining", encoding,
                len(self.remaining_encodings))
        self.remaining_encodings.remove(encoding)
        if len(self.remaining_encodings) == 0:
            self.callback(self)

    def __repr__(self):
        return os.path.basename(self.source)
