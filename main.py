import streamlit as st
# Importamos los módulos que acabamos de crear
from modules import equipos, componentes

st.set_page_config(page_title="CMMS Rendering", layout="wide", page_icon="🏭")

st.title("🏭 CMMS Planta Rendering")
st.sidebar.title("Menú Principal")

# El menú decide qué módulo cargar
opcion = st.sidebar.radio("Ir a:", ["Maestro de Equipos", "Componentes & Specs"])

if opcion == "Maestro de Equipos":
    # Llamamos a la FUNCIÓN, no escribimos todo el código aquí
    equipos.render_equipos_view()

elif opcion == "Componentes & Specs":
    componentes.render_componentes_view()

# Aquí agregaremos en el futuro:
# elif opcion == "Almacén":
#     almacen.render_almacen_view()
