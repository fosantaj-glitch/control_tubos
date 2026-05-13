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
    .total-row { font-size: 1.2em; font-weight: bold; color: #1e1e1e; text-align: right; padding: 10px; background: #f8f9fa; border-top: 2px solid #dee2e6; }
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
    c.execute('CREATE TABLE IF NOT EXISTS clientes (id INTEGER PRIMARY KEY AUTOINCREMENT, empresa TEXT, nombre TEXT, telefono TEXT)')
    try: c.execute('ALTER TABLE clientes ADD COLUMN empresa TEXT')
    except: pass
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
            df = df.drop_duplicates()
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
        st.session_state.autenticado = False; st.session_state.config_autenticado = False; st.session_state.datos_cargados = False; st.rerun()

    st.sidebar.divider()
    menu = ["📊 Resumen de Patio", "🧱 Fabricación Diaria", "📝 Pedidos y Ventas", "🚚 Despachos", "⚙️ Configuración"]
    opcion = st.sidebar.radio("MENÚ", menu)

    if opcion != menu[4]: st.session_state.config_autenticado = False

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
        else: st.info("No hay datos.")

    elif opcion == menu[1]:
        st.header("🧱 Registro de Fabricación Diaria")
        # Obtener productos ordenados como el catálogo
        df_d = pd.read_sql("SELECT medida, seccion FROM diametros", conn)
        df_d['num'] = df_d['medida'].str.extract(r'(\d+)').astype(float)
        seccion_order = {"SIN ARMADURA": 1, "HORMIGON ARMADO": 2, "CON ESPIGA": 3, "TUBERIA CLASE II": 4, "TAPAS PEATONALES": 5}
        df_d['order_sec'] = df_d['seccion'].map(seccion_order)
        df_d = df_d.sort_values(['order_sec', 'num'])
        
        listado_p = [f"{r['medida']} ({r['seccion']})" for _, r in df_d.iterrows()] if not df_d.empty else ["Sin productos"]
        
        with st.form("f_p"):
            c1, c2, c3 = st.columns(3)
            f = c1.date_input("Fecha", obtener_fecha_ecuador())
            d = c2.selectbox("Producto", ["Seleccione..."] + listado_p)
            n = c3.number_input("Cantidad", min_value=1, step=1, value=None, placeholder="0")
            if st.form_submit_button("Guardar Fabricación"):
                if d != "Seleccione..." and n:
                    conn.execute("INSERT INTO produccion (fecha, diametro, cantidad) VALUES (?,?,?)", (str(f), d, n))
                    conn.commit(); st.success("Guardado"); st.rerun()

    elif opcion == menu[2]:
        st.header("📝 Registro de Pedidos y Ventas")
        df_c = pd.read_sql("SELECT nombre, empresa FROM clientes ORDER BY nombre", conn)
        
        # OBTENER PRODUCTOS ORDENADOS Y CON PRECIO
        df_prod_info = pd.read_sql("SELECT medida, seccion, precio FROM diametros", conn)
        df_prod_info['num'] = df_prod_info['medida'].str.extract(r'(\d+)').astype(float)
        seccion_order = {"SIN ARMADURA": 1, "HORMIGON ARMADO": 2, "CON ESPIGA": 3, "TUBERIA CLASE II": 4, "TAPAS PEATONALES": 5}
        df_prod_info['order_sec'] = df_prod_info['seccion'].map(seccion_order)
        df_prod_info = df_prod_info.sort_values(['order_sec', 'num'])
        
        # Mapeo de nombre visible a precio para cálculos
        dict_precios = {f"{r['medida']} ({r['seccion']})": r['precio'] for _, r in df_prod_info.iterrows()}
        listado_cli = [f"{r['nombre']} ({r['empresa']})" for _, r in df_c.iterrows()] if not df_c.empty else ["Sin clientes"]
        listado_prod = list(dict_precios.keys())
        
        with st.form("f_v_multi"):
            st.subheader("🛒 Selección de Venta")
            c_cl, c_pr = st.columns([1, 2])
            cl_full = c_cl.selectbox("Cliente", ["Seleccione..."] + listado_cli)
            prods_sel = c_pr.multiselect("Seleccionar Productos (Ordenados por catálogo)", listado_prod)
            
            st.markdown("---")
            st.subheader("📐 Detalle de Cantidades y Precios")
            
            # Cabecera de la tabla de compra
            h1, h2, h3, h4, h5 = st.columns([3, 1, 1, 1, 1.5])
            h1.write("**Producto**")
            h2.write("**Valor Unit.**")
            h3.write("**% Desc.**")
            h4.write("**Cantidad**")
            h5.write("**Subtotal**")
            
            total_venta = 0.0
            data_final = [] # Para guardar los registros que se insertarán

            if prods_sel:
                for p in prods_sel:
                    p_unit = dict_precios[p]
                    r1, r2, r3, r4, r5 = st.columns([3, 1, 1, 1, 1.5])
                    
                    r1.write(f"**{p}**")
                    r2.write(f"${p_unit:.2f}")
                    desc = r3.number_input("%", min_value=0, max_value=100, value=0, key=f"d_{p}", step=1)
                    cant = r4.number_input("Cant.", min_value=1, step=1, value=None, placeholder="0", key=f"q_{p}")
                    
                    subtotal = 0.0
                    if cant:
                        # Cálculo: (Precio * Cant) * (1 - Desc/100)
                        subtotal = (p_unit * cant) * (1 - (desc / 100))
                    
                    r5.write(f"**${subtotal:.2f}**")
                    total_venta += subtotal
                    if cant:
                        data_final.append((p, cant, desc))

                st.markdown(f'<div class="total-row">VALOR TOTAL DE COMPRA: ${total_venta:.2f}</div>', unsafe_allow_html=True)
            else:
                st.info("Seleccione productos arriba para generar el cuadro de compra.")

            if st.form_submit_button("🚀 Registrar Venta Completa"):
                if cl_full != "Seleccione..." and data_final:
                    cl_pure = cl_full.split(" (")[0]
                    fecha_hoy = str(obtener_fecha_ecuador())
                    for p_name, n_cant, p_desc in data_final:
                        obs = f"Desc: {p_desc}%" if p_desc > 0 else ""
                        conn.execute("INSERT INTO pedidos (fecha, cliente, diametro, cantidad_total, estado, observaciones) VALUES (?,?,?,?,?,?)", (fecha_hoy, cl_pure, p_name, n_cant, 'Pendiente', obs))
                    conn.commit(); st.success("✅ Venta múltiple registrada."); st.rerun()

        st.divider(); st.subheader("🔍 Consultar Estado de Pedidos")
        cf1, cf2, cf3 = st.columns(3); f_cli = cf1.selectbox("Filtrar por Cliente", ["Todos"] + [r['nombre'] for _, r in df_c.iterrows()])
        fv_d = cf2.date_input("Desde", obtener_fecha_ecuador()-timedelta(days=30), key="fv1"); fv_h = cf3.date_input("Hasta", obtener_fecha_ecuador(), key="fv2")
        q = "SELECT p.id as ID, p.fecha as 'Fecha Pedido', p.cliente as Cliente, p.diametro as Producto, p.cantidad_total as 'Cant. Compra', IFNULL(SUM(e.cantidad_entregada), 0) as 'Cant. Despachada', MAX(e.fecha) as 'Último Despacho', (p.cantidad_total - IFNULL(SUM(e.cantidad_entregada), 0)) as Saldo, p.estado as Estado, p.observaciones as Info FROM pedidos p LEFT JOIN entregas e ON p.id = e.pedido_id WHERE p.fecha BETWEEN ? AND ?"
        p_q = [str(fv_d), str(fv_h)]
        if f_cli != "Todos": q += " AND p.cliente = ?"; p_q.append(f_cli)
        q += " GROUP BY p.id ORDER BY p.fecha DESC"
        df_v_h = pd.read_sql(q, conn, params=tuple(p_q))
        st.dataframe(df_v_h.fillna("-"), use_container_width=True, hide_index=True)

    elif opcion == menu[3]:
        st.header("🚚 Control de Despachos")
        query_p = "SELECT p.id, p.fecha, p.cliente, p.diametro, p.cantidad_total, (p.cantidad_total - IFNULL(SUM(e.cantidad_entregada), 0)) as saldo FROM pedidos p LEFT JOIN entregas e ON p.id = e.pedido_id GROUP BY p.id HAVING saldo > 0"
        pedidos_p = pd.read_sql(query_p, conn)
        if not pedidos_p.empty:
            st.table(pedidos_p)
            with st.form("f_desp"):
                c1, c2, c3 = st.columns(3)
                sel_p = c1.selectbox("Pedido", [f"ID {r['id']} - {r['cliente']} ({r['diametro']} | Saldo: {r['saldo']})" for _, r in pedidos_p.iterrows()])
                c_desp = c2.number_input("Cant. Despacho", min_value=1, value=None, placeholder="0")
                f_desp = c3.date_input("Fecha", obtener_fecha_ecuador())
                if st.form_submit_button("Registrar"):
                    if c_desp:
                        pid = int(sel_p.split(" ")[1]); s_act = int(sel_p.split("Saldo: ")[1].replace(")", ""))
                        if c_desp <= s_act:
                            conn.execute("INSERT INTO entregas (pedido_id, fecha, cantidad_entregada) VALUES (?,?,?)", (pid, str(f_desp), c_desp))
                            if c_desp == s_act: conn.execute("UPDATE pedidos SET estado='Entregado' WHERE id=?", (pid,))
                            conn.commit(); st.success("✅ Despachado"); st.rerun()

    elif opcion == menu[4]:
        st.header("⚙️ Administración de Datos")
        if not st.session_state.config_autenticado:
            with st.form("admin_lock"):
                if st.text_input("Clave", type="password") == "Tubos2026" and st.form_submit_button("Entrar"):
                    st.session_state.config_autenticado = True; st.rerun()
        else:
            t1, t2, t3 = st.tabs(["📏 Catálogo", "👥 Clientes", "💰 IVA"])
            with t1:
                df_cat = pd.read_sql("SELECT * FROM diametros", conn)
                if not df_cat.empty:
                    df_cat['num'] = df_cat['medida'].str.extract(r'(\d+)').astype(float)
                    for s in ["SIN ARMADURA", "HORMIGON ARMADO", "CON ESPIGA", "TUBERIA CLASE II", "TAPAS PEATONALES"]:
                        st.markdown(f'<div class="titulo-seccion">{s}</div>', unsafe_allow_html=True)
                        dfs = df_cat[df_cat['seccion'] == s].sort_values('num')
                        if not dfs.empty: st.table(dfs[['medida', 'tipo', 'precio']].assign(idx='').set_index('idx'))
                st.divider(); c_a, c_e, c_b = st.columns(3)
                with c_a:
                    with st.form("a_d"):
                        sec = st.selectbox("Sección", ["SIN ARMADURA", "HORMIGON ARMADO", "CON ESPIGA", "TUBERIA CLASE II", "TAPAS PEATONALES"]); med, tip, pre = st.text_input("Medida"), st.text_input("Tipo"), st.number_input("Precio", format="%.2f")
                        if st.form_submit_button("Añadir"): conn.execute("INSERT INTO diametros (medida, tipo, seccion, precio) VALUES (?,?,?,?)", (med, tip, sec, pre)); conn.commit(); st.rerun()
                with c_e:
                    if not df_cat.empty:
                        with st.form("e_d"):
                            sel = st.selectbox("Elegir", df_cat['medida'].tolist()); nsec = st.selectbox("Secc", ["SIN ARMADURA", "HORMIGON ARMADO", "CON ESPIGA", "TUBERIA CLASE II", "TAPAS PEATONALES"]); nmed, ntip, npre = st.text_input("Med"), st.text_input("Tip"), st.number_input("Pre", format="%.2f")
                            if st.form_submit_button("Editar"): conn.execute("UPDATE diametros SET seccion=?, medida=?, tipo=?, precio=? WHERE medida=?", (nsec, nmed, ntip, npre, sel)); conn.commit(); st.rerun()
                with c_b:
                    if not df_cat.empty:
                        with st.form("b_d"):
                            b_sel = st.selectbox("Borrar", df_cat['medida'].tolist()); 
                            if st.form_submit_button("Borrar"): conn.execute("DELETE FROM diametros WHERE medida=?", (b_sel,)); conn.commit(); st.rerun()
            with t2:
                df_cli = pd.read_sql("SELECT empresa, nombre, telefono FROM clientes ORDER BY nombre ASC", conn)
                st.dataframe(df_cli, use_container_width=True, hide_index=True)
                c_a, c_e, c_b = st.columns(3)
                with c_a:
                    with st.form("a_c"):
                        e, n, t = st.text_input("Empresa"), st.text_input("Contacto"), st.text_input("Teléfono")
                        if st.form_submit_button("Guardar"): conn.execute("INSERT INTO clientes (empresa, nombre, telefono) VALUES (?,?,?)", (e, n, t)); conn.commit(); st.rerun()
                with c_e:
                    if not df_cli.empty:
                        with st.form("e_c"):
                            sel = st.selectbox("Elegir", df_cli['nombre'].tolist()); ne, nn, nt = st.text_input("Emp"), st.text_input("Cont"), st.text_input("Tel")
                            if st.form_submit_button("Actualizar"): conn.execute("UPDATE clientes SET empresa=?, nombre=?, telefono=? WHERE nombre=?", (ne, nn, nt, sel)); conn.commit(); st.rerun()
                with c_b:
                    if not df_cli.empty:
                        with st.form("b_c"):
                            sel = st.selectbox("Eliminar", df_cli['nombre'].tolist())
                            if st.form_submit_button("Borrar"): conn.execute("DELETE FROM clientes WHERE nombre=?", (sel,)); conn.commit(); st.rerun()
            with t3:
                n_iva = st.number_input("IVA (%)", value=float(VALOR_IVA)); 
                if st.button("Actualizar"): conn.execute("UPDATE configuracion SET valor=? WHERE parametro='iva'", (n_iva,)); conn.commit(); st.rerun()
    conn.close()