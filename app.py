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

            # Cálculo de datos para el mes
            df_mes = df[df['Mes'] == mes_actual]
            conteo = df_mes['Inspector'].value_counts().reindex(equipo, fill_value=0).reset_index()
            conteo.columns = ['Inspector', 'Cantidad']
            conteo['Porcentaje'] = (conteo['Cantidad'] / 4 * 100).clip(upper=100)

            # 1. Gráfico de Barras de Cumplimiento %
            fig_progreso = px.bar(
                conteo, 
                x='Porcentaje', 
                y='Inspector', 
                orientation='h',
                title=f"Cumplimiento Grupal (%) - {mes_actual}",
                text=[f"{p}%" for p in conteo['Porcentaje']],
                color='Porcentaje',
                range_x=[0, 100],
                color_continuous_scale='RdYlGn' # De Rojo a Verde
            )
            st.plotly_chart(fig_progreso, use_container_width=True)

            st.divider()

            # 2. Barras de Progreso Individuales (Visual)
            st.write("### Detalle Individual")
            for _, row in conteo.iterrows():
                p = int(row['Porcentaje'])
                c_nom, c_bar = st.columns([1, 4])
                c_nom.write(f"**{row['Inspector']}**")
                c_bar.progress(p / 100)
                c_bar.caption(f"{row['Cantidad']} de 4 inspecciones — **{p}% de cumplimiento**")
            
            st.divider()
            
            # 3. Acumulado Anual
            st.subheader("Historial Total")
            st.dataframe(df, use_container_width=True)
            
        else:
            st.info("No hay datos registrados aún.")
    except Exception as e:
        st.warning("Cargando indicadores...")