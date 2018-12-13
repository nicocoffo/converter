import os
import re
from string import Template
from uuid import uuid4
from jackhammer import Job

from transcoder.jobs.remove import Remove
from transcoder.jobs.merge import Merge
from transcoder.jobs.convert import Convert

SPLIT_SH="""#!/bin/bash
set -ex

export PATH="$$PATH:/opt/rclone"
export LC_ALL=C.UTF-8
export LANG=C.UTF-8

rm -rf /tmp/jackhammer*
mkdir -p "$WORK_DIR"
rclone $RCLONE_ARGS copy "$RCLONE_SOURCE" "$WORK_DIR"
rclone $RCLONE_ARGS mkdir "$RCLONE_TARGET"

pip3 -q install subliminal
subliminal download -l $SUB_LANG -e utf-8 -f --directory "$WORK_DIR" "$ORIGINAL_FILE"
SUB=$$(find "$WORK_DIR" -type f -name *.srt)
if [ -n "$$SUB" ]
then
  mv "$$SUB" "$SUB_BASE.$SUB_LANG.srt"
  rclone $RCLONE_ARGS copy "$SUB_BASE.$SUB_LANG.srt" "$RCLONE_TARGET"
fi

SUBS=$$(ffprobe -v error -show_entries stream=index:stream_tags=language:stream=codec_name -select_streams s -of compact=p=0:nk=1 "$ORIGINAL_FILE" | grep -v pgs || true)
for L in $$(echo "$$SUBS" | cut -d '|' -f 3 | sort | uniq)
do
  NUM=1
  for SUB in $$(echo "$$SUBS" | grep $$L | cut -d '|' -f 1)
  do
    while :
    do
      if [ "$$NUM" -eq 1 ]; then
        OUT="$SUB_BASE.$$L.srt"
      else
        OUT="$SUB_BASE.$$L$$NUM.srt"
      fi
      NUM=$$((NUM+1))
      [ -f $$OUT ] || break
    done
    ffmpeg -i "$ORIGINAL_FILE" -hide_banner -loglevel fatal -map 0:$$SUB "$$OUT"
    rclone $RCLONE_ARGS copy "$$OUT" "$RCLONE_TARGET"
    rm "$$OUT"
  done
done

ffmpeg -i "$ORIGINAL_FILE" -map_metadata -1 -reset_timestamps 1 -c copy \
        -map 0 -segment_time "$SEG_LEN" -f segment "$PATTERN"
rclone $RCLONE_ARGS --exclude "$ORIGINAL_FILENAME" copy "$WORK_DIR" "$RCLONE_TARGET"
echo "Completed $$(ls "$WORK_DIR" | grep -v ".srt$$" | grep -v "$ORIGINAL_FILENAME" | wc -l)"
"""

class Split(Job):
    """
    Job to split a file into segments.
    It then generates jobs to convert and merge the resulting segments
    into a variety of formats.
    """

    def __init__(self, encodings, config):
        super().__init__(config)
        self.encodings = encodings
        assert len(self.encodings) > 0, "Split requires at least one encoding"

        # Fix bases of paths
        self.source = encodings[0].source.replace(
                config['mountLocal'], config['mountRemote'], 1)
        self.target = encodings[0].target.replace(
                config['mountLocal'], config['mountRemote'], 1)

        # Values
        self.tmp_dir = os.path.join(config['tmpDir'], str(uuid4()))
        source_file = os.path.basename(self.source)
        _, ext = os.path.splitext(source_file)
        self.pattern = config['pattern'] + ext
        sub_base = os.path.splitext(source_file)[0]

        # Set command and name
        enc = "-".join([e.name for e in encodings])
        self.name = "split:%s:%s" % (source_file, enc)
        self.script = Template(SPLIT_SH).substitute(
            WORK_DIR=self.work_dir,
            RCLONE_ARGS=config["rcloneArgs"],
            RCLONE_SOURCE=self.source,
            RCLONE_TARGET=self.tmp_dir,
            ORIGINAL_FILE=os.path.join(self.work_dir, source_file),
            ORIGINAL_FILENAME=source_file,
            PATTERN=os.path.join(self.work_dir, self.pattern),
            SUB_LANG=encodings[0].lang,
            SUB_BASE=os.path.join(self.work_dir, sub_base),
            SEG_LEN=encodings[0].calculate_segment_length()
        )

    def success(self):
        # Find a complete line, with segment count
        num = None
        for line in self.stdout.split("\n"):
            match = re.search("Completed (\d*)", line)
            if match:
                num = int(match.group(1))
                break
        if not num:
            return self.failure()

        # Setup the transcode jobs
        jobs = []
        merges = []
        for encoding in self.encodings:
            prereqs = []
            for i in range(num):
                src = self.tmp_dir + "/" + (self.pattern % i)
                prereqs.append(Convert(src, encoding, self.config))
            jobs.extend(prereqs)
            merges.append(Merge(self.tmp_dir, encoding, self.config, prereqs))
        jobs.extend(merges)

        # Delete the temporary directory
        jobs.append(Remove(self.tmp_dir, self.config, merges))
        return jobs

    def failure(self):
        """
        Send a notification for the job failure and
        schedule a cleanup of the temporary directory.
        """
        for enc in self.encodings:
            enc.failure(self)
        return [Remove(self.tmp_dir, self.config)]
