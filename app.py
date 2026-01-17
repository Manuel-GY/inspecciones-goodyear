import streamlit as st
import pandas as pd
import plotly.express as px
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from googleapiclient.discovery import build # Añadido para listar archivos
from datetime import datetime
import pytz
import json

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="KPI Goodyear", layout="wide")

# ID de la carpeta de Google Drive donde están tus archivos Excel/Formatos
ID_CARPETA_FORMATOS = "1_maVBnIQIV8hP-5h5WknvQcmx3KDSd8J" 

equipo = [
    "Nelson Ingles", "Sergio Muñoz", "Javier Pincheira", 
    "Angel Arape", "Marco Uribe", "Jose Saez", "Jaime Plaza",
    "Cristian Curin", "Manuel Rivera", "Claudio Ramirez", 
    "Christian Zuñiga", "Carlos Silva", "Enzo Muñoz",
    "Luis Mella", "Marco Yañez"
]

zonas_reales = [
    "Crane 1", "Crane 2", "Crane 3", "Crane 4", "Crane 5", "Crane 6",
    "Crane 7", "Crane 8", "Crane 9", "Crane 10", "Crane 11",
    "LR1", "LR2", "ULR1", "ULR2",
    "Z12", "Z13", "CC01", "CC02", "CC03", 
    "Press 400B", "Press 500A", "Press 500B", "Press 600A", "Press 600B",
    "Plummer 1", "Plummer 2", "Plummer 3"
]

meses_traduccion = {
    "January": "Enero", "February": "Febrero", "March": "Marzo", "April": "Abril",
    "May": "Mayo", "June": "Junio", "July": "Julio", "August": "Agosto",
    "September": "Septiembre", "October": "Octubre", "November": "Noviembre", "December": "Diciembre"
}

meses_orden = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", 
               "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]

# --- 2. CONEXIONES ---
def obtener_creds():
    creds_dict = json.loads(st.secrets["gcp_service_account"])
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    return ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)

def conectar_google_sheets():
    creds = obtener_creds()
    client = gspread.authorize(creds)
    return client.open("Base Datos Inspecciones Goodyear").sheet1

def listar_archivos_drive():
    creds = obtener_creds()
    service = build('drive', 'v3', credentials=creds)
    # Buscamos archivos dentro de la carpeta específica
    query = f"'{ID_CARPETA_FORMATOS}' in parents and trashed = false"
    results = service.files().list(q=query, fields="files(id, name, webViewLink)").execute()
    return results.get('files', [])

# --- 3. INTERFAZ ---
st.title("🛡️ Sistema de Gestión Goodyear")
tab1, tab2, tab3, tab4 = st.tabs(["📥 Registro", "🚜 Estado Máquinas", "👤 KPI Personal", "📁 Descarga de Formatos"])

with tab1:
    st.header("Cargar Inspección")
    with st.container(border=True):
        col1, col2 = st.columns(2)
        with col1:
            zona_sel = st.selectbox("Máquina/Zona:", zonas_reales)
        with col2:
            ins_sel = st.selectbox("Nombre:", equipo)
        archivo = st.file_uploader("Evidencia (Obligatorio):", type=['xlsx', 'pdf', 'png', 'jpg', 'csv'])
    
    if st.button("🚀 Confirmar Registro"):
        if archivo is None:
            st.warning("⚠️ No se puede registrar: Debe subir un archivo de evidencia para continuar.")
        else:
            try:
                with st.spinner("Registrando..."):
                    ahora = datetime.now(pytz.timezone('America/Santiago'))
                    mes_es = meses_traduccion.get(ahora.strftime("%B"))
                    nueva_fila = [ahora.strftime("%Y-%m-%d %H:%M"), ins_sel, zona_sel, mes_es, ahora.year, archivo.name]
                    sheet = conectar_google_sheets()
                    sheet.append_row(nueva_fila)
                    st.success(f"OK: {zona_sel} registrado por {ins_sel}.")
            except Exception as e:
                st.error(f"Error: {e}")

# Obtención de datos
try:
    sheet = conectar_google_sheets()
    df = pd.DataFrame(sheet.get_all_records())
    anio_act = datetime.now(pytz.timezone('America/Santiago')).year
    df_anio = df[df['Año'] == anio_act]
    mes_actual = meses_traduccion.get(datetime.now(pytz.timezone('America/Santiago')).strftime("%B"))
except:
    df_anio = pd.DataFrame()

with tab2:
    st.header("🚜 Estado de Máquinas")
    if not df_anio.empty:
        pivot_m = df_anio.groupby(['Zona', 'Mes']).size().unstack(fill_value=0)
        pivot_m = pivot_m.reindex(index=zonas_reales, columns=meses_orden, fill_value=0)
        matriz_m = pivot_m.applymap(lambda x: "OK" if x > 0 else "PENDIENTE")

        def color_m(val):
            bg = '#c6efce' if val == "OK" else '#ffc7ce' 
            color = '#006100' if val == "OK" else '#9c0006'
            return f'background-color: {bg}; color: {color}; font-weight: bold; border: 1px solid white'

        st.dataframe(matriz_m.style.applymap(color_m), use_container_width=True, height=650)
    else:
        st.info("Sin registros.")

with tab3:
    st.header("👤 KPI por Persona")
    if not df_anio.empty:
        pivot_p = df_anio.groupby(['Nombre', 'Mes']).size().unstack(fill_value=0)
        pivot_p = pivot_p.reindex(index=equipo, columns=meses_orden, fill_value=0)
        matriz_p = (pivot_p * 25).clip(upper=100)

        def color_p(val):
            if val >= 100: color = '#92d050'
            elif val >= 50: color = '#ffff00'
            elif val > 0: color = '#ffc000'
            else: color = '#ff5050'
            return f'background-color: {color}; color: black'

        st.dataframe(matriz_p.style.applymap(color_p).format("{:.0f}%"), use_container_width=True)
    else:
        st.info("Sin datos de inspectores.")

with tab4:
    st.header("📁 Formatos de Inspección (Excel)")
    st.write("Selecciona el formato que necesites para descargar:")
    try:
        archivos = listar_archivos_drive()
        if archivos:
            # Convertimos a DataFrame para mostrarlo bonito
            df_archivos = pd.DataFrame(archivos)
            df_archivos.columns = ['ID', 'Nombre del Formato', 'Link de Descarga']
            
            # Mostramos la tabla con links clickeables
            st.dataframe(
                df_archivos[['Nombre del Formato', 'Link de Descarga']],
                column_config={
                    "Link de Descarga": st.column_config.LinkColumn("Descargar / Abrir")
                },
                use_container_width=True,
                hide_index=True
            )
        else:
            st.warning("No se encontraron archivos en la carpeta de Drive.")
            st.info(f"Asegúrate de subir los Excel a la carpeta con ID: {ID_CARPETA_FORMATOS}")
    except Exception as e:
        st.error(f"Error al conectar con Drive: {e}")



