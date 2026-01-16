import streamlit as st
import pandas as pd
import plotly.express as px
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import pytz
import json

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="KPI Goodyear - Control Zonas", layout="wide")

# Equipo Actualizado
equipo = [
    "Cristian Curin", 
    "Manuel Rivera", 
    "Claudio Ramirez", 
    "Christian Zuñiga", 
    "Carlos Silva", 
    "Enzo Muñoz"
]

# Zonas Separadas Individualmente
zonas_reales = [
    "Crane 1-6",
    "Crane 7-11",
    "LR 1-2",
    "UR 1-2",
    "Z12",
    "Z13",
    "CC01",
    "CC02",
    "CC03",
    "Press Delivery",
    "Plummers"
]

meses_orden = ["January", "February", "March", "April", "May", "June", 
               "July", "August", "September", "October", "November", "December"]

# --- 2. CONEXIÓN ---
def conectar_google():
    creds_dict = json.loads(st.secrets["gcp_service_account"])
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    return client.open("Base Datos Inspecciones Goodyear").sheet1

# --- 3. INTERFAZ ---
st.title("🛡️ Sistema de Cumplimiento Goodyear")
tab1, tab2 = st.tabs(["📥 Registro de Inspección", "📊 Matriz de Desempeño"])

with tab1:
    st.header("Carga de Actividad por Zona")
    with st.container(border=True):
        col1, col2 = st.columns(2)
        with col1:
            ins_sel = st.selectbox("Inspector:", equipo)
        with col2:
            zona_sel = st.selectbox("Zona Inspeccionada:", zonas_reales)
        
        archivo = st.file_uploader("Evidencia (opcional):", type=['xlsx', 'pdf', 'png', 'jpg', 'csv'])
    
    if st.button("🚀 Confirmar Registro de Zona (+25%)"):
        try:
            with st.spinner("Sincronizando con la base de datos..."):
                ahora = datetime.now(pytz.timezone('America/Santiago'))
                nombre_archivo = archivo.name if archivo else "Sin archivo"
                
                nueva_fila = [
                    ahora.strftime("%Y-%m-%d %H:%M"), 
                    ins_sel, 
                    zona_sel, 
                    ahora.strftime("%B"), 
                    ahora.year, 
                    nombre_archivo
                ]
                
                sheet = conectar_google()
                sheet.append_row(nueva_fila)
                
                st.success(f"✅ ¡Excelente! {ins_sel} ha completado la inspección en {zona_sel}.")
                st.balloons()
        except Exception as e:
            st.error(f"Error al registrar: {e}")

with tab2:
    st.header("📅 Matriz de Desempeño Mensual")
    try:
        sheet = conectar_google()
        data = sheet.get_all_records()
        
        if data:
            df = pd.DataFrame(data)
            df_anio = df[df['Año'] == datetime.now().year]
            
            if not df_anio.empty:
                # Tabla de porcentajes
                pivot = df_anio.groupby(['Inspector', 'Mes']).size().unstack(fill_value=0)
                pivot = pivot.reindex(index=equipo, columns=meses_orden, fill_value=0)
                matriz_kpi = (pivot * 25).clip(upper=100)

                def color_semaforo(val):
                    if val >= 100: color = '#92d050'
                    elif val >= 50: color = '#ffff00'
                    elif val > 0: color = '#ffc000'
                    else: color = '#ff5050'
                    return f'background-color: {color}; color: black'

                st.dataframe(matriz_kpi.style.applymap(color_semaforo).format("{:.0f}%"), use_container_width=True)
                
                st.divider()
                
                # Visualización de Zonas Cubiertas
                st.subheader("📍 Cobertura de Zonas por Inspector")
                fig = px.bar(df_anio, x="Inspector", color="Zona", 
                             title="Historial de Zonas revisadas",
                             text_auto=True)
                st.plotly_chart(fig, use_container_width=True)
            
            with st.expander("📄 Ver Bitácora de Registros"):
                st.dataframe(df.tail(20), use_container_width=True)
        else:
            st.info("Sin registros actuales.")
    except Exception as e:
        st.warning("Cargando datos...")