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
    # Convertimos a string para evitar errores de tipos mixtos
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
    
    # Definimos 3 pestañas explícitas
    tab_arbol, tab_manual, tab_masiva = st.tabs(["🌳 Visualizar Árbol Completo", "✏️ Gestión & Edición", "📦 Carga Masiva"])

    # Carga de datos SEGURA
    df_eq = asegurar_df(get_data("equipos"), COLS_EQUIPOS)
    df_sys = asegurar_df(get_data("sistemas"), COLS_SISTEMAS)
    df_comp = asegurar_df(get_data("componentes"), COLS_COMPONENTES)

    # --- PRE-PROCESAMIENTO PARA GARANTIZAR ENLACES ---
    if not df_sys.empty:
        df_sys['equipo_tag'] = df_sys['equipo_tag'].astype(str)
        df_sys['id'] = df_sys['id'].astype(str)
    if not df_eq.empty:
        df_eq['tag'] = df_eq['tag'].astype(str)
    if not df_comp.empty:
        # Limpiamos IDs flotantes (ej: "1.0" -> "1")
        df_comp['sistema_id'] = df_comp['sistema_id'].astype(str).str.replace(r"\.0$", "", regex=True)

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
                            # Nivel 3: Equipo
                            with st.expander(f"🔹 {eq['nombre']} ({eq['tag']})"):
                                col_info1, col_info2 = st.columns(2)
                                col_info1.caption(f"Tipo: {eq['tipo']} | Criticidad: {eq['criticidad']}")
                                col_info2.caption(f"Estado: {eq['estado']}")
                                
                                # Nivel 4: Sistemas
                                if not df_sys.empty:
                                    sistemas = df_sys[df_sys['equipo_tag'] == str(eq['tag'])]
                                    
                                    if sistemas.empty:
                                        st.warning("⚠️ Sin sistemas registrados.")
                                    
                                    for _, sys in sistemas.iterrows():
                                        st.markdown("---")
                                        st.markdown(f"#### 🎛️ Sistema: {sys['nombre']}")
                                        if sys['descripcion']:
                                            st.caption(f"_{sys['descripcion']}_")
                                        
                                        # Nivel 5: Componentes
                                        if not df_comp.empty:
                                            comps = df_comp[df_comp['sistema_id'] == str(sys['id'])]
                                            
                                            if not comps.empty:
                                                for _, comp in comps.iterrows():
                                                    # Tarjeta visual de detalle
                                                    st.markdown(f"""
                                                    <div style="background-color: #f0f2f6; padding: 10px; border-radius: 5px; margin-bottom: 5px; border-left: 4px solid #ff4b4b;">
                                                        <strong>🔧 {comp['nombre']}</strong><br>
                                                        <span style="font-size: 0.85em;">
                                                        🏷️ <strong>Marca:</strong> {comp['marca']} | <strong>Mod:</strong> {comp['modelo']}<br>
                                                        📦 <strong>Cant:</strong> {comp['cantidad']} | <strong>Cat:</strong> {comp['categoria']}<br>
                                                        🔗 <strong>Repuesto SKU:</strong> {comp['repuesto_sku']}
                                                        </span>
                                                    </div>
                                                    """, unsafe_allow_html=True)
                                            else:
                                                st.caption("🚫 Sin componentes.")

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
                                st.error("Error cargando datos.")

                        with st.form("form_equipo"):
                            val_tag = st.text_input("TAG", value=def_tag).strip().upper()
                            val_tipo = st.text_input("Tipo", value=def_tipo)
                            opts_crit = ["", "Alta", "Media", "Baja"]
                            idx_crit = opts_crit.index(def_crit) if def_crit in opts_crit else 0
                            val_crit = st.selectbox("Criticidad", opts_crit, index=idx_crit)

                            btn_txt = "Guardar Nuevo" if es_nuevo_eq else "Actualizar Datos"
                            if st.form_submit_button(btn_txt):
                                if es_nuevo_eq:
                                    new_id = 1
                                    if not df_eq.empty and 'id' in df_eq:
                                         try:
                                             new_id = int(pd.to_numeric(df_eq['id']).max()) + 1
                                         except:
                                             new_id = len(df_eq) + 1
                                        
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
                                        df_sys.loc[df_sys['equipo_tag'] == str(tag_equipo), 'equipo_tag'] = val_tag
                                        save_data(df_sys, "sistemas")
                                    
                                    save_data(df_eq, "equipos")
                                    st.success("Actualizado!"); st.rerun()

                # --- NIVEL 4: SISTEMAS ---
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
                            sys_exist = df_sys[df_sys['equipo_tag'].astype(str) == str(tag_equipo)]['nombre'].tolist()
                        
                        sistema_sel, es_nuevo_sys = gestionar_filtro_dinamico("Sistema", sys_exist, "sistema")
                    
                    if sistema_sel:
                        with col_sys2:
                            st.markdown(f"**{'🆕 Nuevo Sistema' if es_nuevo_sys else '✏️ Editar Sistema'}**")
                            sys_desc_def = ""
                            sys_idx = None
                            
                            if not es_nuevo_sys and not df_sys.empty:
                                try:
                                    mask = (df_sys['equipo_tag'].astype(str) == str(tag_equipo)) & (df_sys['nombre'] == sistema_sel)
                                    sys_row = df_sys[mask].iloc[0]
                                    sys_desc_def = sys_row['descripcion']
                                    sistema_id = sys_row['id']
                                    sys_idx = sys_row.name
                                except IndexError:
                                    pass
                            
                            with st.form("form_sistema"):
                                val_desc = st.text_input("Descripción", value=sys_desc_def)
                                if st.form_submit_button("Guardar Sistema"):
                                    if es_nuevo_sys:
                                        new_id = 1
                                        if not df_sys.empty:
                                            try: new_id = int(pd.to_numeric(df_sys['id']).max()) + 1
                                            except: new_id = len(df_sys) + 1
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
                            # Asegurar ID como string para filtrar
                            mask_comp = df_comp['sistema_id'].astype(str).str.replace(r"\.0$", "", regex=True) == str(sistema_id)
                            comp_exist = df_comp[mask_comp]['nombre'].tolist()
                        
                        comp_sel, es_nuevo_comp = gestionar_filtro_dinamico("Componente", comp_exist, "comp")
                        
                        if comp_sel:
                            with st.form("form_comp"):
                                st.caption(f"{'🆕 CREANDO' if es_nuevo_comp else '✏️ EDITANDO'}: {comp_sel}")
                                
                                def_marca, def_mod, def_cant, def_cat = "", "", 1, ""
                                comp_idx = None
                                
                                if not es_nuevo_comp:
                                    try:
                                        mask_c = (df_comp['sistema_id'].astype(str).str.replace(r"\.0$", "", regex=True) == str(sistema_id)) & (df_comp['nombre'] == comp_sel)
                                        c_row = df_comp[mask_c].iloc[0]
                                        def_marca = c_row['marca']
                                        def_mod = c_row['modelo']
                                        def_cant = int(c_row['cantidad']) if pd.notna(c_row['cantidad']) else 1
                                        def_cat = c_row['categoria']
                                        comp_idx = c_row.name
                                    except IndexError:
                                        pass

                                c1, c2 = st.columns(2)
                                v_marca = c1.text_input("Marca", value=def_marca)
                                v_mod = c2.text_input("Modelo", value=def_mod)
                                c3, c4 = st.columns(2)
                                v_cant = c3.number_input("Cantidad", min_value=1, value=def_cant)
                                v_cat = c4.text_input("Categoría", value=def_cat)

                                if st.form_submit_button("Guardar Componente"):
                                    if es_nuevo_comp:
                                        new_id = 1
                                        if not df_comp.empty:
                                            try: new_id = int(pd.to_numeric(df_comp['id']).max()) + 1
                                            except: new_id = len(df_comp) + 1
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

    # ==========================================
    # TAB 3: CARGA MASIVA
    # ==========================================
    with tab_masiva:
        st.subheader("Carga Masiva (Excel)")
        st.info("Sube tu Excel con columnas: Planta, Area, Tag_Equipo, Nombre_Equipo...")
        file = st.file_uploader("Subir Excel", type=["xlsx"])
