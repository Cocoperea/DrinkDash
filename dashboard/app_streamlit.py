import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
from pathlib import Path
import auth  # ← una sola vez

# ── Configuración de página ────────────────────────────────────────────────────
st.set_page_config(page_title="DrinkDash - DataVista", layout="wide")

# ── Guard de autenticación ─────────────────────────────────────────────────────
auth.requiere_autenticacion()

# ── Ruta DB ────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH  = BASE_DIR / "dags" / "data" / "drinkdash.db"

# ── Carga de datos ─────────────────────────────────────────────────────────────
@st.cache_data(ttl=60)
def cargar_datos():
    try:
        conn = sqlite3.connect(str(DB_PATH))
        df = pd.read_sql("SELECT * FROM ventas_procesadas", conn)
        conn.close()
        return df
    except Exception as e:
        st.error(f"Error al conectar con la base de datos: {e}")
        return pd.DataFrame()

df = cargar_datos()

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("DrinkDash")
    auth.mostrar_barra_usuario()

# ── Encabezado principal ───────────────────────────────────────────────────────
st.title("DrinkDash - Dashboard Analítico")
st.divider()

if df.empty:
    st.warning("No hay datos en la base. Asegurate de haber procesado al menos un CSV con el ETL.")
    st.stop()

# ══════════════════════════════════════════════════════════════════════════════
# RF-04 — Revenue Total (todos los roles)
# ══════════════════════════════════════════════════════════════════════════════
if auth.tiene_permiso("RF-04"):
    st.subheader("Indicadores Globales")
    col1, col2, col3 = st.columns(3)
    col1.metric("Revenue Total",     f"${df['amount'].sum():,.2f}")
    col2.metric("Unidades Vendidas", f"{df['quantity'].sum():,}")
    col3.metric("Ticket Promedio",   f"${df['amount'].mean():,.2f}")
    st.divider()

# ══════════════════════════════════════════════════════════════════════════════
# RF-05 — Ventas por Franja Horaria (solo Gerencia)
# ══════════════════════════════════════════════════════════════════════════════
if auth.tiene_permiso("RF-05"):
    st.subheader("Ventas por Franja Horaria")
    ventas_hora = df.groupby('purchase_hour')['amount'].sum().reset_index()
    fig_hora = px.bar(ventas_hora, x='purchase_hour', y='amount',
                      labels={'purchase_hour': 'Hora del Día', 'amount': 'Ingresos ($)'},
                      title="Distribución de Ingresos por Hora")
    st.plotly_chart(fig_hora, use_container_width=True)
    st.divider()

# ══════════════════════════════════════════════════════════════════════════════
# RF-07 — Ranking de Productos (todos los roles)
# ══════════════════════════════════════════════════════════════════════════════
if auth.tiene_permiso("RF-07"):
    st.subheader("Ranking de Productos")
    ranking = (df.groupby('product_name')['quantity']
                 .sum().reset_index()
                 .sort_values('quantity', ascending=False)
                 .head(5))
    fig_ranking = px.bar(ranking, x='quantity', y='product_name', orientation='h',
                         labels={'quantity': 'Cantidad Vendida', 'product_name': 'Producto'},
                         title="Top 5 Productos más Vendidos")
    st.plotly_chart(fig_ranking, use_container_width=True)
    st.divider()
