import time
import string
import traceback
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from plexapi.myplex import MyPlexAccount

ExceptionTemplate = string.Template(
"""Server encountered an exception during execution:
  Message: $msg
  Trace:
$trace""")

def plex_scan(config):
    account = MyPlexAccount(config['username'], config['password'])
    plex = account.resource(config['server']).connect()
    if len(plex.sessions()) == 0:
        plex.library.refresh()

MAX_LEN = 500

class Notifications:

    def __init__(self, config):
        self.email = config['email']
        self.plex = config['plex']

    def __send__(self, subject, body):
        msg = MIMEMultipart()
        msg['From'] = self.email['from']
        msg['To'] = self.email['to']
        msg['Subject'] = "Replicant: " + subject
        msg.attach(MIMEText(body, 'plain'))
    
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(self.email['username'], self.email['password'])
        server.sendmail(self.email['from'], self.email['to'], msg.as_string())
        server.quit()

    def send(self, subject, body):
        rep = 0
        while len(body) > MAX_LEN * rep:
            s = subject if rep == 0 else subject + ' '  + str(rep + 1)
            b = body[MAX_LEN * rep:MAX_LEN * (rep + 1)]
            self.__send__(s, b)
            rep += 1

    def send_exception(self, e):
        subject = "Server Exception"
        msg = ExceptionTemplate.substitute(
            msg=str(e),
            trace=''.join(traceback.format_tb(e.__traceback__)))
        self.send(subject, msg)

    def update_services(self, target):
        try:
            plex_scan(self.plex)
            return "Plex updated"
        except Exception as e:
            return e.msg
