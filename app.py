import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, timezone, timedelta

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Control de Tubos - Inventario", layout="wide")

# --- SISTEMA DE SEGURIDAD ---
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False

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

# --- FUNCIONES DE BASE DE DATOS ---
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
    
    # Tablas de Configuración (NUEVAS)
    c.execute('''CREATE TABLE IF NOT EXISTS diametros (id INTEGER PRIMARY KEY AUTOINCREMENT, medida TEXT, precio REAL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS clientes (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, telefono TEXT)''')
    
    # Auto-sembrar diámetros básicos si la tabla está vacía
    c.execute("SELECT COUNT(*) FROM diametros")
    if c.fetchone()[0] == 0:
        diametros_iniciales = [("10 cm", 0.0), ("15 cm", 0.0), ("20 cm", 0.0), ("30 cm", 0.0), ("50 cm", 0.0), ("100 cm", 0.0)]
        c.executemany("INSERT INTO diametros (medida, precio) VALUES (?,?)", diametros_iniciales)
        
    conn.commit()
    conn.close()

init_db()

# Funciones extractoras para los menús desplegables
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

# --- FLUJO PRINCIPAL (SOLO VISIBLE SI LA CLAVE ES CORRECTA) ---
if login():
    st.sidebar.title("🏭 Control Tubos")
    
    if st.sidebar.button("Cerrar Sesión"):
        st.session_state.autenticado = False
        st.rerun()
        
    st.sidebar.divider()
    
    menu = st.sidebar.radio("Navegación", [
        "Resumen de Inventario", 
        "Registro de Producción Diaria", 
        "Gestión de Pedidos y Ventas", 
        "Despachos (Entregas)",
        "Configuración"
    ])

    # Se alimentan automáticamente de la base de datos
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
            
            # Ahora es un menú desplegable conectado a la configuración
            cliente_ped = c2.selectbox("Nombre del Comprador", CLIENTES_DB)
            
            c3, c4 = st.columns(2)
            diametro_ped = c3.selectbox("Diámetro Solicitado", DIAMETROS_DB)
            cant_ped = c4.number_input("Cantidad Total Comprada", min_value=1, step=1)
            
            obs = st.text_area("Información adicional del pedido (Ej. Fechas acordadas de entrega)")
            
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
        st.info("Aquí cruzaremos los pedidos creados con las salidas reales para saber exactamente cuántos tubos faltan por enviar a cada cliente.")

    # --- NUEVA PESTAÑA: CONFIGURACIÓN ---
    elif menu == "Configuración":
        st.header("⚙️ Configuración del Sistema")
        
        tab_diametros, tab_clientes = st.tabs(["📏 Medidas y Precios de Tubos", "👥 Base de Datos de Clientes"])
        
        with tab_diametros:
            st.subheader("Tubos de Hormigón")
            conn = get_connection()
            df_diam = pd.read_sql("SELECT id, medida as Medida, precio as Precio_Unitario FROM diametros ORDER BY id ASC", conn)
            
            col_tabla1, col_form1 = st.columns([3, 2])
            
            with col_tabla1:
                if not df_diam.empty:
                    df_diam['Precio_Unitario'] = df_diam['Precio_Unitario'].apply(lambda x: f"${x:.2f}")
                    st.dataframe(df_diam.drop(columns=['id']), use_container_width=True, hide_index=True)
                else:
                    st.info("No hay medidas registradas.")
            
            with col_form1:
                st.markdown("**Agregar Nueva Medida**")
                with st.form("form_add_diametro", clear_on_submit=True):
                    n_medida = st.text_input("Diámetro (Ej: 80 cm)")
                    n_precio = st.number_input("Precio de Venta ($)", min_value=0.0, step=0.50, format="%.2f")
                    if st.form_submit_button("Guardar Medida", type="primary"):
                        if n_medida.strip():
                            conn.execute("INSERT INTO diametros (medida, precio) VALUES (?, ?)", (n_medida.strip(), n_precio))
                            conn.commit()
                            st.rerun()
            conn.close()

        with tab_clientes:
            st.subheader("Directorio de Compradores")
            conn = get_connection()
            df_cli = pd.read_sql("SELECT id, nombre as Cliente, telefono as Teléfono FROM clientes ORDER BY nombre ASC", conn)
            
            col_tabla2, col_form2 = st.columns([3, 2])
            
            with col_tabla2:
                if not df_cli.empty:
                    st.dataframe(df_cli.drop(columns=['id']), use_container_width=True, hide_index=True)
                else:
                    st.info("La base de datos de clientes está vacía.")
            
            with col_form2:
                st.markdown("**Registrar Nuevo Cliente**")
                with st.form("form_add_cliente", clear_on_submit=True):
                    n_cliente = st.text_input("Nombre Completo o Empresa")
                    n_telefono = st.text_input("Número de Contacto")
                    if st.form_submit_button("Guardar Cliente", type="primary"):
                        if n_cliente.strip():
                            conn.execute("INSERT INTO clientes (nombre, telefono) VALUES (?, ?)", (n_cliente.strip(), n_telefono.strip()))
                            conn.commit()
                            st.rerun()
                        else:
                            st.error("El nombre del cliente es obligatorio.")
            conn.close()