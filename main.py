import streamlit as st
import os

st.title("🛠️ Diagnóstico de Archivos")

st.write("Carpeta actual:", os.getcwd())
st.write("Archivos en raíz:", os.listdir('.'))

if os.path.exists('modules'):
    st.write("Archivos en 'modules':", os.listdir('modules'))
else:
    st.error("❌ LA CARPETA 'modules' NO EXISTE O NO SE ENCUENTRA.")

try:
    from modules import gestion_activos
    st.success("✅ ¡ÉXITO! Se pudo importar gestion_activos.")
except ImportError as e:
    st.error(f"❌ Error importando: {e}")
except Exception as e:
    st.error(f"❌ Otro error: {e}")
