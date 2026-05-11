Entendido, Mateo. Vamos a hacer esos cambios quirúrgicos en la estructura de tu catálogo para que sea mucho más detallado y profesional.

He actualizado el código para que:

En la base de datos: Se cree automáticamente el campo "Tipo" (para que puedas poner si es tubo simple, reforzado, etc.).

En la tabla visual: El orden ahora es: Medida | Tipo | Valor Unitario | Precio más IVA.

Cálculo automático: Tú solo ingresas el valor unitario y la app calcula el 15% de IVA automáticamente para mostrarte el total.

Formularios: He actualizado los cuadros de "Nuevo" y "Editar" para que también te pidan el tipo de tubo.

Aquí tienes el código completo de tu archivo app.py. Reemplaza todo el contenido en GitHub y dale a Commit changes:

Python
import streamlit as st
import pandas as pd
import sqlite3
import requests
from datetime import datetime, date, timezone, timedelta
import time
import os

# --- 1. CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(
    page_title="Control de Tubos - GUILLÉN",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. DISEÑO VISUAL (DEGRADADO DIAGONAL) ---
st.markdown(
    """
    <style>
    .stApp {
        background: linear-gradient(135deg, #ced4da 0%, #e9ecef 40%, #ffffff 100%);
        background-attachment: fixed;
    }
    [data-testid="stSidebar"] {
        background-color: #212529;
        color: white !important;
    }
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
        color: white !important;
    }
    div[role="radiogroup"] label {
        color: white !important;
        background-color: rgba(255, 255, 255, 0.05);
        margin-bottom: 5px;
        border-radius: 5px;
        padding: 10px;
    }
    [data-testid="stHeader"], .stForm, .stDataFrame {
        background-color: white;
        border-radius: 12px;
        padding: 20px;
        box-shadow: 5px 5px 15px rgba(0,0,0,0.05);
    }
    [data-testid="stSidebar"] img {
        border-radius: 10px;
        border: 2px solid #ffffff40;
        margin-bottom: 20px;
    }
    </style>
    """,
    unsafe_allow_html=True
)

URL_GOOGLE = "https://script.google.com/macros/s/AKfycbw2YUNMCJB0fDNZ1jCWFmcgXv5VABsCXvAi6rsUXAVnlsUaQB2kgBvZCuBxEFVMOOL1/exec"

# --- 3. SISTEMA DE SEGURIDAD ---
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False
if "config_autenticado" not in st.session_state:
    st.session_state.config_autenticado = False

NOMBRE_LOGO = "logo.jpg"

def login():
    if not st.session_state.autenticado:
        c1, c2, c3 = st.columns([1, 2, 1])
        with c2:
            st.markdown("<br><br>", unsafe_allow_html=True)
            try: st.image(NOMBRE_LOGO, use_container_width=True)
            except: pass
            st.title("🏭 Inventario GUILLÉN")
            st.subheader("Acceso al Sistema")
            clave = st.text_input("Contraseña", type="password", key="main_login")
            if st.button("Ingresar", type="primary", use_container_width=True):
                if clave == "Tubos2026":
                    st.session_state.autenticado = True
                    st.rerun() 
                else: st.error("❌ Clave incorrecta")
        return False
    return True

# --- 4. BASE DE DATOS ---
def obtener_fecha_ecuador():
    tz_ecuador = timezone(timedelta(hours=-5))
    return datetime.now(tz_ecuador).date()

def get_connection():
    return sqlite3.connect('control_tubos_db.db', check_same_thread=False)

def init_db():
    conn = get_connection()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS produccion (id INTEGER PRIMARY KEY AUTOINCREMENT, fecha TEXT, diametro TEXT, cantidad INTEGER)''')
    c.execute('''CREATE TABLE IF NOT EXISTS pedidos (id INTEGER PRIMARY KEY AUTOINCREMENT, fecha TEXT, cliente TEXT, diametro TEXT, cantidad_total INTEGER, estado TEXT, observaciones TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS entregas (id INTEGER PRIMARY KEY AUTOINCREMENT, pedido_id INTEGER, fecha TEXT, cantidad_entregada INTEGER, FOREIGN KEY(pedido_id) REFERENCES pedidos(id))''')
    
    # Tabla de Diámetros con columna TIPO
    c.execute('''CREATE TABLE IF NOT EXISTS diametros (id INTEGER PRIMARY KEY AUTOINCREMENT, medida TEXT, tipo TEXT, precio REAL)''')
    try: c.execute("ALTER TABLE diametros ADD COLUMN tipo TEXT")
    except: pass

    c.execute('''CREATE TABLE IF NOT EXISTS clientes (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, telefono TEXT)''')
    
    c.execute("SELECT COUNT(*) FROM diametros")
    if c.fetchone()[0] == 0:
        iniciales = [("10 cm", "Estandar", 0.0), ("15 cm", "Estandar", 0.0), ("20 cm", "Estandar", 0.0), ("30 cm", "Estandar", 0.0), ("50 cm", "Estandar", 0.0), ("100 cm", "Estandar", 0.0)]
        c.executemany("INSERT INTO diametros (medida, tipo, precio) VALUES (?,?,?)", iniciales)
    conn.commit()
    conn.close()

init_db()

def obtener_diametros():
    conn = get_connection()
    df = pd.read_sql("SELECT medida, tipo FROM diametros ORDER BY id ASC", conn)
    conn.close()
    return ["Seleccione..."] + [f"{r['medida']} ({r['tipo']})" if r['tipo'] else r['medida'] for _, r in df.iterrows()]

def obtener_clientes():
    conn = get_connection()
    df = pd.read_sql("SELECT nombre FROM clientes ORDER BY nombre ASC", conn)
    conn.close()
    return ["Seleccione Cliente..."] + df['nombre'].tolist()

# --- 5. CUERPO DE LA APP ---
if login():
    try: st.sidebar.image(NOMBRE_LOGO, use_container_width=True)
    except: st.sidebar.title("GUILLÉN")

    if st.sidebar.button("Cerrar Sesión"):
        st.session_state.autenticado = False
        st.session_state.config_autenticado = False
        st.rerun()
    
    st.sidebar.divider()
    OPCION_RESUMEN, OPCION_PROD, OPCION_PEDIDOS, OPCION_DESPACHOS, OPCION_CONFIG = "📊 Resumen de Patio", "🧱 Fabricación Diaria", "📝 Pedidos y Ventas", "🚚 Despachos", "⚙️ Configuración"
    menu = st.sidebar.radio("MENÚ PRINCIPAL", [OPCION_RESUMEN, OPCION_PROD, OPCION_PEDIDOS, OPCION_DESPACHOS, OPCION_CONFIG])

    if menu != OPCION_CONFIG: st.session_state.config_autenticado = False

    DIAM_DB = obtener_diametros()
    CLI_DB = obtener_clientes()

    if menu == OPCION_RESUMEN:
        st.header("📊 Estado Actual del Inventario")
        st.info("Aquí aparecerá el resumen de tubos disponibles próximamente.")

    elif menu == OPCION_PROD:
        st.header("🧱 Registro de Producción")
        with st.form("f_prod"):
            c1, c2, c3 = st.columns(3)
            f_p = c1.date_input("Fecha", obtener_fecha_ecuador())
            d_p = c2.selectbox("Tubo (Medida y Tipo)", DIAM_DB)
            n_p = c3.number_input("Cantidad", min_value=1, step=1)
            if st.form_submit_button("Guardar Fabricación", type="primary"):
                if d_p != "Seleccione...":
                    conn = get_connection(); conn.execute("INSERT INTO produccion (fecha, diametro, cantidad) VALUES (?,?,?)", (f_p.strftime("%Y-%m-%d"), d_p, n_p)); conn.commit(); conn.close()
                    st.success("✅ Datos guardados"); time.sleep(1); st.rerun()

    elif menu == OPCION_PEDIDOS:
        st.header("📝 Registro de Pedidos")
        with st.form("f_ped"):
            c1, c2 = st.columns(2)
            f_v = c1.date_input("Fecha", obtener_fecha_ecuador())
            cl_v = c2.selectbox("Cliente", CLI_DB)
            c3, c4 = st.columns(2)
            di_v = c3.selectbox("Tubo", DIAM_DB)
            ca_v = c4.number_input("Cantidad Solicitada", min_value=1, step=1)
            ob = st.text_area("Notas del Pedido")
            if st.form_submit_button("Crear Pedido", type="primary"):
                if di_v != "Seleccione..." and cl_v != "Seleccione Cliente...":
                    conn = get_connection(); conn.execute("INSERT INTO pedidos (fecha, cliente, diametro, cantidad_total, estado, observaciones) VALUES (?,?,?,?,?,?)", (f_v.strftime("%Y-%m-%d"), cl_v, di_v, ca_v, "Pendiente", ob)); conn.commit(); conn.close()
                    st.success("✅ Pedido registrado"); time.sleep(1); st.rerun()

    elif menu == OPCION_DESPACHOS:
        st.header("🚚 Control de Entregas")
        st.info("Módulo para despachar tubos por camión próximamente.")

    elif menu == OPCION_CONFIG:
        st.header("⚙️ Administración de Datos")
        if not st.session_state.config_autenticado:
            with st.form("admin_lock"):
                cl_adm = st.text_input("Clave de Administrador", type="password")
                if st.form_submit_button("Desbloquear"):
                    if cl_adm == "Tubos2026":
                        st.session_state.config_autenticado = True; st.rerun()
                    else: st.error("Clave incorrecta")
        else:
            st.success("🔓 Acceso de Administrador concedido")
            t1, t2 = st.tabs(["📏 Diámetros y Precios", "👥 Clientes"])
            
            with t1:
                conn = get_connection()
                # CARGA DE DATOS CON NUEVAS COLUMNAS Y CÁLCULO DE IVA
                df_d = pd.read_sql("SELECT id, medida as Medida, tipo as Tipo, precio as [Valor Unitario] FROM diametros ORDER BY id ASC", conn)
                if not df_d.empty:
                    df_d['Precio más IVA'] = df_d['Valor Unitario'] * 1.15
                    # Formatear para visualización
                    df_v = df_d.copy()
                    df_v['Valor Unitario'] = df_v['Valor Unitario'].apply(lambda x: f"${x:.2f}")
                    df_v['Precio más IVA'] = df_v['Precio más IVA'].apply(lambda x: f"${x:.2f}")
                    st.write("**Catálogo de Productos**")
                    st.dataframe(df_v.drop(columns=['id']), use_container_width=True, hide_index=True)
                
                c_a, c_e, c_b = st.columns(3)
                with c_a:
                    with st.form("a_d", clear_on_submit=True):
                        st.write("**Nuevo Producto**")
                        n_m = st.text_input("Medida")
                        n_t = st.text_input("Tipo (Ej: Simple, Reforzado)")
                        n_pr = st.number_input("Valor Unitario", min_value=0.0)
                        if st.form_submit_button("Guardar"):
                            if n_m: conn.execute("INSERT INTO diametros (medida, tipo, precio) VALUES (?,?,?)", (n_m, n_t, n_pr)); conn.commit(); st.rerun()
                with c_e:
                    if not df_d.empty:
                        with st.form("e_d"):
                            st.write("**Editar Producto**")
                            sel = st.selectbox("Elegir Medida", df_d['Medida'].tolist())
                            new_m = st.text_input("Nuevo Nombre Medida")
                            new_t = st.text_input("Nuevo Tipo")
                            new_p = st.number_input("Nuevo Valor Unitario", min_value=0.0)
                            if st.form_submit_button("Actualizar"):
                                if new_m:
                                    conn.execute("UPDATE diametros SET medida=?, tipo=?, precio=? WHERE medida=?", (new_m, new_t, new_p, sel))
                                    conn.execute("UPDATE produccion SET diametro=? WHERE diametro LIKE ?", (f"{new_m}%", f"{sel}%"))
                                    conn.execute("UPDATE pedidos SET diametro=? WHERE diametro LIKE ?", (f"{new_m}%", f"{sel}%"))
                                    conn.commit(); st.rerun()
                with c_b:
                    if not df_d.empty:
                        with st.form("b_d"):
                            st.write("**Borrar**")
                            del_s = st.selectbox("Eliminar", df_d['Medida'].tolist())
                            if st.form_submit_button("Borrar"):
                                conn.execute("DELETE FROM diametros WHERE medida=?", (del_s,)); conn.commit(); st.rerun()
                conn.close()

            with t2:
                conn = get_connection()
                df_c = pd.read_sql("SELECT id, nombre as Nombre, telefono as Telefono FROM clientes ORDER BY nombre ASC", conn)
                st.write("**Directorio de Clientes**")
                st.dataframe(df_c.drop(columns=['id']), use_container_width=True, hide_index=True)
                c1, c2, c3 = st.columns(3)
                with c1:
                    with st.form("a_c", clear_on_submit=True):
                        st.write("**Registrar**")
                        nn, nt = st.text_input("Nombre/Empresa"), st.text_input("Teléfono")
                        if st.form_submit_button("Guardar"):
                            if nn: conn.execute("INSERT INTO clientes (nombre, telefono) VALUES (?,?)", (nn, nt)); conn.commit(); st.rerun()
                with c2:
                    if not df_c.empty:
                        with st.form("e_c"):
                            st.write("**Corregir**")
                            sel_c = st.selectbox("Elegir Cliente", df_c['Nombre'].tolist())
                            new_n, new_t = st.text_input("Nombre Correcto"), st.text_input("Teléfono Correcto")
                            if st.form_submit_button("Actualizar"):
                                if new_n:
                                    conn.execute("UPDATE clientes SET nombre=?, telefono=? WHERE nombre=?", (new_n, new_t, sel_c))
                                    conn.execute("UPDATE pedidos SET cliente=? WHERE cliente=?", (new_n, sel_c))
                                    conn.commit(); st.rerun()
                with c3:
                    if not df_c.empty:
                        with st.form("b_c"):
                            st.write("**Borrar**")
                            del_c = st.selectbox("Eliminar Cliente", df_c['Nombre'].tolist())
                            if st.form_submit_button("Borrar"):
                                conn.execute("DELETE FROM clientes WHERE nombre=?", (del_c,)); conn.commit(); st.rerun()
                conn.close()