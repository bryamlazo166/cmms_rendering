import streamlit as st
import pandas as pd
import json
from utils.db_con import get_data, save_data

# --- CONFIGURACIÓN DE COLUMNAS ---
COLS_EQUIPOS = ["id", "tag", "nombre", "planta", "area", "tipo", "criticidad", "estado"]
COLS_SISTEMAS = ["id", "equipo_tag", "nombre", "descripcion"]
COLS_COMPONENTES = ["id", "sistema_id", "nombre", "marca", "modelo", "cantidad", "categoria", "repuesto_sku", "specs_json"]

# --- LISTA MAESTRA ---
CATEGORIAS_STD = [
    "Motor Eléctrico",
    "Motoreductor (Caja+Motor)",
    "Reductor / Caja Mecánica",
    "Rodamiento / Chumacera",
    "Faja / Correa de Transmisión",
    "Bomba Centrifuga/Positiva",
    "Ventilador / Blower",
    "Válvula",
    "Acoplamiento",
    "PLC / Variador / Eléctrico",
    "Otro / General"
]

# --- FUNCIONES AUXILIARES ---
def asegurar_df(df, columnas_base):
    if df.empty or len(df.columns) == 0:
        return pd.DataFrame(columns=columnas_base)
    for col in columnas_base:
        if col not in df.columns:
            df[col] = None
    return df

def limpiar_id(serie):
    return serie.astype(str).str.replace(r"\.0$", "", regex=True).str.strip()

def limpiar_dato(dato):
    if pd.isna(dato) or str(dato).lower() == 'nan' or str(dato).strip() == "":
        return "-"
    return str(dato)

def formatear_specs_html(json_str):
    try:
        if not json_str or json_str == "{}": return ""
        data = json.loads(json_str)
        items = []
        for k, v in data.items():
            if v and str(v).lower() != 'nan':
                key_nice = k.replace("_", " ").title()
                items.append(f"• <b>{key_nice}:</b> {v}")
        
        if not items: return ""
        
        html = '<div style="display: grid; grid-template-columns: 1fr 1fr; gap: 5px; margin-top: 5px; font-size: 0.9em; color: #cfcfcf;">'
        for item in items:
            html += f'<span>{item}</span>'
        html += '</div>'
        return html
    except:
        return ""

def gestionar_filtro_dinamico(label, opciones_existentes, key_suffix):
    if opciones_existentes is None: opciones_existentes = []
    opciones_limpias = [str(x) for x in opciones_existentes if pd.notna(x) and str(x) != ""]
    opciones = sorted(list(set(opciones_limpias)))
    opciones.insert(0, "➕ CREAR NUEVO...")
    opciones.insert(0, "Seleccionar...")
    
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

def render_specs_dinamicas(categoria, valores_actuales={}):
    specs = {}
    st.markdown("---")
    st.caption(f"⚙️ Plantilla de Datos: {categoria}")
    
    if categoria == "Motor Eléctrico":
        c1, c2, c3 = st.columns(3)
        specs["potencia_hp"] = c1.text_input("Potencia (HP)", value=valores_actuales.get("potencia_hp", ""))
        specs["rpm"] = c2.text_input("RPM", value=valores_actuales.get("rpm", ""))
        specs["voltaje"] = c3.selectbox("Voltaje", ["220V", "380V", "440V", "Medium"], index=0)
        
        c4, c5, c6 = st.columns(3)
        specs["corriente_nom"] = c4.text_input("Amperaje Nom. (A)", value=valores_actuales.get("corriente_nom", ""))
        specs["corriente_max"] = c5.text_input("Amperaje Max. (A)", value=valores_actuales.get("corriente_max", ""))
        specs["factor_servicio"] = c6.text_input("Factor Servicio", value=valores_actuales.get("factor_servicio", ""))
        
        c7, c8 = st.columns(2)
        specs["frame"] = c7.text_input("Frame / Carcasa", value=valores_actuales.get("frame", ""))
        specs["diametro_eje"] = c8.text_input("Ø Eje (mm)", value=valores_actuales.get("diametro_eje", ""))

    elif categoria == "Motoreductor (Caja+Motor)":
        st.caption("⚡ Motor Integrado")
        c1, c2, c3 = st.columns(3)
        specs["potencia_hp"] = c1.text_input("Potencia (HP)", value=valores_actuales.get("potencia_hp", ""))
        specs["voltaje"] = c2.text_input("Voltaje", value=valores_actuales.get("voltaje", ""))
        specs["rpm_entrada"] = c3.text_input("RPM Motor", value=valores_actuales.get("rpm_entrada", ""))
        
        st.caption("⚙️ Caja Reductora")
        c4, c5 = st.columns(2)
        specs["ratio"] = c4.text_input("Relación (i)", value=valores_actuales.get("ratio", ""))
        specs["rpm_salida"] = c5.text_input("RPM Salida", value=valores_actuales.get("rpm_salida", ""))
        
        c6, c7, c8 = st.columns(3)
        specs["torque_nom"] = c6.text_input("Torque Nom (Nm)", value=valores_actuales.get("torque_nom", ""))
        specs["eje_salida"] = c7.text_input("Ø Eje Salida", value=valores_actuales.get("eje_salida", ""))
        specs["aceite"] = c8.text_input("Tipo Aceite", value=valores_actuales.get("aceite", "ISO VG"))

    elif categoria == "Reductor / Caja Mecánica":
        c1, c2 = st.columns(2)
        specs["ratio"] = c1.text_input("Relación (i)", value=valores_actuales.get("ratio", ""))
        specs["hp_termica"] = c2.text_input("Capacidad Térmica (HP)", value=valores_actuales.get("hp_termica", ""))
        c3, c4 = st.columns(2)
        specs["eje_entrada"] = c3.text_input("Ø Eje Entrada", value=valores_actuales.get("eje_entrada", ""))
        specs["eje_salida"] = c4.text_input("Ø Eje Salida", value=valores_actuales.get("eje_salida", ""))

    elif categoria == "Rodamiento / Chumacera":
        c1, c2 = st.columns(2)
        specs["codigo_iso"] = c1.text_input("Código ISO", value=valores_actuales.get("codigo_iso", ""))
        specs["tipo_sello"] = c2.selectbox("Sello", ["Abierto", "ZZ", "2RS", "Laberinto"], index=0)
        c3, c4 = st.columns(2)
        specs["tipo_alojamiento"] = c3.selectbox("Alojamiento", ["Pillow Block", "Flange", "Tensor", "Sin"], index=0)
        specs["grasera"] = c4.checkbox("Con Grasera", value=valores_actuales.get("grasera", False))

    elif categoria == "Faja / Correa de Transmisión":
        c1, c2, c3 = st.columns(3)
        specs["perfil"] = c1.selectbox("Perfil", ["A", "B", "C", "D", "SPA", "SPB", "SPC", "3V", "5V", "8V", "Sincrónica"], index=1)
        specs["longitud"] = c2.text_input("Longitud / Número", value=valores_actuales.get("longitud", ""))
        specs["material"] = c3.text_input("Material", value=valores_actuales.get("material", "Caucho/Lona"))

    elif categoria == "Bomba Centrifuga/Positiva":
        c1, c2 = st.columns(2)
        specs["caudal"] = c1.text_input("Caudal (Q)", value=valores_actuales.get("caudal", ""))
        specs["altura"] = c2.text_input("Altura (H)", value=valores_actuales.get("altura", ""))
        specs["sello"] = st.text_input("Tipo Sello Mecánico", value=valores_actuales.get("sello", ""))

    else:
        specs["detalles"] = st.text_area("Detalles Generales", value=valores_actuales.get("detalles", ""))
        
    return specs

# --- VISTA PRINCIPAL ---
def render_gestion_activos():
    st.header("🏭 Gestión Estandarizada de Activos")
    
    st.markdown("""
    <style>
    .component-card { background-color: #262730; border: 1px solid #363945; border-radius: 8px; padding: 15px; margin-top: 10px; border-left: 5px solid #FF4B4B; }
    .comp-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
    .comp-title { font-weight: bold; font-size: 1.05em; color: #fff; }
    .comp-badge { background-color: #FF4B4B; color: white; padding: 2px 8px; border-radius: 4px; font-size: 0.8em; }
    .comp-details { display: grid; grid-template-columns: 1fr 1fr; gap: 5px; font-size: 0.9em; color: #e0e0e0; margin-bottom: 8px; }
    .comp-specs { border-top: 1px solid #444; padding-top: 8px; font-size: 0.9em; }
    input { color: black !important; }
    </style>
    """, unsafe_allow_html=True)
    
    tab_arbol, tab_manual, tab_masiva = st.tabs(["🌳 Visualizar Árbol", "✏️ Gestión & Edición", "📦 Carga Masiva"])

    # Carga de datos
    df_eq = asegurar_df(get_data("equipos"), COLS_EQUIPOS)
    df_sys = asegurar_df(get_data("sistemas"), COLS_SISTEMAS)
    df_comp = asegurar_df(get_data("componentes"), COLS_COMPONENTES)

    if not df_eq.empty: df_eq['tag'] = df_eq['tag'].astype(str).str.strip().str.upper()
    if not df_sys.empty: df_sys['id'] = limpiar_id(df_sys['id']); df_sys['equipo_tag'] = df_sys['equipo_tag'].astype(str).str.strip().str.upper()
    if not df_comp.empty: df_comp['sistema_id'] = limpiar_id(df_comp['sistema_id'])

    # === TAB 1: ÁRBOL ===
    with tab_arbol:
        if df_eq.empty:
            st.info("Base de datos vacía.")
        else:
            plantas = df_eq['planta'].unique()
            for planta in plantas:
                if pd.isna(planta): continue
                with st.expander(f"🏭 {planta}", expanded=True):
                    areas = df_eq[df_eq['planta'] == planta]['area'].unique()
                    for area in areas:
                        st.markdown(f"### 📍 {area}")
                        equipos = df_eq[(df_eq['planta'] == planta) & (df_eq['area'] == area)]
                        for _, eq in equipos.iterrows():
                            with st.expander(f"🔹 {eq['nombre']} ({eq['tag']})"):
                                st.caption(f"Tipo: {eq['tipo']} | Criticidad: {eq['criticidad']}")
                                if not df_sys.empty:
                                    sistemas = df_sys[df_sys['equipo_tag'] == str(eq['tag'])]
                                    for _, sys in sistemas.iterrows():
                                        st.markdown(f"**🎛️ {sys['nombre']}**")
                                        if not df_comp.empty:
                                            comps = df_comp[df_comp['sistema_id'] == str(sys['id'])]
                                            if not comps.empty:
                                                for _, c in comps.iterrows():
                                                    marca = limpiar_dato(c['marca'])
                                                    modelo = limpiar_dato(c['modelo'])
                                                    sku = limpiar_dato(c['repuesto_sku'])
                                                    specs_html = formatear_specs_html(c['specs_json'])
                                                    
                                                    st.markdown(f"""
                                                    <div class="component-card">
                                                        <div class="comp-header">
                                                            <span class="comp-title">🔧 {c['nombre']}</span>
                                                            <span class="comp-badge">{c['categoria']}</span>
                                                        </div>
                                                        <div class="comp-details">
                                                            <div>🏷️ <b>Marca:</b> {marca}</div>
                                                            <div>🔢 <b>Mod:</b> {modelo}</div>
                                                            <div>📦 <b>Cant:</b> {c['cantidad']}</div>
                                                            <div>🔗 <b>SKU:</b> {sku}</div>
                                                        </div>
                                                        <div class="comp-specs">{specs_html}</div>
                                                    </div>
                                                    """, unsafe_allow_html=True)
                                            else: st.caption("🚫 Sin componentes.")
                                        else: st.caption("🚫 Sin componentes.")
                                        st.markdown("<br>", unsafe_allow_html=True)

    # === TAB 2: GESTIÓN ===
    with tab_manual:
        plantas_exist = df_eq['planta'].unique().tolist() if not df_eq.empty else []
        planta_val, _ = gestionar_filtro_dinamico("Planta", plantas_exist, "planta")
        
        if planta_val:
            areas_exist = df_eq[df_eq['planta'] == planta_val]['area'].unique().tolist() if not df_eq.empty else []
            area_val, _ = gestionar_filtro_dinamico("Área", areas_exist, "area")
            
            if area_val:
                st.divider()
                col_eq1, col_eq2 = st.columns(2)
                with col_eq1:
                    eqs_exist = df_eq[(df_eq['planta'] == planta_val) & (df_eq['area'] == area_val)]['nombre'].tolist() if not df_eq.empty else []
                    equipo_sel, es_nuevo_eq = gestionar_filtro_dinamico("Equipo", eqs_exist, "equipo")

                equipo_row = None; tag_equipo = None
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
                                    st.session_state['sel_equipo'] = equipo_sel
                                    st.success("Creado!"); st.rerun()
                                else:
                                    df_eq.at[eq_idx, 'tag'] = val_tag; df_eq.at[eq_idx, 'tipo'] = val_tipo; df_eq.at[eq_idx, 'criticidad'] = val_crit
                                    save_data(df_eq, "equipos"); st.success("Actualizado!"); st.rerun()

                # Sistema
                sistema_sel = None; es_nuevo_sys = False; sistema_id = None
                if tag_equipo and not es_nuevo_eq:
                    st.divider()
                    col_sys1, col_sys2 = st.columns(2)
                    with col_sys1:
                        sys_exist = df_sys[df_sys['equipo_tag'].astype(str) == str(tag_equipo)]['nombre'].tolist() if not df_sys.empty else []
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

                    # Componente
                    if sistema_id:
                        st.divider()
                        col_comp1, col_comp2 = st.columns([1, 2])
                        with col_comp1:
                            comp_exist = []
                            if not df_comp.empty:
                                sys_id_clean = limpiar_id(pd.Series([sistema_id]))[0]
                                mask_comp = limpiar_id(df_comp['sistema_id']) == sys_id_clean
                                comp_exist = df_comp[mask_comp]['nombre'].tolist()
                            comp_sel, es_nuevo_comp = gestionar_filtro_dinamico("Componente", comp_exist, "comp")
                        
                        if comp_sel:
                            with col_comp2:
                                # LÓGICA CORREGIDA: SELECTOR FUERA DEL FORM
                                st.caption(f"{'🆕 CREANDO' if es_nuevo_comp else '✏️ EDITANDO'}: {comp_sel}")
                                
                                # Carga de datos previos
                                def_marca = ""; def_mod = ""; def_cant = 1; def_cat = "Otro / General"; def_specs = {}
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

                                # SELECCIÓN DE CATEGORÍA FUERA DEL FORMULARIO (UX DINÁMICO)
                                idx_cat = CATEGORIAS_STD.index(def_cat) if def_cat in CATEGORIAS_STD else len(CATEGORIAS_STD)-1
                                v_cat = st.selectbox("Categoría Estándar", CATEGORIAS_STD, index=idx_cat, key="cat_selector_out")

                                # AHORA EL FORMULARIO
                                with st.form("form_comp_final"):
                                    c1, c2 = st.columns(2)
                                    v_marca = c1.text_input("Marca", value=def_marca)
                                    v_mod = c2.text_input("Modelo", value=def_mod)
                                    c3, c4 = st.columns(2)
                                    v_cant = c3.number_input("Cantidad", min_value=1, value=def_cant)
                                    
                                    # Repuestos
                                    df_alm = get_data("almacen")
                                    opts_alm = ["Ninguno"]
                                    if not df_alm.empty:
                                        opts_alm += (df_alm['sku'] + " | " + df_alm['descripcion']).tolist()
                                    v_rep = c4.selectbox("Repuesto Vinculado", opts_alm)

                                    # Specs Dinámicas (Se actualizan porque v_cat está fuera)
                                    specs_finales = render_specs_dinamicas(v_cat, def_specs)

                                    # BOTÓN DE ENVÍO OBLIGATORIO DENTRO DEL FORM
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
