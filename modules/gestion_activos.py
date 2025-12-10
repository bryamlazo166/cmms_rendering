import streamlit as st
import pandas as pd
import json
from utils.db_con import get_data, save_data

# --- DEFINICIÓN DE COLUMNAS (Para evitar errores si la hoja está vacía) ---
COLS_EQUIPOS = ["id", "tag", "nombre", "planta", "area", "tipo", "criticidad", "estado"]
COLS_SISTEMAS = ["id", "equipo_tag", "nombre", "descripcion"]
COLS_COMPONENTES = ["id", "sistema_id", "nombre", "marca", "modelo", "cantidad", "categoria", "repuesto_sku", "specs_json"]

# --- HELPER: ASEGURAR DATAFRAME ---
def asegurar_df(df, columnas_base):
    """Si el DF viene vacío o sin columnas, lo inicializa correctamente."""
    if df.empty or len(df.columns) == 0:
        return pd.DataFrame(columns=columnas_base)
    # Aseguramos que tenga todas las columnas necesarias, si falta alguna la crea vacía
    for col in columnas_base:
        if col not in df.columns:
            df[col] = None
    return df

# --- HELPER: SELECTOR DINÁMICO ---
def gestionar_filtro_dinamico(label, opciones_existentes, key_suffix):
    opciones_limpias = [x for x in opciones_existentes if pd.notna(x) and x != ""]
    opciones = sorted(list(set(opciones_limpias)))
    opciones.insert(0, "➕ CREAR NUEVO...")
    opciones.insert(0, "Seleccionar...")
    
    seleccion = st.selectbox(f"Seleccione {label}", opciones, key=f"sel_{key_suffix}")
    
    valor_final = None
    es_nuevo = False
    
    if seleccion == "➕ CREAR NUEVO...":
        valor_final = st.text_input(f"Escriba nuevo nombre para {label}", key=f"new_{key_suffix}").strip().upper()
        es_nuevo = True
    elif seleccion != "Seleccionar...":
        valor_final = seleccion
        
    return valor_final, es_nuevo

def render_gestion_activos():
    st.header("🏭 Gestión y Edición de Activos")
    
    tab_arbol, tab_manual = st.tabs(["🌳 Visualizar Árbol", "✏️ Gestión & Edición"])

    # Carga de datos SEGURA
    df_eq = asegurar_df(get_data("equipos"), COLS_EQUIPOS)
    df_sys = asegurar_df(get_data("sistemas"), COLS_SISTEMAS)
    df_comp = asegurar_df(get_data("componentes"), COLS_COMPONENTES)

    # ==========================================
    # TAB 1: VISUALIZACIÓN
    # ==========================================
    with tab_arbol:
        if df_eq.empty:
            st.info("No hay activos registrados. Ve a la pestaña de Gestión.")
        else:
            plantas = df_eq['planta'].unique()
            for planta in plantas:
                if pd.isna(planta): continue
                with st.expander(f"🏭 {planta}", expanded=True):
                    areas = df_eq[df_eq['planta'] == planta]['area'].unique()
                    for area in areas:
                        st.markdown(f"**📍 {area}**")
                        equipos = df_eq[(df_eq['planta'] == planta) & (df_eq['area'] == area)]
                        for _, eq in equipos.iterrows():
                            st.markdown(f"&nbsp;&nbsp;&nbsp; 🔹 **{eq['nombre']}** ({eq['tag']})")
                            # Sistemas
                            if not df_sys.empty:
                                sistemas = df_sys[df_sys['equipo_tag'] == eq['tag']]
                                for _, sys in sistemas.iterrows():
                                    st.caption(f"&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; 🎛️ {sys['nombre']}")

    # ==========================================
    # TAB 2: GESTIÓN Y EDICIÓN
    # ==========================================
    with tab_manual:
        st.markdown("##### Navegación por Niveles")
        
        # --- NIVEL 1 & 2: PLANTA Y ÁREA ---
        plantas_exist = df_eq['planta'].unique().tolist() if not df_eq.empty else []
        planta_val, _ = gestionar_filtro_dinamico("Planta", plantas_exist, "planta")
        
        if planta_val:
            areas_exist = []
            if not df_eq.empty:
                areas_exist = df_eq[df_eq['planta'] == planta_val]['area'].unique().tolist()
            area_val, _ = gestionar_filtro_dinamico("Área", areas_exist, "area")
            
            if area_val:
                st.divider()
                
                # --- NIVEL 3: EQUIPO ---
                col_eq1, col_eq2 = st.columns(2)
                with col_eq1:
                    eqs_exist = []
                    if not df_eq.empty:
                        eqs_exist = df_eq[(df_eq['planta'] == planta_val) & (df_eq['area'] == area_val)]['nombre'].tolist()
                    
                    equipo_sel, es_nuevo_eq = gestionar_filtro_dinamico("Equipo", eqs_exist, "equipo")

                equipo_row = None
                tag_equipo = None

                if equipo_sel:
                    with col_eq2:
                        st.markdown(f"**{'🆕 Nuevo Equipo' if es_nuevo_eq else '✏️ Editar Equipo'}**")
                        
                        def_tag, def_tipo, def_crit = "", "", ""
                        eq_idx = None
                        
                        if not es_nuevo_eq:
                            equipo_row = df_eq[(df_eq['nombre'] == equipo_sel) & (df_eq['area'] == area_val)].iloc[0]
                            def_tag = equipo_row['tag']
                            def_tipo = equipo_row['tipo']
                            def_crit = equipo_row['criticidad']
                            eq_idx = equipo_row.name
                            tag_equipo = def_tag

                        with st.form("form_equipo"):
                            val_tag = st.text_input("TAG", value=def_tag).strip().upper()
                            val_tipo = st.text_input("Tipo", value=def_tipo)
                            opts_crit = ["", "Alta", "Media", "Baja"]
                            # Manejo seguro de índice
                            idx_crit = 0
                            if def_crit in opts_crit:
                                idx_crit = opts_crit.index(def_crit)
                            val_crit = st.selectbox("Criticidad", opts_crit, index=idx_crit)

                            btn_txt = "Guardar Nuevo" if es_nuevo_eq else "Actualizar Datos"
                            if st.form_submit_button(btn_txt):
                                if es_nuevo_eq:
                                    # Generación ID seguro
                                    new_id = 1
                                    if not df_eq.empty and 'id' in df_eq and pd.notna(df_eq['id'].max()):
                                        new_id = int(df_eq['id'].max()) + 1
                                        
                                    row = pd.DataFrame([{
                                        "id": new_id, "tag": val_tag, "nombre": equipo_sel,
                                        "planta": planta_val, "area": area_val,
                                        "tipo": val_tipo, "criticidad": val_crit, "estado": "Operativo"
                                    }])
                                    save_data(pd.concat([df_eq, row], ignore_index=True), "equipos")
                                    st.success("Creado!"); st.rerun()
                                else:
                                    df_eq.at[eq_idx, 'tag'] = val_tag
                                    df_eq.at[eq_idx, 'tipo'] = val_tipo
                                    df_eq.at[eq_idx, 'criticidad'] = val_crit
                                    
                                    # Actualizar hijos
                                    if tag_equipo != val_tag and not df_sys.empty:
                                        df_sys.loc[df_sys['equipo_tag'] == tag_equipo, 'equipo_tag'] = val_tag
                                        save_data(df_sys, "sistemas")
                                    
                                    save_data(df_eq, "equipos")
                                    st.success("Actualizado!"); st.rerun()

                # --- NIVEL 4: SISTEMAS ---
                if tag_equipo and not es_nuevo_eq:
                    st.divider()
                    col_sys1, col_sys2 = st.columns(2)
                    
                    with col_sys1:
                        st.markdown(f"🎛️ **Sistemas de: {equipo_sel}**")
                        sys_exist = []
                        if not df_sys.empty:
                            sys_exist = df_sys[df_sys['equipo_tag'] == tag_equipo]['nombre'].tolist()
                        
                        sistema_sel, es_nuevo_sys = gestionar_filtro_dinamico("Sistema", sys_exist, "sistema")
                    
                    sistema_id = None
                    
                    if sistema_sel:
                        with col_sys2:
                            st.markdown(f"**{'🆕 Nuevo Sistema' if es_nuevo_sys else '✏️ Editar Sistema'}**")
                            
                            sys_desc_def = ""
                            sys_idx = None
                            
                            if not es_nuevo_sys and not df_sys.empty:
                                sys_row = df_sys[(df_sys['equipo_tag'] == tag_equipo) & (df_sys['nombre'] == sistema_sel)].iloc[0]
                                sys_desc_def = sys_row['descripcion']
                                sistema_id = sys_row['id']
                                sys_idx = sys_row.name
                            
                            with st.form("form_sistema"):
                                val_desc = st.text_input("Descripción", value=sys_desc_def)
                                
                                if st.form_submit_button("Guardar Sistema"):
                                    if es_nuevo_sys:
                                        new_id = 1
                                        if not df_sys.empty and 'id' in df_sys and pd.notna(df_sys['id'].max()):
                                            new_id = int(df_sys['id'].max()) + 1
                                            
                                        row = pd.DataFrame([{
                                            "id": new_id, "equipo_tag": tag_equipo,
                                            "nombre": sistema_sel, "descripcion": val_desc
                                        }])
                                        save_data(pd.concat([df_sys, row], ignore_index=True), "sistemas")
                                        st.success("Creado!"); st.rerun()
                                    else:
                                        df_sys.at[sys_idx, 'descripcion'] = val_desc
                                        save_data(df_sys, "sistemas")
                                        st.success("Actualizado!"); st.rerun()

                    # --- NIVEL 5: COMPONENTES ---
                    if sistema_id:
                        st.divider()
                        st.markdown(f"🔧 **Componentes de: {sistema_sel}**")
                        
                        comp_exist
