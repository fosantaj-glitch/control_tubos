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
    /* Degradado de arriba-izquierda hacia abajo-derecha */
    .stApp {
        background: linear-gradient(135deg, #ced4da 0%, #e9ecef 40%, #ffffff 100%);
        background-attachment: fixed;
    }

    /* Estilo del menú lateral (Sidebar) */
    [data-testid="stSidebar"] {
        background-color: #212529;
        color: white !important;
    }
    
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
        color: white !important;
    }

    /* Estilo de botones de navegación */
    div[role="radiogroup"] label {
        color: white !important;
        background-color: rgba(255, 255, 255, 0.05);
        margin-bottom: 5px;
        border-radius: 5px;
        padding: 10px;
    }

    /* Estilo para los cuadros blancos de contenido */
    [data-testid="stHeader"], .stForm, .stDataFrame {
        background-color: white;
        border-radius: 12px;
        padding: 20px;
        box-shadow: 5px 5px 15px rgba(0,0,0,0.05);
    }
    
    /* Estilo para el logo */
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

# Nombre exacto del archivo que debe estar en GitHub
NOMBRE_LOGO = "logo.jpg"

def login():
    if not st.session_state.autenticado:
        c1, c2, c3 = st.columns([1, 2, 1])
        with c2:
            st.markdown("<br><br>", unsafe_allow_html=True)
            try:
                st.image(NOMBRE_LOGO, use_container_width=True)
            except:
                pass
            
            st.title("🏭 Inventario GUILLÉN")
            st.subheader("Acceso al Sistema")
            clave = st.text_input("Contraseña", type="password", key="main_login")
            
            if st.button("Ingresar", type="primary", use_container_width=True):
                if clave == "Tubos2026":
                    st.session_state.autenticado = True
                    st.rerun() 
                else:
                    st.error("❌ Clave incorrecta")
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
    c.execute('''CREATE TABLE IF NOT EXISTS diametros (id INTEGER PRIMARY KEY AUTOINCREMENT, medida TEXT, precio REAL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS clientes (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, telefono TEXT)''')
    
    c.execute("SELECT COUNT(*) FROM diametros")
    if c.fetchone()[0] == 0:
        iniciales = [("10 cm", 0.0), ("15 cm", 0.0), ("20 cm", 0.0), ("30 cm", 0.0), ("50 cm", 0.0), ("100 cm", 0.0)]
        c.executemany("INSERT INTO diametros (medida, precio) VALUES (?,?)", iniciales)
    conn.commit()
    conn.close()

init_db()

def ejecutar_respaldo_total():
    try:
        conn = get_connection()
        df_p = pd.read_sql("SELECT * FROM produccion", conn).fillna("")
        df_v = pd.read_sql("SELECT * FROM pedidos", conn).fillna("")
        df_e = pd.read_sql("SELECT * FROM entregas", conn).fillna("")
        df_d = pd.read_sql("SELECT medida, precio FROM diametros", conn).fillna("")
        df_c = pd.read_sql("SELECT nombre, telefono FROM clientes", conn).fillna("")
        conn.close()
        
        payload = {
            "accion": "sobreescribir",
            "Produccion": [df_p.columns.tolist()] + df_p.astype(str).values.tolist(),
            "Pedidos": [df_v.columns.tolist()] + df_v.astype(str).values.tolist(),
            "Entregas": [df_e.columns.tolist()] + df_e.astype(str).values.tolist(),
            "Diametros": [df_d.columns.tolist()] + df_d.astype(str).values.tolist(),
            "Clientes": [df_c.columns.tolist()] + df_c.astype(str).values.tolist()
        }
        requests.post(URL_GOOGLE, json=payload, timeout=25)
    except: pass

def obtener_diametros():
    conn = get_connection()
    df = pd.read_sql("SELECT medida FROM diametros ORDER BY id ASC", conn)
    conn.close()
    return ["Seleccione..."] + df['medida'].tolist()

def obtener_clientes():
    conn = get_connection()
    df = pd.read_sql("SELECT nombre FROM clientes ORDER BY nombre ASC", conn)
    conn.close()
    return ["Seleccione Cliente..."] + df['nombre'].tolist()

# --- 5. CUERPO DE LA APP ---
if login():
    st.sidebar.markdown("<br>", unsafe_allow_html=True)
    
    try:
        st.sidebar.image(NOMBRE_LOGO, use_container_width=True)
    except:
        st.sidebar.title("GUILLÉN")

    if st.sidebar.button("Cerrar Sesión"):
        st.session_state.autenticado = False
        st.session_state.config_autenticado = False
        st.rerun()
    
    st.sidebar.divider()
    
    # Definición clara de las opciones del menú
    OPCION_RESUMEN = "📊 Resumen de Patio"
    OPCION_PROD = "🧱 Fabricación Diaria"
    OPCION_PEDIDOS = "📝 Pedidos y Ventas"
    OPCION_DESPACHOS = "🚚 Despachos"
    OPCION_CONFIG = "⚙️ Configuración"
    
    menu = st.sidebar.radio("MENÚ PRINCIPAL", [OPCION_RESUMEN, OPCION_PROD, OPCION_PEDIDOS, OPCION_DESPACHOS, OPCION_CONFIG])

    # Corrección CRÍTICA: La comparación ahora coincide exactamente con el menú
    if menu != OPCION_CONFIG:
        st.session_state.config_autenticado = False

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
            d_p = c2.selectbox("Diámetro", DIAM_DB)
            n_p = c3.number_input("Cantidad", min_value=1, step=1)
            if st.form_submit_button("Guardar Fabricación", type="primary"):
                if d_p != "Seleccione...":
                    conn = get_connection(); conn.execute("INSERT INTO produccion (fecha, diametro, cantidad) VALUES (?,?,?)", (f_p.strftime("%Y-%m-%d"), d_p, n_p)); conn.commit(); conn.close()
                    st.success("✅ Datos guardados")
                    time.sleep(1); st.rerun()

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
                        st.session_state.config_autenticado = True
                        st.rerun()
                    else:
                        st.error("Clave incorrecta")
        else:
            st.success("🔓 Acceso de Administrador concedido")
            t1, t2 = st.tabs(["📏 Diámetros y Precios", "👥 Clientes"])
            
            with t1:
                conn = get_connection()
                df_d = pd.read_sql("SELECT id, medida as Medida, precio as Precio FROM diametros ORDER BY id ASC", conn)
                st.write("**Catálogo de Productos**")
                st.dataframe(df_d.drop(columns=['id']), use_container_width=True, hide_index=True)
                
                c_a, c_e, c_b = st.columns(3)
                with c_a:
                    with st.form("a_d", clear_on_submit=True):
                        st.write("**Nuevo**")
                        n_m = st.text_input("Nombre Medida")
                        n_pr = st.number_input("Precio", min_value=0.0)
                        if st.form_submit_button("Guardar"):
                            if n_m: conn.execute("INSERT INTO diametros (medida, precio) VALUES (?,?)", (n_m, n_pr)); conn.commit(); st.rerun()
                with c_e:
                    if not df_d.empty:
                        with st.form("e_d"):
                            st.write("**Editar**")
                            sel = st.selectbox("Elegir", df_d['Medida'].tolist())
                            new_m = st.text_input("Nuevo Nombre")
                            new_p = st.number_input("Nuevo Precio", min_value=0.0)
                            if st.form_submit_button("Actualizar"):
                                if new_m:
                                    conn.execute("UPDATE diametros SET medida=?, precio=? WHERE medida=?", (new_m, new_p, sel))
                                    conn.execute("UPDATE produccion SET diametro=? WHERE diametro=?", (new_m, sel))
                                    conn.execute("UPDATE pedidos SET diametro=? WHERE diametro=?", (new_m, sel))
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
                        nn = st.text_input("Nombre/Empresa")
                        nt = st.text_input("Teléfono")
                        if st.form_submit_button("Guardar"):
                            if nn: conn.execute("INSERT INTO clientes (nombre, telefono) VALUES (?,?)", (nn, nt)); conn.commit(); st.rerun()
                with c2:
                    if not df_c.empty:
                        with st.form("e_c"):
                            st.write("**Corregir**")
                            sel_c = st.selectbox("Elegir Cliente", df_c['Nombre'].tolist())
                            new_n = st.text_input("Nombre Correcto")
                            new_t = st.text_input("Teléfono Correcto")
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