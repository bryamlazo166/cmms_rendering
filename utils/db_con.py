import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

def get_data(worksheet_name):
    """
    Lee los datos de la hoja especificada.
    TTL=0 evita que se quede pegado con datos viejos (Caché).
    """
    conn = st.connection("gsheets", type=GSheetsConnection)
    try:
        df = conn.read(worksheet=worksheet_name, ttl=0)
        return df
    except Exception:
        # Si falla (ej: hoja vacía), retornamos un DF vacío
        return pd.DataFrame()

def save_data(df, worksheet_name):
    """
    Guarda los datos en Google Sheets.
    IMPORTANTE: Limpia los NaN para evitar APIError.
    """
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    # --- LA SOLUCIÓN AL ERROR ---
    # Convertimos todos los valores nulos/NaN a cadenas vacías ""
    # Google Sheets NO acepta NaN.
    df_clean = df.fillna("")
    
    conn.update(worksheet=worksheet_name, data=df_clean)
