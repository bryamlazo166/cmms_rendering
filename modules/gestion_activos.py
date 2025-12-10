import streamlit as st
import pandas as pd
from utils.db_con import get_data, save_data

# --- FUNCIÓN HELPER: SELECTOR DINÁMICO ---
def gestionar_filtro_dinamico(label, opciones_existentes, key_suffix):
    """
    Selector que permite elegir de lo existente o crear uno nuevo.
    """
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

# --- VISTA PRINCIPAL ---
def render_gestion_activos():
    st.header("🏭 Gestión Integral de Activos")
    
    # Pestañas reorganizadas para dar prioridad al Árbol Visual
    tab_arbol, tab_manual, tab_masiva = st.tabs(["🌳 Visualizar Árbol", "👆 Gestión Manual", "📦 Carga Masiva"])

    # ==========================================
    # TAB 1: VISUALIZACIÓN DEL ÁRBOL (NUEVO)
    # ==========================================
    with tab_arbol:
        st.subheader("Estructura Jerárquica de Planta")
        
        # Cargar todos los datos
        df_eq = get_data("equipos")
        df_sys = get_data("sistemas")
        df_comp = get_data("componentes")
        
        if df_eq.empty:
            st.info("No hay activos registrados. Ve a la pestaña de Gestión Manual.")
        else:
            # Agrupar por Planta -> Área
            plantas = df_eq['planta'].unique()
            
            for planta in plantas:
                # Nivel 1: Planta
                with st.expander(f"🏭 Planta: {planta}", expanded=True):
                    areas = df_eq[df_eq['planta'] == planta]['area'].unique()
                    
                    for area in areas:
                        st.markdown(f"**📍 Área: {area}**")
                        
                        # Nivel 3: Equipos
                        equipos_area = df_eq[(df_eq['planta'] == planta) & (df_eq['area'] == area)]
                        
                        for _, eq in equipos_area.iterrows():
                            # Usamos columnas para indentar visualmente
                            col_space, col_content = st.columns([0.5, 10])
                            with col_content:
                                with st.expander(f"🔹 {eq['nombre']} ({eq['tag']})"):
                                    st.caption(f"Tipo: {eq['tipo']} | Criticidad: {eq['criticidad']}")
                                    
                                    # Nivel 4: Sistemas
                                    if not df_sys.empty:
                                        sistemas = df_sys[df_sys['equipo_tag'] == eq['tag']]
                                        for _, sys in sistemas.iterrows():
                                            st.markdown(f"- 🎛️ **Sistema:** {sys['nombre']}")
                                            
                                            # Nivel 5: Componentes
                                            if not df_comp.empty:
                                                comps = df_comp[df_comp['sistema_id'] == sys['id']]
                                                for _, comp in comps.iterrows():
                                                    st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; 🔧 {comp['nombre']} | Marca: {comp['marca']} | Cant: {comp['cantidad']}")

    # ==========================================
    # TAB 2: CARGA MANUAL EN CASCADA
    # ==========================================
    with tab_manual:
        st.markdown("##### Seleccione o cree niveles en orden descendente")
        
        # Cargar datos frescos
        df_equipos = get_data("equipos")
        df_sistemas = get_data("sistemas")
        
        # --- NIVEL 1: PLANTA ---
        plantas_exist = df_equipos['planta'].unique().tolist() if not df_equipos.empty else []
        planta_val, _ = gestionar_filtro_dinamico("Planta", plantas_exist, "planta")
        
        if planta_val:
            # --- NIVEL 2: ÁREA ---
            areas_exist = []
            if not df_equipos.empty:
                areas_exist = df_equipos[df_equipos['planta'] == planta_val]['area'].unique().tolist()
            
            area_val, _ = gestionar_filtro_dinamico("Área", areas_exist, "area")
            
            if area_val:
                st.markdown("---")
                # --- NIVEL 3: EQUIPO ---
                col_eq1, col_eq2 = st.columns(2)
                
                with col_eq1:
                    eqs_exist = []
                    if not df_equipos.empty:
                        eqs_exist = df_equipos[
                            (df_equipos['planta'] == planta_val) & 
                            (df_equipos['area'] == area_val)
                        ]['nombre'].tolist()
                    
                    modo_equipo = st.radio("Acción Equipo:", ["Seleccionar Existente", "Crear Nuevo Equipo"], horizontal=True)
                
                tag_equipo_final = None
                nombre_equipo_final = None

                if modo_equipo == "Crear Nuevo Equipo":
                    with col_eq2:
                        st.markdown("**Nuevo Equipo**")
                        # CAMPOS VACÍOS (TEXT INPUT) PARA LIBERTAD TOTAL
                        new_tag = st.text_input("TAG (Único)", placeholder="Ej: DIG-01").strip().upper()
                        new_nom = st.text_input("Nombre")
                        
                        # Tipo ahora es libre, sin lista predefinida
                        tipo = st.text_input("Tipo de Equipo", placeholder="Ej: Digestor, Prensa...")
                        
                        # Criticidad opcional pero con lista vacía inicial
                        crit = st.selectbox("Criticidad", ["", "Alta", "Media", "Baja"], index=0)
                        
                        if st.button("Guardar Equipo"):
                            if new_tag and new_nom:
                                new_id = 1 if df_equipos.empty else df_equipos['id'].max() + 1
                                row = pd.DataFrame([{
                                    "id": new_id, "tag": new_tag, "nombre": new_nom,
                                    "planta": planta_val, "area": area_val,
                                    "tipo": tipo, "criticidad": crit, "estado": "Operativo"
                                }])
                                save_data(pd.concat([df_equipos, row], ignore_index=True), "equipos")
                                st.success("Equipo Guardado")
                                st.rerun()
                else:
                    if eqs_exist:
                        with col_eq2:
                            nom_sel = st.selectbox("Equipo Existente", eqs_exist)
                            datos_eq = df_equipos[(df_equipos['nombre'] == nom_sel) & (df_equipos['area'] == area_val)]
                            if not datos_eq.empty:
                                tag_equipo_final = datos_eq.iloc[0]['tag']
                                nombre_equipo_final = nom_sel
                    else:
                        st.warning("No hay equipos aquí.")

                # --- NIVEL 4: SISTEMAS ---
                if tag_equipo_final:
                    st.divider()
                    st.markdown(f"🎛️ **Sistemas de: {nombre_equipo_final}**")
                    
                    sistemas_exist = []
                    if not df_sistemas.empty:
                        sistemas_exist = df_sistemas[df_sistemas['equipo_tag'] == tag_equipo_final]['nombre'].tolist()
                    
                    sistema_val, es_nuevo_sys = gestionar_filtro_dinamico("Sistema", sistemas_exist, "sistema")
                    
                    sistema_id_final = None
                    
                    if sistema_val:
                        if es_nuevo_sys:
                            if st.button("Confirmar Creación Sistema"):
                                new_id_sys = 1 if df_sistemas.empty else df_sistemas['id'].max() + 1
                                row_sys = pd.DataFrame([{
                                    "id": new_id_sys, "equipo_tag": tag_equipo_final,
                                    "nombre": sistema_val, "descripcion": ""
                                }])
                                save_data(pd.concat([df_sistemas, row_sys], ignore_index=True), "sistemas")
                                st.success(f"Sistema '{sistema_val}' creado.")
                                st.rerun()
                        else:
                            if not df_sistemas.empty:
                                sistema_id_final = df_sistemas[
                                    (df_sistemas['equipo_tag'] == tag_equipo_final) & 
                                    (df_sistemas['nombre'] == sistema_val)
                                ]['id'].values[0]

                        # --- NIVEL 5: COMPONENTES ---
                        if sistema_id_final:
                            st.markdown(f"🔧 **Componentes de: {sistema_val}**")
                            with st.form("add_comp_final"):
                                c1, c2, c3 = st.columns(3)
                                # Campos libres
                                nom_c = c1.text_input("Nombre Componente")
                                marca = c2.text_input("Marca")
                                modelo = c3.text_input("Modelo")
                                
                                c4, c5 = st.columns(2)
                                cant = c4.number_input("Cantidad", min_value=1, step=1)
                                # Categoría libre
                                cat = c5.text_input("Categoría", placeholder="Ej: Motor, Rodamiento...")
                                
                                # Vinculación Stock
                                df_alm = get_data("almacen")
                                lista_sku = ["Ninguno"]
                                if not df_alm.empty:
                                    lista_sku += (df_alm['sku'] + " | " + df_alm['descripcion']).tolist()
                                sku_sel = st.selectbox("Repuesto (Opcional)", lista_sku)
                                
                                if st.form_submit_button("Guardar Componente"):
                                    df_c = get_data("componentes")
                                    new_id_c = 1 if df_c.empty else df_c['id'].max() + 1
                                    sku_limpio = sku_sel.split(" | ")[0] if "|" in sku_sel else ""
                                    
                                    row_c = pd.DataFrame([{
                                        "id": new_id_c, "sistema_id": sistema_id_final,
                                        "nombre": nom_c, "marca": marca, "modelo": modelo,
                                        "cantidad": cant, "categoria": cat, 
                                        "repuesto_sku": sku_limpio, "specs_json": "{}"
                                    }])
                                    save_data(pd.concat([df_c, row_c], ignore_index=True), "componentes")
                                    st.success("✅ Componente Agregado.")

    # ==========================================
    # TAB 3: CARGA MASIVA
    # ==========================================
    with tab_masiva:
        st.subheader("Carga Masiva (Excel)")
        st.info("Sube tu Excel con columnas: Planta, Area, Tag_Equipo, Nombre_Equipo...")
        file = st.file_uploader("Subir Excel", type=["xlsx"])
