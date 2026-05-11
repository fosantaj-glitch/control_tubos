import streamlit as st

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Control de Tubos - Inventario", layout="wide")

# --- SISTEMA DE SEGURIDAD Y BLOQUEO ---
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False

def login():
    """Muestra la pantalla de ingreso de clave"""
    if not st.session_state.autenticado:
        st.title("🏭 Sistema de Control de Tubos")
        st.subheader("Acceso Restringido")
        
        # Cuadro para ingresar la clave
        clave = st.text_input("Ingrese la clave de acceso", type="password")
        
        # Botón para verificar
        if st.button("Entrar", type="primary"):
            if clave == "Tubos2026":
                st.session_state.autenticado = True
                st.rerun() # Recarga la pantalla para quitar el candado
            else:
                st.error("❌ Clave incorrecta. Inténtelo de nuevo.")
        return False
    return True

# --- FLUJO PRINCIPAL DE LA APLICACIÓN ---
if login():
    # Todo lo que esté aquí abajo solo se verá si la clave fue correcta
    st.sidebar.title("🏭 Menú Principal")
    st.sidebar.success("✅ Sesión iniciada correctamente")
    
    # Botón para salir y volver a bloquear la pantalla
    if st.sidebar.button("Cerrar Sesión"):
        st.session_state.autenticado = False
        st.rerun()
        
    st.title("Bienvenido al Sistema")
    st.info("La puerta de entrada está lista. El sistema está esperando que agreguemos las opciones de inventario y pedidos.")