import streamlit as st
import pandas as pd
import json
from utils.db_con import get_data, save_data

def render_configurador():
    st.header("🛠️ Constructor de Familias de Componentes")
    st.markdown("Define qué datos necesitas pedir para cada tipo de componente.")

    # Cargar configuraciones existentes
    df_config = get_data("familias_config")
    if df_config.empty:
        df_config = pd.DataFrame(columns=["id", "nombre_familia", "config_json"])

    # --- SECCIÓN 1: CREAR O EDITAR FAMILIA ---
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("1. Seleccionar Familia")
        familias_existentes = df_config["nombre_familia"].tolist()
        modo = st.radio("Acción:", ["Editar Existente", "Crear Nueva"], horizontal=True)
        
        nombre_familia = ""
        if modo == "Editar Existente":
            if familias_existentes:
                nombre_familia = st.selectbox("Selecciona:", familias_existentes)
            else:
                st.warning("No hay familias creadas.")
        else:
            nombre_familia = st.text_input("Nombre de la Nueva Familia", placeholder="Ej: Válvula Solenoide").strip()

    # --- SECCIÓN 2: DEFINIR CAMPOS ---
    if nombre_familia:
        with col2:
            st.subheader(f"2. Definir Campos para: {nombre_familia}")
            
            # Recuperar campos si ya existen
            campos_actuales = []
            idx_edit = None
            
            if modo == "Editar Existente" and not df_config.empty:
                row = df_config[df_config["nombre_familia"] == nombre_familia]
                if not row.empty:
                    try:
                        campos_actuales = json.loads(row.iloc[0]["config_json"])
                        idx_edit = row.index[0]
                    except: pass

            # Editor de Lista de Campos (Usamos Session State para temporalidad)
            if "temp_campos" not in st.session_state or st.session_state.get("last_fam") != nombre_familia:
                st.session_state["temp_campos"] = campos_actuales
                st.session_state["last_fam"] = nombre_familia

            # Mostrar campos actuales
            st.write("Variables que se pedirán al técnico:")
            
            # Tabla editable pequeña
            lista_editada = []
            for i, campo in enumerate(st.session_state["temp_campos"]):
                c_nom, c_del = st.columns([4, 1])
                new_nom = c_nom.text_input(f"Campo {i+1}", value=campo['nombre'], key=f"c_{i}")
                if not c_del.button("🗑️", key=f"del_{i}"):
                    lista_editada.append({"nombre": new_nom})
            
            st.session_state["temp_campos"] = lista_editada

            # Agregar nuevo campo
            c_new, c_btn = st.columns([4, 1])
            nuevo_campo = c_new.text_input("Agregar Nuevo Campo", placeholder="Ej: Amperaje Nominal", key="new_input_field")
            if c_btn.button("➕"):
                if nuevo_campo:
                    st.session_state["temp_campos"].append({"nombre": nuevo_campo})
                    st.rerun()

            st.divider()
            
            if st.button("💾 GUARDAR CONFIGURACIÓN DE FAMILIA", type="primary"):
                json_str = json.dumps(st.session_state["temp_campos"])
                
                if modo == "Crear Nueva":
                    # Validar duplicado
                    if nombre_familia in familias_existentes:
                        st.error("Ya existe una familia con ese nombre.")
                    else:
                        new_id = 1 if df_config.empty else df_config['id'].max() + 1
                        new_row = pd.DataFrame([{"id": new_id, "nombre_familia": nombre_familia, "config_json": json_str}])
                        save_data(pd.concat([df_config, new_row], ignore_index=True), "familias_config")
                        st.success(f"Familia '{nombre_familia}' creada con éxito.")
                        st.rerun()
                else:
                    # Actualizar
                    df_config.at[idx_edit, "config_json"] = json_str
                    save_data(df_config, "familias_config")
                    st.success("Configuración actualizada.")
