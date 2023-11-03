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
import time

#TODO: 
# 1. Log the readings to a database (firebase firestore) 
#       -> Need to use the server side time stamp for fire store
#       -> Table with cols for the following:
#           --> Timestamp 
#           --> 16kA load value
#           --> 24kA load value
#           --> total load value
#           --> 251 (brine feed flow rate) (m^3 per hour)
#           --> 223 (Chlorine header pressure)  
#           --> Moisture Analyzer Value (Vppm)
#
# 2. Store a value each minute to have as a reference to include in the email alerts
#       STATUS -> Simulated and tested to be impeccable
#
# 3. Adjust alarm logic to only email for a dropoff if sustained 45 seconds of below threshold only
#       STATUS -> Implemented and tested. Appears to work for the test case seen in the test branch
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

#min_ref_time = 0
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
        self.no_load_prepare_alert = False
        self.restart_prepare_alert = False
        self.no_load_alert_assert_time = 0 #for unix timestamp, default of 0
        self.restart_alert_assert_time = 0 
        self.min_ref_sixteen_load = 0
        self.min_ref_twenty_four_load= 0
        self.min_ref_total_load = 0
        self.min_ref_time = 0
    
    def print_alert_flags(self):
        #purely for testing, can be commented out/removed later once functionality verified
        print("CURRENT TOTAL LOAD in kA : " + str(self.total_load))
        print("NO LOAD FLAG : " + str(self.no_load_prepare_alert))
        print("NO LOAD ASSERT TIME : " + str(self.no_load_alert_assert_time))
        print("RESTART FLAG : " + str(self.restart_prepare_alert))
        print("RESTART ASSERT TIME : " + str(self.restart_alert_assert_time))
        print("=====================================")
        print("=====================================")
        return
    
    def print_min_references(self):
        print("MINUTE REFERENCE TOTAL LOAD : " + str(self.min_ref_total_load))
        print("MINUTE REFERENCE 16kA RECTIFIER LOAD : " + str(self.min_ref_sixteen_load))
        print("MINUTE REFERENCE 24kA RECTIFIER LOAD : " + str(self.min_ref_twenty_four_load))
        print("MIN REF TIME : " + str(self.min_ref_time))
        print("=====================================")
        print("=====================================")
        return

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
        if ((rect.restart_prepare_alert == True) 
            and (rect.restart_alert_assert_time != 0)
            and (get_time_from_api().unix_time - rect.restart_alert_assert_time > 45)):
            rectifier_restart_alert(rect)
            rect.restart_prepare_alert = False
            rect.restart_alert_assert_time = 0 #reset flags for timer so as to not spam emails 
            print("SENT RESTART ALERT")

        
    else:
        if (rect.total_load < 1.00):
            rect.no_load_state = True
            if ((rect.no_load_prepare_alert == True) 
                and (rect.no_load_alert_assert_time != 0)
                and (get_time_from_api().unix_time - rect.no_load_alert_assert_time > 45)):
                rectifier_no_load_alert(rect)
                rect.no_load_prepare_alert = False
                rect.no_load_alert_assert_time = 0 #reset flags for timer so as to not spam emails
                print("SENT ALERT NO LOAD")
    
    if(rect.no_load_state != temp):
        #This is a change in state and would warrant a flag being raised
        if (rect.no_load_state == True):
            #rectifier_no_load_alert(rect)
            #NOTE : To deal with the edge case discussed. Minor change here to quickly fix issue
            # Basically, only assert the prepare alert flag when the other prepare alert flag is not asserted
            # This would get rid of the sub 45 second state change during stead state resulting in 'erroneous' emails
            rect.no_load_prepare_alert = not(rect.restart_prepare_alert) #this solves our problems in life
            rect.no_load_alert_assert_time = ((get_time_from_api().unix_time)*rect.no_load_prepare_alert)
            rect.restart_alert_assert_time = 0 #to reset flag in case
            rect.restart_prepare_alert = False
        else:
            #rectifier_restart_alert(rect)
            rect.restart_prepare_alert = not(rect.no_load_prepare_alert)
            rect.restart_alert_assert_time = ((get_time_from_api().unix_time)*rect.restart_prepare_alert)
            rect.no_load_prepare_alert = False
            rect.no_load_alert_assert_time = 0

    return

def rectifier_no_load_alert(rectifier : Rectifier) -> None:
    timestamp = datetime.datetime.fromtimestamp(get_time_from_api().unix_time)
    rectifier_trip_message = f"Rectifer No Load Condition Detected {timestamp} \nTotal Load: {rectifier.total_load}kA \n16kA Rectifier Load: {rectifier.sixteen_load}kA \n24kA Rectifier Load: {rectifier.twenty_four_load}kA \n"
    rectifier_trip_message = rectifier_trip_message + f"\n \n Previous Minute Stored Reading: \n \t Total Load : {rectifier.min_ref_total_load}kA"
    rectifier_trip_message = rectifier_trip_message + f"\n \t 16kA Rectifier Load: {rectifier.min_ref_sixteen_load}kA \n \t 24kA Rectifier Load: {rectifier.min_ref_twenty_four_load}"
    subject = subject = f"[Rectifier No Load Condition]- {timestamp}"
    send_email(subject, rectifier_trip_message) 
    #print(rectifier_trip_message)
    return

def rectifier_restart_alert(rectifier : Rectifier) -> None:
    timestamp = datetime.datetime.fromtimestamp(get_time_from_api().unix_time)
    rectifier_restart_message = f"Rectifer Restart Detected {timestamp} \nTotal Load: {rectifier.total_load}kA \n16kA Rectifier Load: {rectifier.sixteen_load}kA \n24kA Rectifier Load: {rectifier.twenty_four_load}kA \n"
    rectifier_restart_message = rectifier_restart_message + f"\n \n Previous Minute Stored Reading: \n \t Total Load : {rectifier.min_ref_total_load}kA"
    rectifier_restart_message = rectifier_restart_message + f"\n \t 16kA Rectifier Load: {rectifier.min_ref_sixteen_load}kA \n \t 24kA Rectifier Load: {rectifier.min_ref_twenty_four_load}"
    subject = subject = f"[Rectifier Restart]- {timestamp}"
    send_email(subject, rectifier_restart_message)
    #print(rectifier_restart_message)
    return



def ecograph_poll_check(rect: Rectifier, counter) -> None:
    x = requests.get(ecograph_url)
    tree = ET.fromstring(x.text)

    twenty_four_load = tree[8][0].text # 24kA Load Value
    sixteen_load =  tree[9][0].text # 16kA Load Value

    if (counter%60 == 0):
        rect.min_ref_twenty_four_load = round(float(twenty_four_load),2)
        rect.min_ref_sixteen_load = round(float(sixteen_load),2)
        rect.min_ref_total_load = round(rect.min_ref_sixteen_load + rect.min_ref_twenty_four_load,2)
        rect.min_ref_time = get_time_from_api().unix_time
        counter = 0 #reset counter 
    
    print(f'{counter} - 16kA - {sixteen_load} | 24kA - {twenty_four_load}')
    update_rect_values(rect, float(sixteen_load), float(twenty_four_load))

    return

def simulated_eco_poll(rect:Rectifier,counter)-> None:
    url = r"http://127.0.0.1:3000"
    response = requests.get(url).text
    response = response.split(',')
    twenty_four_load = response[1]
    sixteen_load = response[0]
    if (counter%60 == 0):
        rect.min_ref_twenty_four_load = float(twenty_four_load)
        rect.min_ref_sixteen_load = float(sixteen_load)
        rect.min_ref_total_load = rect.min_ref_sixteen_load + rect.min_ref_twenty_four_load
        rect.min_ref_time = get_time_from_api().unix_time
        counter = 0 #reset counter 
    
    print(f'{counter} - 16kA - {sixteen_load} | 24kA - {twenty_four_load}')
    update_rect_values(rect, float(sixteen_load), float(twenty_four_load))
    return

def testcase_for_45_sec_alert() -> None:
    rect = Rectifier()
    update_rect_values(rect, 0, 0)
    time.sleep(1)
    rect.print_alert_flags()
    update_rect_values(rect, 0, 0.5)
    time.sleep(1)
    rect.print_alert_flags()
    time.sleep(1)
    update_rect_values(rect, 0, 0.43)
    rect.print_alert_flags()
    time.sleep(1)
    update_rect_values(rect, 2, 0.43)
    rect.print_alert_flags()
    time.sleep(1)
    update_rect_values(rect, 0, 0.43)
    rect.print_alert_flags()
    time.sleep(2)
    update_rect_values(rect, 0, 0.94)
    rect.print_alert_flags()
    time.sleep(45)
    update_rect_values(rect, 0, 0.94)
    rect.print_alert_flags()
    time.sleep(1)
    update_rect_values(rect, 0, 0.94)
    rect.print_alert_flags()
    time.sleep(1)
    update_rect_values(rect, 0, 0.94)
    rect.print_alert_flags()
    time.sleep(1)
    #Now test for restart condition
    update_rect_values(rect, 2, 0)
    time.sleep(1)
    rect.print_alert_flags()
    update_rect_values(rect, 2, 0.5)
    time.sleep(1)
    rect.print_alert_flags()
    time.sleep(1)
    update_rect_values(rect, 2, 0.43)
    rect.print_alert_flags()
    time.sleep(1)
    update_rect_values(rect, 0, 0.43)
    rect.print_alert_flags()
    time.sleep(1)
    update_rect_values(rect, 0, 0.43)
    rect.print_alert_flags()
    time.sleep(2)
    update_rect_values(rect, 2, 0.94)
    rect.print_alert_flags()
    time.sleep(46)
    update_rect_values(rect, 2.05, 0.94)
    rect.print_alert_flags()
    time.sleep(2)
    update_rect_values(rect, 2.05, 0.94)
    rect.print_alert_flags()
    return

#testcase_for_45_sec_alert() 
rect_1 = Rectifier() 
for interval in IntervalTimer(1):
    counter+=1
    rect_1.print_min_references()
    ecograph_poll_check(rect_1, counter)
    #rect_1.print_min_references()
    #rect_1.print_alert_flags()
    counter = counter%60
