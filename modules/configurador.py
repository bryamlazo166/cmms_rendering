import streamlit as st
import pandas as pd
import json
from utils.db_con import get_data, save_data

def render_configurador():
    st.header("⚙️ Maestros de Configuración")
    st.markdown("Define los estándares para Sistemas y Componentes.")

    tab_comp, tab_sys = st.tabs(["🔩 Maestro de Componentes (Familias)", "🎛️ Maestro de Sistemas"])

    # ==========================================
    # TAB 1: MAESTRO DE COMPONENTES (FAMILIAS)
    # ==========================================
    with tab_comp:
        df_config = get_data("familias_config")
        if df_config.empty or "nombre_familia" not in df_config.columns:
            df_config = pd.DataFrame(columns=["id", "nombre_familia", "config_json"])

        c1, c2 = st.columns([1, 2])
        with c1:
            st.subheader("1. Clase / Familia")
            opciones_fam = df_config["nombre_familia"].tolist()
            accion = st.radio("Acción:", ["Editar Existente", "Crear Nueva"], horizontal=True, key="rad_fam")
            
            nombre_familia = ""
            familia_idx = None
            
            if accion == "Editar Existente":
                if opciones_fam:
                    nombre_familia = st.selectbox("Seleccionar Clase", opciones_fam, key="sel_fam_exist")
                    if not df_config.empty:
                        try: familia_idx = df_config[df_config["nombre_familia"] == nombre_familia].index[0]
                        except: pass
                else: st.warning("Lista vacía.")
            else:
                nombre_familia = st.text_input("Nombre Nueva Clase", placeholder="Ej: MOTOR AC").strip().upper()

        if nombre_familia:
            with c2:
                st.subheader(f"2. Variables de: {nombre_familia}")
                # Lógica de memoria temporal
                if "last_fam" not in st.session_state or st.session_state["last_fam"] != nombre_familia:
                    st.session_state["last_fam"] = nombre_familia
                    st.session_state["campos_temp"] = []
                    if accion == "Editar Existente" and familia_idx is not None:
                        json_data = df_config.at[familia_idx, "config_json"]
                        if json_data:
                            try: st.session_state["campos_temp"] = json.loads(json_data)
                            except: pass

                # Editor visual
                campos = st.session_state["campos_temp"]
                if campos:
                    for i, cp in enumerate(campos):
                        ca, cb, cc = st.columns([3, 2, 1])
                        ca.text(f"📝 {cp['nombre']}")
                        cb.caption(f"Unidad: {cp.get('unidad','-')}")
                        if cc.button("🗑️", key=f"del_c_{i}"):
                            campos.pop(i); st.rerun()
                else: st.info("Sin variables definidas.")

                with st.form("add_field"):
                    n1, n2 = st.columns([2,1])
                    v_nom = n1.text_input("Nombre Variable", placeholder="Ej: Potencia")
                    v_uni = n2.text_input("Unidad", placeholder="HP")
                    if st.form_submit_button("Agregar"):
                        if v_nom: 
                            st.session_state["campos_temp"].append({"nombre": v_nom, "unidad": v_uni})
                            st.rerun()
                
                if st.button("💾 Guardar Familia", type="primary"):
                    js_final = json.dumps(st.session_state["campos_temp"])
                    if accion == "Crear Nueva":
                        if nombre_familia in opciones_fam: st.error("Ya existe.")
                        else:
                            nid = 1 if df_config.empty else (pd.to_numeric(df_config['id'], errors='coerce').max() or 0) + 1
                            row = pd.DataFrame([{"id": nid, "nombre_familia": nombre_familia, "config_json": js_final}])
                            save_data(pd.concat([df_config, row], ignore_index=True), "familias_config")
                            st.success("Creado!"); st.rerun()
                    else:
                        df_config.at[familia_idx, "config_json"] = js_final
                        save_data(df_config, "familias_config")
                        st.success("Actualizado!")

    # ==========================================
    # TAB 2: MAESTRO DE SISTEMAS (NUEVO)
    # ==========================================
    with tab_sys:
        st.subheader("Catálogo de Sistemas Estándar")
        st.info("Define los tipos de sistemas que usas en planta para estandarizar nombres.")
        
        df_sys_conf = get_data("sistemas_config")
        if df_sys_conf.empty: df_sys_conf = pd.DataFrame(columns=["id", "nombre_sistema", "descripcion"])

        # Mostrar tabla actual
        if not df_sys_conf.empty:
            st.dataframe(df_sys_conf[["nombre_sistema", "descripcion"]], use_container_width=True, hide_index=True)
        
        st.divider()
        with st.form("add_sys_conf"):
            c_s1, c_s2 = st.columns(2)
            new_sys_name = c_s1.text_input("Nombre del Sistema", placeholder="Ej: SISTEMA HIDRAULICO").strip().upper()
            new_sys_desc = c_s2.text_input("Descripción", placeholder="Opcional")
            
            if st.form_submit_button("Guardar Nuevo Tipo de Sistema"):
                if new_sys_name:
                    if not df_sys_conf.empty and new_sys_name in df_sys_conf['nombre_sistema'].values:
                        st.error("Ya existe.")
                    else:
                        nid = 1 if df_sys_conf.empty else (pd.to_numeric(df_sys_conf['id'], errors='coerce').max() or 0) + 1
                        row = pd.DataFrame([{"id": nid, "nombre_sistema": new_sys_name, "descripcion": new_sys_desc}])
                        save_data(pd.concat([df_sys_conf, row], ignore_index=True), "sistemas_config")
                        st.success("Guardado!"); st.rerun()
                else:
                    st.error("El nombre es obligatorio.")
