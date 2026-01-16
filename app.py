import streamlit as st
import pandas as pd
import plotly.express as px
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import pytz
import json

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Gestión Inspecciones Goodyear", layout="wide")

equipo = ["Carlos Silva", "Marco Yañez", "Luis Mella", "Cristian Curin", 
          "Enzo Muñoz", "Manuel Rivera", "Claudio Ramirez", "Christian Zuñiga"]

zonas_inspeccion = ["Zona Norte", "Zona Sur", "Planta Principal", "Bodega", "Patio de Maniobras"]

# --- CONEXIÓN SEGURA A GOOGLE SHEETS ---
def conectar_google():
    # Cargamos las credenciales desde los Secrets de Streamlit
    creds_json = json.loads(st.secrets["gcp_service_account"])
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_json, scope)
    client = gspread.authorize(creds)
    # Reemplaza con el nombre EXACTO de tu hoja de Google
    return client.open("Base Datos Inspecciones Goodyear").sheet1

def obtener_fecha_local():
    return datetime.now(pytz.timezone('America/Santiago'))

# --- INTERFAZ ---
st.title("🛡️ Panel de Inspecciones Goodyear")

tab1, tab2 = st.tabs(["📥 Subida de Archivos", "📊 Panel de Estadísticas"])

with tab1:
    st.header("Cargar Nueva Inspección")
    col1, col2 = st.columns(2)
    with col1:
        ins_sel = st.selectbox("Seleccione Inspector:", equipo)
    with col2:
        zona_sel = st.selectbox("Seleccione Zona:", zonas_inspeccion)
    
    archivo = st.file_uploader("Suba su archivo Excel con las inspecciones", type=['xlsx', 'csv'])
    
    if archivo:
        try:
            df_subido = pd.read_excel(archivo) if archivo.name.endswith('.xlsx') else pd.read_csv(archivo)
            st.write(f"Previsualización ({len(df_subido)} filas):")
            st.dataframe(df_subido.head(3))
            
            if st.button("🚀 Procesar y Guardar en la Nube"):
                with st.spinner("Guardando en la base de datos..."):
                    ahora = obtener_fecha_local()
                    df_subido['Fecha_Registro'] = ahora.strftime("%Y-%m-%d %H:%M:%S")
                    df_subido['Inspector'] = ins_sel
                    df_subido['Zona'] = zona_sel
                    df_subido['Mes'] = ahora.strftime("%B")
                    df_subido['Año'] = ahora.year
                    
                    # Enviar a Google Sheets
                    sheet = conectar_google()
                    # Si es la primera vez, enviamos encabezados
                    if not sheet.get_all_values():
                        sheet.insert_row(df_subido.columns.tolist(), 1)
                    
                    sheet.append_rows(df_subido.values.tolist())
                    
                    st.success(f"¡Hecho! Datos de {ins_sel} guardados permanentemente.")
                    st.balloons()
        except Exception as e:
            st.error(f"Error de conexión o lectura: {e}")

with tab2:
    try:
        sheet = conectar_google()
        data = sheet.get_all_records()
        if data:
            df_master = pd.DataFrame(data)
            
            # Métricas
            c1, c2, c3 = st.columns(3)
            c1.metric("Total Inspecciones", len(df_master))
            c2.metric("Promedio Mensual", round(len(df_master)/max(df_master['Mes'].nunique(),1), 2))
            c3.metric("Última subida", str(df_master['Fecha_Registro'].iloc[-1]))

            # Gráficos
            fig = px.bar(df_master, x='Inspector', color='Zona', title="Inspecciones Acumuladas por Equipo")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No hay datos en la base de datos de Google.")
    except:
        st.warning("Conectando con la nube de datos...")