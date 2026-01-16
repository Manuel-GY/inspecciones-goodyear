import streamlit as st
import pandas as pd
import plotly.express as px
import os
from datetime import datetime
import pytz
from streamlit_gsheets import GSheetsConnection

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Control Inspecciones Goodyear", layout="wide")

# Lista de Integrantes
equipo = [
    "Carlos Silva", "Marco Yañez", "Luis Mella", "Cristian Curin", 
    "Enzo Muñoz", "Manuel Rivera", "Claudio Ramirez", "Christian Zuñiga"
]

# Zonas de Inspección
zonas_inspeccion = ["Zona Norte", "Zona Sur", "Planta Principal", "Bodega", "Patio de Maniobras"]

# Conexión a Google Sheets (Se configura en los Secrets de Streamlit)
conn = st.connection("gsheets", type=GSheetsConnection)

def obtener_fecha_local():
    zona_horaria = pytz.timezone('America/Santiago')
    return datetime.now(zona_horaria)

# --- INTERFAZ ---
st.title("📊 Sistema de Inspecciones Goodyear")
tab1, tab2 = st.tabs(["📥 Registro de Inspección", "📈 Panel de Estadísticas"])

with tab1:
    st.header("Subir Reporte Semanal")
    col1, col2 = st.columns(2)
    with col1:
        ins_sel = st.selectbox("Seleccione Inspector:", equipo)
    with col2:
        zona_sel = st.selectbox("Seleccione Zona:", zonas_inspeccion)
    
    archivo = st.file_uploader("Cargar archivo Excel o CSV", type=['xlsx', 'csv'])
    
    if archivo:
        try:
            df_nuevo = pd.read_excel(archivo) if archivo.name.endswith('.xlsx') else pd.read_csv(archivo)
            st.info(f"Registros detectados: {len(df_nuevo)}")
            
            if st.button("💾 Guardar en Google Sheets"):
                ahora = obtener_fecha_local()
                # Preparar datos para la base central
                df_nuevo['Fecha_Registro'] = ahora.strftime("%Y-%m-%d %H:%M:%S")
                df_nuevo['Inspector_Asignado'] = ins_sel
                df_nuevo['Zona_Inspeccion'] = zona_sel
                df_nuevo['Mes'] = ahora.strftime("%B")
                df_nuevo['Año'] = ahora.year
                df_nuevo['Semana_Año'] = ahora.isocalendar()[1]
                
                # Leer historial actual y concatenar
                try:
                    existente = conn.read(ttl=0) # ttl=0 para que siempre lea lo más nuevo
                    df_final = pd.concat([existente, df_nuevo], ignore_index=True)
                except:
                    df_final = df_nuevo
                
                # Actualizar Google Sheets
                conn.update(data=df_final)
                st.success(f"¡Datos de {ins_sel} guardados para siempre!")
                st.balloons()
        except Exception as e:
            st.error(f"Error al procesar: {e}")

with tab2:
    st.header("Estadísticas en Tiempo Real")
    try:
        # Leer datos desde Google Sheets
        df_master = conn.read(ttl=0)
        
        if not df_master.empty:
            # Filtros
            f_ins = st.multiselect("Filtrar Personal:", equipo, default=equipo)
            df_filt = df_master[df_master['Inspector_Asignado'].isin(f_ins)]

            # Métricas
            m1, m2, m3 = st.columns(3)
            total = len(df_filt)
            meses = max(df_filt['Mes'].nunique(), 1)
            semanas = max(df_filt['Semana_Año'].nunique(), 1)
            
            m1.metric("Total Inspecciones", total)
            m2.metric("Promedio Mensual", round(total/meses, 1))
            m3.metric("Promedio Semanal", round(total/semanas, 1))

            # Gráficos
            st.plotly_chart(px.bar(df_filt, x='Inspector_Asignado', color='Zona_Inspeccion', title="Productividad por Persona"), use_container_width=True)
            
            df_evolucion = df_filt.groupby('Mes').size().reset_index(name='Cant')
            st.plotly_chart(px.line(df_evolucion, x='Mes', y='Cant', title="Tendencia Mensual", markers=True), use_container_width=True)
        else:
            st.info("Aún no hay datos en la nube.")
    except:
        st.warning("Conectando con la base de datos de Google...")