import os
from string import Template
from jackhammer import Job

REMUX_SH="""#!/bin/bash
set -ex

export PATH="$$PATH:/opt/rclone"
export LC_ALL=C.UTF-8
export LANG=C.UTF-8

rm -rf "$WORK_DIR"
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

SUBS=$$(ffprobe -v error -show_entries stream=index:stream_tags=language -select_streams s -of compact=p=0:nk=1 "$ORIGINAL_FILE")
for L in $$(echo "$$SUBS" | cut -d '|' -f 2 | sort | uniq)
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
  done
done

ffmpeg -i "$ORIGINAL_FILE" $FFMPEG_ARGS "$CONVERTED_FILE"
rclone $RCLONE_ARGS copy "$CONVERTED_FILE" "$RCLONE_TARGET"

rm -rf "$WORK_DIR" """

class Remux(Job):
    """
    Job to remux a file using FFMPEG.
    Also extracts and organizes subtitles.
    """

    def __init__(self, encoding, config):
        super().__init__(config)
        self.encoding = encoding
        self.priority = 4

        # Fix bases of paths
        self.source = encoding.source.replace(
                config['mountLocal'], config['mountRemote'], 1)
        self.target = encoding.target.replace(
                config['mountLocal'], config['mountRemote'], 1)

        # Determine various filenames
        source_file = os.path.basename(self.source)
        target_file = os.path.basename(self.target)
        sub_base = os.path.splitext(target_file)[0]

        # Fill in the template
        self.name = "remux:%s" % target_file
        self.script = Template(REMUX_SH).substitute(
            WORK_DIR=self.work_dir,
            RCLONE_ARGS=config["rcloneArgs"],
            FFMPEG_ARGS=encoding.get_remux_args(),
            RCLONE_SOURCE=self.source,
            RCLONE_TARGET=os.path.dirname(self.target),
            ORIGINAL_FILE=os.path.join(self.work_dir, source_file),
            CONVERTED_FILE=os.path.join(self.work_dir, target_file),
            SUB_LANG=encoding.lang,
            SUB_BASE=os.path.join(self.work_dir, sub_base)
        )

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
