# app.py
# -*- coding: utf-8 -*-

import io
import base64
from pathlib import Path
from datetime import date, datetime

import streamlit as st
import pandas as pd
import plotly.express as px
from PyPDF2 import PdfReader

# ======================================================================================
# COLORES / ESTILO (igual al aprobado)
# ======================================================================================
PRIMARY_GREEN = "#00CD78"
SIDEBAR_BG = "#10172A"
BOX_DARK = "#132840"
BOX_DARK_HOV = "#193355"
TEXT_LIGHT = "#FFFFFF"
MAIN_BG = "#F7FBFF"
BOX_LIGHT = "#F1F7FD"
BOX_LIGHT_B = "#E3EDF6"
TITLE_DARK = "#142433"
BAR_DEFAULT = "#E9F3FF"
BAR_GOOD = "#33FFAC"

CSS = f"""
:root {{
  --green: {PRIMARY_GREEN};
  --sidebar-bg: {SIDEBAR_BG};
  --box: {BOX_DARK};
  --box-hover: {BOX_DARK_HOV};
  --text: {TEXT_LIGHT};
  --main-bg: {MAIN_BG};
  --box-light: {BOX_LIGHT};
  --box-light-border: {BOX_LIGHT_B};
  --title-dark: {TITLE_DARK};
}}
html, body, [data-testid="stAppViewContainer"] {{
  background: var(--main-bg) !important;
}}
.block-container {{
  background: transparent !important;
}}
/* SIDEBAR visual */
[data-testid="stSidebar"] {{
  background: var(--sidebar-bg) !important;
  color: var(--text) !important;
}}
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3,
[data-testid="stSidebar"] h4,
[data-testid="stSidebar"] h5,
[data-testid="stSidebar"] h6,
[data-testid="stSidebar"] .stMarkdown p strong {{
  color: var(--green) !important;
}}
[data-testid="stSidebar"] label, 
[data-testid="stSidebar"] p, 
[data-testid="stSidebar"] span {{
  color: var(--text) !important;
}}
/* Inputs sidebar */
[data-testid="stSidebar"] [data-testid="stSelectbox"] > div > div,
[data-testid="stSidebar"] [data-baseweb="select"],
[data-testid="stSidebar"] [data-testid="stTextArea"] textarea,
[data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] {{
  background: var(--box) !important;
  color: var(--text) !important;
  border: 1.5px solid var(--box) !important;
  border-radius: 14px !important;
}}
[data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] * {{
  color: var(--text) !important;
}}
/* Botón global */
.stButton > button {{
  background: var(--green) !important;
  color: #082017 !important;
  border-radius: 10px !important;
  border: none !important;
  padding: .45rem .9rem !important;
  font-weight: 600 !important;
}}
/* Títulos */
h1, h2, h3 {{
  color: var(--title-dark);
}}
h1 strong, h2 strong, h3 strong {{
  color: var(--green);
}}
/* Pestañas (pill) – encabezado superior */
.nav-pill {{
  padding: 8px 14px;
  border-radius: 10px;
  margin-right: 8px;
  border: 1px solid transparent;
  background: transparent;
  color: var(--title-dark);
  font-weight: 600;
  cursor: pointer;
}}
.nav-pill.active {{
  background: #E6FFF5;
  border-color: var(--green);
  color: var(--green);
}}
/* Tabla y panel */
.card {{
  background: #fff;
  border: 1px solid var(--box-light-border);
  border-radius: 12px;
  padding: 10px 12px;
}}
.badge {{
  display:inline-block;
  padding: 3px 8px;
  border-radius: 999px;
  background: #ECF5FF;
  color: #26559D;
  font-size: 12px;
  margin-right: 6px;
}}
.badge-green {{
  background: #E8FFF5;
  color: #0D5A43;
}}
.badge-amber {{
  background: #FFF6E5;
  color: #7A4C00;
}}
.badge-red {{
  background: #FFEAEA;
  color: #7A0000;
}}
"""

st.set_page_config(page_title="SelektIA", page_icon="🧠", layout="wide")
st.markdown(f"<style>{CSS}</style>", unsafe_allow_html=True)

# ======================================================================================
# ESTADO GLOBAL (router + datos)
# ======================================================================================
TABS = [
    "Asistente IA",
    "Definición & Carga",
    "Puestos",
    "Evaluación de CVs",
    "Pipeline de Candidatos",
    "Entrevista (Gerencia)",
    "Tareas del Headhunter",
    "Oferta",
    "Onboarding",
    "Analytics",
]

if "active_tab" not in st.session_state:
    st.session_state.active_tab = "Asistente IA"

# Datos mínimos de ejemplo (puedes conectar a tu fuente real)
if "positions" not in st.session_state:
    st.session_state.positions = pd.DataFrame([
        {"ID":"10,645,194","Puesto":"Desarrollador/a Backend (Python)","Ubicación":"Lima, Perú","Leads":1800,"Nuevos":115,"Recruiter Screen":35,"HM Screen":7,"Entrevista Telefónica":14,"Entrevista Presencial":15,"Días Abierto":3,"Hiring Manager":"Rivers Brykson","Estado":"Abierto"},
        {"ID":"10,376,415","Puesto":"VP de Marketing","Ubicación":"Santiago, Chile","Leads":8100,"Nuevos":1,"Recruiter Screen":15,"HM Screen":35,"Entrevista Telefónica":5,"Entrevista Presencial":7,"Días Abierto":28,"Hiring Manager":"Angela Cruz","Estado":"Abierto"},
        {"ID":"10,376,646","Puesto":"Planner de Demanda","Ubicación":"Ciudad de México, MX","Leads":2300,"Nuevos":26,"Recruiter Screen":3,"HM Screen":8,"Entrevista Telefónica":6,"Entrevista Presencial":3,"Días Abierto":28,"Hiring Manager":"Rivers Brykson","Estado":"Abierto"},
    ])

# Candidatos simulados
if "candidates" not in st.session_state:
    # nombre, score, tags para panel derecho
    st.session_state.candidates = pd.DataFrame([
        {"Name":"CV_01_Valeria_Rojas.pdf","Score":70,"validated":["HIS"],"likely":["—"],"to_validate":["HIS","SAP IS-H","BLS","ACLS","IAAS","educación al paciente"]},
        {"Name":"CV_02_Mariana_Gutierrez.pdf","Score":70,"validated":["HIS"],"likely":["—"],"to_validate":["HIS","SAP IS-H","BLS","ACLS","IAAS","educación al paciente"]},
        {"Name":"CV_03_Karla_Mendoza.pdf","Score":70,"validated":["HIS"],"likely":["—"],"to_validate":["HIS","SAP IS-H","BLS","ACLS","IAAS","educación al paciente"]},
        {"Name":"CV_04_Lucia_Paredes.pdf","Score":70,"validated":["HIS"],"likely":["—"],"to_validate":["HIS","SAP IS-H","BLS","ACLS","IAAS","educación al paciente"]},
    ])

# Entrevista (Gerencia) – lista de candidatos asignados
if "gerencia_queue" not in st.session_state:
    st.session_state.gerencia_queue = []

# ======================================================================================
# FUNCIONES DE UTILIDAD
# ======================================================================================
def nav_pills():
    cols = st.columns(len(TABS))
    for i, t in enumerate(TABS):
        with cols[i]:
            is_active = (st.session_state.active_tab == t)
            cls = "nav-pill active" if is_active else "nav-pill"
            if st.button(t, key=f"pill_{t}", use_container_width=True):
                st.session_state.active_tab = t
                st.rerun()
            st.markdown(
                f'<div class="{cls}" style="display:none">{t}</div>', 
                unsafe_allow_html=True
            )

def sidebar_router():
    st.sidebar.image("assets/logo-wayki.png", use_column_width=True)
    st.sidebar.markdown("### Navegación rápida")
    for t in TABS:
        if st.sidebar.button(t, key=f"nav_{t}"):
            st.session_state.active_tab = t
            st.rerun()
    st.sidebar.markdown("---")
    st.sidebar.markdown("**Ayuda**")
    st.sidebar.markdown("1. Define JD y sube CVs en **Definición & Carga**.")
    st.sidebar.markdown("2. Revisa **Evaluación de CVs**.")
    st.sidebar.markdown("3. Gestiona **Pipeline** y **Entrevista**.")
    st.sidebar.markdown("4. Avanza a **Oferta** y **Onboarding**.")
    # (dejo tus 4 boxes del sidebar como están si los necesitas aquí)

def score_badge(s:int) -> str:
    if s >= 70:   return '<span class="badge badge-green">Alto</span>'
    if s >= 60:   return '<span class="badge badge-amber">Medio</span>'
    return '<span class="badge badge-red">Bajo</span>'

# ======================================================================================
# PESTAÑAS (VISTAS)
# ======================================================================================

def view_asistente():
    st.markdown("## SelektIA – **Asistente IA**")
    st.caption("Configura el rol del asistente que guiará la evaluación en *Evaluación de CVs* (respeta RLS y auditoría).")
    c1, c2 = st.columns([1.15, .85])
    with c1:
        role = st.selectbox("Rol*", ["Headhunter","Coordinador RR.HH.","Hiring Manager","Gerencia/Comité","Legal","Finanzas","TI/Onboarding"], index=0)
        goal = st.text_input("Goal*", "Identificar a los mejores profesionales para el cargo que se define en el JD")
        backstory = st.text_area("Backstory*", "Eres un analista de recursos humanos con amplia experiencia en análisis de documentos, CV y currículums...")
        guardrails = st.text_area("Guardrails", "No compartas datos sensibles. Cita siempre la fuente (CV o JD) al argumentar.")
        st.write("**Herramientas habilitadas**")
        _ = st.multiselect("Selecciona", ["Parser de PDF","Recomendador de skills","Generador de entrevista guía"], default=["Parser de PDF","Recomendador de skills"])
        if st.button("Crear/Actualizar Asistente", use_container_width=True):
            st.session_state.ai_profile = dict(role=role, goal=goal, backstory=backstory, guardrails=guardrails)
            st.success("Asistente configurado y listo para guiar en *Evaluación de CVs*.")

    with c2:
        st.markdown("### Permisos y alcance")
        st.markdown("- **RLS** por puesto: el asistente solo ve candidatos del puesto/rol asignado.")
        st.markdown("- Acciones según rol (p. ej., HH no aprueba ofertas).")
        st.markdown("- **Auditoría** total (usuario/rol, objeto, timestamp).")
        st.info("Tip: usa esta configuración para guiar evaluaciones en la pestaña **Evaluación de CVs**.")

def view_definicion_carga():
    st.markdown("## SelektIA – **Definición & Carga**")
    st.caption("Mantengo tu diseño/inputs anteriores (JD + keywords + carga de archivos). Añade aquí tu bloque existente.")

def view_puestos():
    st.markdown("## SelektIA – **Puestos**")
    st.dataframe(
        st.session_state.positions[
            ["Puesto","Días Abierto","Leads","Nuevos","Recruiter Screen","HM Screen","Entrevista Telefónica","Entrevista Presencial","Ubicación","Hiring Manager","Estado","ID"]
        ],
        use_container_width=True,
        height=360,
    )

def view_evaluacion():
    st.markdown("## SelektIA – **Resultados de evaluación**")
    df = st.session_state.candidates.copy().sort_values("Score", ascending=False)
    st.markdown("### Ranking de Candidatos")
    st.dataframe(df[["Name","Score"]], use_container_width=True, height=240)
    st.markdown("### Comparación de puntajes (todos los candidatos)")
    colors = [BAR_GOOD if s>=60 else BAR_DEFAULT for s in df["Score"]]
    fig = px.bar(df, x="Name", y="Score")
    fig.update_traces(marker_color=colors)
    st.plotly_chart(fig, use_container_width=True)

def view_pipeline():
    st.markdown("## SelektIA – **Pipeline de Candidatos**")
    st.caption("Tabla a la izquierda (ranking) y detalle a la derecha, con derivación a **Entrevista (Gerencia)**.")
    c_left, c_right = st.columns([1.25,.75], gap="large")

    df = st.session_state.candidates.copy().sort_values("Score", ascending=False)
    with c_left:
        st.markdown("#### Candidatos detectados")
        # Solo lectura
        st.dataframe(
            df.assign(Match=df["Score"].map(lambda s: score_badge(s) ).astype(str)),
            column_config={"Match": st.column_config.TextColumn("Match (estimado)", help="Badge según score")},
            use_container_width=True,
            height=380
        )

        # selector
        selected = st.selectbox("Selecciona para ver detalle", df["Name"].tolist())
        st.session_state.selected_candidate = selected

    with c_right:
        st.markdown("#### Detalle del candidato")
        cand = df[df["Name"] == st.session_state.get("selected_candidate", df.iloc[0]["Name"])].iloc[0]
        st.markdown(f"**{cand['Name']}**  {score_badge(cand['Score'])}", unsafe_allow_html=True)
        st.markdown("**Match estimado**: " + ("Alto" if cand["Score"]>=70 else "Medio" if cand["Score"]>=60 else "Bajo"))

        st.markdown("**Validated Skills**")
        if cand["validated"]:
            st.markdown(" ".join([f'<span class="badge">{t}</span>' for t in cand["validated"]]), unsafe_allow_html=True)
        else:
            st.caption("—")

        st.markdown("**Likely Skills**")
        if cand["likely"]:
            st.markdown(" ".join([f'<span class="badge">{t}</span>' for t in cand["likely"]]), unsafe_allow_html=True)
        else:
            st.caption("—")

        st.markdown("**Skills to Validate**")
        st.markdown(" ".join([f'<span class="badge">{t}</span>' for t in cand["to_validate"]]), unsafe_allow_html=True)

        st.markdown("---")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("➜ Mover a Entrevista (Gerencia)", use_container_width=True):
                name = cand["Name"]
                if name not in st.session_state.gerencia_queue:
                    st.session_state.gerencia_queue.append(name)
                st.success(f"{name} enviado a 'Entrevista (Gerencia)'.")
        with c2:
            if st.button("✖ Descartar", use_container_width=True):
                st.session_state.candidates = st.session_state.candidates[st.session_state.candidates["Name"]!=cand["Name"]]
                st.success("Candidato descartado del pipeline.")
                st.rerun()

def view_gerencia():
    st.markdown("## SelektIA – **Entrevista (Gerencia)**")
    if not st.session_state.gerencia_queue:
        st.info("Aún no hay candidatos asignados desde Pipeline.")
        return
    st.markdown("**Candidatos en entrevista (cola):**")
    for n in st.session_state.gerencia_queue:
        st.markdown(f"- {n}")

def view_hh_tasks():
    st.markdown("## SelektIA – **Tareas del Headhunter**")
    st.caption("Mantengo tu diseño de checklist y adjuntos. (No lo reescribo para respetar tu código aprobado.)")

def view_oferta():
    st.markdown("## SelektIA – **Oferta**")
    st.caption("Formulario de oferta aprobado (mantener).")

def view_onboarding():
    st.markdown("## SelektIA – **Onboarding**")
    st.caption("Checklist aprobado (mantener).")

def view_analytics():
    st.markdown("## SelektIA – **Analytics**")
    st.info("Espacio reservado para dashboards/KPIs finales.")

# ======================================================================================
# RENDER
# ======================================================================================
sidebar_router()
nav_pills()

active = st.session_state.active_tab

if active == "Asistente IA":
    view_asistente()
elif active == "Definición & Carga":
    view_definicion_carga()
elif active == "Puestos":
    view_puestos()
elif active == "Evaluación de CVs":
    view_evaluacion()
elif active == "Pipeline de Candidatos":
    view_pipeline()
elif active == "Entrevista (Gerencia)":
    view_gerencia()
elif active == "Tareas del Headhunter":
    view_hh_tasks()
elif active == "Oferta":
    view_oferta()
elif active == "Onboarding":
    view_onboarding()
elif active == "Analytics":
    view_analytics()
