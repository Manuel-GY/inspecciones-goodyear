import streamlit as st
import pandas as pd
import plotly.express as px
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

# SUSTITUYE ESTO POR EL ID DE TU CARPETA DE GOOGLE DRIVE
ID_CARPETA_RESPALDOS = "1_maVBnIQIV8hP-5h5WknvQcmx3KDSd8J?usp=drive_link" 

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
    
    metadata = {
        'name': nombre_archivo,
        'parents': [ID_CARPETA_RESPALDOS]
    }
    
    media = MediaIoBaseUpload(io.BytesIO(archivo_binario.getvalue()), 
                              mimetype=archivo_binario.type, 
                              resumable=True)
    
    archivo_en_drive = drive_service.files().create(body=metadata, media_body=media, fields='id, webViewLink').execute()
    return archivo_en_drive.get('webViewLink')

# --- 3. INTERFAZ ---
st.title("🛡️ Sistema de Gestión Goodyear")
tab1, tab2 = st.tabs(["📥 Carga de Inspección", "📊 Matriz de Cumplimiento"])

with tab1:
    st.header("Nueva Inspección")
    with st.container(border=True):
        ins_sel = st.selectbox("Inspector:", equipo)
        archivo = st.file_uploader("Subir respaldo (PDF, Excel, Foto):", type=['xlsx', 'pdf', 'png', 'jpg', 'csv'])
    
    if archivo and st.button("🚀 Registrar y Subir Archivo"):
        try:
            with st.spinner("Subiendo respaldo a la nube..."):
                ahora = datetime.now(pytz.timezone('America/Santiago'))
                nombre_final = f"{ins_sel}_{ahora.strftime('%Y%m%d_%H%M')}_{archivo.name}"
                
                # 1. Subir archivo físico a Google Drive y obtener LINK
                link_respaldo = subir_a_drive(archivo, nombre_final)
                
                # 2. Guardar registro en Google Sheets
                creds = obtener_creds()
                client = gspread.authorize(creds)
                sheet = client.open("Base Datos Inspecciones Goodyear").sheet1
                
                nueva_fila = [
                    ahora.strftime("%Y-%m-%d %H:%M"), 
                    ins_sel, 
                    "Planta", 
                    ahora.strftime("%B"), 
                    ahora.year, 
                    link_respaldo # Aquí guardamos la URL para consultar después
                ]
                
                sheet.append_row(nueva_fila)
                st.success(f"¡Inspección guardada! Archivo disponible en la base de datos.")
                st.balloons()
        except Exception as e:
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
            # Matriz de colores
            df_anio = df[df['Año'] == datetime.now().year]
            pivot = df_anio.groupby(['Inspector', 'Mes']).size().unstack(fill_value=0)
            pivot = pivot.reindex(index=equipo, columns=meses_orden, fill_value=0)
            matriz_kpi = (pivot * 25).clip(upper=100)

            def color_semaforo(val):
                if val >= 100: color = '#92d050'
                elif val >= 50: color = '#ffff00'
                elif val > 0: color = '#ffc000'
                else: color = '#ff5050'
                return f'background-color: {color}; color: black'

            st.write("### Cumplimiento Mensual %")
            st.dataframe(matriz_kpi.style.applymap(color_semaforo).format("{:.0f}%"), use_container_width=True)

            st.divider()
            
            # --- CONSULTA DE RESPALDOS ---
            st.subheader("🔗 Historial de Respaldos (Consultar)")
            # Mostramos los últimos registros con el Link clickeable
            df_consulta = df[['Fecha_Hora', 'Inspector', 'Archivo']].tail(15)
            
            # Configura la columna para que el link sea un botón azul
            st.dataframe(
                df_consulta, 
                column_config={"Archivo": st.column_config.LinkColumn("Ver Documento")},
                use_container_width=True,
                hide_index=True
            )
            
        else:
            st.info("No hay datos en la base de datos.")
    except Exception as e:
        st.error(f"Error al cargar matriz: {e}")