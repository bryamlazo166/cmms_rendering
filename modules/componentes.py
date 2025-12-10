import streamlit as st
import pandas as pd
import json
from datetime import datetime
from utils.db_con import get_data, save_data

def render_componentes_view():
    st.header("2. Asignación de Componentes y Datos Técnicos")
    
    # 1. Obtener lista de Equipos (Padres)
    df_equipos = get_data("equipos")
    
    if df_equipos.empty:
        st.warning("⚠️ No hay equipos registrados. Ve al Maestro de Equipos primero.")
        return

    equipo_tags = df_equipos["tag"].tolist()
    padre_sel = st.selectbox("Seleccione Equipo Principal", equipo_tags)
    
    st.divider()
    
    col_izq, col_der = st.columns([1, 1])
    
    with col_izq:
        nombre_comp = st.text_input("Nombre Componente", placeholder="Ej: Motor Principal")
        categoria = st.selectbox("Categoría", ["Motor Electrico", "Motoreductor", "Transmision (Fajas)", "Rodamiento / Chumacera"])
        
        # --- AQUÍ ESTÁ LA CONEXIÓN CON ALMACÉN ---
        st.write("📦 **Vinculación con Repuesto**")
        df_almacen = get_data("almacen")
        lista_repuestos = ["Ninguno"]
        
        if not df_almacen.empty:
            # Creamos formato visual: "SKU | DESCRIPCION"
            # Aseguramos que sean strings para evitar errores
            df_almacen['display'] = df_almacen['sku'].astype(str) + " | " + df_almacen['descripcion'].astype(str)
            lista_repuestos += df_almacen['display'].tolist()
            
        sku_seleccionado = st.selectbox("Seleccionar del Stock", lista_repuestos)
        
        # Limpiamos para guardar solo el SKU en la base de datos
        sku_final = ""
        if sku_seleccionado != "Ninguno":
            sku_final = sku_seleccionado.split(" | ")[0]
        # -----------------------------------------

    # Lógica de Especificaciones Técnicas (JSON)
    with col_der:
        st.markdown(f"**Especificaciones: {categoria}**")
        specs = {}
        
        if categoria == "Motor Electrico":
            specs["potencia_hp"] = st.number_input("Potencia (HP)", min_value=0.1)
            specs["rpm"] = st.number_input("RPM", step=10)
            specs["voltaje"] = st.selectbox("Voltaje", ["220V", "440V", "380V"])
            specs["frame"] = st.text_input("Frame / Carcasa")
            
        elif categoria == "Transmision (Fajas)":
            specs["perfil"] = st.selectbox("Perfil", ["A", "B", "C", "SPA", "SPB", "5V"])
            specs["cantidad"] = st.number_input("Cantidad", min_value=1)
            specs["codigo"] = st.text_input("Código Comercial", placeholder="Ej: B-52")
            
        elif categoria == "Motoreductor":
            specs["ratio"] = st.text_input("Relación (Ratio)", placeholder="1:20")
            specs["eje_salida"] = st.number_input("Eje Salida (mm)")
            specs["aceite"] = st.text_input("Tipo Aceite", value="ISO VG 220")
            
        elif categoria == "Rodamiento / Chumacera":
            specs["numero"] = st.text_input("Número ISO", placeholder="6302-ZZ")
            specs["tipo"] = st.selectbox("Tipo", ["Bola", "Rodillo", "Chumacera"])
            specs["grasera"] = st.checkbox("Tiene grasera?", value=True)

    if st.button("Guardar Componente"):
        if nombre_comp:
            df_comps = get_data("componentes")
            new_id = 1 if df_comps.empty else df_comps['id'].max() + 1
            
            # Guardamos specs como texto JSON
            json_specs = json.dumps(specs)
            
            new_comp = pd.DataFrame([{
                "id": new_id, 
                "equipo_tag": padre_sel, 
                "nombre": nombre_comp,
                "categoria": categoria, 
                "specs_json": json_specs,
                "repuesto_sku": sku_final, # Guardamos el SKU vinculado
                "fecha_instalacion": datetime.now().strftime("%Y-%m-%d")
            }])
            
            df_final = pd.concat([df_comps, new_comp], ignore_index=True)
            save_data(df_final, "componentes")
            st.success(f"✅ Componente '{nombre_comp}' guardado y vinculado con repuesto {sku_final}.")
            st.cache_data.clear()
        else:
            st.error("❌ El nombre del componente es obligatorio")
