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

# ── Sidebar: título y usuario ──────────────────────────────────────────────────
with st.sidebar:
    st.title("DrinkDash")
    auth.mostrar_barra_usuario()
 
# ── Encabezado principal ───────────────────────────────────────────────────────
st.title("DrinkDash - Dashboard Analítico")
st.divider()
 
if df.empty:
    st.warning("No hay datos en la base. Asegurate de haber procesado al menos un CSV con el ETL.")
    st.stop()
 
# ── Detección de la columna de fecha ─────────────────────────────────────────
COL_FECHA = None
for candidata in ['purchase_datetime', 'purchase_date', 'date', 'fecha', 'created_at', 'timestamp', 'sale_date', 'order_date']:
    if candidata in df.columns:
        COL_FECHA = candidata
        break
 
tiene_fecha = False
if COL_FECHA:
    df['_purchase_date'] = pd.to_datetime(df[COL_FECHA], errors='coerce')
    df['_fecha'] = df['_purchase_date'].dt.date
    tiene_fecha = df['_fecha'].notna().any()
 
# ══════════════════════════════════════════════════════════════════════════════
# Panel de filtros en cascada: fecha → categoría → marca
# ══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("---")
    st.subheader("🔍 Filtros")
 
    # ── 1. Fecha ──────────────────────────────────────────────────────────────
    if tiene_fecha:
        fecha_min = df['_fecha'].min()
        fecha_max = df['_fecha'].max()
        rango_fechas = st.date_input(
            "Rango de fechas",
            value=(fecha_min, fecha_max),
            min_value=fecha_min,
            max_value=fecha_max,
            key="filtro_fechas",
        )
        if isinstance(rango_fechas, (list, tuple)) and len(rango_fechas) == 2:
            fecha_desde, fecha_hasta = rango_fechas[0], rango_fechas[1]
        else:
            fecha_desde, fecha_hasta = fecha_min, fecha_max
    else:
        fecha_desde = fecha_hasta = fecha_min = fecha_max = None
        st.caption("⚠️ No se detectó columna de fecha.")
 
    # Base restringida por fecha
    if tiene_fecha:
        df_tras_fecha = df[
            (df['_fecha'] >= fecha_desde) &
            (df['_fecha'] <= fecha_hasta)
        ]
    else:
        df_tras_fecha = df
 
    # ── 2. Categoría ──────────────────────────────────────────────────────────
    tiene_categoria = 'category' in df.columns
    if tiene_categoria:
        cats_disponibles = sorted(df_tras_fecha['category'].dropna().unique().tolist())
        categorias_sel = st.multiselect(
            "Categoría",
            options=cats_disponibles,
            default=[],
            placeholder="Todas las categorías",
        )
        categorias_sel = [c for c in categorias_sel if c in cats_disponibles]
    else:
        categorias_sel = []
 
    df_tras_cat = df_tras_fecha[df_tras_fecha['category'].isin(categorias_sel)] if categorias_sel else df_tras_fecha
 
    # ── 3. Marca ──────────────────────────────────────────────────────────────
    tiene_marca = 'brand' in df.columns
    if tiene_marca:
        marcas_disponibles = sorted(df_tras_cat['brand'].dropna().unique().tolist())

        if not marcas_disponibles:
            st.caption("⚠️ No hay marcas disponibles para la categoría y fecha seleccionadas.")
            marcas_sel = []
        else:
            marcas_sel = st.multiselect(
                "Marca",
                options=marcas_disponibles,
                default=[],
                placeholder="Todas las marcas",
            )
            marcas_sel = [m for m in marcas_sel if m in marcas_disponibles]
    else:
        marcas_sel = []
 
# ── DataFrame final ────────────────────────────────────────────────────────────
df_filtrado = df_tras_cat[df_tras_cat['brand'].isin(marcas_sel)] if marcas_sel and tiene_marca else df_tras_cat.copy()
 
filtros_activos = bool(
    categorias_sel or marcas_sel or (
        tiene_fecha and (fecha_desde != fecha_min or fecha_hasta != fecha_max)
    )
)
if filtros_activos:
    st.info(f"🔎 Filtros aplicados — mostrando {len(df_filtrado):,} de {len(df):,} registros.")
 
# ══════════════════════════════════════════════════════════════════════════════
# RF-04 — Revenue Total  (KPI + gráfico de área)
# ══════════════════════════════════════════════════════════════════════════════
if auth.tiene_permiso("RF-04"):
    st.subheader("Indicadores Globales")

    if df_filtrado.empty:
        st.warning(
            "⚠️ No se encontraron transacciones para los filtros seleccionados. "
            "Probá con otro rango de fechas, categoría o marca."
        )
    elif df_filtrado['amount'].isna().all() or df_filtrado['amount'].sum() == 0:
        st.info(
            "ℹ️ No se registraron ventas para el período y filtros seleccionados. "
            "Intentá ampliar el rango de fechas o cambiar los filtros."
        )
    else:
        # ── KPIs ─────────────────────────────────────────────────────────────
        col1, col2, col3 = st.columns(3)
        col1.metric("Revenue Total",     f"${df_filtrado['amount'].sum():,.2f}")
        col2.metric("Unidades Vendidas", f"{df_filtrado['quantity'].sum():,}")
        col3.metric("Ticket Promedio",   f"${df_filtrado['amount'].mean():,.2f}")

        # ── Gráfico de área: evolución temporal del revenue ───────────────────
        if tiene_fecha:
            serie_fecha = pd.to_datetime(df_filtrado[COL_FECHA], errors='coerce')
            revenue_tiempo = (
                df_filtrado['amount']
                .groupby(serie_fecha.dt.to_period('D'))
                .sum()
                .reset_index()
            )
            revenue_tiempo.columns = ['periodo', 'revenue']

            if revenue_tiempo.empty or revenue_tiempo['revenue'].sum() == 0:
                st.info("ℹ️ No hay datos de revenue disponibles para graficar en el período seleccionado.")
            else:
                granularidad = st.selectbox(
                    "Granularidad del gráfico",
                    options=["Diario", "Mensual", "Anual"],
                    index=0,
                    key="rf04_granularidad",
                )

                freq_map  = {"Diario": "D",   "Mensual": "M",   "Anual": "Y"}
                label_map = {"Diario": "Día", "Mensual": "Mes", "Anual": "Año"}
                freq   = freq_map[granularidad]
                xlabel = label_map[granularidad]

                # Reagrupar según la granularidad elegida
                revenue_tiempo = (
                    df_filtrado['amount']
                    .groupby(serie_fecha.dt.to_period(freq))
                    .sum()
                    .reset_index()
                )
                revenue_tiempo.columns = ['periodo', 'revenue']
                revenue_tiempo['periodo_dt'] = revenue_tiempo['periodo'].dt.to_timestamp()

                if granularidad == "Diario":
                    revenue_tiempo['periodo_label'] = revenue_tiempo['periodo_dt'].dt.strftime('%d/%m/%Y')
                elif granularidad == "Mensual":
                    revenue_tiempo['periodo_label'] = revenue_tiempo['periodo_dt'].dt.strftime('%b %Y')
                else:
                    revenue_tiempo['periodo_label'] = revenue_tiempo['periodo_dt'].dt.strftime('%Y')

                fig_area = px.area(
                    revenue_tiempo,
                    x='periodo_label',
                    y='revenue',
                    labels={'periodo_label': xlabel, 'revenue': 'Revenue ($)'},
                    title=f"Evolución del Revenue — Vista {granularidad}",
                )
                fig_area.update_traces(
                    line_color='#1f77b4',
                    fillcolor='rgba(31, 119, 180, 0.15)',
                    hovertemplate='%{x}<br>Revenue: $%{y:,.2f}<extra></extra>',
                )
                fig_area.update_layout(xaxis_tickangle=-45)
                st.plotly_chart(fig_area, use_container_width=True)

    st.divider()

# ══════════════════════════════════════════════════════════════════════════════
# RF-05 — Ventas por Franja Horaria (solo Gerencia)
# ══════════════════════════════════════════════════════════════════════════════
if auth.tiene_permiso("RF-05"):
    st.subheader("Ventas por Franja Horaria")

    if df_filtrado.empty:
        st.warning(
            "⚠️ No se encontraron transacciones para los filtros seleccionados. "
            "Probá con otro rango de fechas, categoría o marca."
        )
    elif 'purchase_hour' not in df_filtrado.columns:
        st.warning("⚠️ No se encontró la columna de hora en los datos.")
    else:
        ventas_hora = (
            df_filtrado.groupby('purchase_hour')
            .size()
            .reset_index(name='cantidad_transacciones')
        )

        if ventas_hora.empty or ventas_hora['cantidad_transacciones'].sum() == 0:
            st.info("ℹ️ No se registraron transacciones para el período y filtros seleccionados.")
        else:
            fig_hora = px.bar(
                ventas_hora,
                x='purchase_hour',
                y='cantidad_transacciones',
                labels={
                    'purchase_hour': 'Hora del Día',
                    'cantidad_transacciones': 'Cantidad de Transacciones'
                },
                title="Distribución de Transacciones por Franja Horaria",
            )
            fig_hora.update_layout(
                xaxis=dict(
                    tickmode='linear',
                    tick0=0,
                    dtick=1,
                    title='Hora del Día'
                ),
                yaxis_title='Cantidad de Transacciones',
                bargap=0.2,
            )
            fig_hora.update_traces(
                hovertemplate='%{x}hs<br>Transacciones: %{y}<extra></extra>',
            )
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
