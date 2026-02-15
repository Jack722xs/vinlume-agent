import random
import google.generativeai as genai
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from config import GOOGLE_API_KEY, LINK_INSTAGRAM, MAX_PEDIDO_AUTOMATICO, ADMIN_ID
from src.ui import keyboards as kb
from src.ui import strings as txt
from src.services.itunes import buscar_portada_album
from src.services.email import enviar_correo_confirmacion
from src.services.sheets import registrar_venta_en_excel

genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel('models/gemini-2.5-flash-preview-09-2025')

sesiones = {}

async def reiniciar_sesion(chat_id, context):
    if chat_id in sesiones: del sesiones[chat_id]
    await context.bot.send_message(chat_id, "🔄 Operación reiniciada.", reply_markup=kb.kb_reiniciar())

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await context.bot.send_message(
        update.effective_chat.id,
        txt.MSG_BIENVENIDA.format(nombre=user.first_name),
        reply_markup=kb.kb_inicio()
    )

async def preguntar_cantidad(chat_id, context):
    sesiones[chat_id]['paso'] = 'esperando_cantidad'
    await context.bot.send_message(chat_id, txt.MSG_PASO_1, reply_markup=kb.kb_cantidad())

async def pedir_lista_albumes(chat_id, context):
    cant = sesiones[chat_id]['cantidad_meta']
    sesiones[chat_id]['paso'] = 'esperando_nombres'
    
    msg = f"💿 Paso 2:\n\nEntendido, será/n {cant} llavero/s.\n"
    if cant == 1:
        msg += txt.MSG_PASO_2_SINGLE
    else:
        msg += txt.MSG_PASO_2_MULTI.format(cant=cant)
    
    await context.bot.send_message(chat_id, msg, reply_markup=kb.kb_cancelar_unico())

async def mostrar_configurador_nfc(chat_id, context):
    ses = sesiones[chat_id]
    ses['paso'] = 'configurando_nfc'
    
    texto_base = txt.MSG_INFO_NFC
    total_precio = 0
    
    for idx, item in enumerate(ses['carrito']):
        estado = "✅ CON NFC" if item['nfc'] else "💿 Normal"
        precio_item = 5000 if item['nfc'] else 4000
        total_precio += precio_item
        texto_base += f"• {item['nombre']} → {estado}\n"

    ses['total_temporal'] = total_precio
    texto_base += f"\n💰 Total Actual: ${total_precio}"
    
    await context.bot.send_message(chat_id, texto_base, reply_markup=kb.kb_nfc_config(ses['carrito'], total_precio))

async def confirmar_datos(chat_id, context):
    s = sesiones[chat_id]
    msg = txt.MSG_CONFIRMACION_DATOS.format(telefono=s.get('telefono'), email=s.get('email'), direccion=s.get('direccion'))
    await context.bot.send_message(chat_id, msg, reply_markup=kb.kb_confirmar_datos())

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
        await context.bot.send_message(chat_id, txt.MSG_QUE_ES_NFC, reply_markup=kb.kb_volver_inicio())
        return
    elif data == 'start_human':
        await context.bot.send_message(chat_id, txt.MSG_CONTACTO_HUMANO, reply_markup=kb.kb_volver_inicio())  
    elif data == 'start_info':
        await context.bot.send_message(chat_id, txt.MSG_INFO_GENERAL, reply_markup=kb.kb_menu_info())
    
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
        await context.bot.send_message(chat_id, "📝 ¡Perfecto! Vamos con tus datos de envío.\n\n📞 ¿Cuál es tu número de teléfono?\n(Ejemplo: +569 912345678)")

    elif data.startswith('fix_'):
        campo = data.split('_')[1]
        sesiones[chat_id]['paso'] = f'esperando_{campo}'
        await context.bot.send_message(chat_id, f"✏️ Escribe tu nuevo {campo}:")

    elif data == 'datos_ok':
        s = sesiones[chat_id]
        s['paso'] = 'esperando_pago'
        msj = txt.MSG_RESUMEN_PAGO.format(total=s['total_temporal'])
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
                msj_exito = txt.MSG_PAGO_APROBADO.format(order_id=s['order_id'])
                await context.bot.send_message(id_cliente, msj_exito)
                await q.edit_message_caption(f"{q.message.caption}\n\n✅ APROBADO #{s['order_id']}")
            else:
                await q.edit_message_caption("⚠️ ERROR CRÍTICO EN BASE DE DATOS")
            del sesiones[id_cliente]

        elif accion == "rech":
            await context.bot.send_message(id_cliente, txt.MSG_PAGO_RECHAZADO)
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
                
                url = await buscar_portada_album(album)
                
                sesiones[chat_id]['carrito'].append({'nombre': album, 'nfc': False}) 
                if url:
                    sesiones[chat_id]['url_portada'] = url
                    await context.bot.send_photo(chat_id, url, caption=f"💿 Busqué: {album}\n¿Es correcta esta portada?", reply_markup=kb.kb_confirmar_portada())
                else:
                    await mostrar_configurador_nfc(chat_id, context)
            else:
                await context.bot.send_message(chat_id, resp.replace("CHAT:", ""), reply_markup=kb.kb_reiniciar())
        except:
            await context.bot.send_message(chat_id, "Hola, usa el menú para comenzar tu pedido.", reply_markup=kb.kb_reiniciar())
        return
    
    paso = sesiones[chat_id].get('paso')

    if paso == 'esperando_cantidad_manual':
        if text.isdigit():
            cant = int(text)
            if cant > MAX_PEDIDO_AUTOMATICO:
                await context.bot.send_message(chat_id, f"⚠️ ¡Wow! Para pedidos de {cant} unidades (Mayoristas), por favor contáctanos directamente por Instagram para coordinar stock y precios especiales.\n\n👉 {LINK_INSTAGRAM}", reply_markup=kb.kb_volver_inicio())
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
            url = await buscar_portada_album(items[0])
            if url:
                sesiones[chat_id]['url_portada'] = url
                await context.bot.send_photo(chat_id, url, caption=f"💿 Busqué: {items[0]}\n¿Es correcta esta portada?", reply_markup=kb.kb_confirmar_portada())
                return
        
        await mostrar_configurador_nfc(chat_id, context)
    
    elif paso == 'esperando_telefono':
        sesiones[chat_id]['telefono'] = text
        if 'email' in sesiones[chat_id]: await confirmar_datos(chat_id, context)
        else:
            sesiones[chat_id]['paso'] = 'esperando_email'
            await context.bot.send_message(chat_id, "📧 ¿Cuál es tu Email?\n(Ejemplo: jack@ejemplo.com)")

    elif paso == 'esperando_email':
        sesiones[chat_id]['email'] = text
        if 'direccion' in sesiones[chat_id]: await confirmar_datos(chat_id, context)
        else:
            sesiones[chat_id]['paso'] = 'esperando_direccion'
            await context.bot.send_message(chat_id, "🚚 ¿Cuál es tu dirección de envío?") #añadir sistema de gestion de pago de envios

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
        
        if s.get('file_id_portada'):
            await context.bot.send_photo(ADMIN_ID, s['file_id_portada'], caption="🎨 DISEÑO CLIENTE")
            
        await context.bot.send_photo(ADMIN_ID, fid, caption=txt_admin, reply_markup=kb.kb_admin_pago(chat_id))
        await context.bot.send_message(chat_id, "📩 ¡Recibido! Estamos verificando tu comprobante.")