import os
import json
import datetime
import logging
import gspread
import smtplib
import requests
import random
import re
from rich.console import Console
from rich.panel import Panel
from rich.align import Align
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from google.oauth2.service_account import Credentials
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from dotenv import load_dotenv
import google.generativeai as genai

# ==========================================
# CONFIGURACIÓN
# ==========================================
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY") 
SHEET_ID = os.getenv("SHEET_ID")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
EMAIL_SENDER = os.getenv("EMAIL_SENDER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
LINK_INSTAGRAM = "https://www.instagram.com/vinlume_disk/"

# LÍMITE DE SEGURIDAD
MAX_PEDIDO_AUTOMATICO = 20 

# Logs
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("googleapiclient").setLevel(logging.WARNING)

# Gemini AI
genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel('models/gemini-2.5-flash-preview-09-2025')

sesiones = {}

# ==========================================
# UTILIDADES VISUALES
# ==========================================

def mostrar_banner():
    console = Console()
    mensaje = "[bold cyan]VINLUME DISK SYSTEM[/]\n[white]Enterprise Flow v2.0[/]"
    panel = Panel(Align.center(mensaje, vertical="middle"), border_style="cyan", title="ONLINE", style="on black")
    console.print(panel)

def limpiar_texto(texto):
    if not texto: return ""
    return str(texto)[:500].replace("\n", " | ").strip()

def buscar_portada_album(busqueda):
    try:
        url = "https://itunes.apple.com/search"
        params = {"term": busqueda, "media": "music", "entity": "album", "limit": 1}
        response = requests.get(url, params=params, timeout=5)
        data = response.json()
        if data["resultCount"] > 0:
            return data["results"][0]["artworkUrl100"].replace("100x100bb", "600x600bb")
    except:
        pass
    return None

# ==========================================
# GESTIÓN DE CORREO Y EXCEL
# ==========================================

def enviar_correo_confirmacion(destinatario, datos):
    if not EMAIL_SENDER or not EMAIL_PASSWORD:
        return False
    
    url_portada = datos.get('url_portada')
    if not url_portada or url_portada == "MANUAL" or len(datos['carrito']) > 1:
        url_portada = "https://images.icon-icons.com/2008/PNG/512/compact_disc_cd_icon_123442.png"

    html_items = ""
    for item in datos['carrito']:
        tipo = "NFC" if item['nfc'] else "Normal"
        html_items += f"<li><b>{item['nombre']}</b> <span style='color:#666; font-size:12px;'>({tipo})</span></li>"

    msg = MIMEMultipart()
    msg['From'] = f"VinLume Disk <{EMAIL_SENDER}>"
    msg['To'] = destinatario
    msg['Subject'] = f"Confirmación #{datos['order_id']} 💿 - VinLume Disk"

    cuerpo = f"""
    <html>
    <body style="font-family: Helvetica, Arial, sans-serif; background-color: #f4f4f4; padding: 20px;">
      <div style="max-width: 600px; margin: 0 auto; background-color: #fff; border-radius: 8px; overflow: hidden;">
        <div style="background-color: #000; color: #fff; padding: 20px; text-align: center;">
            <h1 style="margin:0;">VINLUME DISK</h1>
            <p>Pedido #{datos['order_id']}</p>
        </div>
        <div style="padding: 30px;">
            <h2 style="color: #333;">¡Hola {datos['cliente']}!</h2>
            <p>Tu pago está confirmado. Aquí está el detalle de tu producción:</p>
            
            <div style="display: flex; gap: 20px; margin: 20px 0; background: #f9f9f9; padding: 15px; border-radius: 8px;">
                <img src="{url_portada}" style="width: 80px; height: 80px; object-fit: cover; border-radius: 5px;">
                <div>
                    <ul style="margin: 0; padding-left: 20px; line-height: 1.6;">
                        {html_items}
                    </ul>
                    <p style="font-weight: bold; margin-top: 10px;">Total: ${datos['total']}</p>
                </div>
            </div>

            <p><strong>📍 Envío a:</strong><br>{datos.get('direccion', '-')}</p>
            <hr style="border:0; border-top:1px solid #eee;">
            <p style="text-align: center;">
                <a href="{LINK_INSTAGRAM}" style="color: #007bff; text-decoration: none;">Contactar con Soporte en Instagram</a>
            </p>
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
        return True
    except Exception as e:
        print(f"❌ Error enviando correo: {e}")
        return False

def registrar_venta_en_excel(datos):
    print(f"log Exportando pedido #{datos['order_id']}...") 
    try:
        items_str = []
        tiene_nfc_global = "No"
        
        for item in datos['carrito']:
            tag = "(NFC)" if item['nfc'] else "(Normal)"
            items_str.append(f"{item['nombre']} {tag}")
            if item['nfc']: tiene_nfc_global = "Si/Mixto"

        str_final_producto = " || ".join(items_str)

        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds_dict = json.load(open("credentials.json"))
        if "private_key" in creds_dict: creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        client = gspread.authorize(creds)
        sheet = client.open_by_key(SHEET_ID).worksheet("Ventas")

        nueva_fila = [
            datetime.datetime.now().strftime("%d/%m/%Y"), 
            limpiar_texto(str_final_producto),            
            tiene_nfc_global,                             
            datos['order_id'],                            
            len(datos['carrito']),                        
            "Variado",                                    
            datos['total'],                               
            datos.get('telefono', '-'),
            datos.get('email', '-'),
            datos.get('direccion', '-'),
            "Transferencia",
            "Pagado",
            "En Producción",
            "Pendiente",
            datos['cliente']
        ]
        sheet.append_row(nueva_fila)
        return True
    except Exception as e:
        print(f"Error crítico Excel: {e}")
        return False

# ==========================================
# LÓGICA BOT
# ==========================================

def get_cancel_button():
    return InlineKeyboardButton("❌ Cancelar / Reiniciar", callback_data='cancel_order')

def get_back_button():
    return InlineKeyboardButton("🔙 Volver al Inicio", callback_data='back_start')

async def reiniciar_sesion(chat_id, context):
    if chat_id in sesiones: del sesiones[chat_id]
    await context.bot.send_message(chat_id, "🔄 Operación reiniciada.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("💿 Iniciar Nuevo Pedido", callback_data='start_bot')]]))



async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    kb = [
        [InlineKeyboardButton("🤖 Hacer Pedido", callback_data='start_bot')],
        [InlineKeyboardButton("👤 Hablar con Humano", callback_data='start_human')],
        [InlineKeyboardButton("❓ Info, Precios y Dudas", callback_data='start_info')]
    ]
    await context.bot.send_message(
        update.effective_chat.id,
        f"💿 VINLUME DISK Chile 💿\n\nHola {user.first_name}. Bienvenido a nuestra tienda de llaveros personalizados.\nSelecciona una opción 👀:",
        reply_markup=InlineKeyboardMarkup(kb)
    )

async def preguntar_cantidad(chat_id, context):
    sesiones[chat_id]['paso'] = 'esperando_cantidad'
    kb = [
        [InlineKeyboardButton("1 Unidad 💿", callback_data='cant_1'), InlineKeyboardButton("2 Unidades 💿", callback_data='cant_2')],
        [InlineKeyboardButton("3 Unidades 💿", callback_data='cant_3'), InlineKeyboardButton("4 Unidades 💿", callback_data='cant_4')],
        [InlineKeyboardButton("Más de 4 (Escribir)", callback_data='cant_manual')],
        [get_back_button()] # boton Volver al inicio
    ]
    await context.bot.send_message(chat_id, "💿 Paso 1:\n\n¡Genial! Empecemos. ¿Cuántos llaveros deseas pedir?", reply_markup=InlineKeyboardMarkup(kb))

async def pedir_lista_albumes(chat_id, context):
    cant = sesiones[chat_id]['cantidad_meta']
    sesiones[chat_id]['paso'] = 'esperando_nombres'
    
    msg = f"💿 Paso 2:\n\nEntendido, será/n {cant} llavero/s.\n📀📀📀"
    if cant == 1:
        msg += "Por favor, escribe el nombre del Artista y del Álbum:\n \nEjemplo: Twenty One Pilots - Trench"
    else:
        msg += f"Por favor, escribe la lista de los {cant} álbumes (uno por línea o separados por comas).\n\nEjemplo:\nBad Bunny - Un Verano Sin ti\nLinkin Park - Meteora"
    
    #boton de cancelar
    kb = [[get_cancel_button()]]
    
    await context.bot.send_message(chat_id, msg, reply_markup=InlineKeyboardMarkup(kb))

async def mostrar_configurador_nfc(chat_id, context):
    ses = sesiones[chat_id]
    ses['paso'] = 'configurando_nfc'
    
    texto_base = "📲 Paso 3: Tecnología NFC\n\nAquí puedes activar el chip inteligente para cada llavero. Toca el botón del álbum para activarlo/desactivarlo.\n\n"
    
    keyboard = []
    total_precio = 0
    
    for idx, item in enumerate(ses['carrito']):
        estado = "✅ CON NFC" if item['nfc'] else "💿 Normal"
        precio_item = 5000 if item['nfc'] else 4000
        total_precio += precio_item
        
        texto_base += f"• {item['nombre']} → {estado}\n"
        
        btn_text = f"{idx+1}. {item['nombre'][:15]}... ({'NFC' if item['nfc'] else 'No'})"
        keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"toggle_{idx}")])

    ses['total_temporal'] = total_precio
    texto_base += f"\n💰 Total Actual: ${total_precio}"
    
    # Botones extra de ayuda y control
    keyboard.append([InlineKeyboardButton("🤔 ¿Qué es el NFC?", callback_data="what_is_nfc")])
    keyboard.append([InlineKeyboardButton("✅ Confirmar y Seguir", callback_data="confirm_nfc")])
    keyboard.append([get_cancel_button()])
    
    await context.bot.send_message(chat_id, texto_base, reply_markup=InlineKeyboardMarkup(keyboard))

async def confirmar_datos(chat_id, context):
    s = sesiones[chat_id]
    msg = (f"📋 CONFIRMA TUS DATOS\n\n"
           f"Por favor revisa que todo esté correcto para el envío 👀:\n\n"
           f"📞 {s.get('telefono')}\n"
           f"📧 {s.get('email')}\n"
           f"🚚 {s.get('direccion')}\n\n"
           f"¿Están bien los datos? \n 👇👇👇")
    
    kb = [
        [InlineKeyboardButton("✅ Sí, todo perfecto", callback_data='datos_ok')],
        [InlineKeyboardButton("✏️ Corregir Teléfono", callback_data='fix_telefono')],
        [InlineKeyboardButton("✏️ Corregir Email", callback_data='fix_email')],
        [InlineKeyboardButton("✏️ Corregir Dirección", callback_data='fix_direccion')],
        [get_cancel_button()]
    ]
    await context.bot.send_message(chat_id, msg, reply_markup=InlineKeyboardMarkup(kb))

async def manejar_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    chat_id = update.effective_chat.id
    data = q.data
    if data == 'cancel_order':
        await reiniciar_sesion(chat_id, context)
        return
    elif data == 'back_start':
        await start(update, context)
        return
    elif data == 'what_is_nfc':
        kb = [[InlineKeyboardButton("🔙 Volver al Inicio", callback_data='back_start')]]
        await context.bot.send_message(chat_id, "📲 **¿Qué es NFC?**\n\nEs un chip invisible dentro del llavero. \nAl acercar tu celular, se abre automáticamente el álbum en Spotify, YouTube o el link que tú quieras. ¡Sin usar la cámara, solo por contacto! ✨", reply_markup=InlineKeyboardMarkup(kb))
        return
    elif data == 'start_human':
        kb = [[InlineKeyboardButton("🔙 Volver al Inicio", callback_data='back_start')]]
        await context.bot.send_message(chat_id, f"👤 **Contacto Directo**\n\nPara pedidos mayoristas (+20 unidades), diseños complejos o dudas específicas, escríbenos directo:\n\n👉 {LINK_INSTAGRAM}", reply_markup=InlineKeyboardMarkup(kb))  
    elif data == 'start_info':
        msj = ("ℹ️ INFORMACIÓN Y PRECIOS\n\n"
               "• Normal ($4.000): Llavero con la portada en alta calidad.\n"
               "• Con NFC ($5.000): Incluye chip inteligente para escanear con el celular.\n\n"
               "🚚 Enviamos a todo Chile 📤.\n\n"
               "💡 ¿Tienes dudas? Puedes escribirme tu pregunta aquí mismo y te responderé. O si estás listo, toca abajo:")
        
        kb = [
            [InlineKeyboardButton("💿 Hacer Pedido", callback_data='start_bot')],
            [InlineKeyboardButton("🤔 ¿Qué es NFC?", callback_data='what_is_nfc')],
            [InlineKeyboardButton("🔙 Volver al Inicio", callback_data='back_start')]
        ]
        await context.bot.send_message(chat_id, msj, reply_markup=InlineKeyboardMarkup(kb))
    
    elif data == 'start_bot':
        sesiones[chat_id] = {'cliente': update.effective_user.first_name, 'carrito': []}
        await preguntar_cantidad(chat_id, context)

    elif data.startswith('cant_'):
        if data == 'cant_manual':
            sesiones[chat_id]['paso'] = 'esperando_cantidad_manual'
            await context.bot.send_message(chat_id, "⌨️ Por favor, escribe el número de unidades (Máximo 20 por aquí):")
        else:
            cant = int(data.split('_')[1])
            sesiones[chat_id]['cantidad_meta'] = cant
            await pedir_lista_albumes(chat_id, context)

    elif data == 'cover_si':
        await mostrar_configurador_nfc(chat_id, context)
    
    elif data == 'cover_manual':
        sesiones[chat_id]['url_portada'] = "MANUAL"
        sesiones[chat_id]['paso'] = 'esperando_foto'
        await context.bot.send_message(chat_id, "📸 ¡Vale! Envíame la imagen que quieres usar.")

    elif data.startswith('toggle_'):
        idx = int(data.split('_')[1])
        item = sesiones[chat_id]['carrito'][idx]
        item['nfc'] = not item['nfc']
        await q.message.delete()
        await mostrar_configurador_nfc(chat_id, context)

    elif data == 'confirm_nfc':
        sesiones[chat_id]['paso'] = 'esperando_telefono'
        await context.bot.send_message(chat_id, "📝 ¡Perfecto! Vamos con tus datos de envío.\n\n📞 ¿Cuál es tu número de teléfono?")

    elif data.startswith('fix_'):
        campo = data.split('_')[1]
        sesiones[chat_id]['paso'] = f'esperando_{campo}'
        await context.bot.send_message(chat_id, f"✏️ Escribe tu nuevo {campo}:")

    elif data == 'datos_ok':
        s = sesiones[chat_id]
        s['paso'] = 'esperando_pago'
        msj = (f"💳 RESUMEN FINAL\n==================================================\n"
               f"💵 Total a pagar: ${s['total_temporal']}\n\n"
               f"🏦 Datos de Transferencia:\n"
               f"• Banco: Banco Estado\nCuenta: CuentaRUT\n"
               f"• Nombre: JACK MAURO CARDENAS GARCIA\n"
               f"• Rut: 21221234-5\n\n==================================================\n\n"
               f"📸 Por favor, envía aquí tu comprobante de pago.\n (📸 Como Imagen)")
        await context.bot.send_message(chat_id, msj)

    elif "|" in data:
        accion, id_cliente = data.split("|")
        id_cliente = int(id_cliente)
        
        if id_cliente not in sesiones:
            await q.edit_message_caption("⚠️ Esta sesión ha expirado.")
            return
        
        s = sesiones[id_cliente]
        if accion == "aprob":
            s['order_id'] = f"VD-{random.randint(10000, 99999)}"
            s['total'] = s['total_temporal']
            
            if registrar_venta_en_excel(s):
                if '@' in str(s.get('email')): enviar_correo_confirmacion(s['email'], s)
                
                msj_exito = (f"🎉 ¡Pago Aprobado!\n\n"
                             f"👍 Tu código de seguimiento es: #{s['order_id']}\nGuardalo bien para cualquier consulta futura.\n\n"
                             f"Tu pedido ya pasó a producción .\n\n"
                             f"Para pedir nuevamente, toca aquí: /start \n\n"
                             f" ahora estamos a tu servicio. Cualquier duda, contáctanos en:\n{LINK_INSTAGRAM}")
                
                await context.bot.send_message(id_cliente, msj_exito)
                await q.edit_message_caption(f"{q.message.caption}\n\n✅ APROBADO #{s['order_id']}")
            else:
                await q.edit_message_caption("⚠️ ERROR CRÍTICO EN BASE DE DATOS")
            
            del sesiones[id_cliente]

        elif accion == "rech":
            msj_rechazo = (f"❌ Tu pago no pudo ser verificado.\n\n"
                           f"Para más información y dudas hablar por interno a:\n{LINK_INSTAGRAM}")
            await context.bot.send_message(id_cliente, msj_rechazo)
            await q.edit_message_caption("🚫 RECHAZADO")
            del sesiones[id_cliente]

async def manejar_texto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    text = update.message.text
    
    if chat_id not in sesiones:
        prompt = f"Eres el asistente de Vinlume Disk (tienda de llaveros CD). Cliente dice: '{text}'. Si quiere comprar un album responde COMPRA:Album. Si tiene dudas responde CHAT:RespuestaAmable"
        try:
            resp = model.generate_content(prompt).text
            if "COMPRA:" in resp:
                album = resp.split(":")[1].strip()
                sesiones[chat_id] = {'cliente': update.effective_user.first_name, 'carrito': [], 'cantidad_meta': 1}
                url = buscar_portada_album(album)
                sesiones[chat_id]['carrito'].append({'nombre': album, 'nfc': False}) 
                if url:
                    sesiones[chat_id]['url_portada'] = url
                    kb = [[InlineKeyboardButton("✅ Sí, es ese", callback_data='cover_si'), InlineKeyboardButton("🖼️ No (Subir mía)", callback_data='cover_manual')]]
                    await context.bot.send_photo(chat_id, url, caption=f"💿 Busqué: {album}\n¿Es correcta esta portada?", reply_markup=InlineKeyboardMarkup(kb))
                else:
                    await mostrar_configurador_nfc(chat_id, context)
            else:
                await context.bot.send_message(chat_id, resp.replace("CHAT:", ""), reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("💿 Hacer Pedido", callback_data='start_bot')]]))
        except:
            await context.bot.send_message(chat_id, "Hola, usa el menú para comenzar tu pedido.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Ver Menú", callback_data='start_bot')]]))
        return
    
    paso = sesiones[chat_id].get('paso')

    if paso == 'esperando_cantidad_manual':
        if text.isdigit():
            cant = int(text)
            if cant > MAX_PEDIDO_AUTOMATICO:
                kb = [[InlineKeyboardButton("🔙 Volver al Inicio", callback_data='back_start')]]
                await context.bot.send_message(chat_id, f"⚠️ ¡Wow! Para pedidos de {cant} unidades (Mayoristas), por favor contáctanos directamente por Instagram para coordinar stock y precios especiales.\n\n👉 {LINK_INSTAGRAM}", reply_markup=InlineKeyboardMarkup(kb))
                del sesiones[chat_id] 
            elif cant > 0:
                sesiones[chat_id]['cantidad_meta'] = cant
                await pedir_lista_albumes(chat_id, context)
            else:
                await context.bot.send_message(chat_id, "⚠️ El número debe ser mayor a 0.")
        else:
            await context.bot.send_message(chat_id, "⚠️ Por favor, ingresa solo números.")

    elif paso == 'esperando_nombres':
        meta = sesiones[chat_id]['cantidad_meta']
        if "\n" in text:
            items = [x.strip() for x in text.split("\n") if x.strip()]
        else:
            items = [x.strip() for x in text.split(",") if x.strip()]
        
        if len(items) != meta:
            await context.bot.send_message(chat_id, f"⚠️ Pediste {meta} unidades, pero escribiste {len(items)} nombres.\nPor favor revisa la lista y envíala de nuevo.")
            return
        
        sesiones[chat_id]['carrito'] = [{'nombre': item, 'nfc': False} for item in items]
        
        if meta == 1:
            url = buscar_portada_album(items[0])
            if url:
                sesiones[chat_id]['url_portada'] = url
                kb = [[InlineKeyboardButton("✅ Sí, es ese", callback_data='cover_si'), InlineKeyboardButton("🖼️ No (Subir mía)", callback_data='cover_manual')]]
                await context.bot.send_photo(chat_id, url, caption=f"💿 Busqué: {items[0]}\n¿Es correcta esta portada?", reply_markup=InlineKeyboardMarkup(kb))
                return
        
        await mostrar_configurador_nfc(chat_id, context)
    
    elif paso == 'esperando_telefono':
        sesiones[chat_id]['telefono'] = text
        if 'email' in sesiones[chat_id]: await confirmar_datos(chat_id, context)
        else:
            sesiones[chat_id]['paso'] = 'esperando_email'
            await context.bot.send_message(chat_id, "📧 ¿Cuál es tu Email?")

    elif paso == 'esperando_email':
        sesiones[chat_id]['email'] = text
        if 'direccion' in sesiones[chat_id]: await confirmar_datos(chat_id, context)
        else:
            sesiones[chat_id]['paso'] = 'esperando_direccion'
            await context.bot.send_message(chat_id, "🚚 ¿Cuál es tu dirección de envío?")

    elif paso == 'esperando_direccion':
        sesiones[chat_id]['direccion'] = text
        await confirmar_datos(chat_id, context)

async def manejar_foto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id not in sesiones: return
    
    paso = sesiones[chat_id].get('paso')
    fid = update.message.photo[-1].file_id

    if paso == 'esperando_foto':
        sesiones[chat_id]['file_id_portada'] = fid
        await mostrar_configurador_nfc(chat_id, context)

    elif paso == 'esperando_pago':
        s = sesiones[chat_id]
        txt_admin = f"🚨 NUEVA ORDEN (${s['total_temporal']})\n👤 {s['cliente']}\n"
        for i in s['carrito']:
            txt_admin += f"- {i['nombre']} ({'NFC' if i['nfc'] else 'No'})\n"
        
        kb = [[InlineKeyboardButton("✅ APROBAR", callback_data=f"aprob|{chat_id}")],
              [InlineKeyboardButton("❌ RECHAZAR", callback_data=f"rech|{chat_id}")]]
        
        if s.get('file_id_portada'):
            await context.bot.send_photo(ADMIN_ID, s['file_id_portada'], caption="🎨 DISEÑO CLIENTE")
            
        await context.bot.send_photo(ADMIN_ID, fid, caption=txt_admin, reply_markup=InlineKeyboardMarkup(kb))
        await context.bot.send_message(chat_id, "📩 ¡Recibido! Estamos verificando tu comprobante.")

if __name__ == '__main__':
    mostrar_banner()
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CallbackQueryHandler(manejar_callback))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), manejar_texto))
    app.add_handler(MessageHandler(filters.PHOTO, manejar_foto))
    app.run_polling()