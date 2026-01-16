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

# --- 2. CONEXIÓN ---
def conectar_google():
    creds_dict = json.loads(st.secrets["gcp_service_account"])
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    return client.open("Base Datos Inspecciones Goodyear").sheet1

# --- 3. INTERFAZ ---
st.title("🛡️ Panel de Cumplimiento Goodyear")
tab1, tab2 = st.tabs(["📥 Registro de Inspección", "📊 Matriz de Desempeño"])

with tab1:
    st.header("Nueva Carga")
    with st.container(border=True):
        ins_sel = st.selectbox("Seleccione Inspector:", equipo)
        archivo = st.file_uploader("Subir respaldo (solo para registro):", type=['xlsx', 'pdf', 'png', 'jpg', 'csv'])
    
    if archivo and st.button("🚀 Confirmar Registro (+25%)"):
        try:
            with st.spinner("Registrando en la base de datos..."):
                ahora = datetime.now(pytz.timezone('America/Santiago'))
                
                # Preparamos los datos (Guardamos solo el nombre del archivo como texto)
                nueva_fila = [
                    ahora.strftime("%Y-%m-%d %H:%M"), 
                    ins_sel, 
                    "Planta", 
                    ahora.strftime("%B"), 
                    ahora.year, 
                    archivo.name # Solo guardamos el nombre del archivo
                ]
                
                sheet = conectar_google()
                sheet.append_row(nueva_fila)
                
                st.success(f"¡Registro exitoso! {ins_sel} ha sumado 25% a su meta mensual.")
                st.balloons()
        except Exception as e:
            st.error(f"Error al conectar con la base de datos: {e}")

with tab2:
    st.header("📅 Matriz de Cumplimiento Anual")
    try:
        sheet = conectar_google()
        data = sheet.get_all_records()
        
        if data:
            df = pd.DataFrame(data)
            anio_act = datetime.now().year
            df_anio = df[df['Año'] == anio_act]
            
            if not df_anio.empty:
                # Crear Matriz (Pivote)
                pivot = df_anio.groupby(['Inspector', 'Mes']).size().unstack(fill_value=0)
                pivot = pivot.reindex(index=equipo, columns=meses_orden, fill_value=0)
                
                # Calcular % (Meta 4 = 100%)
                matriz_kpi = (pivot * 25).clip(upper=100)

                # Estilo de Colores (Semáforo)
                def color_semaforo(val):
                    if val >= 100: color = '#92d050' # Verde
                    elif val >= 50: color = '#ffff00' # Amarillo
                    elif val > 0: color = '#ffc000'   # Naranja
                    else: color = '#ff5050'           # Rojo
                    return f'background-color: {color}; color: black'

                st.write(f"### Reporte de Avance % - {anio_act}")
                st.dataframe(matriz_kpi.style.applymap(color_semaforo).format("{:.0f}%"), use_container_width=True)
                
                st.divider()
                
                # Gráfico de barras del mes actual
                mes_actual = datetime.now(pytz.timezone('America/Santiago')).strftime("%B")
                st.subheader(f"Progreso Detallado: {mes_actual}")
                
                df_mes_actual = matriz_kpi[mes_actual].reset_index()
                df_mes_actual.columns = ['Inspector', 'Cumplimiento']
                
                fig = px.bar(df_mes_actual, x='Cumplimiento', y='Inspector', orientation='h',
                             range_x=[0, 100], text_auto=True, color='Cumplimiento',
                             color_continuous_scale='RdYlGn')
                st.plotly_chart(fig, use_container_width=True)
            
            with st.expander("Ver historial de registros (Bitácora)"):
                st.dataframe(df.tail(20), use_container_width=True)
        else:
            st.info("Aún no hay datos registrados.")
    except Exception as e:
        st.warning("Cargando datos...")