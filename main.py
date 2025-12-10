import streamlit as st
# Agregamos la importación de almacen
from modules import equipos, componentes, almacen

st.set_page_config(page_title="CMMS Rendering", layout="wide", page_icon="🏭")
st.title("🏭 CMMS Planta Rendering")

# Menú actualizado
menu = ["Maestro de Equipos", "Componentes & Specs", "Almacén de Repuestos"]
opcion = st.sidebar.radio("Ir a:", menu)

if opcion == "Maestro de Equipos":
    equipos.render_equipos_view()

elif opcion == "Componentes & Specs":
    componentes.render_componentes_view()

elif opcion == "Almacén de Repuestos":
    almacen.render_almacen_view()
