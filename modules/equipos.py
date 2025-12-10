import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

def get_connection():
    """Centraliza la conexión."""
    return st.connection("gsheets", type=GSheetsConnection)

def get_data(worksheet):
    """Trae datos frescos sin caché."""
    conn = get_connection()
    try:
        return conn.read(worksheet=worksheet, ttl=0)
    except:
        return pd.DataFrame()

def save_data(df, worksheet):
    """Guarda datos."""
    conn = get_connection()
    conn.update(worksheet=worksheet, data=df)
