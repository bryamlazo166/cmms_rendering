import streamlit as st
import pandas as pd
import json
from utils.db_con import get_data, save_data

# --- CONFIGURACIÓN ---
COLS_EQUIPOS = ["id", "tag", "nombre", "planta", "area", "tipo", "criticidad", "estado"]
COLS_SISTEMAS = ["id", "equipo_tag", "nombre", "descripcion"]
COLS_COMPONENTES = ["id", "sistema_id", "nombre", "marca", "modelo", "cantidad", "categoria", "repuesto_sku", "specs_json"]

# --- HELPERS ---
def asegurar_df(df, columnas_base):
    if df.empty or len(df.columns) == 0: return pd.DataFrame(columns=columnas_base)
    for col in columnas_base:
        if col not in df.columns: df[col] = None
    return df

def limpiar_id(serie):
    return serie.astype(str).str.replace(r"\.0$", "", regex=True).str.strip()

def limpiar_dato(dato):
    if pd.isna(dato) or str(dato).lower() == 'nan' or str(dato).strip() == "": return "-"
    return str(dato)

def formatear_specs_html(json_str):
    try:
        if not json_str or json_str == "{}": return ""
        data = json.loads(json_str)
        items = [f"• <b>{k}:</b> {v}" for k, v in data.items() if v and str(v).lower() != 'nan']
        if not items: return ""
        html = '<div style="display: grid; grid-template-columns: 1fr 1fr; gap: 5px; margin-top: 5px; font-size: 0.9em; color: #cfcfcf;">' + "".join([f'<span>{i}</span>' for i in items]) + '</div>'
        return html
    except: return ""

def gestionar_filtro_dinamico(label, opciones_existentes, key_suffix):
    if opciones_existentes is None: opciones_existentes = []
    opciones = sorted(list(set([str(x) for x in opciones_existentes if pd.notna(x) and str(x) != ""])))
    opciones.insert(0, "➕ CREAR NUEVO..."); opciones.insert(0, "Seleccionar...")
    sel = st.selectbox(f"Seleccione {label}", opciones, key=f"sel_{key_suffix}")
    
    if sel == "➕ CREAR NUEVO...":
        val = st.text_input(f"Nuevo {label}", key=f"new_{key_suffix}").strip().upper()
        return val, True
    elif sel != "Seleccionar...":
        return sel, False
    return None, False

# --- LÓGICA DINÁMICA DE CAMPOS (CONECTADA A DB) ---
def render_specs_dinamicas_db(categoria, valores_actuales={}):
    """
    Lee la hoja 'familias_config' y genera los campos definidos por el usuario.
    """
    specs = {}
    st.markdown("---")
    
    # 1. Cargar configuración desde Google Sheets
    df_config = get_data("familias_config")
    
    campos_definidos = []
    
    # Buscar si existe la familia
    if not df_config.empty:
        row = df_config[df_config["nombre_familia"] == categoria]
        if not row.empty:
            try:
                campos_definidos = json.loads(row.iloc[0]["config_json"])
            except: pass
    
    # 2. Renderizar campos
    if campos_definidos:
        st.caption(f"⚙️ Datos Específicos para: {categoria}")
        # Crear grid dinámico (2 columnas)
        cols = st.columns(2)
        
        for i, campo_def in enumerate(campos_definidos):
            nombre_campo = campo_def['nombre']
            col_idx = i % 2
            
            # Recuperar valor previo si existe (Edición)
            val_previo = valores_actuales.get(nombre_campo, "")
            
            # Generar Input
            specs[nombre_campo] = cols[col_idx].text_input(nombre_campo, value=val_previo)
    else:
        # Fallback si no hay configuración
        st.info(f"La familia '{categoria}' no tiene campos configurados. Ve al módulo 'Configuración' para agregarlos.")
        specs["Detalles Generales"] = st.text_area("Detalles", value=valores_actuales.get("Detalles Generales", ""))
        
    return specs

# --- VISTA PRINCIPAL ---
def render_gestion_activos():
    st.header("🏭 Gestión de Activos")
    
    # Estilos CSS
    st.markdown("""<style>.component-card {background-color: #262730; border: 1px solid #444; border-radius: 8px; padding: 10px; margin-top: 5px; border-left: 4px solid #FF4B4B;} input {color: black !important;}</style>""", unsafe_allow_html=True)
    
    tab_arbol, tab_manual = st.tabs(["🌳 Visualizar Árbol", "✏️ Gestión & Edición"])

    # Carga datos
    df_eq = asegurar_df(get_data("equipos"), COLS_EQUIPOS)
    df_sys = asegurar_df(get_data("sistemas"), COLS_SISTEMAS)
    df_comp = asegurar_df(get_data("componentes"), COLS_COMPONENTES)
    # Cargar lista de familias disponibles para el dropdown
    df_familias = get_data("familias_config")
    lista_familias = df_familias["nombre_familia"].tolist() if not df_familias.empty else ["General"]

    # Normalización IDs
    if not df_eq.empty: df_eq['tag'] = df_eq['tag'].astype(str).str.strip().str.upper()
    if not df_sys.empty: df_sys['id'] = limpiar_id(df_sys['id']); df_sys['equipo_tag'] = df_sys['equipo_tag'].astype(str).str.strip().str.upper()
    if not df_comp.empty: df_comp['sistema_id'] = limpiar_id(df_comp['sistema_id'])

    with tab_arbol:
        if df_eq.empty: st.info("Sin datos.")
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

    with tab_manual:
        # ... (Código de Planta/Area/Equipo/Sistema igual que antes, resumido para foco en Componente) ...
        # [Aquí va la lógica de niveles 1-4 que ya tenías, la omito para no exceder longitud, PEGA LA ANTERIOR AQUÍ]
        # Si quieres el código completo 100% incluyendo niveles 1-4, avísame. 
        # Asumiré que integras esta parte o te doy el bloque completo abajo.
        
        # ... (Imaginemos que llegamos al Nivel 5: Componente) ...
        # Simulamos la selección previa para mostrar el cambio:
        
        plantas_exist = df_eq['planta'].unique().tolist() if not df_eq.empty else []
        planta_val, _ = gestionar_filtro_dinamico("Planta", plantas_exist, "planta")
        if planta_val:
            areas_exist = df_eq[df_eq['planta'] == planta_val]['area'].unique().tolist() if not df_eq.empty else []
            area_val, _ = gestionar_filtro_dinamico("Área", areas_exist, "area")
            if area_val:
                eqs_exist = df_eq[(df_eq['planta'] == planta_val) & (df_eq['area'] == area_val)]['nombre'].tolist() if not df_eq.empty else []
                equipo_sel, es_nuevo_eq = gestionar_filtro_dinamico("Equipo", eqs_exist, "equipo")
                
                tag_equipo = None
                if equipo_sel and not es_nuevo_eq:
                     tag_equipo = df_eq[(df_eq['nombre'] == equipo_sel) & (df_eq['area'] == area_val)].iloc[0]['tag']

                if tag_equipo:
                    sys_exist = df_sys[df_sys['equipo_tag'].astype(str) == str(tag_equipo)]['nombre'].tolist() if not df_sys.empty else []
                    sistema_sel, es_nuevo_sys = gestionar_filtro_dinamico("Sistema", sys_exist, "sistema")
                    
                    sistema_id = None
                    if sistema_sel and not es_nuevo_sys and not df_sys.empty:
                         sistema_id = df_sys[(df_sys['equipo_tag'].astype(str) == str(tag_equipo)) & (df_sys['nombre'] == sistema_sel)].iloc[0]['id']

                    if sistema_id:
                        st.divider()
                        comp_exist = []
                        if not df_comp.empty:
                            sys_id_clean = limpiar_id(pd.Series([sistema_id]))[0]
                            mask_comp = limpiar_id(df_comp['sistema_id']) == sys_id_clean
                            comp_exist = df_comp[mask_comp]['nombre'].tolist()
                        
                        comp_sel, es_nuevo_comp = gestionar_filtro_dinamico("Componente", comp_exist, "comp")
                        
                        if comp_sel:
                            with st.form("form_comp_dinamico"):
                                st.caption(f"{'🆕 CREANDO' if es_nuevo_comp else '✏️ EDITANDO'}: {comp_sel}")
                                
                                # Datos Base
                                def_marca = ""; def_mod = ""; def_cant = 1; def_cat = lista_familias[0]; def_specs = {}
                                comp_idx = None
                                
                                if not es_nuevo_comp:
                                    try:
                                        sys_id_clean = limpiar_id(pd.Series([sistema_id]))[0]
                                        mask_c = (limpiar_id(df_comp['sistema_id']) == sys_id_clean) & (df_comp['nombre'] == comp_sel)
                                        c_row = df_comp[mask_c].iloc[0]
                                        def_marca = c_row['marca']; def_mod = c_row['modelo']; def_cant = int(c_row['cantidad'])
                                        def_cat = c_row['categoria']; 
                                        if c_row['specs_json']: def_specs = json.loads(c_row['specs_json'])
                                        comp_idx = c_row.name
                                    except: pass

                                c1, c2 = st.columns(2)
                                v_marca = c1.text_input("Marca", value=def_marca)
                                v_mod = c2.text_input("Modelo", value=def_mod)
                                c3, c4 = st.columns(2)
                                v_cant = c3.number_input("Cantidad", min_value=1, value=def_cant)
                                
                                # SELECTOR DE CATEGORÍA BASADO EN LA DB (FAMILIAS CONFIGURADAS)
                                idx_cat = lista_familias.index(def_cat) if def_cat in lista_familias else 0
                                v_cat = c4.selectbox("Categoría / Familia", lista_familias, index=idx_cat)

                                # RENDERIZADO DINÁMICO
                                specs_finales = render_specs_dinamicas_db(v_cat, def_specs)

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
