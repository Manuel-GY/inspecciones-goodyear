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

def conectar_google():
    creds_dict = json.loads(st.secrets["gcp_service_account"])
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    return client.open("Base Datos Inspecciones Goodyear").sheet1

# --- 2. INTERFAZ ---
st.title("🛡️ Panel de Cumplimiento Goodyear")
tab1, tab2 = st.tabs(["📥 Subir Inspección", "📊 Dashboard de Metas"])

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
    st.header("📈 Cumplimiento Mensual (Meta: 4)")
    try:
        sheet = conectar_google()
        data = sheet.get_all_records()
        if data:
            df = pd.DataFrame(data)
            
            # Filtro Mes Actual
            mes_actual = datetime.now(pytz.timezone('America/Santiago')).strftime("%B")
            st.subheader(f"Progreso de {mes_actual}")

            # Cálculo de KPI por persona
            df_mes = df[df['Mes'] == mes_actual]
            conteo = df_mes['Inspector'].value_counts().reindex(equipo, fill_value=0).reset_index()
            conteo.columns = ['Inspector', 'Cantidad']
            
            # Visualización de Barras de Progreso (25% por unidad)
            for _, row in conteo.iterrows():
                # Calculamos el porcentaje
                unidades = row['Cantidad']
                porcentaje = min(int(unidades / 4 * 100), 100)
                
                c_nom, c_bar = st.columns([1, 4])
                c_nom.write(f"**{row['Inspector']}**")
                
                # Color dinámico: verde si llegó a la meta
                color_css = "stProgress > div > div > div > div { background-color: green; }" if porcentaje == 100 else ""
                st.markdown(f"<style>{color_css}</style>", unsafe_allow_html=True)
                
                c_bar.progress(porcentaje / 100)
                c_bar.caption(f"{unidades} de 4 inspecciones — **{porcentaje}% de cumplimiento**")
            
            st.divider()
            
            # Gráfico Comparativo Anual
            st.subheader("Acumulado Anual")
            fig_anio = px.bar(df['Inspector'].value_counts().reindex(equipo, fill_value=0).reset_index(), 
                             x='Inspector', y='count', title="Total de Inspecciones en el Año",
                             color='count', text_auto=True)
            st.plotly_chart(fig_anio, use_container_width=True)
            
        else:
            st.info("No hay datos registrados aún.")
    except Exception as e:
        st.warning("Cargando indicadores...")