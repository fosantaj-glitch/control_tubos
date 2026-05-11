import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, timezone, timedelta

st.set_page_config(page_title="Control de Tubos - Inventario", layout="wide")

def obtener_fecha_ecuador():
    tz_ecuador = timezone(timedelta(hours=-5))
    return datetime.now(tz_ecuador).date()

def get_connection():
    return sqlite3.connect('control_tubos_db.db', check_same_thread=False)

def init_db():
    conn = get_connection()
    c = conn.cursor()
    # Tabla 1: Lo que se fabrica (Suma al inventario)
    c.execute('''CREATE TABLE IF NOT EXISTS produccion 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, fecha TEXT, diametro TEXT, cantidad INTEGER)''')
    
    # Tabla 2: El contrato de venta (No resta del inventario hasta que se entrega)
    c.execute('''CREATE TABLE IF NOT EXISTS pedidos 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, fecha TEXT, cliente TEXT, diametro TEXT, 
                  cantidad_total INTEGER, estado TEXT, observaciones TEXT)''')
                  
    # Tabla 3: Lo que sale en el camión (Resta del inventario y actualiza el pedido)
    c.execute('''CREATE TABLE IF NOT EXISTS entregas 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, pedido_id INTEGER, fecha TEXT, cantidad_entregada INTEGER,
                  FOREIGN KEY(pedido_id) REFERENCES pedidos(id))''')
    conn.commit()
    conn.close()

init_db()

# --- MENÚ LATERAL ---
st.sidebar.title("🏭 Control Tubos")
menu = st.sidebar.radio("Navegación", [
    "Resumen de Inventario", 
    "Registro de Producción Diaria", 
    "Gestión de Pedidos y Ventas", 
    "Despachos (Entregas)"
])

# Variables base
DIAMETROS = ["Seleccione...", "10 cm", "15 cm", "20 cm", "30 cm", "50 cm", "100 cm"] # Ajustaremos estos a tu realidad

if menu == "Resumen de Inventario":
    st.header("📊 Inventario en Tiempo Real")
    st.info("Aquí pondremos los indicadores de cuántos tubos de cada medida hay disponibles en patio hoy.")

elif menu == "Registro de Producción Diaria":
    st.header("🧱 Registrar Fabricación")
    with st.form("form_produccion"):
        c1, c2, c3 = st.columns(3)
        fecha_prod = c1.date_input("Fecha de Fabricación", obtener_fecha_ecuador())
        diametro_prod = c2.selectbox("Diámetro del Tubo", DIAMETROS)
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
        cliente = c2.text_input("Nombre del Comprador")
        
        c3, c4 = st.columns(2)
        diametro_ped = c3.selectbox("Diámetro Solicitado", DIAMETROS)
        cant_ped = c4.number_input("Cantidad Total Comprada", min_value=1, step=1)
        
        obs = st.text_area("Información adicional del pedido (Ej. Fechas acordadas de entrega)")
        
        if st.form_submit_button("Crear Pedido", type="primary"):
            if diametro_ped != "Seleccione..." and cliente:
                conn = get_connection()
                conn.execute("INSERT INTO pedidos (fecha, cliente, diametro, cantidad_total, estado, observaciones) VALUES (?,?,?,?,?,?)", 
                             (fecha_ped.strftime("%Y-%m-%d"), cliente, diametro_ped, cant_ped, "Pendiente", obs))
                conn.commit(); conn.close()
                st.success("✅ Pedido registrado con éxito.")
            else:
                st.error("Complete el cliente y el diámetro.")

elif menu == "Despachos (Entregas)":
    st.header("🚚 Registrar Salida de Material")
    st.info("Aquí cruzaremos los pedidos creados con las salidas reales para saber exactamente cuántos tubos faltan por enviar a cada cliente.")