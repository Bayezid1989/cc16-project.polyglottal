import os
from dotenv import load_dotenv
load_dotenv()

# LINE
_LINE_TOKEN = os.getenv('_LINE_TOKEN')
_LINE_SECRET = os.getenv('_LINE_SECRET')

# Email
EMAIL_USER = os.getenv('MAILJET_USER')
EMAIL_PASS = os.getenv('MAILJET_PASS')
