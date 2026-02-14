import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from config import EMAIL_SENDER, EMAIL_PASSWORD, LINK_INSTAGRAM

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