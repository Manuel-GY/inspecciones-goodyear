import streamlit as st
import pandas as pd
import plotly.express as px
import os
from datetime import datetime
import pytz

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Gestión Inspecciones Goodyear", layout="wide")

# Archivo donde se guardará todo (Se crea solo)
DB_PATH = "base_datos_inspecciones.csv"

equipo = ["Carlos Silva", "Marco Yañez", "Luis Mella", "Cristian Curin", 
          "Enzo Muñoz", "Manuel Rivera", "Claudio Ramirez", "Christian Zuñiga"]

zonas_inspeccion = ["Zona Norte", "Zona Sur", "Planta Principal", "Bodega", "Patio de Maniobras"]

def obtener_fecha_local():
    zona_horaria = pytz.timezone('America/Santiago')
    return datetime.now(zona_horaria)

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
            # Leer el excel
            df_subido = pd.read_excel(archivo) if archivo.name.endswith('.xlsx') else pd.read_csv(archivo)
            
            if st.button("🚀 Procesar y Guardar Inspección"):
                ahora = obtener_fecha_local()
                
                # Agregar los datos automáticos a cada fila del Excel
                df_subido['Fecha_Registro'] = ahora.strftime("%Y-%m-%d %H:%M:%S")
                df_subido['Inspector'] = ins_sel
                df_subido['Zona'] = zona_sel
                df_subido['Mes'] = ahora.strftime("%B")
                df_subido['Año'] = ahora.year
                
                # Guardar en el archivo acumulativo
                if not os.path.isfile(DB_PATH):
                    df_subido.to_csv(DB_PATH, index=False, encoding='utf-8-sig')
                else:
                    df_subido.to_csv(DB_PATH, mode='a', header=False, index=False, encoding='utf-8-sig')
                
                st.success(f"¡Excelente! Se han registrado {len(df_subido)} inspecciones para {ins_sel}.")
                st.balloons()
        except Exception as e:
            st.error(f"Error al leer el Excel: {e}")

with tab2:
    if os.path.exists(DB_PATH):
        df_master = pd.read_csv(DB_PATH)
        
        # Métricas
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Inspecciones", len(df_master))
        c2.metric("Promedio Mensual", round(len(df_master)/max(df_master['Mes'].nunique(),1), 2))
        c3.metric("Última subida", df_master['Fecha_Registro'].iloc[-1])

        # Gráficos
        fig = px.bar(df_master, x='Inspector', color='Zona', title="Inspecciones Acumuladas")
        st.plotly_chart(fig, use_container_width=True)
        
        st.write("### Historial Completo")
        st.dataframe(df_master)
    else:
        st.info("Aún no hay inspecciones guardadas. Sube un archivo en la otra pestaña.")