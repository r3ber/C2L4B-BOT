import os
from dotenv import load_dotenv

load_dotenv()

#bot Configuration
TOKEN = os.getenv("token")
ANNOUNCEMENT_CHANNEL_ID = int(os.getenv("announchannel")) if os.getenv("announchannel") else None
GEMINI_API_KEY = os.getenv("gemini_api_key")

#team Configuration
TEAM_ID = 412730 

#paths
DATA_DIR = "data"
LIBRARY_DIR = "great-library"

if not TOKEN:
    raise ValueError("Bot token not found in environment variables!")