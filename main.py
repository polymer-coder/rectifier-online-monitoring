import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import requests
#from dotenv import load_dotenv
import datetime

sender_email = "stephen.garret.jogie@gmail.com"
receiver_email = "stephen.garret.jogie@ansamcal.com"
username = "stephen.garret.jogie@gmail.com"
password = input(f"enter password for {username}: ")
smtp_server = "smtp.gmail.com"
smtp_port = 465

class Timestamp:
    def __init__(self, unix: int, datetime: str):
        self.unix_time = unix
        self.datetime = datetime

class Rectifier:
    def __init__(self):
        self.total_load = 0
        self.sixteen_load = 0
        self.twenty_four_load = 0



def get_time_from_api() -> Timestamp:
    url = r"http://worldtimeapi.org/api/timezone/America/Port_of_Spain"
    response = requests.get(url).json()
    return Timestamp(response["unixtime"], response["datetime"])

def send_email(subject:str,message:str) -> None:
    msg = MIMEMultipart()
    msg["From"] = sender_email
    msg["To"] = receiver_email
    msg["Subject"] = subject
    msg.attach(MIMEText(message, "plain"))
    context = ssl.create_default_context()

    try:
        with smtplib.SMTP_SSL(smtp_server, smtp_port, context=context) as smtp:
            smtp.login(username, password)

            # Send the email
            smtp.send_message(msg)
            print(f"{datetime.datetime.fromtimestamp(get_time_from_api().unix_time)} Email sent successfully.")

    except Exception as e:
        print(f"Error: {e}")
    return


def rectifier_no_load_alert(rectifier : Rectifier) -> None:
    timestamp = datetime.datetime.fromtimestamp(get_time_from_api().unix_time)
    rectifier_trip_message = f"Rectifer No Load Condition Detected {timestamp} \nTotal Load: {rectifier.total_load}kA \n16kA Rectifier Load: {rectifier.sixteen_load}kA \n24kA Rectifier Load: {rectifier.twenty_four_load}kA"
    subject = subject = f"[Rectifier Trip]- {timestamp}"
    send_email(subject, rectifier_trip_message)
    return

#rectifier_trip_message = f"Rectifer No Load Condition Detected {datetime.datetime.fromtimestamp(get_time_from_api().unix_time)} \nTotal Load: {total_load}kA \n16kA Rectifier Load: {sixteen_load}kA \n24kA Rectifier Load: {twenty_four_load}kA"
#rectifier_restart_message = f"Rectifer Restart Detected {datetime.datetime.fromtimestamp(get_time_from_api().unix_time)} \nTotal Load: {total_load}kA \n16kA Rectifier Load: {sixteen_load}kA \n24kA Rectifier Load: {twenty_four_load}kA"

def test_thing() -> None:
    rect_1 = Rectifier() 
    rect_1.total_load = 0.5 #test val
    rectifier_no_load_alert(rect_1)
    return

test_thing()