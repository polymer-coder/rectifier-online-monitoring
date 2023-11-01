import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import requests
from dotenv import load_dotenv

class Timestamp:
    def __init__(self, unix:int, datetime:str):
        self.unix_time = unix
        self.datetime = datetime
 
def get_time_from_api() -> Timestamp:
    url = r"http://worldtimeapi.org/api/timezone/America/Port_of_Spain"
    response = requests.get(url).json()
    return Timestamp(response['unixtime'],response['datetime'])


load_dotenv()

password = os.getenv('GMAIL_APP_PASSWORD')

sender_email = 'developer.polymer@gmail.com'
receiver_email = 'simeon.ramjit@ansamcal.com'
subject = f'[Rectifier Trip]- {get_time_from_api().datetime}'
message = 'This is the body of the email.'


smtp_server = 'smtp.gmail.com'
smtp_port = 465
username = 'developer.polymer@gmail.com'
password = os.environ.get("GMAIL_APP_PASSWORD")
print(password)

msg = MIMEMultipart()
msg['From'] = sender_email
msg['To'] = receiver_email
msg['Subject'] = subject

msg.attach(MIMEText(message, 'plain'))

context = ssl.create_default_context()

try:
    with smtplib.SMTP_SSL(smtp_server, smtp_port, context=context) as smtp:
        smtp.login(username, password)
        
        # Send the email
        smtp.send_message(msg)
        print('Email sent successfully.')

except Exception as e:
    print(f'Error: {e}')

