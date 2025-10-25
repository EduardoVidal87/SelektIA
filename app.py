# app.py
# -*- coding: utf-8 -*-

import io
import base64
from pathlib import Path
from datetime import date, datetime

import streamlit as st
import pandas as pd

# ======================================================================================
# CONFIGURACIÓN BÁSICA
# ======================================================================================

st.set_page_config(
    page_title="SelektIA",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Paleta y rutas de assets (CAMBIO: tamaño de logo 220)
PRIMARY_GREEN = "#00CD78"
SIDEBAR_BG = "#0E192B"  # fondo panel izquierdo
LOGO_PATH = "assets/selektia-logo.png"  # tu archivo de logo
LOGO_WIDTH = 220  # <<— Aumentado. Ajusta si lo quieres aún más grande.

# ======================================================================================
# CSS — (mantenemos diseño; solo branding y botones a la izquierda)
# ======================================================================================

CSS = f"""
:root {{
  --green: {PRIMARY_GREEN};
  --sidebar-bg: {SIDEBAR_BG};
}}

html, body, [data-testid="stAppViewContainer"] {{
  background: #F7FBFF !important;
}}

[data-testid="stSidebar"] {{
  background: var(--sidebar-bg) !important;
  color: #fff !important;
  padding-top: 10px !important;
  border-right: 1px solid #0E2033;
}}

/* Branding del sidebar (NO se recolorea el logo; solo el texto “Powered…”) */
.sidebar-brand {{
  display:flex; flex-direction:column; align-items:center; justify-content:center;
  padding: 8px 10px 14px 10px;
}}
.sidebar-brand .sidebar-logo {{
  display:flex; align-items:center; justify-content:center; width:100%;
}}
.sidebar-brand .sidebar-logo img {{
  max-width: 100%;
  width: {LOGO_WIDTH}px;     /* <<— tamaño de logo */
  height: auto;
  -webkit-filter: none; filter: none; /* respeta colores del archivo */
}}
.sidebar-brand .brand-sub {{
  margin-top: 4px;
  font-size: 12px;
  font-weight: 600;
  color: #00CD78;            /* <<— “Powered by Wayki Consulting” con color del logo */
  opacity: 1;
}}

.sidebar-section-title {{
  margin: 18px 12px 8px;
  font-size: 11.5px;
  letter-spacing: .5px;
  font-weight: 800;
  color: var(--green);
  text-transform: uppercase;
}}

/* Botones del sidebar: texto a la izquierda (mantenemos) */
.sidebar-btn > button {{
  width: 100% !important;
  background: #0F2138 !important;  /* mismo tono del panel ya aprobado */
  border: 1px solid #0F2138 !important;
  color: #FFFFFF !important;
  text-align: left !important;           /* IZQUIERDA */
  justify-content: flex-start !important;/* IZQUIERDA */
  padding: 10px 14px !important;
  border-radius: 10px !important;
  margin: 6px 10px !important;
  font-weight: 600 !important;
}}
.sidebar-btn > button:hover {{
  border-color: var(--green) !important;
  box-shadow: 0 0 0 1px var(--green) inset !important;
}}

h1, h2, h3 {{
  color: #142433;
}}
h1 strong, h2 strong, h3 strong {{
  color: var(--green);
}}

/* Botones del cuerpo: texto a la izquierda (como acordamos) */
.stButton > button {{
  text-align: left !important;
  justify-content: flex-start !important;
}}
"""

st.markdown(f"<style>{CSS}</style>", unsafe_allow_html=True)

# ======================================================================================
# ESTADO / ROUTER
# ======================================================================================

if "route" not in st.session_state:
    st.session_state.route = "Definición & Carga"

# ======================================================================================
# UTILIDADES (branding y navegación)
# ======================================================================================

def nav_btn(label: str, route: str):
    """Botón de navegación alineado a la izquierda (sidebar)."""
    key = f"nav_{route}"
    if st.button(label, key=key, use_container_width=True):
        st.session_state.route = route
        st.experimental_rerun()

def render_sidebar_logo():
    """Logo centrado + powered en color del logo; NO altera colores del archivo."""
    try:
        b = open(LOGO_PATH, "rb").read()
        encoded = base64.b64encode(b).decode()
        ext = Path(LOGO_PATH).suffix[1:]
        st.markdown(
            f"""
            <div class="sidebar-brand">
              <div class="sidebar-logo">
                <img src="data:image/{ext};base64,{encoded}" alt="SelektIA"/>
              </div>
              <div class="brand-sub">Powered by Wayki Consulting</div>
            </div>
            """,
            unsafe_allow_html=True
        )
    except Exception:
        # Fallback si no encuentra la imagen
        st.markdown(
            """
            <div class="sidebar-brand">
              <div style="font-size:26px;font-weight:800;color:#00CD78">SelektIA</div>
              <div class="brand-sub">Powered by Wayki Consulting</div>
            </div>
            """,
            unsafe_allow_html=True
        )

# ======================================================================================
# SIDEBAR — NAVEGACIÓN (sin cambios en boxes/estructura)
# ======================================================================================

with st.sidebar:
    render_sidebar_logo()

    # Bloque compacto
    st.markdown('<div class="sidebar-section-title">Dashboard</div>', unsafe_allow_html=True)
    with st.container():
        st.markdown('<div class="sidebar-btn">', unsafe_allow_html=True)
        nav_btn("Analytics", "Analytics")
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="sidebar-section-title">Asistente IA</div>', unsafe_allow_html=True)
    with st.container():
        st.markdown('<div class="sidebar-btn">', unsafe_allow_html=True)
        nav_btn("Flujos", "Flujos")
        nav_btn("Agentes", "Agentes")             # aquí está la configuración del asistente
        nav_btn("Tareas de Agente", "Tareas de Agente")
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="sidebar-section-title">Proceso de Selección</div>', unsafe_allow_html=True)
    with st.container():
        st.markdown('<div class="sidebar-btn">', unsafe_allow_html=True)
        nav_btn("Definición & Carga", "Definición & Carga")
        nav_btn("Puestos", "Puestos")
        nav_btn("Evaluación de CVs", "Evaluación de CVs")
        nav_btn("Pipeline de Candidatos", "Pipeline de Candidatos")
        nav_btn("Entrevista (Gerencia)", "Entrevista (Gerencia)")
        nav_btn("Tareas del Headhunter", "Tareas del Headhunter")
        nav_btn("Oferta", "Oferta")
        nav_btn("Onboarding", "Onboarding")
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="sidebar-section-title">Acciones</div>', unsafe_allow_html=True)
    with st.container():
        st.markdown('<div class="sidebar-btn">', unsafe_allow_html=True)
        nav_btn("Crear tarea", "Crear tarea")
        st.markdown("</div>", unsafe_allow_html=True)

# ======================================================================================
# PÁGINAS (igual que antes; placeholders donde aplicaba)
# ======================================================================================

def page_analytics():
    st.header("Analytics")
    st.info("(Placeholder) Aquí puedes renderizar tus KPIs y gráficos.")

def page_definicion():
    st.header("Definición & Carga")

    puesto = st.selectbox(
        "Puesto",
        ["Enfermera/o Asistencial","Tecnólogo/a Médico","Recepcionista de Admisión","Médico/a General","Químico/a Farmacéutico/a"],
        index=0,
        key="def_puesto"
    )

    jd = st.text_area("Descripción / JD", height=220, key="def_jd")
    keywords = st.text_area(
        "Palabras clave (coma separada)",
        value="HIS, SAP IS-H, BLS, ACLS, IAAS, educación al paciente, seguridad del paciente, protocolos",
        key="def_kw"
    )

    files = st.file_uploader("Subir CVs (PDF o TXT)", type=["pdf","txt"], accept_multiple_files=True, key="def_upl")
    if files:
        st.success(f"{len(files)} archivo(s) listos para procesar.")

def page_puestos():
    st.header("Puestos")
    # demo de la tabla aprobada
    df = pd.DataFrame([
        {"Puesto":"Desarrollador/a Backend (Python)","Días Abierto":3,"Leads":1800,"Nuevos":115,"Recruiter Screen":35,"HM Screen":7,"Entrevista Telefónica":14,"Entrevista Presencial":15,"Ubicación":"Lima, Perú","Hiring Manager":"Rivers Brykson","Estado":"Abierto","ID":"10,645,194"},
        {"Puesto":"VP de Marketing","Días Abierto":28,"Leads":8100,"Nuevos":1,"Recruiter Screen":15,"HM Screen":35,"Entrevista Telefónica":5,"Entrevista Presencial":7,"Ubicación":"Santiago, Chile","Hiring Manager":"Angela Cruz","Estado":"Abierto","ID":"10,376,415"},
        {"Puesto":"Planner de Demanda","Días Abierto":28,"Leads":2300,"Nuevos":26,"Recruiter Screen":3,"HM Screen":8,"Entrevista Telefónica":6,"Entrevista Presencial":3,"Ubicación":"Ciudad de México, MX","Hiring Manager":"Rivers Brykson","Estado":"Abierto","ID":"10,376,646"},
    ])
    st.dataframe(df, use_container_width=True, height=420)

def page_eval_cvs():
    st.header("Evaluación de CVs")
    st.info("(Placeholder) Conecta aquí tu evaluación.")

def page_pipeline():
    st.header("Pipeline de Candidatos")
    left, right = st.columns([1.1, 1])
    with left:
        st.subheader("Candidatos")
        # lista demo
        cands = [
            "CV_01_Daniela_Rojas_Enfermera_Asistencial.pdf — 70%",
            "CV_02_Mariana_Gutierrez.pdf — 70%",
            "CV_03_Karla_Mendoza.pdf — 70%",
            "CV_04_Lucia_Paredes.pdf — 70%",
            "CV_05_Rocio_Aguilar.pdf — 43%",
        ]
        sel = st.radio("", cands, index=0, label_visibility="collapsed")
        if st.button("Mover a 'Entrevista (Gerencia)'", key="pl_to_mgr", use_container_width=True):
            st.success("Candidato derivado a la pestaña Entrevista (Gerencia).")
    with right:
        st.subheader("Detalle del candidato")
        st.write("Match estimado: **Alto**")
        st.caption("Validated Skills: HIS")
        st.caption("Likely Skills: —")
        st.caption("Skills to Validate: HIS, SAP IS-H, BLS, ACLS, IAAS, educación al paciente")

def page_entrevista():
    st.header("Entrevista (Gerencia)")
    st.info("(Placeholder) Rúbrica y consolidado se visualizan aquí.")

def page_tareas_hh():
    st.header("Tareas del Headhunter")
    st.info("(Placeholder) Checklist HH, notas obligatorias y adjuntos.")

def page_oferta():
    st.header("Oferta")
    if "offers" not in st.session_state:
        st.session_state.offers = {}

    cand = st.text_input("Candidato", value="CV_02_Mariana_Gutierrez.pdf")
    salario = st.text_input("Salario neto (rango)", value="S/ 4,500 – 5,200")
    beneficios = st.text_input("Bonos/beneficios", value="Bono anual, EPS")
    inicio = st.date_input("Fecha de inicio", value=date.today())
    aprobadores = st.multiselect("Aprobadores", ["Gerencia","Legal","Finanzas"], default=["Gerencia","Legal","Finanzas"])

    cols = st.columns([1,1,1,2])
    if cols[0].button("Enviar", use_container_width=True):
        st.session_state.offers[cand] = {
            "estado": "Enviada",
            "salario": salario,
            "beneficios": beneficios,
            "inicio": str(inicio),
            "aprobadores": aprobadores,
            "ts": datetime.utcnow().isoformat()
        }
        st.success("Oferta enviada.")
    if cols[1].button("Registrar contraoferta", use_container_width=True):
        st.session_state.offers[cand] = st.session_state.offers.get(cand, {})
        st.session_state.offers[cand]["estado"] = "Contraoferta"
        st.success("Contraoferta registrada.")
    if cols[2].button("Marcar aceptada", use_container_width=True):
        st.session_state.offers[cand] = st.session_state.offers.get(cand, {})
        st.session_state.offers[cand]["estado"] = "Aceptada"
        st.success("Oferta aceptada. Se disparará Onboarding automáticamente.")

    estado = st.session_state.offers.get(cand, {}).get("estado", "—")
    st.write(f"**Estado actual:** {estado}")

def page_onboarding():
    st.header("Onboarding")
    st.info("(Placeholder) Checklist con fechas límite y responsables.")

def page_flujos():
    st.header("Flujos")
    st.info("(Placeholder) Define o visualiza flujos del proceso.")

def page_agentes():
    st.header("Agentes (Asistente IA)")
    st.caption("Configura tu asistente. Al guardar, se conserva en sesión.")
    as_state = st.session_state.setdefault("asistente_cfg", {
        "rol":"Headhunter",
        "objetivo":"Identificar a los mejores profesionales para el cargo definido en el JD",
        "backstory":"Eres un analista de RR.HH. con experiencia en análisis de documentos, CV y currículums.",
        "guardrails":"No compartas datos sensibles. Cita siempre la fuente (CV o JD) al argumentar.",
        "herr": ["Parser de PDF", "Recomendador …"]
    })

    as_state["rol"] = st.selectbox("Rol*", ["Headhunter","Coordinador RR.HH.","HM","Gerencia"], index=0, key="ag_rol")
    as_state["objetivo"] = st.text_input("Objetivo*", value=as_state["objetivo"], key="ag_goal")
    as_state["backstory"] = st.text_area("Backstory*", value=as_state["backstory"], height=120, key="ag_back")
    as_state["guardrails"] = st.text_area("Guardrails", value=as_state["guardrails"], height=80, key="ag_guard")
    as_state["herr"] = st.multiselect("Herramientas habilitadas", ["Parser de PDF","Recomendador …","Extractor entidades"], default=as_state["herr"], key="ag_tools")

    if st.button("Crear/Actualizar Asistente", use_container_width=True):
        st.session_state.asistente_cfg = as_state
        st.success("Asistente guardado. Esta configuración guiará la evaluación de CVs.")

def page_tareas_agente():
    st.header("Tareas de Agente")
    st.info("(Placeholder) Muestra tareas de tu asistente/agente.")

def page_crear_tarea():
    st.header("Crear tarea")
    titulo = st.text_input("Título")
    desc = st.text_area("Descripción", height=160)
    fecha = st.date_input("Fecha límite", value=date.today())
    if st.button("Guardar", use_container_width=True):
        st.success("Tarea guardada.")

# ======================================================================================
# ROUTER
# ======================================================================================

ROUTES = {
    "Analytics": page_analytics,
    "Definición & Carga": page_definicion,
    "Puestos": page_puestos,
    "Evaluación de CVs": page_eval_cvs,
    "Pipeline de Candidatos": page_pipeline,
    "Entrevista (Gerencia)": page_entrevista,
    "Tareas del Headhunter": page_tareas_hh,
    "Oferta": page_oferta,
    "Onboarding": page_onboarding,
    "Flujos": page_flujos,
    "Agentes": page_agentes,
    "Tareas de Agente": page_tareas_agente,
    "Crear tarea": page_crear_tarea,
}

ROUTES.get(st.session_state.route, page_definicion)()
