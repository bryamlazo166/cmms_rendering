import streamlit as st
import pandas as pd
import json
from utils.db_con import get_data, save_data

def render_configurador():
    st.header("⚙️ Maestros de Configuración")
    st.info("Estructura: Sistema (Padre) ➝ Familia de Componentes (Hijo)")

    tab_sys, tab_comp = st.tabs(["1️⃣ Maestro de Sistemas", "2️⃣ Maestro de Componentes (Por Sistema)"])

    # ==========================================
    # TAB 1: MAESTRO DE SISTEMAS (PADRE)
    # ==========================================
    with tab_sys:
        st.subheader("Tipos de Sistemas Estándar")
        
        df_sys_conf = get_data("sistemas_config")
        if df_sys_conf.empty: df_sys_conf = pd.DataFrame(columns=["id", "nombre_sistema", "descripcion"])

        # Mostrar tabla actual
        if not df_sys_conf.empty:
            st.dataframe(df_sys_conf[["nombre_sistema", "descripcion"]], use_container_width=True, hide_index=True)
        
        st.divider()
        with st.form("add_sys_conf"):
            c_s1, c_s2 = st.columns(2)
            new_sys_name = c_s1.text_input("Nuevo Tipo de Sistema", placeholder="Ej: TRANSMISION MECANICA").strip().upper()
            new_sys_desc = c_s2.text_input("Descripción", placeholder="Opcional")
            
            if st.form_submit_button("Guardar Tipo de Sistema"):
                if new_sys_name:
                    if not df_sys_conf.empty and new_sys_name in df_sys_conf['nombre_sistema'].values:
                        st.error("Ya existe.")
                    else:
                        nid = 1 if df_sys_conf.empty else (pd.to_numeric(df_sys_conf['id'], errors='coerce').max() or 0) + 1
                        row = pd.DataFrame([{"id": nid, "nombre_sistema": new_sys_name, "descripcion": new_sys_desc}])
                        save_data(pd.concat([df_sys_conf, row], ignore_index=True), "sistemas_config")
                        st.success(f"Sistema '{new_sys_name}' creado."); st.rerun()
                else:
                    st.error("Nombre obligatorio.")

    # ==========================================
    # TAB 2: MAESTRO DE COMPONENTES (HIJO)
    # ==========================================
    with tab_comp:
        # Cargar Sistemas para vincular
        lista_sistemas = df_sys_conf["nombre_sistema"].tolist() if not df_sys_conf.empty else []
        
        if not lista_sistemas:
            st.warning("⚠️ Primero debes crear Sistemas en la pestaña anterior.")
        else:
            c_main1, c_main2 = st.columns([1, 2])
            
            # SELECCIÓN DEL PADRE (SISTEMA)
            with c_main1:
                st.subheader("Paso A: Elegir Sistema")
                sistema_padre = st.selectbox("Asociar a Sistema:", lista_sistemas)
                st.divider()
                
                # CREAR O EDITAR FAMILIA
                st.subheader("Paso B: Familia")
                df_fam = get_data("familias_config")
                if df_fam.empty or "sistema_asociado" not in df_fam.columns:
                    df_fam = pd.DataFrame(columns=["id", "nombre_familia", "sistema_asociado", "config_json"])

                # Filtrar familias que pertenecen a este sistema
                familias_del_sistema = df_fam[df_fam["sistema_asociado"] == sistema_padre]["nombre_familia"].tolist()
                
                modo = st.radio("Acción:", ["Editar Existente", "Crear Nueva"], horizontal=True)
                nombre_familia = ""
                idx_fam = None
                
                if modo == "Editar Existente":
                    if familias_del_sistema:
                        nombre_familia = st.selectbox("Seleccionar Familia", familias_del_sistema)
                        try: idx_fam = df_fam[(df_fam["nombre_familia"]==nombre_familia) & (df_fam["sistema_asociado"]==sistema_padre)].index[0]
                        except: pass
                    else: st.info("No hay familias en este sistema.")
                else:
                    nombre_familia = st.text_input("Nombre Nueva Familia", placeholder="Ej: FAJA EN V").strip().upper()

            # DEFINIR VARIABLES
            if nombre_familia:
                with c_main2:
                    st.subheader(f"Paso C: Variables para '{nombre_familia}'")
                    
                    # Memoria temporal
                    key_mem = f"fields_{sistema_padre}_{nombre_familia}"
                    if "current_fam_key" not in st.session_state or st.session_state["current_fam_key"] != key_mem:
                        st.session_state["current_fam_key"] = key_mem
                        st.session_state["campos_temp"] = []
                        # Cargar si existe
                        if modo == "Editar Existente" and idx_fam is not None:
                            try: st.session_state["campos_temp"] = json.loads(df_fam.at[idx_fam, "config_json"])
                            except: pass

                    # Tabla editora
                    campos = st.session_state["campos_temp"]
                    for i, cp in enumerate(campos):
                        ca, cb, cc = st.columns([3, 2, 1])
                        ca.text(f"🔹 {cp['nombre']}")
                        cb.caption(f"Unidad: {cp.get('unidad','-')}")
                        if cc.button("🗑️", key=f"d_{i}"):
                            campos.pop(i); st.rerun()

                    with st.form("add_field_fam"):
                        n1, n2 = st.columns([2,1])
                        v_nom = n1.text_input("Nombre Variable", placeholder="Ej: Longitud")
                        v_uni = n2.text_input("Unidad", placeholder="mm")
                        if st.form_submit_button("Agregar Variable"):
                            if v_nom: 
                                st.session_state["campos_temp"].append({"nombre": v_nom, "unidad": v_uni})
                                st.rerun()

                    st.divider()
                    if st.button("💾 GUARDAR FAMILIA", type="primary"):
                        js_final = json.dumps(st.session_state["campos_temp"])
                        
                        if modo == "Crear Nueva":
                            # Validar duplicado en el mismo sistema
                            if nombre_familia in familias_del_sistema:
                                st.error("Ya existe en este sistema.")
                            else:
                                nid = 1 if df_fam.empty else (pd.to_numeric(df_fam['id'], errors='coerce').max() or 0) + 1
                                row = pd.DataFrame([{
                                    "id": nid, 
                                    "nombre_familia": nombre_familia, 
                                    "sistema_asociado": sistema_padre, # VINCULACIÓN CLAVE
                                    "config_json": js_final
                                }])
                                save_data(pd.concat([df_fam, row], ignore_index=True), "familias_config")
                                st.success("Familia creada y vinculada."); st.rerun()
                        else:
                            df_fam.at[idx_fam, "config_json"] = js_final
                            save_data(df_fam, "familias_config")
                            st.success("Actualizado!")
