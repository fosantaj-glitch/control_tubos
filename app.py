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
    [data-testid="stSidebar"] { background-color: #212529 !important; }
    [data-testid="stSidebar"] p, [data-testid="stSidebar"] span, [data-testid="stSidebar"] label, 
    [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3,
    div[role="radiogroup"] label { color: #ffffff !important; }
    
    section[data-testid="stSidebar"] .stButton button {
        background-color: #ffffff !important;
        border: 2px solid #adb5bd !important;
        border-radius: 8px !important;
        padding: 10px !important;
        width: 100% !important;
    }
    section[data-testid="stSidebar"] .stButton button p { color: #000000 !important; font-weight: bold !important; }
    
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

# TU URL ACTUALIZADA
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

# --- 4. BASE DE DATOS Y CONEXIÓN ---
def obtener_fecha_ecuador():
    return datetime.now(timezone(timedelta(hours=-5))).date()

def get_connection():
    return sqlite3.connect('control_tubos_db.db', check_same_thread=False)

def init_db():
    conn = get_connection()
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS produccion (id INTEGER PRIMARY KEY, fecha TEXT, diametro TEXT, cantidad INTEGER)')
    c.execute('CREATE TABLE IF NOT EXISTS pedidos (id INTEGER PRIMARY KEY, fecha TEXT, cliente TEXT, diametro TEXT, cantidad_total INTEGER, estado TEXT, observaciones TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS diametros (id INTEGER PRIMARY KEY, medida TEXT, tipo TEXT, seccion TEXT, precio REAL)')
    c.execute('CREATE TABLE IF NOT EXISTS clientes (id INTEGER PRIMARY KEY, nombre TEXT, telefono TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS configuracion (id INTEGER PRIMARY KEY, parametro TEXT, valor REAL)')
    conn.commit(); conn.close()

init_db()

def descargar_datos():
    try:
        response = requests.post(URL_GOOGLE, json={"accion": "leer"}, timeout=30)
        if response.status_code == 200:
            data = response.json()
            if data.get("resultado") == "éxito":
                tablas = data.get("datos", {})
                conn = get_connection()
                mapeo = [("Produccion", "produccion"), ("Pedidos", "pedidos"), 
                         ("Diametros", "diametros"), ("Clientes", "clientes"), ("Configuracion", "configuracion")]
                for hoja, tabla_db in mapeo:
                    if hoja in tablas and len(tablas[hoja]) > 1:
                        df = pd.DataFrame(tablas[hoja][1:], columns=tablas[hoja][0])
                        df = df.replace(r'^\s*$', None, regex=True)
                        conn.execute(f"DELETE FROM {tabla_db}")
                        df.to_sql(tabla_db, conn, if_exists='append', index=False)
                conn.commit(); conn.close()
                return True
    except: pass
    return False

def subir_datos():
    try:
        conn = get_connection()
        payload = {"accion": "sobreescribir"}
        tablas = {"Produccion": "produccion", "Pedidos": "pedidos", "Diametros": "diametros", "Clientes": "clientes", "Configuracion": "configuracion"}
        for hoja, db in tablas.items():
            df = pd.read_sql(f"SELECT * FROM {db}", conn).fillna("")
            payload[hoja] = [df.columns.tolist()] + df.values.tolist()
        conn.close()
        return requests.post(URL_GOOGLE, json=payload, timeout=30).status_code == 200
    except: return False

# --- 5. INTERFAZ ---
if login():
    if not st.session_state.datos_cargados:
        with st.spinner("📥 Sincronizando TUBOS_DB..."):
            if descargar_datos():
                st.session_state.datos_cargados = True
                st.rerun()

    st.sidebar.markdown("<br>", unsafe_allow_html=True)
    try: st.sidebar.image("logo.jpg", use_container_width=True)
    except: st.sidebar.title("GUILLÉN")

    if st.sidebar.button("💾 Respaldar a Drive"):
        if subir_datos(): st.sidebar.success("✅ Guardado")
        else: st.sidebar.error("❌ Error")
                
    if st.sidebar.button("🚪 Cerrar Sesión"):
        st.session_state.autenticado = False
        st.session_state.datos_cargados = False
        st.rerun()

    st.sidebar.divider()
    menu = ["📊 Resumen de Patio", "🧱 Fabricación", "📝 Pedidos", "🚚 Despachos", "⚙️ Configuración"]
    opcion = st.sidebar.radio("MENÚ", menu)

    conn = get_connection()
    iva = conn.execute("SELECT valor FROM configuracion WHERE parametro='iva'").fetchone()
    VALOR_IVA = iva[0] if iva else 15.0

    if opcion == menu[0]:
        st.header("📊 Stock Real en Patio")
        df_p = pd.read_sql("SELECT diametro, SUM(cantidad) as fab FROM produccion GROUP BY diametro", conn)
        df_v = pd.read_sql("SELECT diametro, SUM(cantidad_total) as ped FROM pedidos GROUP BY diametro", conn)
        
        if not df_p.empty:
            resumen = pd.merge(df_p, df_v, on="diametro", how="left").fillna(0)
            resumen['Stock Disponible'] = resumen['fab'] - resumen['ped']
            resumen.columns = ['Producto / Diámetro', 'Total Fabricado', 'Total Vendido', 'Stock en Patio']
            st.dataframe(resumen, use_container_width=True, hide_index=True)
        else:
            st.warning("No hay datos de fabricación para mostrar.")

    elif opcion == menu[1]:
        st.header("🧱 Fabricación Diaria")
        df_d = pd.read_sql("SELECT medida, seccion FROM diametros ORDER BY medida", conn)
        listado = [f"{r['medida']} ({r['seccion']})" for _, r in df_d.iterrows()]
        with st.form("prod"):
            c1, c2, c3 = st.columns(3)
            f = c1.date_input("Fecha", obtener_fecha_ecuador())
            d = c2.selectbox("Tubo", ["Seleccione..."] + listado)
            n = c3.number_input("Cantidad", min_value=1, step=1)
            if st.form_submit_button("Guardar"):
                if d != "Seleccione...":
                    conn.execute("INSERT INTO produccion (fecha, diametro, cantidad) VALUES (?,?,?)", (str(f), d, n))
                    conn.commit(); st.success("Guardado"); st.rerun()

    elif opcion == menu[2]:
        st.header("📝 Registro de Pedidos")
        df_c = pd.read_sql("SELECT nombre FROM clientes ORDER BY nombre", conn)
        df_d = pd.read_sql("SELECT medida, seccion FROM diametros ORDER BY medida", conn)
        with st.form("ped"):
            c1, c2 = st.columns(2)
            cl = c1.selectbox("Cliente", ["Seleccione..."] + df_c['nombre'].tolist())
            d = c2.selectbox("Tubo", ["Seleccione..."] + [f"{r['medida']} ({r['seccion']})" for _, r in df_d.iterrows()])
            n = st.number_input("Cantidad Solicitada", min_value=1, step=1)
            if st.form_submit_button("Registrar Pedido"):
                if cl != "Seleccione..." and d != "Seleccione...":
                    conn.execute("INSERT INTO pedidos (fecha, cliente, diametro, cantidad_total, estado) VALUES (?,?,?,?,?)", (str(obtener_fecha_ecuador()), cl, d, n, 'Pendiente'))
                    conn.commit(); st.success("Registrado"); st.rerun()

    elif opcion == menu[3]:
        st.header("🚚 Pedidos Pendientes por Despachar")
        pedidos = pd.read_sql("SELECT fecha, cliente, diametro, cantidad_total as Cantidad FROM pedidos WHERE estado='Pendiente'", conn)
        if not pedidos.empty:
            st.table(pedidos)
        else:
            st.info("No hay despachos pendientes.")

    elif opcion == menu[4]:
        st.header("⚙️ Configuración")
        if not st.session_state.config_autenticado:
            with st.form("admin"):
                if st.form_submit_button("Desbloquear con Clave"):
                    st.session_state.config_autenticado = True; st.rerun()
        else:
            t1, t2, t3 = st.tabs(["📏 Catálogo", "👥 Clientes", "💰 IVA"])
            with t1:
                df = pd.read_sql("SELECT * FROM diametros", conn)
                if not df.empty:
                    df['Pulgadas'] = (df['medida'].str.extract('(\d+)').astype(float) / 25.4).apply(math.ceil).astype(str) + '"'
                    for s in ["SIN ARMADURA", "HORMIGON ARMADO", "CON ESPIGA", "TUBERIA CLASE II", "TAPAS PEATONALES"]:
                        st.markdown(f'<div class="titulo-seccion">{s}</div>', unsafe_allow_html=True)
                        dfs = df[df['seccion'] == s]
                        if not dfs.empty: st.table(dfs[['medida', 'Pulgadas', 'tipo', 'precio']])
                with st.form("add"):
                    c1, c2, c3, c4 = st.columns(4)
                    sec = c1.selectbox("Sección", ["SIN ARMADURA", "HORMIGON ARMADO", "CON ESPIGA", "TUBERIA CLASE II", "TAPAS PEATONALES"])
                    med = c2.text_input("Medida (mm)")
                    tip = c3.text_input("Tipo")
                    pre = c4.number_input("Precio", format="%.2f")
                    if st.form_submit_button("Añadir"):
                        conn.execute("INSERT INTO diametros (medida, tipo, seccion, precio) VALUES (?,?,?,?)", (med, tip, sec, pre))
                        conn.commit(); st.rerun()
            with t3:
                n_iva = st.number_input("IVA %", value=float(VALOR_IVA))
                if st.button("Actualizar IVA"):
                    conn.execute("UPDATE configuracion SET valor=? WHERE parametro='iva'", (n_iva,))
                    conn.commit(); st.rerun()
    conn.close()