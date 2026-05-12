import streamlit as st
import pandas as pd
import sqlite3
import requests
from datetime import datetime, timezone, timedelta
import time
import math

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Control de Tubos - GUILLÉN", page_icon="🏭", layout="wide", initial_sidebar_state="expanded")

# --- 2. DISEÑO VISUAL ---
st.markdown(
    """
    <style>
    .stApp {
        background: linear-gradient(135deg, #ced4da 0%, #e9ecef 40%, #ffffff 100%);
        background-attachment: fixed;
    }
    [data-testid="stSidebar"] {
        background-color: #212529 !important;
    }
    [data-testid="stSidebar"] p, [data-testid="stSidebar"] span, [data-testid="stSidebar"] label, 
    [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3,
    div[role="radiogroup"] label { color: #ffffff !important; }
    
    section[data-testid="stSidebar"] .stButton button {
        background-color: #ffffff !important;
        border: 2px solid #adb5bd !important;
        border-radius: 8px !important;
        padding: 10px !important;
        width: 100% !important;
        display: block !important;
    }
    section[data-testid="stSidebar"] .stButton button p { color: #000000 !important; font-weight: bold !important; }
    section[data-testid="stSidebar"] .stButton button:hover { background-color: #e9ecef !important; border-color: #ffffff !important; }
    
    [data-testid="stHeader"], .stForm, .stDataFrame {
        background-color: white; border-radius: 12px; padding: 20px; box-shadow: 5px 5px 15px rgba(0,0,0,0.05);
    }
    .titulo-seccion {
        background-color: #f1f3f5; color: #5c636a; padding: 6px 15px; border-radius: 4px;
        margin-top: 25px; margin-bottom: 10px; text-align: center; font-weight: 600;
        font-size: 1.05em; text-transform: uppercase; letter-spacing: 2px; border-bottom: 2px solid #8c9296;
    }
    </style>
    """, unsafe_allow_html=True
)

# NUEVA DIRECCIÓN PROPORCIONADA
URL_GOOGLE = "https://script.google.com/macros/s/AKfycbwoL0M4LCT2s8oAt362Jkb21lKvJM-HmGXErlrH3DQ3WE6GMypfaJO6_xfW1R-U3VS_/exec"

# --- 3. SEGURIDAD Y ESTADOS ---
if "autenticado" not in st.session_state: st.session_state.autenticado = False
if "config_autenticado" not in st.session_state: st.session_state.config_autenticado = False
if "datos_cargados" not in st.session_state: st.session_state.datos_cargados = False

def login():
    if not st.session_state.autenticado:
        c1, c2, c3 = st.columns([1, 2, 1])
        with c2:
            st.markdown("<br><br>", unsafe_allow_html=True)
            try: st.image("logo.jpg", use_container_width=True)
            except: pass
            st.title("🏭 Inventario GUILLÉN")
            st.subheader("Acceso al Sistema")
            clave = st.text_input("Contraseña", type="password")
            if st.button("Ingresar", type="primary", use_container_width=True):
                if clave == "Tubos2026":
                    st.session_state.autenticado = True
                    st.rerun() 
                else: st.error("❌ Clave incorrecta")
        return False
    return True

# --- 4. BASE DE DATOS Y CONEXIÓN A GOOGLE ---
def obtener_fecha_ecuador():
    return datetime.now(timezone(timedelta(hours=-5))).date()

def get_connection():
    return sqlite3.connect('control_tubos_db.db', check_same_thread=False)

def init_db():
    conn = get_connection()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS produccion (id INTEGER PRIMARY KEY AUTOINCREMENT, fecha TEXT, diametro TEXT, cantidad INTEGER)''')
    c.execute('''CREATE TABLE IF NOT EXISTS pedidos (id INTEGER PRIMARY KEY AUTOINCREMENT, fecha TEXT, cliente TEXT, diametro TEXT, cantidad_total INTEGER, estado TEXT, observaciones TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS entregas (id INTEGER PRIMARY KEY AUTOINCREMENT, pedido_id INTEGER, fecha TEXT, cantidad_entregada INTEGER, FOREIGN KEY(pedido_id) REFERENCES pedidos(id))''')
    c.execute('''CREATE TABLE IF NOT EXISTS diametros (id INTEGER PRIMARY KEY AUTOINCREMENT, medida TEXT, tipo TEXT, seccion TEXT, precio REAL)''')
    try: c.execute("ALTER TABLE diametros ADD COLUMN seccion TEXT")
    except: pass
    c.execute("UPDATE diametros SET seccion = 'SIN ARMADURA' WHERE seccion IS NULL OR seccion = ''")
    c.execute('''CREATE TABLE IF NOT EXISTS clientes (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, telefono TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS configuracion (id INTEGER PRIMARY KEY, parametro TEXT, valor REAL)''')
    if conn.execute("SELECT COUNT(*) FROM configuracion WHERE parametro='iva'").fetchone()[0] == 0:
        conn.execute("INSERT INTO configuracion (parametro, valor) VALUES ('iva', 15.0)")
    conn.commit(); conn.close()

init_db()

def descargar_datos():
    try:
        response = requests.post(URL_GOOGLE, json={"accion": "leer"}, timeout=30)
        try:
            data = response.json()
        except ValueError:
            return False, "Google denegó el acceso. Verifica que la URL tenga permisos de 'Cualquiera'."

        if response.status_code == 200:
            if data.get("resultado") == "éxito":
                tablas = data.get("datos", {})
                conn = get_connection()
                mapeo = [("Produccion", "produccion"), ("Pedidos", "pedidos"), ("Entregas", "entregas"), 
                         ("Diametros", "diametros"), ("Clientes", "clientes"), ("Configuracion", "configuracion")]
                
                for hoja, tabla_db in mapeo:
                    if hoja in tablas and len(tablas[hoja]) > 1:
                        headers = tablas[hoja][0]
                        rows = tablas[hoja][1:]
                        df = pd.DataFrame(rows, columns=headers)
                        df = df.replace(r'^\s*$', None, regex=True)
                        conn.execute(f"DELETE FROM {tabla_db}")
                        df.to_sql(tabla_db, conn, if_exists='append', index=False)
                        
                conn.commit(); conn.close()
                return True, "Datos cargados correctamente"
            else:
                return False, data.get("detalle", "Error en el script de Google.")
        return False, f"Error HTTP {response.status_code}"
    except Exception as e:
        return False, str(e)

def subir_datos():
    try:
        conn = get_connection()
        payload = {"accion": "sobreescribir"}
        tablas = {
            "Produccion": "SELECT id, fecha, diametro, cantidad FROM produccion",
            "Pedidos": "SELECT id, fecha, cliente, diametro, cantidad_total, estado, observaciones FROM pedidos",
            "Entregas": "SELECT id, pedido_id, fecha, cantidad_entregada FROM entregas",
            "Diametros": "SELECT id, medida, tipo, seccion, precio FROM diametros",
            "Clientes": "SELECT id, nombre, telefono FROM clientes",
            "Configuracion": "SELECT id, parametro, valor FROM configuracion"
        }
        for nombre, query in tablas.items():
            df = pd.read_sql(query, conn).fillna("")
            payload[nombre] = [df.columns.tolist()] + df.values.tolist()
        conn.close()
        response = requests.post(URL_GOOGLE, json=payload, timeout=30)
        return response.status_code == 200
    except: return False

# --- VARIABLES GLOBALES ---
SECCIONES = ["SIN ARMADURA", "HORMIGON ARMADO", "CON ESPIGA", "TUBERIA CLASE II", "TAPAS PEATONALES"]

def obtener_iva():
    conn = get_connection()
    res = conn.execute("SELECT valor FROM configuracion WHERE parametro='iva'").fetchone()
    conn.close()
    return res[0] if res else 15.0

def obtener_diametros():
    conn = get_connection()
    df = pd.read_sql("SELECT medida, seccion FROM diametros", conn)
    conn.close()
    if not df.empty:
        df['num'] = df['medida'].str.extract('(\d+)').astype(float)
        df = df.sort_values('num', ascending=True)
        return ["Seleccione..."] + [f"{r['medida']} ({r['seccion']})" for _, r in df.iterrows()]
    return ["Seleccione..."]

def obtener_clientes():
    conn = get_connection()
    df = pd.read_sql("SELECT nombre FROM clientes ORDER BY nombre ASC", conn)
    conn.close()
    return ["Seleccione Cliente..."] + df['nombre'].tolist()

# --- 5. INTERFAZ PRINCIPAL ---
if login():
    if not st.session_state.datos_cargados:
        with st.spinner("📥 Sincronizando con TUBOS_DB..."):
            exito, msj = descargar_datos()
            st.session_state.datos_cargados = True
            if exito:
                st.success("✅ " + msj)
                time.sleep(1)
                st.rerun()
            else:
                st.error(f"⚠️ {msj}")

    st.sidebar.markdown("<br>", unsafe_allow_html=True)
    try: st.sidebar.image("logo.jpg", use_container_width=True)
    except: st.sidebar.title("GUILLÉN")

    st.sidebar.markdown("### ☁️ Nube")
    if st.sidebar.button("💾 Respaldar Datos", type="primary", use_container_width=True):
        with st.spinner("Subiendo a Drive..."):
            if subir_datos(): st.sidebar.success("✅ Guardado con éxito")
            else: st.sidebar.error("❌ Error al guardar")
                
    if st.sidebar.button("🚪 Cerrar Sesión", use_container_width=True):
        st.session_state.autenticado = False
        st.session_state.config_autenticado = False
        st.rerun()

    st.sidebar.divider()
    MENU = ["📊 Resumen de Patio", "🧱 Fabricación Diaria", "📝 Pedidos y Ventas", "🚚 Despachos", "⚙️ Configuración"]
    opcion = st.sidebar.radio("MENÚ PRINCIPAL", MENU)

    if opcion != "⚙️ Configuración": st.session_state.config_autenticado = False

    DIAM_DB = obtener_diametros()
    CLI_DB = obtener_clientes()
    VALOR_IVA = obtener_iva()

    if opcion == MENU[1]:
        st.header("🧱 Registro de Fabricación")
        with st.form("f_prod"):
            c1, c2, c3 = st.columns(3)
            f_p = c1.date_input("Fecha", obtener_fecha_ecuador())
            d_p = c2.selectbox("Tubo", DIAM_DB)
            n_p = c3.number_input("Cantidad", min_value=1, step=1, value=None, placeholder="Escriba...")
            if st.form_submit_button("Guardar", type="primary"):
                if d_p != "Seleccione..." and n_p:
                    conn = get_connection(); conn.execute("INSERT INTO produccion (fecha, diametro, cantidad) VALUES (?,?,?)", (f_p.strftime("%Y-%m-%d"), d_p, n_p)); conn.commit(); conn.close()
                    st.success("✅ Guardado"); time.sleep(1); st.rerun()

    elif opcion == MENU[2]:
        st.header("📝 Registro de Pedidos")
        with st.form("f_ped"):
            c1, c2 = st.columns(2)
            f_v = c1.date_input("Fecha", obtener_fecha_ecuador())
            cl_v = c2.selectbox("Cliente", CLI_DB)
            c3, c4 = st.columns(2)
            di_v = c3.selectbox("Tubo", DIAM_DB)
            ca_v = c4.number_input("Cantidad", min_value=1, step=1, value=None, placeholder="Escriba...")
            if st.form_submit_button("Registrar", type="primary"):
                if di_v != "Seleccione..." and cl_v != "Seleccione Cliente..." and ca_v:
                    conn = get_connection(); conn.execute("INSERT INTO pedidos (fecha, cliente, diametro, cantidad_total, estado, observaciones) VALUES (?,?,?,?,?,?)", (f_v.strftime("%Y-%m-%d"), cl_v, di_v, ca_v, "Pendiente", "")); conn.commit(); conn.close()
                    st.success("✅ Registrado"); time.sleep(1); st.rerun()

    elif opcion == MENU[4]:
        st.header("⚙️ Administración")
        if not st.session_state.config_autenticado:
            with st.form("admin_lock"):
                cl_adm = st.text_input("Clave", type="password")
                if st.form_submit_button("Desbloquear"):
                    if cl_adm == "Tubos2026": st.session_state.config_autenticado = True; st.rerun()
                    else: st.error("❌ Incorrecta")
        else:
            t1, t2, t3 = st.tabs(["📏 Catálogo", "👥 Clientes", "💰 IVA"])
            with t1:
                conn = get_connection()
                df_base = pd.read_sql("SELECT medida, tipo, seccion, precio FROM diametros", conn)
                if not df_base.empty:
                    df_base['num'] = df_base['medida'].str.extract('(\d+)').astype(float)
                    df_base['Pulgadas'] = (df_base['num'] / 25.4).apply(math.ceil).astype(str) + '"'
                    df_base['Total'] = df_base['precio'] * (1 + (VALOR_IVA / 100))
                    for sec in SECCIONES:
                        st.markdown(f'<div class="titulo-seccion">{sec}</div>', unsafe_allow_html=True)
                        df_sec = df_base[df_base['seccion'] == sec].sort_values('num', ascending=True)
                        if not df_sec.empty:
                            df_mostrar = df_sec[['medida', 'Pulgadas', 'tipo', 'precio', 'Total']].rename(columns={'medida': 'Medida (mm)', 'precio': 'Unitario', 'Total': 'Con IVA'})
                            df_mostrar['Unitario'] = df_mostrar['Unitario'].apply(lambda x: f"${x:.2f}")
                            df_mostrar['Con IVA'] = df_mostrar['Con IVA'].apply(lambda x: f"${x:.2f}")
                            st.table(df_mostrar.assign(index='').set_index('index'))
                st.divider()
                c_a, c_e, c_b = st.columns(3)
                with c_a:
                    with st.form("a_d", clear_on_submit=True):
                        st.write("Nuevo")
                        n_sec, n_m, n_t = st.selectbox("Sección", SECCIONES), st.text_input("Medida"), st.text_input("Tipo")
                        n_p = st.number_input("Precio", min_value=0.0, format="%.2f")
                        if st.form_submit_button("Guardar"):
                            conn.execute("INSERT INTO diametros (medida, tipo, seccion, precio) VALUES (?,?,?,?)", (n_m, n_t, n_sec, n_p))
                            conn.commit(); st.rerun()
                with c_e:
                    if not df_base.empty:
                        with st.form("e_d"):
                            st.write("Editar")
                            op_ed = {f"{r['medida']} ({r['seccion']})": r['medida'] for _, r in df_base.iterrows()}
                            sel_m = op_ed[st.selectbox("Elegir", list(op_ed.keys()))]
                            ns, nm, nt = st.selectbox("Sección", SECCIONES), st.text_input("Nuevo Nombre"), st.text_input("Nuevo Tipo")
                            np = st.number_input("Nuevo Precio", min_value=0.0, format="%.2f")
                            if st.form_submit_button("Actualizar"):
                                conn.execute("UPDATE diametros SET seccion=?, medida=?, tipo=?, precio=? WHERE medida=?", (ns, nm, nt, np, sel_m))
                                conn.commit(); st.rerun()
                with c_b:
                    if not df_base.empty:
                        with st.form("b_d"):
                            st.write("Borrar")
                            del_s = st.selectbox("Eliminar", df_base['medida'].unique())
                            if st.form_submit_button("Borrar"):
                                conn.execute("DELETE FROM diametros WHERE medida=?", (del_s,))
                                conn.commit(); st.rerun()
                conn.close()
            with t3:
                st.write("IVA")
                with st.form("f_iva"):
                    n_iva = st.number_input("% IVA", value=float(VALOR_IVA), format="%.2f")
                    if st.form_submit_button("Actualizar"):
                        conn = get_connection(); conn.execute("UPDATE configuracion SET valor=? WHERE parametro='iva'", (n_iva,)); conn.commit(); conn.close(); st.rerun()