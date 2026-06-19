"""
Crea la tabla 'usuarios' e inserta usuarios de prueba.
Ejecutar UNA SOLA VEZ antes de levantar la app:

    python init_usuarios.py

Usuarios creados:
    gerencia@drinkdash.com   /  Gerencia123!
    direccion@drinkdash.com  /  Direccion123!
    ventas@drinkdash.com     /  Ventas123!
    marketing@drinkdash.com  /  Marketing123!
    marketing2@drinkdash.com /  Marketing2123!
"""

import sqlite3
import bcrypt
from datetime import datetime, timedelta
from pathlib import Path
# ── Ruta DB ────────────────────────────────────────────────────────────────────

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH  = BASE_DIR / "dags" / "data" / "drinkdash.db"

USUARIOS_PRUEBA = [
    {"nombre": "Admin Gerencia",   "email": "gerencia@drinkdash.com",  "password": "Gerencia123!",  "rol": "gerencia"},
    {"nombre": "Admin Dirección",  "email": "direccion@drinkdash.com", "password": "Direccion123!", "rol": "direccion"},
    {"nombre": "Admin Ventas",     "email": "ventas@drinkdash.com",    "password": "Ventas123!",    "rol": "ventas"},
    {"nombre": "Admin Marketing",  "email": "marketing@drinkdash.com", "password": "Marketing123!", "rol": "marketing"},
    {"nombre": "Admin Marketing 2", "email": "marketing2@drinkdash.com", "password": "Marketing2123!", "rol": "marketing"},
]


def hashear_password(password: str) -> str:
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def crear_tabla_usuarios(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre            TEXT    NOT NULL,
            email             TEXT    NOT NULL UNIQUE,
            password_hash     TEXT    NOT NULL,
            rol               TEXT    NOT NULL CHECK(rol IN ('gerencia','direccion','ventas','marketing')),
            intentos_fallidos INTEGER NOT NULL DEFAULT 0,
            bloqueado_hasta   TEXT    DEFAULT NULL,
            creado_en         TEXT    NOT NULL DEFAULT (datetime('now'))
        )
    """)
    conn.commit()
    print("✓ Tabla 'usuarios' verificada / creada.")


def insertar_usuarios_prueba(conn):
    insertados = omitidos = 0
    for u in USUARIOS_PRUEBA:
        existe = conn.execute(
            "SELECT 1 FROM usuarios WHERE email = ?", (u["email"],)
        ).fetchone()
        if existe:
            omitidos += 1
            print(f"  · Omitido (ya existe): {u['email']}")
            continue
        conn.execute(
            "INSERT INTO usuarios (nombre, email, password_hash, rol) VALUES (?, ?, ?, ?)",
            (u["nombre"], u["email"], hashear_password(u["password"]), u["rol"])
        )
        insertados += 1
        print(f"  ✓ Creado: {u['email']}  [rol: {u['rol']}]")
    conn.commit()
    print(f"\nResumen: {insertados} creado(s), {omitidos} omitido(s).")

def bloquear_usuario(conn, email: str, minutos: int):
    bloqueado_hasta = (datetime.now() + timedelta(minutes=minutos)).isoformat()
    conn.execute(
        "UPDATE usuarios SET bloqueado_hasta = ?, intentos_fallidos = 0 WHERE email = ?",
        (bloqueado_hasta, email)
    )
    conn.commit()
    print(f"Usuario '{email}' bloqueado hasta {bloqueado_hasta}.")

if __name__ == "__main__":

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    print(f"Conectando a: {DB_PATH}\n")
    conn = sqlite3.connect(DB_PATH)
    try:
        crear_tabla_usuarios(conn)
        print("\nInsertando usuarios de prueba:")
        insertar_usuarios_prueba(conn)
        print("\n" + "─" * 45)
        print("BLQUEO DE USUARIOS DE PRUEBA:")
        print("─" * 45)
        bloquear_usuario(conn, "marketing2@drinkdash.com", 999999)
        print("CREDENCIALES DE PRUEBA:")
        print("─" * 45)
        for u in USUARIOS_PRUEBA:
            print(f"  {u['rol']:<12}  {u['email']:<30}  {u['password']})")
    finally:
        conn.close()
