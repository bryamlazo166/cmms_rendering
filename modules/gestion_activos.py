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
    if df.empty or len(df.columns) == 0:
        return pd.DataFrame(columns=columnas_base)
    for col in columnas_base:
        if col not in df.columns:
            df[col] = None
    return df

# --- HELPER: SELECTOR DINÁMICO ---
def gestionar_filtro_dinamico(label, opciones_existentes, key_suffix):
    # Aseguramos que opciones_existentes sea una lista válida
    if opciones_existentes is None:
        opciones_existentes = []
        
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
                            try:
                                equipo_row = df_eq[(df_eq['nombre'] == equipo_sel) & (df_eq['area'] == area_val)].iloc[0]
                                def_tag = equipo_row['tag']
                                def_tipo = equipo_row['tipo']
                                def_crit = equipo_row['criticidad']
                                eq_idx = equipo_row.name
                                tag_equipo = def_tag
                            except IndexError:
                                st.error("Error cargando datos del equipo.")

                        with st.form("form_equipo"):
                            val_tag = st.text_input("TAG", value=def_tag).strip().upper()
                            val_tipo = st.text_input("Tipo", value=def_tipo)
                            opts_crit = ["", "Alta", "Media", "Baja"]
                            idx_crit = 0
                            if def_crit in opts_crit:
                                idx_crit = opts_crit.index(def_crit)
                            val_crit = st.selectbox("Criticidad", opts_crit, index=idx_crit)

                            btn_txt = "Guardar Nuevo" if es_nuevo_eq else "Actualizar Datos"
                            if st.form_submit_button(btn_txt):
                                if es_nuevo_eq:
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
                # Inicializamos variables para evitar NameError
                sistema_sel = None
                es_nuevo_sys = False
                sistema_id = None

                if tag_equipo and not es_nuevo_eq:
                    st.divider()
                    col_sys1, col_sys2 = st.columns(2)
                    
                    with col_sys1:
                        st.markdown(f"🎛️ **Sistemas de: {equipo_sel}**")
                        sys_exist = []
                        if not df_sys.empty:
                            sys_exist = df_sys[df_sys['equipo_tag'] == tag_equipo]['nombre'].tolist()
                        
                        sistema_sel, es_nuevo_sys = gestionar_filtro_dinamico("Sistema", sys_exist, "sistema")
                    
                    if sistema_sel:
                        with col_sys2:
                            st.markdown(f"**{'🆕 Nuevo Sistema' if es_nuevo_sys else '✏️ Editar Sistema'}**")
                            
                            sys_desc_def = ""
                            sys_idx = None
                            
                            if not es_nuevo_sys and not df_sys.empty:
                                try:
                                    sys_row = df_sys[(df_sys['equipo_tag'] == tag_equipo) & (df_sys['nombre'] == sistema_sel)].iloc[0]
                                    sys_desc_def = sys_row['descripcion']
                                    sistema_id = sys_row['id']
                                    sys_idx = sys_row.name
                                except IndexError:
                                    st.error("Error cargando sistema.")
                            
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
                        
                        # Inicialización explícita para evitar NameError
                        comp_exist = []
                        if not df_comp.empty:
                            comp_exist = df_comp[df_comp['sistema_id'] == sistema_id]['nombre'].tolist()
                        
                        comp_sel, es_nuevo_comp = gestionar_filtro_dinamico("Componente", comp_exist, "comp")
                        
                        if comp_sel:
                            with st.form("form_comp"):
                                st.caption(f"{'🆕 CREANDO' if es_nuevo_comp else '✏️ EDITANDO'}: {comp_sel}")
                                
                                def_marca, def_mod, def_cant, def_cat = "", "", 1, ""
                                comp_idx = None
                                
                                if not es_nuevo_comp:
                                    try:
                                        c_row = df_comp[(df_comp['sistema_id'] == sistema_id) & (df_comp['nombre'] == comp_sel)].iloc[0]
                                        def_marca = c_row['marca']
                                        def_mod = c_row['modelo']
                                        def_cant = int(c_row['cantidad']) if pd.notna(c_row['cantidad']) else 1
                                        def_cat = c_row['categoria']
                                        comp_idx = c_row.name
                                    except IndexError:
                                        st.warning("Datos de componente incompletos.")

                                c1, c2 = st.columns(2)
                                v_marca = c1.text_input("Marca", value=def_marca)
                                v_mod = c2.text_input("Modelo", value=def_mod)
                                
                                c3, c4 = st.columns(2)
                                v_cant = c3.number_input("Cantidad", min_value=1, value=def_cant)
                                v_cat = c4.text_input("Categoría", value=def_cat)

                                if st.form_submit_button("Guardar Componente"):
                                    if es_nuevo_comp:
                                        new_id = 1
                                        if not df_comp.empty and 'id' in df_comp and pd.notna(df_comp['id'].max()):
                                            new_id = int(df_comp['id'].max()) + 1
                                            
                                        row = pd.DataFrame([{
                                            "id": new_id, "sistema_id": sistema_id, "nombre": comp_sel,
                                            "marca": v_marca, "modelo": v_mod, "cantidad": v_cant,
                                            "categoria": v_cat, "repuesto_sku": "", "specs_json": "{}"
                                        }])
                                        save_data(pd.concat([df_comp, row], ignore_index=True), "componentes")
                                    else:
                                        df_comp.at[comp_idx, 'marca'] = v_marca
                                        df_comp.at[comp_idx, 'modelo'] = v_mod
                                        df_comp.at[comp_idx, 'cantidad'] = v_cant
                                        df_comp.at[comp_idx, 'categoria'] = v_cat
                                        save_data(df_comp, "componentes")
                                    
                                    st.success("Guardado!"); st.rerun()
