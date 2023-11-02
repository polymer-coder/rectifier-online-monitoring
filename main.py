import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import requests
from dotenv import load_dotenv
import datetime
import xml.etree.ElementTree as ET
from interval_timer import IntervalTimer

#TODO: 
# 1. Log the readings to a database (firebase firestore)
#       -> Table with cols for the following:
#           --> Timestamp (primary key)
#           --> 16kA load value
#           --> 24kA load value
#           --> total load value
#           --> 251 (brine feed flow rate) (m^3 per hour)
#           --> 223 (Chlorine header pressure)  
#           --> Moisture Analyzer Value (Vppm)
#
# 2. Store a value each minute to have as a reference to include in the email alerts
#       
# 3. Adjust alarm logic to only email for a dropoff if sustained 45 seconds of below threshold only
#       -> Can add an alert_prepare flag boolean value to the rectifier class
#       -> Can also add a int value for a unix timestamp for when above flag initially raised
#       -> When the first instance of below threshold is detected. Raise flag and log unix timestamp
#       -> Keep checking until either the following happens:
#           -->CASE 1: still below threshold when (current_time - logged timestamp >= 45) AND flag still raised
#               ---> We would then send the email and reset the flag and timestamp value
#           -->CASE 2: no longer below threshold within 45 second interval
#               ---> We then reset the flag and timestamp without sending any email

load_dotenv()

#==============================================================================
#===========================GLOBAL VARIABLES===================================
#==============================================================================
sender_email = os.environ.get("SENDER_EMAIL")
receiver_email = os.environ.get("RECEIPIENT_EMAILS")
username = os.environ.get("MAIL_USERNAME")
password = os.environ.get("GMAIL_APP_PASSWORD")

smtp_server = os.environ.get("SMTP_SERVER")
smtp_port = os.environ.get("SMTP_PORT")

ecograph_url = os.environ.get("ECOGRAPH_URL")

sixteen_load = 999
twenty_four_load= 999
counter = 0
#==============================================================================
#===========================GLOBAL VARIABLES END===============================
#==============================================================================

class Timestamp:
    def __init__(self, unix: int, datetime: str):
        self.unix_time = unix
        self.datetime = datetime

class Rectifier:
    def __init__(self):
        self.total_load = 0
        self.sixteen_load = 0
        self.twenty_four_load = 0
        self.no_load_state = False #will use this to check switch between states

rect_1 = Rectifier() 

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

def update_rect_values(rect : Rectifier, val_16k : float, val_24k : float) -> None:
    temp = rect.no_load_state
    rect.total_load = round(val_16k + val_24k,2)
    # print(rect.total_load) # test line
    rect.sixteen_load = round(val_16k,2)
    rect.twenty_four_load = round(val_24k,2)

    if (rect.total_load > 2.00):
        rect.no_load_state = False
    else:
        if (rect.total_load < 1.00):
            rect.no_load_state = True
    
    if(rect.no_load_state != temp):
        #This is a change in state and would warrant an email alert
        if (rect.no_load_state == True):
            rectifier_no_load_alert(rect)
        else:
            rectifier_restart_alert(rect)

    return

def rectifier_no_load_alert(rectifier : Rectifier) -> None:
    timestamp = datetime.datetime.fromtimestamp(get_time_from_api().unix_time)
    rectifier_trip_message = f"Rectifer No Load Condition Detected {timestamp} \nTotal Load: {rectifier.total_load}kA \n16kA Rectifier Load: {rectifier.sixteen_load}kA \n24kA Rectifier Load: {rectifier.twenty_four_load}kA"
    subject = subject = f"[Rectifier No Load Condition]- {timestamp}"
    send_email(subject, rectifier_trip_message)
    return

def rectifier_restart_alert(rectifier : Rectifier) -> None:
    timestamp = datetime.datetime.fromtimestamp(get_time_from_api().unix_time)
    rectifier_restart_message = f"Rectifer Restart Detected {timestamp} \nTotal Load: {rectifier.total_load}kA \n16kA Rectifier Load: {rectifier.sixteen_load}kA \n24kA Rectifier Load: {rectifier.twenty_four_load}kA"
    subject = subject = f"[Rectifier Restart]- {timestamp}"
    send_email(subject, rectifier_restart_message)
    return



def ecograph_poll_check(counter) -> None:
    x = requests.get(ecograph_url)
    tree = ET.fromstring(x.text)

    twenty_four_load = tree[8][0].text # 24kA Load Value
    sixteen_load =  tree[9][0].text # 16kA Load Value
    print(f'{counter} - 16kA - {sixteen_load} | 24kA - {twenty_four_load}')
    update_rect_values(rect_1, float(sixteen_load), float(twenty_four_load))

    return



for interval in IntervalTimer(1):
    counter+=1
    ecograph_poll_check(counter)
