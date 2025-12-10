import streamlit as st
import pandas as pd
import json
from utils.db_con import get_data, save_data

# --- FUNCIÓN HELPER MEJORADA ---
def gestionar_filtro_dinamico(label, opciones_existentes, key_suffix):
    opciones_limpias = [x for x in opciones_existentes if pd.notna(x) and x != ""]
    opciones = sorted(list(set(opciones_limpias)))
    opciones.insert(0, "➕ AGREGAR NUEVO...")
    opciones.insert(0, "Seleccionar...")
    
    seleccion = st.selectbox(f"Seleccione {label}", opciones, key=f"sel_{key_suffix}")
    
    valor_final = None
    es_nuevo = False
    
    if seleccion == "➕ AGREGAR NUEVO...":
        valor_final = st.text_input(f"Escriba nuevo nombre para {label}", key=f"new_{key_suffix}").strip().upper()
        es_nuevo = True
    elif seleccion != "Seleccionar...":
        valor_final = seleccion
        
    return valor_final, es_nuevo

def render_gestion_activos():
    st.header("🏭 Gestión Integral de Activos")
    
    tab_arbol, tab_manual, tab_masiva = st.tabs(["🌳 Visualizar Árbol", "👆 Gestión & Edición Completa", "📦 Carga Masiva"])

    # ==========================================
    # TAB 1: VISUALIZACIÓN
    # ==========================================
    with tab_arbol:
        st.subheader("Estructura Jerárquica")
        df_eq = get_data("equipos")
        df_sys = get_data("sistemas")
        df_comp = get_data("componentes")
        
        if df_eq.empty:
            st.info("No hay activos registrados.")
        else:
            plantas = df_eq['planta'].unique()
            for planta in plantas:
                with st.expander(f"🏭 {planta}", expanded=True):
                    areas = df_eq[df_eq['planta'] == planta]['area'].unique()
                    for area in areas:
                        st.markdown(f"**📍 {area}**")
                        equipos_area = df_eq[(df_eq['planta'] == planta) & (df_eq['area'] == area)]
                        for _, eq in equipos_area.iterrows():
                            col_space, col_content = st.columns([0.5, 10])
                            with col_content:
                                with st.expander(f"🔹 {eq['nombre']} ({eq['tag']})"):
                                    if not df_sys.empty:
                                        sistemas = df_sys[df_sys['equipo_tag'] == eq['tag']]
                                        for _, sys in sistemas.iterrows():
                                            st.markdown(f"**🎛️ {sys['nombre']}**")
                                            if not df_comp.empty:
                                                comps = df_comp[df_comp['sistema_id'] == sys['id']]
                                                for _, comp in comps.iterrows():
                                                    st.caption(f"🔧 {comp['nombre']} | {comp['marca']} ({comp['cantidad']})")

    # ==========================================
    # TAB 2: GESTIÓN MANUAL (EDICIÓN EN CASCADA)
    # ==========================================
    with tab_manual:
        st.markdown("##### Navegación por Niveles")
        
        df_equipos = get_data("equipos")
        df_sistemas = get_data("sistemas")
        df_componentes = get_data("componentes") # Cargamos componentes también
        
        # --- NIVEL 1 & 2: PLANTA Y ÁREA ---
        plantas_exist = df_equipos['planta'].unique().tolist() if not df_equipos.empty else []
        planta_val, _ = gestionar_filtro_dinamico("Planta", plantas_exist, "planta")
        
        if planta_val:
            areas_exist = []
            if not df_equipos.empty:
                areas_exist = df_equipos[df_equipos['planta'] == planta_val]['area'].unique().tolist()
            area_val, _ = gestionar_filtro_dinamico("Área", areas_exist, "area")
            
            if area_val:
                st.divider()
                # --- NIVEL 3: EQUIPO ---
                col_eq1, col_eq2 = st.columns(2)
                with col_eq1:
                    eqs_exist = []
                    if not df_equipos.empty:
                        eqs_exist = df_equipos[(df_equipos['planta'] == planta_val) & (df_equipos['area'] == area_val)]['nombre'].tolist()
                    modo_equipo = st.radio("Nivel Equipo:", ["Seleccionar", "Crear Nuevo"], horizontal=True, key="mode_eq")
                
                equipo_row = None
                tag_equipo = None

                # CREAR EQUIPO
                if modo_equipo == "Crear Nuevo":
                    with col_eq2:
                        st.markdown("**Nuevo Equipo**")
                        new_tag = st.text_input("TAG", placeholder="DIG-01").strip().upper()
                        new_nom = st.text_input("Nombre")
                        tipo = st.text_input("Tipo")
                        if st.button("Guardar Equipo"):
                            if new_tag and new_nom:
                                new_id = 1 if df_equipos.empty else df_equipos['id'].max() + 1
                                row = pd.DataFrame([{"id": new_id, "tag": new_tag, "nombre": new_nom, "planta": planta_val, "area": area_val, "tipo": tipo, "criticidad": "", "estado": "Operativo"}])
                                save_data(pd.concat([df_equipos, row], ignore_index=True), "equipos")
                                st.success("Guardado!"); st.rerun()
                
                # SELECCIONAR / EDITAR EQUIPO
                else:
                    if eqs_exist:
                        with col_eq2:
                            nom_sel = st.selectbox("Equipo", eqs_exist)
                            equipo_row = df_equipos[(df_equipos['nombre'] == nom_sel) & (df_equipos['area'] == area_val)].iloc[0]
                            tag_equipo = equipo_row['tag']
                            
                            with st.expander("✏️ Editar Datos del Equipo"):
                                with st.form("edit_eq"):
                                    e_nom = st.text_input("Nombre", value=equipo_row['nombre'])
                                    e_tipo = st.text_input("Tipo", value=equipo_row['tipo'])
                                    if st.form_submit_button("Actualizar Equipo"):
                                        idx = equipo_row.name
                                        df_equipos.at[idx, 'nombre'] = e_nom
                                        df_equipos.at[idx, 'tipo'] = e_tipo
                                        save_data(df_equipos, "equipos")
                                        st.success("Equipo Actualizado"); st.rerun()

                # --- NIVEL 4: SISTEMAS ---
                if tag_equipo:
                    st.divider()
                    st.markdown(f"🎛️ **Sistemas de: {equipo_row['nombre']}**")
                    
                    sistemas_exist = []
                    if not df_sistemas.empty:
                        sistemas_exist = df_sistemas[df_sistemas['equipo_tag'] == tag_equipo]['nombre'].tolist()
                    
                    sistema_val, es_nuevo_sys = gestionar_filtro_dinamico("Sistema", sistemas_exist, "sistema")
                    
                    sistema_id = None
                    
                    if sistema_val:
                        # CREAR SISTEMA
                        if es_nuevo_sys:
                            if st.button("Crear Sistema"):
                                new_id = 1 if df_sistemas.empty else df_sistemas['id'].max() + 1
                                row = pd.DataFrame([{"id": new_id, "equipo_tag": tag_equipo, "nombre": sistema_val, "descripcion": ""}])
                                save_data(pd.concat([df_sistemas, row], ignore_index=True), "sistemas")
                                st.success("Sistema Creado"); st.rerun()
                        # EDITAR SISTEMA
                        else:
                            sys_row = df_sistemas[(df_sistemas['equipo_tag'] == tag_equipo) & (df_sistemas['nombre'] == sistema_val)].iloc[0]
                            sistema_id = sys_row['id']
                            
                            with st.expander(f"✏️ Editar Sistema: {sistema_val}"):
                                with st.form("edit_sys"):
                                    e_sys_nom = st.text_input("Nombre Sistema", value=sys_row['nombre'])
                                    if st.form_submit_button("Actualizar Sistema"):
                                        df_sistemas.at[sys_row.name, 'nombre'] = e_sys_nom
                                        save_data(df_sistemas, "sistemas")
                                        st.success("Sistema Actualizado"); st.rerun()

                        # --- NIVEL 5: COMPONENTES ---
                        if sistema_id:
                            st.divider()
                            st.markdown(f"🔧 **Componentes de: {sistema_val}**")
                            
                            # Buscar componentes existentes en este sistema
                            comps_existentes = []
                            if not df_componentes.empty:
                                comps_existentes = df_componentes[df_componentes['sistema_id'] == sistema_id]['nombre'].tolist()
                            
                            # Selector inteligente para Componente
                            comp_val, es_nuevo_comp = gestionar_filtro_dinamico("Componente", comps_existentes, "comp")
                            
                            # FORMULARIO UNIFICADO (CREAR O EDITAR)
                            if comp_val:
                                with st.form("gestion_comp"):
                                    st.caption(f"{'🆕 CREANDO' if es_nuevo_comp else '✏️ EDITANDO'}: {comp_val}")
                                    
                                    # Valores por defecto
                                    def_marca, def_modelo, def_cant, def_cat = "", "", 1, ""
                                    comp_row_idx = None
                                    
                                    if not es_nuevo_comp and not df_componentes.empty:
                                        # Cargar datos existentes
                                        c_row = df_componentes[(df_componentes['sistema_id'] == sistema_id) & (df_componentes['nombre'] == comp_val)].iloc[0]
                                        def_marca = c_row['marca']
                                        def_modelo = c_row['modelo']
                                        def_cant = int(c_row['cantidad'])
                                        def_cat = c_row['categoria']
                                        comp_row_idx = c_row.name
                                    
                                    c1, c2 = st.columns(2)
                                    val_marca = c1.text_input("Marca", value=def_marca)
                                    val_modelo = c2.text_input("Modelo", value=def_modelo)
                                    
                                    c3, c4 = st.columns(2)
                                    val_cant = c3.number_input("Cantidad", min_value=1, value=def_cant)
                                    val_cat = c4.text_input("Categoría", value=def_cat, placeholder="Rodamiento, Motor...")
                                    
                                    # Repuestos
                                    df_alm = get_data("almacen")
                                    opts_alm = ["Ninguno"] + (df_alm['sku'] + " | " + df_alm['descripcion']).tolist() if not df_alm.empty else ["Ninguno"]
                                    val_rep = st.selectbox("Repuesto Vinculado", opts_alm)

                                    btn_txt = "Guardar Nuevo" if es_nuevo_comp else "Actualizar Datos"
                                    
                                    if st.form_submit_button(btn_txt):
                                        sku_clean = val_rep.split(" | ")[0] if "|" in val_rep else ""
                                        
                                        if es_nuevo_comp:
                                            new_id = 1 if df_componentes.empty else df_componentes['id'].max() + 1
                                            new_row = pd.DataFrame([{
                                                "id": new_id, "sistema_id": sistema_id, "nombre": comp_val,
                                                "marca": val_marca, "modelo": val_modelo, "cantidad": val_cant,
                                                "categoria": val_cat, "repuesto_sku": sku_clean, "specs_json": "{}"
                                            }])
                                            save_data(pd.concat([df_componentes, new_row], ignore_index=True), "componentes")
                                            st.success("Creado!")
                                        else:
                                            # Actualizar existente
                                            df_componentes.at[comp_row_idx, 'marca'] = val_marca
                                            df_componentes.at[comp_row_idx, 'modelo'] = val_modelo
                                            df_componentes.at[comp_row_idx, 'cantidad'] = val_cant
                                            df_componentes.at[comp_row_idx, 'categoria'] = val_cat
                                            if sku_clean:
                                                df_componentes.at[comp_row_idx, 'repuesto_sku'] = sku_clean
                                            
                                            save_data(df_componentes, "componentes")
                                            st.success("Actualizado!")
                                        st.rerun()

    with tab_masiva:
        st.info("Carga masiva disponible.")
        file = st.file_uploader("Subir Excel", type=["xlsx"])
