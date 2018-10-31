#!/bin/bash
set -ex

# Install tools & ffmpeg
DEBIAN_FRONTEND=noninteractive apt-get -y -qq update
DEBIAN_FRONTEND=noninteractive apt-get -y -qq install unzip ffmpeg python3-pip

# Install rclone
cd /opt
curl -O https://downloads.rclone.org/rclone-current-linux-amd64.zip
unzip rclone-current-linux-amd64.zip
rm rclone-current-linux-amd64.zip
mv rclone-*-linux-amd64 rclone

# Install mp4_automator
pip3 install requests
pip3 install requests[security]
pip3 install requests-cache
pip3 install babelfish
pip3 install "guessit<2"
pip3 install stevedore==1.19.1
pip3 install "subliminal<2"
pip3 install qtfaststart
git clone https://github.com/mdhiggins/sickbeard_mp4_automator.git
