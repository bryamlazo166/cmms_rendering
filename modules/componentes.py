import streamlit as st
import pandas as pd
import json
from datetime import datetime
from utils.db_con import get_data, save_data

def render_componentes_view():
    st.header("2. Asignación de Componentes y Datos Técnicos")
    
    # Obtenemos la lista de padres desde el otro módulo (vía DB)
    df_equipos = get_data("equipos")
    
    if df_equipos.empty:
        st.warning("⚠️ No hay equipos registrados. Ve al módulo de Equipos primero.")
        return

    equipo_tags = df_equipos["tag"].tolist()
    padre_sel = st.selectbox("Seleccione Equipo Principal", equipo_tags)
    
    st.divider()
    
    col_izq, col_der = st.columns([1, 1])
    
    with col_izq:
        nombre_comp = st.text_input("Nombre Componente", placeholder="Ej: Motor Principal")
        categoria = st.selectbox("Categoría", ["Motor Electrico", "Motoreductor", "Transmision (Fajas)", "Rodamiento / Chumacera"])
        sku = st.text_input("SKU Repuesto", placeholder="Ej: ROD-6302-ZZ")

    # Lógica de Specs (JSON)
    with col_der:
        st.markdown(f"**Especificaciones: {categoria}**")
        specs = {}
        
        if categoria == "Motor Electrico":
            specs["potencia_hp"] = st.number_input("Potencia (HP)", min_value=0.1)
            specs["rpm"] = st.number_input("RPM", step=10)
            specs["voltaje"] = st.selectbox("Voltaje", ["220V", "440V"])
        elif categoria == "Transmision (Fajas)":
            specs["perfil"] = st.selectbox("Perfil", ["A", "B", "C", "SPA", "5V"])
            specs["cantidad"] = st.number_input("Cantidad", min_value=1)
            specs["codigo"] = st.text_input("Código", placeholder="B-52")
        # ... Puedes agregar más IFs aquí para otros tipos ...

    if st.button("Guardar Componente"):
        if nombre_comp:
            df_comps = get_data("componentes")
            new_id = 1 if df_comps.empty else df_comps['id'].max() + 1
            
            json_specs = json.dumps(specs)
            
            new_comp = pd.DataFrame([{
                "id": new_id, "equipo_tag": padre_sel, "nombre": nombre_comp,
                "categoria": categoria, "specs_json": json_specs,
                "repuesto_sku": sku, "fecha_instalacion": datetime.now().strftime("%Y-%m-%d")
            }])
            
            df_final = pd.concat([df_comps, new_comp], ignore_index=True)
            save_data(df_final, "componentes")
            st.success("Componente agregado exitosamente.")
            st.cache_data.clear()
