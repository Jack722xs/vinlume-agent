from config import LINK_INSTAGRAM

MSG_BIENVENIDA = "💿 VINLUME DISK Chile 💿\n\nHola {nombre}. Bienvenido a nuestra tienda de llaveros personalizados.\nSelecciona una opción 👀:"
MSG_PASO_1 = "💿 Paso 1:\n\n¡Genial! Empecemos. ¿Cuántos llaveros deseas pedir?"
MSG_PASO_2_SINGLE = "Por favor, escribe el nombre del Artista y del Álbum:\n \nEjemplo: Twenty One Pilots - Trench"
MSG_PASO_2_MULTI = "Por favor, escribe la lista de los {cant} álbumes (uno por línea o separados por comas).\n\nEjemplo:\nBad Bunny - Un Verano Sin ti\nLinkin Park - Meteora"
MSG_INFO_NFC = "📲 Paso 3: Tecnología NFC\n\nAquí puedes activar el chip inteligente para cada llavero. Toca el botón del álbum para activarlo/desactivarlo.\n llavero NORMAL= $4000\n llavero Con NFC= $5000\n\n"
MSG_QUE_ES_NFC = "📲 ¿Qué es NFC?\n\nEs un chip invisible dentro del llavero. \nAl acercar tu celular, se abre automáticamente el álbum en Spotify, YouTube o el link que tú quieras. ¡Sin usar la cámara, solo por contacto! ✨"
MSG_CONTACTO_HUMANO = f"👤 Contacto Directo\n\nPara pedidos mayoristas (+20 unidades), diseños complejos o dudas específicas, escríbenos directo:\n\n👉 {LINK_INSTAGRAM}"
MSG_INFO_GENERAL = ("ℹ️ INFORMACIÓN Y PRECIOS\n\n"
               "• Normal ($4.000): Llavero con la portada en alta calidad.\n"
               "• Con NFC ($5.000): Incluye chip inteligente para escanear con el celular.\n\n"
               "🚚 Enviamos a todo Chile 📤.\n\n"
               "💡 ¿Tienes dudas? Puedes escribirme tu pregunta aquí mismo y te responderé. O si estás listo, toca abajo:")
MSG_SELECCION_REGION = "🚚 **Selecciona tu Región de Envío**\n\nEl precio se sumará automáticamente a tu total."

MSG_CONFIRMACION_DATOS = ("📋 CONFIRMA TUS DATOS\n\n"
           "Por favor revisa que todo esté correcto para el envío 👀:\n\n"
           "📍 **Zona:** {zona} (${precio_envio})\n"
           "📞 **Teléfono:** {telefono}\n"
           "📧 **Email:** {email}\n"
           "🏠 **Dirección:** {direccion}\n\n"
           "💰 **Total Productos:** ${total_productos}\n"
           "🚚 **Envío:** ${precio_envio}\n"
           "⭐️ **TOTAL FINAL:** ${total_final}\n\n"
           "¿Están bien los datos? \n 👇👇👇")


MSG_RESUMEN_PAGO = ("💳 RESUMEN FINAL\n==================================================\n"
               "💵 Subtotal: ${subtotal}\n"
               "{texto_descuento}"
               "⭐️ **TOTAL A PAGAR: ${total}**\n\n"
               "🏦 Datos de Transferencia:\n"
               "• Banco: Banco Estado\nCuenta: CuentaRUT\n"
               "• Nombre: JACK MAURO CARDENAS GARCIA\n"
               "• Rut: 21221234-5\n\n==================================================\n\n"
               "📸 Por favor, envía aquí tu comprobante de pago.\n (📸 Como Imagen)")

MSG_PAGO_APROBADO = ("🎉 ¡Pago Aprobado!\n\n"
                             "👍 Tu código de seguimiento es: #{order_id}\nGuardalo bien para cualquier consulta futura.\n\n"
                             "Tu pedido ya pasó a producción .\n\n"
                             "Para pedir nuevamente, toca aquí: /start \n\n"
                             f" ahora estamos a tu servicio. Cualquier duda, contáctanos en:\n{LINK_INSTAGRAM}")

MSG_PAGO_RECHAZADO = (f"❌ Tu pago no pudo ser verificado.\n\n"
                           f"Para más información y dudas hablar por interno a:\n{LINK_INSTAGRAM}\n\n para iniciar un nuevo pedido, toca aquí: /start")