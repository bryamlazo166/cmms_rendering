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
    if df.empty or len(df.columns) == 0:
        return pd.DataFrame(columns=columnas_base)
    for col in columnas_base:
        if col not in df.columns:
            df[col] = None
    return df

def limpiar_id(serie):
    return serie.astype(str).str.replace(r"\.0$", "", regex=True).str.strip()

def gestionar_filtro_dinamico(label, opciones_existentes, key_suffix):
    # 1. Preparar opciones
    if opciones_existentes is None: opciones_existentes = []
    opciones_limpias = [str(x) for x in opciones_existentes if pd.notna(x) and str(x) != ""]
    opciones = sorted(list(set(opciones_limpias)))
    
    opciones.insert(0, "➕ CREAR NUEVO...")
    opciones.insert(0, "Seleccionar...")
    
    # 2. Renderizar
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

# --- ESPECIFICACIONES TÉCNICAS ---
def render_specs_dinamicas(categoria, valores_actuales={}):
    specs = {}
    st.markdown("---")
    st.caption(f"⚙️ Ficha Técnica: {categoria}")
    cat_upper = str(categoria).upper()
    
    if "MOTOR" in cat_upper and "REDUCTOR" not in cat_upper:
        c1, c2, c3 = st.columns(3)
        specs["potencia_hp
