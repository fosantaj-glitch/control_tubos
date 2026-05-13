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
    .stApp { background: linear-gradient(135deg, #ced4da 0%, #e9ecef 40%, #ffffff 100%); background-attachment: fixed; }
    [data-testid="stSidebar"] { background-color: #212529 !important; }
    [data-testid="stSidebar"] p, [data-testid="stSidebar"] span, [data-testid="stSidebar"] label, 
    [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3,
    div[role="radiogroup"] label { color: #ffffff !important; }
    section[data-testid="stSidebar"] .stButton button { background-color: #ffffff !important; border: 2px solid #adb5bd !important; border-radius: 8px !important; padding: 10px !important; width: 100% !important; }
    section[data-testid="stSidebar"] .stButton button p { color: #000000 !important; font-weight: bold !important; }
    [data-testid="stHeader"], .stForm, .stDataFrame { background-color: white; border-radius: 12px; padding: 20px; box-shadow: 5px 5px 15px rgba(0,0,0,0.05); }
    .titulo-seccion { background-color: #f1f3f5; color: #5c636a; padding: 6px 15px; border-radius: 4px; margin-top: 25px; margin-bottom: 10px; text-align: center; font-weight: 600; font-size: 1.05em; text-transform: uppercase; letter-spacing: 2px; border-bottom: 2px solid #8c9296; }
    </style>
    """, unsafe_allow_html=True
)

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
            clave = st.text_input("Contraseña", type="password", key="login_pass")
            if st.button("Ingresar", type="primary", use_container_width=True):
                if clave == "Tubos2026": st.session_state.autenticado = True; st.rerun() 
                else: st.error("❌ Clave incorrecta")
        return False
    return True

# --- 4. BASE DE DATOS Y CONEXIÓN ---
def obtener_fecha_ecuador():
    return datetime.now(timezone(timedelta(hours=-5))).date()

def get_connection():
    return sqlite3.connect('control_tubos_db.db', check_same_thread=False)

def init_db():
    conn = get_connection(); c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS produccion (id INTEGER PRIMARY KEY AUTOINCREMENT, fecha TEXT, diametro TEXT, cantidad INTEGER)')
    c.execute('CREATE TABLE IF NOT EXISTS pedidos (id INTEGER PRIMARY KEY AUTOINCREMENT, fecha TEXT, cliente TEXT, diametro TEXT, cantidad_total INTEGER, estado TEXT, observaciones TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS entregas (id INTEGER PRIMARY KEY AUTOINCREMENT, pedido_id INTEGER, fecha TEXT, cantidad_entregada INTEGER)')
    c.execute('CREATE TABLE IF NOT EXISTS diametros (id INTEGER PRIMARY KEY AUTOINCREMENT, medida TEXT, tipo TEXT, seccion TEXT, precio REAL)')
    c.execute('CREATE TABLE IF NOT EXISTS clientes (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, telefono TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS configuracion (id INTEGER PRIMARY KEY AUTOINCREMENT, parametro TEXT, valor REAL)')
    conn.commit(); conn.close()

init_db()

def descargar_datos():
    try:
        response = requests.post(URL_GOOGLE, json={"accion": "leer"}, timeout=30)
        if response.status_code == 200:
            data = response.json()
            if data.get("resultado") == "éxito":
                tablas = data.get("datos", {}); conn = get_connection()
                mapeo = [("Produccion", "produccion"), ("Pedidos", "pedidos"), ("Entregas", "entregas"), ("Diametros", "diametros"), ("Clientes", "clientes"), ("Configuracion", "configuracion")]
                for hoja, tabla_db in mapeo:
                    if hoja in tablas and len(tablas[hoja]) > 1:
                        df = pd.DataFrame(tablas[hoja][1:], columns=tablas[hoja][0])
                        df = df.replace(r'^\s*$', None, regex=True).dropna(how='all')
                        db_cols = pd.read_sql(f"PRAGMA table_info({tabla_db})", conn)['name'].tolist()
                        df = df[[c for c in df.columns if c in db_cols]]
                        conn.execute(f"DELETE FROM {tabla_db}"); df.to_sql(tabla_db, conn, if_exists='append', index=False)
                conn.commit(); conn.close(); return True, "OK"
    except Exception as e: return False, str(e)
    return False, "Error"

def subir_datos():
    try:
        conn = get_connection(); payload = {"accion": "sobreescribir"}
        tablas = {"Produccion": "produccion", "Pedidos": "pedidos", "Entregas": "entregas", "Diametros": "diametros", "Clientes": "clientes", "Configuracion": "configuracion"}
        for hoja, db in tablas.items():
            df = pd.read_sql(f"SELECT * FROM {db}", conn).fillna("")
            df = df.drop_duplicates() # Evita duplicados si se presiona el botón varias veces
            payload[hoja] = [df.columns.tolist()] + df.values.tolist()
        conn.close(); return requests.post(URL_GOOGLE, json=payload, timeout=30).status_code == 200
    except: return False

# --- 5. INTERFAZ ---
if login():
    if not st.session_state.datos_cargados:
        with st.spinner("📥 Sincronizando..."): descargar_datos(); st.session_state.datos_cargados = True; st.rerun()

    st.sidebar.markdown("<br>", unsafe_allow_html=True)
    try: st.sidebar.image("logo.jpg", use_container_width=True)
    except: st.sidebar.title("GUILLÉN")
    
    if st.sidebar.button("💾 Respaldar a Drive"):
        with st.spinner("Enviando paquete único a Drive..."):
            if subir_datos(): st.sidebar.success("✅ Guardado Exitoso")
            else: st.sidebar.error("❌ Error al guardar")
                
    if st.sidebar.button("🚪 Cerrar Sesión"):
        st.session_state.autenticado = False; st.session_state.datos_cargados = False; st.rerun()

    st.sidebar.divider()
    menu = ["📊 Resumen de Patio", "🧱 Fabricación Diaria", "📝 Pedidos y Ventas", "🚚 Despachos", "⚙️ Configuración"]
    opcion = st.sidebar.radio("MENÚ", menu)

    conn = get_connection()
    res_iva = conn.execute("SELECT valor FROM configuracion WHERE parametro='iva'").fetchone()
    VALOR_IVA = res_iva[0] if res_iva else 15.0

    if opcion == menu[0]:
        st.header("📊 Stock Real en Patio")
        df_p = pd.read_sql("SELECT diametro, SUM(cantidad) as fab FROM produccion GROUP BY diametro", conn)
        df_v = pd.read_sql("SELECT diametro, SUM(cantidad_total) as ped FROM pedidos GROUP BY diametro", conn)
        if not df_p.empty:
            resumen = pd.merge(df_p, df_v, on="diametro", how="left").fillna(0)
            resumen['Stock Disponible'] = resumen['fab'] - resumen['ped']
            resumen.columns = ['Producto / Diámetro', 'Total Fabricado', 'Total Vendido', 'Stock en Patio']
            st.dataframe(resumen, use_container_width=True, hide_index=True)
        else: st.info("No hay datos de fabricación.")

    elif opcion == menu[1]:
        st.header("🧱 Registro de Fabricación Diaria")
        df_d = pd.read_sql("SELECT medida, seccion FROM diametros ORDER BY medida", conn)
        listado = [f"{r['medida']} ({r['seccion']})" for _, r in df_d.iterrows()]
        
        with st.form("f_p"):
            c1, c2, c3 = st.columns(3)
            f = c1.date_input("Fecha", obtener_fecha_ecuador())
            d = c2.selectbox("Producto", ["Seleccione..."] + listado)
            n = c3.number_input("Cantidad", min_value=1, step=1)
            if st.form_submit_button("Guardar Fabricación"):
                if d != "Seleccione...":
                    conn.execute("INSERT INTO produccion (fecha, diametro, cantidad) VALUES (?,?,?)", (str(f), d, n))
                    conn.commit(); st.success("Guardado"); st.rerun()

        st.divider()
        st.subheader("🔍 Consultar Producción por Periodo")
        c1, c2 = st.columns(2)
        f_desde = c1.date_input("Fecha Desde", obtener_fecha_ecuador() - timedelta(days=7))
        f_hasta = c2.date_input("Fecha Hasta", obtener_fecha_ecuador())
        
        df_hist = pd.read_sql("SELECT id, fecha, diametro, cantidad FROM produccion WHERE fecha BETWEEN ? AND ? ORDER BY fecha DESC", conn, params=(str(f_desde), str(f_hasta)))
        
        if not df_hist.empty:
            st.dataframe(df_hist, use_container_width=True, hide_index=True)
            st.markdown("---")
            st.subheader("🛠️ Editar o Borrar Registro")
            with st.form("f_edit_prod"):
                c1, c2, c3, c4 = st.columns([1, 2, 2, 1])
                id_sel = c1.selectbox("ID a Modificar", df_hist['id'].tolist())
                f_new = c2.date_input("Nueva Fecha")
                d_new = c3.selectbox("Nuevo Producto", listado)
                n_new = c4.number_input("Nueva Cantidad", min_value=1, step=1)
                
                col_btn1, col_btn2 = st.columns(2)
                if col_btn1.form_submit_button("✅ Actualizar Registro", use_container_width=True):
                    conn.execute("UPDATE produccion SET fecha=?, diametro=?, cantidad=? WHERE id=?", (str(f_new), d_new, n_new, id_sel))
                    conn.commit(); st.success("Actualizado"); st.rerun()
                
                if col_btn2.form_submit_button("🗑️ Borrar Registro", use_container_width=True):
                    conn.execute("DELETE FROM produccion WHERE id=?", (id_sel,))
                    conn.commit(); st.warning("Registro Eliminado"); st.rerun()
        else:
            st.info("No hay registros en el periodo seleccionado.")

    elif opcion == menu[2]:
        st.header("📝 Registro de Pedidos y Ventas")
        df_c = pd.read_sql("SELECT nombre FROM clientes ORDER BY nombre", conn)
        df_d = pd.read_sql("SELECT medida, seccion FROM diametros ORDER BY medida", conn)
        with st.form("f_v"):
            c1, c2, c3 = st.columns(3)
            cl = c1.selectbox("Cliente", ["Seleccione..."] + df_c['nombre'].tolist())
            d = c2.selectbox("Producto", ["Seleccione..."] + [f"{r['medida']} ({r['seccion']})" for _, r in df_d.iterrows()])
            n = c3.number_input("Cantidad", min_value=1, step=1)
            if st.form_submit_button("Registrar Pedido"):
                if cl != "Seleccione..." and d != "Seleccione...":
                    conn.execute("INSERT INTO pedidos (fecha, cliente, diametro, cantidad_total, estado, observaciones) VALUES (?,?,?,?,?,?)", (str(obtener_fecha_ecuador()), cl, d, n, 'Pendiente', ''))
                    conn.commit(); st.success("Registrado"); st.rerun()

    elif opcion == menu[3]:
        st.header("🚚 Control de Despachos")
        pedidos = pd.read_sql("SELECT id, fecha, cliente, diametro, cantidad_total as Cantidad FROM pedidos WHERE estado='Pendiente'", conn)
        if not pedidos.empty:
            st.table(pedidos)
            with st.form("desp"):
                sel = st.selectbox("Pedido a Entregar", [f"ID {r['id']} - {r['cliente']}" for _, r in pedidos.iterrows()])
                if st.form_submit_button("Marcar como Entregado"):
                    pid = int(sel.split(" ")[1])
                    conn.execute("UPDATE pedidos SET estado='Entregado' WHERE id=?", (pid,)); conn.commit(); st.rerun()
        else: st.info("Sin despachos pendientes.")

    elif opcion == menu[4]:
        st.header("⚙️ Administración de Datos")
        if not st.session_state.config_autenticado:
            with st.form("admin_lock"):
                cl_adm = st.text_input("Clave de Administrador", type="password")
                if st.form_submit_button("Desbloquear"):
                    if cl_adm == "Tubos2026":
                        st.session_state.config_autenticado = True; st.rerun()
                    else: st.error("❌ Clave incorrecta")
        else:
            t1, t2, t3 = st.tabs(["📏 Catálogo de Productos", "👥 Clientes", "💰 IVA"])
            
            # --- PESTAÑA 1: CATÁLOGO ---
            with t1:
                df = pd.read_sql("SELECT * FROM diametros", conn)
                if not df.empty:
                    df['num'] = df['medida'].str.extract(r'(\d+)').astype(float)
                    df['Pulgadas'] = (df['num'] / 25.4).apply(lambda x: f'{math.ceil(x)}"' if pd.notna(x) else "-")
                    df['Total'] = df['precio'] * (1 + (VALOR_IVA / 100))
                    for s in ["SIN ARMADURA", "HORMIGON ARMADO", "CON ESPIGA", "TUBERIA CLASE II", "TAPAS PEATONALES"]:
                        st.markdown(f'<div class="titulo-seccion">{s}</div>', unsafe_allow_html=True)
                        dfs = df[df['seccion'] == s].sort_values('num', ascending=True)
                        if not dfs.empty:
                            dfm = dfs[['medida', 'Pulgadas', 'tipo', 'precio', 'Total']].rename(columns={'medida': 'Medida (mm)', 'precio': 'Unitario ($)', 'Total': f'Con {VALOR_IVA}% IVA'})
                            dfm['Unitario ($)'] = dfm['Unitario ($)'].apply(lambda x: f"${x:.2f}")
                            dfm[f'Con {VALOR_IVA}% IVA'] = dfm[f'Con {VALOR_IVA}% IVA'].apply(lambda x: f"${x:.2f}")
                            st.table(dfm.assign(idx='').set_index('idx'))
                
                st.divider()
                c_a, c_e, c_b = st.columns(3)
                with c_a:
                    with st.form("a_d", clear_on_submit=True):
                        st.write("**Nuevo Producto**")
                        n_sec = st.selectbox("Sección", ["SIN ARMADURA", "HORMIGON ARMADO", "CON ESPIGA", "TUBERIA CLASE II", "TAPAS PEATONALES"])
                        n_m = st.text_input("Medida (mm)")
                        n_t = st.text_input("Tipo/Detalle")
                        n_p = st.number_input("Valor Unitario", min_value=0.0, format="%.2f")
                        if st.form_submit_button("Guardar"):
                            conn.execute("INSERT INTO diametros (medida, tipo, seccion, precio) VALUES (?,?,?,?)", (n_m, n_t, n_sec, n_p))
                            conn.commit(); st.rerun()
                with c_e:
                    if not df.empty:
                        with st.form("e_d"):
                            st.write("**Editar Producto**")
                            op_ed = {f"{r['medida']} ({r['seccion']})": r['medida'] for _, r in df.iterrows()}
                            sel_m = op_ed[st.selectbox("Elegir Medida", list(op_ed.keys()))]
                            new_s = st.selectbox("Nueva Sección", ["SIN ARMADURA", "HORMIGON ARMADO", "CON ESPIGA", "TUBERIA CLASE II", "TAPAS PEATONALES"])
                            new_m = st.text_input("Nuevo Nombre Medida (mm)")
                            new_t = st.text_input("Nuevo Tipo/Detalle")
                            new_p = st.number_input("Nuevo Valor Unitario", min_value=0.0, format="%.2f")
                            if st.form_submit_button("Actualizar"):
                                conn.execute("UPDATE diametros SET seccion=?, medida=?, tipo=?, precio=? WHERE medida=?", (new_s, new_m, new_t, new_p, sel_m))
                                conn.commit(); st.rerun()
                with c_b:
                    if not df.empty:
                        with st.form("b_d"):
                            st.write("**Borrar**")
                            del_s = st.selectbox("Eliminar", df['medida'].unique())
                            if st.form_submit_button("Borrar"):
                                conn.execute("DELETE FROM diametros WHERE medida=?", (del_s,))
                                conn.commit(); st.rerun()

            # --- PESTAÑA 2: CLIENTES ---
            with t2:
                df_c = pd.read_sql("SELECT * FROM clientes ORDER BY nombre ASC", conn)
                st.write("**Directorio de Clientes**")
                st.dataframe(df_c.drop(columns=['id']), use_container_width=True, hide_index=True)
                c1, c2, c3 = st.columns(3)
                with c1:
                    with st.form("a_c", clear_on_submit=True):
                        st.write("**Registrar**")
                        nn, nt = st.text_input("Nombre"), st.text_input("Teléfono")
                        if st.form_submit_button("Guardar"):
                            if nn: 
                                conn.execute("INSERT INTO clientes (nombre, telefono) VALUES (?,?)", (nn, nt))
                                conn.commit(); st.rerun()
                with c2:
                    if not df_c.empty:
                        with st.form("e_c"):
                            st.write("**Corregir**")
                            sel_c = st.selectbox("Elegir Cliente", df_c['nombre'].tolist())
                            new_n = st.text_input("Nombre Correcto")
                            new_t = st.text_input("Teléfono Correcto")
                            if st.form_submit_button("Actualizar"):
                                if new_n:
                                    conn.execute("UPDATE clientes SET nombre=?, telefono=? WHERE nombre=?", (new_n, new_t, sel_c))
                                    conn.commit(); st.rerun()
                with c3:
                    if not df_c.empty:
                        with st.form("b_c"):
                            st.write("**Borrar**")
                            del_c = st.selectbox("Eliminar Cliente", df_c['nombre'].tolist())
                            if st.form_submit_button("Borrar"):
                                conn.execute("DELETE FROM clientes WHERE nombre=?", (del_c,))
                                conn.commit(); st.rerun()

            # --- PESTAÑA 3: IVA ---
            with t3:
                st.write("**Configuración de IVA**")
                with st.form("f_iva"):
                    n_iva = st.number_input("IVA (%)", min_value=0.0, max_value=100.0, value=float(VALOR_IVA), format="%.2f")
                    if st.form_submit_button("Actualizar"):
                        conn.execute("UPDATE configuracion SET valor=? WHERE parametro='iva'", (n_iva,))
                        conn.commit(); st.success("IVA actualizado"); st.rerun()
    conn.close()