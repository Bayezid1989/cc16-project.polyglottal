from dotenv import load_dotenv
load_dotenv()

# LINE
import os
_LINE_TOKEN = os.getenv('_LINE_TOKEN')
_LINE_SECRET = os.getenv('_LINE_SECRET')