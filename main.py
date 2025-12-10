import streamlit as st
from modules import gestion_activos, almacen, monitoreo

st.set_page_config(page_title="CMMS Rendering", layout="wide", page_icon="🏭")
st.sidebar.title("CMMS Rendering")

menu = ["Gestión de Activos (Arbol)", "Almacén de Repuestos", "Monitoreo Predictivo"]
opcion = st.sidebar.radio("Navegación:", menu)

if opcion == "Gestión de Activos (Arbol)":
    gestion_activos.render_gestion_activos()

elif opcion == "Almacén de Repuestos":
    almacen.render_almacen_view()

elif opcion == "Monitoreo Predictivo":
    monitoreo.render_monitoreo_view()
