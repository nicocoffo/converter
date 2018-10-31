#!/bin/bash
set -ex

### CONVERT ####################################################################
FILE="$1"
SRC="$2"
DST="$3"

# Download
echo "Downloading $SRC/$FILE"
/opt/rclone/rclone --config /opt/rclone.conf copy "crypt:$SRC/$FILE" /tmp/.

# Convert
python3 /opt/sickbeard_mp4_automator/manual.py -ai "/tmp/$FILE"

NEW_FILE=`find /tmp -name "*.mp4" | head -n 1`

# Upload
echo "Upload $NEW_FILE"
/opt/rclone/rclone --config /opt/rclone.conf mkdir "crypt:$DST/"
/opt/rclone/rclone --config /opt/rclone.conf copy "$NEW_FILE" "crypt:$DST/"
