from string import Template
from jackhammer import Job

REMOVE_SH="""#!/bin/bash
set -ex

export PATH="$$PATH:/opt/rclone"
export LC_ALL=C.UTF-8
export LANG=C.UTF-8

rclone $RCLONE_ARGS purge $DST || true
"""

class Remove(Job):
    """
    Remove a directory or file.
    """

    def __init__(self, dst, config, prereqs=[]):
        super().__init__(config, prereqs=prereqs)
        self.dst = dst
        self.priority = 0

        # Fill in the template
        self.name = "remove:%s" % self.dst
        self.script = Template(REMOVE_SH).substitute(
            RCLONE_ARGS=config["rcloneArgs"],
            DST=self.dst
        )
