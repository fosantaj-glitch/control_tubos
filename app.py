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
    .total-row { font-size: 1.3em; font-weight: bold; color: #d90429; text-align: right; padding: 20px; background: #f1f3f5; border-radius: 8px; margin-top: 10px; border: 2px solid #adb5bd; }
    </style>
    """, unsafe_allow_html=True
)

URL_GOOGLE = "https://script.google.com/macros/s/AKfycbwoL0M4LCT2s8oAt362Jkb21lKvJM-HmGXErlrH3DQ3WE6GMypfaJO6_xfW1R-U3VS_/exec"

# --- 3. SEGURIDAD Y ESTADOS ---
if "autenticado" not in st.session_state: st.session_state.autenticado = False
if "config_autenticado" not in st.session_state: st.session_state.config_autenticado = False
if "datos_cargados" not in st.session_state: st.session_state.datos_cargados = False
if "k_desp" not in st.session_state: st.session_state.k_desp = 0 

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

# --- 4. BASE DE DATOS ---
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
    except: return False, "Error"
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

def limpiar_formulario_venta():
    if "cl_sel" in st.session_state: st.session_state.cl_sel = "Seleccione..."
    if "prods_sel" in st.session_state: st.session_state.prods_sel = []
    for k in list(st.session_state.keys()):
        if k.startswith("d_") or k.startswith("q_"): st.session_state[k] = 0 if k.startswith("d_") else None

# --- 5. INTERFAZ ---
if login():
    if not st.session_state.datos_cargados:
        with st.spinner("📥 Sincronizando..."): descargar_datos(); st.session_state.datos_cargados = True; st.rerun()

    st.sidebar.markdown("<br>", unsafe_allow_html=True)
    try: st.sidebar.image("logo.jpg", use_container_width=True)
    except: st.sidebar.title("GUILLÉN")
    
    if st.sidebar.button("💾 Respaldar a Drive"):
        if subir_datos(): st.sidebar.success("✅ Guardado")
        else: st.sidebar.error("❌ Error")

    # NUEVO BOTÓN DE ACTUALIZACIÓN
    if st.sidebar.button("🔄 Refrescar Datos"):
        st.rerun()
                
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
        df_v = pd.read_sql("SELECT p.diametro, SUM(e.cantidad_entregada) as desp FROM entregas e JOIN pedidos p ON e.pedido_id = p.id GROUP BY p.diametro", conn)
        if not df_p.empty:
            resumen = pd.merge(df_p, df_v, on="diametro", how="left").fillna(0)
            resumen['Stock Disponible'] = resumen['fab'] - resumen['desp']
            resumen.columns = ['Producto / Diámetro', 'Total Fabricado', 'Total Despachado', 'Stock en Patio']
            st.dataframe(resumen, use_container_width=True, hide_index=True)
        else: st.info("Sin datos.")

    elif opcion == menu[1]:
        st.header("🧱 Fabricación Diaria")
        df_ord = pd.read_sql("SELECT medida, seccion FROM diametros", conn)
        df_ord['num'] = df_ord['medida'].str.extract(r'(\d+)').astype(float)
        df_ord['order_sec'] = df_ord['seccion'].map({"SIN ARMADURA": 1, "HORMIGON ARMADO": 2, "CON ESPIGA": 3, "TUBERIA CLASE II": 4, "TAPAS PEATONALES": 5})
        df_ord = df_ord.sort_values(['order_sec', 'num'])
        listado_p = [f"{r['medida']} ({r['seccion']})" for _, r in df_ord.iterrows()] if not df_ord.empty else ["Sin productos"]
        
        with st.form("f_p"):
            c1, c2, c3 = st.columns(3)
            f, d = c1.date_input("Fecha", obtener_fecha_ecuador()), c2.selectbox("Producto", ["Seleccione..."] + listado_p)
            n = c3.number_input("Cantidad", min_value=1, step=1, value=None, placeholder="0")
            if st.form_submit_button("Guardar"):
                if d != "Seleccione..." and n:
                    conn.execute("INSERT INTO produccion (fecha, diametro, cantidad) VALUES (?,?,?)", (str(f), d, n)); conn.commit(); st.success("✅ Guardado"); st.rerun()

        st.divider(); st.subheader("🔍 Consultar / Editar Producción")
        c1, c2 = st.columns(2); f_d = c1.date_input("Desde", obtener_fecha_ecuador()-timedelta(days=30), key="fp1"); f_h = c2.date_input("Hasta", obtener_fecha_ecuador(), key="fp2")
        df_h = pd.read_sql("SELECT * FROM produccion WHERE fecha BETWEEN ? AND ? ORDER BY id DESC", conn, params=(str(f_d), str(f_h)))
        st.dataframe(df_h, use_container_width=True, hide_index=True)
        st.markdown("---")
        with st.form("f_edit_prod"):
            c1, c2, c3, c4 = st.columns([1, 2, 2, 1]); ids_p = pd.read_sql("SELECT id FROM produccion ORDER BY id DESC", conn)
            id_s = c1.selectbox("ID a Modificar", ids_p['id'].tolist() if not ids_p.empty else ["-"])
            fn, dn, nn = c2.date_input("Nueva Fecha"), c3.selectbox("Nuevo Producto", listado_p), c4.number_input("Nueva Cant.", min_value=1, step=1, value=None, placeholder="0")
            b1, b2 = st.columns(2)
            if b1.form_submit_button("✅ Actualizar"):
                if id_s != "-" and nn: conn.execute("UPDATE produccion SET fecha=?, diametro=?, cantidad=? WHERE id=?", (str(fn), dn, nn, id_s)); conn.commit(); st.success("Actualizado"); st.rerun()
            if b2.form_submit_button("🗑️ Borrar"):
                if id_s != "-": conn.execute("DELETE FROM produccion WHERE id=?", (id_s,)); conn.commit(); st.warning("Eliminado"); st.rerun()

    elif opcion == menu[2]:
        st.header("📝 Pedidos y Ventas")
        df_c = pd.read_sql("SELECT nombre, empresa FROM clientes ORDER BY nombre", conn)
        df_pi = pd.read_sql("SELECT medida, seccion, precio FROM diametros", conn)
        df_pi['num'] = df_pi['medida'].str.extract(r'(\d+)').astype(float)
        df_pi['os'] = df_pi['seccion'].map({"SIN ARMADURA": 1, "HORMIGON ARMADO": 2, "CON ESPIGA": 3, "TUBERIA CLASE II": 4, "TAPAS PEATONALES": 5})
        df_pi = df_pi.sort_values(['os', 'num'])
        dict_precios = {f"{r['medida']} ({r['seccion']})": r['precio'] for _, r in df_pi.iterrows()}
        listado_cli = [f"{r['nombre']} ({r['empresa']})" for _, r in df_c.iterrows()]
        listado_prod = list(dict_precios.keys())
        
        st.subheader("🛒 Selección de Cliente y Productos")
        c1, c2 = st.columns([1, 2]); cl_f = c1.selectbox("Cliente", ["Seleccione..."] + listado_cli, key="cl_sel")
        p_sel = c2.multiselect("Buscador de Productos", listado_prod, key="prods_sel")

        if p_sel:
            st.divider(); st.subheader("📐 Detalle de Cantidades")
            h1, h2, h3, h4, h5 = st.columns([3, 1, 1, 1, 1.5])
            h1.write("**Producto**"); h2.write("**P. Unitario**"); h3.write("**% Desc.**"); h4.write("**Cant. Compra**"); h5.write("**Subtotal**")
            total_v = 0.0; d_save = []
            for p in p_sel:
                p_u = dict_precios[p]; r1, r2, r3, r4, r5 = st.columns([3, 1, 1, 1, 1.5])
                r1.write(f"**{p}**"); r2.write(f"${p_u:.2f}")
                dv = r3.number_input("%", min_value=0, max_value=100, step=1, value=0, key=f"d_{p}")
                cv = r4.number_input("Cant.", min_value=1, step=1, value=None, placeholder="0", key=f"q_{p}")
                sub = (p_u * (cv if cv else 0)) * (1 - (dv / 100))
                r5.write(f"**${sub:.2f}**"); total_v += sub
                if cv: d_save.append((p, cv, dv))
            st.markdown(f'<div class="total-row">VALOR TOTAL DE COMPRA: ${total_v:.2f}</div><br>', unsafe_allow_html=True)
            b_reg, b_limp = st.columns(2)
            if b_reg.button("🚀 Registrar Venta Completa", type="primary", use_container_width=True):
                if cl_f != "Seleccione..." and d_save:
                    cl_p = cl_f.split(" (")[0]; f_h = str(obtener_fecha_ecuador())
                    for pn, nc, pd in d_save: conn.execute("INSERT INTO pedidos (fecha, cliente, diametro, cantidad_total, estado, observaciones) VALUES (?,?,?,?,?,?)", (f_h, cl_p, pn, nc, 'Pendiente', f"Desc: {pd}%" if pd > 0 else ""))
                    conn.commit(); limpiar_formulario_venta(); st.success("✅ Venta registrada"); time.sleep(1); st.rerun()
            b_limp.button("🧹 Limpiar Registro", use_container_width=True, on_click=limpiar_formulario_venta)

        st.divider(); st.subheader("🧾 Historial Detallado por Cliente")
        cli_d = st.selectbox("Seleccione un cliente:", ["Seleccione..."] + listado_cli, key="cli_historial")
        if cli_d != "Seleccione...":
            cp = cli_d.split(" (")[0]; df_dc = pd.read_sql("SELECT id, fecha, diametro as Producto, cantidad_total as Cant, observaciones as Info, estado FROM pedidos WHERE cliente=? ORDER BY id DESC", conn, params=(cp,))
            if not df_dc.empty:
                st.dataframe(df_dc, use_container_width=True, hide_index=True)
                st.markdown("---"); st.subheader(f"🛠️ Editar/Borrar Pedido de {cp}")
                with st.form("f_edit_ped_cli"):
                    c1, c2, c3, c4, c5 = st.columns([1, 2, 2, 1, 1])
                    ivs = c1.selectbox("ID", df_dc['id'].tolist()); cln = c2.selectbox("Nuevo Cliente", listado_cli, index=listado_cli.index(cli_d)); prn = c3.selectbox("Nuevo Producto", listado_prod)
                    can = c4.number_input("Nueva Cant.", min_value=1, step=1, value=None, placeholder="0"); esn = c5.selectbox("Estado", ["Pendiente", "Entregado"])
                    b1, b2 = st.columns(2)
                    if b1.form_submit_button("✅ Actualizar"):
                        if ivs and can: conn.execute("UPDATE pedidos SET cliente=?, diametro=?, cantidad_total=?, estado=? WHERE id=?", (cln.split(" (")[0], prn, can, esn, ivs)); conn.commit(); st.success("Actualizado"); time.sleep(1); st.rerun()
                    if b2.form_submit_button("🗑️ Borrar"):
                        if ivs: conn.execute("DELETE FROM pedidos WHERE id=?", (ivs,)); conn.execute("DELETE FROM entregas WHERE pedido_id=?", (ivs,)); conn.commit(); st.warning("Eliminado"); time.sleep(1); st.rerun()

    elif opcion == menu[3]:
        st.header("🚚 Control de Despachos")
        df_p_pen = pd.read_sql("SELECT id, fecha, cliente, diametro, cantidad_total FROM pedidos WHERE estado != 'Entregado'", conn)
        df_ent = pd.read_sql("SELECT pedido_id, SUM(cantidad_entregada) as entregado FROM entregas GROUP BY pedido_id", conn)
        ped_p = pd.merge(df_p_pen, df_ent, left_on='id', right_on='pedido_id', how='left').fillna(0)
        ped_p['saldo'] = ped_p['cantidad_total'] - ped_p['entregado']
        ped_p = ped_p[ped_p['saldo'] > 0].copy()
        if not ped_p.empty:
            st.table(ped_p[['id', 'fecha', 'cliente', 'diametro', 'cantidad_total', 'saldo']])
            with st.form("f_desp"):
                c1, c2, c3 = st.columns(3); sel_p = c1.selectbox("Pedido", [f"ID {r['id']} - {r['cliente']} ({r['diametro']} | Saldo: {int(r['saldo'])})" for _, r in ped_p.iterrows()])
                c_d = c2.number_input("Cantidad", min_value=1, step=1, value=None, placeholder="0", key=f"c_desp_{st.session_state.k_desp}")
                f_d = c3.date_input("Fecha", obtener_fecha_ecuador())
                if st.form_submit_button("Registrar Despacho"):
                    if c_d:
                        pid = int(sel_p.split(" ")[1]); s_a = int(sel_p.split("Saldo: ")[1].replace(")", ""))
                        if c_d <= s_a:
                            conn.execute("INSERT INTO entregas (pedido_id, fecha, cantidad_entregada) VALUES (?,?,?)", (pid, str(f_d), c_d))
                            if c_d == s_a: conn.execute("UPDATE pedidos SET estado='Entregado' WHERE id=?", (pid,))
                            conn.commit(); st.session_state.k_desp += 1; st.success("✅ Despachado"); time.sleep(1); st.rerun()
                        else: st.error("❌ Excede saldo")
        else: st.info("✅ Todo despachado.")

        st.divider(); st.subheader("🔍 Historial y Edición de Despachos")
        df_hd = pd.read_sql('SELECT e.id, e.fecha, e.cantidad_entregada as Cant, p.cliente, p.diametro, e.pedido_id FROM entregas e JOIN pedidos p ON e.pedido_id = p.id ORDER BY e.id DESC', conn)
        if not df_hd.empty:
            st.dataframe(df_hd.drop(columns=['pedido_id']), use_container_width=True, hide_index=True)
            with st.form("f_edit_desp"):
                c1, c2, c3 = st.columns([1, 2, 2]); ids_e = c1.selectbox("ID Despacho", df_hd['id'].tolist())
                nf_e, nc_e = c2.date_input("Nueva Fecha"), c3.number_input("Nueva Cantidad", min_value=1, step=1, value=None, placeholder="0")
                b1, b2 = st.columns(2)
                if b1.form_submit_button("✅ Actualizar"):
                    if ids_e and nc_e:
                        ped_id = df_hd[df_hd['id'] == ids_e]['pedido_id'].iloc[0]; tot_p = conn.execute("SELECT cantidad_total FROM pedidos WHERE id=?", (int(ped_id),)).fetchone()[0]
                        ent_o = conn.execute("SELECT SUM(cantidad_entregada) FROM entregas WHERE pedido_id=? AND id!=?", (int(ped_id), int(ids_e))).fetchone()[0] or 0
                        if (ent_o + nc_e) <= tot_p:
                            conn.execute("UPDATE entregas SET fecha=?, cantidad_entregada=? WHERE id=?", (str(nf_e), nc_e, int(ids_e)))
                            conn.execute("UPDATE pedidos SET estado=? WHERE id=?", ('Entregado' if (ent_o + nc_e) == tot_p else 'Pendiente', int(ped_id)))
                            conn.commit(); st.success("✅ Actualizado"); time.sleep(1); st.rerun()
                        else: st.error("❌ Supera compra original")
                if b2.form_submit_button("🗑️ Borrar"):
                    if ids_e:
                        p_id = df_hd[df_hd['id'] == ids_e]['pedido_id'].iloc[0]; conn.execute("DELETE FROM entregas WHERE id=?", (int(ids_e),))
                        conn.execute("UPDATE pedidos SET estado='Pendiente' WHERE id=?", (int(p_id),)); conn.commit(); st.warning("Eliminado"); time.sleep(1); st.rerun()

    elif opcion == menu[4]:
        st.header("⚙️ Administración")
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
            with t2:
                df_cli = pd.read_sql("SELECT empresa, nombre, telefono FROM clientes ORDER BY nombre ASC", conn)
                st.dataframe(df_cli, use_container_width=True, hide_index=True)
                ca, ce, cb = st.columns(3)
                with ca:
                    with st.form("ac"):
                        e, n, t = st.text_input("Empresa"), st.text_input("Contacto"), st.text_input("Teléfono")
                        if st.form_submit_button("Guardar"): conn.execute("INSERT INTO clientes (empresa, nombre, telefono) VALUES (?,?,?)", (e,n,t)); conn.commit(); st.rerun()
                with ce:
                    if not df_cli.empty:
                        with st.form("ec"):
                            sel = st.selectbox("Elegir", df_cli['nombre'].tolist()); ne, nn, nt = st.text_input("Nueva Emp"), st.text_input("Nuevo Cont"), st.text_input("Nuevo Tel")
                            if st.form_submit_button("Actualizar"): conn.execute("UPDATE clientes SET empresa=?, nombre=?, telefono=? WHERE nombre=?", (ne, nn, nt, sel)); conn.commit(); st.rerun()
                with cb:
                    if not df_cli.empty:
                        with st.form("bc"):
                            sel = st.selectbox("Eliminar", df_cli['nombre'].tolist())
                            if st.form_submit_button("Borrar"): conn.execute("DELETE FROM clientes WHERE nombre=?", (sel,)); conn.commit(); st.rerun()
            with t3:
                n_iva = st.number_input("IVA (%)", value=float(VALOR_IVA)); 
                if st.button("Actualizar"): conn.execute("UPDATE configuracion SET valor=? WHERE parametro='iva'", (n_iva,)); conn.commit(); st.rerun()
    conn.close()