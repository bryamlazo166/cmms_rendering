import streamlit as st
import pandas as pd
from utils.db_con import get_data, save_data

def render_equipos_view():
    st.header("🏭 Maestro de Equipos (Niveles 1-3)")
    st.markdown("Jerarquía: **Planta** ➝ **Área** ➝ **Equipo**")
    
    with st.form("form_equipo"):
        c1, c2 = st.columns(2)
        # Nivel 1 y 2
        planta = c1.selectbox("Planta", ["Planta Principal", "Planta Harinas", "Tratamiento Aguas"])
        area = c2.selectbox("Área", ["Recepcion", "Coccion", "Prensado", "Molienda", "Servicios", "Despacho"])
        
        # Nivel 3
        c3, c4 = st.columns(2)
        tag = c3.text_input("TAG Técnico (Único)", placeholder="Ej: DIG-01").strip().upper()
        nombre = c4.text_input("Nombre del Equipo", placeholder="Ej: Digestor Continuo 1")
        
        c5, c6 = st.columns(2)
        tipo = c5.selectbox("Tipo de Equipo", ["Digestor", "Prensa", "Molino", "Caldera", "Centrifuga", "Transportador"])
        crit = c6.select_slider("Criticidad", ["Baja", "Media", "Alta"])
        
        if st.form_submit_button("Guardar Equipo"):
            if not tag or not nombre:
                st.error("❌ Tag y Nombre son obligatorios")
            else:
                df = get_data("equipos")
                if not df.empty and tag in df['tag'].values:
                    st.error("⚠️ Ese TAG ya existe.")
                else:
                    new_id = 1 if df.empty else df['id'].max() + 1
                    new_row = pd.DataFrame([{
                        "id": new_id, "tag": tag, "nombre": nombre,
                        "planta": planta, "area": area, 
                        "tipo": tipo, "criticidad": crit, "estado": "Operativo"
                    }])
                    save_data(pd.concat([df, new_row], ignore_index=True), "equipos")
                    st.success(f"✅ Equipo '{nombre}' registrado en {area}.")
                    st.cache_data.clear()

    # Visualización mejorada
    st.divider()
    st.subheader("Listado de Activos")
    df_show = get_data("equipos")
    if not df_show.empty:
        # Ordenar columnas para ver primero lo importante
        st.dataframe(
            df_show[["planta", "area", "tag", "nombre", "tipo", "criticidad"]], 
            use_container_width=True
        )
