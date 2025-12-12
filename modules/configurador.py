import streamlit as st
import pandas as pd
import json
from utils.db_con import get_data, save_data

def render_configurador():
    st.header("⚙️ Maestros de Configuración (Estándares)")
    st.info("Define aquí los tipos de Sistemas y sus Componentes permitidos.")

    tab_sys, tab_comp = st.tabs(["1️⃣ Maestro de Sistemas", "2️⃣ Maestro de Componentes"])

    # ==========================================
    # TAB 1: MAESTRO DE SISTEMAS
    # ==========================================
    with tab_sys:
        st.subheader("Catálogo de Sistemas")
        
        # Cargar datos
        df_sys_conf = get_data("sistemas_config")
        if df_sys_conf.empty: 
            df_sys_conf = pd.DataFrame(columns=["id", "nombre_sistema", "descripcion"])

        # Mostrar tabla
        if not df_sys_conf.empty:
            st.dataframe(df_sys_conf[["nombre_sistema", "descripcion"]], use_container_width=True, hide_index=True)
        else:
            st.warning("No hay sistemas definidos. Crea el primero (Ej: SISTEMA DE TRANSMISIÓN).")
        
        st.divider()
        with st.form("add_sys_conf"):
            st.write("➕ **Agregar Nuevo Tipo de Sistema**")
            c1, c2 = st.columns(2)
            new_sys = c1.text_input("Nombre Sistema", placeholder="Ej: SISTEMA HIDRAULICO").strip().upper()
            new_desc = c2.text_input("Descripción", placeholder="Opcional")
            
            if st.form_submit_button("Guardar Sistema Maestro"):
                if new_sys:
                    if not df_sys_conf.empty and new_sys in df_sys_conf['nombre_sistema'].values:
                        st.error("Ya existe.")
                    else:
                        nid = 1
                        if not df_sys_conf.empty:
                            try: nid = int(pd.to_numeric(df_sys_conf['id']).max()) + 1
                            except: nid = len(df_sys_conf) + 1
                        
                        row = pd.DataFrame([{"id": nid, "nombre_sistema": new_sys, "descripcion": new_desc}])
                        save_data(pd.concat([df_sys_conf, row], ignore_index=True), "sistemas_config")
                        st.success(f"Sistema '{new_sys}' creado."); st.rerun()
                else:
                    st.error("Nombre obligatorio.")

    # ==========================================
    # TAB 2: MAESTRO DE COMPONENTES (VINCULADO)
    # ==========================================
    with tab_comp:
        # Cargar Sistemas para el filtro
        lista_sistemas = df_sys_conf["nombre_sistema"].tolist() if not df_sys_conf.empty else []
        
        if not lista_sistemas:
            st.error("⚠️ Primero crea Sistemas en la pestaña 1.")
        else:
            c_main1, c_main2 = st.columns([1, 2])
            
            # 1. SELECCIONAR SISTEMA PADRE
            with c_main1:
                st.subheader("A. Elegir Sistema")
                sistema_padre = st.selectbox("Asociar Familia a:", lista_sistemas)
                st.divider()
                
                # 2. CREAR/EDITAR FAMILIA
                st.subheader("B. Familia")
                df_fam = get_data("familias_config")
                if df_fam.empty or "sistema_asociado" not in df_fam.columns:
                    df_fam = pd.DataFrame(columns=["id", "nombre_familia", "sistema_asociado", "config_json"])

                # Filtro: Solo familias de este sistema
                fams_del_sistema = df_fam[df_fam["sistema_asociado"] == sistema_padre]["nombre_familia"].tolist()
                
                modo = st.radio("Acción:", ["Editar Existente", "Crear Nueva"], horizontal=True)
                nombre_fam = ""
                idx_fam = None
                
                if modo == "Editar Existente":
                    if fams_del_sistema:
                        nombre_fam = st.selectbox("Seleccionar Familia", fams_del_sistema)
                        try: idx_fam = df_fam[(df_fam["nombre_familia"]==nombre_fam) & (df_fam["sistema_asociado"]==sistema_padre)].index[0]
                        except: pass
                    else: st.info("No hay familias en este sistema.")
                else:
                    nombre_fam = st.text_input("Nombre Nueva Familia", placeholder="Ej: BOMBA DE PISTONES").strip().upper()

            # 3. DEFINIR CAMPOS TÉCNICOS
            if nombre_fam:
                with c_main2:
                    st.subheader(f"C. Variables para '{nombre_fam}'")
                    
                    # Gestión de memoria temporal para editar campos
                    key_mem = f"fields_{sistema_padre}_{nombre_fam}"
                    if "current_fam_key" not in st.session_state or st.session_state["current_fam_key"] != key_mem:
                        st.session_state["current_fam_key"] = key_mem
                        st.session_state["campos_temp"] = []
                        if modo == "Editar Existente" and idx_fam is not None:
                            try: st.session_state["campos_temp"] = json.loads(df_fam.at[idx_fam, "config_json"])
                            except: pass

                    # Mostrar campos actuales
                    campos = st.session_state["campos_temp"]
                    if campos:
                        for i, cp in enumerate(campos):
                            ca, cb, cc = st.columns([3, 2, 1])
                            ca.text(f"🔹 {cp['nombre']}")
                            cb.caption(f"Unidad: {cp.get('unidad','-')}")
                            if cc.button("🗑️", key=f"del_{i}"):
                                campos.pop(i); st.rerun()
                    else: st.info("Agrega variables técnicas abajo.")

                    with st.form("add_var"):
                        n1, n2 = st.columns([2,1])
                        v_nom = n1.text_input("Nombre Variable", placeholder="Ej: Caudal Máximo")
                        v_uni = n2.text_input("Unidad", placeholder="L/min")
                        if st.form_submit_button("Agregar Variable"):
                            if v_nom: 
                                st.session_state["campos_temp"].append({"nombre": v_nom, "unidad": v_uni})
                                st.rerun()

                    st.divider()
                    if st.button("💾 GUARDAR FAMILIA", type="primary"):
                        js_final = json.dumps(st.session_state["campos_temp"])
                        
                        if modo == "Crear Nueva":
                            if nombre_fam in fams_del_sistema: st.error("Ya existe.")
                            else:
                                nid = 1
                                if not df_fam.empty:
                                    try: nid = int(pd.to_numeric(df_fam['id']).max()) + 1
                                    except: nid = len(df_fam) + 1
                                
                                row = pd.DataFrame([{
                                    "id": nid, "nombre_familia": nombre_fam, 
                                    "sistema_asociado": sistema_padre, "config_json": js_final
                                }])
                                save_data(pd.concat([df_fam, row], ignore_index=True), "familias_config")
                                st.success("Guardado!"); st.rerun()
                        else:
                            df_fam.at[idx_fam, "config_json"] = js_final
                            save_data(df_fam, "familias_config")
                            st.success("Actualizado!")
