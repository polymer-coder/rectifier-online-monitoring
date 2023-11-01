import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import requests
from dotenv import load_dotenv
import datetime


class Timestamp:
    def __init__(self, unix: int, datetime: str):
        self.unix_time = unix
        self.datetime = datetime


def get_time_from_api() -> Timestamp:
    url = r"http://worldtimeapi.org/api/timezone/America/Port_of_Spain"
    response = requests.get(url).json()
    return Timestamp(response["unixtime"], response["datetime"])


load_dotenv()
total_load = 0
sixteen_load = 0
twenty_four_load = 0
password = os.getenv("GMAIL_APP_PASSWORD")
timestamp = datetime.datetime.fromtimestamp(get_time_from_api().unix_time)

sender_email = "developer.polymer@gmail.com"
receiver_email = "simeon.ramjit@ansamcal.com"
subject = f"[Rectifier Trip]- {timestamp}"
rectifier_trip_message = f"Rectifer Trip Detected {datetime.datetime.fromtimestamp(get_time_from_api().unix_time)} \nTotal Load: {total_load}kA \n16kA Rectifier Load: {sixteen_load}kA \n24kA Rectifier Load: {twenty_four_load}kA"
rectifier_restart_message = f"Rectifer Restart Detected {datetime.datetime.fromtimestamp(get_time_from_api().unix_time)} \nTotal Load: {total_load}kA \n16kA Rectifier Load: {sixteen_load}kA \n24kA Rectifier Load: {twenty_four_load}kA"


smtp_server = "smtp.gmail.com"
smtp_port = 465
username = "developer.polymer@gmail.com"
password = os.environ.get("GMAIL_APP_PASSWORD")
print(password)

msg = MIMEMultipart()
msg["From"] = sender_email
msg["To"] = receiver_email
msg["Subject"] = subject

msg.attach(MIMEText(rectifier_trip_message, "plain"))

context = ssl.create_default_context()

try:
    with smtplib.SMTP_SSL(smtp_server, smtp_port, context=context) as smtp:
        smtp.login(username, password)

        # Send the email
        smtp.send_message(msg)
        print(f"{datetime.datetime.fromtimestamp(get_time_from_api().unix_time)} Email sent successfully.")

except Exception as e:
    print(f"Error: {e}")
