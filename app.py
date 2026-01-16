import streamlit as st
import pandas as pd
import plotly.express as px
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import pytz
import json

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="KPI Goodyear - Control Maquinaria", layout="wide")

# Equipo Actualizado (Incluyendo los nuevos ingresos)
equipo = [
    "Nelson Ingles", "Sergio Muñoz", "Javier Pincheira", 
    "Angel Arape", "Marcos Uribe", "Jose Saez", "Jaime Plaza",
    "Cristian Curin", "Manuel Rivera", "Claudio Ramirez", 
    "Christian Zuñiga", "Carlos Silva", "Enzo Muñoz",
    "Luis Mella", "Marco Yañez"
]

# Zonas Desglosadas (Cranes 1-11 + Racks separados + Otras zonas)
zonas_reales = [
    "Crane 1", "Crane 2", "Crane 3", "Crane 4", "Crane 5", "Crane 6",
    "Crane 7", "Crane 8", "Crane 9", "Crane 10", "Crane 11",
    "LR1", "LR2", "ULR1", "ULR2",
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
st.title("🛡️ Gestión de Inspecciones Goodyear")
tab1, tab2 = st.tabs(["📥 Registro de Inspección", "📊 Matriz por Máquina"])

with tab1:
    st.header("Cargar Nueva Revisión")
    with st.container(border=True):
        col1, col2 = st.columns(2)
        with col1:
            zona_sel = st.selectbox("Seleccione Máquina/Zona:", zonas_reales)
        with col2:
            ins_sel = st.selectbox("Inspector Responsable:", equipo)
        
        archivo = st.file_uploader("Evidencia (opcional):", type=['xlsx', 'pdf', 'png', 'jpg', 'csv'])
    
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
                st.success(f"✅ ¡Registro exitoso! {zona_sel} marcada como OK.")
                st.balloons()
        except Exception as e:
            st.error(f"Error al conectar: {e}")

with tab2:
    st.header("📅 Estado de Cobertura Mensual")
    try:
        sheet = conectar_google()
        data = sheet.get_all_records()
        
        if data:
            df = pd.DataFrame(data)
            anio_act = datetime.now(pytz.timezone('America/Santiago')).year
            df_anio = df[df['Año'] == anio_act]
            
            # --- MATRIZ POR MÁQUINA ---
            pivot_maquina = df_anio.groupby(['Zona', 'Mes']).size().unstack(fill_value=0)
            pivot_maquina = pivot_maquina.reindex(index=zonas_reales, columns=meses_orden, fill_value=0)
            
            # Estilo binario: OK (Verde) / PENDIENTE (Rojo)
            matriz_status = pivot_maquina.applymap(lambda x: 100 if x > 0 else 0)

            def color_maquinas(val):
                color = '#92d050' if val == 100 else '#ff5050'
                return f'background-color: {color}; color: black; font-weight: bold; border: 1px solid white'

            st.write(f"### Matriz de Máquinas - {anio_act}")
            st.dataframe(
                matriz_status.style.applymap(color_maquinas).format(lambda x: "OK" if x == 100 else "PENDIENTE"), 
                use_container_width=True
            )

            st.divider()
            
            # Gráfico de cobertura del mes actual
            ahora = datetime.now(pytz.timezone('America/Santiago'))
            mes_actual = meses_traduccion.get(ahora.strftime("%B"))
            
            st.subheader(f"Resumen de Cobertura: {mes_actual}")
            inspeccionadas = (matriz_status[mes_actual] == 100).sum()
            total_maquinas = len(zonas_reales)
            porcentaje = (inspeccionadas / total_maquinas) * 100

            st.progress(porcentaje / 100)
            col_kpi1, col_kpi2 = st.columns(2)
            col_kpi1.metric("Máquinas Listas", f"{inspeccionadas} de {total_maquinas}")
            col_kpi2.metric("Porcentaje Total", f"{porcentaje:.1f}%")

        else:
            st.info("No hay registros en la base de datos.")
    except Exception as e:
        st.error(f"Error al cargar datos: {e}")