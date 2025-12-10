import streamlit as st
import pandas as pd
import json
from datetime import datetime
from utils.db_con import get_data, save_data

def render_componentes_view():
    st.header("🛠️ Gestión de Componentes (Niveles 4-5)")
    st.info("Jerarquía: Equipo ➝ **Sistema** ➝ **Componente**")

    # --- CARGA DE DATOS ---
    df_equipos = get_data("equipos")
    if df_equipos.empty:
        st.warning("Primero registra equipos.")
        return

    # --- SELECCIÓN EN CASCADA VISUAL (POR NOMBRE) ---
    # 1. Seleccionar Área
    areas = df_equipos["area"].unique()
    area_sel = st.selectbox("Filtrar por Área", areas)
    
    # 2. Seleccionar Equipo (Mostrando Nombre, no solo TAG)
    eq_filtrados = df_equipos[df_equipos["area"] == area_sel].copy()
    # Creamos columna visual: "Digestor 1 | DIG-01"
    eq_filtrados["display"] = eq_filtrados["nombre"] + " | " + eq_filtrados["tag"]
    
    equipo_sel_str = st.selectbox("Seleccionar Equipo", eq_filtrados["display"].tolist())
    tag_equipo = equipo_sel_str.split(" | ")[-1] # Recuperamos el TAG oculto

    st.divider()

    # --- GESTIÓN DE SISTEMAS (NIVEL 4) ---
    col_sys1, col_sys2 = st.columns([2, 1])
    
    df_sistemas = get_data("sistemas")
    
    # Filtrar sistemas de este equipo
    sistemas_del_equipo = pd.DataFrame()
    if not df_sistemas.empty:
        sistemas_del_equipo = df_sistemas[df_sistemas["equipo_tag"] == tag_equipo]

    with col_sys1:
        # Selector de Sistema existente o opción de crear
        opciones_sistema = ["➕ CREAR NUEVO SISTEMA"] 
        if not sistemas_del_equipo.empty:
            opciones_sistema += sistemas_del_equipo["nombre"].tolist()
        
        sistema_sel = st.selectbox("Seleccionar Sistema", opciones_sistema)

    # Lógica para crear sistema nuevo al vuelo
    sistema_id_final = None
    
    if sistema_sel == "➕ CREAR NUEVO SISTEMA":
        with col_sys2:
            new_sys_name = st.text_input("Nombre Nuevo Sistema", placeholder="Ej: Sist. Hidráulico")
            if st.button("Crear Sistema"):
                if new_sys_name:
                    new_id_sys = 1 if df_sistemas.empty else df_sistemas['id'].max() + 1
                    new_sys_row = pd.DataFrame([{
                        "id": new_id_sys, "equipo_tag": tag_equipo, 
                        "nombre": new_sys_name, "descripcion": "Alta manual"
                    }])
                    save_data(pd.concat([df_sistemas, new_sys_row], ignore_index=True), "sistemas")
                    st.success("Sistema creado. Seleccionalo de la lista.")
                    st.rerun()
    else:
        # Obtener ID del sistema seleccionado
        if not sistemas_del_equipo.empty:
            sistema_id_final = sistemas_del_equipo[sistemas_del_equipo["nombre"] == sistema_sel]["id"].values[0]

    # --- ALTA DE COMPONENTE (NIVEL 5) ---
    if sistema_id_final is not None:
        st.markdown(f"Agregando componente a: **{equipo_sel_str}** ➝ **{sistema_sel}**")
        
        with st.form("form_componente"):
            c1, c2, c3 = st.columns(3)
            nombre_comp = c1.text_input("Nombre Componente", placeholder="Ej: Motor Principal")
            marca = c2.text_input("Marca", placeholder="Ej: WEG / SKF")
            modelo = c3.text_input("Modelo", placeholder="Ej: 132M-4")
            
            c4, c5, c6 = st.columns(3)
            cantidad = c4.number_input("Cantidad", min_value=1, step=1)
            categoria = c5.selectbox("Categoría", ["Motor", "Reductor", "Rodamiento", "Faja", "Bomba", "Válvula"])
            
            # Vinculación con Almacén (Visualización por Nombre)
            df_almacen = get_data("almacen")
            lista_repuestos = ["Sin Asignar"]
            if not df_almacen.empty:
                # Mostramos: "SKU | Descripción"
                df_almacen['display'] = df_almacen['sku'] + " | " + df_almacen['descripcion']
                lista_repuestos += df_almacen['display'].tolist()
            
            repuesto_sel = c6.selectbox("Repuesto Stock", lista_repuestos)
            sku_final = repuesto_sel.split(" | ")[0] if "|" in repuesto_sel else ""

            # Specs Técnicas (Simplificado para ejemplo)
            st.markdown("Details Técnicos")
            specs = {}
            if categoria == "Motor":
                specs["hp"] = st.text_input("Potencia HP")
                specs["rpm"] = st.text_input("RPM")
            elif categoria == "Rodamiento":
                specs["codigo_iso"] = st.text_input("Código ISO")
            
            if st.form_submit_button("💾 Guardar Componente"):
                if nombre_comp:
                    df_comps = get_data("componentes")
                    new_id_c = 1 if df_comps.empty else df_comps['id'].max() + 1
                    
                    new_comp = pd.DataFrame([{
                        "id": new_id_c,
                        "sistema_id": sistema_id_final, # Vinculamos al Sistema
                        "nombre": nombre_comp,
                        "marca": marca,
                        "modelo": modelo,
                        "cantidad": cantidad,
                        "categoria": categoria,
                        "repuesto_sku": sku_final,
                        "specs_json": json.dumps(specs)
                    }])
                    
                    save_data(pd.concat([df_comps, new_comp], ignore_index=True), "componentes")
                    st.success("✅ Componente guardado con éxito")
