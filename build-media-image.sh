#!/bin/bash
set -ex

# Install tools & ffmpeg
DEBIAN_FRONTEND=noninteractive apt-get -y -qq clean
rm -rf /var/lib/apt/lists/*
DEBIAN_FRONTEND=noninteractive apt-get -y -qq clean
DEBIAN_FRONTEND=noninteractive apt-get -y -qq update
DEBIAN_FRONTEND=noninteractive add-apt-repository -y -n ppa:stebbins/handbrake-releases
DEBIAN_FRONTEND=noninteractive apt-get -y -qq install unzip ffmpeg handbrake-cli ruby mp4v2-utils python3 python3-pip

# Install rclone
cd /opt
curl -O https://downloads.rclone.org/rclone-current-linux-amd64.zip
unzip rclone-current-linux-amd64.zip
rm rclone-current-linux-amd64.zip
mv rclone-*-linux-amd64 rclone

# Get transcoding bin
git clone https://github.com/donmelton/video_transcoding.git /opt/video_transcoding
sed -i -e 's/ruby -W/ruby/g' /opt/video_transcoding/bin/transcode-video

# Get python dependencies
pip3 install subliminal
