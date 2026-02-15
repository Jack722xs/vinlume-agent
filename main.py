import logging
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, PicklePersistence
from rich.console import Console
from rich.panel import Panel
from rich.align import Align
from config import TELEGRAM_TOKEN
from src.handlers import messages

# Logs
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("googleapiclient").setLevel(logging.WARNING)

def mostrar_banner():
    console = Console()
    mensaje = "[bold cyan]VINLUME DISK SYSTEM[/]\n[white]Enterprise Flow v2.1[/]"
    panel = Panel(Align.center(mensaje, vertical="middle"), border_style="cyan", title="ONLINE", style="on black")
    console.print(panel)

if __name__ == '__main__':
    mostrar_banner()
    
    persistencia = PicklePersistence(filepath='vinlume_data.pickle')
    
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).persistence(persistencia).build()
    
    app.add_handler(CommandHandler('start', messages.start))
    app.add_handler(CallbackQueryHandler(messages.manejar_callback))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), messages.manejar_texto))
    app.add_handler(MessageHandler(filters.PHOTO, messages.manejar_foto))
    app.run_polling()