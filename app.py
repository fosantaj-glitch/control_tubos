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

# --- 2. DISEÑO VISUAL PROFESIONAL (CSS PERSONALIZADO) ---
# He aplicado un degradado diagonal de fondo para toda la página (izquierda->derecha i abajo)
# Y un estilo oscuro metálico para el menú lateral basado en el logo.
st.markdown(
    """
    <style>
    /* Degradado Diagonal para toda la página */
    .stApp {
        background-image: linear-gradient(135deg, #f8f9fa 0%, #e1e7ec 50%, #bac2cb 100%);
        background-attachment: fixed;
    }

    /* Estilo del Sidebar (Menú Lateral) */
    [data-testid="stSidebar"] {
        background-image: linear-gradient(180deg, #2c3e50 0%, #1a2533 100%);
        color: white !important;
    }
    
    /* Asegurar que los textos del sidebar sean blancos */
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
    [data-testid="stSidebar"] .stAlert p {
        color: white !important;
    }

    /* Enmascaramiento circular para el logo rectangular proporcionado */
    [data-testid="stSidebar"] img {
        border-radius: 50%;
        border: 4px solid #f8f9fa60;
        margin-top: 1rem;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }
    
    /* Estilos del menú radio sidebar */
    [data-testid="stSidebarNav"] li {
        margin-left: 0.5rem;
    }
    div[role="radiogroup"] label {
        color: white !important;
        font-weight: 500;
    }
    div[role="radiogroup"] label:hover {
        background-color: #f8f9fa20;
        border-radius: 5px;
    }

    /* Estilo de los formularios y tablas principales */
    [data-testid="stHeader"], [data-testid="stForm"] {
        background-color: white;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin-bottom: 1rem;
    }
    
    /* Encabezados oscuros para contraste */
    [data-testid="stHeader"] h1 {
        color: #1a2533;
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

def login():
    if not st.session_state.autenticado:
        c_p1, c_p2, c_p3 = st.columns([1, 2, 1])
        with c_p2:
            st.markdown("<br>", unsafe_allow_html=True)
            try:
                # Intenta cargar el logo centrado si existe
                st.image("logo.png", width=300, use_column_width=True)
            except: pass
            
            st.title("🏭 Sistema Control Inventario GUILLÉN")
            st.subheader("Acceso Restringido")
            clave = st.text_input("Ingrese la clave de acceso", type="password", key="login_key")
            
            if st.button("Entrar", type="primary", use_container_width=True):
                if clave == "Tubos2026":
                    st.session_state.autenticado = True
                    st.rerun() 
                else:
                    st.error("❌ Clave incorrecta. Inténtelo de nuevo.")
        return False
    return True

# --- 4. FUNCIONES DE BASE DE DATOS Y RESPALDO ---
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
        st.toast("✅ Respaldo total completado en la nube.")
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

# --- 5. FLUJO PRINCIPAL ---
if login():
    st.sidebar.markdown("<br>", unsafe_allow_html=True) # Espacio arriba
    
    # Intenta cargar el logo en el sidebar. Requiere subir logo.png a GitHub
    if os.path.exists("logo.png"):
        st.sidebar.image("logo.png")
    else:
        st.sidebar.warning("⚠️ Sube archivo logo.png para personalizar.")
        st.sidebar.title("🏭 GUILLÉN TUBOS")
    
    if st.sidebar.button("Cerrar Sesión", use_container_width=True):
        st.session_state.autenticado = False
        st.session_state.config_autenticado = False
        st.rerun()
    st.sidebar.divider()
    
    menu = st.sidebar.radio("Navegación", ["📊 Resumen de Patio", "🧱 Fabricación Diaria", "📝 Pedidos y Ventas", "🚚 Despachos", "⚙️ Configuración"])

    if menu != "Configuración":
        st.session_state.config_autenticado = False

    DIAMETROS_DB = obtener_diametros()
    CLIENTES_DB = obtener_clientes()

    if menu == "📊 Resumen de Patio":
        st.header("📊 Patio de Tubos GUILLÉN - Inventario Hoy")
        st.info("Próximamente: Indicadores de stock en tiempo real.")

    elif menu == "🧱 Fabricación Diaria":
        st.header("🧱 Registrar Producción de Fábrica")
        with st.form("form_produccion"):
            c1, c2, c3 = st.columns(3)
            fecha_p = c1.date_input("Fecha de Fabricación", obtener_fecha_ecuador())
            diam_p = c2.selectbox("Diámetro del Tubo", DIAMETROS_DB)
            cant_p = c3.number_input("Cantidad Fabricada", min_value=1, step=1)
            if st.form_submit_button("Guardar Producción", type="primary"):
                if diam_p != "Seleccione...":
                    conn = get_connection(); conn.execute("INSERT INTO produccion (fecha, diametro, cantidad) VALUES (?,?,?)", (fecha_p.strftime("%Y-%m-%d"), diam_p, cant_p)); conn.commit(); conn.close()
                    st.success("✅ Guardado"); time.sleep(1); st.rerun()

    elif menu == "📝 Pedidos y Ventas":
        st.header("📝 Nuevo Pedido de Cliente")
        with st.form("form_pedidos"):
            c1, c2 = st.columns(2)
            fecha_v = c1.date_input("Fecha del Pedido", obtener_fecha_ecuador())
            cli_v = c2.selectbox("Cliente", CLIENTES_DB)
            c3, c4 = st.columns(2)
            diam_v = c3.selectbox("Diámetro", DIAMETROS_DB)
            cant_v = c4.number_input("Cantidad Total Comprada", min_value=1, step=1)
            obs = st.text_area("Información adicional")
            if st.form_submit_button("Crear Pedido", type="primary"):
                if diam_v != "Seleccione..." and cli_v != "Seleccione Cliente...":
                    conn = get_connection(); conn.execute("INSERT INTO pedidos (fecha, cliente, diametro, cantidad_total, estado, observaciones) VALUES (?,?,?,?,?,?)", (fecha_v.strftime("%Y-%m-%d"), cli_v, diam_v, cant_v, "Pendiente", obs)); conn.commit(); conn.close()
                    st.success("✅ Pedido Creado"); time.sleep(1); st.rerun()

    elif menu == "🚚 Despachos":
        st.header("🚚 Registrar Salida (Carga de Camiones)")
        st.info("Próximamente: Módulo de despachos parciales.")

    elif menu == "⚙️ Configuración":
        st.header("⚙️ Configuración y Administración de Datos Base")
        
        # Validación de clave secundaria para administración
        if not st.session_state.config_autenticado:
            st.warning("⚠️ Esta área requiere permisos de administrador.")
            with st.form("auth_admin"):
                clave_adm = st.text_input("Ingrese la clave de administrador (Misma que al ingreso)", type="password")
                if st.form_submit_button("Desbloquear Configuración", type="primary"):
                    if clave_adm == "Tubos2026":
                        st.session_state.config_autenticado = True; st.rerun()
                    else: st.error("Clave incorrecta")
        else:
            tab_diam, tab_cli = st.tabs(["📏 Medidas y Precios", "👥 Directorio de Clientes"])
            
            with tab_diam:
                conn = get_connection()
                df_d = pd.read_sql("SELECT id, medida as Medida, precio as Precio FROM diametros ORDER BY id ASC", conn)
                
                # Diseño de tres columnas: Lista, Agregar/Corregir, Borrar
                c_ta, c_form, c_del = st.columns([2, 1.5, 1])
                
                with c_ta:
                    st.markdown("**Lista Actual**")
                    if not df_d.empty:
                        df_d_disp = df_d.copy()
                        df_d_disp['Precio'] = df_d_disp['Precio'].apply(lambda x: f"${x:.2f}")
                        st.dataframe(df_d_disp.drop(columns=['id']), use_container_width=True, hide_index=True)
                    else:
                        st.info("No hay medidas registradas.")
                
                with c_form:
                    # Sistema unificado para agregar o editar
                    with st.form("add_edit_diam", clear_on_submit=True):
                        if not df_d.empty:
                            st.markdown("**Añadir o Corregir Medida**")
                            d_disp = pd.read_sql("SELECT medida FROM diametros ORDER BY id ASC", conn)['medida'].tolist()
                            opc_edit = ["-- NUEVO --"] + d_disp
                            sel_d = st.selectbox("Medida a gestionar", opc_edit)
                            
                            # Carga datos si se selecciona una existente
                            pre_m = sel_d if sel_d != "-- NUEVO --" else ""
                            pre_p = 0.0
                            if sel_d != "-- NUEVO --":
                                pre_p = df_d[df_d['Medida'] == sel_d]['Precio'].values[0]
                                
                            f_med = st.text_input("Medida / Diámetro Correcto", value=pre_m)
                            f_pre = st.number_input("Precio ($) Correcto", value=float(pre_p), min_value=0.0)
                            
                            if st.form_submit_button("Guardar Cambios", type="primary"):
                                if f_med:
                                    if sel_d == "-- NUEVO --":
                                        # Agregar
                                        conn.execute("INSERT INTO diametros (medida, precio) VALUES (?,?)", (f_med.strip(), f_pre))
                                        st.success("Guardado")
                                    else:
                                        # Actualizar base + historial de movimientos (integridad de datos)
                                        conn.execute("UPDATE diametros SET medida=?, precio=? WHERE medida=?", (f_med.strip(), f_pre, sel_d))
                                        conn.execute("UPDATE produccion SET diametro=? WHERE diametro=?", (f_med.strip(), sel_d))
                                        conn.execute("UPDATE pedidos SET diametro=? WHERE diametro=?", (f_med.strip(), sel_d))
                                        st.success("Actualizado")
                                    conn.commit(); time.sleep(0.5); st.rerun()
                                else:
                                    st.error("Nombre de medida es obligatorio.")
                        else:
                            # Caso inicial si está vacía
                            st.markdown("**Agregar Primera Medida**")
                            f_med = st.text_input("Diámetro (Ej: 80 cm)")
                            f_pre = st.number_input("Precio ($)", min_value=0.0)
                            if st.form_submit_button("Guardar"):
                                if f_med:
                                    conn.execute("INSERT INTO diametros (medida, precio) VALUES (?,?)", (f_med.strip(), f_pre))
                                    conn.commit(); st.rerun()

                with c_del:
                    # Columna exclusiva para borrado seguro
                    if not df_d.empty:
                        with st.form("del_d"):
                            st.markdown("**Sistema de Borrado**")
                            d_del = st.selectbox("Medida a eliminar permanentemente", list(dict(zip(df_d['Medida'], df_d['id'])).keys()))
                            # Advertencia de integridad
                            st.caption("⚠️ Ojo: El borrado NO eliminará registros de patio antiguos para no perder historial.")
                            if st.form_submit_button("BORRAR MEDIDA", type="secondary"):
                                conn.execute("DELETE FROM diametros WHERE medida=?", (d_del,))
                                conn.commit(); time.sleep(0.5); st.rerun()
                conn.close()

            with tab_cli:
                conn = get_connection()
                df_c = pd.read_sql("SELECT id, nombre as Cliente, telefono as Teléfono FROM clientes ORDER BY nombre ASC", conn)
                
                # Diseño unificado de tres columnas
                c_ta_c, c_form_c, c_del_c = st.columns([2, 1.5, 1])
                
                with c_ta_c:
                    st.markdown("**Directorio Histórico**")
                    if not df_c.empty:
                        st.dataframe(df_c.drop(columns=['id']), use_container_width=True, hide_index=True)
                    else:
                        st.info("El directorio está vacío.")
                
                with c_form_c:
                    # Sistema unificado para agregar o editar clientes
                    with st.form("add_edit_cli", clear_on_submit=True):
                        if not df_c.empty:
                            st.markdown("**Añadir o Corregir Cliente**")
                            c_disp = pd.read_sql("SELECT nombre FROM clientes ORDER BY nombre ASC", conn)['nombre'].tolist()
                            opc_edit_c = ["-- NUEVO --"] + c_disp
                            sel_c = st.selectbox("Cliente a gestionar", opc_edit_c)
                            
                            pre_c = sel_c if sel_c != "-- NUEVO --" else ""
                            pre_t = ""
                            if sel_c != "-- NUEVO --":
                                pre_t = df_c[df_c['Cliente'] == sel_c]['Teléfono'].values[0]
                                
                            f_c = st.text_input("Nombre o Empresa Correcta", value=pre_c)
                            f_t = st.text_input("Teléfono Correcto", value=pre_t)
                            
                            if st.form_submit_button("Guardar Cambios", type="primary"):
                                if f_c:
                                    if sel_c == "-- NUEVO --":
                                        conn.execute("INSERT INTO clientes (nombre, telefono) VALUES (?,?)", (f_c.strip(), f_t.strip()))
                                        st.success("Guardado")
                                    else:
                                        # Actualizar base + historial de pedidos antigua (integridad)
                                        conn.execute("UPDATE clientes SET nombre=?, telefono=? WHERE nombre=?", (f_c.strip(), f_t.strip(), sel_c))
                                        conn.execute("UPDATE pedidos SET cliente=? WHERE cliente=?", (f_c.strip(), sel_c))
                                        st.success("Actualizado")
                                    conn.commit(); time.sleep(0.5); st.rerun()
                        else:
                            st.markdown("**Registrar Primer Cliente**")
                            f_c = st.text_input("Nombre / Empresa")
                            f_t = st.text_input("Teléfono")
                            if st.form_submit_button("Registrar"):
                                if f_c:
                                    conn.execute("INSERT INTO clientes (nombre, telefono) VALUES (?,?)", (f_c.strip(), f_t.strip()))
                                    conn.commit(); st.rerun()
                
                with c_del_c:
                    if not df_c.empty:
                        with st.form("del_c"):
                            st.markdown("**Sistema de Borrado**")
                            c_del_s = st.selectbox("Cliente a eliminar", list(dict(zip(df_c['Cliente'], df_c['id'])).keys()))
                            st.caption("⚠️ Ojo: Solo lo quita de la lista de configuración, NO de pedidos viejos.")
                            if st.form_submit_button("BORRAR CLIENTE", type="secondary"):
                                conn.execute("DELETE FROM clientes WHERE nombre=?", (c_del_s,))
                                conn.commit(); time.sleep(0.5); st.rerun()
                conn.close()