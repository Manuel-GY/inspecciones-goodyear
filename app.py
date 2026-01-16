import streamlit as st
import pandas as pd
import plotly.express as px
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import pytz
import json

# --- 1. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Gestión Inspecciones Goodyear", layout="wide")

# Datos Maestros
equipo = ["Carlos Silva", "Marco Yañez", "Luis Mella", "Cristian Curin", 
          "Enzo Muñoz", "Manuel Rivera", "Claudio Ramirez", "Christian Zuñiga"]

zonas_inspeccion = ["Zona Norte", "Zona Sur", "Planta Principal", "Bodega", "Patio de Maniobras"]

# --- 2. CONEXIÓN A GOOGLE SHEETS ---
def conectar_google():
    # Extrae las credenciales desde los Secrets de Streamlit
    creds_dict = json.loads(st.secrets["gcp_service_account"])
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    # Abre la hoja por su nombre exacto
    return client.open("Base Datos Inspecciones Goodyear").sheet1

def obtener_fecha_local():
    return datetime.now(pytz.timezone('America/Santiago'))

# --- 3. INTERFAZ DE USUARIO ---
st.title("🛡️ Panel de Control Goodyear")
st.markdown("Sistema de carga masiva y estadísticas de inspecciones.")

tab1, tab2 = st.tabs(["📥 Subida de Archivos (Excel)", "📊 Panel de Estadísticas"])

# PESTAÑA 1: CARGA DE DATOS
with tab1:
    st.header("Registrar Nueva Inspección")
    
    with st.container(border=True):
        col1, col2 = st.columns(2)
        with col1:
            ins_sel = st.selectbox("Seleccione Inspector Responsable:", equipo)
        with col2:
            zona_sel = st.selectbox("Seleccione Zona de Trabajo:", zonas_inspeccion)
        
        archivo = st.file_uploader("Arrastre aquí su archivo Excel (.xlsx o .csv)", type=['xlsx', 'csv'])
    
    if archivo:
        try:
            # Leer el archivo según su extensión
            if archivo.name.endswith('.xlsx'):
                df_subido = pd.read_excel(archivo)
            else:
                df_subido = pd.read_csv(archivo)
            
            # SOLUCIÓN AL ERROR 'nan': Convertimos vacíos a texto para que Google Sheets lo acepte
            df_subido = df_subido.fillna('')
            
            st.info(f"Se han detectado {len(df_subido)} filas en el archivo.")
            st.dataframe(df_subido.head(5), use_container_width=True)
            
            if st.button("🚀 Guardar Todo en la Nube"):
                with st.spinner("Procesando y enviando datos a Google Drive..."):
                    ahora = obtener_fecha_local()
                    
                    # Agregar metadatos automáticos a cada fila
                    df_subido['Fecha_Registro'] = ahora.strftime("%Y-%m-%d %H:%M:%S")
                    df_subido['Inspector'] = ins_sel
                    df_subido['Zona'] = zona_sel
                    df_subido['Mes'] = ahora.strftime("%B")
                    df_subido['Año'] = ahora.year
                    
                    # Conectar y subir
                    sheet = conectar_google()
                    
                    # Si la hoja está vacía, subir también los encabezados
                    if not sheet.get_all_values():
                        sheet.insert_row(df_subido.columns.tolist(), 1)
                    
                    # Convertir DataFrame a lista de listas para Google Sheets
                    datos_finales = df_subido.values.tolist()
                    sheet.append_rows(datos_finales)
                    
                    st.success(f"¡Éxito! {len(df_subido)} registros guardados en la base de datos.")
                    st.balloons()
                    
        except Exception as e:
            st.error(f"Error al procesar: {e}")

# PESTAÑA 2: ESTADÍSTICAS
with tab2:
    st.header("Rendimiento del Equipo")
    
    try:
        sheet = conectar_google()
        lista_datos = sheet.get_all_records()
        
        if lista_datos:
            df_master = pd.DataFrame(lista_datos)
            
            # Filtro por inspector
            inspectores_f = st.multiselect("Filtrar por Personal:", equipo, default=equipo)
            df_filtrado = df_master[df_master['Inspector'].isin(inspectores_f)]

            # Métricas rápidas
            m1, m2, m3 = st.columns(3)
            m1.metric("Total Inspecciones", len(df_filtrado))
            m2.metric("Meses Activos", df_filtrado['Mes'].nunique())
            m3.metric("Último Registro", str(df_filtrado['Fecha_Registro'].iloc[-1]))

            st.divider()

            # Gráfico de barras
            fig_bar = px.bar(df_filtrado, x='Inspector', color='Zona', 
                             title="Inspecciones Acumuladas por Persona",
                             labels={'count': 'Cantidad de Filas'})
            st.plotly_chart(fig_bar, use_container_width=True)
            
            # Tabla de datos crudos
            with st.expander("Ver base de datos completa"):
                st.dataframe(df_filtrado)
        else:
            st.warning("La base de datos en Google Sheets está vacía.")
            
    except Exception as e:
        st.info("Conectando con la base de datos... Por favor, asegúrese de haber compartido la hoja con el correo de la cuenta de servicio.")