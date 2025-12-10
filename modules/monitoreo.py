import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from utils.db_con import get_data, save_data

def render_monitoreo_view():
    st.header("📈 Monitoreo de Condición (CBM)")
    
    # 1. Cargar datos
    df_equipos = get_data("equipos")
    df_componentes = get_data("componentes")
    
    if df_equipos.empty:
        st.warning("No hay equipos registrados.")
        return

    # 2. Filtros en Cascada
    # Planta
    plantas = df_equipos["planta"].unique() if "planta" in df_equipos.columns else []
    planta_sel = st.selectbox("1. Planta", plantas)
    
    # Área (Filtrada)
    areas = df_equipos[df_equipos["planta"] == planta_sel]["area"].unique() if not df_equipos.empty else []
    area_sel = st.selectbox("2. Área", areas)
    
    # Equipo (Filtrado)
    eqs = df_equipos[(df_equipos["planta"] == planta_sel) & (df_equipos["area"] == area_sel)]
    # Creamos lista "Nombre | TAG"
    eqs["display"] = eqs["nombre"] + " | " + eqs["tag"]
    eq_sel_str = st.selectbox("3. Equipo", eqs["display"].unique())
    
    if eq_sel_str:
        tag_eq = eq_sel_str.split(" | ")[-1]
        
        # Componente (Filtrado por sistema si existe, o directo por equipo)
        # Nota: Si implementaste sistemas, aquí deberíamos filtrar sistemas primero.
        # Por simplicidad para que compile, listamos todos los componentes vinculados a ese equipo (vía sistemas o directo)
        
        # Primero buscamos sistemas de ese equipo
        df_sistemas = get_data("sistemas")
        ids_sistemas = []
        if not df_sistemas.empty:
            ids_sistemas = df_sistemas[df_sistemas["equipo_tag"] == tag_eq]["id"].tolist()
            
        # Ahora componentes de esos sistemas
        comps_filtrados = pd.DataFrame()
        if not df_componentes.empty and ids_sistemas:
            comps_filtrados = df_componentes[df_componentes["sistema_id"].isin(ids_sistemas)]
            
        if not comps_filtrados.empty:
            comps_filtrados["display"] = comps_filtrados["nombre"] + " (" + comps_filtrados["categoria"] + ")"
            comp_sel_str = st.selectbox("4. Componente", comps_filtrados["display"].unique())
            
            # Recuperar ID para guardar
            comp_row = comps_filtrados[comps_filtrados["display"] == comp_sel_str].iloc[0]
            comp_id = comp_row["id"]
            
            st.divider()
            
            # PESTAÑAS DE ACCIÓN
            t1, t2 = st.tabs(["📝 Nueva Lectura", "📊 Ver Gráfica"])
            
            with t1:
                with st.form("lectura_sensor"):
                    c1, c2 = st.columns(2)
                    param = c1.selectbox("Parámetro", ["Vibración (mm/s)", "Temperatura (°C)", "Ruido (dB)"])
                    val = c2.number_input("Valor", step=0.1)
                    tec = st.text_input("Técnico")
                    
                    if st.form_submit_button("Guardar"):
                        df_lec = get_data("lecturas")
                        new_id = 1 if df_lec.empty else df_lec['id'].max() + 1
                        new_row = pd.DataFrame([{
                            "id": new_id, "componente_id": comp_id,
                            "fecha": datetime.now().strftime("%Y-%m-%d"),
                            "hora": datetime.now().strftime("%H:%M"),
                            "parametro": param, "valor": val, "tecnico": tec
                        }])
                        save_data(pd.concat([df_lec, new_row], ignore_index=True), "lecturas")
                        st.success("Lectura Guardada")
            
            with t2:
                df_hist = get_data("lecturas")
                if not df_hist.empty:
                    # Filtramos por este componente
                    mis_datos = df_hist[df_hist["componente_id"] == comp_id]
                    if not mis_datos.empty:
                        param_ver = st.selectbox("Ver variable:", mis_datos["parametro"].unique())
                        grafico = mis_datos[mis_datos["parametro"] == param_ver]
                        
                        fig = px.line(grafico, x="fecha", y="valor", markers=True, title=f"Tendencia: {param_ver}")
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.info("No hay datos históricos para este componente.")
        else:
            st.warning("Este equipo no tiene componentes registrados en el árbol.")
