import json
import datetime
import gspread
from google.oauth2.service_account import Credentials
from config import SHEET_ID

def limpiar_texto(texto):
    if not texto: return ""
    return str(texto)[:500].replace("\n", " | ").strip()

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