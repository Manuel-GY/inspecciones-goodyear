import streamlit as st
import pandas as pd
import plotly.express as px
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import pytz
import json

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="KPI Goodyear", layout="wide")

# Listado de Inspectores
equipo = [
    "Nelson Ingles", "Sergio Muñoz", "Javier Pincheira", 
    "Angel Arape", "Marco Uribe", "Jose Saez", "Jaime Plaza",
    "Cristian Curin", "Manuel Rivera", "Claudio Ramirez", 
    "Christian Zuñiga", "Carlos Silva", "Enzo Muñoz",
    "Luis Mella", "Marco Yañez"
]

# Listado de Máquinas / Zonas
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

# --- 2. CONEXIÓN ---
def conectar_google():
    creds_dict = json.loads(st.secrets["gcp_service_account"])
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    return client.open("Base Datos Inspecciones Goodyear").sheet1

# --- 3. INTERFAZ ---
st.title("🛡️ Sistema de Gestión Goodyear")
tab1, tab2, tab3 = st.tabs(["📥 Registro", "🚜 Estado Máquinas", "👤 KPI Personal"])

with tab1:
    st.header("Cargar Inspección")
    with st.container(border=True):
        col1, col2 = st.columns(2)
        with col1:
            zona_sel = st.selectbox("Máquina/Zona:", zonas_reales)
        with col2:
            ins_sel = st.selectbox("Inspector:", equipo)
        archivo = st.file_uploader("Evidencia (opcional):", type=['xlsx', 'pdf', 'png', 'jpg', 'csv'])
    
    if st.button("🚀 Confirmar Registro"):
        try:
            with st.spinner("Registrando..."):
                ahora = datetime.now(pytz.timezone('America/Santiago'))
                mes_es = meses_traduccion.get(ahora.strftime("%B"))
                nueva_fila = [
                    ahora.strftime("%Y-%m-%d %H:%M"), 
                    ins_sel, 
                    zona_sel, 
                    mes_es, 
                    ahora.year, 
                    archivo.name if archivo else "Sin archivo"
                ]
                sheet = conectar_google()
                sheet.append_row(nueva_fila)
                st.success(f"OK: {zona_sel} registrada por {ins_sel}.")
        except Exception as e:
            st.error(f"Error: {e}")

# Obtención de datos
try:
    sheet = conectar_google()
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
            bg = '#c6efce' if val == "OK" else '#ffc7ce' # Colores pastel tipo Excel
            color = '#006100' if val == "OK" else '#9c0006'
            return f'background-color: {bg}; color: {color}; font-weight: bold; border: 1px solid white'

        st.dataframe(matriz_m.style.applymap(color_m), use_container_width=True, height=650)
    else:
        st.info("Sin registros.")

with tab3:
    st.header("👤 KPI por Persona")
    if not df_anio.empty:
        # Cada registro = 25% de meta individual
        pivot_p = df_anio.groupby(['Nombre', 'Mes']).size().unstack(fill_value=0)
        pivot_p = pivot_p.reindex(index=equipo, columns=meses_orden, fill_value=0)
        matriz_p = (pivot_p * 25).clip(upper=100)

        def color_p(val):
            if val >= 100: color = '#92d050'
            elif val >= 50: color = '#ffff00'
            elif val > 0: color = '#ffc000'
            else: color = '#ff5050'
            return f'background-color: {color}; color: black'

        st.write("### Cumplimiento Individual %")
        st.dataframe(matriz_p.style.applymap(color_p).format("{:.0f}%"), use_container_width=True)
        
        # Resumen gráfico
        st.divider()
        df_mes = matriz_p[mes_actual].reset_index()
        df_mes.columns = ['Nombre', 'Porcentaje']
        fig = px.bar(df_mes, x='Porcentaje', y='Inspector', orientation='h', 
                     range_x=[0, 100], color='Porcentaje', 
                     color_continuous_scale='RdYlGn', text_auto=True,
                     title=f"Avance del Mes: {mes_actual}")
        st.plotly_chart(fig, use_container_width=True)
    else:

        st.info("Sin datos de inspectores.")

