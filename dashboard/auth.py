"""
Módulo de autenticación y control de roles (RBAC) para DrinkDash.
Maneja: login, logout, sesión con st.session_state, hashing bcrypt
y bloqueo temporal por intentos fallidos (RNF-01).
"""

import sqlite3
import bcrypt
import streamlit as st
from datetime import datetime, timedelta
import os

# ── Ruta a la base de datos ────────────────────────────────────────────────────
if os.name == 'nt':
    DB_PATH = "data/drinkdash.db"
else:
    DB_PATH = "/opt/airflow/data/drinkdash.db"

# ── Seguridad ──────────────────────────────────────────────────────────────────
MAX_INTENTOS_FALLIDOS    = 3   # RNF-01: bloqueo tras 3 intentos
DURACION_BLOQUEO_MINUTOS = 15

# ── Permisos por rol (RBAC) ────────────────────────────────────────────────────
# Cada entrada mapea un rol a los RF que puede ver.
# A medida que se implementen nuevos RF en app_streamlit.py,
# simplemente se agregan a la lista del rol correspondiente.
PERMISOS_POR_ROL = {
    "gerencia": {
        "label": "Gerencia",
        "rfs": ["RF-04", "RF-05", "RF-06", "RF-07", "RF-08", "RF-09", "RF-10"],
        "puede_exportar": False,
    },
    "direccion": {
        "label": "Dirección",
        "rfs": ["RF-04", "RF-06", "RF-07", "RF-08", "RF-09", "RF-12", "RF-13", "RF-14"],
        "puede_exportar": True,
    },
    "ventas": {
        "label": "Ventas",
        "rfs": ["RF-04", "RF-06", "RF-07", "RF-08", "RF-10"],
        "puede_exportar": False,
    },
    "marketing": {
        "label": "Marketing",
        "rfs": ["RF-04", "RF-06", "RF-07", "RF-08", "RF-11", "RF-12", "RF-14"],
        "puede_exportar": False,
    },
}


# ── Helpers de base de datos ───────────────────────────────────────────────────

def _get_conn():
    return sqlite3.connect(DB_PATH)


def _get_usuario(email: str):
    """Devuelve el registro del usuario como dict, o None si no existe."""
    try:
        conn = _get_conn()
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM usuarios WHERE email = ?",
            (email.lower().strip(),)
        ).fetchone()
        conn.close()
        return dict(row) if row else None
    except Exception:
        return None


def _actualizar_intentos(email: str, resetear: bool = False):
    """Incrementa los intentos fallidos o los resetea tras un login exitoso."""
    conn = _get_conn()
    if resetear:
        conn.execute(
            "UPDATE usuarios SET intentos_fallidos = 0, bloqueado_hasta = NULL WHERE email = ?",
            (email.lower().strip(),)
        )
    else:
        row = conn.execute(
            "SELECT intentos_fallidos FROM usuarios WHERE email = ?",
            (email.lower().strip(),)
        ).fetchone()
        if row:
            nuevos_intentos = row[0] + 1
            bloqueado_hasta = None
            if nuevos_intentos >= MAX_INTENTOS_FALLIDOS:
                bloqueado_hasta = (
                    datetime.now() + timedelta(minutes=DURACION_BLOQUEO_MINUTOS)
                ).isoformat()
            conn.execute(
                "UPDATE usuarios SET intentos_fallidos = ?, bloqueado_hasta = ? WHERE email = ?",
                (nuevos_intentos, bloqueado_hasta, email.lower().strip())
            )
    conn.commit()
    conn.close()


# ── Lógica de autenticación ────────────────────────────────────────────────────

def verificar_credenciales(email: str, password: str):
    """
    Valida credenciales contra la base de datos.
    Retorna (True, "ok") o (False, motivo).
    """
    usuario = _get_usuario(email)

    if usuario is None:
        return False, "usuario_no_encontrado"

    if usuario.get("bloqueado_hasta"):
        bloqueado_hasta = datetime.fromisoformat(usuario["bloqueado_hasta"])
        if datetime.now() < bloqueado_hasta:
            minutos = int((bloqueado_hasta - datetime.now()).total_seconds() / 60) + 1
            return False, f"cuenta_bloqueada:{minutos}"

    try:
        ok = bcrypt.checkpw(
            password.encode("utf-8"),
            usuario["password_hash"].encode("utf-8")
        )
    except Exception:
        return False, "error_db"

    if ok:
        _actualizar_intentos(email, resetear=True)
        return True, "ok"

    _actualizar_intentos(email, resetear=False)
    return False, "contrasena_incorrecta"


def inicializar_sesion():
    """Inicializa las claves de sesión. Llamar al inicio de app_streamlit.py."""
    defaults = {
        "autenticado":    False,
        "usuario_email":  None,
        "usuario_nombre": None,
        "usuario_rol":    None,
        "permisos":       {},
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def login(email: str, password: str):
    """Autentica al usuario y carga su sesión si las credenciales son válidas."""
    ok, motivo = verificar_credenciales(email, password)
    if ok:
        usuario = _get_usuario(email)
        rol = usuario["rol"].lower()
        st.session_state.autenticado    = True
        st.session_state.usuario_email  = usuario["email"]
        st.session_state.usuario_nombre = usuario["nombre"]
        st.session_state.usuario_rol    = rol
        st.session_state.permisos       = PERMISOS_POR_ROL.get(rol, {})
    return ok, motivo


def logout():
    """Cierra la sesión limpiando el estado. RF-02."""
    for key in ["autenticado", "usuario_email", "usuario_nombre", "usuario_rol", "permisos"]:
        st.session_state[key] = False if key == "autenticado" else None
    st.rerun()


def requiere_autenticacion():
    """
    Guard: si el usuario no está logueado, muestra la pantalla de login
    y detiene la ejecución del resto del script.
    """
    inicializar_sesion()
    if not st.session_state.autenticado:
        _mostrar_pantalla_login()
        st.stop()


def tiene_permiso(rf: str) -> bool:
    """Verifica si el rol activo tiene acceso a un RF."""
    return rf in st.session_state.get("permisos", {}).get("rfs", [])


def puede_exportar() -> bool:
    """Verifica si el rol activo puede exportar reportes (solo Dirección)."""
    return st.session_state.get("permisos", {}).get("puede_exportar", False)


# ── Componentes de UI ──────────────────────────────────────────────────────────

def _mostrar_pantalla_login():
    """Renderiza el formulario de inicio de sesión."""
    _, col, _ = st.columns([1, 2, 1])
    with col:
        st.markdown("## DrinkDash")
        st.caption("DataVista Solutions · Grupo 10")
        st.divider()

        with st.form("form_login", clear_on_submit=True):
            email    = st.text_input("Correo electrónico", placeholder="usuario@drinkdash.com")
            password = st.text_input("Contraseña", type="password", placeholder="••••••••")
            submit   = st.form_submit_button("Ingresar", use_container_width=True, type="primary")

        if submit:
            if not email or not password:
                st.error("Completá los dos campos para continuar.")
            else:
                ok, motivo = login(email, password)
                if ok:
                    st.rerun()
                else:
                    _mostrar_error_login(motivo)

        st.caption("© 2026 DataVista Solutions · Acceso restringido")


def _mostrar_error_login(motivo: str):
    if motivo == "usuario_no_encontrado":
        st.error("Usuario o contraseña incorrectos.")
    elif motivo.startswith("cuenta_bloqueada"):
        st.error("Inicio de sesión fallido, su usuario ha sido bloqueado.")
    elif motivo == "contrasena_incorrecta":
        st.error("Usuario o contraseña incorrectos.")
    else:
        st.error("Ocurrió un error al iniciar sesión. Intentá nuevamente.")


def mostrar_barra_usuario():
    """
    Muestra en el sidebar el nombre, rol del usuario y el botón de logout.
    Llamar dentro de `with st.sidebar:` en app_streamlit.py.
    """
    rol_label = st.session_state.get("permisos", {}).get("label", "—")
    st.markdown(f"**{st.session_state.usuario_nombre or st.session_state.usuario_email}**")
    st.caption(f"Rol: {rol_label}")
    st.divider()
    if st.button("Cerrar sesión", use_container_width=True):
        logout()
