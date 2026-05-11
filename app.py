import streamlit as st
import pandas as pd
import sqlite3
import requests
from datetime import datetime, date, timezone, timedelta
import time

# --- 1. CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Control de Tubos - Inventario", layout="wide")

URL_GOOGLE = "https://script.google.com/macros/s/AKfycbw2YUNMCJB0fDNZ1jCWFmcgXv5VABsCXvAi6rsUXAVnlsUaQB2kgBvZCuBxEFVMOOL1/exec"

# --- 2. SISTEMA DE SEGURIDAD ---
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False

if "config_autenticado" not in st.session_state:
    st.session_state.config_autenticado = False

def login():
    if not st.session_state.autenticado:
        st.title("🏭 Sistema de Control de Tubos")
        st.subheader("Acceso Restringido")
        clave = st.text_input("Ingrese la clave de acceso", type="password")
        if st.button("Entrar", type="primary"):
            if clave == "Tubos2026":
                st.session_state.autenticado = True
                st.rerun() 
            else:
                st.error("❌ Clave incorrecta. Inténtelo de nuevo.")
        return False
    return True

# --- 3. FUNCIONES DE BASE DE DATOS ---
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
        diametros_iniciales = [("10 cm", 0.0), ("15 cm", 0.0), ("20 cm", 0.0), ("30 cm", 0.0), ("50 cm", 0.0), ("100 cm", 0.0)]
        c.executemany("INSERT INTO diametros (medida, precio) VALUES (?,?)", diametros_iniciales)
    conn.commit()
    conn.close()

init_db()

def enviar_a_google(hoja, fila):
    try: requests.post(URL_GOOGLE, json={"hoja": hoja, "fila": fila}, timeout=15)
    except: pass

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

# --- 4. FLUJO PRINCIPAL ---
if login():
    st.sidebar.title("🏭 Control Tubos")
    if st.sidebar.button("Cerrar Sesión"):
        st.session_state.autenticado = False
        st.session_state.config_autenticado = False
        st.rerun()
    st.sidebar.divider()
    
    menu = st.sidebar.radio("Navegación", ["Resumen de Inventario", "Registro de Producción Diaria", "Gestión de Pedidos y Ventas", "Despachos (Entregas)", "Configuración"])

    if menu != "Configuración":
        st.session_state.config_autenticado = False

    DIAMETROS_DB = obtener_diametros()
    CLIENTES_DB = obtener_clientes()

    if menu == "Resumen de Inventario":
        st.header("📊 Inventario en Tiempo Real")
        st.info("Espacio para indicadores de stock (Próximamente)")

    elif menu == "Registro de Producción Diaria":
        st.header("🧱 Registrar Fabricación")
        with st.form("form_produccion"):
            c1, c2, c3 = st.columns(3)
            fecha_p = c1.date_input("Fecha", obtener_fecha_ecuador())
            diam_p = c2.selectbox("Diámetro", DIAMETROS_DB)
            cant_p = c3.number_input("Cantidad", min_value=1, step=1)
            if st.form_submit_button("Guardar Producción", type="primary"):
                if diam_p != "Seleccione...":
                    conn = get_connection(); conn.execute("INSERT INTO produccion (fecha, diametro, cantidad) VALUES (?,?,?)", (fecha_p.strftime("%Y-%m-%d"), diam_p, cant_p)); conn.commit(); conn.close()
                    st.success("✅ Guardado"); time.sleep(1); st.rerun()

    elif menu == "Gestión de Pedidos y Ventas":
        st.header("📝 Nuevo Pedido / Venta")
        with st.form("form_pedidos"):
            c1, c2 = st.columns(2)
            fecha_v = c1.date_input("Fecha", obtener_fecha_ecuador())
            cli_v = c2.selectbox("Cliente", CLIENTES_DB)
            c3, c4 = st.columns(2)
            diam_v = c3.selectbox("Diámetro", DIAMETROS_DB)
            cant_v = c4.number_input("Cantidad Total", min_value=1, step=1)
            obs = st.text_area("Observaciones")
            if st.form_submit_button("Crear Pedido", type="primary"):
                if diam_v != "Seleccione..." and cli_v != "Seleccione Cliente...":
                    conn = get_connection(); conn.execute("INSERT INTO pedidos (fecha, cliente, diametro, cantidad_total, estado, observaciones) VALUES (?,?,?,?,?,?)", (fecha_v.strftime("%Y-%m-%d"), cli_v, diam_v, cant_v, "Pendiente", obs)); conn.commit(); conn.close()
                    st.success("✅ Pedido Creado"); time.sleep(1); st.rerun()

    elif menu == "Despachos (Entregas)":
        st.header("🚚 Registrar Salida")
        st.info("Módulo de carga de camiones (Próximamente)")

    elif menu == "Configuración":
        st.header("⚙️ Configuración del Sistema")
        if not st.session_state.config_autenticado:
            with st.form("auth_admin"):
                clave_adm = st.text_input("Ingrese clave de administrador", type="password")
                if st.form_submit_button("Desbloquear"):
                    if clave_adm == "Tubos2026":
                        st.session_state.config_autenticado = True; st.rerun()
                    else: st.error("Clave incorrecta")
        else:
            st.success("🔓 Modo Administrador Activo")
            tab_diam, tab_cli = st.tabs(["📏 Medidas y Precios", "👥 Directorio de Clientes"])
            
            with tab_diam:
                conn = get_connection()
                df_d = pd.read_sql("SELECT id, medida as Medida, precio as Precio FROM diametros ORDER BY id ASC", conn)
                st.dataframe(df_d.drop(columns=['id']), use_container_width=True, hide_index=True)
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    with st.form("add_d", clear_on_submit=True):
                        st.markdown("**Agregar**")
                        nm, np = st.text_input("Nueva Medida"), st.number_input("Precio ($)", min_value=0.0)
                        if st.form_submit_button("Guardar"):
                            if nm: conn.execute("INSERT INTO diametros (medida, precio) VALUES (?,?)", (nm, np)); conn.commit(); st.rerun()
                with col2:
                    if not df_d.empty:
                        with st.form("edit_d"):
                            st.markdown("**Corregir**")
                            opc_d = dict(zip(df_d['Medida'], df_d['id']))
                            d_sel = st.selectbox("Seleccione", list(opc_d.keys()))
                            new_m, new_p = st.text_input("Nombre Correcto"), st.number_input("Precio Correcto", min_value=0.0)
                            if st.form_submit_button("Actualizar", type="primary"):
                                if new_m:
                                    conn.execute("UPDATE diametros SET medida=?, precio=? WHERE id=?", (new_m, new_p, opc_d[d_sel]))
                                    conn.execute("UPDATE produccion SET diametro=? WHERE diametro=?", (new_m, d_sel))
                                    conn.execute("UPDATE pedidos SET diametro=? WHERE diametro=?", (new_m, d_sel))
                                    conn.commit(); st.rerun()
                with col3:
                    if not df_d.empty:
                        with st.form("del_d"):
                            st.markdown("**Borrar**")
                            d_del = st.selectbox("Eliminar medida", list(dict(zip(df_d['Medida'], df_d['id'])).keys()))
                            if st.form_submit_button("Eliminar"):
                                conn.execute("DELETE FROM diametros WHERE medida=?", (d_del,)); conn.commit(); st.rerun()
                conn.close()

            with tab_cli:
                conn = get_connection()
                df_c = pd.read_sql("SELECT id, nombre as Cliente, telefono as Teléfono FROM clientes ORDER BY nombre ASC", conn)
                st.dataframe(df_c.drop(columns=['id']), use_container_width=True, hide_index=True)
                
                c1, c2, c3 = st.columns(3)
                with c1:
                    with st.form("add_c", clear_on_submit=True):
                        st.markdown("**Nuevo**")
                        nc, nt = st.text_input("Nombre"), st.text_input("Teléfono")
                        if st.form_submit_button("Registrar"):
                            if nc: conn.execute("INSERT INTO clientes (nombre, telefono) VALUES (?,?)", (nc, nt)); conn.commit(); st.rerun()
                with col2:
                    if not df_c.empty:
                        with st.form("edit_c"):
                            st.markdown("**Corregir**")
                            opc_c = dict(zip(df_c['Cliente'], df_c['id']))
                            c_sel = st.selectbox("Seleccione Cliente", list(opc_c.keys()))
                            new_c, new_t = st.text_input("Nombre Correcto"), st.text_input("Teléfono Correcto")
                            if st.form_submit_button("Actualizar", type="primary"):
                                if new_c:
                                    conn.execute("UPDATE clientes SET nombre=?, telefono=? WHERE id=?", (new_c, new_t, opc_c[c_sel]))
                                    conn.execute("UPDATE pedidos SET cliente=? WHERE cliente=?", (new_c, c_sel))
                                    conn.commit(); st.rerun()
                with col3:
                    if not df_c.empty:
                        with st.form("del_c"):
                            st.markdown("**Borrar**")
                            c_del = st.selectbox("Eliminar cliente", list(dict(zip(df_c['Cliente'], df_c['id'])).keys()))
                            if st.form_submit_button("Borrar"):
                                conn.execute("DELETE FROM clientes WHERE nombre=?", (c_del,)); conn.commit(); st.rerun()
                conn.close()