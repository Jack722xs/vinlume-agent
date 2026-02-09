from rich.console import Console
from rich.panel import Panel
from rich.align import Align
import os
import time
import json
import datetime
import logging
import gspread
import smtplib
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from google.oauth2.service_account import Credentials
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from dotenv import load_dotenv
import google.generativeai as genai

# variable de entorno
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
SHEET_ID = os.getenv("SHEET_ID")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
EMAIL_SENDER = os.getenv("EMAIL_SENDER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")

# Configuración de Gemini
genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel('models/gemini-2.5-flash-preview-09-2025')

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)

def mostrar_banner():
    console = Console()
    mensaje = "[bold white]VINLUME DISK[/]\n[dim]Mini CD Keychains • Chile[/]"
    panel = Panel(
        Align.center(mensaje, vertical="middle"),
        border_style="white",
        title="💿 System Online",
        subtitle="v2.0",
        padding=(1, 10), # Relleno
        style="on black" 
    )
    console.print(panel)

def enviar_correo_confirmacion(destinatario, datos):
    if not EMAIL_SENDER or not EMAIL_PASSWORD:
        print("⚠️ ERROR: Faltan credenciales de correo en .env")
        return False

    # 1. ya no quiero apis
    print(f"🔎 Buscando portada para: {datos['diseno']}...")
    url_portada = buscar_portada_album(datos['diseno'])

    print(f"📧 Enviando correo a {destinatario}...")
    
    msg = MIMEMultipart()
    msg['From'] = f"VinLume Disk <{EMAIL_SENDER}>"
    msg['To'] = destinatario
    msg['Subject'] = f"Tu Pedido está en Producción 💿 - VinLume Disk"

    # HTML BASURA, MEJORAR DESPUES
    cuerpo = f"""
    <html>
      <body style="font-family: 'Helvetica', Arial, sans-serif; color: #333; background-color: #f4f4f4; padding: 20px;">
        
        <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 10px rgba(0,0,0,0.1);">
            
            <div style="background-color: #000; color: #fff; padding: 20px; text-align: center;">
                <h1 style="margin: 0; font-size: 24px;">VinLume Disk</h1>
                <p style="margin: 5px 0 0 0; font-size: 14px; color: #ccc;">Confirmación de Compra</p>
            </div>

            <div style="padding: 20px; text-align: center; background-color: #eee;">
                <p style="color: #000; font-weight: bold;">✅ PAGO APROBADO &rarr; EN PRODUCCIÓN</p>
            </div>

            <div style="padding: 30px;">
                <h2 style="color: #333; border-bottom: 2px solid #eee; padding-bottom: 10px;">Detalle del pedido</h2>
                
                <table style="width: 100%; border-collapse: collapse; margin-top: 20px;">
                    <tr>
                        <td style="width: 120px; vertical-align: top; padding-right: 20px;">
                            <img src="{url_portada}" alt="Portada Album" style="width: 120px; height: 120px; object-fit: cover; border-radius: 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.2);">
                        </td>
                        
                        <td style="vertical-align: top;">
                            <h3 style="margin: 0 0 10px 0; color: #000; font-size: 18px;">{datos['diseno']}</h3>
                            <p style="margin: 0; color: #666;">Tipo: {datos['tipo']}</p>
                            <p style="margin: 5px 0 0 0; color: #666;">Cantidad: {datos['cantidad']}</p>
                            <h2 style="margin: 15px 0 0 0; color: #2ecc71;">${datos['total']} CLP</h2>
                        </td>
                    </tr>
                </table>

                <br><hr style="border: 0; border-top: 1px solid #eee;"><br>

                <p><strong>Dirección de envío:</strong><br>{datos.get('direccion', 'No especificada')}</p>
                
                <div style="margin-top: 30px; padding: 15px; background-color: #f9f9f9; border-radius: 5px; font-size: 12px; color: #777; text-align: center;">
                    Gracias por confiar en VinLume Disk.<br>
                    Te notificaremos cuando tu pedido sea despachado 🚚.
                </div>
            </div>
        </div>
      </body>
    </html>
    """
    
    msg.attach(MIMEText(cuerpo, 'html'))

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        print("✅ Correo enviado con éxito.")
        return True
    except Exception as e:
        print(f"Error enviando correo: {e}")
        return False


def buscar_portada_album(busqueda):
    """
    Busca la carátula del álbum en la API de iTunes y devuelve la URL.
    Si no encuentra nada, devuelve una imagen genérica de 'No Image'.
    """
    try:
        url = "https://itunes.apple.com/search"
        params = {
            "term": busqueda,
            "media": "music",
            "entity": "album",
            "limit": 1
        }
        response = requests.get(url, params=params)
        data = response.json()
        
        if data["resultCount"] > 0:
            # Reescalalo
            imagen_url = data["results"][0]["artworkUrl100"]
            return imagen_url.replace("100x100bb", "600x600bb")
    except Exception as e:
        print(f"Error buscando carátula: {e}")
    
    # Imagen por defecto si no encuentra nada la api penca de itunes
    return "https://cdn-icons-png.flaticon.com/512/8660/8660552.png"

def conectar_google_sheets():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    try:
        with open("credentials.json", "r") as f:
            creds_dict = json.load(f)
        if "private_key" in creds_dict:
            creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        client = gspread.authorize(creds)
        sheet = client.open_by_key(SHEET_ID).worksheet("Ventas")
        return sheet
        
    except FileNotFoundError:
        print("ERROR: No encuentro el archivo credentials.json")
        raise
    except Exception as e:
        print(f"ERROR CONECTANDO A SHEETS: {e}")
        raise

def obtener_catalogo():
    return [
        {"Producto": "Llavero Mini CD", "Precio": 4000},
        {"Producto": "Llavero Mini CD con NFC", "Precio": 5000}
    ]

def registrar_venta_en_excel(datos):
    print(f"📤 Conectando a Excel para guardar: {datos['diseno']}...") 
    try:
        sheet = conectar_google_sheets() 
        fecha_actual = datetime.datetime.now().strftime("%d/%m/%Y")
        tiene_nfc = "Sí" if "nfc" in str(datos['tipo']).lower() else "No"
        cadena_extra = "Ninguna" 
        
        #Plantilla para el Mapeo de columnas en GOOGLE SHEETS empresas futuras 👹👹:
        nueva_fila = [
            fecha_actual,       # A: Fecha
            datos['diseno'],    # B: Diseño
            tiene_nfc,          # C: NFC
            cadena_extra,       # D: Cadena
            datos['cantidad'],  # E: Cantidad
            datos['precio'],    # F: Precio Unit
            datos['total'],     # G: Total
            datos.get('telefono', '-'),  # H: Teléfono
            datos.get('email', '-'),     # I: Email
            datos.get('direccion', '-'), # J: Dirección
            "Transferencia",    # K: Método
            "Pagado",           # L: Estado Pago
            "Pendiente",        # M: Estado Prod
            "Pendiente",        # N: Estado Entrega
            datos['cliente']    # O: Nombre Cliente
        ]
        
        sheet.append_row(nueva_fila)
        print("✅ ¡Venta guardada y stock descontado!")
        return True
    
    except Exception as e:
        print(f"Error crítico guardando en Excel: {e}")
        return False

def pensar_respuesta(mensaje, catalogo):
    catalogo_str = json.dumps(catalogo, ensure_ascii=False)

    prompt = f"""
    Eres VinlumeBot.
    CATÁLOGO: {catalogo_str}
    OBJETIVO: Vender Llaveros Mini CD a toda costa se ordenado y usa emojis para un mejor feedback ($4000) o con NFC ($5000).
    SI EL CLIENTE QUIERE COMPRAR, RESPONDE SOLO UN JSON (sin texto extra):

    {{
      "accion": "VENTA",
      "tipo_exacto": "Llavero Mini CD" o "Llavero Mini CD con NFC",
      "diseno_cliente": "Artista - Album",
      "cantidad": 1
    }}
    
    SI SOLO PREGUNTA, responde amable y corto como vendedor.
    CLIENTE: "{mensaje}"
    """
    
    for intento in range(2):
        try:
            response = model.generate_content(prompt)
            texto_limpio = response.text.strip().replace("```json", "").replace("```", "")
            return texto_limpio
        except Exception as e:
            print(f"Error IA: {e}")
            time.sleep(2)   
    return "Estoy pensando... dame un momento porfavor."

pedidos_pendientes = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(update.effective_chat.id, "¡Hola! 💿 Bienvenido a Vinlume Disk\nTienda chilena de llaveros mini CD personalizados\n▶️ ¿Qué álbum quieres en tu llavero?\n▶️ ¿Deseas Informacion?estoy a la espera de tu respuesta. 😊")

async def manejar_mensaje(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    chat_id = update.effective_chat.id
    
    # captura de datos del cliente /esto es fase beta/
    # Si el cliente está en medio de un pedido mando foto
    if chat_id in pedidos_pendientes:
        p = pedidos_pendientes[chat_id]
        paso = p.get('paso')
        
        if paso == 'esperando_telefono':
            p['telefono'] = user_text
            p['paso'] = 'esperando_email'
            await context.bot.send_message(chat_id, "📧 Gracias. Ahora, \n¿cuál es tu email para enviarte la boleta? 😊")
            return

        elif paso == 'esperando_email':
            p['email'] = user_text
            p['paso'] = 'esperando_direccion'
            await context.bot.send_message(chat_id, "🚚 Último dato: \n¿Cuál es tu dirección de envío/entrega? 📤")
            return
            #se supone que esto va al admin de forma exclusiva. hacer mas tests
        elif paso == 'esperando_direccion':
            p['direccion'] = user_text
            caption = (f"🚨 NUEVO PEDIDO COMPLETO\n"
                       f"👤 {p['cliente']}\n"
                       f"💿 {p['detalle_txt']}\n"
                       f"💰 ${p['total']}\n"
                       f"📞 {p['telefono']}\n"
                       f"📧 {p['email']}\n"
                       f"🚚 {p['direccion']}")
            
            kb = [
                [InlineKeyboardButton("✅ APROBAR", callback_data=f"ok|{chat_id}")],
                [InlineKeyboardButton("❌ RECHAZAR", callback_data=f"no|{chat_id}")],
                [InlineKeyboardButton("⚠️ DIFERENCIA $$", callback_data=f"dif|{chat_id}")]
            ]
            
            await context.bot.send_photo(ADMIN_ID, p['foto_id'], caption=caption, reply_markup=InlineKeyboardMarkup(kb))
            await context.bot.send_message(chat_id, "📩 Datos recibidos 👀. Esperando validación de 💿 VinlumeDisk...")
            del p['paso'] 
            return
        
    # ------------------------------------------

    catalogo = obtener_catalogo()
    respuesta = pensar_respuesta(user_text, catalogo)
    
    if "accion" in respuesta and "VENTA" in respuesta:
        try:
            datos = json.loads(respuesta)
            tipo = datos.get("tipo_exacto", "Llavero Mini CD")
            diseno = datos.get("diseno_cliente", "Diseño Pendiente")
            cantidad = int(datos.get("cantidad", 1))
            
            precio = 4000
            for item in catalogo:
                if str(item['Producto']).lower() == str(tipo).lower():
                    precio = int(item['Precio'])    
            total = precio * cantidad
            
            pedidos_pendientes[chat_id] = {
                "cliente": update.effective_user.first_name,
                "diseno": diseno,
                "tipo": tipo,
                "cantidad": cantidad, 
                "precio": precio, 
                "total": total,
                "detalle_txt": f"{diseno} ({tipo})",
                "paso": "esperando_foto"
            }
            
            await context.bot.send_message(chat_id, f"==============================\n\n✅ Pedido: {diseno}\n💿 Tipo: {tipo}\n💰 Total: ${total}\n\n==============================\nDATOS DE PAGO \n============================== JACK MAURO CARDENAS GARCIA\n RUT: 21774312-5\n BANCO: Banco Estado\n CUENTA: CuentaRUT\n NRO CUENTA: 21774312\n\n📸 Por favor, envía el comprobante de pago en este chat 👀.")
        except Exception as e:
            print(f"Error parseando JSON: {e}")
            await context.bot.send_message(chat_id, "Entendí que quieres comprar, pero no capté bien el diseño \n (se claro/clara respecto al artista y su respectivo album para que su produccion sea mas rapida). \n ¿Podrías repetirlo?")
    else:
        await context.bot.send_message(chat_id, respuesta)


async def manejar_foto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    
    if chat_id in pedidos_pendientes and pedidos_pendientes[chat_id].get('paso') == 'esperando_foto':
        pedidos_pendientes[chat_id]['foto_id'] = update.message.photo[-1].file_id
        pedidos_pendientes[chat_id]['paso'] = 'esperando_telefono'
        
        await context.bot.send_message(chat_id, "✅✅ Comprobante recibido. \n📞 Para gestionar el envío, necesito tu número de teléfono:\nEjemplo: +56912345678")
    else:
        await context.bot.send_message(chat_id, "No tengo un pedido activo tuyo. Porfavor dime primero qué quieres comprar 😊.")

async def decision_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    data = q.data.split("|")
    accion = data[0]
    chat_cliente = int(data[1])
    
    if chat_cliente in pedidos_pendientes:
        p = pedidos_pendientes[chat_cliente]
        
        if accion == "ok":
            exito = registrar_venta_en_excel(p)
            
            if exito:
                # arreglar esta tonteria despues
                if p.get('email') and '@' in p['email']:
                    enviar_correo_confirmacion(p['email'], p)
                else:
                    print("⚠️ No se envió correo: Email inválido o no proporcionado.")

                await context.bot.send_message(chat_cliente, "🎉 ¡Pago confirmado! 🎉 \nTu pedido pasara a producción y se te informara su avance. \n📧 Se te ha enviado un comprobante a tu correo.")
                await q.edit_message_caption(caption=f"{q.message.caption}\n\n✅ GUARDADO Y CONFIRMADO ")
            else:
                await q.edit_message_caption(caption=f"{q.message.caption}\n\n⚠️ ERROR DE CONEXIÓN A LA BBDD")
        elif accion == "no":
            await context.bot.send_message(chat_cliente, "❌ Tu pago no pudo ser verificado. Por favor, intenta nuevamente o contáctanos en:\n\n📷Instagram: https://www.instagram.com/vinlume_disk?igsh=MTNvOXk1ZHp2Nm1xbw==\n✉️Correo: vinlume.disk@gmail.com")
            await q.edit_message_caption(caption="🚫 PAGO RECHAZADO POR LOS ADMINISTRADORES")
        elif accion == "dif":
            await context.bot.send_message(chat_cliente, "⚠️ El monto transferido es incorrecto. Por favor transfiere la diferencia y envía el comprobante aquí.")
            await q.edit_message_caption(caption=f"{q.message.caption}\n\n💸 SOLICITANDO DIFERENCIA")
        if accion in ["ok", "no"]:
            del pedidos_pendientes[chat_cliente]
    else:
        await q.edit_message_caption(caption="⚠️ Este pedido ya expiró o ya fue procesado.")

if __name__ == '__main__':
    mostrar_banner()
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    
    app.add_handler(CommandHandler('start', start))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), manejar_mensaje))
    app.add_handler(MessageHandler(filters.PHOTO, manejar_foto))
    app.add_handler(CallbackQueryHandler(decision_admin))
    
    app.run_polling()