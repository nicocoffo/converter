import string
import traceback
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

ExceptionTemplate = string.Template(
"""Server encountered an exception during execution:
  Message: $msg
  Trace:
$trace""")

class Notifications:
    def __init__(self, config):
        self.email = config['email']

    def send(self, subject, body):
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

    def send_exception(self, e):
        subject = "Server Exception"
        msg = ExceptionTemplate.substitute(
            msg=str(e),
            trace=''.join(traceback.format_tb(e.__traceback__)))
        self.send(subject, msg)

    def update_services(self, target):
        return "No services to update"

#def plex_scan(config):
#    account = MyPlexAccount(config['username'], config['password'])
#    plex = account.resource(config['server']).connect()
#    plex.library.refresh()
#
#def trigger_plex_scan(job):
#    if not 'plex' in job.config:
#        return
#    #Timer(20, plex_scan, args=[job.config['plex']])
#    plex_scan(job.config['plex'])
#def job_failure_notification(job):
#    if not 'email' in job.config:
#        return
#
#    subject = "Converter - Failed Job: %s" % job.name
#    msg = "Issue encountered in job: %s" % job
#    msg += "\nSTDOUT:\n%s" % job.stdout
#    msg += "\nSTDERR:\n%s" % job.stderr
#    send_email(subject, msg, job.config['email'])
#
#def job_success_notification(job):
#    # TODO: Timing info, optional message
#    if not 'email' in job.config:
#        return
#
#    subject = "Converter - Successful Job: %s" % job.name
#    msg = "Job completed: %s" % job
#    send_email(subject, msg, job.config['email'])
#from time import sleep
#from plexapi.myplex import MyPlexAccount
#from threading import Timer
