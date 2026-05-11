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

# URL_GOOGLE = "PEGA_AQUI_TU_URL_DE_APPS_SCRIPT" # Avísame cuando la tengas para activarlo

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
    c.execute('''CREATE TABLE IF NOT EXISTS diametros (id INTEGER PRIMARY KEY AUTOINCREMENT, medida TEXT, tipo TEXT, precio REAL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS clientes (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, telefono TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS configuracion (id INTEGER PRIMARY KEY, parametro TEXT, valor REAL)''')
    
    if conn.execute("SELECT COUNT(*) FROM configuracion WHERE parametro='iva'").fetchone()[0] == 0:
        conn.execute("INSERT INTO configuracion (parametro, valor) VALUES ('iva', 15.0)")

    if conn.execute("SELECT COUNT(*) FROM diametros").fetchone()[0] == 0:
        iniciales = [("10 cm", "Estandar", 0.0), ("15 cm", "Estandar", 0.0), ("20 cm", "Estandar", 0.0), ("30 cm", "Estandar", 0.0), ("50 cm", "Estandar", 0.0), ("100 cm", "Estandar", 0.0)]
        c.executemany("INSERT INTO diametros (medida, tipo, precio) VALUES (?,?,?)", iniciales)
    
    conn.commit()
    conn.close()

init_db()

def obtener_iva():
    conn = get_connection()
    res = conn.execute("SELECT valor FROM configuracion WHERE parametro='iva'").fetchone()
    conn.close()
    return res[0] if res else 15.0

def obtener_diametros():
    """Obtiene la lista de tubos ordenada ascendentemente por diámetro numérico"""
    conn = get_connection()
    df = pd.read_sql("SELECT medida, tipo FROM diametros", conn)
    conn.close()
    if not df.empty:
        # Extraer números para ordenar (ej: '10 cm' -> 10.0)
        df['num'] = df['medida'].str.extract('(\d+)').astype(float)
        df = df.sort_values('num')
        return ["Seleccione..."] + [f"{r['medida']} ({r['tipo']})" if r['tipo'] else r['medida'] for _, r in df.iterrows()]
    return ["Seleccione..."]

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
    OP_RESUMEN, OP_PROD, OP_PEDIDOS, OP_DESPACHOS, OP_CONFIG = "📊 Resumen de Patio", "🧱 Fabricación Diaria", "📝 Pedidos y Ventas", "🚚 Despachos", "⚙️ Configuración"
    menu = st.sidebar.radio("MENÚ PRINCIPAL", [OP_RESUMEN, OP_PROD, OP_PEDIDOS, OP_DESPACHOS, OP_CONFIG])

    if menu != OP_CONFIG: st.session_state.config_autenticado = False

    DIAM_DB = obtener_diametros()
    CLI_DB = obtener_clientes()
    VALOR_IVA = obtener_iva()

    if menu == OP_RESUMEN:
        st.header("📊 Estado Actual del Inventario")
        st.info("Aquí aparecerá el resumen de tubos disponibles próximamente.")

    elif menu == OP_PROD:
        st.header("🧱 Registro de Producción")
        with st.form("f_prod"):
            c1, c2, c3 = st.columns(3)
            f_p = c1.date_input("Fecha", obtener_fecha_ecuador())
            d_p = c2.selectbox("Tubo (Medida y Tipo)", DIAM_DB)
            n_p = c3.number_input("Cantidad", min_value=1, step=1, value=None, placeholder="Escriba cantidad...")
            if st.form_submit_button("Guardar Fabricación", type="primary"):
                if d_p != "Seleccione..." and n_p:
                    conn = get_connection(); conn.execute("INSERT INTO produccion (fecha, diametro, cantidad) VALUES (?,?,?)", (f_p.strftime("%Y-%m-%d"), d_p, n_p)); conn.commit(); conn.close()
                    st.success("✅ Datos guardados"); time.sleep(1); st.rerun()
                else: st.error("Complete los campos obligatorios.")

    elif menu == OP_PEDIDOS:
        st.header("📝 Registro de Pedidos")
        with st.form("f_ped"):
            c1, c2 = st.columns(2)
            f_v = c1.date_input("Fecha", obtener_fecha_ecuador())
            cl_v = c2.selectbox("Cliente", CLI_DB)
            c3, c4 = st.columns(2)
            di_v = c3.selectbox("Tubo", DIAM_DB)
            ca_v = c4.number_input("Cantidad Solicitada", min_value=1, step=1, value=None, placeholder="Escriba cantidad...")
            ob = st.text_area("Notas del Pedido")
            if st.form_submit_button("Crear Pedido", type="primary"):
                if di_v != "Seleccione..." and cl_v != "Seleccione Cliente..." and ca_v:
                    conn = get_connection(); conn.execute("INSERT INTO pedidos (fecha, cliente, diametro, cantidad_total, estado, observaciones) VALUES (?,?,?,?,?,?)", (f_v.strftime("%Y-%m-%d"), cl_v, di_v, ca_v, "Pendiente", ob)); conn.commit(); conn.close()
                    st.success("✅ Pedido registrado"); time.sleep(1); st.rerun()
                else: st.error("Complete los campos obligatorios.")

    elif menu == OP_DESPACHOS:
        st.header("🚚 Control de Entregas")
        st.info("Módulo para despachar tubos próximamente.")

    elif menu == OP_CONFIG:
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
            t1, t2, t3 = st.tabs(["📏 Diámetros y Precios", "👥 Clientes", "💰 Impuestos"])
            
            with t1:
                conn = get_connection()
                df_d = pd.read_sql("SELECT id, medida as Medida, tipo as Tipo, precio as [Valor Unitario] FROM diametros", conn)
                if not df_d.empty:
                    # Ordenar numéricamente antes de mostrar
                    df_d['num_sort'] = df_d['Medida'].str.extract('(\d+)').astype(float)
                    df_d = df_d.sort_values('num_sort')
                    
                    df_d['Precio más IVA'] = df_d['Valor Unitario'] * (1 + (VALOR_IVA / 100))
                    df_v = df_d.copy()
                    df_v['Valor Unitario'] = df_v['Valor Unitario'].apply(lambda x: f"${x:.2f}")
                    df_v['Precio más IVA'] = df_v['Precio más IVA'].apply(lambda x: f"${x:.2f}")
                    st.write(f"**Catálogo de Productos (Ordenado por diámetro - IVA: {VALOR_IVA}%)**")
                    st.dataframe(df_v.drop(columns=['id', 'num_sort']), use_container_width=True, hide_index=True)
                
                c_a, c_e, c_b = st.columns(3)
                with c_a:
                    with st.form("a_d", clear_on_submit=True):
                        st.write("**Nuevo Producto**")
                        n_m, n_t = st.text_input("Medida"), st.text_input("Tipo")
                        n_pr = st.number_input("Valor Unitario", min_value=0.0, value=None, placeholder="0.00")
                        if st.form_submit_button("Guardar"):
                            if n_m and n_pr is not None: 
                                conn.execute("INSERT INTO diametros (medida, tipo, precio) VALUES (?,?,?)", (n_m, n_t, n_pr)); conn.commit(); st.rerun()
                with c_e:
                    if not df_d.empty:
                        with st.form("e_d"):
                            st.write("**Editar Producto**")
                            # El menú de edición ahora también sale ordenado
                            opciones_ed = df_d['Medida'].tolist()
                            sel = st.selectbox("Elegir Medida", opciones_ed)
                            new_m, new_t = st.text_input("Nuevo Nombre Medida"), st.text_input("Nuevo Tipo")
                            new_p = st.number_input("Nuevo Valor Unitario", min_value=0.0, value=None, placeholder="0.00")
                            if st.form_submit_button("Actualizar"):
                                if new_m and new_p is not None:
                                    conn.execute("UPDATE diametros SET medida=?, tipo=?, precio=? WHERE medida=?", (new_m, new_t, new_p, sel))
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
                                    conn.commit(); st.rerun()
                with c3:
                    if not df_c.empty:
                        with st.form("b_c"):
                            st.write("**Borrar**")
                            del_c = st.selectbox("Eliminar Cliente", df_c['Nombre'].tolist())
                            if st.form_submit_button("Borrar"):
                                conn.execute("DELETE FROM clientes WHERE nombre=?", (del_c,)); conn.commit(); st.rerun()
                conn.close()

            with t3:
                st.write("**Configuración de IVA**")
                st.info(f"IVA actual: **{VALOR_IVA}%**")
                with st.form("f_iva"):
                    n_iva = st.number_input("Nuevo IVA (%)", min_value=0.0, max_value=100.0, value=float(VALOR_IVA), step=1.0)
                    if st.form_submit_button("Actualizar"):
                        conn = get_connection()
                        conn.execute("UPDATE configuracion SET valor=? WHERE parametro='iva'", (n_iva,))
                        conn.commit(); conn.close(); st.success("IVA actualizado"); time.sleep(1); st.rerun()