import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px

# Configuración de la página
st.set_page_config(page_title="DrinkDash - DataVista", layout="wide")
st.title("DrinkDash - Dashboard Analítico")

# Conexión a SQLite
@st.cache_data
def cargar_datos():
    try:
        conn = sqlite3.connect("data/drinkdash.db")
        query = "SELECT * FROM ventas_procesadas"
        df = pd.read_sql(query, conn)
        conn.close()
        return df
    except Exception as e:
        st.error(f"Error al conectar con la base de datos: {e}")
        return pd.DataFrame()

df = cargar_datos()

if df.empty:
    st.warning("No hay datos en la base. Asegurate de que Airflow haya procesado el CSV.")
else:
    # --- KPIs Generales ---
    st.subheader("Indicadores Globales: ")
    col1, col2, col3 = st.columns(3)
    
    revenue_total = df['amount'].sum()
    unidades_vendidas = df['quantity'].sum()
    ticket_promedio = df['amount'].mean()
    
    col1.metric("Revenue Total", f"${revenue_total:,.2f}")
    col2.metric("Unidades Vendidas", f"{unidades_vendidas:,}")
    col3.metric("Ticket Promedio", f"${ticket_promedio:,.2f}")
    
    st.divider()

    # --- Gráficos con Plotly ---
    colA, colB = st.columns(2)
    
    with colA:
        st.subheader("Ventas por Franja Horaria")
        ventas_hora = df.groupby('purchase_hour')['amount'].sum().reset_index()
        fig_hora = px.bar(ventas_hora, x='purchase_hour', y='amount', 
                          labels={'purchase_hour': 'Hora del Día', 'amount': 'Ingresos ($)'},
                          title="Distribución de Ingresos por Hora")
        st.plotly_chart(fig_hora, use_container_width=True)

    with colB:
        st.subheader("Ranking de Productos")
        ranking = df.groupby('product_name')['quantity'].sum().reset_index().sort_values(by='quantity', ascending=False).head(5)
        fig_ranking = px.bar(ranking, x='quantity', y='product_name', orientation='h',
                             labels={'quantity': 'Cantidad Vendida', 'product_name': 'Producto'},
                             title="Top 5 Productos más Vendidos")
                             
        st.plotly_chart(fig_ranking, use_container_width=True)    