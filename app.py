import streamlit as st
import pandas as pd
import plotly.express as px
import os
from datetime import datetime

# --- 1. CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Control de Inspecciones Goodyear", layout="wide")

# Nombre del archivo que servirá de base de datos en tu OneDrive
DB_PATH = "base_datos_inspecciones.csv"

# --- 2. LISTAS DE DATOS MAESTROS ---
equipo = [
    "Carlos Silva", "Marco Yañez", "Luis Mella", "Cristian Curin", 
    "Enzo Muñoz", "Manuel Rivera", "Claudio Ramirez", "Christian Zuñiga"
]

# Puedes editar estas zonas según necesites
zonas_inspeccion = [
    "Zona Norte", "Zona Sur", "Planta Principal", 
    "Bodega", "Patio de Maniobras", "Recepción"
]

# --- 3. FUNCIONES DE LÓGICA DE DATOS ---
def guardar_datos(df_nuevo, inspector, zona):
    """Añade metadatos y guarda los datos en el archivo CSV."""
    ahora = datetime.now()
    # Agregamos información de control que no viene en el Excel original
    df_nuevo['Fecha_Registro'] = ahora.strftime("%Y-%m-%d %H:%M:%S")
    df_nuevo['Inspector_Asignado'] = inspector
    df_nuevo['Zona_Inspeccion'] = zona
    df_nuevo['Mes'] = ahora.strftime("%B") # Nombre del mes
    df_nuevo['Año'] = ahora.year
    df_nuevo['Semana_Año'] = ahora.isocalendar()[1]

    # Guardado persistente
    if not os.path.isfile(DB_PATH):
        df_nuevo.to_csv(DB_PATH, index=False, encoding='utf-8-sig')
    else:
        df_nuevo.to_csv(DB_PATH, mode='a', header=False, index=False, encoding='utf-8-sig')

# --- 4. INTERFAZ DE USUARIO (FRONTEND) ---
st.title("📊 Sistema de Gestión de Inspecciones")
st.markdown("---")

tab1, tab2 = st.tabs(["📥 Cargar Reporte Semanal", "📈 Panel de Estadísticas"])

# PESTAÑA DE CARGA
with tab1:
    st.header("Registro de Datos")
    col_a, col_b = st.columns(2)
    
    with col_a:
        ins_sel = st.selectbox("Seleccione su Nombre:", equipo)
    with col_b:
        zona_sel = st.selectbox("Seleccione Zona Inspeccionada:", zonas_inspeccion)
    
    archivo = st.file_uploader("Subir archivo Excel o CSV", type=['xlsx', 'csv'])
    
    if archivo:
        try:
            if archivo.name.endswith('.xlsx'):
                df_temp = pd.read_excel(archivo)
            else:
                df_temp = pd.read_csv(archivo)
            
            st.info(f"Se detectaron {len(df_temp)} registros en el archivo.")
            st.write("Vista previa de la subida:")
            st.dataframe(df_temp.head(5))
            
            if st.button("🚀 Confirmar y Guardar Datos"):
                guardar_datos(df_temp, ins_sel, zona_sel)
                st.success(f"¡Excelente! Los datos de {ins_sel} han sido integrados correctamente.")
        except Exception as e:
            st.error(f"Error al procesar el archivo: {e}")

# PESTAÑA DE ESTADÍSTICAS
with tab2:
    st.header("Análisis de Rendimiento")
    
    if os.path.exists(DB_PATH):
        # Leer base de datos y convertir fechas
        df_master = pd.read_csv(DB_PATH)
        df_master['Fecha_Registro'] = pd.to_datetime(df_master['Fecha_Registro'])
        
        # --- FILTROS LATERALES O SUPERIORES ---
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            filtro_ins = st.multiselect("Filtrar Personal:", options=equipo, default=equipo)
        with col_f2:
            filtro_zona = st.multiselect("Filtrar Zonas:", options=zonas_inspeccion, default=zonas_inspeccion)
        
        # Aplicar filtros
        df_filtrado = df_master[
            (df_master['Inspector_Asignado'].isin(filtro_ins)) & 
            (df_master['Zona_Inspeccion'].isin(filtro_zona))
        ]

        if not df_filtrado.empty:
            # --- CÁLCULOS TEMPORALES ---
            total_insp = len(df_filtrado)
            # Contamos semanas y meses únicos para promedios reales
            semanas_activas = max(df_filtrado['Semana_Año'].nunique(), 1)
            meses_activos = max(df_filtrado['Mes'].nunique(), 1)
            
            # --- MÉTRICAS ---
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Total Inspecciones", total_insp)
            m2.metric("Promedio Semanal", round(total_insp / semanas_activas, 1))
            m3.metric("Promedio Mensual", round(total_insp / meses_activos, 1))
            m4.metric("Personal Activo", df_filtrado['Inspector_Asignado'].nunique())

            st.divider()

            # --- GRÁFICOS ---
            c1, c2 = st.columns(2)
            
            with c1:
                # Barras por persona y zona
                fig_bar = px.bar(df_filtrado, x='Inspector_Asignado', color='Zona_Inspeccion', 
                                 title="Inspecciones por Persona y Zona",
                                 labels={'Inspector_Asignado': 'Inspector', 'count': 'Cantidad'})
                st.plotly_chart(fig_bar, use_container_width=True)
            
            with c2:
                # Tendencia por mes
                df_mes = df_filtrado.groupby(['Mes', 'Inspector_Asignado']).size().reset_index(name='Cantidad')
                fig_line = px.line(df_mes, x='Mes', y='Cantidad', color='Inspector_Asignado',
                                   title="Rendimiento Mensual por Inspector", markers=True)
                st.plotly_chart(fig_line, use_container_width=True)
            
            # Gráfico de distribución de zonas
            st.subheader("Cobertura por Zona")
            fig_pie = px.pie(df_filtrado, names='Zona_Inspeccion', hole=0.4, 
                             color_discrete_sequence=px.colors.sequential.RdBu)
            st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.warning("No hay datos que coincidan con los filtros seleccionados.")
    else:
        st.info("La base de datos está vacía. Registra tu primera inspección para ver estadísticas.")