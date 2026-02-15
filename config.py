import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


BASE_DIR = Path(__file__).resolve().parent


TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY") 
SHEET_ID = os.getenv("SHEET_ID")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
EMAIL_SENDER = os.getenv("EMAIL_SENDER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")

LINK_INSTAGRAM = "https://www.instagram.com/vinlume_disk/"
MAX_PEDIDO_AUTOMATICO = 20