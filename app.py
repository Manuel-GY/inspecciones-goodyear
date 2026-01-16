import streamlit as st
import pandas as pd
import plotly.express as px
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import pytz
import json

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="KPI Goodyear - Control por Máquina", layout="wide")

# Equipo Actualizado
equipo = [
    "Cristian Curin", "Manuel Rivera", "Claudio Ramirez", 
    "Christian Zuñiga", "Carlos Silva", "Enzo Muñoz",
    "Luis Mella", "Marco Yañez"
]

# Zonas/Máquinas desglosadas individualmente
zonas_reales = [
    "Crane 1-6", "Crane 7-11", "LR 1-2", "UR 1-2", 
    "Z12", "Z13", "CC01", "CC02", "CC03", 
    "Press Delivery", "Plummers"
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
st.title("🛡️ Control de Inspecciones por Máquina - Goodyear")
tab1, tab2 = st.tabs(["📥 Registro de Inspección", "📊 Matriz de Máquinas"])

with tab1:
    st.header("Cargar Nueva Revisión")
    with st.container(border=True):
        col1, col2 = st.columns(2)
        with col1:
            zona_sel = st.selectbox("Seleccione Máquina/Zona:", zonas_reales)
        with col2:
            ins_sel = st.selectbox("Inspector Responsable:", equipo)
        
        archivo = st.file_uploader("Evidencia de la revisión:", type=['xlsx', 'pdf', 'png', 'jpg', 'csv'])
    
    if st.button("🚀 Registrar Inspección"):
        try:
            with st.spinner("Guardando en base de datos..."):
                ahora = datetime.now(pytz.timezone('America/Santiago'))
                mes_espanol = meses_traduccion.get(ahora.strftime("%B"))
                nombre_archivo = archivo.name if archivo else "Sin archivo"
                
                nueva_fila = [
                    ahora.strftime("%Y-%m-%d %H:%M"), 
                    ins_sel, zona_sel, mes_espanol, ahora.year, nombre_archivo
                ]
                
                sheet = conectar_google()
                sheet.append_row(nueva_fila)
                st.success(f"✅ Máquina {zona_sel} marcada como inspeccionada.")
                st.balloons()
        except Exception as e:
            st.error(f"Error: {e}")

with tab2:
    st.header("📅 Matriz de Cobertura por Máquina")
    try:
        sheet = conectar_google()
        data = sheet.get_all_records()
        
        if data:
            df = pd.DataFrame(data)
            anio_act = datetime.now(pytz.timezone('America/Santiago')).year
            df_anio = df[df['Año'] == anio_act]
            
            # --- MATRIZ POR MÁQUINA ---
            # Agrupamos por Zona y Mes para saber si se inspeccionó
            pivot_maquina = df_anio.groupby(['Zona', 'Mes']).size().unstack(fill_value=0)
            pivot_maquina = pivot_maquina.reindex(index=zonas_reales, columns=meses_orden, fill_value=0)
            
            # Si el conteo es > 0, la máquina está OK (100%), si es 0, falta (0%)
            matriz_maquinas = pivot_maquina.applymap(lambda x: 100 if x > 0 else 0)

            def color_maquinas(val):
                color = '#92d050' if val == 100 else '#ff5050' # Verde si está ok, Rojo si falta
                return f'background-color: {color}; color: black; font-weight: bold'

            st.write(f"### Estado de Inspección Mensual - Año {anio_act}")
            st.write("Verde: Inspeccionada | Rojo: Pendiente")
            st.dataframe(
                matriz_maquinas.style.applymap(color_maquinas).format(lambda x: "OK" if x == 100 else "PENDIENTE"), 
                use_container_width=True
            )

            st.divider()
            
            # Gráfico de resumen del mes actual
            mes_actual_ingles = datetime.now(pytz.timezone('America/Santiago')).strftime("%B")
            mes_actual = meses_traduccion.get(mes_actual_ingles)
            
            st.subheader(f"Progreso de Cobertura Total: {mes_actual}")
            inspeccionadas = (matriz_maquinas[mes_actual] == 100).sum()
            total_maquinas = len(zonas_reales)
            porcentaje_total = (inspeccionadas / total_maquinas) * 100

            st.progress(porcentaje_total / 100)
            st.metric("Máquinas Cubiertas", f"{inspeccionadas} de {total_maquinas}", f"{porcentaje_total:.1f}% Total")

        else:
            st.info("No hay datos registrados aún.")
    except Exception as e:
        st.error(f"Error al cargar matriz: {e}")