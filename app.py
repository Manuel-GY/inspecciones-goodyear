import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from datetime import datetime
import pytz
import json
import io

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="KPI Goodyear - Cloud", layout="wide")

# TU ID DE CARPETA (Asegúrate que sea solo el código)
ID_CARPETA_RESPALDOS = "1_maVBnIQIV8hP-5h5WknvQcmx3KDSd8J" 

equipo = ["Carlos Silva", "Marco Yañez", "Luis Mella", "Cristian Curin", 
          "Enzo Muñoz", "Manuel Rivera", "Claudio Ramirez", "Christian Zuñiga"]

meses_orden = ["January", "February", "March", "April", "May", "June", 
               "July", "August", "September", "October", "November", "December"]

# --- 2. CONEXIONES ---
def obtener_creds():
    creds_dict = json.loads(st.secrets["gcp_service_account"])
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    return ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)

def subir_a_drive(archivo_binario, nombre_archivo):
    creds = obtener_creds()
    drive_service = build('drive', 'v3', credentials=creds)
    
    file_metadata = {
        'name': nombre_archivo,
        'parents': [ID_CARPETA_RESPALDOS]
    }
    
    media = MediaIoBaseUpload(io.BytesIO(archivo_binario.getvalue()), 
                              mimetype=archivo_binario.type, 
                              resumable=True)
    
    # 1. Creamos el archivo
    archivo_en_drive = drive_service.files().create(
        body=file_metadata, 
        media_body=media, 
        fields='id, webViewLink',
        supportsAllDrives=True
    ).execute()
    
    file_id = archivo_en_drive.get('id')
    
    # 2. TRUCO PARA LA CUOTA: Hacer que el archivo sea público para quien tenga el link 
    # o simplemente asegurar que herede los permisos de la carpeta.
    permission = {
        'type': 'anyone',
        'role': 'reader',
    }
    drive_service.permissions().create(fileId=file_id, body=permission).execute()
    
    return archivo_en_drive.get('webViewLink')

# --- 3. INTERFAZ ---
st.title("🛡️ Sistema de Gestión Goodyear")
tab1, tab2 = st.tabs(["📥 Carga de Inspección", "📊 Matriz de Cumplimiento"])

with tab1:
    st.header("Nueva Inspección")
    with st.container(border=True):
        ins_sel = st.selectbox("Inspector:", equipo)
        archivo = st.file_uploader("Subir respaldo:", type=['xlsx', 'pdf', 'png', 'jpg', 'csv'])
    
    if archivo and st.button("🚀 Registrar y Subir"):
        try:
            with st.spinner("Subiendo respaldo..."):
                ahora = datetime.now(pytz.timezone('America/Santiago'))
                nombre_final = f"{ins_sel}_{ahora.strftime('%Y%m%d_%H%M')}_{archivo.name}"
                
                # Subir
                link_respaldo = subir_a_drive(archivo, nombre_final)
                
                # Guardar en Google Sheets
                creds = obtener_creds()
                client = gspread.authorize(creds)
                sheet = client.open("Base Datos Inspecciones Goodyear").sheet1
                
                nueva_row = [ahora.strftime("%Y-%m-%d %H:%M"), ins_sel, "Planta", ahora.strftime("%B"), ahora.year, link_respaldo]
                sheet.append_row(nueva_row)
                
                st.success("¡Guardado correctamente! El archivo ya está en tu Drive.")
                st.balloons()
        except Exception as e:
            if "storageQuotaExceeded" in str(e):
                st.error("Error de Espacio: Google no permite que el bot use su propio espacio. Por favor, asegúrate de que la carpeta de Drive esté compartida con el bot como EDITOR.")
            else:
                st.error(f"Error al procesar: {e}")

with tab2:
    st.header("📅 Seguimiento Anual")
    try:
        creds = obtener_creds()
        client = gspread.authorize(creds)
        sheet = client.open("Base Datos Inspecciones Goodyear").sheet1
        data = sheet.get_all_records()
        
        if data:
            df = pd.DataFrame(data)
            anio_act = datetime.now().year
            df_anio = df[df['Año'] == anio_act]
            
            if not df_anio.empty:
                pivot = df_anio.groupby(['Inspector', 'Mes']).size().unstack(fill_value=0)
                pivot = pivot.reindex(index=equipo, columns=meses_orden, fill_value=0)
                matriz = (pivot * 25).clip(upper=100)

                def color_semaforo(val):
                    if val >= 100: color = '#92d050'
                    elif val >= 50: color = '#ffff00'
                    elif val > 0: color = '#ffc000'
                    else: color = '#ff5050'
                    return f'background-color: {color}; color: black'

                st.dataframe(matriz.style.applymap(color_semaforo).format("{:.0f}%"), use_container_width=True)
            
            st.divider()
            st.subheader("🔗 Links de Respaldos")
            df_links = df[['Fecha_Hora', 'Inspector', 'Archivo']].tail(10)
            st.dataframe(df_links, column_config={"Archivo": st.column_config.LinkColumn("Ver Documento")}, use_container_width=True)
        else:
            st.info("No hay datos registrados.")
    except Exception as e:
        st.error(f"Error al cargar: {e}")