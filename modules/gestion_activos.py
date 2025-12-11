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
    """Renderiza el JSON técnico en HTML bonito"""
    try:
        if not json_str or json_str == "{}": return ""
        data = json.loads(json_str)
        items = [f"• <b>{k}:</b> {v}" for k, v in data.items() if v and str(v).lower() != 'nan']
        if not items: return ""
        # Grid automático
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

# --- MOTOR DE RENDERIZADO DINÁMICO (EL CORAZÓN DEL SISTEMA) ---
def render_campos_dinamicos(categoria, valores_actuales={}):
    """
    Busca la configuración en DB y dibuja los inputs necesarios.
    """
    specs = {}
    st.markdown("---")
    
    # 1. Leer Configuración Maestra
    df_config = get_data("familias_config")
    campos_definidos = []
    
    if not df_config.empty:
        # Buscar la fila donde nombre_familia coincide con la categoría seleccionada
        row = df_config[df_config["nombre_familia"] == categoria]
        if not row.empty:
            try:
                campos_definidos = json.loads(row.iloc[0]["config_json"])
            except: pass
    
    # 2. Dibujar Inputs
    if campos_definidos:
        st.caption(f"⚙️ Ficha Técnica Dinámica: {categoria}")
        cols = st.columns(2) # Layout de 2 columnas
        
        for i, campo in enumerate(campos_definidos):
            nombre = campo['nombre']
            unidad = campo.get('unidad', '')
            label_full = f"{nombre} ({unidad})" if unidad else nombre
            
            # Recuperar valor si estamos editando
            val_previo = valores_actuales.get(nombre, "")
            
            # Dibujar en columna A o B
            specs[nombre] = cols[i % 2].text_input(label_full, value=val_previo)
    else:
        st.info(f"La familia '{categoria}' no tiene configuración. Ve a 'Maestro de Clases' para definir sus campos.")
        specs["Observaciones"] = st.text_area("Datos Generales", value=valores_actuales.get("Observaciones", ""))
        
    return specs

# --- VISTA PRINCIPAL ---
def render_gestion_activos():
    st.header("🏭 Gestión de Activos (Data-Driven)")
    
    st.markdown("""<style>.component-card {background-color: #262730; border: 1px solid #444; border-radius: 8px; padding: 10px; margin-top: 5px; border-left: 4px solid #FF4B4B;} input {color: black !important;}</style>""", unsafe_allow_html=True)
    
    tab_arbol, tab_manual, tab_masiva = st.tabs(["🌳 Visualizar Árbol", "✏️ Gestión & Edición", "📦 Carga Masiva"])

    # Carga de datos
    df_eq = asegurar_df(get_data("equipos"), COLS_EQUIPOS)
    df_sys = asegurar_df(get_data("sistemas"), COLS_SISTEMAS)
    df_comp = asegurar_df(get_data("componentes"), COLS_COMPONENTES)
    # Cargar Familias para el Selector
    df_fam = get_data("familias_config")
    lista_familias = df_fam["nombre_familia"].tolist() if not df_fam.empty else ["GENERAL"]

    if not df_eq.empty: df_eq['tag'] = df_eq['tag'].astype(str).str.strip().str.upper()
    if not df_sys.empty: df_sys['id'] = limpiar_id(df_sys['id']); df_sys['equipo_tag'] = df_sys['equipo_tag'].astype(str).str.strip().str.upper()
    if not df_comp.empty: df_comp['sistema_id'] = limpiar_id(df_comp['sistema_id'])

    # === TAB 1: ÁRBOL ===
    with tab_arbol:
        if df_eq.empty: st.info("Sistema vacío. Comienza creando activos.")
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

    # === TAB 2: GESTIÓN ===
    with tab_manual:
        # -- Selectores Niveles 1-4 (Resumidos para brevedad, lógica igual a la anterior) --
        plantas_exist = df_eq['planta'].unique().tolist() if not df_eq.empty else []
        planta_val, _ = gestionar_filtro_dinamico("Planta", plantas_exist, "planta")
        if planta_val:
            areas_exist = df_eq[df_eq['planta'] == planta_val]['area'].unique().tolist() if not df_eq.empty else []
            area_val, _ = gestionar_filtro_dinamico("Área", areas_exist, "area")
            if area_val:
                eqs_exist = df_eq[(df_eq['planta'] == planta_val) & (df_eq['area'] == area_val)]['nombre'].tolist() if not df_eq.empty else []
                equipo_sel, es_nuevo_eq = gestionar_filtro_dinamico("Equipo", eqs_exist, "equipo")
                
                # ... (Formulario Equipo y Sistema - IGUAL QUE ANTES) ...
                # Para ahorrar espacio en la respuesta, asumo que usas el mismo bloque de guardar Equipo/Sistema del código anterior.
                # Lo importante es llegar al COMPONENTE, que es donde cambia la lógica.
                
                tag_equipo = None
                if equipo_sel and not es_nuevo_eq:
                     tag_equipo = df_eq[(df_eq['nombre'] == equipo_sel) & (df_eq['area'] == area_val)].iloc[0]['tag']
                     
                     # Renderizado Form Equipo (Simplificado aquí para contexto)
                     if es_nuevo_eq: pass # (Tu lógica de guardar equipo)

                if tag_equipo:
                    sys_exist = df_sys[df_sys['equipo_tag'].astype(str) == str(tag_equipo)]['nombre'].tolist() if not df_sys.empty else []
                    sistema_sel, es_nuevo_sys = gestionar_filtro_dinamico("Sistema", sys_exist, "sistema")
                    
                    sistema_id = None
                    if sistema_sel and not es_nuevo_sys and not df_sys.empty:
                         try: sistema_id = df_sys[(df_sys['equipo_tag'].astype(str) == str(tag_equipo)) & (df_sys['nombre'] == sistema_sel)].iloc[0]['id']
                         except: pass

                    # --- NIVEL 5: COMPONENTE DINÁMICO ---
                    if sistema_id:
                        st.divider()
                        comp_exist = []
                        if not df_comp.empty:
                            sys_clean = limpiar_id(pd.Series([sistema_id]))[0]
                            mask = limpiar_id(df_comp['sistema_id']) == sys_clean
                            comp_exist = df_comp[mask]['nombre'].tolist()
                        
                        comp_sel, es_nuevo_comp = gestionar_filtro_dinamico("Componente", comp_exist, "comp")
                        
                        if comp_sel:
                            st.caption(f"{'🆕 CREANDO' if es_nuevo_comp else '✏️ EDITANDO'}: {comp_sel}")
                            
                            # Cargar datos previos
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
                            # Esto permite que la UI se refresque instantáneamente al cambiar familia
                            idx_cat = lista_familias.index(def_cat) if def_cat in lista_familias else 0
                            v_cat = st.selectbox("Familia / Clase (Configurada en Maestro)", lista_familias, index=idx_cat)

                            # FORMULARIO FINAL
                            with st.form("form_comp_sap"):
                                c1, c2 = st.columns(2)
                                v_marca = c1.text_input("Marca", value=def_marca)
                                v_mod = c2.text_input("Modelo", value=def_mod)
                                v_cant = st.number_input("Cantidad", min_value=1, value=def_cant)
                                
                                # AQUÍ ESTÁ LA MAGIA: Renderiza según lo que configuraste en el otro módulo
                                specs_finales = render_campos_dinamicos(v_cat, def_specs)

                                # Repuestos
                                df_alm = get_data("almacen")
                                opts_alm = ["Ninguno"] + (df_alm['sku'] + " | " + df_alm['descripcion']).tolist() if not df_alm.empty else ["Ninguno"]
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
        st.file_uploader("Subir Excel", type=["xlsx"])
