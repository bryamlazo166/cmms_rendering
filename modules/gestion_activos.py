import streamlit as st
import pandas as pd
from utils.db_con import get_data, save_data

# --- FUNCIÓN HELPER: SELECTOR CON OPCIÓN DE CREAR ---
def gestionar_filtro_dinamico(label, opciones_existentes, key_suffix):
    """
    Crea un selectbox que incluye la opción de '➕ AGREGAR NUEVO...'.
    Si se selecciona, muestra un campo de texto para escribirlo.
    Retorna: (valor_final, es_nuevo)
    """
    # Aseguramos que la lista no tenga nulos y sea única
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
    st.header("🏭 Gestión Integral de Activos (Jerarquía)")
    st.info("Flujo: Planta ➝ Área ➝ Equipo ➝ Sistema ➝ Componente")

    tab_manual, tab_masiva = st.tabs(["👆 Carga Manual (Cascada)", "📦 Carga Masiva (Excel)"])

    # ==========================================
    # TAB 1: CARGA MANUAL EN CASCADA
    # ==========================================
    with tab_manual:
        # Cargar datos base
        df_equipos = get_data("equipos")
        df_sistemas = get_data("sistemas")
        
        # --- NIVEL 1: PLANTA ---
        plantas_exist = df_equipos['planta'].unique().tolist() if not df_equipos.empty else []
        planta_val, _ = gestionar_filtro_dinamico("Planta", plantas_exist, "planta")
        
        if planta_val:
            # --- NIVEL 2: ÁREA (Filtrado por Planta) ---
            areas_exist = []
            if not df_equipos.empty:
                areas_exist = df_equipos[df_equipos['planta'] == planta_val]['area'].unique().tolist()
            
            area_val, _ = gestionar_filtro_dinamico("Área", areas_exist, "area")
            
            if area_val:
                st.markdown("---")
                # --- NIVEL 3: EQUIPO ---
                col_eq1, col_eq2 = st.columns(2)
                
                with col_eq1:
                    # Filtramos equipos existentes en esa Area/Planta para mostrar lista
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
                        st.info("🆕 Creando nuevo Equipo")
                        new_tag = st.text_input("TAG Equipo (Único)", placeholder="Ej: DIG-01").strip().upper()
                        new_nom = st.text_input("Nombre Equipo")
                        tipo = st.selectbox("Tipo", ["Digestor", "Prensa", "Molino", "Caldera", "Motor", "Bomba"])
                        crit = st.select_slider("Criticidad", ["Baja", "Media", "Alta"])
                        
                        if st.button("Guardar Equipo Nivel 3"):
                            if new_tag and new_nom:
                                new_id = 1 if df_equipos.empty else df_equipos['id'].max() + 1
                                row = pd.DataFrame([{
                                    "id": new_id, "tag": new_tag, "nombre": new_nom,
                                    "planta": planta_val, "area": area_val,
                                    "tipo": tipo, "criticidad": crit, "estado": "Operativo"
                                }])
                                save_data(pd.concat([df_equipos, row], ignore_index=True), "equipos")
                                st.success("Equipo Guardado")
                                st.rerun() # Recargar para que aparezca
                else:
                    # Seleccionar existente
                    if eqs_exist:
                        with col_eq2:
                            nom_sel = st.selectbox("Equipo Existente", eqs_exist)
                            # Buscar el TAG de ese nombre
                            datos_eq = df_equipos[(df_equipos['nombre'] == nom_sel) & (df_equipos['area'] == area_val)]
                            if not datos_eq.empty:
                                tag_equipo_final = datos_eq.iloc[0]['tag']
                                nombre_equipo_final = nom_sel
                                st.caption(f"TAG Seleccionado: **{tag_equipo_final}**")
                    else:
                        st.warning("No hay equipos en esta área. Crea uno nuevo.")

                # --- NIVEL 4: SISTEMAS (Solo si hay equipo seleccionado) ---
                if tag_equipo_final:
                    st.markdown("---")
                    st.markdown(f"🎛️ **Sistemas de: {nombre_equipo_final}**")
                    
                    # Filtrar sistemas de este equipo
                    sistemas_exist = []
                    if not df_sistemas.empty:
                        sistemas_exist = df_sistemas[df_sistemas['equipo_tag'] == tag_equipo_final]['nombre'].tolist()
                    
                    sistema_val, es_nuevo_sys = gestionar_filtro_dinamico("Sistema", sistemas_exist, "sistema")
                    
                    sistema_id_final = None
                    
                    if sistema_val:
                        # Si es nuevo, hay que guardarlo antes de seguir
                        if es_nuevo_sys:
                            if st.button("Confirmar Creación de Sistema"):
                                new_id_sys = 1 if df_sistemas.empty else df_sistemas['id'].max() + 1
                                row_sys = pd.DataFrame([{
                                    "id": new_id_sys, "equipo_tag": tag_equipo_final,
                                    "nombre": sistema_val, "descripcion": "Creado en cascada"
                                }])
                                save_data(pd.concat([df_sistemas, row_sys], ignore_index=True), "sistemas")
                                st.success(f"Sistema '{sistema_val}' creado.")
                                st.rerun()
                        else:
                            # Recuperar ID del sistema existente
                            if not df_sistemas.empty:
                                try:
                                    sistema_id_final = df_sistemas[
                                        (df_sistemas['equipo_tag'] == tag_equipo_final) & 
                                        (df_sistemas['nombre'] == sistema_val)
                                    ]['id'].values[0]
                                except:
                                    st.error("Error recuperando ID del sistema.")

                        # --- NIVEL 5: COMPONENTES (Solo si hay sistema ID) ---
                        if sistema_id_final:
                            st.markdown(f"🔧 **Agregar Componente a: {sistema_val}**")
                            with st.form("add_comp_final"):
                                c1, c2, c3 = st.columns(3)
                                nom_c = c1.text_input("Nombre Componente")
                                marca = c2.text_input("Marca")
                                modelo = c3.text_input("Modelo")
                                
                                c4, c5 = st.columns(2)
                                cant = c4.number_input("Cantidad", 1)
                                cat = c5.selectbox("Categoría", ["Motor", "Rodamiento", "Faja", "Reductor"])
                                
                                # Vinculación Repuesto
                                df_alm = get_data("almacen")
                                lista_sku = ["Ninguno"]
                                if not df_alm.empty:
                                    lista_sku += (df_alm['sku'] + " | " + df_alm['descripcion']).tolist()
                                sku_sel = st.selectbox("Repuesto", lista_sku)
                                
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
    # TAB 2: CARGA MASIVA INTELIGENTE
    # ==========================================
    with tab_masiva:
        st.subheader("Carga Masiva de Estructura Completa")
        st.markdown("""
        Sube un Excel con estas columnas (respetar encabezados):
        `Planta`, `Area`, `Tag_Equipo`, `Nombre_Equipo`, `Sistema`, `Componente`, `Marca`, `Modelo`
        """)
        
        file = st.file_uploader("Subir Excel", type=["xlsx"])
        
        if file and st.button("Procesar Estructura Completa"):
            st.info("Funcionalidad en construcción: Requiere mapeo avanzado de IDs.")
