import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
import auth

# ── Configuración de página ────────────────────────────────────────────────────
# Establece el título de la pestaña del navegador, el layout "wide" para que
# el contenido ocupe todo el ancho de la pantalla, y el sidebar expandido por defecto.
st.set_page_config(
    page_title="DrinkDash - DataVista",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ══════════════════════════════════════════════════════════════════════════════
# CSS GLOBAL — TEMA OSCURO
# ══════════════════════════════════════════════════════════════════════════════
# Streamlit no tiene un sistema de temas oscuros tan granular como necesitamos,
# así que inyectamos CSS directamente usando st.markdown con unsafe_allow_html=True.
# Esto nos permite sobrescribir los estilos internos de Streamlit.
#
# IMPORTANTE: los selectores como [data-testid="stMetric"] apuntan a atributos
# internos de Streamlit. Si Streamlit actualiza su versión, estos pueden cambiar.
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<style>
/* ── 1. FUENTE PERSONALIZADA ──────────────────────────────────────────────────
   Importamos DM Sans desde Google Fonts. Es una fuente moderna, legible y
   apropiada para dashboards de datos. DM Mono se usa para valores numéricos. */
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&family=DM+Mono:wght@400;500&display=swap');

/* ── 2. VARIABLES DE COLOR (DESIGN TOKENS) ────────────────────────────────────
   Definimos todos los colores en un solo lugar usando variables CSS (:root).
   Esto nos permite cambiar el tema completo modificando solo estas líneas,
   sin tener que buscar colores hardcodeados en todo el archivo. */
:root {
    --bg-base:        #0f1117;   /* Fondo principal de la app */
    --bg-sidebar:     #161b27;   /* Fondo del sidebar, levemente más claro */
    --bg-card:        #1c2333;   /* Fondo de tarjetas y componentes */
    --bg-card-hover:  #222b3a;   /* Fondo de tarjetas al pasar el mouse */
    --bg-header:      #161b27;   /* Fondo del header de Streamlit */
    --accent-blue:    #4f8ef7;   /* Color principal de acción / resaltado */
    --accent-green:   #3ecf8e;   /* Indicadores positivos */
    --accent-red:     #f26b6b;   /* Indicadores negativos */
    --accent-yellow:  #f5a623;   /* Alertas / destacados */
    --accent-purple:  #8b5cf6;   /* Color secundario de acción */
    --text-primary:   #e8eaf0;   /* Texto principal (títulos, valores) */
    --text-secondary: #8b95a8;   /* Texto secundario (labels, subtítulos) */
    --text-muted:     #4a5568;   /* Texto desactivado / muy secundario */
    --border:         #2a3347;   /* Bordes de tarjetas y separadores */
    --border-light:   #1e2a3a;   /* Bordes internos de grillas en gráficos */
}

/* ── 3. RESET GLOBAL ──────────────────────────────────────────────────────────
   Aplica la fuente y el color de fondo a todos los elementos de la página.
   [class*="css"] captura los contenedores generados dinámicamente por Streamlit. */
html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif !important;
    background-color: var(--bg-base) !important;
    color: var(--text-primary) !important;
}

/* ── 4. SIDEBAR ───────────────────────────────────────────────────────────────
   Estiliza el panel lateral. El borde derecho separa visualmente el sidebar
   del contenido principal sin usar una sombra pesada. */
[data-testid="stSidebar"] {
    background-color: var(--bg-sidebar) !important;
    border-right: 1px solid var(--border) !important;
    padding-top: 0 !important;
}
[data-testid="stSidebar"] > div:first-child {
    padding-top: 0 !important;  /* Elimina el padding por defecto de Streamlit arriba del sidebar */
}

/* ── 5. ÁREA PRINCIPAL Y HEADER ───────────────────────────────────────────────
   El contenedor principal hereda el fondo oscuro.
   El header de Streamlit (barra superior) también se oscurece para que no
   rompa la continuidad visual con el sidebar. */
[data-testid="stAppViewContainer"] > .main {
    background-color: var(--bg-base) !important;
}
header[data-testid="stHeader"] {
    background-color: var(--bg-header) !important;
    border-bottom: 1px solid var(--border) !important;
}

/* ── 6. TARJETAS KPI (st.metric) ──────────────────────────────────────────────
   st.metric es el componente de Streamlit para mostrar indicadores clave.
   Lo estilizamos para que parezca una tarjeta oscura con borde sutil,
   similar a los mockups del proyecto. */
[data-testid="stMetric"] {
    background-color: var(--bg-card) !important;
    border: 1px solid var(--border) !important;
    border-radius: 12px !important;
    padding: 20px 24px !important;
    transition: background 0.2s;  /* Transición suave al hover */
}
[data-testid="stMetric"]:hover {
    background-color: var(--bg-card-hover) !important;
}
/* Label del KPI (ej: "Revenue Total") — pequeño y en mayúsculas */
[data-testid="stMetricLabel"] {
    font-size: 0.75rem !important;
    font-weight: 500 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.08em !important;
    color: var(--text-secondary) !important;
}
/* Valor principal del KPI (ej: "$2.847.320") — grande y en negrita */
[data-testid="stMetricValue"] {
    font-size: 1.9rem !important;
    font-weight: 700 !important;
    color: var(--text-primary) !important;
    letter-spacing: -0.02em !important;
}
/* Delta / variación (ej: "+12,4% vs mes anterior") */
[data-testid="stMetricDelta"] {
    font-size: 0.8rem !important;
    font-weight: 500 !important;
}

/* ── 7. BARRA DE HERRAMIENTAS DE PLOTLY ───────────────────────────────────────
   Oculta el fondo blanco de la modebar (zoom, descarga, etc.) de Plotly
   para que se integre con el fondo oscuro. */
.js-plotly-plot .plotly .modebar {
    background: transparent !important;
}

/* ── 8. SELECTBOX Y MULTISELECT ───────────────────────────────────────────────
   Estiliza los controles de selección para que sigan el tema oscuro.
   Sin esto, Streamlit los mostraría con fondo blanco o gris claro. */
[data-testid="stSelectbox"] > div > div,
[data-testid="stMultiSelect"] > div > div {
    background-color: var(--bg-card) !important;
    border: 1px solid var(--border) !important;
    border-radius: 8px !important;
    color: var(--text-primary) !important;
}

/* ── 9. BOTONES ───────────────────────────────────────────────────────────────
   Estilo base para todos los botones de la app.
   El hover cambia el borde a azul para dar feedback visual sin ser agresivo. */
[data-testid="stButton"] > button {
    background-color: var(--bg-card) !important;
    border: 1px solid var(--border) !important;
    color: var(--text-primary) !important;
    border-radius: 8px !important;
    font-weight: 500 !important;
    transition: all 0.15s !important;
}
[data-testid="stButton"] > button:hover {
    border-color: var(--accent-blue) !important;
    color: var(--accent-blue) !important;
}

/* ── 10. SEPARADORES ─────────────────────────────────────────────────────────
   Los <hr> y st.divider() usan el color de borde del tema. */
hr {
    border-color: var(--border) !important;
    margin: 1rem 0 !important;
}

/* ── 11. CAJAS DE ALERTA ─────────────────────────────────────────────────────
   st.warning, st.info, st.error generan estos contenedores.
   Les damos bordes redondeados y borde consistente con el tema. */
[data-testid="stAlert"] {
    border-radius: 10px !important;
    border: 1px solid var(--border) !important;
}

/* ── 12. SCROLLBAR PERSONALIZADA ─────────────────────────────────────────────
   Reemplaza la scrollbar por defecto del navegador con una más delgada
   y acorde al tema oscuro. Solo funciona en Chrome/Edge (webkit). */
::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: var(--bg-base); }
::-webkit-scrollbar-thumb { background: var(--border); border-radius: 10px; }
</style>
""", unsafe_allow_html=True)

# ── Guard de autenticación ─────────────────────────────────────────────────────
# Si el usuario no está logueado, auth.requiere_autenticacion() muestra
# la pantalla de login y detiene la ejecución del resto del script con st.stop().
# Solo continúa si hay una sesión válida en st.session_state.
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

# ── Detección de columna de fecha ─────────────────────────────────────────────
COL_FECHA = None
for candidata in ['purchase_datetime', 'purchase_date', 'date', 'fecha', 'created_at', 'timestamp', 'sale_date', 'order_date']:
    if candidata in df.columns:
        COL_FECHA = candidata
        break

tiene_fecha = False
if COL_FECHA and not df.empty:
    df['_purchase_date'] = pd.to_datetime(df[COL_FECHA], errors='coerce')
    df['_fecha'] = df['_purchase_date'].dt.date
    tiene_fecha = df['_fecha'].notna().any()

# ══════════════════════════════════════════════════════════════════════════════
# CONFIGURACIÓN DE NAVEGACIÓN POR ROL
# ══════════════════════════════════════════════════════════════════════════════
# Leemos el rol y datos del usuario desde st.session_state, que fue
# poblado por auth.login() al iniciar sesión.
ROL      = st.session_state.get("usuario_rol", "")
NOMBRE   = st.session_state.get("usuario_nombre") or st.session_state.get("usuario_email", "")
PERMISOS = st.session_state.get("permisos", {})
ROL_LABEL = PERMISOS.get("label", ROL.capitalize())

# Título del dashboard según el rol del usuario logueado
TITULO_POR_ROL = {
    "gerencia":  "Dashboard Gerencia",
    "ventas":    "Dashboard Ventas",
    "marketing": "Dashboard Marketing",
    "direccion": "Dashboard Dirección",
}
DASHBOARD_TITULO = TITULO_POR_ROL.get(ROL, "Dashboard")

# Ítems de navegación del sidebar para cada rol.
# Cada ítem es una tupla (clave_interna, etiqueta_visible).
# La clave interna se usa en st.session_state.seccion_activa para saber
# qué sección renderizar en el área de contenido.
# Al agregar un nuevo RF, se agrega su ítem aquí y luego se usa la clave
# como condición: if st.session_state.seccion_activa == "clave":
NAV_POR_ROL = {
    "gerencia": [
        ("resumen",    "Resumen general"),
        ("horario",    "Ventas por horario"),
        ("evolucion",  "Evolución de ventas"),
        ("ticket",     "Ticket promedio"),
        ("ranking",    "Ranking de productos"),
        ("descuentos", "Análisis de descuentos"),
    ],
    "ventas": [
        ("resumen",    "Resumen ventas"),
        ("cantidades", "Cantidades vendidas"),
        ("ranking",    "Ranking de productos"),
        ("descuentos", "Análisis de descuentos"),
        ("ticket",     "Ticket promedio"),
        ("revenue",    "Revenue total"),
    ],
    "marketing": [
        ("resumen",        "Comportamiento de mercado"),
        ("frecuencia",     "Frecuencia de compra"),
        ("marcas",         "Preferencias de marca"),
        ("estacionalidad", "Estacionalidad"),
        ("efectividad",    "Efectividad de descuentos"),
        ("revenue",        "Revenue total"),
    ],
    "direccion": [
        ("resumen",        "Resumen estratégico"),
        ("crecimiento",    "Crecimiento"),
        ("elasticidad",    "Elasticidad precio-demanda"),
        ("estacionalidad", "Estacionalidad"),
        ("descuentos",     "Análisis de descuentos"),
        ("exportar",       "Exportar reportes"),
    ],
}
nav_items = NAV_POR_ROL.get(ROL, [])

# Inicializamos la sección activa en session_state la primera vez.
# session_state persiste entre reruns de Streamlit dentro de la misma sesión,
# por lo que recordamos qué sección eligió el usuario.
if "seccion_activa" not in st.session_state:
    st.session_state.seccion_activa = nav_items[0][0] if nav_items else "resumen"

# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════
with st.sidebar:

    # ── Logo DrinkDash ─────────────────────────────────────────────────────────
    # Usamos HTML inline para tener control total sobre el diseño del logo.
    # Streamlit no tiene un componente nativo para esto, por eso usamos
    # st.markdown con HTML crudo. El ícono "D" tiene un gradiente azul-violeta
    # que coincide con la identidad visual del mockup.
    st.markdown("""
    <div style="padding: 24px 16px 16px 16px; display:flex; align-items:center; gap:10px;">
        <div style="
            width:36px; height:36px; border-radius:10px;
            background: linear-gradient(135deg, #4f8ef7, #7c3aed);
            display:flex; align-items:center; justify-content:center;
            font-weight:700; font-size:1rem; color:white; flex-shrink:0;">
            D
        </div>
        <span style="font-size:1.15rem; font-weight:700; color:#e8eaf0;">
            Drink<span style="color:#4f8ef7;">Dash</span>
        </span>
    </div>
    """, unsafe_allow_html=True)

    # ── Etiqueta de sección "NAVEGACIÓN" ──────────────────────────────────────
    st.markdown(
        '<div style="padding: 0 16px; margin-bottom:8px; font-size:0.65rem; '
        'font-weight:600; letter-spacing:0.1em; color:#4a5568; text-transform:uppercase;">'
        'NAVEGACIÓN</div>',
        unsafe_allow_html=True
    )

    # ── Botones de navegación ──────────────────────────────────────────────────
    # Por cada ítem del menú del rol, creamos un botón de Streamlit.
    # Al hacer clic, guardamos la clave en session_state y forzamos un rerun
    # para que el contenido principal se actualice mostrando la sección elegida.
    for key, label in nav_items:
        if st.button(label, key=f"nav_{key}", use_container_width=True):
            st.session_state.seccion_activa = key
            st.rerun()

    # ── CSS específico para los botones del sidebar ────────────────────────────
    # Los botones de navegación deben verse como ítems de menú (sin borde,
    # fondo transparente, alineados a la izquierda), no como botones normales.
    # Este bloque CSS sobreescribe solo los botones dentro del sidebar,
    # sin afectar a los botones del resto de la app.
    st.markdown("""
    <style>
    [data-testid="stSidebar"] [data-testid="stButton"] > button {
        background: transparent !important;
        border: none !important;
        text-align: left !important;
        justify-content: flex-start !important;
        padding: 8px 16px !important;
        border-radius: 8px !important;
        color: #8b95a8 !important;
        font-size: 0.875rem !important;
        font-weight: 400 !important;
    }
    [data-testid="stSidebar"] [data-testid="stButton"] > button:hover {
        background: rgba(79,142,247,0.08) !important;
        color: #e8eaf0 !important;
        border: none !important;
    }
    </style>
    """, unsafe_allow_html=True)

    # ── Espaciador visual ──────────────────────────────────────────────────────
    st.markdown('<div style="flex:1; min-height:40px;"></div>', unsafe_allow_html=True)

    # ── Sección de filtros ─────────────────────────────────────────────────────
    st.markdown('<hr style="border-color:#2a3347; margin: 8px 0;"/>', unsafe_allow_html=True)
    st.markdown(
        '<div style="padding: 0 4px 6px; font-size:0.65rem; font-weight:600; '
        'letter-spacing:0.1em; color:#4a5568; text-transform:uppercase;">FILTROS</div>',
        unsafe_allow_html=True
    )

    if not df.empty:
        # Filtro de fecha
        if tiene_fecha:
            fecha_min = df['_fecha'].min()
            fecha_max = df['_fecha'].max()
            rango_fechas = st.date_input(
                "Período",
                value=(fecha_min, fecha_max),
                min_value=fecha_min,
                max_value=fecha_max,
                key="filtro_fechas",
            )
            if isinstance(rango_fechas, (list, tuple)) and len(rango_fechas) == 2:
                fecha_desde, fecha_hasta = rango_fechas[0], rango_fechas[1]
            else:
                fecha_desde, fecha_hasta = fecha_min, fecha_max
            df_tras_fecha = df[(df['_fecha'] >= fecha_desde) & (df['_fecha'] <= fecha_hasta)]
        else:
            fecha_desde = fecha_hasta = fecha_min = fecha_max = None
            df_tras_fecha = df

        # Filtro de categoría — solo muestra categorías disponibles para el período seleccionado
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

        # Filtro de marca — en cascada: solo muestra marcas del período + categoría seleccionados
        tiene_marca = 'brand' in df.columns
        if tiene_marca:
            marcas_disponibles = sorted(df_tras_cat['brand'].dropna().unique().tolist())
            if not marcas_disponibles:
                # Si no hay marcas disponibles para la combinación actual, ocultamos el multiselect
                # para evitar el "No results" nativo de Streamlit que confunde al usuario
                st.caption("⚠️ Sin marcas para esta selección.")
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
    else:
        # Si el DataFrame está vacío, inicializamos las variables para evitar errores más adelante
        df_tras_cat = df
        categorias_sel = []
        marcas_sel = []
        fecha_desde = fecha_hasta = fecha_min = fecha_max = None

    # ── Info del usuario logueado ──────────────────────────────────────────────
    # Mostramos el nombre, rol e iniciales del usuario al pie del sidebar.
    # Las iniciales se generan tomando la primera letra de cada palabra del nombre.
    st.markdown('<hr style="border-color:#2a3347; margin:12px 0 8px;"/>', unsafe_allow_html=True)
    iniciales = "".join([p[0].upper() for p in NOMBRE.split()[:2]]) if NOMBRE else "?"
    st.markdown(f"""
    <div style="display:flex; align-items:center; gap:10px; padding: 4px 4px 12px;">
        <div style="
            width:32px; height:32px; border-radius:50%;
            background: linear-gradient(135deg, #4f8ef7, #7c3aed);
            display:flex; align-items:center; justify-content:center;
            font-size:0.75rem; font-weight:700; color:white; flex-shrink:0;">
            {iniciales}
        </div>
        <div>
            <div style="font-size:0.8rem; font-weight:600; color:#e8eaf0; line-height:1.2;">{NOMBRE}</div>
            <div style="font-size:0.7rem; color:#4a5568;">Rol: {ROL_LABEL}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if st.button("Cerrar sesión", use_container_width=True, key="btn_logout"):
        auth.logout()

# ── DataFrame final con todos los filtros aplicados ───────────────────────────
# Aplicamos el filtro de marca sobre el df ya filtrado por fecha y categoría.
# Si no hay marca seleccionada, usamos el df filtrado hasta categoría.
if not df.empty:
    df_filtrado = df_tras_cat[df_tras_cat['brand'].isin(marcas_sel)] if marcas_sel and tiene_marca else df_tras_cat.copy()
else:
    df_filtrado = df.copy()

# ══════════════════════════════════════════════════════════════════════════════
# HEADER DEL ÁREA DE CONTENIDO
# ══════════════════════════════════════════════════════════════════════════════

# Badge de período — pequeña etiqueta en la esquina superior derecha del header
# que muestra el mes/período activo del filtro de fechas, igual al mockup.
periodo_badge = ""
if tiene_fecha and not df.empty:
    try:
        periodo_badge = (
            f'<span style="background:#1c2333; border:1px solid #2a3347; border-radius:6px; '
            f'padding:4px 12px; font-size:0.8rem; color:#8b95a8; font-weight:500;">'
            f'{fecha_desde.strftime("%b %Y") if fecha_desde else ""}</span>'
        )
    except Exception:
        periodo_badge = ""

# Título del dashboard con badge de período a la derecha
st.markdown(f"""
<div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:8px;">
    <h1 style="font-size:1.5rem; font-weight:700; color:#e8eaf0; margin:0; letter-spacing:-0.02em;">
        {DASHBOARD_TITULO}
    </h1>
    {periodo_badge}
</div>
""", unsafe_allow_html=True)

# Banner informativo cuando hay filtros activos
# Solo se muestra si el usuario modificó algún filtro respecto al estado inicial
filtros_activos = bool(
    categorias_sel or marcas_sel or (
        tiene_fecha and not df.empty and (fecha_desde != fecha_min or fecha_hasta != fecha_max)
    )
)
if filtros_activos and not df_filtrado.empty:
    st.markdown(f"""
    <div style="background:#1c2333; border:1px solid #2a3347; border-radius:8px;
                padding:8px 14px; margin-bottom:12px; font-size:0.8rem; color:#8b95a8;">
        🔎 Filtros aplicados — mostrando
        <strong style="color:#e8eaf0;">{len(df_filtrado):,}</strong>
        de <strong style="color:#e8eaf0;">{len(df):,}</strong> registros
    </div>
    """, unsafe_allow_html=True)

# ── Sin datos ──────────────────────────────────────────────────────────────────
if df.empty:
    st.warning("No hay datos en la base. Asegurate de haber procesado al menos un CSV con el ETL.")
    st.stop()

# ══════════════════════════════════════════════════════════════════════════════
# HELPERS DE ESTILO PARA GRÁFICOS PLOTLY
# ══════════════════════════════════════════════════════════════════════════════
# En lugar de repetir la configuración de tema oscuro en cada gráfico,
# definimos un diccionario base PLOTLY_LAYOUT con todos los parámetros
# visuales comunes y una función aplicar_layout() que lo aplica a cualquier figura.

# Configuración base compartida por todos los gráficos
PLOTLY_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",   # Fondo del área total del gráfico: transparente
    plot_bgcolor="rgba(0,0,0,0)",    # Fondo del área de datos: transparente
    # Así el fondo oscuro de la tarjeta HTML que los envuelve se ve a través
    font=dict(family="DM Sans", color="#8b95a8", size=12),
    title_font=dict(family="DM Sans", color="#e8eaf0", size=14, weight=600),
    xaxis=dict(gridcolor="#1e2a3a", linecolor="#2a3347", tickcolor="#4a5568"),
    yaxis=dict(gridcolor="#1e2a3a", linecolor="#2a3347", tickcolor="#4a5568"),
    margin=dict(l=40, r=20, t=50, b=40),
    legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color="#8b95a8")),
    hoverlabel=dict(bgcolor="#1c2333", bordercolor="#2a3347", font=dict(color="#e8eaf0")),
)

def aplicar_layout(fig, titulo=""):
    """
    Aplica el tema oscuro estándar a una figura de Plotly.
    Uso: aplicar_layout(fig, "Título del gráfico")
    """
    layout = dict(PLOTLY_LAYOUT)
    if titulo:
        layout["title"] = dict(text=titulo, font=dict(family="DM Sans", color="#e8eaf0", size=14))
    fig.update_layout(**layout)
    return fig

def card_grafico(titulo):
    """
    Renderiza el encabezado de una tarjeta oscura con título.
    Se usa antes de st.plotly_chart() para que el gráfico quede
    visualmente contenido dentro de la tarjeta.
    Nota: el cierre </div> se debe agregar manualmente después del gráfico.
    """
    st.markdown(f"""
    <div style="background:#1c2333; border:1px solid #2a3347; border-radius:12px;
                padding:20px 20px 4px; margin-bottom:16px;">
        <div style="font-size:0.9rem; font-weight:600; color:#e8eaf0; margin-bottom:4px;">
            {titulo}
        </div>
    """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# RF-04 — Revenue Total
# Solo se renderiza si la sección activa es "resumen" (para todos los roles)
# ══════════════════════════════════════════════════════════════════════════════
if auth.tiene_permiso("RF-04") and st.session_state.seccion_activa == "resumen":
    if auth.tiene_permiso("RF-04"):

        if df_filtrado.empty:
            st.warning("⚠️ No se encontraron transacciones para los filtros seleccionados.")
        elif df_filtrado['amount'].isna().all() or df_filtrado['amount'].sum() == 0:
            st.info("ℹ️ No se registraron ventas para el período y filtros seleccionados.")
        else:
            # ── KPIs en 4 columnas ────────────────────────────────────────────────
            kpi_cols = st.columns(4)
            revenue_total   = df_filtrado['amount'].sum()
            unidades_total  = df_filtrado['quantity'].sum() if 'quantity' in df_filtrado.columns else 0
            ticket_promedio = df_filtrado['amount'].mean()
            n_transacciones = len(df_filtrado)

            kpi_cols[0].metric("Revenue total",    f"${revenue_total:,.0f}")
            kpi_cols[1].metric("Unidades vendidas", f"{unidades_total:,.0f}")
            kpi_cols[2].metric("Ticket promedio",   f"${ticket_promedio:,.1f}")
            kpi_cols[3].metric("Transacciones",     f"{n_transacciones:,}")

            # Espaciado visual entre KPIs y gráfico
            st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

            # ── Gráfico de área: evolución temporal del revenue ───────────────────
            if tiene_fecha:
                serie_fecha = pd.to_datetime(df_filtrado[COL_FECHA], errors='coerce')

                # Agrupación inicial diaria para chequear si hay datos
                revenue_tiempo = (
                    df_filtrado['amount']
                    .groupby(serie_fecha.dt.to_period('D'))
                    .sum()
                    .reset_index()
                )
                revenue_tiempo.columns = ['periodo', 'revenue']

                if not revenue_tiempo.empty and revenue_tiempo['revenue'].sum() > 0:
                    # Selector de granularidad: el usuario elige si ver por día, mes o año
                    col_gran, _ = st.columns([1, 3])
                    with col_gran:
                        granularidad = st.selectbox(
                            "Granularidad",
                            options=["Diario", "Mensual", "Anual"],
                            index=0,
                            key="rf04_granularidad",
                            label_visibility="collapsed",
                        )

                    freq_map  = {"Diario": "D", "Mensual": "M", "Anual": "Y"}
                    freq      = freq_map[granularidad]

                    # Reagrupamos con la granularidad elegida
                    revenue_tiempo = (
                        df_filtrado['amount']
                        .groupby(serie_fecha.dt.to_period(freq))
                        .sum()
                        .reset_index()
                    )
                    revenue_tiempo.columns = ['periodo', 'revenue']
                    revenue_tiempo['periodo_dt'] = revenue_tiempo['periodo'].dt.to_timestamp()

                    # Formatos de etiqueta según granularidad
                    fmt = {'Diario': '%d/%m/%Y', 'Mensual': '%b %Y', 'Anual': '%Y'}
                    revenue_tiempo['label'] = revenue_tiempo['periodo_dt'].dt.strftime(fmt[granularidad])

                    # Gráfico de área con go.Scatter (fill='tozeroy' rellena hacia el eje X)
                    fig_area = go.Figure()
                    fig_area.add_trace(go.Scatter(
                        x=revenue_tiempo['label'],
                        y=revenue_tiempo['revenue'],
                        mode='lines',
                        fill='tozeroy',
                        line=dict(color='#4f8ef7', width=2),
                        fillcolor='rgba(79,142,247,0.12)',
                        hovertemplate='%{x}<br>Revenue: $%{y:,.0f}<extra></extra>',
                    ))
                    aplicar_layout(fig_area, f"Evolución del Revenue — Vista {granularidad}")
                    fig_area.update_layout(xaxis_tickangle=-30, showlegend=False)

                    # Envolvemos el gráfico en una tarjeta HTML oscura
                    card_grafico("Evolución de ventas — Revenue mensual")
                    st.plotly_chart(fig_area, use_container_width=True)
                    st.markdown("</div>", unsafe_allow_html=True)
                else:
                    st.info("ℹ️ No hay datos de revenue para graficar en el período seleccionado.")


# ══════════════════════════════════════════════════════════════════════════════
# RF-05 — Ventas por Franja Horaria (solo Gerencia)
# Solo se renderiza si la sección activa es "horario"
# ══════════════════════════════════════════════════════════════════════════════
if auth.tiene_permiso("RF-05") and st.session_state.seccion_activa == "horario":
    if auth.tiene_permiso("RF-05"):

        if df_filtrado.empty:
            st.warning("⚠️ No se encontraron transacciones para los filtros seleccionados.")
        elif 'purchase_hour' not in df_filtrado.columns:
            st.warning("⚠️ No se encontró la columna de hora en los datos.")
        else:
            # Contamos transacciones (filas) por hora — no suma de montos,
            # porque la regla de negocio dice "cantidad de transacciones agrupadas por hora"
            ventas_hora = (
                df_filtrado.groupby('purchase_hour')
                .size()
                .reset_index(name='cantidad_transacciones')
            )

            if ventas_hora.empty or ventas_hora['cantidad_transacciones'].sum() == 0:
                st.info("ℹ️ No se registraron transacciones para el período seleccionado.")
            else:
                fig_hora = go.Figure()
                fig_hora.add_trace(go.Bar(
                    x=ventas_hora['purchase_hour'],
                    y=ventas_hora['cantidad_transacciones'],
                    marker_color='#4f8ef7',
                    hovertemplate='%{x}hs<br>Transacciones: %{y}<extra></extra>',
                ))
                aplicar_layout(fig_hora, "Ventas por franja horaria")
                fig_hora.update_layout(
                    xaxis=dict(tickmode='linear', tick0=0, dtick=2, gridcolor="#1e2a3a"),
                    yaxis=dict(gridcolor="#1e2a3a"),
                    bargap=0.3,
                    showlegend=False,
                )
                card_grafico("Ventas por franja horaria")
                st.plotly_chart(fig_hora, use_container_width=True)
                st.markdown("</div>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# RF-07 — Ranking de Productos (todos los roles)
# La clave "ranking" es la misma para todos los roles que tienen este ítem
# ══════════════════════════════════════════════════════════════════════════════
if auth.tiene_permiso("RF-07") and st.session_state.seccion_activa == "ranking":
    if auth.tiene_permiso("RF-07"):

        if df_filtrado.empty:
            st.warning("⚠️ No se encontraron transacciones para los filtros seleccionados.")
        elif 'product_name' not in df_filtrado.columns or 'quantity' not in df_filtrado.columns:
            st.warning("⚠️ No se encontraron las columnas necesarias para generar el ranking.")
        else:
            # Controles de cantidad de productos a mostrar y criterio de ordenamiento
            col_top, col_orden, _ = st.columns([1, 2, 3])
            with col_top:
                top_n = st.selectbox("Mostrar", options=[5, 10, 20, 50], index=0, key="rf07_top_n")
            with col_orden:
                orden = st.selectbox(
                    "Ordenar por",
                    options=["Unidades (mayor a menor)", "Unidades (menor a mayor)"],
                    index=0,
                    key="rf07_orden",
                )

            ascending = orden == "Unidades (menor a mayor)"

            ranking = (
                df_filtrado.groupby('product_name')['quantity']
                .sum()
                .reset_index()
                .sort_values('quantity', ascending=ascending)
                .head(top_n)
            )

            if ranking.empty or ranking['quantity'].sum() == 0:
                st.info("ℹ️ No se registraron unidades vendidas para el período seleccionado.")
            else:
                fig_ranking = go.Figure()
                fig_ranking.add_trace(go.Bar(
                    x=ranking['quantity'],
                    y=ranking['product_name'],
                    orientation='h',
                    marker_color='#4f8ef7',
                    hovertemplate='%{y}<br>Unidades: %{x:,}<extra></extra>',
                ))
                aplicar_layout(fig_ranking, f"Top {top_n} Productos más vendidos")
                # categoryorder controla el orden visual de las barras en el eje Y
                fig_ranking.update_layout(
                    yaxis=dict(
                        categoryorder='total ascending' if not ascending else 'total descending',
                        gridcolor="#1e2a3a"
                    ),
                    xaxis=dict(gridcolor="#1e2a3a"),
                    showlegend=False,
                )
                card_grafico(f"Top {top_n} productos más vendidos")
                st.plotly_chart(fig_ranking, use_container_width=True)
                st.markdown("</div>", unsafe_allow_html=True)