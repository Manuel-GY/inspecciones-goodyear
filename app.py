import streamlit as st
import pandas as pd
import plotly.express as px
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="Estadísticas Goodyear", layout="wide")

# Conexión con la hoja de respuestas del formulario
conn = st.connection("gsheets", type=GSheetsConnection)

st.title("📊 Panel de Control de Inspecciones")

# Botón grande para ir al formulario de carga
st.sidebar.markdown("### Acciones")
st.sidebar.link_button("➕ Registrar Nueva Inspección", "AQUÍ_PEGA_EL_LINK_DE_TU_FORMULARIO")

try:
    # Leer datos (ttl=0 para ver cambios inmediatos)
    df = conn.read(ttl=0)
    
    if not df.empty:
        # Ajustar nombres de columnas según tu formulario
        # Google Forms suele poner: "Marca temporal", "Inspector", "Zona", "Cantidad..."
        
        # --- MÉTRICAS ---
        m1, m2 = st.columns(2)
        total_insp = df.iloc[:, 3].sum() if len(df.columns) > 3 else len(df)
        m1.metric("Total Inspecciones", int(total_insp))
        m2.metric("Registros Realizados", len(df))

        st.divider()

        # --- GRÁFICOS ---
        col_chart1, col_chart2 = st.columns(2)
        
        with col_chart1:
            # Gráfico por Inspector (Columna 2 del formulario)
            fig_ins = px.bar(df, x=df.columns[1], y=df.columns[3], 
                             title="Inspecciones por Persona", color=df.columns[1])
            st.plotly_chart(fig_ins, use_container_width=True)

        with col_chart2:
            # Gráfico por Zona (Columna 3 del formulario)
            fig_zona = px.pie(df, names=df.columns[2], values=df.columns[3], 
                              title="Distribución por Zona", hole=0.4)
            st.plotly_chart(fig_zona, use_container_width=True)

        st.subheader("Historial de Registros")
        st.dataframe(df, use_container_width=True)
        
    else:
        st.info("Esperando el primer registro del formulario...")
        
except Exception as e:
    st.warning("Configurando conexión con la base de datos...")