#!/bin/bash
set -ex

### CONFIGURE ##################################################################
cat << EOF > /opt/rclone.conf
[drive]
type = drive
scope = drive
service_account_credentials = REMOVED

[crypt]
type = crypt
remote = drive:/data
filename_encryption = standard
directory_name_encryption = true
password = REMOVED
password2 = REMOVED
EOF

# MP4 Config
#echo '' > /opt/mp4.conf
