from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread
import logging
import json

logger = logging.getLogger("replicant.watcher")


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
            try:
                queue.put(json.loads(post_data))
            except:
                logging.error("Bad request")
            self._set_response()

    httpd = HTTPServer(('', port), Server)
    Thread(target=httpd.serve_forever).start()
    return httpd

def stop_server(server):
    Thread(target=server.shutdown, daemon=True).start()
