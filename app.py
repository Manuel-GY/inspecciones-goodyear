import streamlit as st
import pandas as pd
import plotly.express as px
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import pytz
import json

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Gestión Inspecciones Goodyear", layout="wide")

equipo = ["Carlos Silva", "Marco Yañez", "Luis Mella", "Cristian Curin", 
          "Enzo Muñoz", "Manuel Rivera", "Claudio Ramirez", "Christian Zuñiga"]

zonas_inspeccion = ["Zona Norte", "Zona Sur", "Planta Principal", "Bodega", "Patio de Maniobras"]

# --- 2. CONEXIÓN ---
def conectar_google():
    creds_dict = json.loads(st.secrets["gcp_service_account"])
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    # Asegúrate de que tu hoja de Google se llame así exactamente
    return client.open("Base Datos Inspecciones Goodyear").sheet1

def obtener_fecha_local():
    return datetime.now(pytz.timezone('America/Santiago'))

# --- 3. INTERFAZ ---
st.title("🛡️ Panel de Inspecciones Goodyear")

tab1, tab2 = st.tabs(["📥 Subir Inspección", "📊 Estadísticas"])

with tab1:
    st.header("Registrar Nueva Inspección")
    
    with st.container(border=True):
        col1, col2 = st.columns(2)
        with col1:
            ins_sel = st.selectbox("Inspector:", equipo)
        with col2:
            zona_sel = st.selectbox("Zona:", zonas_inspeccion)
        
        archivo = st.file_uploader("Sube el archivo de respaldo (Excel o PDF)", type=['xlsx', 'csv', 'pdf'])
    
    if archivo:
        st.success(f"Archivo '{archivo.name}' listo para procesar.")
        
        if st.button("🚀 Confirmar y Sumar +1 Inspección"):
            with st.spinner("Guardando registro..."):
                try:
                    ahora = obtener_fecha_local()
                    
                    # CREAMOS UNA SOLA FILA (No importa el contenido del archivo)
                    nueva_fila = [
                        ahora.strftime("%Y-%m-%d %H:%M:%S"), # Fecha y Hora
                        ins_sel,                             # Nombre del Inspector
                        zona_sel,                            # Zona
                        ahora.strftime("%B"),                # Mes
                        ahora.year,                          # Año
                        archivo.name                         # Nombre del archivo como respaldo
                    ]
                    
                    sheet = conectar_google()
                    
                    # Si la hoja está totalmente vacía, ponemos encabezados primero
                    if not sheet.get_all_values():
                        encabezados = ["Fecha_Hora", "Inspector", "Zona", "Mes", "Año", "Archivo_Respaldo"]
                        sheet.insert_row(encabezados, 1)
                    
                    # Guardamos la inspección
                    sheet.append_row(nueva_fila)
                    
                    st.success(f"¡Hecho! Se sumó 1 inspección a {ins_sel}.")
                    st.balloons()
                except Exception as e:
                    st.error(f"Error al guardar: {e}")

with tab2:
    st.header("Resumen de Inspecciones")
    try:
        sheet = conectar_google()
        data = sheet.get_all_records()
        
        if data:
            df = pd.DataFrame(data)
            
            # Métricas
            c1, c2 = st.columns(2)
            c1.metric("Total General", len(df))
            c2.metric("Último Inspector", df['Inspector'].iloc[-1])

            # Gráfico simple de barras (Cuenta cuántas veces aparece cada nombre)
            df_conteo = df['Inspector'].value_counts().reset_index()
            df_conteo.columns = ['Inspector', 'Cantidad']
            
            fig = px.bar(df_conteo, x='Inspector', y='Cantidad', 
                         title="Total de Inspecciones Realizadas por Persona",
                         color='Inspector', text_auto=True)
            st.plotly_chart(fig, use_container_width=True)
            
            st.write("### Detalle de registros")
            st.dataframe(df, use_container_width=True)
        else:
            st.info("Aún no hay registros en la base de datos.")
    except:
        st.warning("Cargando datos desde la nube...")