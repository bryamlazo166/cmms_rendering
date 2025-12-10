import streamlit as st
# Ahora sí funcionará porque existen los 3 archivos
from modules import gestion_activos, almacen, monitoreo

st.set_page_config(page_title="CMMS Rendering", layout="wide", page_icon="🏭")
st.sidebar.image("https://cdn-icons-png.flaticon.com/512/900/900782.png", width=50)
st.sidebar.title("CMMS Rendering")

# Menú Principal
menu = ["Gestión de Activos (Arbol)", "Almacén de Repuestos", "Monitoreo Predictivo"]
opcion = st.sidebar.radio("Ir a:", menu)

if opcion == "Gestión de Activos (Arbol)":
    gestion_activos.render_gestion_activos()

elif opcion == "Almacén de Repuestos":
    almacen.render_almacen_view()

elif opcion == "Monitoreo Predictivo":
    monitoreo.render_monitoreo_view()
