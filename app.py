importar streamlit como st
importar pandas como pd
importar sqlite3
solicitudes de importación
from datetime import datetime, date, timezone, timedelta
hora de importación
importar sistema operativo

# --- 1. CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(
    page_title="Control de Tubos - GUILLÉN",
    page_icon="🏭",
    diseño="ancho",
    initial_sidebar_state="expanded"
)

# --- 2. DISEÑO VISUAL (DEGRADADO DIAGONAL) ---
st.markdown(
    """
    <style>
    .stApp {
        fondo: gradiente lineal(135 grados, #ced4da 0%, #e9ecef 40%, #ffffff 100%);
        adjunto de fondo: fijo;
    }
    [data-testid="stSidebar"] {
        color de fondo: #212529;
        color: blanco !importante;
    }
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
        color: blanco !importante;
    }
    div[role="radiogroup"] label {
        color: blanco !importante;
        color de fondo: rgba(255, 255, 255, 0.05);
        margen inferior: 5px;
        radio de borde: 5px;
        relleno: 10px;
    }
    [data-testid="stHeader"], .stForm, .stDataFrame {
        color de fondo: blanco;
        radio de borde: 12px;
        relleno: 20px;
        box-shadow: 5px 5px 15px rgba(0,0,0,0.05);
    }
    [data-testid="stSidebar"] img {
        radio de borde: 10px;
        borde: 2px sólido #ffffff40;
        margen inferior: 20px;
    }
    </style>
    """,
    unsafe_allow_html=Verdadero
)

URL_GOOGLE = "https://script.google.com/macros/s/AKfycbw2YUNMCJB0fDNZ1jCWFmcgXv5VABsCXvAi6rsUXAVnlsUaQB2kgBvZCuBxEFVMOOL1/exec"

# --- 3. SISTEMA DE SEGURIDAD ---
Si "autenticado" no está en st.session_state:
    st.session_state.autenticado = Falso
Si "config_autenticado" no está en st.session_state:
    st.session_state.config_autenticado = Falso

NOMBRE_LOGO = "logo.jpg"

def login():
    si no st.session_state.autenticado:
        c1, c2, c3 = st.columns([1, 2, 1])
        con c2:
            st.markdown("<br><br>", unsafe_allow_html=True)
            try: st.image(NOMBRE_LOGO, use_container_width=True)
            excepto: pasar
            st.title("🏭 Inventario GUILLÉN")
            st.subheader("Acceso al Sistema")
            clave = st.text_input("Contraseña", type="password", key="main_login")
            if st.button("Ingresar", type="primary", use_container_width=True):
                if clave == "Tubos2026":
                    st.session_state.autenticado = Verdadero
                    st.rerun()
                demás:
                    st.error("❌ Clave incorrecta")
        devolver Falso
    devolver verdadero

# --- 4. BASE DE DATOS ---
def obtener_fecha_ecuador():
    tz_ecuador = zona horaria(delta_tiempo(horas=-5))
    return datetime.now(tz_ecuador).date()

def obtener_conexión():
    return sqlite3.connect('control_tubos_db.db', check_same_thread=False)

def init_db():
    conn = obtener_conexión()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS producción (id INTEGER PRIMARY KEY AUTOINCREMENT, fecha TEXT, diametro TEXT, cantidad INTEGER)''')
    c.execute('''CREAR TABLA SI NO EXISTE pedidos (id INTEGER PRIMARY KEY AUTOINCREMENT, fecha TEXTO, cliente TEXTO, diámetro TEXTO, cantidad_total INTEGER, estado TEXTO, observaciones TEXTO)'')
    c.execute('''CREAR TABLA SI NO EXISTE entregas (id INTEGER PRIMARY KEY AUTOINCREMENT, pedido_id INTEGER, fecha TEXT, cantidad_entregada INTEGER, FOREIGN KEY(pedido_id) REFERENCIAS pedidos(id))''')
    c.execute('''CREATE TABLE IF NOT EXISTS diametros (id INTEGER PRIMARY KEY AUTOINCREMENT, medida TEXT, tipo TEXT, precio REAL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS clientes (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, telefono TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS configuración (id INTEGER PRIMARY KEY, parámetro TEXT, valor REAL)''')
    
    if conn.execute("SELECT COUNT(*) FROM configuracion WHERE parametro='iva'").fetchone()[0] == 0:
        conn.execute("INSERT INTO configuracion (parámetro, valor) VALUES ('iva', 15.0)")

    if conn.execute("SELECT COUNT(*) FROM diametros").fetchone()[0] == 0:
        iniciales = [("500 mm", "Estandar", 0.0), ("600 mm", "Estandar", 0.0), ("700 mm", "Estandar", 0.0)]
        c.executemany("INSERT INTO diametros (medida, tipo, precio) VALUES (?,?,?)", iniciales)
    
    conn.commit()
    conexión.close()

init_db()

def obtener_iva():
    conn = obtener_conexión()
    res = conn.execute("SELECT valor FROM configuración WHERE parametro='iva'").fetchone()
    conexión.close()
    Devuelve res[0] si res, de lo contrario 15.0

def obtener_diametros():
    """Obtiene la lista ordenada de menor a mayor (500, 600, 700...)"""
    conn = obtener_conexión()
    df = pd.read_sql("SELECT medida, tipo FROM diametros", conn)
    conexión.close()
    si df no está vacío:
        df['num'] = df['medida'].str.extract('(\d+)').astype(float)
        df = df.sort_values('num', ascending=True)
        return ["Seleccione..."] + [f"{r['medida']} ({r['tipo']})" if r['tipo'] else r['medida'] for _, r in df.iterrows()]
    devolver ["Seleccione..."]

def obtener_clientes():
    conn = obtener_conexión()
    df = pd.read_sql("SELECT nombre FROM clientes ORDER BY nombre ASC", conn)
    conexión.close()
    return ["Seleccione Cliente..."] + df['nombre'].tolist()

# --- 5. CUERPO DE LA APP ---
si login():
    try: st.sidebar.image(NOMBRE_LOGO, use_container_width=True)
    excepto: st.sidebar.title("GUILLÉN")

    if st.sidebar.button("Cerrar Sesión"):
        st.session_state.autenticado = Falso
        st.session_state.config_autenticado = Falso
        st.rerun()
    
    barra lateral.divider()
    OPCION_RESUMEN, OPCION_PROD, OPCION_PEDIDOS, OPCION_DESPACHOS, OPCION_CONFIG = "📊 Resumen de Patio", "🧱 Fabricación Diaria", "📝 Pedidos y Ventas", "🚚 Despachos", "⚙️ Configuración"
    menu = st.sidebar.radio("MENÚ PRINCIPAL", [OPCION_RESUMEN, OPCION_PROD, OPCION_PEDIDOS, OPCION_DESPACHOS, OPCION_CONFIG])

    Si menu != OPCION_CONFIG: st.session_state.config_autenticado = False

    DIAM_DB = obtener_diametros()
    CLI_DB = obtener_clientes()
    VALOR_IVA = obtener_iva()

    si menu == OPCION_RESUMEN:
        st.header("📊 Estado Actual del Inventario")
        st.info("Aquí aparecerá el resumen de tubos disponibles próximamente.")

    elif menu == OPCION_PROD:
        st.header("🧱 Registro de Producción")
        con st.form("f_prod"):
            c1, c2, c3 = st.columns(3)
            f_p = c1.date_input("Fecha", obtener_fecha_ecuador())
            d_p = c2.selectbox("Tubo (Medida y Tipo)", DIAM_DB)
            n_p = c3.number_input("Cantidad", min_value=1, paso=1, valor=Ninguno, placeholder="Escribe cantidad...")
            if st.form_submit_button("Guardar Fabricación", type="primary"):
                si d_p != "Seleccione..." y n_p:
                    conn = get_connection(); conn.execute("INSERT INTO producción (fecha, diametro, cantidad) VALUES (?,?,?)", (f_p.strftime("%Y-%m-%d"), d_p, n_p)); conn.commit(); conn.close()
                    st.success("✅ Datos guardados"); time.sleep(1); st.rerun()
                else: st.error("Complete los campos obligatorios.")

    elif menu == OPCION_PEDIDOS:
        st.header("📝 Registro de Pedidos")
        con st.form("f_ped"):
            c1, c2 = st.columns(2)
            f_v = c1.date_input("Fecha", obtener_fecha_ecuador())
            cl_v = c2.selectbox("Cliente", CLI_DB)
            c3, c4 = st.columns(2)
            di_v = c3.selectbox("Tubo", DIAM_DB)
            ca_v = c4.number_input("Cantidad Solicitada", min_value=1, step=1, value=None, placeholder="Escribe cantidad...")
            ob = st.text_area("Notas del Pedido")
            if st.form_submit_button("Crear Pedido", type="primary"):
                if di_v != "Seleccione..." y cl_v != "Seleccione Cliente..." y ca_v:
                    conexión = get_connection(); conn.execute("INSERT INTO pedidos (fecha, cliente, diametro, cantidad_total, estado, observaciones) VALUES (?,?,?,?,?,?)", (f_v.strftime("%Y-%m-%d"), cl_v, di_v, ca_v, "Pendiente", ob)); conexión.commit(); conexión.cerrar()
                    st.success("✅ Pedido registrado"); time.sleep(1); st.rerun()
                else: st.error("Complete los campos obligatorios.")

    menú elif == OPCION_DESPACHOS:
        st.header("🚚 Control de Entregas")
        st.info("Módulo para despachar tubos por camión próximamente.")

    elif menu == OPCION_CONFIG:
        st.header("⚙️ Administración de Datos")
        Si no se ha autenticado st.session_state.config:
            con st.form("admin_lock"):
                cl_adm = st.text_input("Clave de Administrador", type="password")
                if st.form_submit_button("Desbloquear"):
                    si cl_adm == "Tubos2026":
                        st.session_state.config_autenticado = True; st.rerun()
                    else: st.error("Clave incorrecta")
        demás:
            st.success("🔓 Acceso de Administrador concedido")
            t1, t2, t3 = st.tabs(["📏 Diámetros y Precios", "👥 Clientes", "💰 Impuestos"])
            
            con t1:
                conn = obtener_conexión()
                df_d = pd.read_sql("SELECT id, medida como Medida, tipo como Tipo, precio como [Valor Unitario] FROM diametros", conn)
                si no df_d.empty:
                    # Ordenar de menor a mayor (Ej. 500, 600, 700)
                    df_d['num_sort'] = df_d['Medida'].str.extract('(\d+)').astype(float)
                    df_d = df_d.sort_values('num_sort', ascending=True)
                    
                    df_d['Precio más IVA'] = df_d['Valor Unitario'] * (1 + (VALOR_IVA / 100))
                    df_v = df_d.copy()
                    df_v['Valor Unitario'] = df_v['Valor Unitario'].apply(lambda x: f"${x:.2f}")
                    df_v['Precio más IVA'] = df_v['Precio más IVA'].apply(lambda x: f"${x:.2f}")
                    st.write(f"**Catálogo de Productos (Ordenado por diámetro - IVA: {VALOR_IVA}%)**")
                    st.dataframe(df_v.drop(columns=['id', 'num_sort']), use_container_width=True, hide_index=True)
                
                c_a, c_e, c_b = st.columns(3)
                con c_a:
                    con st.form("a_d", clear_on_submit=True):
                        st.write("**Nuevo Producto**")
                        n_m, n_t = st.text_input("Medida"), st.text_input("Tipo")
                        n_pr = st.number_input("Valor Unitario", min_value=0.0, value=None, placeholder="0.00")
                        Si st.form_submit_button("Guardar"):
                            Si n_m y n_pr no son None:
                                conn.execute("INSERT INTO diametros (medida, tipo, precio) VALUES (?,?,?)", (n_m, n_t, n_pr)); conn.commit(); st.rerun()
                con c_e:
                    si no df_d.empty:
                        con st.form("e_d"):
                            st.write("**Editar Producto**")
                            opciones_ed = df_d['Medida'].tolist()
                            sel = st.selectbox("Elegir Medida", opciones_ed)
                            new_m, new_t = st.text_input("Nuevo Nombre Medida"), st.text_input("Nuevo Tipo")
                            new_p = st.number_input("Nuevo Valor Unitario", min_value=0.0, value=None, placeholder="0.00")
                            si st.form_submit_button("Actualizar"):
                                Si new_m y new_p no son None:
                                    conn.execute("ACTUALIZAR diámetros SET medida=?, tipo=?, precio=? WHERE medida=?", (new_m, new_t, new_p, sel))
                                    conn.execute("UPDATE procion SET diametro=? WHERE diametro LIKE ?", (f"{new_m}%", f"{sel}%"))
                                    conn.execute("UPDATE pedidos SET diametro=? WHERE diametro LIKE ?", (f"{new_m}%", f"{sel}%"))
                                    conn.commit(); st.rerun()
                con c_b:
                    si no df_d.empty:
                        con st.form("b_d"):
                            st.write("**Borrar**")
                            del_s = st.selectbox("Eliminar", df_d['Medida'].tolist())
                            Si st.form_submit_button("Borrar"):
                                conn.execute("DELETE FROM diametros WHERE medida=?", (del_s,)); conn.commit(); st.rerun()
                conexión.close()

            con t2:
                conn = obtener_conexión()
                df_c = pd.read_sql("SELECT id, nombre as Nombre, telefono as Telefono FROM clientes ORDER BY nombre ASC", conn)
                st.write("**Directorio de Clientes**")
                st.dataframe(df_c.drop(columns=['id']), use_container_width=True, hide_index=True)
                c1, c2, c3 = st.columns(3)
                con c1:
                    con st.form("a_c", clear_on_submit=True):
                        st.write("**Registrador**")
                        nn, nt = st.text_input("Nombre/Empresa"), st.text_input("Teléfono")
                        Si st.form_submit_button("Guardar"):
                            if nn: conn.execute("INSERT INTO clientes (nombre, telefono) VALUES (?,?)", (nn, nt)); conn.commit(); st.rerun()
                con c2:
                    si no df_c.empty:
                        con st.form("e_c"):
                            st.write("**Corregir**")
                            sel_c = st.selectbox("Elegir Cliente", df_c['Nombre'].tolist())
                            new_n, new_t = st.text_input("Nombre Correcto"), st.text_input("Teléfono Correcto")
                            si st.form_submit_button("Actualizar"):
                                si new_n:
                                    conn.execute("ACTUALIZAR clientes SET nombre=?, telefono=? WHERE nombre=?", (new_n, new_t, sel_c))
                                    conn.execute("ACTUALIZAR pedidos SET cliente=? DONDE cliente=?", (new_n, sel_c))
                                    conn.commit(); st.rerun()
                con c3:
                    si no df_c.empty:
                        con st.form("b_c"):
                            st.write("**Borrar**")
                            del_c = st.selectbox("Eliminar Cliente", df_c['Nombre'].tolist())
                            Si st.form_submit_button("Borrar"):
                                conn.execute("DELETE FROM clientes WHERE nombre=?", (del_c,)); conn.commit(); st.rerun()
                conexión.close()

            con t3:
                st.write("**Configuración de IVA**")
                st.info(f"IVA real: **{VALOR_IVA}%**")
                con st.form("f_iva"):
                    n_iva = st.number_input("Nuevo IVA (%)", min_value=0.0, max_value=100.0, value=float(VALOR_IVA), step=1.0)
                    si st.form_submit_button("Actualizar"):
                        conn = obtener_conexión()
                        conn.execute("ACTUALIZAR configuracion SET valor=? WHERE parametro='iva'", (n_iva,))
                        conn.commit(); conn.close(); st.success("IVA actualizado"); time.sleep(1); st.rerun()
