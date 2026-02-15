import random
import google.generativeai as genai
from telegram import Update
from telegram.ext import ContextTypes

from config import GOOGLE_API_KEY, LINK_INSTAGRAM, MAX_PEDIDO_AUTOMATICO, ADMIN_IDS, PRECIOS_ENVIO, CUPONES
from src.ui import keyboards as kb
from src.ui import strings as txt
from src.services.itunes import buscar_portada_album
from src.services.email import enviar_correo_confirmacion
from src.services.sheets import registrar_venta_en_excel

genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel('models/gemini-2.5-flash-preview-09-2025')

async def reiniciar_sesion(chat_id, context):
    context.user_data.clear()
    await context.bot.send_message(chat_id, "🔄 Operación reiniciada.", reply_markup=kb.kb_reiniciar())

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    context.user_data['cliente'] = user.first_name
    await context.bot.send_message(
        update.effective_chat.id,
        txt.MSG_BIENVENIDA.format(nombre=user.first_name),
        reply_markup=kb.kb_inicio()
    )

async def preguntar_cantidad(chat_id, context):
    context.user_data['paso'] = 'esperando_cantidad'
    await context.bot.send_message(chat_id, txt.MSG_PASO_1, reply_markup=kb.kb_cantidad())

async def pedir_lista_albumes(chat_id, context):
    cant = context.user_data['cantidad_meta']
    context.user_data['paso'] = 'esperando_nombres'
    
    msg = f"💿 Paso 2:\n\nEntendido, será/n {cant} llavero/s.\n"
    if cant == 1:
        msg += txt.MSG_PASO_2_SINGLE
    else:
        msg += txt.MSG_PASO_2_MULTI.format(cant=cant)
    
    await context.bot.send_message(chat_id, msg, reply_markup=kb.kb_cancelar_unico())

async def mostrar_configurador_nfc(chat_id, context):
    ses = context.user_data
    ses['paso'] = 'configurando_nfc'
    
    texto_base = txt.MSG_INFO_NFC
    total_productos = 0
    
    if 'carrito' not in ses: ses['carrito'] = []

    for idx, item in enumerate(ses['carrito']):
        estado = "✅ CON NFC" if item['nfc'] else "💿 Normal"
        precio_item = 5000 if item['nfc'] else 4000
        total_productos += precio_item
        texto_base += f"• {item['nombre']} → {estado}\n"

    ses['subtotal_productos'] = total_productos
    ses['total_temporal'] = total_productos 
    
    texto_base += f"\n💰 Subtotal Productos: ${total_productos}"
    
    await context.bot.send_message(chat_id, texto_base, reply_markup=kb.kb_nfc_config(ses['carrito'], total_productos))

async def confirmar_datos(chat_id, context):
    s = context.user_data
    costo_envio = s.get('precio_envio', 0)
    subtotal_prod = s.get('subtotal_productos', 0)
    descuento_aplicado = 0
    total_final = subtotal_prod + costo_envio
    
    cupon_activo = s.get('cupon_aplicado') 
    
    if cupon_activo:
        valor_cupon = CUPONES.get(cupon_activo)
        
        if valor_cupon == "GOD_MODE":
            descuento_aplicado = total_final # Descuenta todo
            total_final = 0
            msg_extra = "⚡️ Cupón DIOS: ¡TODO GRATIS!\n"
            
        elif valor_cupon == "FREE_SHIP":
            descuento_aplicado = costo_envio
            total_final = subtotal_prod 
            msg_extra = "🎟 Cupón: Envío Gratis\n"
            
        elif isinstance(valor_cupon, float):
            descuento_aplicado = int(subtotal_prod * valor_cupon)
            total_final = (subtotal_prod - descuento_aplicado) + costo_envio
            msg_extra = f"🎟 Cupón: -${descuento_aplicado}\n"
    else:
        msg_extra = ""

    s['total_temporal'] = total_final 
    s['descuento_valor'] = descuento_aplicado

    msg = txt.MSG_CONFIRMACION_DATOS.format(
        zona=s.get('zona_envio', 'No definida'),
        precio_envio=costo_envio,
        telefono=s.get('telefono'),
        email=s.get('email'),
        direccion=s.get('direccion'),
        total_productos=subtotal_prod,
        total_final=total_final
    )
    
    if cupon_activo:
        msg += f"\n✨ {msg_extra}"

    await context.bot.send_message(chat_id, msg, reply_markup=kb.kb_confirmar_datos(ya_tiene_cupon=bool(cupon_activo)))

async def manejar_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    chat_id = update.effective_chat.id
    data = q.data
    s = context.user_data
    
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
        s.clear()
        s['cliente'] = update.effective_user.first_name
        s['carrito'] = []
        await preguntar_cantidad(chat_id, context)

    elif data.startswith('cant_'):
        if data == 'cant_manual':
            s['paso'] = 'esperando_cantidad_manual'
            await context.bot.send_message(chat_id, "⌨️ Por favor, escribe el número de unidades (Máximo 20 por aquí):")
        else:
            cant = int(data.split('_')[1])
            s['cantidad_meta'] = cant
            await pedir_lista_albumes(chat_id, context)

    elif data == 'cover_si':
        await mostrar_configurador_nfc(chat_id, context)
    
    elif data == 'cover_manual':
        s['url_portada'] = "MANUAL"
        s['paso'] = 'esperando_foto'
        await context.bot.send_message(chat_id, "📸 ¡Vale! Envíame la imagen que quieres usar.")

    elif data.startswith('toggle_'):
        idx = int(data.split('_')[1])
        item = s['carrito'][idx]
        item['nfc'] = not item['nfc']
        await q.message.delete()
        await mostrar_configurador_nfc(chat_id, context)

    elif data == 'confirm_nfc':
        s['paso'] = 'esperando_telefono'
        await context.bot.send_message(chat_id, "📝 ¡Perfecto! Vamos con tus datos.\n\n📞 ¿Cuál es tu número de teléfono?\n(Ejemplo: +569 912345678)")

    elif data.startswith('region_'):
        zona_seleccionada = data.split('_')[1]
        precio = PRECIOS_ENVIO.get(zona_seleccionada, 0)
        s['zona_envio'] = zona_seleccionada
        s['precio_envio'] = precio
        s['paso'] = 'esperando_direccion'
        await context.bot.send_message(chat_id, f"✅ Zona: {zona_seleccionada} (${precio})\n\n🏠 Ahora escribe tu dirección exacta (Calle, Número, Comuna):")

    elif data.startswith('fix_'):
        campo = data.split('_')[1]
        if campo == 'direccion':
            s['paso'] = 'seleccionando_zona' 
            await context.bot.send_message(chat_id, txt.MSG_SELECCION_REGION, reply_markup=kb.kb_regiones())
        else:
            s['paso'] = f'esperando_{campo}'
            await context.bot.send_message(chat_id, f"✏️ Escribe tu nuevo {campo}:")

    elif data == 'ingresar_cupon':
        s['paso'] = 'esperando_cupon'
        await context.bot.send_message(chat_id, "🎟 Escribe tu código de descuento:")

    elif data == 'datos_ok':
        s['paso'] = 'esperando_pago'
        
        txt_descuento = ""
        if s.get('cupon_aplicado'):
            monto_desc = s.get('descuento_valor', 0)
            txt_descuento = f"🎟 Descuento ({s['cupon_aplicado']}): -${monto_desc}\n"
            
        sub_real = s.get('subtotal_productos', 0) + s.get('precio_envio', 0)

        msj = txt.MSG_RESUMEN_PAGO.format(
            subtotal=sub_real,
            texto_descuento=txt_descuento,
            total=s['total_temporal']
        )
        await context.bot.send_message(chat_id, msj)

    elif "|" in data:
        accion, id_cliente_str = data.split("|")
        id_cliente = int(id_cliente_str)
        try:
            s_cliente = context.application.user_data[id_cliente]
        except KeyError:
            await q.edit_message_caption("⚠️ Sesión expirada.")
            return
        
        if accion == "aprob":
            s_cliente['order_id'] = f"VD-{random.randint(10000, 99999)}"
            s_cliente['total'] = s_cliente['total_temporal']
            
            if registrar_venta_en_excel(s_cliente):
                if '@' in str(s_cliente.get('email')): enviar_correo_confirmacion(s_cliente['email'], s_cliente)
                msj_exito = txt.MSG_PAGO_APROBADO.format(order_id=s_cliente['order_id'])
                await context.bot.send_message(id_cliente, msj_exito)
                await q.edit_message_caption(f"{q.message.caption}\n\n✅ APROBADO #{s_cliente['order_id']}")
                s_cliente.clear()
            else:
                await q.edit_message_caption("⚠️ ERROR BASE DE DATOS")

        elif accion == "rech":
            await context.bot.send_message(id_cliente, txt.MSG_PAGO_RECHAZADO)
            await q.edit_message_caption("🚫 RECHAZADO")
            s_cliente.clear()

async def manejar_texto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    text = update.message.text
    s = context.user_data 
    
    if 'paso' not in s:
        prompt = f"Eres el asistente de Vinlume Disk. Cliente: '{text}'. Si es compra: COMPRA:Album. Si duda: CHAT:Respuesta"
        try:
            resp = model.generate_content(prompt).text
            if "COMPRA:" in resp:
                album = resp.split(":")[1].strip()
                s['cliente'] = update.effective_user.first_name
                s['carrito'] = []
                s['cantidad_meta'] = 1
                
                url = await buscar_portada_album(album)
                s['carrito'].append({'nombre': album, 'nfc': False}) 
                
                if url:
                    s['url_portada'] = url
                    await context.bot.send_photo(chat_id, url, caption=f"💿 Busqué: {album}\n¿Es correcta?", reply_markup=kb.kb_confirmar_portada())
                else:
                    s['url_portada'] = "MANUAL"
                    s['paso'] = 'esperando_foto'
                    await context.bot.send_message(chat_id, f"💿 Registré: {album}\n\nNo hallé la portada. 📸 Envíame la foto.")
            else:
                await context.bot.send_message(chat_id, resp.replace("CHAT:", ""), reply_markup=kb.kb_reiniciar())
        except:
            await context.bot.send_message(chat_id, "Usa el menú para comenzar.", reply_markup=kb.kb_reiniciar())
        return
    
    paso = s.get('paso')

    #VALIDACIÓN DE CUPÓN
    if paso == 'esperando_cupon':
        codigo = text.upper().strip() # Convertir a mayúsculas
        if codigo in CUPONES:
            s['cupon_aplicado'] = codigo
            await context.bot.send_message(chat_id, f"🎉 ¡Genial! Cupón {codigo} aplicado correctamente.")
            await confirmar_datos(chat_id, context)
        else:
            await context.bot.send_message(chat_id, "❌ Ese cupón no existe o expiró.\n¿Quieres intentar otro o seguir sin cupón?", 
                                           reply_markup=kb.kb_confirmar_datos(ya_tiene_cupon=False))

    elif paso == 'esperando_cantidad_manual':
        if text.isdigit():
            cant = int(text)
            if cant > MAX_PEDIDO_AUTOMATICO:
                await context.bot.send_message(chat_id, f"⚠️ Pedidos mayoristas en Instagram: {LINK_INSTAGRAM}", reply_markup=kb.kb_volver_inicio())
                s.clear() 
            elif cant > 0:
                s['cantidad_meta'] = cant
                await pedir_lista_albumes(chat_id, context)
            else:
                await context.bot.send_message(chat_id, "⚠️ Ingresa un número válido.")
        else:
            await context.bot.send_message(chat_id, "⚠️ Solo números.")

    elif paso == 'esperando_nombres':
        meta = s['cantidad_meta']
        items = [x.strip() for x in (text.split("\n") if "\n" in text else text.split(",")) if x.strip()]
        
        if len(items) != meta:
            await context.bot.send_message(chat_id, f"⚠️ Deben ser {meta} nombres. Revisar lista.")
            return
        
        s['carrito'] = [{'nombre': item, 'nfc': False} for item in items]
        
        if meta == 1:
            url = await buscar_portada_album(items[0])
            if url:
                s['url_portada'] = url
                await context.bot.send_photo(chat_id, url, caption=f"💿 Busqué: {items[0]}\n¿Es correcta?", reply_markup=kb.kb_confirmar_portada())
                return
            else:
                s['url_portada'] = "MANUAL"
                s['paso'] = 'esperando_foto'
                await context.bot.send_message(chat_id, f"💿 Registré: {items[0]}\n\nNo hallé la portada. 📸 Envíame la foto.")
                return
        
        await mostrar_configurador_nfc(chat_id, context)
    
    elif paso == 'esperando_telefono':
        s['telefono'] = text
        if 'email' in s: await confirmar_datos(chat_id, context)
        else:
            s['paso'] = 'esperando_email'
            await context.bot.send_message(chat_id, "📧 ¿Cuál es tu Email?")

    elif paso == 'esperando_email':
        s['email'] = text
        s['paso'] = 'seleccionando_zona'
        await context.bot.send_message(chat_id, txt.MSG_SELECCION_REGION, reply_markup=kb.kb_regiones())

    elif paso == 'esperando_direccion':
        s['direccion'] = text
        await confirmar_datos(chat_id, context)

async def manejar_foto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    s = context.user_data
    if 'paso' not in s: return
    paso = s.get('paso')
    fid = update.message.photo[-1].file_id

    if paso == 'esperando_foto':
        s['file_id_portada'] = fid
        await mostrar_configurador_nfc(chat_id, context)

    elif paso == 'esperando_pago':
        cupon_txt = f" (🎟 {s['cupon_aplicado']})" if s.get('cupon_aplicado') else ""
        txt_admin = f"🚨 NUEVA ORDEN (${s['total_temporal']}){cupon_txt}\n👤 {s['cliente']}\n📍 {s.get('zona_envio', '-')}\n"
        for i in s['carrito']:
            txt_admin += f"- {i['nombre']} ({'NFC' if i['nfc'] else 'No'})\n"
        
        for admin_id in ADMIN_IDS:
            try:
                if s.get('file_id_portada'):
                    await context.bot.send_photo(admin_id, s['file_id_portada'], caption="🎨 DISEÑO CLIENTE")
                await context.bot.send_photo(admin_id, fid, caption=txt_admin, reply_markup=kb.kb_admin_pago(chat_id))
            except: pass
        
        await context.bot.send_message(chat_id, "📩 ¡Recibido! Verificando comprobante.")