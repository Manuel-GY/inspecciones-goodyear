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

# Equipo Actualizado (8 integrantes)
equipo = [
    "Cristian Curin", "Manuel Rivera", "Claudio Ramirez", 
    "Christian Zuñiga", "Carlos Silva", "Enzo Muñoz",
    "Luis Mella", "Marco Yañez"
]

# Zonas del sistema
zonas_reales = [
    "Crane 1-6", "Crane 7-11", "LR 1-2", "UR 1-2", 
    "Z12", "Z13", "CC01", "CC02", "CC03", 
    "Press Delivery", "Plummers"
]

# Diccionario de traducción para meses
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
tab1, tab2 = st.tabs(["📥 Registro", "📊 Análisis por Zona"])

with tab1:
    st.header("Registrar Nueva Inspección")
    with st.container(border=True):
        col1, col2 = st.columns(2)
        with col1:
            ins_sel = st.selectbox("Inspector:", equipo)
        with col2:
            zona_sel = st.selectbox("Zona a Inspeccionar:", zonas_reales)
        
        archivo = st.file_uploader("Evidencia (opcional):", type=['xlsx', 'pdf', 'png', 'jpg', 'csv'])
    
    if st.button("🚀 Confirmar Registro"):
        try:
            with st.spinner("Guardando..."):
                ahora = datetime.now(pytz.timezone('America/Santiago'))
                # Obtenemos mes en inglés para guardar y lo traducimos
                mes_ingles = ahora.strftime("%B")
                mes_espanol = meses_traduccion.get(mes_ingles, mes_ingles)
                
                nombre_archivo = archivo.name if archivo else "Sin archivo"
                
                nueva_fila = [
                    ahora.strftime("%Y-%m-%d %H:%M"), 
                    ins_sel, 
                    zona_sel, 
                    mes_espanol, 
                    ahora.year, 
                    nombre_archivo
                ]
                
                sheet = conectar_google()
                sheet.append_row(nueva_fila)
                st.success(f"✅ Inspección en {zona_sel} registrada por {ins_sel}.")
                st.balloons()
        except Exception as e:
            st.error(f"Error: {e}")

with tab2:
    st.header("📈 Estado de Cobertura de Zonas")
    try:
        sheet = conectar_google()
        data = sheet.get_all_records()
        
        if data:
            df = pd.DataFrame(data)
            ahora = datetime.now(pytz.timezone('America/Santiago'))
            mes_actual_ingles = ahora.strftime("%B")
            mes_actual = meses_traduccion.get(mes_actual_ingles, mes_actual_ingles)
            
            df_mes = df[(df['Mes'] == mes_actual) & (df['Año'] == ahora.year)]
            
            # 1. Gráfico por Zona
            st.subheader(f"Zonas Revisadas en {mes_actual}")
            
            conteo_zonas = df_mes['Zona'].value_counts().reindex(zonas_reales, fill_value=0).reset_index()
            conteo_zonas.columns = ['Zona', 'Cantidad']
            
            fig_zonas = px.bar(
                conteo_zonas, 
                x='Zona', 
                y='Cantidad',
                color='Cantidad',
                color_continuous_scale='Greens',
                text_auto=True,
                title="Frecuencia de Inspección por Área"
            )
            st.plotly_chart(fig_zonas, use_container_width=True)

            # 2. Matriz de Cumplimiento
            st.divider()
            st.subheader("Cumplimiento de Metas por Inspector")
            
            df_anio = df[df['Año'] == ahora.year]
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

        else:
            st.info("No hay datos para mostrar gráficos aún.")
    except Exception as e:
        st.warning(f"Error al cargar matriz: {e}")