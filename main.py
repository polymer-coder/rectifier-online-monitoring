import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import requests
#from dotenv import load_dotenv
import datetime

#==============================================================================
#===========================GLOBAL VARIABLES===================================
#==============================================================================
sender_email = "stephen.garret.jogie@gmail.com"
receiver_email = r"stephen.garret.jogie@ansamcal.com;simeon.ramjit@ansamcal.com"
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
        self.no_load_state = False #will use this to check switch between states


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



def test_thing() -> None:
    rect_1 = Rectifier() 
    update_rect_values(rect_1, 2.5,2) #test val
    #rectifier_no_load_alert(rect_1)
    update_rect_values(rect_1, 2.5,2.5)
    update_rect_values(rect_1, 0.5,1)
    update_rect_values(rect_1, 0.5,0)
    update_rect_values(rect_1, 1.5,0.0)
    update_rect_values(rect_1, 1.6,0.41)
    update_rect_values(rect_1, 2.5,2)
    #rectifier_restart_alert(rect_1)
    
    return

test_thing()