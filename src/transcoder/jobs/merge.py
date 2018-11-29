import os
from string import Template
from jackhammer import Job, JobState

MERGE_SH="""#!/bin/bash
set -ex

export PATH="$$PATH:/opt/rclone"
export LC_ALL=C.UTF-8
export LANG=C.UTF-8

rm -rf "$WORK_DIR"
mkdir -p "$WORK_DIR"
rclone $RCLONE_ARGS mkdir "$RCLONE_TARGET"

rclone $RCLONE_ARGS copy --include *.srt "$RCLONE_SOURCE" "$WORK_DIR"
for SUBFILE in "$WORK_DIR"/*.srt
do
  E="$${SUBFILE##*.}"
  REST="$${SUBFILE%.*}"
  L="$${REST##*.}"
  mv "$$SUBFILE" "$SUB_BASE.$$L.$$E"
  rclone $RCLONE_ARGS copy "$SUB_BASE.$$L.$$E" "$RCLONE_TARGET"
done

rclone $RCLONE_ARGS copy --include $PATTERN "$RCLONE_SOURCE" "$WORK_DIR"
ffmpeg -f concat -safe 0 -i \
        <(for f in "$WORK_DIR"/$PATTERN; do echo "file '$$f'"; done) \
        -c copy -movflags faststart -map 0 -metadata:s:a:0 language="$AUDIO_LANG" \
        "$CONVERTED_FILE"
rclone $RCLONE_ARGS copy "$CONVERTED_FILE" "$RCLONE_TARGET"

rm -rf "$WORK_DIR" """

class Merge(Job):
    """
    Merge a series of video segments.
    """

    def __init__(self, source, encoding, config, prereqs=[]):
        super().__init__(config, prereqs=prereqs)
        # Args
        self.source = source
        self.encoding = encoding
        self.priority = 5

        # Fix bases of paths
        self.target = encoding.target.replace(
                config['mountLocal'], config['mountRemote'], 1)

        # Determine various filenames
        target_file = os.path.basename(self.target)
        sub_base = os.path.splitext(target_file)[0]
        pattern = "*." + encoding.name + "." + encoding.extension

        # Fill in the template
        self.name = "merge:%s" % target_file
        self.script = Template(MERGE_SH).substitute(
            WORK_DIR=self.work_dir,
            RCLONE_ARGS=config["rcloneArgs"],
            RCLONE_SOURCE=self.source,
            RCLONE_TARGET=os.path.dirname(self.target),
            CONVERTED_FILE=os.path.join(self.work_dir, target_file),
            AUDIO_LANG=encoding.info.lang,
            SUB_BASE=os.path.join(self.work_dir, sub_base),
            PATTERN=pattern
        )

    def prepare(self):
        """
        Fail this job if any prereqs failed. 
        """
        super().prepare()
        if self.state != JobState.Ready:
            return

        for job in self.prereqs:
            if job.state != JobState.Success:
                self.state = JobState.Failure
                return

    def success(self):
        """
        Send a success notification.
        """
        self.encoding.success(self)
        return []

    def failure(self):
        """
        Send a failure notification.
        """
        self.encoding.failure(self)
        return []
