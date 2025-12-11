import streamlit as st
import pandas as pd
import json
from utils.db_con import get_data, save_data

def render_configurador():
    st.header("⚙️ Maestro de Clases y Características")
    st.markdown("Define las familias de componentes y sus fichas técnicas (Lógica SAP PM).")

    # Cargar DB
    df_config = get_data("familias_config")
    if df_config.empty or "nombre_familia" not in df_config.columns:
        df_config = pd.DataFrame(columns=["id", "nombre_familia", "config_json"])

    # --- SELECCIÓN O CREACIÓN DE FAMILIA ---
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("1. Clase / Familia")
        opciones_fam = df_config["nombre_familia"].tolist()
        accion = st.radio("Acción:", ["Editar Existente", "Crear Nueva"], horizontal=True)
        
        nombre_familia = ""
        familia_idx = None
        
        if accion == "Editar Existente":
            if opciones_fam:
                nombre_familia = st.selectbox("Seleccionar Clase", opciones_fam)
                if not df_config.empty:
                    try:
                        familia_idx = df_config[df_config["nombre_familia"] == nombre_familia].index[0]
                    except: pass
            else:
                st.warning("No existen familias. Crea una.")
        else:
            nombre_familia = st.text_input("Nombre Nueva Clase", placeholder="Ej: Motor Trifásico").strip().upper()

    # --- DEFINICIÓN DE CARACTERÍSTICAS (CAMPOS) ---
    if nombre_familia:
        with col2:
            st.subheader(f"2. Características de: {nombre_familia}")
            st.info("Agrega los campos técnicos que debe tener esta familia.")

            # Inicializar estado temporal si cambiamos de familia
            if "last_fam_config" not in st.session_state or st.session_state["last_fam_config"] != nombre_familia:
                st.session_state["last_fam_config"] = nombre_familia
                st.session_state["campos_temp"] = []
                
                # Si editamos, cargamos lo existente
                if accion == "Editar Existente" and familia_idx is not None:
                    json_data = df_config.at[familia_idx, "config_json"]
                    if json_data:
                        try: st.session_state["campos_temp"] = json.loads(json_data)
                        except: pass

            # --- EDITOR DE CAMPOS ---
            # Mostramos lista actual
            campos_actuales = st.session_state["campos_temp"]
            
            if campos_actuales:
                for i, campo in enumerate(campos_actuales):
                    c1, c2, c3 = st.columns([3, 2, 1])
                    c1.text(f"📝 {campo['nombre']}")
                    c2.caption(f"Unidad: {campo.get('unidad', '-')}")
                    if c3.button("❌", key=f"del_{i}"):
                        campos_actuales.pop(i)
                        st.rerun()
            else:
                st.caption("Sin características definidas.")

            st.markdown("---")
            # Formulario para agregar nuevo campo
            with st.form("add_field"):
                c_new1, c_new2 = st.columns([3, 2])
                new_nom = c_new1.text_input("Nombre Característica", placeholder="Ej: Potencia")
                new_uni = c_new2.text_input("Unidad Medida", placeholder="Ej: HP / KW")
                
                if st.form_submit_button("➕ Agregar Característica"):
                    if new_nom:
                        st.session_state["campos_temp"].append({
                            "nombre": new_nom,
                            "unidad": new_uni
                        })
                        st.rerun()

            st.divider()
            
            # --- GUARDAR EN BASE DE DATOS ---
            if st.button("💾 GUARDAR CONFIGURACIÓN MAESTRA", type="primary"):
                json_final = json.dumps(st.session_state["campos_temp"])
                
                if accion == "Crear Nueva":
                    if nombre_familia in opciones_fam:
                        st.error("Esa familia ya existe.")
                    else:
                        new_id = 1
                        if not df_config.empty and 'id' in df_config:
                             try: new_id = int(pd.to_numeric(df_config['id']).max()) + 1
                             except: new_id = len(df_config) + 1
                        
                        new_row = pd.DataFrame([{
                            "id": new_id,
                            "nombre_familia": nombre_familia,
                            "config_json": json_final
                        }])
                        save_data(pd.concat([df_config, new_row], ignore_index=True), "familias_config")
                        st.success(f"Familia {nombre_familia} creada.")
                        st.rerun()
                else:
                    # Actualizar
                    if familia_idx is not None:
                        df_config.at[familia_idx, "config_json"] = json_final
                        save_data(df_config, "familias_config")
                        st.success("Configuración actualizada.")
