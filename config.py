import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY") 
SHEET_ID = os.getenv("SHEET_ID")

admin_env = os.getenv("ADMIN_ID", "")
ADMIN_IDS = [int(x.strip()) for x in admin_env.split(",")] if admin_env else []
ADMIN_ID = ADMIN_IDS[0] if ADMIN_IDS else 0

EMAIL_SENDER = os.getenv("EMAIL_SENDER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")

LINK_INSTAGRAM = "https://www.instagram.com/vinlume_disk/"
MAX_PEDIDO_AUTOMATICO = 20

PRECIOS_ENVIO = {
    "RM (Santiago)": 3500,
    "Zona Norte": 6000,
    "Zona Centro": 5000,
    "Zona Sur": 6000,
    "Extremo Sur": 9000
}
CUPONES = {
    "VINLUME10TG": 0.10,  # 10% de descuento
    "CLIENTEPROTG": 0.15, # 15% de descuento
    "ENVIOGRATISTG": "FREE_SHIP",
    "CLAU100": "GOD_MODE", # Código especial para pedidos gratis (solo para testing, eliminar en producción)
}