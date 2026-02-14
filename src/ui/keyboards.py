from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def get_cancel_button():
    return InlineKeyboardButton("❌ Cancelar / Reiniciar", callback_data='cancel_order')

def get_back_button():
    return InlineKeyboardButton("🔙 Volver al Inicio", callback_data='back_start')

def kb_inicio():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🤖 Hacer Pedido", callback_data='start_bot')],
        [InlineKeyboardButton("👤 Hablar con Humano", callback_data='start_human')],
        [InlineKeyboardButton("❓ Info, Precios y Dudas", callback_data='start_info')]
    ])

def kb_reiniciar():
    return InlineKeyboardMarkup([[InlineKeyboardButton("💿 Iniciar Nuevo Pedido", callback_data='start_bot')]])

def kb_cantidad():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("1 Unidad 💿", callback_data='cant_1'), InlineKeyboardButton("2 Unidades 💿", callback_data='cant_2')],
        [InlineKeyboardButton("3 Unidades 💿", callback_data='cant_3'), InlineKeyboardButton("4 Unidades 💿", callback_data='cant_4')],
        [InlineKeyboardButton("Más de 4 (Escribir)", callback_data='cant_manual')],
        [get_back_button()]
    ])

def kb_cancelar_unico():
    return InlineKeyboardMarkup([[get_cancel_button()]])

def kb_nfc_config(carrito, total_precio):
    keyboard = []
    for idx, item in enumerate(carrito):
        btn_text = f"{idx+1}. {item['nombre'][:15]}... ({'NFC' if item['nfc'] else 'No'})"
        keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"toggle_{idx}")])
    
    keyboard.append([InlineKeyboardButton("🤔 ¿Qué es el NFC?", callback_data="what_is_nfc")])
    keyboard.append([InlineKeyboardButton("✅ Confirmar y Seguir", callback_data="confirm_nfc")])
    keyboard.append([get_cancel_button()])
    return InlineKeyboardMarkup(keyboard)

def kb_confirmar_datos():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Sí, todo perfecto", callback_data='datos_ok')],
        [InlineKeyboardButton("✏️ Corregir Teléfono", callback_data='fix_telefono')],
        [InlineKeyboardButton("✏️ Corregir Email", callback_data='fix_email')],
        [InlineKeyboardButton("✏️ Corregir Dirección", callback_data='fix_direccion')],
        [get_cancel_button()]
    ])

def kb_volver_inicio():
    return InlineKeyboardMarkup([[get_back_button()]])

def kb_menu_info():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💿 Hacer Pedido", callback_data='start_bot')],
        [InlineKeyboardButton("🤔 ¿Qué es NFC?", callback_data='what_is_nfc')],
        [InlineKeyboardButton("🔙 Volver al Inicio", callback_data='back_start')]
    ])

def kb_confirmar_portada():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Sí, es ese", callback_data='cover_si'), InlineKeyboardButton("🖼️ No (Subir mía)", callback_data='cover_manual')]
    ])

def kb_admin_pago(chat_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ APROBAR", callback_data=f"aprob|{chat_id}")],
        [InlineKeyboardButton("❌ RECHAZAR", callback_data=f"rech|{chat_id}")]
    ])