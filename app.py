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

zonas_disponibles = ["Zona Norte", "Zona Sur", "Planta", "Bodega", "Patio", "Maestranza"]

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
    st.header("Nueva Carga de Datos")
    with st.container(border=True):
        col1, col2 = st.columns(2)
        with col1:
            ins_sel = st.selectbox("Seleccione Inspector:", equipo)
        with col2:
            zona_sel = st.selectbox("Seleccione Zona inspeccionada:", zonas_disponibles)
        
        archivo = st.file_uploader("Seleccionar archivo de respaldo:", type=['xlsx', 'pdf', 'png', 'jpg', 'csv'])
    
    if archivo and st.button("🚀 Confirmar Registro (+25%)"):
        try:
            with st.spinner("Registrando en la base de datos..."):
                ahora = datetime.now(pytz.timezone('America/Santiago'))
                
                # Datos a guardar: Fecha, Inspector, Zona, Mes, Año, Nombre Archivo
                nueva_fila = [
                    ahora.strftime("%Y-%m-%d %H:%M"), 
                    ins_sel, 
                    zona_sel, 
                    ahora.strftime("%B"), 
                    ahora.year, 
                    archivo.name 
                ]
                
                sheet = conectar_google()
                sheet.append_row(nueva_fila)
                
                st.success(f"✅ ¡Registro exitoso! {ins_sel} ha inspeccionado {zona_sel}.")
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
                # Matriz Principal por Inspector
                pivot = df_anio.groupby(['Inspector', 'Mes']).size().unstack(fill_value=0)
                pivot = pivot.reindex(index=equipo, columns=meses_orden, fill_value=0)
                matriz_kpi = (pivot * 25).clip(upper=100)

                def color_semaforo(val):
                    if val >= 100: color = '#92d050'
                    elif val >= 50: color = '#ffff00'
                    elif val > 0: color = '#ffc000'
                    else: color = '#ff5050'
                    return f'background-color: {color}; color: black'

                st.write(f"### Cumplimiento Mensual % ({anio_act})")
                st.dataframe(matriz_kpi.style.applymap(color_semaforo).format("{:.0f}%"), use_container_width=True)
                
                st.divider()
                
                # Detalle por Zonas
                st.subheader("🔍 Detalle por Zonas este mes")
                mes_actual = datetime.now(pytz.timezone('America/Santiago')).strftime("%B")
                df_mes = df_anio[df_anio['Mes'] == mes_actual]
                
                if not df_mes.empty:
                    fig = px.bar(df_mes, x="Inspector", color="Zona", title=f"Inspecciones realizadas en {mes_actual}",
                                 barmode="group", text_auto=True)
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info(f"No hay inspecciones registradas en {mes_actual} aún.")
            
            with st.expander("📄 Ver Bitácora Completa (Últimos registros)"):
                st.dataframe(df.tail(15), use_container_width=True)
        else:
            st.info("Aún no hay datos registrados.")
    except Exception as e:
        st.warning("Cargando matriz...")