import os
import time
import json
import datetime
import logging
import gspread
from google.oauth2.service_account import Credentials
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from dotenv import load_dotenv
import google.generativeai as genai

#variable de entorno
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
SHEET_ID = os.getenv("SHEET_ID")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

# Configuración de Gemini
genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel('models/gemini-2.5-flash-preview-09-2025')

# Configuración de Logs
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)

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

def registrar_venta_en_excel(diseno, tipo, cantidad, precio_unit, total):
    print(f"📤 Conectando a Excel para guardar: {diseno}...") 
    try:
        sheet = conectar_google_sheets() 
        fecha_actual = datetime.datetime.now().strftime("%d/%m/%Y")
        tiene_nfc = "Sí" if "nfc" in str(tipo).lower() else "No"
        cadena_extra = "Ninguna" 
        
#Mapeo de columnas
        nueva_fila = [
            fecha_actual,       # A: Fecha
            diseno,             # B: Diseño
            tiene_nfc,          # C: NFC
            cadena_extra,       # D: Cadena
            cantidad,           # E: Cantidad
            precio_unit,        # F: Precio Unit
            total,              # G: Total
            "Transferencia",    # H: Método
            "Pagado",           # I: Estado Pago
            "Pendiente",        # J: Estado Prod
            "Pendiente"         # K: Estado Entrega
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
    OBJETIVO: Vender Llaveros Mini CD a toda costa ($4000) o con NFC ($5000).
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
    await context.bot.send_message(update.effective_chat.id, """¡Hola! 💿 Bienvenido a Vinlume Disk. 
                                                                tienda chilena de llaveros mini CD personalizados 
                                                                ▶️ ¿Qué álbum quieres en tu llavero?
                                                                ▶️ ¿Deseas Informacion?
                                   
                                                                estoy a la espera de tu respuesta. 😊""")

async def manejar_mensaje(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    chat_id = update.effective_chat.id
    
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
                "detalle_txt": f"{diseno} ({tipo})"
            }
            
            await context.bot.send_message(chat_id, f"==============================\n\n✅ Pedido: {diseno}\n💿 Tipo: {tipo}\n💰 Total: ${total}\n==== DATOS DE PAGO ====\n\n JACK MAURO CARDENAS GARCIA\n RUT: 21774312-5\n BANCO: Banco Estado\n CUENTA: CuentaRUT\n NRO CUENTA: 21774312\n\n📸 Por favor, envía el comprobante de pago en este chat 👀.")
        except Exception as e:
            print(f"Error parseando JSON: {e}")
            await context.bot.send_message(chat_id, "Entendí que quieres comprar, pero no capté bien el diseño \n (se claro/clara respecto al artista y su respectivo album para que su produccion sea mas rapida). \n ¿Podrías repetirlo?")
    else:
        await context.bot.send_message(chat_id, respuesta)


async def manejar_foto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id not in pedidos_pendientes:
        await context.bot.send_message(chat_id, "No tengo un pedido activo. Porfavor dime primero qué quieres comprar 😊.")
        return
    
#sistema de validacion de pago, fase de prueba
    p = pedidos_pendientes[chat_id]
    caption = f"🚨 NUEVO PAGO\n👤 {p['cliente']}\n💿 {p['detalle_txt']}\n💰 ${p['total']}"
    
    kb = [
        [InlineKeyboardButton("✅ APROBAR Y GUARDAR", callback_data=f"ok|{chat_id}")],
        [InlineKeyboardButton("❌ RECHAZAR", callback_data=f"no|{chat_id}")]
    ]
    
    await context.bot.send_photo(ADMIN_ID, update.message.photo[-1].file_id, caption=caption, reply_markup=InlineKeyboardMarkup(kb))
    await context.bot.send_message(chat_id, "📩 Comprobante recibido 👀. Esperando validación de 💿 VinlumeDisk...")

async def decision_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    data = q.data.split("|")
    accion = data[0]
    chat_cliente = int(data[1])
    
    if chat_cliente in pedidos_pendientes:
        p = pedidos_pendientes[chat_cliente]
        
        if accion == "ok":
            exito = registrar_venta_en_excel(
                p['diseno'], 
                p['tipo'], 
                p['cantidad'], 
                p['precio'], 
                p['total']
            )
            
            if exito:
                await context.bot.send_message(chat_cliente, "🎉 ¡Pago confirmado! 🎉 \nTu pedido pasara a producción y se te informara su avance.")
                await q.edit_message_caption(caption=f"{q.message.caption}\n\n✅ GUARDADO Y CONFIRMADO ")
            else:
                await q.edit_message_caption(caption=f"{q.message.caption}\n\n⚠️ ERROR DE CONEXIÓN A LA BBDD")
        else:
            await context.bot.send_message(chat_cliente, "❌ Tu pago no pudo ser verificado. Por favor, intenta nuevamente o contáctanos en:\n\n📷 Instagram: https://www.instagram.com/vinlume_disk?igsh=MTNvOXk1ZHp2Nm1xbw==\n✉️ Correo: vinlume.disk@gmail.com")
            await q.edit_message_caption(caption="🚫 PAGO RECHAZADO POR LOS ADMINISTRADORES")
        
        del pedidos_pendientes[chat_cliente]
    else:
        await q.edit_message_caption(caption="⚠️ Este pedido ya expiró o ya fue procesado.")

if __name__ == '__main__':
    print(" ")
    print("======================================")
    print("=== VINLUME BOT 1.0 por @jack722x ===")
    print("========= 📀VinlumeDisk📀 ===========")
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    
    app.add_handler(CommandHandler('start', start))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), manejar_mensaje))
    app.add_handler(MessageHandler(filters.PHOTO, manejar_foto))
    app.add_handler(CallbackQueryHandler(decision_admin))
    
    app.run_polling()