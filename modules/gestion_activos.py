import streamlit as st
import pandas as pd
import json
from utils.db_con import get_data, save_data

# --- DEFINICIÓN DE COLUMNAS ---
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
    if opciones_existentes is None: opciones_existentes = []
    opciones_limpias = [str(x) for x in opciones_existentes if pd.notna(x) and str(x) != ""]
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
    
    tab_arbol, tab_manual = st.tabs(["🌳 Visualizar Árbol Completo", "✏️ Gestión & Edición"])

    # Carga de datos SEGURA
    df_eq = asegurar_df(get_data("equipos"), COLS_EQUIPOS)
    df_sys = asegurar_df(get_data("sistemas"), COLS_SISTEMAS)
    df_comp = asegurar_df(get_data("componentes"), COLS_COMPONENTES)

    # --- PRE-PROCESAMIENTO PARA GARANTIZAR ENLACES (IMPORTANTE) ---
    # Convertimos IDs y Tags a String para evitar errores de comparación (1 vs "1")
    if not df_sys.empty:
        df_sys['equipo_tag'] = df_sys['equipo_tag'].astype(str)
        df_sys['id'] = df_sys['id'].astype(str)
    if not df_eq.empty:
        df_eq['tag'] = df_eq['tag'].astype(str)
    if not df_comp.empty:
        df_comp['sistema_id'] = df_comp['sistema_id'].astype(str).str.replace(".0", "", regex=False)

    # ==========================================
    # TAB 1: VISUALIZACIÓN DEL ÁRBOL (DETALLADO)
    # ==========================================
    with tab_arbol:
        if df_eq.empty:
            st.info("No hay activos registrados. Ve a la pestaña de Gestión.")
        else:
            plantas = df_eq['planta'].unique()
            for planta in plantas:
                if pd.isna(planta): continue
                
                with st.expander(f"🏭 PLANTA: {planta}", expanded=True):
                    areas = df_eq[df_eq['planta'] == planta]['area'].unique()
                    for area in areas:
                        st.markdown(f"### 📍 Área: {area}")
                        
                        equipos = df_eq[(df_eq['planta'] == planta) & (df_eq['area'] == area)]
                        
                        for _, eq in equipos.iterrows():
                            # Nivel 3: Equipo (Expander)
                            with st.expander(f"🔹 EQUIPO: {eq['nombre']} ({eq['tag']})"):
                                c_kpi1, c_kpi2, c_kpi3 = st.columns(3)
                                c_kpi1.caption(f"**Tipo:** {eq['tipo']}")
                                c_kpi2.caption(f"**Criticidad:** {eq['criticidad']}")
                                c_kpi3.caption(f"**Estado:** {eq['estado']}")
                                
                                # Nivel 4: Sistemas
                                if not df_sys.empty:
                                    # Filtro seguro por string
                                    sistemas = df_sys[df_sys['equipo_tag'] == str(eq['tag'])]
                                    
                                    if sistemas.empty:
                                        st.warning("⚠️ No tiene sistemas registrados.")
                                    
                                    for _, sys in sistemas.iterrows():
                                        st.markdown("---")
                                        st.markdown(f"#### 🎛️ Sistema: {sys['nombre']}")
                                        if sys['descripcion']:
                                            st.caption(f"_{sys['descripcion']}_")
                                        
                                        # Nivel 5: Componentes
                                        if not df_comp.empty:
                                            # Filtro seguro por string
                                            comps = df_comp[df_comp['sistema_id'] == str(sys['id'])]
                                            
                                            if not comps.empty:
                                                for _, comp in comps.iterrows():
                                                    # FICHA TÉCNICA DEL COMPONENTE
                                                    st.markdown(f"""
                                                    <div style="background-color: #f0f2f6; padding: 10px; border-radius: 5px; margin-bottom: 5px; border-left: 5px solid #ff4b4b;">
                                                        <strong>🔧 {comp['nombre']}</strong><br>
                                                        <span style="font-size: 0.9em;">
                                                        • 🏷️ <strong>Marca:</strong> {comp['marca']} | <strong>Modelo:</strong> {comp['modelo']}<br>
                                                        • 📦 <strong>Cant:</strong> {comp['cantidad']} | <strong>Cat:</strong> {comp['categoria']}<br>
                                                        • 🔗 <strong>SKU Repuesto:</strong> {comp['repuesto_sku']}
                                                        </span>
                                                    </div>
                                                    """, unsafe_allow_html=True)
                                            else:
                                                st.caption("🚫 Sin componentes registrados en este sistema.")

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
                                    if not df_eq.empty:
                                        # Asegurar ID numérico
                                        df_eq['id'] = pd.to_numeric(df_eq['id'], errors='coerce').fillna(0)
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
                                    
                                    # Actualizar hijos (Cascada TAG)
                                    if tag_equipo != val_tag and not df_sys.empty:
                                        df_sys.loc[df_sys['equipo_tag'] == tag_equipo, 'equipo_tag'] = val_tag
                                        save_data(df_sys, "sistemas")
                                    
                                    save_data(df_eq, "equipos")
                                    st.success("Actualizado!"); st.rerun()

                # --- NIVEL 4: SISTEMAS ---
                # Inicializamos para evitar NameError
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
                            sys_exist = df_sys[df_sys['equipo_tag'] == str(tag_equipo)]['nombre'].tolist()
                        
                        sistema_sel, es_nuevo_sys = gestionar_filtro_dinamico("Sistema", sys_exist, "sistema")
                    
                    if sistema_sel:
                        with col_sys2:
                            st.markdown(f"**{'🆕 Nuevo Sistema' if es_nuevo_sys else '✏️ Editar Sistema'}**")
                            
                            sys_desc_def = ""
                            sys_idx = None
                            
                            if not es_nuevo_sys and not df_sys.empty:
                                try:
                                    # Convertir a string para asegurar match
                                    mask = (df_sys['equipo_tag'].astype(str) == str(tag_equipo)) & (df_sys['nombre'] == sistema_sel)
                                    sys_row = df_sys[mask].iloc[0]
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
                                        if not df_sys.empty:
                                            df_sys['id'] = pd.to_numeric(df_sys['id'], errors='coerce').fillna(0)
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
                        
                        comp_exist = []
                        if not df_comp.empty:
                            # Asegurar comparación de ID como string
                            mask_comp = df_comp['sistema_id'].astype(str).str.replace(".0", "") == str(sistema_id)
                            comp_exist = df_comp[mask_comp]['nombre'].tolist()
                        
                        comp_sel, es_nuevo_comp = gestionar_filtro_dinamico("Componente", comp_exist, "comp")
                        
                        if comp_sel:
                            with st.form("form_comp"):
                                st.caption(f"{'🆕 CREANDO' if es_nuevo_comp else '✏️ EDITANDO'}: {comp_sel}")
                                
                                def_marca, def_mod, def_cant, def_cat = "", "", 1, ""
                                comp_idx = None
                                
                                if not es_nuevo_comp:
                                    try:
                                        mask_c = (df_comp['sistema_id'].astype(str).str.replace(".0", "") == str(sistema_id)) & (df_comp['nombre'] == comp_sel)
                                        c_row = df_comp[mask_c].iloc[0]
                                        def_marca = c_row['marca']
                                        def_mod = c_row['modelo']
