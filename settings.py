from dotenv import load_dotenv
from datetime import datetime, timedelta
import pathlib
import os
import sys

load_dotenv('.env')

if len(sys.argv) > 1:
    DATE = datetime.strptime(str(sys.argv[1]), '%Y-%m-%d')
    
else:
    DATE = datetime.now()

# Mailbox settings
SMTP_HOST = os.environ.get('SMTP_HOST')
SMTP_PORT = os.environ.get('SMTP_PORT')
SMTP_USERNAME = os.environ.get('SMTP_USERNAME')
SMTP_PASSWORD = os.environ.get('SMTP_PASSWORD')

# Subject of emails to get form mailbox
SEARCH_SUBJECT = os.environ.get('SEARCH_SUBJECT')

# Subject of email message report to send
MESSAGE_SUBJECT = os.environ.get('MESSAGE_SUBJECT').replace(
    '$(fecha_ayer)', f'{DATE.strftime("%d-%m-%Y")}')


# Email message template
with open(os.environ.get('MESSAGE_FILE'), mode='r', encoding='utf8') as f:
    MESSAGE = """"""
    for line in f.readlines():
        MESSAGE += line

# List of email recipients to send notifications.
EMAIL_RECIPIENTS = os.environ.get('EMAIL_RECIPIENTS')

# Carbon copy recipients
CC = os.environ.get('CC')

# Project settings
# BASE_DIR = pathlib.Path(__file__).resolve().parent
BASE_DIR = os.path.dirname(__file__)

# File settings
# Folder to storage reports downloaded from Cloudfeet
FILES_DIR = os.environ.get('FILES_DIR')
# File name of checklist report dowloaded from Cloudfeet
CHECKLIST_NAME = os.environ.get('CHECKLIST_NAME')
# File name of report from Geotab
REPORT_NAME = os.environ.get('REPORT_NAME')
# File name of report after processing.
REPORT_DIR = os.environ.get('REPORT_DIR')


# Logging settings
LOG_NAME = os.environ.get('LOG_NAME')

#Web service settings
WEBSERVICE_URL = os.environ.get('WEBSERVICE_URL')

# Web browser settings
# Browser engine
CHROME_DRIVER_PATH = "/usr/bin/chromedriver"
FIREFOX_DRIVER_PATH = os.path.join(BASE_DIR, "robot", "browser", "Driver", "geckodriver.exe")
FIREFOX_BINARY = "/usr/bin/firefox"

# Maximum time to wait for a download to complete
MAX_TIME = 10

# Navigation session

AE_URL = os.environ.get('AE_URL')
AERIE_URL = os.environ.get('AERIE_URL')
ARTURO_URL = os.environ.get('ARTURO_URL')
BERSHKA_URL = os.environ.get('BERSHKA_URL')
BRONZINI_URL = os.environ.get('BRONZINI_URL')
HM_URL = os.environ.get('HM_URL')
KOAJ_URL = os.environ.get('KOAJ_URL')
MASSIMO_URL = os.environ.get('MASSIMO_URL')
NAFNAF_URL = os.environ.get('NAFNAF_URL')
NAUTY_URL = os.environ.get('NAUTY_URL')
OFFCORSS_URL = os.environ.get('OFFCORSS_URL')
PULLBEAR_URL = os.environ.get('PULLBEAR_URL')
POLITO_URL = os.environ.get('POLITO_URL')
MANGO_URL = os.environ.get('MANGO_URL')
ETA_URL = os.environ.get('ETA_URL')
DEPRATI_URL = os.environ.get('DEPRATI_URL')

TENNIS_URL = os.environ.get('TENNIS_URL')
TENNIS_CATEGORIES = os.environ.get('TENNIS_CATEGORIES').split(",")
ZARA_URL = os.environ.get('ZARA_URL')