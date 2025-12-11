import streamlit as st
import pandas as pd
import json
from utils.db_con import get_data, save_data

# --- DEFINICIÓN DE COLUMNAS ---
COLS_EQUIPOS = ["id", "tag", "nombre", "planta", "area", "tipo", "criticidad", "estado"]
COLS_SISTEMAS = ["id", "equipo_tag", "nombre", "descripcion"]
COLS_COMPONENTES = ["id", "sistema_id", "nombre", "marca", "modelo", "cantidad", "categoria", "repuesto_sku", "specs_json"]

# --- HELPERS ---
def asegurar_df(df, columnas_base):
    if df.empty or len(df.columns) == 0:
        return pd.DataFrame(columns=columnas_base)
    for col in columnas_base:
        if col not in df.columns:
            df[col] = None
    return df

def limpiar_id(serie):
    return serie.astype(str).str.replace(r"\.0$", "", regex=True).str.strip()

def gestionar_filtro_dinamico(label, opciones_existentes, key_suffix):
    # 1. Preparar opciones
    if opciones_existentes is None: opciones_existentes = []
    opciones_limpias = [str(x) for x in opciones_existentes if pd.notna(x) and str(x) != ""]
    opciones = sorted(list(set(opciones_limpias)))
    
    opciones.insert(0, "➕ CREAR NUEVO...")
    opciones.insert(0, "Seleccionar...")
    
    # 2. Renderizar
    key_widget = f"sel_{key_suffix}"
    seleccion = st.selectbox(f"Seleccione {label}", opciones, key=key_widget)
    
    valor_final = None
    es_nuevo = False
    
    if seleccion == "➕ CREAR NUEVO...":
        valor_final = st.text_input(f"Escriba nuevo nombre para {label}", key=f"new_{key_suffix}").strip().upper()
        es_nuevo = True
    elif seleccion != "Seleccionar...":
        valor_final = seleccion
        
    return valor_final, es_nuevo

# --- ESPECIFICACIONES TÉCNICAS ---
def render_specs_dinamicas(categoria, valores_actuales={}):
    specs = {}
    st.markdown("---")
    st.caption(f"⚙️ Ficha Técnica: {categoria}")
    cat_upper = str(categoria).upper()
    
    if "MOTOR" in cat_upper and "REDUCTOR" not in cat_upper:
        c1, c2, c3 = st.columns(3)
        specs["potencia_hp"] = c1.text_input("Potencia (HP)", value=valores_actuales.get("potencia_hp", ""))
        specs["rpm_motor"] = c2.text_input("RPM", value=valores_actuales.get("rpm_motor", ""))
        specs["voltaje"] = c3.text_input("Voltaje (V)", value=valores_actuales.get("voltaje", ""))
        c4, c5 = st.columns(2)
        specs["corriente_nom"] = c4.text_input("Amperaje (A)", value=valores_actuales.get("corriente_nom", ""))
        specs["frame"] = c5.text_input("Frame/Carcasa", value=valores_actuales.get("frame", ""))

    elif "REDUCTOR" in cat_upper or "MOTOREDUCTOR" in cat_upper:
        c1, c2 = st.columns(2)
        specs["potencia_hp"] = c1.text_input("Potencia Motor (HP)", value=valores_actuales.get("potencia_hp", ""))
        specs["ratio"] = c2.text_input("Relación (Ratio)", value=valores_actuales.get("ratio", ""))
        c3, c4 = st.columns(2)
        specs["rpm_salida"] = c3.text_input("RPM Salida", value=valores_actuales.get("rpm_salida", ""))
        specs["eje_salida"] = c4.text_input("Ø Eje Salida", value=valores_actuales.get("eje_salida", ""))

    elif "RODAMIENTO" in cat_upper or "CHUMACERA" in cat_upper:
        c1, c2 = st.columns(2)
        specs["codigo_iso"] = c1.text_input("Código ISO", value=valores_actuales.get("codigo_iso", ""))
        specs["tipo_sello"] = c2.selectbox("Sello", ["Abierto", "ZZ", "2RS"], index=0)

    elif "FAJA" in cat_upper:
        c1, c2 = st.columns(2)
        specs["perfil"] = c1.text_input("Perfil", value=valores_actuales.get("perfil", ""))
        specs["longitud"] = c2.text_input("Longitud", value=valores_actuales.get("longitud", ""))

    else:
        specs["detalles"] = st.text_area("Detalles Generales", value=valores_actuales.get("detalles", ""))
        
    return specs

# --- VISTA PRINCIPAL ---
def render_gestion_activos():
    st.header("🏭 Gestión y Edición de Activos")
    
    # CSS para forzar colores legibles en móviles (Tema Oscuro)
    st.markdown("""
    <style>
    div[data-testid="stExpander"] details summary p { font-size: 1.1em; font-weight: bold; }
    input { color: black !important; }
    </style>
    """, unsafe_allow_html=True)
    
    tab_arbol, tab_manual, tab_masiva = st.tabs(["🌳 Visualizar Árbol", "✏️ Gestión & Edición", "📦 Carga Masiva"])

    # Carga de datos
    df_eq = asegurar_df(get_data("equipos"), COLS_EQUIPOS)
    df_sys = asegurar_df(get_data("sistemas"), COLS_SISTEMAS)
    df_comp = asegurar_df(get_data("componentes"), COLS_COMPONENTES)

    # Normalización
    if not df_eq.empty: df_eq['tag'] = df_eq['tag'].astype(str).str.strip().str.upper()
    if not df_sys.empty: 
        df_sys['id'] = limpiar_id(df_sys['id'])
        df_sys['equipo_tag'] = df_sys['equipo_tag'].astype(str).str.strip().str.upper()
    if not df_comp.empty: df_comp['sistema_id'] = limpiar_id(df_comp['sistema_id'])

    # === TAB 1: ÁRBOL ===
    with tab_arbol:
        if df_eq.empty:
            st.info("No hay activos registrados.")
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
                            with st.expander(f"🔹 {eq['nombre']} ({eq['tag']})"):
                                if not df_sys.empty:
                                    sistemas = df_sys[df_sys['equipo_tag'] == str(eq['tag'])]
                                    for _, sys in sistemas.iterrows():
                                        st.markdown(f"**🎛️ {sys['nombre']}**")
                                        if not df_comp.empty:
                                            comps = df_comp[df_comp['sistema_id'] == str(sys['id'])]
                                            for _, comp in comps.iterrows():
                                                st.caption(f"🔧 {comp['nombre']} | {comp['marca']} ({comp['cantidad']})")

    # === TAB 2: GESTIÓN ===
    with tab_manual:
        # Nivel 1 & 2
        plantas_exist = df_eq['planta'].unique().tolist() if not df_eq.empty else []
        planta_val, _ = gestionar_filtro_dinamico("Planta", plantas_exist, "planta")
        
        if planta_val:
            areas_exist = []
            if not df_eq.empty:
                areas_exist = df_eq[df_eq['planta'] == planta_val]['area'].unique().tolist()
            area_val, _ = gestionar_filtro_dinamico("Área", areas_exist, "area")
            
            if area_val:
                st.divider()
                
                # Nivel 3: Equipo
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
                        st.markdown(f"**{'🆕 Nuevo' if es_nuevo_eq else '✏️ Editar'} Equipo**")
                        def_tag = ""; def_tipo = ""; def_crit = ""; eq_idx = None
                        if not es_nuevo_eq:
                            try:
                                equipo_row = df_eq[(df_eq['nombre'] == equipo_sel) & (df_eq['area'] == area_val)].iloc[0]
                                def_tag = equipo_row['tag']; def_tipo = equipo_row['tipo']; def_crit = equipo_row['criticidad']
                                eq_idx = equipo_row.name; tag_equipo = def_tag
                            except: pass

                        with st.form("form_equipo"):
                            val_tag = st.text_input("TAG", value=def_tag).strip().upper()
                            val_tipo = st.text_input("Tipo", value=def_tipo)
                            opts_crit = ["", "Alta", "Media", "Baja"]
                            idx_crit = opts_crit.index(def_crit) if def_crit in opts_crit else 0
                            val_crit = st.selectbox("Criticidad", opts_crit, index=idx_crit)

                            if st.form_submit_button("Guardar Equipo"):
                                if es_nuevo_eq:
                                    new_id = 1
                                    if not df_eq.empty:
                                         try: new_id = int(pd.to_numeric(df_eq['id']).max()) + 1
                                         except: new_id = len(df_eq) + 1
                                    row = pd.DataFrame([{"id": new_id, "tag": val_tag, "nombre": equipo_sel, "planta": planta_val, "area": area_val, "tipo": val_tipo, "criticidad": val_crit, "estado": "Operativo"}])
                                    save_data(pd.concat([df_eq, row], ignore_index=True), "equipos")
                                    # TRUCO DE MEMORIA
                                    st.session_state['sel_equipo'] = equipo_sel
                                    st.success("Creado!"); st.rerun()
                                else:
                                    df_eq.at[eq_idx, 'tag'] = val_tag; df_eq.at[eq_idx, 'tipo'] = val_tipo; df_eq.at[eq_idx, 'criticidad'] = val_crit
                                    save_data(df_eq, "equipos"); st.success("Actualizado!"); st.rerun()

                # Nivel 4: Sistema
                sistema_sel = None; es_nuevo_sys = False; sistema_id = None
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
                            st.markdown(f"**{'🆕 Nuevo' if es_nuevo_sys else '✏️ Editar'} Sistema**")
                            sys_desc_def = ""; sys_idx = None
                            if not es_nuevo_sys and not df_sys.empty:
                                try:
                                    mask = (df_sys['equipo_tag'].astype(str) == str(tag_equipo)) & (df_sys['nombre'] == sistema_sel)
                                    sys_row = df_sys[mask].iloc[0]
                                    sys_desc_def = sys_row['descripcion']; sistema_id = sys_row['id']; sys_idx = sys_row.name
                                except: pass
                            
                            with st.form("form_sistema"):
                                val_desc = st.text_input("Descripción", value=sys_desc_def)
                                if st.form_submit_button("Guardar Sistema"):
                                    if es_nuevo_sys:
                                        new_id = 1
                                        if not df_sys.empty:
                                            try: new_id = int(pd.to_numeric(df_sys['id']).max()) + 1
                                            except: new_id = len(df_sys) + 1
                                        row = pd.DataFrame([{"id": new_id, "equipo_tag": tag_equipo, "nombre": sistema_sel, "descripcion": val_desc}])
                                        save_data(pd.concat([df_sys, row], ignore_index=True), "sistemas")
                                        st.session_state['sel_sistema'] = sistema_sel
                                        st.success("Creado!"); st.rerun()
                                    else:
                                        df_sys.at[sys_idx, 'descripcion'] = val_desc
                                        save_data(df_sys, "sistemas"); st.success("Actualizado!"); st.rerun()

                    # Nivel 5: Componente
                    if sistema_id:
                        st.divider()
                        st.markdown(f"🔧 **Componentes de: {sistema_sel}**")
                        comp_exist = []
                        if not df_comp.empty:
                            sys_id_clean = limpiar_id(pd.Series([sistema_id]))[0]
                            mask_comp = limpiar_id(df_comp['sistema_id']) == sys_id_clean
                            comp_exist = df_comp[mask_comp]['nombre'].tolist()
                        
                        comp_sel, es_nuevo_comp = gestionar_filtro_dinamico("Componente", comp_exist, "comp")
                        
                        if comp_sel:
                            with st.form("form_comp"):
                                st.caption(f"{'🆕 CREANDO' if es_nuevo_comp else '✏️ EDITANDO'}: {comp_sel}")
                                
                                def_marca = ""; def_mod = ""; def_cant = 1; def_cat = ""; def_specs = {}
                                comp_idx = None
                                
                                if not es_nuevo_comp:
                                    try:
                                        sys_id_clean = limpiar_id(pd.Series([sistema_id]))[0]
                                        mask_c = (limpiar_id(df_comp['sistema_id']) == sys_id_clean) & (df_comp['nombre'] == comp_sel)
                                        c_row = df_comp[mask_c].iloc[0]
                                        def_marca = c_row['marca']; def_mod = c_row['modelo']
                                        def_cant = int(c_row['cantidad']) if pd.notna(c_row['cantidad']) else 1
                                        def_cat = c_row['categoria']
                                        if c_row['specs_json']: def_specs = json.loads(c_row['specs_json'])
                                        comp_idx = c_row.name
                                    except: pass

                                c1, c2 = st.columns(2)
                                v_marca = c1.text_input("Marca", value=def_marca)
                                v_mod = c2.text_input("Modelo", value=def_mod)
                                c3, c4 = st.columns(2)
                                v_cant = c3.number_input("Cantidad", min_value=1, value=def_cant)
                                cats = ["Motor Eléctrico", "Motoreductor", "Rodamiento", "Faja", "Bomba"]
                                idx_cat = cats.index(def_cat) if def_cat in cats else 0
                                v_cat = c4.selectbox("Categoría", cats, index=idx_cat)

                                specs_finales = render_specs_dinamicas(v_cat, def_specs)

                                if st.form_submit_button("Guardar Componente"):
                                    specs_str = json.dumps(specs_finales)
                                    if es_nuevo_comp:
                                        new_id = 1
                                        if not df_comp.empty:
                                            try: new_id = int(pd.to_numeric(df_comp['id']).max()) + 1
                                            except: new_id = len(df_comp) + 1
                                        row = pd.DataFrame([{
                                            "id": new_id, "sistema_id": sistema_id, "nombre": comp_sel,
                                            "marca": v_marca, "modelo": v_mod, "cantidad": v_cant,
                                            "categoria": v_cat, "repuesto_sku": "", "specs_json": specs_str
                                        }])
                                        save_data(pd.concat([df_comp, row], ignore_index=True), "componentes")
                                        st.session_state['sel_comp'] = comp_sel
                                        st.success("Guardado!"); st.rerun()
                                    else:
                                        df_comp.at[comp_idx, 'marca'] = v_marca
                                        df_comp.at[comp_idx, 'modelo'] = v_mod
                                        df_comp.at[comp_idx, 'cantidad'] = v_cant
                                        df_comp.at[comp_idx, 'categoria'] = v_cat
                                        df_comp.at[comp_idx, 'specs_json'] = specs_str
                                        save_data(df_comp, "componentes"); st.success("Actualizado!"); st.rerun()

    with tab_masiva:
        st.info("Carga masiva disponible.")
        file = st.file_uploader("Subir Excel", type=["xlsx"])
