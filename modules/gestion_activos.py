import streamlit as st
import pandas as pd
import json
from utils.db_con import get_data, save_data

# --- CONFIGURACIÓN ESTRUCTURAL ---
COLS_EQUIPOS = ["id", "tag", "nombre", "planta", "area", "tipo", "criticidad", "estado"]
COLS_SISTEMAS = ["id", "equipo_tag", "nombre", "descripcion"]
COLS_COMPONENTES = ["id", "sistema_id", "nombre", "marca", "modelo", "cantidad", "categoria", "repuesto_sku", "specs_json"]

# --- FUNCIONES DE LIMPIEZA Y SEGURIDAD ---
def asegurar_df(df, columnas_base):
    if df is None or df.empty: return pd.DataFrame(columns=columnas_base)
    for c in columnas_base:
        if c not in df.columns: df[c] = None
    return df

def limpiar_id(serie):
    return serie.astype(str).str.replace(r"\.0$", "", regex=True).str.strip()

def limpiar_dato(dato):
    if pd.isna(dato) or str(dato).lower() in ['nan', 'none', ''] or str(dato).strip() == "": return "-"
    return str(dato)

def formatear_specs_html_ejecutivo(json_str):
    """Genera una grilla HTML bonita para la vista gerencial."""
    try:
        if not json_str or json_str == "{}": return "<span style='color:#777; font-style:italic;'>Sin especificaciones técnicas.</span>"
        data = json.loads(json_str)
        
        items_html = ""
        for k, v in data.items():
            if v and str(v).lower() not in ['nan', 'none', '']:
                key_nice = k.replace("_", " ").title()
                items_html += f"""
                <div style="background: rgba(255,255,255,0.05); padding: 4px 8px; border-radius: 4px; margin-bottom: 4px;">
                    <span style="color: #bbb; font-size: 0.8em; display: block;">{key_nice}</span>
                    <span style="color: #fff; font-weight: 500; font-size: 0.95em;">{v}</span>
                </div>
                """
        
        if not items_html: return "<span style='color:#777;'>Sin datos detallados.</span>"
        return f"""<div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(120px, 1fr)); gap: 6px; margin-top: 8px;">{items_html}</div>"""
    except:
        return "Error en formato de datos."

# --- SELECTOR INTELIGENTE ---
def gestionar_filtro_dinamico(label, opciones_existentes, key_suffix):
    if opciones_existentes is None: opciones_existentes = []
    opciones_limpias = sorted(list(set([str(x) for x in opciones_existentes if pd.notna(x) and str(x) != ""])))
    opciones_limpias.insert(0, "➕ CREAR NUEVO...")
    opciones_limpias.insert(0, "Seleccionar...")
    
    key_widget = f"sel_{key_suffix}"
    key_force = f"force_{key_suffix}"
    idx_default = 0
    
    if key_force in st.session_state:
        val_force = st.session_state[key_force]
        if val_force in opciones_limpias: idx_default = opciones_limpias.index(val_force)
        del st.session_state[key_force]
    elif key_widget in st.session_state:
        curr = st.session_state[key_widget]
        if curr in opciones_limpias: idx_default = opciones_limpias.index(curr)
    
    seleccion = st.selectbox(f"Seleccione {label}", opciones_limpias, index=idx_default, key=key_widget)
    
    valor_final = None; es_nuevo = False
    if seleccion == "➕ CREAR NUEVO...":
        valor_final = st.text_input(f"Nombre nuevo {label}", key=f"new_{key_suffix}").strip().upper()
        es_nuevo = True
    elif seleccion != "Seleccionar...":
        valor_final = seleccion
        
    return valor_final, es_nuevo

# --- RENDERIZADOR DE INPUTS DE EDICIÓN (CORREGIDO CON KEYS ÚNICAS) ---
def render_campos_dinamicos(categoria, valores_actuales={}, key_prefix="new"):
    """
    Renderiza los inputs dinámicos.
    IMPORTANTE: key_prefix asegura que los campos de un componente no se mezclen con otro.
    """
    specs = {}
    st.markdown("---")
    df_config = get_data("familias_config")
    campos_definidos = []
    
    if not df_config.empty and "nombre_familia" in df_config.columns:
        row = df_config[df_config["nombre_familia"] == categoria]
        if not row.empty:
            try: campos_definidos = json.loads(row.iloc[0]["config_json"])
            except: pass
    
    if campos_definidos:
        st.caption(f"⚙️ Datos Técnicos: {categoria}")
        cols = st.columns(2)
        for i, campo in enumerate(campos_definidos):
            nombre = campo['nombre']
            unidad = campo.get('unidad', '')
            label = f"{nombre} ({unidad})" if unidad else nombre
            val = valores_actuales.get(nombre, "")
            
            # AQUÍ ESTÁ LA SOLUCIÓN: Creamos un ID único para este input
            unique_key = f"{key_prefix}_{nombre}_{i}"
            
            specs[nombre] = cols[i % 2].text_input(label, value=val, key=unique_key)
    else:
        st.info(f"Familia '{categoria}' sin campos definidos.")
        unique_key_obs = f"{key_prefix}_obs"
        specs["Observaciones"] = st.text_area("Detalles", value=valores_actuales.get("Observaciones", ""), key=unique_key_obs)
    return specs

# --- VISTA PRINCIPAL ---
def render_gestion_activos():
    st.header("🏭 Gestión de Activos")
    
    # CSS PARA VISTA EJECUTIVA
    st.markdown("""
    <style>
    .sys-header {
        color: #FF4B4B; font-size: 1.1em; font-weight: bold; 
        margin-top: 15px; margin-bottom: 5px; border-bottom: 1px solid #444; padding-bottom: 5px;
    }
    .tech-card {
        background-color: #1E1E1E; 
        border: 1px solid #333; 
        border-left: 4px solid #FF4B4B; 
        border-radius: 6px; 
        padding: 12px; 
        margin-bottom: 10px;
    }
    .tech-title { font-size: 1em; font-weight: bold; color: white; display: flex; justify-content: space-between;}
    .tech-main-data { 
        display: flex; gap: 15px; margin-bottom: 10px; font-size: 0.9em; color: #ddd; border-bottom: 1px solid #333; padding-bottom: 5px;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Carga de datos
    df_eq = asegurar_df(get_data("equipos"), COLS_EQUIPOS)
    df_sys = asegurar_df(get_data("sistemas"), COLS_SISTEMAS)
    df_comp = asegurar_df(get_data("componentes"), COLS_COMPONENTES)
    df_fam = get_data("familias_config")
    lista_familias = df_fam["nombre_familia"].tolist() if (not df_fam.empty and "nombre_familia" in df_fam.columns) else ["General"]

    # Normalización IDs
    if not df_eq.empty: df_eq['tag'] = df_eq['tag'].astype(str).str.strip().str.upper()
    if not df_sys.empty: df_sys['id'] = limpiar_id(df_sys['id']); df_sys['equipo_tag'] = df_sys['equipo_tag'].astype(str).str.strip().str.upper()
    if not df_comp.empty: df_comp['sistema_id'] = limpiar_id(df_comp['sistema_id'])

    tab_arbol, tab_manual, tab_masiva = st.tabs(["🌳 Visualizar Planta (Gerencia)", "✏️ Gestión & Edición", "📦 Carga Masiva"])

    # ==========================================
    # TAB 1: VISUALIZACIÓN EJECUTIVA
    # ==========================================
    with tab_arbol:
        if df_eq.empty:
            st.info("Planta sin activos configurados.")
        else:
            plantas = df_eq['planta'].unique()
            planta_sel = st.selectbox("Seleccione Planta:", plantas)
            
            if planta_sel:
                areas = df_eq[df_eq['planta'] == planta_sel]['area'].unique()
                for area in areas:
                    with st.expander(f"📍 ÁREA: {area}", expanded=False):
                        equipos_area = df_eq[(df_eq['planta'] == planta_sel) & (df_eq['area'] == area)]
                        
                        for _, eq in equipos_area.iterrows():
                            st.markdown(f"### 🔹 {eq['nombre']} <span style='font-size:0.7em; color:#888;'>({eq['tag']})</span>", unsafe_allow_html=True)
                            c1, c2, c3 = st.columns(3)
                            c1.info(f"**Tipo:** {eq['tipo']}")
                            c2.warning(f"**Criticidad:** {eq['criticidad']}")
                            c3.success(f"**Estado:** {eq['estado']}")
                            
                            if not df_sys.empty:
                                sistemas = df_sys[df_sys['equipo_tag'] == str(eq['tag'])]
                                for _, sys in sistemas.iterrows():
                                    st.markdown(f"<div class='sys-header'>🎛️ SISTEMA: {sys['nombre']}</div>", unsafe_allow_html=True)
                                    if not df_comp.empty:
                                        comps = df_comp[df_comp['sistema_id'] == str(sys['id'])]
                                        if not comps.empty:
                                            for _, c in comps.iterrows():
                                                marca = limpiar_dato(c['marca'])
                                                modelo = limpiar_dato(c['modelo'])
                                                sku = limpiar_dato(c['repuesto_sku'])
                                                html_specs = formatear_specs_html_ejecutivo(c['specs_json'])
                                                
                                                st.markdown(f"""
                                                <div class="tech-card">
                                                    <div class="tech-title">
                                                        <span>🔧 {c['nombre']}</span>
                                                        <span style="background:#FF4B4B; padding:2px 6px; border-radius:4px; font-size:0.7em;">{c['categoria']}</span>
                                                    </div>
                                                    <div class="tech-main-data">
                                                        <span>🏷️ <b>Marca:</b> {marca}</span>
                                                        <span>#️⃣ <b>Mod:</b> {modelo}</span>
                                                        <span>📦 <b>SKU:</b> {sku}</span>
                                                        <span>🔢 <b>Cant:</b> {c['cantidad']}</span>
                                                    </div>
                                                    <div style="margin-top:5px;">{html_specs}</div>
                                                </div>
                                                """, unsafe_allow_html=True)
                                        else: st.caption("   *Sin componentes.*")
                            st.markdown("---")

    # ==========================================
    # TAB 2: GESTIÓN DE DATOS
    # ==========================================
    with tab_manual:
        c_planta, c_area = st.columns(2)
        p_exist = df_eq['planta'].unique().tolist() if not df_eq.empty else []
        with c_planta: p_val, _ = gestionar_filtro_dinamico("Planta", p_exist, "planta")
        
        if p_val:
            a_exist = df_eq[df_eq['planta'] == p_val]['area'].unique().tolist() if not df_eq.empty else []
            with c_area: a_val, _ = gestionar_filtro_dinamico("Área", a_exist, "area")
            
            if a_val:
                st.divider()
                ce1, ce2 = st.columns([1, 2])
                with ce1:
                    e_exist = df_eq[(df_eq['planta'] == p_val) & (df_eq['area'] == a_val)]['nombre'].tolist() if not df_eq.empty else []
                    e_sel, e_new = gestionar_filtro_dinamico("Equipo", e_exist, "equipo")
                
                tag_eq_sel = None
                if e_sel:
                    with ce2:
                        st.caption(f"{'🆕 CREANDO' if e_new else '✏️ EDITANDO'}: {e_sel}")
                        def_tag=""; def_typ=""; def_cri="Media"; eq_idx=None
                        if not e_new and not df_eq.empty:
                            try:
                                r = df_eq[(df_eq['nombre']==e_sel) & (df_eq['area']==a_val)].iloc[0]
                                def_tag=r['tag']; def_typ=r['tipo']; def_cri=r['criticidad']; eq_idx=r.name; tag_eq_sel=def_tag
                            except: pass
                        
                        with st.form("f_eq"):
                            c_a, c_b, c_c = st.columns(3)
                            v_tag = c_a.text_input("TAG", value=def_tag).strip().upper()
                            v_typ = c_b.text_input("Tipo", value=def_typ)
                            v_cri = c_c.selectbox("Criticidad", ["Alta", "Media", "Baja"], index=["Alta", "Media", "Baja"].index(def_cri) if def_cri in ["Alta", "Media", "Baja"] else 1)
                            if st.form_submit_button("Guardar Equipo"):
                                if not v_tag: st.error("Falta TAG")
                                else:
                                    if e_new:
                                        nid = 1 if df_eq.empty else (pd.to_numeric(df_eq['id'], errors='coerce').max() or 0) + 1
                                        row = pd.DataFrame([{"id": nid, "tag": v_tag, "nombre": e_sel, "planta": p_val, "area": a_val, "tipo": v_typ, "criticidad": v_cri, "estado": "Operativo"}])
                                        save_data(pd.concat([df_eq, row], ignore_index=True), "equipos")
                                        st.session_state['force_equipo'] = e_sel
                                    else:
                                        df_eq.at[eq_idx, 'tag'] = v_tag; df_eq.at[eq_idx, 'tipo'] = v_typ; df_eq.at[eq_idx, 'criticidad'] = v_cri
                                        save_data(df_eq, "equipos")
                                    st.success("Listo!"); st.rerun()

                # Sistema
                if tag_eq_sel:
                    st.divider()
                    cs1, cs2 = st.columns([1, 2])
                    with cs1:
                        s_exist = df_sys[df_sys['equipo_tag'].astype(str) == str(tag_eq_sel)]['nombre'].tolist() if not df_sys.empty else []
                        s_sel, s_new = gestionar_filtro_dinamico("Sistema", s_exist, "sistema")
                    
                    sys_id_sel = None
                    if s_sel:
                        with cs2:
                            st.caption(f"{'🆕 CREANDO' if s_new else '✏️ EDITANDO'} SISTEMA")
                            def_desc=""; sys_idx=None
                            if not s_new and not df_sys.empty:
                                try:
                                    r = df_sys[(df_sys['equipo_tag'].astype(str)==str(tag_eq_sel)) & (df_sys['nombre']==s_sel)].iloc[0]
                                    def_desc=r['descripcion']; sys_id_sel=r['id']; sys_idx=r.name
                                except: pass
                            
                            with st.form("f_sys"):
                                v_desc = st.text_input("Descripción", value=def_desc)
                                if st.form_submit_button("Guardar Sistema"):
                                    if s_new:
                                        nid = 1 if df_sys.empty else (pd.to_numeric(df_sys['id'], errors='coerce').max() or 0) + 1
                                        row = pd.DataFrame([{"id": nid, "equipo_tag": tag_eq_sel, "nombre": s_sel, "descripcion": v_desc}])
                                        save_data(pd.concat([df_sys, row], ignore_index=True), "sistemas")
                                        st.session_state['force_sistema'] = s_sel
                                    else:
                                        df_sys.at[sys_idx, 'descripcion'] = v_desc
                                        save_data(df_sys, "sistemas")
                                    st.success("Listo!"); st.rerun()

                    # Componente
                    if sys_id_sel:
                        st.divider()
                        cc1, cc2 = st.columns([1, 2])
                        with cc1:
                            c_exist = []
                            if not df_comp.empty:
                                clean_sys_id = limpiar_id(pd.Series([sys_id_sel]))[0]
                                c_exist = df_comp[limpiar_id(df_comp['sistema_id']) == clean_sys_id]['nombre'].tolist()
                            c_sel, c_new = gestionar_filtro_dinamico("Componente", c_exist, "comp")
                        
                        if c_sel:
                            with cc2:
                                st.caption(f"{'🆕 CREANDO' if c_new else '✏️ EDITANDO'} COMPONENTE")
                                d_mar=""; d_mod=""; d_cant=1; d_cat=lista_familias[0]; d_specs={}
                                c_idx=None; c_sku=""
                                
                                if not c_new and not df_comp.empty:
                                    try:
                                        clean_sys_id = limpiar_id(pd.Series([sys_id_sel]))[0]
                                        r = df_comp[(limpiar_id(df_comp['sistema_id'])==clean_sys_id) & (df_comp['nombre']==c_sel)].iloc[0]
                                        d_mar=r['marca']; d_mod=r['modelo']; d_cant=int(r['cantidad'] or 1); d_cat=r['categoria']; c_sku=r['repuesto_sku']
                                        if r['specs_json']: d_specs=json.loads(r['specs_json'])
                                        c_idx=r.name
                                    except: pass
                                
                                idx_cat = lista_familias.index(d_cat) if d_cat in lista_familias else 0
                                v_cat = st.selectbox("Clase / Familia", lista_familias, index=idx_cat, key="cat_main")
                                
                                with st.form("f_comp"):
                                    col_a, col_b, col_c = st.columns(3)
                                    v_mar = col_a.text_input("Marca", value=d_mar)
                                    v_mod = col_b.text_input("Modelo", value=d_mod)
                                    v_cant = col_c.number_input("Cant", min_value=1, value=d_cant)
                                    v_sku = st.text_input("SKU / Código Repuesto", value=c_sku)
                                    
                                    # --- CLAVE DEL FIX: PASAR UN PREFIJO ÚNICO ---
                                    # Si estamos editando, usamos el ID del componente (c_idx)
                                    # Si es nuevo, usamos 'new_comp'
                                    # Así Streamlit sabe que los campos son únicos para este registro
                                    prefix_unico = str(c_idx) if c_idx is not None else "new_comp"
                                    specs_final = render_campos_dinamicos(v_cat, d_specs, key_prefix=prefix_unico)
                                    
                                    if st.form_submit_button("Guardar Componente"):
                                        js_str = json.dumps(specs_final)
                                        
                                        if c_new:
                                            nid = 1 if df_comp.empty else (pd.to_numeric(df_comp['id'], errors='coerce').max() or 0) + 1
                                            row = pd.DataFrame([{"id": nid, "sistema_id": sys_id_sel, "nombre": c_sel, "marca": v_mar, "modelo": v_mod, "cantidad": v_cant, "categoria": v_cat, "repuesto_sku": v_sku, "specs_json": js_str}])
                                            save_data(pd.concat([df_comp, row], ignore_index=True), "componentes")
                                            st.session_state['force_comp'] = c_sel
                                        else:
                                            df_comp.at[c_idx, 'marca'] = v_mar
                                            df_comp.at[c_idx, 'modelo'] = v_mod
                                            df_comp.at[c_idx, 'cantidad'] = v_cant
                                            df_comp.at[c_idx, 'categoria'] = v_cat
                                            df_comp.at[c_idx, 'repuesto_sku'] = v_sku
                                            df_comp.at[c_idx, 'specs_json'] = js_str
                                            save_data(df_comp, "componentes")
                                        st.success("Guardado!"); st.rerun()

    with tab_masiva:
        st.file_uploader("Subir Excel", type=["xlsx"])
