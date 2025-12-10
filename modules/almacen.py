import streamlit as st
import pandas as pd
from utils.db_con import get_data, save_data

def render_almacen_view():
    st.header("📦 Gestión de Almacén y Repuestos")
    
    # Pestañas internas del módulo
    tab1, tab2 = st.tabs(["📋 Inventario", "➕ Nuevo Repuesto"])

    # --- TAB 1: VER INVENTARIO ---
    with tab1:
        df_almacen = get_data("almacen")
        
        if not df_almacen.empty:
            # Buscador rápido
            filtro = st.text_input("🔍 Buscar por SKU o Descripción", "")
            if filtro:
                df_almacen = df_almacen[
                    df_almacen['descripcion'].str.contains(filtro, case=False, na=False) |
                    df_almacen['sku'].str.contains(filtro, case=False, na=False)
                ]
            
            st.dataframe(df_almacen, use_container_width=True)
            
            # Métricas rápidas
            st.caption(f"Total de items distintos: {len(df_almacen)}")
        else:
            st.info("El almacén está vacío. Agrega items en la otra pestaña.")

    # --- TAB 2: AGREGAR REPUESTO ---
    with tab2:
        st.subheader("Dar de alta Material")
        with st.form("form_almacen"):
            c1, c2 = st.columns(2)
            sku = c1.text_input("SKU / Código Interno (Único)", placeholder="Ej: ROD-6302-ZZ").strip().upper()
            desc = c2.text_input("Descripción", placeholder="Ej: Rodamiento Rígido de Bolas")
            
            c3, c4, c5 = st.columns(3)
            marca = c3.text_input("Marca / Fabricante")
            stock = c4.number_input("Stock Inicial", min_value=0, step=1)
            unidad = c5.selectbox("Unidad", ["UND", "JGO", "LT", "MT", "KG"])
            
            ubicacion = st.text_input("Ubicación Física", placeholder="Ej: Estante B, Nivel 2")
            
            submitted = st.form_submit_button("Guardar Repuesto")
            
            if submitted:
                # Validaciones
                if not sku or not desc:
                    st.error("El SKU y la Descripción son obligatorios.")
                else:
                    df_actual = get_data("almacen")
                    
                    # Verificar si ya existe el SKU
                    if not df_actual.empty and sku in df_actual['sku'].values:
                        st.error(f"¡El SKU {sku} ya existe en el sistema!")
                    else:
                        new_item = pd.DataFrame([{
                            "sku": sku, "descripcion": desc, "marca": marca,
                            "stock_actual": stock, "unidad": unidad,
                            "ubicacion_fisica": ubicacion, "precio_promedio": 0.0
                        }])
                        
                        df_final = pd.concat([df_actual, new_item], ignore_index=True)
                        save_data(df_final, "almacen")
                        st.success(f"Repuesto {sku} registrado correctamente.")
                        st.cache_data.clear() # Limpiar caché para que aparezca en la lista
