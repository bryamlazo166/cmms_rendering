import streamlit as st
import pandas as pd
import json
from utils.db_con import get_data, save_data

# --- CONFIGURACIÓN DE ESTRUCTURA (SAP PM STYLE) ---
COLS_EQUIPOS = ["id", "tag", "nombre", "planta", "area", "tipo", "criticidad", "estado"]
COLS_SISTEMAS = ["id", "equipo_tag", "nombre", "descripcion"]
COLS_COMPONENTES = ["id", "sistema_id", "nombre", "marca", "modelo", "cantidad", "categoria", "repuesto_sku", "specs_json"]

# --- FUNCIONES AUXILIARES ROBUSTAS ---
def asegurar_df(df, columnas_base):
    """
    Si el DataFrame está vacío o corrupto, lo reconstruye con las columnas correctas.
    """
    if df is None or df.empty:
        return pd.DataFrame(columns=columnas_base)
    
    # Si faltan columnas, las agregamos vacías
    missing_cols = [c for c in columnas_base if c not in df.columns]
    if missing_cols:
        for c in missing_cols:
            df[c] = None
    return df

def limpiar_id(serie):
    """Limpia los IDs numéricos que Excel convierte a 1.0"""
    return serie.astype(str).str.replace(r"\.0$", "", regex=True).str.strip()

def limpiar_dato(dato):
    if pd.isna(dato) or str(dato).lower() == 'nan' or str(dato).strip() == "": return "-"
    return str(dato)

def formatear_specs_html(json_str):
    try:
        if not json_str or json_str == "{}": return ""
        data = json.loads(json_str)
        items = [f"• <b>{k.replace('_', ' ').title()}:</b> {v}" for k, v in data.items() if v and str(v).lower() != 'nan']
        if not items: return ""
        html = '<div style="display: grid; grid-template-columns: 1fr 1fr; gap: 5px; margin-top: 5px; font-size: 0.9em; color: #cfcfcf;">' + "".join([f'<span>{i}</span>' for i in items]) + '</div>'
        return html
    except: return ""

def gestionar_filtro_dinamico(label, opciones_existentes, key_suffix):
    """
    Maneja la lógica de 'Seleccionar o Crear' con memoria persistente.
    """
    if opciones_existentes is None: opciones_existentes = []
    # Limpiamos y ordenamos opciones
    opciones_limpias = sorted(list(set([str(x) for x in opciones_existentes if pd.notna(x) and str(x) != ""])))
    
    # Agregamos opciones de control
    opciones_limpias.insert(0, "➕ CREAR NUEVO...")
    opciones_limpias.insert(0, "Seleccionar...")
    
    # Recuperamos selección anterior si existe en memoria
    key_widget = f"sel_{key_suffix}"
    idx_default = 0
    
    if key_widget in st.session_state:
        val_memoria = st.session_state[key_widget]
        if val_memoria in opciones_limpias:
            idx_default = opciones_limpias.index(val_memoria)
    
    seleccion = st.selectbox(f"Seleccione {label}", opciones_limpias, index=idx_default, key=key_widget)
    
    valor_final = None
    es_nuevo = False
    
    if seleccion == "➕ CREAR NUEVO...":
        valor_final = st.text_input(f"Escriba nombre para nuevo {label}", key=f"new_{key_suffix}").strip().upper()
        es_nuevo = True
    elif seleccion != "Seleccionar...":
        valor_final = seleccion
        
    return valor_final, es_nuevo

# --- RENDERIZADOR DE CAMPOS DINÁMICOS (LÓGICA MAESTRA) ---
def render_campos_dinamicos(categoria, valores_actuales={}):
    specs = {}
    st.markdown("---")
    
    # 1. Cargar Configuración desde DB
    df_config = get_data("familias_config")
    campos_definidos = []
    
    if not df_config.empty and "nombre_familia" in df_config.columns:
        row = df_config[df_config["nombre_familia"] == categoria]
        if not row.empty:
            try:
                campos_definidos = json.loads(row.iloc[0]["config_json"])
            except: pass
    
    # 2. Renderizar
    if campos_definidos:
        st.caption(f"⚙️ Ficha Técnica: {categoria}")
        cols = st.columns(2)
        for i, campo in enumerate(campos_definidos):
            nombre = campo['nombre']
            unidad = campo.get('unidad', '')
            label_full = f"{nombre} ({unidad})" if unidad else nombre
            val_previo = valores_actuales.get(nombre, "")
            specs[nombre] = cols[i % 2].text_input(label_full, value=val_previo)
    else:
        st.info(f"La familia '{categoria}' no tiene campos configurados. (Configúralo en 'Maestro de Clases')")
        specs["Observaciones"] = st.text_area("Datos Generales", value=valores_actuales.get("Observaciones", ""))
        
    return specs

# --- VISTA PRINCIPAL ---
def render_gestion_activos():
    st.header("🏭 Gestión de Activos (Data-Driven)")
    
    # Estilos CSS (Tema Oscuro)
    st.markdown("""<style>
    .component-card {background-color: #262730; border: 1px solid #444; border-radius: 8px; padding: 10px; margin-top: 5px; border-left: 4px solid #FF4B4B;} 
    input {color: black !important;}
    </style>""", unsafe_allow_html=True)
    
    tab_arbol, tab_manual, tab_masiva = st.tabs(["🌳 Visualizar Árbol", "✏️ Gestión & Edición", "📦 Carga Masiva"])

    # Carga Segura de Datos
    df_eq = asegurar_df(get_data("equipos"), COLS_EQUIPOS)
    df_sys = asegurar_df(get_data("sistemas"), COLS_SISTEMAS)
    df_comp = asegurar_df(get_data("componentes"), COLS_COMPONENTES)
    df_fam = get_data("familias_config")
    
    lista_familias = df_fam["nombre_familia"].tolist() if (not df_fam.empty and "nombre_familia" in df_fam.columns) else ["GENERAL"]

    # Normalización IDs (Evita errores de enlace)
    if not df_eq.empty: df_eq['tag'] = df_eq['tag'].astype(str).str.strip().str.upper()
    if not df_sys.empty: df_sys['id'] = limpiar_id(df_sys['id']); df_sys['equipo_tag'] = df_sys['equipo_tag'].astype(str).str.strip().str.upper()
    if not df_comp.empty: df_comp['sistema_id'] = limpiar_id(df_comp['sistema_id'])

    # === TAB 1: ÁRBOL ===
    with tab_arbol:
        if df_eq.empty: st.info("El sistema está vacío. Ve a la pestaña 'Gestión & Edición' para crear tu Planta.")
        else:
            for planta in df_eq['planta'].unique():
                if pd.isna(planta): continue
                with st.expander(f"🏭 {planta}", expanded=True):
                    for area in df_eq[df_eq['planta'] == planta]['area'].unique():
                        st.markdown(f"### 📍 {area}")
                        for _, eq in df_eq[(df_eq['planta'] == planta) & (df_eq['area'] == area)].iterrows():
                            with st.expander(f"🔹 {eq['nombre']} ({eq['tag']})"):
                                if not df_sys.empty:
                                    for _, sys in df_sys[df_sys['equipo_tag'] == str(eq['tag'])].iterrows():
                                        st.markdown(f"**🎛️ {sys['nombre']}**")
                                        if not df_comp.empty:
                                            comps = df_comp[df_comp['sistema_id'] == str(sys['id'])]
                                            for _, c in comps.iterrows():
                                                specs_html = formatear_specs_html(c['specs_json'])
                                                st.markdown(f"""<div class="component-card"><strong>🔧 {c['nombre']}</strong> <small>({c['categoria']})</small><br>Marca: {limpiar_dato(c['marca'])} | Mod: {limpiar_dato(c['modelo'])}<br>{specs_html}</div>""", unsafe_allow_html=True)

    # === TAB 2: GESTIÓN (FORMULARIO CASCADA) ===
    with tab_manual:
        # NIVEL 1: PLANTA
        plantas_exist = df_eq['planta'].unique().tolist() if not df_eq.empty else []
        planta_val, _ = gestionar_filtro_dinamico("Planta", plantas_exist, "planta")
        
        if planta_val:
            # NIVEL 2: ÁREA
            areas_exist = df_eq[df_eq['planta'] == planta_val]['area'].unique().tolist() if not df_eq.empty else []
            area_val, _ = gestionar_filtro_dinamico("Área", areas_exist, "area")
            
            if area_val:
                st.divider()
                
                # NIVEL 3: EQUIPO
                col_eq1, col_eq2 = st.columns(2)
                with col_eq1:
                    eqs_exist = df_eq[(df_eq['planta'] == planta_val) & (df_eq['area'] == area_val)]['nombre'].tolist() if not df_eq.empty else []
                    equipo_sel, es_nuevo_eq = gestionar_filtro_dinamico("Equipo", eqs_exist, "equipo")

                equipo_row = None; tag_equipo = None
                
                # Si tenemos un nombre de equipo (seleccionado o escrito) mostramos el formulario
                if equipo_sel:
                    with col_eq2:
                        st.markdown(f"**{'🆕 Nuevo' if es_nuevo_eq else '✏️ Editar'} Equipo**")
                        def_tag = ""; def_tipo = ""; def_crit = ""; eq_idx = None
                        if not es_nuevo_eq and not df_eq.empty:
                            try:
                                equipo_row = df_eq[(df_eq['nombre'] == equipo_sel) & (df_eq['area'] == area_val)].iloc[0]
                                def_tag = equipo_row['tag']; def_tipo = equipo_row['tipo']; def_crit = equipo_row['criticidad']
                                eq_idx = equipo_row.name; tag_equipo = def_tag
                            except: pass

                        with st.form("form_equipo"):
                            val_tag = st.text_input("TAG (Único)", value=def_tag).strip().upper()
                            val_tipo = st.text_input("Tipo Equipo", value=def_tipo)
                            opts_crit = ["", "Alta", "Media", "Baja"]
                            idx_crit = opts_crit.index(def_crit) if def_crit in opts_crit else 0
                            val_crit = st.selectbox("Criticidad", opts_crit, index=idx_crit)

                            if st.form_submit_button("Guardar Equipo"):
                                if not val_tag:
                                    st.error("El TAG es obligatorio")
                                else:
                                    if es_nuevo_eq:
                                        new_id = 1
                                        if not df_eq.empty:
                                             try: new_id = int(pd.to_numeric(df_eq['id']).max()) + 1
                                             except: new_id = len(df_eq) + 1
                                        row = pd.DataFrame([{"id": new_id, "tag": val_tag, "nombre": equipo_sel, "planta": planta_val, "area": area_val, "tipo": val_tipo, "criticidad": val_crit, "estado": "Operativo"}])
                                        save_data(pd.concat([df_eq, row], ignore_index=True), "equipos")
                                        # ¡MAGIA! Forzamos la memoria para que no se resetee
                                        st.session_state['sel_equipo'] = equipo_sel 
                                        st.success("Creado!"); st.rerun()
                                    else:
                                        df_eq.at[eq_idx, 'tag'] = val_tag; df_eq.at[eq_idx, 'tipo'] = val_tipo; df_eq.at[eq_idx, 'criticidad'] = val_crit
                                        save_data(df_eq, "equipos"); st.success("Actualizado!"); st.rerun()

                # NIVEL 4: SISTEMA (Solo si hay equipo TAG guardado)
                if tag_equipo:
                    st.divider()
                    col_sys1, col_sys2 = st.columns(2)
                    with col_sys1:
                        sys_exist = df_sys[df_sys['equipo_tag'].astype(str) == str(tag_equipo)]['nombre'].tolist() if not df_sys.empty else []
                        sistema_sel, es_nuevo_sys = gestionar_filtro_dinamico("Sistema", sys_exist, "sistema")
                    
                    sistema_id = None
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
                                val_desc = st.text_input("Descripción Sistema", value=sys_desc_def)
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

                    # NIVEL 5: COMPONENTE (Solo si hay sistema ID guardado)
                    if sistema_id:
                        st.divider()
                        col_comp1, col_comp2 = st.columns([1, 2])
                        with col_comp1:
                            comp_exist = []
                            if not df_comp.empty:
                                sys_clean = limpiar_id(pd.Series([sistema_id]))[0]
                                mask = limpiar_id(df_comp['sistema_id']) == sys_clean
                                comp_exist = df_comp[mask]['nombre'].tolist()
                            comp_sel, es_nuevo_comp = gestionar_filtro_dinamico("Componente", comp_exist, "comp")
                        
                        if comp_sel:
                            st.caption(f"{'🆕 CREANDO' if es_nuevo_comp else '✏️ EDITANDO'}: {comp_sel}")
                            
                            def_marca = ""; def_mod = ""; def_cant = 1; def_cat = lista_familias[0]; def_specs = {}
                            comp_idx = None
                            
                            if not es_nuevo_comp:
                                try:
                                    sys_clean = limpiar_id(pd.Series([sistema_id]))[0]
                                    mask_c = (limpiar_id(df_comp['sistema_id']) == sys_clean) & (df_comp['nombre'] == comp_sel)
                                    c_row = df_comp[mask_c].iloc[0]
                                    def_marca = c_row['marca']; def_mod = c_row['modelo']; def_cant = int(c_row['cantidad'])
                                    def_cat = c_row['categoria']
                                    if c_row['specs_json']: def_specs = json.loads(c_row['specs_json'])
                                    comp_idx = c_row.name
                                except: pass

                            # SELECTOR DE CATEGORÍA FUERA DEL FORM
                            idx_cat = lista_familias.index(def_cat) if def_cat in lista_familias else 0
                            v_cat = st.selectbox("Familia / Clase", lista_familias, index=idx_cat)

                            with st.form("form_comp_sap"):
                                c1, c2 = st.columns(2)
                                v_marca = c1.text_input("Marca", value=def_marca)
                                v_mod = c2.text_input("Modelo", value=def_mod)
                                v_cant = st.number_input("Cantidad", min_value=1, value=def_cant)
                                
                                # Renderizado Dinámico
                                specs_finales = render_campos_dinamicos(v_cat, def_specs)

                                # Repuesto
                                df_alm = get_data("almacen")
                                opts_alm = ["Ninguno"]
                                if not df_alm.empty:
                                    opts_alm += (df_alm['sku'] + " | " + df_alm['descripcion']).tolist()
                                v_rep = st.selectbox("Repuesto Vinculado", opts_alm)

                                if st.form_submit_button("Guardar Componente"):
                                    specs_str = json.dumps(specs_finales)
                                    sku_clean = v_rep.split(" | ")[0] if "|" in v_rep else ""
                                    
                                    if es_nuevo_comp:
                                        new_id = 1
                                        if not df_comp.empty:
                                            try: new_id = int(pd.to_numeric(df_comp['id']).max()) + 1
                                            except: new_id = len(df_comp) + 1
                                        row = pd.DataFrame([{
                                            "id": new_id, "sistema_id": sistema_id, "nombre": comp_sel,
                                            "marca": v_marca, "modelo": v_mod, "cantidad": v_cant,
                                            "categoria": v_cat, "repuesto_sku": sku_clean, "specs_json": specs_str
                                        }])
                                        save_data(pd.concat([df_comp, row], ignore_index=True), "componentes")
                                        st.session_state['sel_comp'] = comp_sel
                                        st.success("Guardado!"); st.rerun()
                                    else:
                                        df_comp.at[comp_idx, 'marca'] = v_marca
                                        df_comp.at[comp_idx, 'modelo'] = v_mod
                                        df_comp.at[comp_idx, 'cantidad'] = v_cant
                                        df_comp.at[comp_idx, 'categoria'] = v_cat
                                        df_comp.at[comp_idx, 'repuesto_sku'] = sku_clean
                                        df_comp.at[comp_idx, 'specs_json'] = specs_str
                                        save_data(df_comp, "componentes")
                                        st.success("Actualizado!"); st.rerun()

    with tab_masiva:
        st.info("Carga masiva disponible.")
        file = st.file_uploader("Subir Excel", type=["xlsx"])
