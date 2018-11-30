import os
import math
import logging
from transcoder.jobs.remux import Remux
from transcoder.videoInfo import VideoInfo
from transcoder.templates import SuccessReport, FailureReport

logger = logging.getLogger("replicant.transcoder")


class Encoding:
    def __init__(self, source, target, info, finished, notifications, config):
        # Args
        self.source = source
        self.info = info
        self.finished = finished
        self.notifications = notifications
        self.lang = self.info.lang

        # Calculate the expected output
        self.target = os.path.join(target, os.path.basename(source))
        self.target = self.transform_filename(self.target)

        # Segment length constants
        self.seg_min = config['segmentMin']
        self.seg_max = config['segmentMax']
        self.parts = config['segmentParts']

        # Constraints
        self.constraints = [
            (lambda i: i.general().isstreamable == "Yes",
                "Not web optimised"),
            (lambda i: i.general().internet_media_type == self.media_type,
                "Wrong media type"),
            (lambda i: i.general().overall_bit_rate <= self.bit_rate,
                "Exceeds maximum bit rate"),
            (lambda i: i.resolution() <= self.video_resolution,
                "Exceeds maximum resolution"),
            (lambda i: i.video().format == self.video_format,
                "Bad video format"),
            (lambda i: i.video().bit_depth == self.video_bit_depth,
                "Bad video bit depth"),
            (lambda i: i.level() <= self.video_level,
                "Bad video level"),
            (lambda i: i.audio().format == self.audio_format,
                "Bad audio format"),
        ]

    def validate(self, detailed=False):
        """
        Validates a file conforms to the encoding.
        Returns a string describing the issue, otherwise returns None in
        the successful case.
        """
        if not os.path.isfile(self.target):
            return (False, "Target does not exist")

        msg = ""
        info = VideoInfo(self.target)
        for (constraint, desc) in self.constraints:
            if not constraint(info):
                msg += desc + "\n"
                if not detailed:
                    break

        out = False
        if msg == "":
            # Compare lengths
            delta = abs(self.info.general().duration - info.general().duration)
            out = delta <= 10000
            if out:
                msg = "Valid encoding"
            else:
                msg = "Durations differ by more than 10 seconds"

        if detailed:
            msg += "\n" + info.report()

        return (out, msg)

    def calculate_segment_length(self):
        secs = math.ceil(self.info.general().duration / (1000.0 * self.parts))
        if secs < self.seg_min:
            return self.seg_min
        if secs > self.seg_max:
            return self.seg_max
        return secs

    def transform_filename(self, source):
        """
        Transform a filename into the format desired by this encoding.
        """
        parts = source.split(".")
        if len(parts) > 2:
            parts[-2] = self.name
        parts[-1] = self.extension
        return ".".join(parts)

    def exceeded(self):
        """
        Determine whether a significant amount of information will be lost
        transcoding the source into this format. Returns true if so.
        """
        res = self.info.resolution()
        if res > self.video_resolution:
            return True
        if res == self.video_resolution:
            return self.info.general().overall_bit_rate > self.bit_rate
        return False

    def is_remuxable(self):
        """
        A file is considered remuxable if its video component can be
        packaged into a new container without transcoding.
        """
        if self.info.resolution() > self.video_resolution:
            return False
        bit_rate = self.bit_rate - self.audio_bit_rate
        return self.info.video().bit_rate < bit_rate

    def get_remux_args(self):
        """
        FFMPEG arguments to remux the file.
        Assumes is_remuxable returns True.
        """
        args = ["-hide_banner",
                "-nostdin",
                "-movflags",
                "faststart",
                "-map_metadata",
                "-1",
                "-map_chapters",
                "-1",
                "-map",
                "0:v:" + self.info.video().stream_identifier,
                "-map",
                "0:a:" + self.info.audio().stream_identifier,
                "-sn",
                "-dn",
                "-c:v",
                "copy",
                "-c:a:0",
                "aac",
                "-ac:a:0",
                str(self.audio_channels),
                "-b:a:0",
                str(self.audio_bit_rate),
                "-metadata:s:a:0",
                "language=" + self.info.get_audio_lang()]
        return " ".join(args)

    def get_args(self):
        return self.args

    def success(self, job):
        """
        Verify the produced file is valid and run the callback.
        """
        self.finished(self)

        # Verify the output is valid
        (valid, report) = self.validate(detailed=True)
        if valid:
            service = self.notifications.update_services(self.target)
        else:
            service = "Bad encoding, not done"

        # Send a notification with details thus far
        subject = "Successful Encoding: %s" % self
        msg = SuccessReport.substitute(
            source=self.source,
            target=self.target,
            encoding=self.name,
            encoding_report=report,
            job=job.report(),
            service=service)
        self.notifications.send(subject, msg)

    def failure(self, job):
        """
        Send a notification detailing the failed job and run the callback.
        """
        self.finished(self)

        subject = "Failed Encoding: %s" % self
        msg = FailureReport.substitute(
            source=self.source,
            target=self.target,
            encoding=self.name,
            job=job.report())
        self.notifications.send(subject, msg)

    def __repr__(self):
        return os.path.basename(self.target)

class LowBitRate(Encoding):
    def __init__(self, source, target, info, finished, notifications, config):
        # Container properties
        self.name = "720p"
        self.extension = "mp4"
        self.bit_rate = 2000000
        self.bit_rate_buffer = 50000
        self.media_type = 'video/mp4'

        # Audio properties
        self.audio_bit_rate = 128000
        self.audio_channels = 1
        self.audio_format = 'AAC'

        # Video properties
        self.video_bit_rate = self.bit_rate - self.bit_rate_buffer - self.audio_bit_rate
        self.video_bit_depth = 8
        self.video_resolution = 720 * 1280
        self.video_format = 'AVC'
        self.video_level = 4.1

        self.args = '--target 720p=1750 --mp4 --quick --720p --abr --audio-width main=stereo -H ab=192'
        super().__init__(source, target, info, finished, notifications, config)

class HighBitRate(Encoding):
    def __init__(self, source, target, info, finished, notifications, config):
        # Container properties
        self.name = '1080p'
        self.extension = 'mp4'
        self.bit_rate = 8000000
        self.bit_rate_buffer = 50000
        self.media_type = 'video/mp4'

        # Audio properties
        self.audio_bit_rate = 384000
        self.audio_channels = 2
        self.audio_format = 'AAC'

        # Video properties
        self.video_bit_rate = self.bit_rate - self.bit_rate_buffer - self.audio_bit_rate
        self.video_bit_depth = 8
        self.video_resolution = 1080 * 1920
        self.video_format = 'AVC'
        self.video_level = 4.1

        self.args = '--target 1080p=7550 --mp4 --quick --max-height 1080 --max-width 1920 --abr --audio-width main=stereo -H ab=384'
        super().__init__(source, target, info, finished, notifications, config)
