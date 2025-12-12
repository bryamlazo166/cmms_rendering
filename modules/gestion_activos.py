import streamlit as st
import pandas as pd
import json
from utils.db_con import get_data, save_data

# --- CONFIGURACIÓN ESTRUCTURAL ---
COLS_EQUIPOS = ["id", "tag", "nombre", "planta", "area", "tipo", "criticidad", "estado"]
COLS_SISTEMAS = ["id", "equipo_tag", "nombre", "descripcion"]
COLS_COMPONENTES = ["id", "sistema_id", "nombre", "marca", "modelo", "cantidad", "categoria", "repuesto_sku", "specs_json"]

# --- FUNCIONES AUXILIARES ---
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
    try:
        if not json_str or json_str == "{}": return "<span style='color:#777; font-style:italic;'>-</span>"
        data = json.loads(json_str)
        items_html = ""
        for k, v in data.items():
            if v and str(v).lower() not in ['nan', 'none', '']:
                items_html += f"""
                <div style="background: rgba(255,255,255,0.08); padding: 3px 6px; border-radius: 3px;">
                    <span style="color: #aaa; font-size: 0.7em; display: block;">{k}</span>
                    <span style="color: #fff; font-weight: 600; font-size: 0.85em;">{v}</span>
                </div>
                """
        return f"""<div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(90px, 1fr)); gap: 4px; margin-top: 4px;">{items_html}</div>"""
    except: return ""

# --- SELECTOR "PEGAJOSO" (ESTO EVITA EL REINICIO) ---
def gestionar_filtro_dinamico_persistente(label, opciones_existentes, key_unique):
    """
    Selector que prioriza mantener el valor seleccionado en session_state
    sobre cualquier reseteo de la página.
    """
    if opciones_existentes is None: opciones_existentes = []
    lista_opciones = sorted(list(set([str(x) for x in opciones_existentes if pd.notna(x) and str(x) != ""])))
    lista_opciones.insert(0, "➕ CREAR NUEVO...")
    lista_opciones.insert(0, "Seleccionar...")
    
    # Claves de estado
    key_widget = f"sel_{key_unique}"
    key_force = f"force_{key_unique}"
    
    # Determinar índice
    idx = 0
    
    # 1. ¿Hay orden de fuerza? (Viene de guardar un nuevo item)
    if key_force in st.session_state:
        val = st.session_state[key_force]
        if val in lista_opciones: idx = lista_opciones.index(val)
        del st.session_state[key_force] # Consumir orden
        
    # 2. ¿Hay selección previa válida?
    elif key_widget in st.session_state:
        if st.session_state[key_widget] in lista_opciones:
            idx = lista_opciones.index(st.session_state[key_widget])
    
    seleccion = st.selectbox(f"Seleccione {label}", lista_opciones, index=idx, key=key_widget)
    
    valor_final = None
    es_nuevo = False
    
    if seleccion == "➕ CREAR NUEVO...":
        valor_final = st.text_input(f"Nombre nuevo {label}", key=f"new_{key_unique}").strip().upper()
        es_nuevo = True
    elif seleccion != "Seleccionar...":
        valor_final = seleccion
        
    return valor_final, es_nuevo

# --- RENDERIZADOR CAMPOS ---
def render_campos_dinamicos(categoria, valores_actuales={}, key_prefix="new"):
    specs = {}
    st.markdown("---")
    df_config = get_data("familias_config")
    
    campos = []
    if not df_config.empty and "nombre_familia" in df_config.columns:
        row = df_config[df_config["nombre_familia"] == categoria]
        if not row.empty:
            try: campos = json.loads(row.iloc[0]["config_json"])
            except: pass
            
    if campos:
        st.caption(f"⚙️ Datos Técnicos: {categoria}")
        cols = st.columns(2)
        for i, campo in enumerate(campos):
            nom = campo['nombre']
            uni = campo.get('unidad','')
            lbl = f"{nom} ({uni})" if uni else nom
            specs[nom] = cols[i%2].text_input(lbl, value=valores_actuales.get(nom,""), key=f"{key_prefix}_{nom}_{i}")
    else:
        st.info("Sin configuración específica.")
        specs["General"] = st.text_area("Detalles", value=valores_actuales.get("General",""), key=f"{key_prefix}_gen")
    return specs

# --- MAIN RENDER ---
def render_gestion_activos():
    st.header("🏭 Gestión de Activos")
    
    st.markdown("""<style>
    .sys-header { background: #262730; color: #FF4B4B; padding: 5px 10px; border-radius: 4px; font-weight: bold; margin-top: 15px; border-left: 3px solid #FF4B4B; }
    .comp-row { margin-left: 15px; padding: 8px; border-bottom: 1px solid #333; }
    .comp-title { color: #fff; font-weight: 600; }
    .comp-meta { color: #aaa; font-size: 0.85em; }
    </style>""", unsafe_allow_html=True)

    # Carga de Datos
    df_eq = asegurar_df(get_data("equipos"), COLS_EQUIPOS)
    df_sys = asegurar_df(get_data("sistemas"), COLS_SISTEMAS)
    df_comp = asegurar_df(get_data("componentes"), COLS_COMPONENTES)
    df_fam_conf = get_data("familias_config")
    df_sys_conf = get_data("sistemas_config")

    # Listas Maestras
    list_familias = df_fam_conf["nombre_familia"].tolist() if not df_fam_conf.empty else ["GENERAL"]
    list_sistemas_std = df_sys_conf["nombre_sistema"].tolist() if not df_sys_conf.empty else []

    # Normalizar IDs
    if not df_eq.empty: df_eq['tag'] = df_eq['tag'].astype(str).str.strip().str.upper()
    if not df_sys.empty: df_sys['id'] = limpiar_id(df_sys['id']); df_sys['equipo_tag'] = df_sys['equipo_tag'].astype(str).str.strip().str.upper()
    if not df_comp.empty: df_comp['sistema_id'] = limpiar_id(df_comp['sistema_id'])

    tab_arbol, tab_manual, tab_masiva = st.tabs(["🌳 Visualizar Planta", "✏️ Gestión & Edición", "📦 Carga Masiva"])

    # === TAB 1: VISUALIZACIÓN ===
    with tab_arbol:
        if df_eq.empty: st.warning("Sin datos.")
        else:
            planta_sel = st.selectbox("Planta:", df_eq['planta'].unique())
            if planta_sel:
                for area in df_eq[df_eq['planta']==planta_sel]['area'].unique():
                    with st.expander(f"📍 {area}", expanded=False):
                        eqs = df_eq[(df_eq['planta']==planta_sel) & (df_eq['area']==area)]
                        for _, eq in eqs.iterrows():
                            st.markdown(f"### 🔹 {eq['nombre']} <small>({eq['tag']})</small>", unsafe_allow_html=True)
                            
                            if not df_sys.empty:
                                sistemas = df_sys[df_sys['equipo_tag'] == str(eq['tag'])]
                                for _, sys in sistemas.iterrows():
                                    st.markdown(f"<div class='sys-header'>🎛️ {sys['nombre']}</div>", unsafe_allow_html=True)
                                    if sys['descripcion']: st.caption(sys['descripcion'])
                                    
                                    if not df_comp.empty:
                                        comps = df_comp[df_comp['sistema_id'] == str(sys['id'])]
                                        for _, c in comps.iterrows():
                                            specs = formatear_specs_html_ejecutivo(c['specs_json'])
                                            st.markdown(f"""
                                            <div class='comp-row'>
                                                <div class='comp-title'>🔧 {c['nombre']} <span style='background:#444; padding:2px 5px; font-size:0.7em; border-radius:3px;'>{c['categoria']}</span></div>
                                                <div class='comp-meta'>Marca: {limpiar_dato(c['marca'])} | Mod: {limpiar_dato(c['modelo'])} | Cant: {c['cantidad']}</div>
                                                {specs}
                                            </div>
                                            """, unsafe_allow_html=True)
                            st.markdown("---")

    # === TAB 2: GESTIÓN (CON MEMORIA ANTI-FLICKER) ===
    with tab_manual:
        c1, c2 = st.columns(2)
        
        # 1. PLANTA
        l_planta = df_eq['planta'].unique().tolist() if not df_eq.empty else []
        with c1: v_planta, _ = gestionar_filtro_dinamico_persistente("Planta", l_planta, "planta")
        
        if v_planta:
            # 2. ÁREA
            l_area = df_eq[df_eq['planta']==v_planta]['area'].unique().tolist() if not df_eq.empty else []
            with c2: v_area, _ = gestionar_filtro_dinamico_persistente("Área", l_area, "area")
            
            if v_area:
                st.divider()
                ce1, ce2 = st.columns([1,2])
                with ce1:
                    l_eq = df_eq[(df_eq['planta']==v_planta) & (df_eq['area']==v_area)]['nombre'].tolist() if not df_eq.empty else []
                    sel_eq, new_eq = gestionar_filtro_dinamico_persistente("Equipo", l_eq, "equipo")
                
                tag_eq = None
                if sel_eq:
                    with ce2: # Formulario Equipo
                        st.caption(f"{'🆕 CREANDO' if new_eq else '✏️ EDITANDO'}: {sel_eq}")
                        d_tag=""; d_typ=""; eq_idx=None
                        if not new_eq and not df_eq.empty:
                            try:
                                r = df_eq[(df_eq['nombre']==sel_eq)&(df_eq['area']==v_area)].iloc[0]
                                d_tag=r['tag']; d_typ=r['tipo']; eq_idx=r.name; tag_eq=d_tag
                            except: pass
                        
                        with st.form("f_eq"):
                            ct1, ct2 = st.columns(2)
                            i_tag = ct1.text_input("TAG", value=d_tag).strip().upper()
                            i_typ = ct2.text_input("Tipo", value=d_typ)
                            if st.form_submit_button("Guardar Equipo"):
                                if not i_tag: st.error("TAG requerido")
                                else:
                                    if new_eq:
                                        nid = 1 if df_eq.empty else (pd.to_numeric(df_eq['id'], errors='coerce').max() or 0)+1
                                        row = pd.DataFrame([{"id":nid, "tag":i_tag, "nombre":sel_eq, "planta":v_planta, "area":v_area, "tipo":i_typ, "criticidad":"Media", "estado":"OK"}])
                                        save_data(pd.concat([df_eq, row], ignore_index=True), "equipos")
                                        st.session_state['force_equipo'] = sel_eq # MEMORIA
                                    else:
                                        df_eq.at[eq_idx,'tag']=i_tag; df_eq.at[eq_idx,'tipo']=i_typ
                                        save_data(df_eq, "equipos")
                                    st.success("Ok"); st.rerun()

                # 4. SISTEMA
                if tag_eq:
                    st.divider()
                    cs1, cs2 = st.columns([1,2])
                    with cs1:
                        # Buscamos sistemas de este equipo
                        l_sys = df_sys[df_sys['equipo_tag'].astype(str)==str(tag_eq)]['nombre'].tolist() if not df_sys.empty else []
                        sel_sys, new_sys = gestionar_filtro_dinamico_persistente("Sistema", l_sys, "sistema")
                    
                    id_sys = None
                    if sel_sys:
                        with cs2:
                            st.caption(f"{'🆕 CREANDO' if new_sys else '✏️ EDITANDO'} SISTEMA")
                            
                            # Pre-llenado de datos
                            d_desc=""; sys_idx=None
                            
                            # Si es nuevo, intentamos ver si el nombre coincide con un estándar
                            if new_sys and sel_sys in list_sistemas_std:
                                try: d_desc = df_sys_conf[df_sys_conf['nombre_sistema']==sel_sys].iloc[0]['descripcion']
                                except: pass
                            
                            if not new_sys and not df_sys.empty:
                                try:
                                    r = df_sys[(df_sys['equipo_tag'].astype(str)==str(tag_eq))&(df_sys['nombre']==sel_sys)].iloc[0]
                                    d_desc=r['descripcion']; id_sys=r['id']; sys_idx=r.name
                                except: pass
                            
                            # Selector de tipo estándar si es nuevo, o texto libre
                            with st.form("f_sys"):
                                if new_sys:
                                    # Aquí usamos el Maestro de Sistemas para sugerir nombres
                                    st.write(f"Nombre: **{sel_sys}**")
                                    if not list_sistemas_std: st.warning("No hay sistemas estándar configurados.")
                                    else: st.info("Tip: Usa nombres del maestro para estandarizar.")
                                i_desc = st.text_input("Descripción", value=d_desc)
                                
                                if st.form_submit_button("Guardar Sistema"):
                                    if new_sys:
                                        nid = 1 if df_sys.empty else (pd.to_numeric(df_sys['id'], errors='coerce').max() or 0)+1
                                        row = pd.DataFrame([{"id":nid, "equipo_tag":tag_eq, "nombre":sel_sys, "descripcion":i_desc}])
                                        save_data(pd.concat([df_sys, row], ignore_index=True), "sistemas")
                                        st.session_state['force_sistema'] = sel_sys # MEMORIA
                                    else:
                                        df_sys.at[sys_idx,'descripcion']=i_desc
                                        save_data(df_sys, "sistemas")
                                    st.success("Ok"); st.rerun()

                    # 5. COMPONENTE
                    if id_sys:
                        st.divider()
                        cc1, cc2 = st.columns([1,2])
                        with cc1:
                            l_comp = []
                            if not df_comp.empty:
                                clean_id = limpiar_id(pd.Series([id_sys]))[0]
                                l_comp = df_comp[limpiar_id(df_comp['sistema_id'])==clean_id]['nombre'].tolist()
                            sel_comp, new_comp = gestionar_filtro_dinamico_persistente("Componente", l_comp, "comp")
                        
                        if sel_comp:
                            with cc2:
                                st.caption(f"{'🆕 CREANDO' if new_comp else '✏️ EDITANDO'}: {sel_comp}")
                                d_mar=""; d_mod=""; d_cant=1; d_cat=list_familias[0]; d_specs={}
                                c_idx=None; c_sku=""
                                
                                if not new_comp and not df_comp.empty:
                                    try:
                                        clean_id = limpiar_id(pd.Series([id_sys]))[0]
                                        r = df_comp[(limpiar_id(df_comp['sistema_id'])==clean_id)&(df_comp['nombre']==sel_comp)].iloc[0]
                                        d_mar=r['marca']; d_mod=r['modelo']; d_cant=int(r['cantidad'] or 1); d_cat=r['categoria']; c_sku=r['repuesto_sku']
                                        if r['specs_json']: d_specs=json.loads(r['specs_json'])
                                        c_idx=r.name
                                    except: pass
                                
                                # Selector de Familia (Fuera del Form)
                                ix_c = list_familias.index(d_cat) if d_cat in list_familias else 0
                                v_cat = st.selectbox("Clase / Familia (Maestro)", list_familias, index=ix_c, key="fam_comp")
                                
                                with st.form("f_comp"):
                                    c_1, c_2, c_3 = st.columns(3)
                                    v_mar = c_1.text_input("Marca", value=d_mar)
                                    v_mod = c_2.text_input("Modelo", value=d_mod)
                                    v_cant = c_3.number_input("Cant", 1, value=d_cant)
                                    v_sku = st.text_input("SKU", value=c_sku)
                                    
                                    # Campos dinámicos (Usamos ID o 'new' para key única)
                                    k_pref = str(c_idx) if c_idx is not None else "new"
                                    specs_end = render_campos_dinamicos(v_cat, d_specs, key_prefix=k_pref)
                                    
                                    if st.form_submit_button("Guardar Componente"):
                                        js_str = json.dumps(specs_end)
                                        if new_comp:
                                            nid = 1 if df_comp.empty else (pd.to_numeric(df_comp['id'], errors='coerce').max() or 0)+1
                                            row = pd.DataFrame([{"id":nid, "sistema_id":id_sys, "nombre":sel_comp, "categoria":v_cat, "marca":v_mar, "modelo":v_mod, "cantidad":v_cant, "repuesto_sku":v_sku, "specs_json":js_str}])
                                            save_data(pd.concat([df_comp, row], ignore_index=True), "componentes")
                                            st.session_state['force_comp'] = sel_comp # MEMORIA
                                        else:
                                            df_comp.at[c_idx,'marca']=v_mar; df_comp.at[c_idx,'modelo']=v_mod
                                            df_comp.at[c_idx,'cantidad']=v_cant; df_comp.at[c_idx,'categoria']=v_cat
                                            df_comp.at[c_idx,'repuesto_sku']=v_sku; df_comp.at[c_idx,'specs_json']=js_str
                                            save_data(df_comp, "componentes")
                                        st.success("Ok"); st.rerun()

    with tab_masiva:
        st.file_uploader("Carga Masiva", type=["xlsx"])
