import streamlit as st
from modules import gestion_activos, almacen, monitoreo, configurador

st.set_page_config(page_title="CMMS SAP-Style", layout="wide", page_icon="🏭")
st.sidebar.title("CMMS Rendering")

menu = ["Gestión de Activos", "Maestro de Clases", "Almacén", "Monitoreo"]
opcion = st.sidebar.radio("Ir a:", menu)

if opcion == "Gestión de Activos":
    gestion_activos.render_gestion_activos()
elif opcion == "Maestro de Clases":
    configurador.render_configurador()
elif opcion == "Almacén":
    almacen.render_almacen_view()
elif opcion == "Monitoreo":
    monitoreo.render_monitoreo_view()
