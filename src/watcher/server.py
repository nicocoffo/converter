from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread
import logging
import json
import os

logger = logging.getLogger("replicant.watcher")


def sonarr_extract(j):
    """
    Convert a sonarr webhook into the expected format.
    """
    if not 'eventType' in j or j['eventType'] != 'Download':
        return None
    if not 'episodes' in j:
        return None
    path = os.path.join(j['series']['path'], j['episodeFile']['relativePath'])
    return { 'path': path }

def radarr_extract(j):
    """
    Convert a radarr webhook into the expected format.
    """
    if not 'eventType' in j or j['eventType'] != 'Download':
        return None
    if not 'movieFile' in j:
        return None
    path = j['movieFile']['path']
    return { 'path': path }

def run_server(port, queue):
    class Server(BaseHTTPRequestHandler):
        def _set_response(self):
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
    
        def do_GET(self):
            self._set_response()
    
        def do_POST(self):
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            logger.info("Post: %s", post_data)
            try:
                j = json.loads(post_data)
                sonarr = sonarr_extract(j)
                if sonarr:
                    queue.put(sonarr)
                else:
                    queue.put(j)
            except:
                logging.error("Bad request")
            self._set_response()

    httpd = HTTPServer(('', port), Server)
    Thread(target=httpd.serve_forever).start()
    return httpd

def stop_server(server):
    Thread(target=server.shutdown, daemon=True).start()
