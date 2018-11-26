import yaml

NOTIFICATIONS = { }

WATCHER = {
        'loopDelay': 1200,
        'backupPath': '/state/finished.gz',
        'root': '/data/original',
        'port': 9234
        }

SCHEDULER = {
        'loopDelay': 2,
        'joinTimeout': 240,
        'readyTimeout': 20,
        'maxWorkers': 8,
        'minWorkerDuration': 60
        }

CLOUD = {
        'session' : {
            'username': 'root',
            'keyBits': 2048
            }
        }

TRANSCODER = {
        'src': '/data/original',
        'dst': '/data/optimised',
        'job': {
            'pattern': 'output%03d.original',
            'tmpDir': 'remote:/transcoding',
            'mountLocal': '/data',
            'mountRemote': 'remote:',
            'rcloneArgs': '--config /opt/rclone.conf',
            'maxAttempts': 3
            }
        }

DEFAULT_CONFIG = {
        'logFormat': '%(asctime)s - %(name)-12s - %(levelname)-5s - %(message)s',
        'watcher': WATCHER,
        'scheduler': SCHEDULER,
        'notifications': NOTIFICATIONS,
        'cloud': CLOUD,
        'transcoder': TRANSCODER
        }

def merge(source, destination):
    for key, value in source.items():
        if isinstance(value, dict):
            node = destination.setdefault(key, {})
            merge(value, node)
        else:
            destination[key] = value
    return destination

def parse_config(path):
    with open(path, 'r') as ymlfile:
        return merge(yaml.load(ymlfile), DEFAULT_CONFIG)
