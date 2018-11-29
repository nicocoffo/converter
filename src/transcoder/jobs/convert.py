import os
from string import Template
from jackhammer import Job, JobState

CONVERT_SH="""#!/bin/bash
set -ex

export PATH="$$PATH:/opt/rclone/:/opt/video_transcoding/bin/"
export LC_ALL=C.UTF-8
export LANG=C.UTF-8

rm -rf "$WORK_DIR"
mkdir -p "$WORK_DIR"
rclone $RCLONE_ARGS mkdir "$RCLONE_TARGET"

rclone $RCLONE_ARGS copy "$RCLONE_SOURCE" "$WORK_DIR"
transcode-video $FFMPEG_ARGS "$ORIGINAL_FILE" -o "$CONVERTED_FILE"
rclone $RCLONE_ARGS copy "$CONVERTED_FILE" "$RCLONE_TARGET"

rm -rf "$WORK_DIR" """

class Convert(Job):
    """
    Convert a media file to a quality.

    Args:
        source: rclone path to the source file.
        encoding: Encoding object, describing the desired output.
        config: General job configuration.
        prereqs: Prerequisits for this job.
    """

    def __init__(self, source, encoding, config, prereqs=[]):
        super().__init__(config, prereqs=prereqs)
        self.source = source
        self.encoding = encoding
        self.priority = 8

        # Determine various filenames
        source_file = os.path.basename(source)
        target_file = encoding.transform_filename(source_file)

        # Fill in the template
        self.name = "convert:%s" % target_file
        self.script = Template(CONVERT_SH).substitute(
            WORK_DIR=self.work_dir,
            RCLONE_ARGS=self.config["rcloneArgs"],
            FFMPEG_ARGS=encoding.get_args(),
            RCLONE_SOURCE=self.source,
            RCLONE_TARGET=os.path.dirname(self.source),
            ORIGINAL_FILE=os.path.join(self.work_dir, source_file),
            CONVERTED_FILE=os.path.join(self.work_dir, target_file),
        )
