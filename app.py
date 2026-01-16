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

equipo = ["Carlos Silva", "Marco Yañez", "Luis Mella", "Cristian Curin", 
          "Enzo Muñoz", "Manuel Rivera", "Claudio Ramirez", "Christian Zuñiga"]

meses_orden = ["January", "February", "March", "April", "May", "June", 
               "July", "August", "September", "October", "November", "December"]

def conectar_google():
    creds_dict = json.loads(st.secrets["gcp_service_account"])
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    return client.open("Base Datos Inspecciones Goodyear").sheet1

# --- 2. INTERFAZ ---
st.title("🛡️ Panel de Cumplimiento Goodyear")
tab1, tab2 = st.tabs(["📥 Subir Inspección", "📊 Matriz de Cumplimiento Anual"])

with tab1:
    st.header("Registro de Actividad")
    with st.container(border=True):
        ins_sel = st.selectbox("Seleccione Inspector:", equipo)
        zona_sel = st.selectbox("Zona:", ["Zona Norte", "Zona Sur", "Planta", "Bodega", "Patio"])
        archivo = st.file_uploader("Subir respaldo:", type=['xlsx', 'pdf', 'png', 'jpg'])
    
    if archivo and st.button("🚀 Registrar Inspección (+25%)"):
        try:
            ahora = datetime.now(pytz.timezone('America/Santiago'))
            nueva_fila = [ahora.strftime("%Y-%m-%d %H:%M"), ins_sel, zona_sel, ahora.strftime("%B"), ahora.year, archivo.name]
            sheet = conectar_google()
            sheet.append_row(nueva_fila)
            st.success(f"¡Registro exitoso para {ins_sel}!")
            st.balloons()
        except Exception as e:
            st.error(f"Error: {e}")

with tab2:
    st.header("📅 Matriz de Desempeño Anual")
    try:
        sheet = conectar_google()
        data = sheet.get_all_records()
        if data:
            df = pd.DataFrame(data)
            anio_actual = datetime.now().year
            df_anio = df[df['Año'] == anio_actual]

            # --- CÁLCULO DE LA MATRIZ ---
            # Agrupamos por Inspector y Mes, contando registros
            pivot = df_anio.groupby(['Inspector', 'Mes']).size().unstack(fill_value=0)
            
            # Aseguramos que todos los inspectores y meses existan en la tabla
            pivot = pivot.reindex(index=equipo, columns=meses_orden, fill_value=0)
            
            # Convertimos conteo a porcentaje (Cada uno vale 25%, máximo 100%)
            matriz_kpi = (pivot * 25).clip(upper=100)

            # Agregamos columna de Promedio Anual (Total)
            matriz_kpi['PROMEDIO TOTAL'] = matriz_kpi.mean(axis=1).round(1)

            # --- APLICAR COLORES (ESTILO EXCEL) ---
            def color_semaforo(val):
                if isinstance(val, str): return ''
                if val >= 100: color = '#92d050' # Verde
                elif val >= 50: color = '#ffff00' # Amarillo
                elif val > 0: color = '#ffc000' # Naranja
                else: color = '#ff5050' # Rojo
                return f'background-color: {color}; color: black; border: 1px solid white'

            st.write(f"### Cumplimiento % - Año {anio_actual}")
            st.dataframe(matriz_kpi.style.applymap(color_semaforo).format("{:.0f}%"), use_container_width=True)

            st.divider()

            # --- GRÁFICO DE PROGRESO DEL MES ACTUAL ---
            mes_actual = datetime.now(pytz.timezone('America/Santiago')).strftime("%B")
            st.subheader(f"Detalle de {mes_actual}")
            
            conteo_mes = matriz_kpi[mes_actual].reset_index()
            conteo_mes.columns = ['Inspector', 'Porcentaje']
            
            fig = px.bar(conteo_mes, x='Porcentaje', y='Inspector', orientation='h',
                         title=f"Progreso Mensual %", color='Porcentaje',
                         range_x=[0, 100], color_continuous_scale='RdYlGn', text_auto=True)
            st.plotly_chart(fig, use_container_width=True)
            
        else:
            st.info("No hay datos registrados aún.")
    except Exception as e:
        st.warning("Cargando matriz de datos...")