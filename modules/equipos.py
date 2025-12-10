import streamlit as st
import pandas as pd
from utils.db_con import get_data, save_data

def render_equipos_view():
    st.header("1. Registro de Equipos Principales")
    st.info("Catálogo Maestro: Digestores, Prensas, Molinos")
    
    # Formulario para agregar equipos
    with st.form("form_equipo"):
        c1, c2 = st.columns(2)
        tag = c1.text_input("TAG (Ej: DIG-01)").strip().upper()
        nombre = c2.text_input("Nombre del Equipo")
        
        area = c1.selectbox("Área", ["Recepcion", "Coccion", "Prensado", "Molienda", "Servicios"])
        tipo = c2.selectbox("Tipo", ["Digestor", "Prensa Tornillo", "Centrifuga", "Molino", "Transportador", "Caldera"])
        crit = st.select_slider("Criticidad", ["Baja", "Media", "Alta"])
        
        submitted = st.form_submit_button("Guardar Equipo")
        
        if submitted:
            if not tag or not nombre:
                st.error("❌ El TAG y el Nombre son obligatorios.")
            else:
                # 1. Obtener datos actuales
                df_equipos = get_data("equipos")
                
                # 2. Validar duplicados de TAG
                if not df_equipos.empty and tag in df_equipos['tag'].values:
                    st.error(f"⚠️ El TAG '{tag}' ya existe.")
                else:
                    # 3. Generar ID
                    new_id = 1 if df_equipos.empty else df_equipos['id'].max() + 1
                    
                    # 4. Crear fila nueva
                    new_row = pd.DataFrame([{
                        "id": new_id, 
                        "tag": tag, 
                        "nombre": nombre, 
                        "area": area, 
                        "tipo": tipo, 
                        "criticidad": crit, 
                        "estado": "Operativo"
                    }])
                    
                    # 5. Guardar
                    df_updated = pd.concat([df_equipos, new_row], ignore_index=True)
                    save_data(df_updated, "equipos")
                    st.success(f"✅ Equipo {tag} guardado correctamente.")
                    st.cache_data.clear()

    st.divider()
    
    # Tabla visual para ver lo que has creado
    st.subheader("Listado de Equipos")
    df_show = get_data("equipos")
    if not df_show.empty:
        st.dataframe(df_show, use_container_width=True)
    else:
        st.info("Aún no hay equipos registrados.")
