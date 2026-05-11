Entendido perfectamente. Vamos a aplicar una Doble Verificación de seguridad. Aunque ya estés dentro de la aplicación, al intentar entrar a "Configuración" el sistema te solicitará nuevamente la clave Tubos2026 para desbloquear las opciones de administración de clientes y diámetros.

Aquí tienes el código completo de tu archivo app.py actualizado. Solo tienes que copiarlo y pegarlo íntegramente en GitHub:

Python
import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, timezone, timedelta

# --- 1. CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Control de Tubos - Inventario", layout="wide")

# --- 2. SISTEMA DE SEGURIDAD GENERAL ---
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False

# Estado para la clave secundaria de configuración
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
    # Tablas de Movimientos
    c.execute('''CREATE TABLE IF NOT EXISTS produccion (id INTEGER PRIMARY KEY AUTOINCREMENT, fecha TEXT, diametro TEXT, cantidad INTEGER)''')
    c.execute('''CREATE TABLE IF NOT EXISTS pedidos (id INTEGER PRIMARY KEY AUTOINCREMENT, fecha TEXT, cliente TEXT, diametro TEXT, cantidad_total INTEGER, estado TEXT, observaciones TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS entregas (id INTEGER PRIMARY KEY AUTOINCREMENT, pedido_id INTEGER, fecha TEXT, cantidad_entregada INTEGER, FOREIGN KEY(pedido_id) REFERENCES pedidos(id))''')
    
    # Tablas de Configuración
    c.execute('''CREATE TABLE IF NOT EXISTS diametros (id INTEGER PRIMARY KEY AUTOINCREMENT, medida TEXT, precio REAL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS clientes (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, telefono TEXT)''')
    
    c.execute("SELECT COUNT(*) FROM diametros")
    if c.fetchone()[0] == 0:
        diametros_iniciales = [("10 cm", 0.0), ("15 cm", 0.0), ("20 cm", 0.0), ("30 cm", 0.0), ("50 cm", 0.0), ("100 cm", 0.0)]
        c.executemany("INSERT INTO diametros (medida, precio) VALUES (?,?)", diametros_iniciales)
        
    conn.commit()
    conn.close()

init_db()

def obtener_diametros():
    conn = get_connection()
    try:
        df = pd.read_sql("SELECT medida FROM diametros ORDER BY id ASC", conn)
        res = ["Seleccione..."] + df['medida'].tolist()
    except:
        res = ["Seleccione..."]
    conn.close()
    return res

def obtener_clientes():
    conn = get_connection()
    try:
        df = pd.read_sql("SELECT nombre FROM clientes ORDER BY nombre ASC", conn)
        res = ["Seleccione Cliente..."] + df['nombre'].tolist()
    except:
        res = ["Seleccione Cliente..."]
    conn.close()
    return res

# --- 4. FLUJO PRINCIPAL (SOLO SI ESTÁ AUTENTICADO) ---
if login():
    st.sidebar.title("🏭 Control Tubos")
    
    if st.sidebar.button("Cerrar Sesión"):
        st.session_state.autenticado = False
        st.session_state.config_autenticado = False # Resetea también la de configuración
        st.rerun()
        
    st.sidebar.divider()
    
    menu = st.sidebar.radio("Navegación", [
        "Resumen de Inventario", 
        "Registro de Producción Diaria", 
        "Gestión de Pedidos y Ventas", 
        "Despachos (Entregas)",
        "Configuración"
    ])

    # Al cambiar de pestaña en el menú, bloqueamos la configuración de nuevo por seguridad
    if menu != "Configuración":
        st.session_state.config_autenticado = False

    DIAMETROS_DB = obtener_diametros()
    CLIENTES_DB = obtener_clientes()

    if menu == "Resumen de Inventario":
        st.header("📊 Inventario en Tiempo Real")
        st.info("Aquí pondremos los indicadores de cuántos tubos de cada medida hay disponibles en patio hoy.")

    elif menu == "Registro de Producción Diaria":
        st.header("🧱 Registrar Fabricación")
        with st.form("form_produccion"):
            c1, c2, c3 = st.columns(3)
            fecha_prod = c1.date_input("Fecha de Fabricación", obtener_fecha_ecuador())
            diametro_prod = c2.selectbox("Diámetro del Tubo", DIAMETROS_DB)
            cant_prod = c3.number_input("Cantidad Fabricada", min_value=1, step=1)
            
            if st.form_submit_button("Guardar Producción", type="primary"):
                if diametro_prod != "Seleccione...":
                    conn = get_connection()
                    conn.execute("INSERT INTO produccion (fecha, diametro, cantidad) VALUES (?,?,?)", 
                                 (fecha_prod.strftime("%Y-%m-%d"), diametro_prod, cant_prod))
                    conn.commit(); conn.close()
                    st.success(f"✅ Se agregaron {cant_prod} tubos de {diametro_prod} al inventario.")
                else:
                    st.error("Seleccione un diámetro válido.")

    elif menu == "Gestión de Pedidos y Ventas":
        st.header("📝 Nuevo Pedido / Venta")
        with st.form("form_pedidos"):
            c1, c2 = st.columns(2)
            fecha_ped = c1.date_input("Fecha del Pedido", obtener_fecha_ecuador())
            cliente_ped = c2.selectbox("Nombre del Comprador", CLIENTES_DB)
            
            c3, c4 = st.columns(2)
            diametro_ped = c3.selectbox("Diámetro Solicitado", DIAMETROS_DB)
            cant_ped = c4.number_input("Cantidad Total Comprada", min_value=1, step=1)
            
            obs = st.text_area("Información adicional del pedido")
            
            if st.form_submit_button("Crear Pedido", type="primary"):
                if diametro_ped != "Seleccione..." and cliente_ped != "Seleccione Cliente...":
                    conn = get_connection()
                    conn.execute("INSERT INTO pedidos (fecha, cliente, diametro, cantidad_total, estado, observaciones) VALUES (?,?,?,?,?,?)", 
                                 (fecha_ped.strftime("%Y-%m-%d"), cliente_ped, diametro_ped, cant_ped, "Pendiente", obs))
                    conn.commit(); conn.close()
                    st.success("✅ Pedido registrado con éxito.")
                else:
                    st.error("Complete seleccionando el cliente y el diámetro.")

    elif menu == "Despachos (Entregas)":
        st.header("🚚 Registrar Salida de Material")
        st.info("Próximamente: Módulo para registrar las cargas de camiones.")

    # --- 5. PESTAÑA CONFIGURACIÓN (CON CLAVE) ---
    elif menu == "Configuración":
        st.header("⚙️ Configuración del Sistema")
        
        # Validación de clave secundaria
        if not st.session_state.config_autenticado:
            st.warning("⚠️ Esta área requiere permisos de administrador.")
            with st.form("auth_admin"):
                clave_adm = st.text_input("Ingrese la clave de administrador", type="password")
                if st.form_submit_button("Desbloquear Configuración"):
                    if clave_adm == "Tubos2026":
                        st.session_state.config_autenticado = True
                        st.rerun()
                    else:
                        st.error("Clave incorrecta")
        else:
            # Si la clave es correcta, mostramos la configuración
            st.success("🔓 Modo Administrador Activo")
            
            tab_diametros, tab_clientes = st.tabs(["📏 Medidas y Precios", "👥 Directorio de Clientes"])
            
            with tab_diametros:
                conn = get_connection()
                df_diam = pd.read_sql("SELECT id, medida as Medida, precio as Precio_Unitario FROM diametros ORDER BY id ASC", conn)
                c_t1, c_f1 = st.columns([3, 2])
                with c_t1:
                    if not df_diam.empty:
                        df_diam['Precio_Unitario'] = df_diam['Precio_Unitario'].apply(lambda x: f"${x:.2f}")
                        st.dataframe(df_diam.drop(columns=['id']), use_container_width=True, hide_index=True)
                with c_f1:
                    st.markdown("**Aumentar Diámetro**")
                    with st.form("add_diam", clear_on_submit=True):
                        n_m = st.text_input("Medida")
                        n_p = st.number_input("Precio ($)", min_value=0.0, step=0.50)
                        if st.form_submit_button("Guardar"):
                            if n_m:
                                conn.execute("INSERT INTO diametros (medida, precio) VALUES (?,?)", (n_m, n_p))
                                conn.commit(); st.rerun()
                conn.close()

            with tab_clientes:
                conn = get_connection()
                df_cli = pd.read_sql("SELECT id, nombre as Cliente, telefono as Teléfono FROM clientes ORDER BY nombre ASC", conn)
                c_t2, c_f2 = st.columns([3, 2])
                with c_t2:
                    if not df_cli.empty:
                        st.dataframe(df_cli.drop(columns=['id']), use_container_width=True, hide_index=True)
                with c_f2:
                    st.markdown("**Nuevo Cliente**")
                    with st.form("add_cli", clear_on_submit=True):
                        n_c = st.text_input("Nombre")
                        n_t = st.text_input("Teléfono")
                        if st.form_submit_button("Registrar"):
                            if n_c:
                                conn.execute("INSERT INTO clientes (nombre, telefono) VALUES (?,?)", (n_c, n_t))
                                conn.commit(); st.rerun()
                conn.close()