# app.py
# -*- coding: utf-8 -*-

import io
import base64
import re
import json
from pathlib import Path
from datetime import datetime, date, timedelta
import random

import streamlit as st
import pandas as pd
import plotly.express as px
from PyPDF2 import PdfReader

# =========================================================
# PALETA / CONST
# =========================================================
PRIMARY = "#00CD78"
SIDEBAR_BG = "#0E192B"     # fondo panel izquierdo
SIDEBAR_TX = "#B9C7DF"     # texto gris azulado
BODY_BG    = "#F7FBFF"
CARD_BG    = "#0E192B"     # mismo color que sidebar
TITLE_DARK = "#142433"

BAR_DEFAULT = "#E9F3FF"
BAR_GOOD    = "#33FFAC"

# Catálogos ligeros (para creación de puestos)
DEPARTMENTS = ["Tecnología", "Marketing", "Operaciones", "Finanzas", "RR.HH.", "Atención al cliente", "Ventas", "Salud"]
EMP_TYPES = ["Tiempo completo", "Medio tiempo", "Prácticas", "Temporal", "Consultoría"]
SENIORITIES = ["Junior", "Semi Senior", "Senior", "Lead", "Manager", "Director"]
WORK_MODELS = ["Presencial", "Híbrido", "Remoto"]
SHIFTS = ["Diurno", "Nocturno", "Rotativo"]
PRIORITIES = ["Alta", "Media", "Baja"]
CURRENCIES = ["USD", "PEN", "EUR", "CLP", "MXN", "COP", "ARS"]

# Portales simulados (integración demo)
JOB_BOARDS = ["laborum.pe", "Computrabajo", "Bumeran", "Indeed", "LinkedIn Jobs"]

# Instrucción estilo “asistente” para la Ficha de Evaluación
EVAL_INSTRUCTION = (
  "Debes analizar los CVs de postulantes y calificarlos de 0% a 100% según el nivel de coincidencia con el JD. "
  "Incluye un análisis breve que explique por qué califica o no el postulante, destacando habilidades must-have, "
  "nice-to-have, brechas y hallazgos relevantes."
)

# ===== Avatares por defecto para agentes (ROBOT/BOT por rol; simulación) =====
AGENT_DEFAULT_IMAGES = {
  "Headhunter": "https://images.unsplash.com/photo-1581090464777-f3220bbe1b8b?q=80&w=512&auto=format&fit=crop",        # robot recruiter
  "Coordinador RR.HH.": "https://images.unsplash.com/photo-1542751371-adc38448a05e?q=80&w=512&auto=format&fit=crop",   # robot dashboard
  "Admin RR.HH.": "https://images.unsplash.com/photo-1526378722484-bd91ca387e72?q=80&w=512&auto=format&fit=crop",      # robot assistant
}
# Modelos LLM — SOLO PARA SIMULAR (no se consumen)
LLM_MODELS = [
  "gpt-4o-mini", "gpt-4.1", "gpt-4o",
  "claude-3.5-sonnet", "claude-3-haiku",
  "gemini-1.5-pro", "mixtral-8x7b", "llama-3.1-70b"
]

# =========================================================
# PRESETS DE PUESTOS: JD + KEYWORDS + POOL DE SKILLS PARA GENERAR CVS
# =========================================================
ROLE_PRESETS = {
  "Enfermera/o Asistencial": {
    "jd": (
      "Brindar atención de enfermería segura y de calidad a pacientes hospitalizados y ambulatorios, "
      "cumpliendo protocolos clínicos y normas de bioseguridad. Realizar valoración inicial y seguimiento "
      "(signos vitales, dolor, riesgo de caídas/IAAS), administrar medicamentos y terapias según prescripción, "
      "ejecutar procedimientos (curaciones, instalación de vía periférica, toma de muestras), y registrar en HIS / SAP IS-H. "
      "Educar al paciente y familia sobre cuidados y alta segura. Participar en rondas clínicas, auditorías, y acciones "
      "para la seguridad del paciente. Mantener vigentes certificaciones BLS/ACLS."
    ),
    "keywords": "HIS, SAP IS-H, BLS, ACLS, IAAS, educación al paciente, seguridad del paciente, protocolos, triage, signos vitales, curaciones, vía periférica, administración de medicamentos, registro clínico",
    "must": ["HIS","BLS","ACLS","IAAS","Seguridad del paciente"],
    "nice": ["SAP IS-H","Educación al paciente","Protocolos"],
    "synth_skills": ["HIS","BLS","ACLS","IAAS","Educación al paciente","Seguridad del paciente","Protocolos","Excel"]
  },
  "Tecnólogo/a Médico": {
    "jd": (
      "Realizar procedimientos de apoyo al diagnóstico (laboratorio, imágenes o terapia física, según especialidad), "
      "asegurando la calidad técnica y seguridad del paciente. Gestionar muestras/equipos, registrar resultados en HIS, "
      "cumplir normas IAAS y bioseguridad. Coordinar con médicos y enfermería."
    ),
    "keywords": "HIS, laboratorio, radiología, terapia física, calibración de equipos, bioseguridad, IAAS, reporte de resultados, control de calidad",
    "must": ["HIS","IAAS","Bioseguridad"],
    "nice": ["Control de calidad","Gestión de equipos"],
    "synth_skills": ["HIS","IAAS","Bioseguridad","Control de calidad","Gestión de equipos","Excel"]
  },
  "Recepcionista de Admisión": {
    "jd": (
      "Brindar atención presencial y telefónica a pacientes, gestionar admisiones/citas, facturación y caja básica. "
      "Registrar en HIS/ERP, verificar coberturas, resolver dudas y escalar incidencias. Mantener altos estándares "
      "de servicio y confidencialidad."
    ),
    "keywords": "atención al cliente, admisión, call center, HIS, ERP, facturación, caja, manejo de objeciones, protocolo de atención",
    "must": ["Atención al cliente","HIS"],
    "nice": ["ERP","Facturación","Caja"],
    "synth_skills": ["Atención al cliente","HIS","ERP","Facturación","Caja","Protocolos"]
  },
  "Médico/a General": {
    "jd": (
      "Atender consulta externa y emergencia, realizar historia clínica, diagnósticos y prescripción basada en guías. "
      "Coordinar interconsultas, registrar en HIS / SAP IS-H, promover educación al paciente y seguridad clínica. "
      "Participar en comités y actividades IAAS."
    ),
    "keywords": "HIS, SAP IS-H, anamnesis, diagnóstico, prescripción, protocolos, IAAS, seguridad del paciente, guardias",
    "must": ["HIS","Protocolos","Seguridad del paciente"],
    "nice": ["SAP IS-H","IAAS"],
    "synth_skills": ["HIS","Protocolos","Seguridad del paciente","IAAS","SAP IS-H","Educación al paciente"]
  },
  "Químico/a Farmacéutico/a": {
    "jd": (
      "Gestionar farmacia hospitalaria, dispensación segura, validación de prescripciones, control de stock y "
      "farmacovigilancia. Registrar en HIS/ERP, asegurar cumplimiento de BPM y normativas."
    ),
    "keywords": "dispensación, HIS, ERP, farmacovigilancia, BPM, control de stock, validación de recetas, protocolos",
    "must": ["HIS","ERP","BPM"],
    "nice": ["Farmacovigilancia","Control de stock"],
    "synth_skills": ["HIS","ERP","BPM","Farmacovigilancia","Control de stock","Protocolos"]
  },
  # ——— Roles generales (no clínicos) ———
  "Asistente Administrativo": {
    "jd": (
      "Brindar soporte administrativo: gestión documental, agenda, compras menores, logística de reuniones y "
      "reportes en Excel. Manejo de correo, redacción, atención a proveedores y archivo. Apoyo en facturación y caja chica."
    ),
    "keywords": "Excel, Word, PowerPoint, gestión documental, atención a proveedores, compras, logística, caja chica, facturación, redacción",
    "must": ["Excel","Gestión documental","Redacción"],
    "nice": ["Facturación","Caja"],
    "synth_skills": ["Excel","Word","PowerPoint","Gestión documental","Redacción","Facturación","Caja","Atención al cliente"]
  },
  "Ingeniero/a de Proyectos": {
    "jd": (
      "Planificar, ejecutar y controlar proyectos de ingeniería. Elaborar cronogramas, presupuestos, especificaciones y "
      "gestión de riesgos. Seguimiento de avances, control de cambios y reportes a stakeholders. Manejo de MS Project, "
      "AutoCAD/BIM y metodologías PMBOK/Agile."
    ),
    "keywords": "MS Project, AutoCAD, BIM, presupuestos, cronogramas, control de cambios, riesgos, PMBOK, Agile, KPI, licitaciones",
    "must": ["MS Project","AutoCAD","Presupuestos"],
    "nice": ["BIM","PMBOK","Agile"],
    "synth_skills": ["MS Project","AutoCAD","BIM","Presupuestos","Cronogramas","Riesgos","PMBOK","Agile","Excel","Power BI"]
  },
  "Business Analytics": {
    "jd": (
      "Recolectar, transformar y analizar datos para generar insights accionables. Modelar KPIs, construir dashboards en "
      "Power BI/Tableau, SQL intermedio-avanzado, storytelling con datos y documentación. Trabajar con stakeholders "
      "de negocio para priorizar hipótesis y experimientos."
    ),
    "keywords": "SQL, Power BI, Tableau, ETL, KPI, storytelling, Excel avanzado, Python, A/B testing, métricas de negocio",
    "must": ["SQL","Power BI"],
    "nice": ["Tableau","Python","ETL"],
    "synth_skills": ["SQL","Power BI","Tableau","Excel","ETL","KPIs","Storytelling","Python","A/B testing"]
  },
  "Diseñador/a UX": {
    "jd": (
      "Liderar procesos de research, definición de flujos, wireframes y prototipos de alta fidelidad. "
      "Validar con usuarios, handoff a desarrollo y medición post-lanzamiento. Dominio de Figma, heurísticas de usabilidad "
      "y accesibilidad. Experiencia en design systems."
    ),
    "keywords": "Figma, UX research, prototipado, wireframes, heurísticas, accesibilidad, design system, usabilidad, tests con usuarios",
    "must": ["Figma","UX Research","Prototipado"],
    "nice": ["Heurísticas","Accesibilidad","Design System"],
    "synth_skills": ["Figma","UX Research","Prototipado","Wireframes","Accesibilidad","Heurísticas","Design System","Analytics"]
  },
}

# =========================================================
# CSS — (botones a la IZQUIERDA + branding + mejoras agentes)
# =========================================================
CSS = f"""
:root {{
  --green: {PRIMARY};
  --sb-bg: {SIDEBAR_BG};
  --sb-tx: {SIDEBAR_TX};
  --body: {BODY_BG};
  --sb-card: {CARD_BG};
}}

/* Fondo app */
html, body, [data-testid="stAppViewContainer"] {{
  background: var(--body) !important;
}}
.block-container {{
  background: transparent !important;
  padding-top: 1.25rem !important;
}}

/* Sidebar base */
[data-testid="stSidebar"] {{
  background: var(--sb-bg) !important;
  color: var(--sb-tx) !important;
}}
[data-testid="stSidebar"] * {{
  color: var(--sb-tx) !important;
}}

/* Branding */
.sidebar-brand {{
  display:flex; flex-direction:column;
  align-items:center; justify-content:center;
  padding: 0 0 2px;
  margin-top: -10px;
  position: relative;
  top: -2px;
  text-align:center;
}}
.sidebar-brand .brand-title {{
  color: var(--green) !important;
  font-weight: 800 !important;
  font-size: 44px !important;
  line-height: 1.05 !important;
}}
.sidebar-brand .brand-sub {{
  margin-top: 2px !important;
  color: var(--green) !important;
  font-size: 11.5px !important;
  opacity: .95 !important;
}}

/* Títulos de sección del sidebar (verde) */
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3,
[data-testid="stSidebar"] h4,
[data-testid="stSidebar"] h5,
[data-testid="stSidebar"] h6 {{
  color: var(--green) !important;
  letter-spacing: .5px;
  margin: 12px 10px 6px !important;
  line-height: 1.05 !important;
}}

/* Botones del sidebar */
[data-testid="stSidebar"] .stButton > button {{
  width: 100% !important;
  display: flex !important;
  justify-content: flex-start !important;
  align-items: center !important;
  text-align: left !important;
  gap: 8px !important;
  background: var(--sb-card) !important;
  border: 1px solid var(--sb-bg) !important;
  color: #ffffff !important;
  border-radius: 12px !important;
  padding: 9px 12px !important;
  margin: 6px 8px !important;
  font-weight: 600 !important;
}}
[data-testid="stSidebar"] .stButton > button * {{ text-align: left !important; }}

/* CUERPO: Botones a la izquierda */
.block-container .stButton > button {{
  width: auto !important;
  display: flex !important;
  justify-content: flex-start !important;
  align-items: center !important;
  text-align: left !important;
  background: var(--green) !important;
  color: #082017 !important;
  border-radius: 10px !important;
  border: none !important;
  padding: .50rem .90rem !important;
  font-weight: 700 !important;
}}
.block-container .stButton > button:hover {{ filter: brightness(.96); }}

/* Títulos del cuerpo */
h1, h2, h3 {{ color: {TITLE_DARK}; }}
h1 strong, h2 strong, h3 strong {{ color: var(--green); }}

/* Inputs claros */
.block-container [data-testid="stSelectbox"] > div > div,
.block-container [data-baseweb="select"],
.block-container [data-testid="stTextInput"] input,
.block-container [data-testid="stTextArea"] textarea {{
  background: #F1F7FD !important;
  color: {TITLE_DARK} !important;
  border: 1.5px solid #E3EDF6 !important;
  border-radius: 10px !important;
}}

/* Tablas */
.block-container table {{
  background: #fff !important;
  border: 1px solid #E3EDF6 !important;
  border-radius: 8px !important;
}}
.block-container thead th {{
  background: #F1F7FD !important;
  color: {TITLE_DARK} !important;
}}

/* Tarjeta */
.k-card {{
  background:#fff;border:1px solid #E3EDF6;border-radius:12px;padding:14px;
}}
.badge {{
  display:inline-flex;align-items:center;gap:6px;
  background:#F1F7FD;border:1px solid #E3EDF6;border-radius:24px;
  padding:4px 10px;font-size:12px;color:#1B2A3C;
}}

/* ====== MEJORAS para cards de agentes ====== */
.agent-card .stButton > button {{
  background: var(--body) !important;        /* mismo color panel derecho */
  color: {TITLE_DARK} !important;
  border: 1px solid #E3EDF6 !important;
  border-radius: 10px !important;
  font-weight: 700 !important;
  padding: 6px 10px !important;
}}
.agent-detail {{
  background:#fff;border:2px solid #E3EDF6;border-radius:16px;padding:16px;
  box-shadow: 0 6px 18px rgba(14,25,43,.08);
}}
"""

CSS += """
.match-chip {
  display:inline-flex; align-items:center; gap:8px;
  border-radius:999px; padding:6px 12px; font-weight:700; font-size:12.5px;
  border:1px solid #E3EDF6; background:#F1F7FD; color:#1B2A3C;
}
.match-dot { width:10px; height:10px; border-radius:999px; display:inline-block; }
.match-strong { background: #33FFAC; }
.match-good   { background: #A7F3D0; }
.match-ok     { background: #E9F3FF; }

.skill-pill {
  display:inline-flex; align-items:center; gap:6px;
  margin: 4px 6px 0 0; padding:6px 10px; border-radius:999px;
  border:1px solid #E3EDF6; background:#FFFFFF; color:#1B2A3C; font-size:12px;
}
.skill-pill.checked { background:#F1F7FD; border-color:#E3EDF6; }
"""

# =========================================================
st.set_page_config(page_title="SelektIA", page_icon="🧠", layout="wide")
st.markdown(f"<style>{CSS}</style>", unsafe_allow_html=True)

# =========================================================
# PERSISTENCIA (JSON local) — Agentes
# =========================================================
DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)
AGENTS_FILE = DATA_DIR / "agents.json"

def load_agents() -> list:
  if AGENTS_FILE.exists():
    try:
      return json.loads(AGENTS_FILE.read_text(encoding="utf-8"))
    except Exception:
      return []
  return []

def save_agents(agents: list):
  try:
    AGENTS_FILE.write_text(json.dumps(agents, ensure_ascii=False, indent=2), encoding="utf-8")
  except Exception as e:
    st.error(f"No se pudo guardar agents.json: {e}")

# =========================================================
# ESTADO
# =========================================================
ss = st.session_state
if "section" not in ss: ss.section = "def_carga"
if "tasks" not in ss: ss.tasks = []
if "candidates" not in ss: ss.candidates = []
if "offers" not in ss: ss.offers = {}
if "agents_loaded" not in ss:
  ss.agents = load_agents()
  ss.agents_loaded = True

# Carga de puestos base (resumida aquí; igual al bloque previo que ya te funcionaba)
if "positions" not in ss:
  ss.positions = pd.DataFrame([
      {"ID":"10,645,194","Puesto":"Desarrollador/a Backend (Python)","Días Abierto":3,
       "Leads":1800,"Nuevos":115,"Recruiter Screen":35,"HM Screen":7,
       "Entrevista Telefónica":14,"Entrevista Presencial":15,"Ubicación":"Lima, Perú",
       "Hiring Manager":"Rivers Brykson","Estado":"Abierto",
       "Experiencia Min":3,"MustHave":"Python, APIs REST, SQL","NiceToHave":"AWS, Docker","JD":"Construcción de APIs y servicios backend."},
      {"ID":"10,376,415","Puesto":"Asistente Administrativo","Días Abierto":7,
       "Leads":450,"Nuevos":25,"Recruiter Screen":8,"HM Screen":5,
       "Entrevista Telefónica":3,"Entrevista Presencial":2,"Ubicación":"Lima, Perú",
       "Hiring Manager":"Lucía Vega","Estado":"Abierto",
       "Experiencia Min":1,"MustHave":"Excel, Gestión documental, Redacción","NiceToHave":"Facturación, Caja","JD":ROLE_PRESETS["Asistente Administrativo"]["jd"]},
      {"ID":"10,376,646","Puesto":"Business Analytics","Días Abierto":14,
       "Leads":1300,"Nuevos":40,"Recruiter Screen":10,"HM Screen":6,
       "Entrevista Telefónica":4,"Entrevista Presencial":3,"Ubicación":"Santiago, Chile",
       "Hiring Manager":"Angela Cruz","Estado":"Abierto",
       "Experiencia Min":2,"MustHave":"SQL, Power BI","NiceToHave":"Tableau, Python","JD":ROLE_PRESETS["Business Analytics"]["jd"]},
      {"ID":"10,376,777","Puesto":"Diseñador/a UX","Días Abierto":10,
       "Leads":900,"Nuevos":22,"Recruiter Screen":7,"HM Screen":4,
       "Entrevista Telefónica":3,"Entrevista Presencial":2,"Ubicación":"Bogotá, Colombia",
       "Hiring Manager":"Rivers Brykson","Estado":"Abierto",
       "Experiencia Min":2,"MustHave":"Figma, UX Research, Prototipado","NiceToHave":"Heurísticas, Accesibilidad, Design System","JD":ROLE_PRESETS["Diseñador/a UX"]["jd"]},
      {"ID":"10,376,888","Puesto":"Ingeniero/a de Proyectos","Días Abierto":20,
       "Leads":1100,"Nuevos":18,"Recruiter Screen":6,"HM Screen":5,
       "Entrevista Telefónica":4,"Entrevista Presencial":3,"Ubicación":"Ciudad de México, MX",
       "Hiring Manager":"Rivers Brykson","Estado":"Abierto",
       "Experiencia Min":3,"MustHave":"MS Project, AutoCAD, Presupuestos","NiceToHave":"BIM, PMBOK, Agile","JD":ROLE_PRESETS["Ingeniero/a de Proyectos"]["jd"]},
  ])

# =========================================================
# TAXONOMÍA DE SKILLS (demo sin IA)
# =========================================================
SKILL_SYNONYMS = {
  "HIS": ["his", "hospital information system"],
  "SAP IS-H": ["sap is-h", "sap is h", "sap hospital"],
  "BLS": ["bls", "basic life support"],
  "ACLS": ["acls", "advanced cardiac life support"],
  "IAAS": ["iaas", "infecciones asociadas a la atención", "infecciones nosocomiales"],
  "Educación al paciente": ["educación al paciente", "patient education"],
  "Seguridad del paciente": ["seguridad del paciente", "patient safety"],
  "Protocolos": ["protocolos", "protocol"],
  "Gestión documental": ["gestión documental", "archivo", "document control"],
  "Redacción": ["redacción", "writing", "composición de documentos"],
  "Atención al cliente": ["atención al cliente", "customer service"],
  "Facturación": ["facturación", "billing"],
  "Caja": ["caja", "cash handling"],
  "Python": ["python"],
  "APIs REST": ["api rest", "apis rest", "rest api", "restful"],
  "SQL": ["sql", "postgres", "mysql", "t-sql"],
  "Docker": ["docker"],
  "AWS": ["aws", "amazon web services"],
  "Power BI": ["power bi"],
  "Excel": ["excel", "xlsx"],
  "Tableau": ["tableau"],
  "ETL": ["etl", "extract transform load"],
  "KPIs": ["kpi", "kpis", "indicadores"],
  "MS Project": ["ms project", "microsoft project"],
  "AutoCAD": ["autocad"],
  "BIM": ["bim", "revit"],
  "Presupuestos": ["presupuesto", "presupuestos", "costeo"],
  "Cronogramas": ["cronograma", "cronogramas", "planning"],
  "Riesgos": ["riesgos", "risk management"],
  "PMBOK": ["pmbok"],
  "Agile": ["agile", "scrum", "kanban"],
  "Figma": ["figma"],
  "UX Research": ["ux research", "investigación de usuarios"],
  "Prototipado": ["prototipado", "prototype", "prototipos"],
  "Wireframes": ["wireframes", "wireframing"],
  "Accesibilidad": ["accesibilidad", "accessibility", "wcag"],
  "Heurísticas": ["heurísticas", "heuristic"],
  "Design System": ["design system"],
  "ERP": ["erp", "sap", "oracle ebs"],
  "Bioseguridad": ["bioseguridad"],
}

# =========================================================
# UTILS
# =========================================================
def _normalize(t: str) -> str:
  return re.sub(r"\s+", " ", (t or "")).strip().lower()

def infer_skills(text: str) -> set:
  t = _normalize(text)
  found = set()
  for canonical, syns in SKILL_SYNONYMS.items():
    for s in syns:
      if s in t:
        found.add(canonical)
        break
  return found

def score_fit_by_skills(jd_text: str, must_list: list[str], nice_list: list[str], cv_text: str):
  jd_skills = infer_skills(jd_text)
  must = set([m.strip() for m in must_list if m.strip()]) or jd_skills
  nice = set([n.strip() for n in nice_list if n.strip()]) - must

  cv_sk = infer_skills(cv_text)

  matched_must = sorted(list(must & cv_sk))
  matched_nice = sorted(list(nice & cv_sk))
  gaps_must = sorted(list(must - cv_sk))
  gaps_nice = sorted(list(nice - cv_sk))
  extras = sorted(list((cv_sk & (jd_skills | must | nice)) - set(matched_must) - set(matched_nice)))

  cov_must = len(matched_must)/len(must) if must else 0
  cov_nice = len(matched_nice)/len(nice) if nice else 0
  extra_factor = min(len(extras), 5)/5

  score = 100 * (0.65*cov_must + 0.20*cov_nice + 0.15*extra_factor)
  score = int(round(score))

  explain = {
    "matched_must": matched_must, "matched_nice": matched_nice,
    "gaps_must": gaps_must, "gaps_nice": gaps_nice, "extras": extras,
    "must_total": len(must), "nice_total": len(nice)
  }
  return score, explain

def build_analysis_text(name: str, explain: dict) -> str:
  ok_m = ", ".join(explain["matched_must"]) if explain["matched_must"] else "sin must-have claros"
  ok_n = ", ".join(explain["matched_nice"]) if explain["matched_nice"] else "—"
  gaps = ", ".join(explain["gaps_must"][:3]) if explain["gaps_must"] else "sin brechas críticas"
  extras = ", ".join(explain["extras"][:3]) if explain["extras"] else "—"
  return (
    f"{name} evidencia buen encaje en must-have ({ok_m}). "
    f"En nice-to-have destaca: {ok_n}. "
    f"Brechas principales: {gaps}. "
    f"Extras relevantes detectados: {extras}."
  )

def pdf_viewer_embed(file_bytes: bytes, height=520):
  try:
    b64 = base64.b64encode(file_bytes).decode("utf-8")
    html = f'''
      <div class="pdf-frame" style="border:0; width:100%;">
        <embed src="data:application/pdf;base64,{b64}" type="application/pdf" width="100%" height="{height}px"/>
      </div>'''
    st.components.v1.html(html, height=height)
  except Exception as e:
    st.error(f"No se pudo previsualizar el PDF. {e}")
    st.download_button("Descargar PDF", data=file_bytes, file_name="cv.pdf", mime="application/pdf")

def extract_text_from_file(uploaded_file) -> str:
  try:
    suffix = Path(uploaded_file.name).suffix.lower()
    if suffix == ".pdf":
      pdf_reader = PdfReader(io.BytesIO(uploaded_file.read()))
      text = ""
      for page in pdf_reader.pages:
        text += page.extract_text() or ""
      return text
    else:
      return uploaded_file.read().decode("utf-8", errors="ignore")
  except Exception as e:
    st.error(f"Error al leer '{uploaded_file.name}': {e}")
    return ""

def _max_years(text_low: str) -> int:
  years = 0
  for m in re.finditer(r'(\d{1,2})\s*(años|year|years)', text_low):
    try:
      years = max(years, int(m.group(1)))
    except Exception:
      pass
  if years == 0 and ("años" in text_low or "experiencia" in text_low or "years" in text_low):
    years = 5
  return years

def extract_meta(cv_text: str) -> dict:
  text_low = cv_text.lower()
  universidad = ""
  uni_match = re.search(r'(universidad|university)\s+([^\n,;]+)', text_low)
  if uni_match:
    universidad = (uni_match.group(0) or "").strip().title()
  anios_exp = _max_years(text_low)
  titulo = ""
  for key in ["licenciado", "bachiller", "ingeniero", "enfermera", "enfermero", "qu\u00edmico", "m\u00e9dico", "tecn\u00f3logo"]:
    if key in text_low:
      titulo = key.title()
      break
  ubicacion = ""
  ciudades = ["lima","santiago","bogot\u00e1","ciudad de m\u00e9xico","mexico city","quito","buenos aires","montevideo","la paz"]
  for c in ciudades:
    if c in text_low:
      ubicacion = c.title()
      break
  return {
    "universidad": universidad or "—",
    "anios_exp": anios_exp,
    "titulo": titulo or "—",
    "ubicacion": ubicacion or "—",
    "ultima_actualizacion": datetime.today().date().isoformat()
  }

def simple_score(cv_text: str, jd: str, keywords: str) -> tuple[int, str]:
  base = 0
  reasons = []
  text_low = cv_text.lower()
  jd_low = jd.lower()
  hits = 0
  kws = [k.strip().lower() for k in keywords.split(",") if k.strip()]
  for k in kws:
    if k and k in text_low:
      hits += 1
  if kws:
    pct_k = hits/len(kws)
    base += int(pct_k*70)
    found_list = [k for k in kws if k in text_low]
    reasons.append(f"{hits}/{len(kws)} keywords encontradas — Coincidencias: {', '.join(found_list)[:120]}")
  jd_terms = [t for t in set(jd_low.split()) if len(t) > 3]
  match_terms = sum(1 for t in jd_terms if t in text_low)
  if jd_terms:
    pct_jd = match_terms/len(jd_terms)
    base += int(pct_jd*30)
    reasons.append("Coincidencias con el JD (aprox.)")
  base = max(0, min(100, base))
  return base, " — ".join(reasons)

def _offers_to_df(offers_dict: dict) -> pd.DataFrame:
  if not offers_dict:
    return pd.DataFrame(columns=["Candidato","Puesto","Ubicación","Modalidad","Salario","Estado","Inicio","Caduca"])
  rows = []
  for cand, o in offers_dict.items():
    rows.append({
      "Candidato": cand,
      "Puesto": o.get("puesto",""),
      "Ubicación": o.get("ubicacion",""),
      "Modalidad": o.get("modalidad",""),
      "Salario": o.get("salario",""),
      "Estado": o.get("estado","Borrador"),
      "Inicio": o.get("fecha_inicio",""),
      "Caduca": o.get("caducidad",""),
    })
  return pd.DataFrame(rows)

def _simulate_publish(urls_text: str) -> tuple[str, str, str]:
  urls = [u.strip() for u in (urls_text or "").splitlines() if u.strip()] \
         or [u.strip() for u in (urls_text or "").split(",") if u.strip()]
  if urls:
    return ("Publicado", date.today().isoformat(), ", ".join(urls))
  return ("Listo para publicar", "", "")

def _skills_from_csv(text: str) -> list[str]:
  return [s.strip() for s in (text or "").split(",") if s.strip()]

def _match_level(row: dict | pd.Series) -> tuple[str, str]:
  try:
    leads = int(row.get("Leads", 0))
    nuevos = int(row.get("Nuevos", 0))
    expmin = int(row.get("Experiencia Min", 0) or 0)
  except Exception:
    leads, nuevos, expmin = 0, 0, 0
  if (leads >= 3000) or (nuevos >= 20) or (expmin >= 5):
    return ("Strong Match", "match-strong")
  if (leads >= 1200) or (nuevos >= 8) or (expmin >= 3):
    return ("Good Match", "match-good")
  return ("Ok Match", "match-ok")

def _dummy_name(board: str, idx: int) -> str:
  base = {
    "laborum.pe": "LAB",
    "Computrabajo": "CTJ",
    "Bumeran": "BUM",
    "Indeed": "IND",
    "LinkedIn Jobs": "LIJ",
  }.get(board, "EXT")
  return f"{base}_Candidato_{idx:02d}.pdf"

def _dummy_cv_text(query: str, location: str) -> str:
  skills = ["HIS", "SAP IS-H", "BLS", "ACLS", "IAAS", "educación al paciente", "seguridad del paciente", "protocolos"]
  core = ", ".join(skills[:6])
  return (
    f"Resumen profesional — {query} en {location}. Universidad Nacional Mayor de San Marcos. "
    f"Experiencia: 5 años en hospitales y clínicas. Certificaciones: BLS, ACLS. "
    f"Habilidades: {core}. Logros: implementación de protocolos IAAS."
  )

def _make_candidate_from_board(board: str, idx: int, jd_text: str, keywords: str, query: str, location: str) -> dict:
  text = _dummy_cv_text(query or "Profesional", location or "Lima")
  score, reasons = simple_score(text, jd_text, keywords)
  meta = extract_meta(text)
  return {
    "Name": _dummy_name(board, idx),
    "Score": score,
    "Reasons": reasons,
    "_bytes": text.encode("utf-8"),
    "_is_pdf": False,
    "_text": text,
    "meta": meta
  }

FIRST_NAMES = ["Ana","Bruno","Carla","Daniel","Elena","Fernando","Gabriela","Hugo","Irene","Javier","Karina","Luis","María","Nicolás","Olga","Pablo","Rocío","Sofía","Tomás","Valeria"]
LAST_NAMES  = ["Rojas","García","Quispe","Torres","Muñoz","Pérez","Salas","Vargas","Huamán","Ramírez","Castro","Mendoza","Flores","López","Fernández","Cortez","Ramos","Díaz","Campos","Navarro"]

def _synth_cv_text(role: str, pool_skills: list[str], city: str, years: int) -> str:
  k = min(len(pool_skills), max(4, min(8, len(pool_skills))))
  picked = random.sample(pool_skills, k=random.randint(4, k))
  txt = (
    f"Resumen profesional — {role} en {city}. "
    f"Experiencia: {years} años. Manejo de {', '.join(picked)}. "
    f"Universidad Nacional Mayor de San Marcos. Participación en proyectos de mejora continua y protocolos. "
    f"Responsabilidades: soporte, coordinación y documentación."
  )
  return txt

def generate_sample_cvs_for_role(role: str, jd_text: str, n: int = 25) -> list[dict]:
  preset = ROLE_PRESETS.get(role, {})
  pool = preset.get("synth_skills") or list(infer_skills(jd_text) or {"Excel","Gestión documental"})
  cities = ["Lima, Perú","Santiago, Chile","Bogotá, Colombia","Quito, Ecuador","Ciudad de México, MX"]
  out = []
  for i in range(n):
    name = f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"
    years = random.choice([0,1,1,2,3,4,5,6,7,8,10])
    city = random.choice(cities)
    text = _synth_cv_text(role, pool, city, years)
    meta = extract_meta(text)
    meta["anios_exp"] = years
    file_name = f"CV_{role.replace('/','-')}_{i+1:02d}_{name.replace(' ','_')}.txt"
    out.append({
      "Name": file_name,
      "Score": 0,
      "Reasons": "",
      "_bytes": text.encode("utf-8"),
      "_is_pdf": False,
      "_text": text,
      "meta": meta
    })
  return out

def _file_to_data_uri(uploaded_image) -> str | None:
  try:
    mime = uploaded_image.type or "image/png"
    b = uploaded_image.read()
    b64 = base64.b64encode(b).decode("utf-8")
    return f"data:{mime};base64,{b64}"
  except Exception:
    return None

def _safe_index(seq, val, default=0):
  try:
    return seq.index(val)
  except Exception:
    return default

# =========================================================
# SIDEBAR (branding + navegación)
# =========================================================
with st.sidebar:
  st.markdown(
    """
    <div class="sidebar-brand">
      <div class="brand-title">SelektIA</div>
      <div class="brand-sub">Powered by Wayki Consulting</div>
    </div>
    """, unsafe_allow_html=True
  )

  st.markdown("#### DASHBOARD")
  if st.button("Analytics", key="sb_analytics"):
    ss.section = "analytics"

  st.markdown("#### ASISTENTE IA")
  for txt, sec in [("Flujos","flows"),("Agentes","agents"),("Tareas de Agente","agent_tasks")]:
    if st.button(txt, key=f"sb_{sec}"):
      ss.section = sec

  st.markdown("#### PROCESO DE SELECCIÓN")
  pages = [
    ("Definición & Carga","def_carga"),
    ("Puestos","puestos"),
    ("Evaluación de CVs","eval"),
    ("Pipeline de Candidatos","pipeline"),
    ("Entrevista (Gerencia)","interview"),
    ("Tareas del Headhunter","hh_tasks"),
    ("Oferta","offer"),
    ("Onboarding","onboarding"),
  ]
  for txt, sec in pages:
    if st.button(txt, key=f"sb_{sec}"):
      ss.section = sec

  st.markdown("#### ACCIONES")
  if st.button("Crear tarea", key="sb_task"):
    ss.section = "create_task"

# =========================================================
# PÁGINAS
# =========================================================
def page_def_carga():
  st.header("Definición & Carga")

  roles = list(ROLE_PRESETS.keys())
  role = st.selectbox("Puesto", roles, index=_safe_index(roles, "Enfermera/o Asistencial", 0))
  preset = ROLE_PRESETS.get(role, {})

  jd_text = st.text_area("Descripción / JD", height=180, value=preset.get("jd",""))
  kw_text = st.text_area("Palabras clave (coma separada)", height=100, value=preset.get("keywords",""))
  ss["last_role"] = role
  ss["last_jd_text"] = jd_text
  ss["last_kw_text"] = kw_text

  files = st.file_uploader("Subir CVs (PDF o TXT)", type=["pdf","txt"], accept_multiple_files=True)
  if files:
    if st.button("Procesar CVs cargados"):
      ss.candidates = []
      for f in files:
        f_bytes = f.read(); f.seek(0)
        text = extract_text_from_file(f)
        score, reasons = simple_score(text, jd_text, kw_text)
        meta = extract_meta(text)
        ss.candidates.append({
          "Name": f.name, "Score": score, "Reasons": reasons,
          "_bytes": f_bytes, "_is_pdf": Path(f.name).suffix.lower()==".pdf",
          "_text": text, "meta": meta
        })
      st.success("CVs cargados y analizados.")

  with st.expander("🔌 Importar desde portales (demo)"):
    col1, col2, col3 = st.columns([1,1,1])
    with col1:
      sources = st.multiselect("Portales", options=JOB_BOARDS, default=["laborum.pe"])
      qty = st.number_input("Cantidad por portal", min_value=1, max_value=30, value=6, step=1)
    with col2:
      search_q = st.text_input("Búsqueda", value=role)
      location = st.text_input("Ubicación", value="Lima, Perú")
    with col3:
      _ = st.date_input("Publicado desde", value=date.today() - timedelta(days=15))
    st.caption("Nota: Integración simulada para demo (sin scraping real).")
    if st.button("Traer CVs (demo)"):
      imported = []
      for board in sources:
        for i in range(1, int(qty)+1):
          imported.append(_make_candidate_from_board(board, i, jd_text, kw_text, search_q, location))
      ss.candidates = (ss.candidates or []) + imported
      st.success(f"Importados {len(imported)} CVs simulados desde: {', '.join(sources)}.")

  with st.expander("🧪 Generar CVs de muestra para este puesto (demo)"):
    n = st.slider("Cantidad", min_value=10, max_value=40, value=25, step=5)
    st.caption("Crea CVs sintéticos con skills acordes al puesto seleccionado.")
    if st.button("Generar CVs de muestra"):
      ss.candidates = generate_sample_cvs_for_role(role, jd_text, n=n)
      st.success(f"Se generaron {n} CVs de muestra para {role}.")

def page_puestos():
  st.header("Puestos")
  left, center, right = st.columns([0.95, 1.2, 0.9])

  with left:
    st.markdown("**Puestos abiertos**")
    if ss.positions.empty:
      st.info("Aún no hay puestos creados.")
      selected_id = None
    else:
      df_list = ss.positions.copy()
      df_list = df_list.sort_values(["Estado", "Días Abierto", "Leads"], ascending=[True, True, False]).reset_index(drop=True)
      options = []; labels_for_radio = []
      for _, row in df_list.iterrows():
        label, css = _match_level(row)
        st.markdown(
          f"""
          <div style="border:1px solid #E3EDF6; border-radius:12px; padding:10px; margin-bottom:8px; background:#FFFFFF;">
            <div style="display:flex; justify-content:space-between; align-items:center;">
              <div>
                <div style="font-weight:800;color:{TITLE_DARK};">{row['Puesto']}</div>
                <div style="font-size:12px;opacity:.8">{row.get('Ubicación','')}</div>
              </div>
              <div class="match-chip">
                <span class="match-dot {css}"></span>{label}
              </div>
            </div>
            <div style="display:flex; gap:10px; margin-top:6px; flex-wrap:wrap; font-size:12px; opacity:.85">
              <span>Leads: <b>{row.get('Leads',0)}</b></span>
              <span>Nuevos: <b>{row.get('Nuevos',0)}</b></span>
              <span>Días abierto: <b>{row.get('Días Abierto',0)}</b></span>
            </div>
          </div>
          """,
          unsafe_allow_html=True
        )
        options.append(row["ID"])
        labels_for_radio.append(f"{row['Puesto']} — {row.get('Ubicación','')} · {label}")
      preselect = ss.get("selected_position_id", options[0] if options else None)
      selected_id = st.radio("Selecciona un puesto", options=options,
                             index=options.index(preselect) if (preselect in options) else 0,
                             format_func=lambda x: labels_for_radio[options.index(x)])
      ss["selected_position_id"] = selected_id

  selected_row = None
  if not ss.positions.empty and ss.get("selected_position_id"):
    try:
      selected_row = ss.positions[ss.positions["ID"] == ss["selected_position_id"]].iloc[0].to_dict()
    except Exception:
      selected_row = ss.positions.iloc[0].to_dict()

  with center:
    if not selected_row:
      st.caption("Selecciona un puesto para ver el detalle.")
    else:
      title = selected_row.get("Puesto", "—")
      ubic = selected_row.get("Ubicación", "—")
      st.markdown(f"<h2 style='margin:0;color:{TITLE_DARK}'>{title}</h2>", unsafe_allow_html=True)
      st.caption(ubic)
      cta, cta2 = st.columns([1,1])
      with cta:
        if st.button("Publicar ahora", key="pub_now"):
          estado_ap = selected_row.get("Estado Aprobación", "Pendiente")
          if (estado_ap == "Aprobado"):
            status, fpub, sites = _simulate_publish(selected_row.get("Publicaciones",""))
            ss.positions.loc[ss.positions["ID"] == selected_row["ID"], "Estado Publicación"] = status
            ss.positions.loc[ss.positions["ID"] == selected_row["ID"], "Fecha Publicación"] = fpub
            ss.positions.loc[ss.positions["ID"] == selected_row["ID"], "Publicado En"] = sites
            st.success("Puesto publicado (simulado).")
          else:
            st.info("Este puesto aún no está aprobado.")
      with cta2:
        st.button("Agregar al Job Cart", key="add_cart")
      st.markdown("---")
      st.subheader("Job Description")
      jd = (selected_row.get("JD", "") or "").strip() or "—"
      st.write(jd)

  with right:
    if selected_row:
      label, css = _match_level(selected_row)
      st.markdown('<div class="k-card">', unsafe_allow_html=True)
      st.markdown(
        f'<div class="match-chip" style="margin-bottom:8px;"><span class="match-dot {css}"></span>{label}</div>',
        unsafe_allow_html=True
      )
      exp_min = selected_row.get("Experiencia Min", 0) or 0
      if isinstance(exp_min, float): exp_min = int(exp_min)
      exp_txt = f"≥ {exp_min} años de experiencia" if exp_min else "Experiencia deseada: no especificada"
      st.markdown(f"- {exp_txt}")
      st.markdown("**Matching Skills**")
      must = _skills_from_csv(selected_row.get("MustHave",""))
      nice = _skills_from_csv(selected_row.get("NiceToHave",""))
      if not must and not nice:
        st.caption("Aún no has definido skills para este puesto.")
      else:
        row1 = "".join([f'<span class="skill-pill checked">✓ {s}</span>' for s in must[:12]])
        if row1: st.markdown(row1, unsafe_allow_html=True)
        if nice:
          st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
          st.caption("Deseables")
          row2 = "".join([f'<span class="skill-pill">{s}</span>' for s in nice[:12]])
          st.markdown(row2, unsafe_allow_html=True)
      st.markdown("</div>", unsafe_allow_html=True)

  st.markdown("")
  with st.expander("📋 Ver tabla completa (vista clásica)"):
    st.dataframe(
      ss.positions[
        ["Puesto","Días Abierto","Leads","Nuevos","Recruiter Screen",
         "HM Screen","Entrevista Telefónica","Entrevista Presencial","Ubicación",
         "Hiring Manager","Estado","ID"]
      ].sort_values(["Estado","Días Abierto","Leads"], ascending=[True,True,False]),
      use_container_width=True, height=320
    )

  # Crear puesto (igual que antes; lo dejo intacto por brevedad)
  with st.expander("➕ Crear nuevo puesto"):
    c1, c2 = st.columns(2)
    with c1:
      req_id = st.text_input("Requisition ID / Código interno")
      job_title = st.text_input("Puesto / Título del cargo")
      department = st.selectbox("Departamento", DEPARTMENTS, index=0)
      location = st.text_input("Ubicación (ciudad, país)", value="Lima, Perú")
      emp_type = st.selectbox("Tipo de empleo", EMP_TYPES, index=0)
      seniority = st.selectbox("Seniority", SENIORITIES, index=2)
      work_model = st.selectbox("Modalidad", WORK_MODELS, index=0)
      openings = st.number_input("Headcount (número de vacantes)", 1, 999, 1)
      hiring_manager = st.text_input("Hiring Manager", value="")
      recruiter = st.text_input("Recruiter", value="")
      reason = st.text_input("Razón de la vacante (reemplazo/crecimiento)", value="")
    with c2:
      currency = st.selectbox("Moneda", CURRENCIES, index=0)
      sal_min = st.number_input("Salario mínimo", 0.0, 1e9, 0.0, step=100.0)
      sal_max = st.number_input("Salario máximo", 0.0, 1e9, 0.0, step=100.0)
      shift = st.selectbox("Turno", SHIFTS, index=0)
      languages = st.text_input("Idiomas requeridos (coma separada)", value="Español")
      education = st.text_input("Educación requerida", value="Bachiller o titulado")
      years_exp = st.number_input("Años de experiencia (mínimo)", 0, 50, 2)
      priority = st.selectbox("Prioridad", PRIORITIES, index=0)
      target_date = st.date_input("Fecha objetivo de contratación", value=date.today()+timedelta(days=30))
      expiry_date = st.date_input("Fecha de expiración de publicación", value=date.today()+timedelta(days=45))
      approvers = st.text_input("Aprobadores", value="Gerencia, Legal, Finanzas")
    jd = st.text_area("Descripción / Responsabilidades (JD)", height=150)
    must = st.text_area("Must-have (skills/tecnologías clave, coma separada)", height=90, value="")
    nice = st.text_area("Nice-to-have (deseables, coma separada)", height=90, value="")
    benefits = st.text_area("Beneficios / Bonos", height=90, value="")
    screening = st.text_area("Preguntas de screening (una por línea)", height=120, value="")
    post_urls = st.text_area("URLs de publicación (una por línea o separadas por coma)", height=70, value="")
    st.markdown("---")
    st.subheader("Aprobación de requisición")
    require_approval = st.toggle("Requiere aprobación antes de publicar", value=True)
    approval_status = st.selectbox("Estado de aprobación", ["Pendiente","Aprobado","Rechazado"], index=0)
    approved_by = st.text_input("Aprobado por (si aplica)", value="")
    approval_date = st.date_input("Fecha de aprobación (si aplica)", value=date.today())
    approval_notes = st.text_area("Notas de aprobación", height=70, value="")
    save = st.button("Guardar puesto")
    if save:
      new_row = {
        "ID": req_id or f"AUT-{int(datetime.now().timestamp())}",
        "Puesto": job_title, "Días Abierto": 0, "Leads": 0, "Nuevos": 0,
        "Recruiter Screen": 0, "HM Screen": 0, "Entrevista Telefónica": 0, "Entrevista Presencial": 0,
        "Ubicación": location, "Hiring Manager": hiring_manager or recruiter, "Estado": "Abierto",
        "Departamento": department, "Tipo Empleo": emp_type, "Seniority": seniority, "Modalidad": work_model,
        "Vacantes": openings, "Recruiter": recruiter, "Razón": reason, "Moneda": currency,
        "Salario Min": sal_min, "Salario Max": sal_max, "Turno": shift, "Idiomas": languages, "Educación": education,
        "Experiencia Min": years_exp, "Prioridad": priority, "Fecha Objetivo": str(target_date),
        "Expira": str(expiry_date), "Aprobadores": approvers, "JD": jd, "MustHave": must, "NiceToHave": nice,
        "Beneficios": benefits, "Screening Qs": screening, "Publicaciones": post_urls,
        "Requiere Aprobación": require_approval, "Estado Aprobación": approval_status,
        "Aprobado Por": approved_by if approval_status == "Aprobado" else "",
        "Fecha Aprobación": str(approval_date) if approval_status == "Aprobado" else "",
        "Notas Aprobación": approval_notes, "Estado Publicación": "Borrador", "Fecha Publicación": "", "Publicado En": ""
      }
      should_publish = (not require_approval) or (approval_status == "Aprobado")
      if should_publish:
        pub_status, pub_date, pub_sites = _simulate_publish(post_urls)
        new_row["Estado Publicación"] = pub_status
        new_row["Fecha Publicación"] = pub_date
        new_row["Publicado En"] = pub_sites
        if pub_status == "Publicado":
          st.success(f"Puesto publicado automáticamente en: {pub_sites}")
        else:
          st.info("Aprobado, pero sin URLs de publicación. Quedó como 'Listo para publicar'.")
      else:
        new_row["Estado Publicación"] = "Pendiente de aprobación"
      ss.positions = pd.concat([pd.DataFrame([new_row]), ss.positions], ignore_index=True)
      st.success("Puesto creado.")

def page_eval():
  st.header("Resultados de evaluación")
  if not ss.candidates:
    st.info("Carga o genera CVs en **Definición & Carga**.")
    return

  jd_text = st.text_area("JD para matching por skills (opcional)", ss.get("last_jd_text",""), height=140)
  with st.expander("Configurar skills objetivo (opcional)"):
    preset = ROLE_PRESETS.get(ss.get("last_role",""), {})
    c1, c2 = st.columns(2)
    with c1:
      must_default = ", ".join(preset.get("must", []))
      must_default = st.text_area("Must-have (coma separada)", value=must_default)
    with c2:
      nice_default = ", ".join(preset.get("nice", []))
      nice_default = st.text_area("Nice-to-have (coma separada)", value=nice_default)
  must_list = [s.strip() for s in (must_default or "").split(",") if s.strip()]
  nice_list = [s.strip() for s in (nice_default or "").split(",") if s.strip()]

  enriched = []
  for cand in ss.candidates:
    cv_text = cand.get("_text") or (cand.get("_bytes") or b"").decode("utf-8","ignore")
    fit, explain = score_fit_by_skills(jd_text, must_list, nice_list, cv_text or "")
    enriched.append({
      "Name": cand["Name"], "Fit": fit,
      "Must (ok/total)": f"{len(explain['matched_must'])}/{explain['must_total']}",
      "Nice (ok/total)": f"{len(explain['matched_nice'])}/{explain['nice_total']}",
      "Extras": ", ".join(explain["extras"])[:60],
      "_exp": explain, "_is_pdf": cand["_is_pdf"], "_bytes": cand["_bytes"],
      "_text": cv_text or "", "meta": cand.get("meta", {})
    })

  df = pd.DataFrame(enriched).sort_values("Fit", ascending=False).reset_index(drop=True)

  st.subheader("Ranking por Fit de Skills")
  st.dataframe(df[["Name","Fit","Must (ok/total)","Nice (ok/total)","Extras"]],
               use_container_width=True, height=250)

  st.subheader("Detalle y explicación")
  selected = st.selectbox("Elige un candidato", df["Name"].tolist())
  row = df[df["Name"] == selected].iloc[0]
  exp = row["_exp"]

  c1, c2 = st.columns([1.1, 0.9])
  with c1:
    fig = px.bar(pd.DataFrame([{"Candidato": row["Name"], "Fit": row["Fit"]}]),
                 x="Candidato", y="Fit", title="Fit por skills")
    fig.update_traces(marker_color=BAR_GOOD if row["Fit"] >= 60 else BAR_DEFAULT,
                      hovertemplate="%{x}<br>Fit: %{y}%")
    fig.update_layout(plot_bgcolor="#FFFFFF", paper_bgcolor="rgba(0,0,0,0)",
                      font=dict(color=TITLE_DARK), xaxis_title=None, yaxis_title="Fit")
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("**Explicación**")
    st.markdown(f"- **Must-have (ok/total):** {len(exp['matched_must'])}/{exp['must_total']}")
    if exp["matched_must"]:
      st.markdown("  - ✓ " + ", ".join(exp["matched_must"]))
    if exp["gaps_must"]:
      st.markdown("  - ✗ Faltantes: " + ", ".join(exp["gaps_must"]))
    st.markdown(f"- **Nice-to-have (ok/total):** {len(exp['matched_nice'])}/{exp['nice_total']}")
    if exp["matched_nice"]:
      st.markdown("  - ✓ " + ", ".join(exp["matched_nice"]))
    if exp["gaps_nice"]:
      st.markdown("  - ✗ Faltantes: " + ", ".join(exp["gaps_nice"]))
    if exp["extras"]:
      st.markdown("- **Extras relevantes:** " + ", ".join(exp["extras"]))

  with c2:
    st.markdown("**CV (visor)**")
    if row["_is_pdf"]:
      pdf_viewer_embed(row["_bytes"], height=420)
    else:
      st.text_area("Contenido (TXT)", row["_text"], height=260)

  st.markdown("---")
  def _pills(lst, checked=False):
    if not lst: return ""
    cls = "skill-pill checked" if checked else "skill-pill"
    return "".join([f'<span class="{cls}">{"✓ " if checked else ""}{s}</span>' for s in lst])
  st.markdown("**Pills de coincidencia (must / nice / extras):**", unsafe_allow_html=True)
  st.markdown(_pills(exp["matched_must"], checked=True), unsafe_allow_html=True)
  st.markdown(_pills(exp["matched_nice"], checked=True), unsafe_allow_html=True)
  if exp["extras"]:
    st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
    st.caption("Extras")
    st.markdown(_pills(exp["extras"], checked=False), unsafe_allow_html=True)

def page_pipeline():
  st.header("Pipeline de Candidatos")
  if not ss.candidates:
    st.info("Primero carga o genera CVs en **Definición & Carga**.")
    return

  jd_text = ss.get("last_jd_text", "") or ""
  must_list = ROLE_PRESETS.get(ss.get("last_role",""), {}).get("must", [])
  nice_list = ROLE_PRESETS.get(ss.get("last_role",""), {}).get("nice", [])
  ranked = []
  for c in ss.candidates:
    cv_text = c.get("_text") or (c.get("_bytes") or b"").decode("utf-8","ignore")
    fit, exp = score_fit_by_skills(jd_text, must_list, nice_list, cv_text or "")
    ranked.append((fit, c, exp))
  ranked.sort(key=lambda x: x[0], reverse=True)

  c1, c2 = st.columns([1.2, 1])
  with c1:
    st.markdown("**Candidatos**")
    table_rows = []
    for fit, c, _exp in ranked:
      m = c.get("meta", {})
      table_rows.append({
        "Candidato": c["Name"], "Fit": fit,
        "Años Exp.": m.get("anios_exp", 0), "Universidad": m.get("universidad", "—"),
        "Actualizado": m.get("ultima_actualizacion", "—"),
      })
    df_table = pd.DataFrame(table_rows).sort_values(["Fit","Años Exp."], ascending=[False, False])
    st.dataframe(df_table, use_container_width=True, height=300)
    names = df_table["Candidato"].tolist()
    preselect = ss.get("selected_cand", names[0] if names else "")
    sel_name = st.radio("Selecciona un candidato", names, index=names.index(preselect) if preselect in names else 0)
    ss["selected_cand"] = sel_name

  with c2:
    st.markdown("**Detalle del candidato**")
    if "selected_cand" not in ss:
      st.caption("Selecciona un candidato de la lista.")
      return
    tup = next((t for t in ranked if t[1]["Name"] == ss["selected_cand"]), None)
    if not tup:
      st.caption("Candidato no encontrado.")
      return
    fit, row, exp = tup
    m = row.get("meta", {})

    st.markdown(f"**{row['Name']}**")
    st.markdown('<div class="k-card">', unsafe_allow_html=True)
    match_txt = "✅ Alto" if fit >= 70 else ("🟡 Medio" if fit >= 40 else "🔴 Bajo")
    st.markdown(f"**Match por skills:** {match_txt}  \n**Puntuación:** {fit}%")
    st.markdown("---")
    st.markdown("**Instrucción**")
    st.caption(EVAL_INSTRUCTION)
    st.markdown("**Análisis (resumen)**")
    st.write(build_analysis_text(row["Name"], exp))
    st.markdown("---")
    st.markdown("**Universidad**  \n" + m.get("universidad", "—"))
    st.markdown(f"**Años de experiencia**  \n{m.get('anios_exp', 0)}")
    st.markdown("**Ubicación**  \n" + m.get("ubicacion", "—"))
    st.markdown("**Título**  \n" + m.get("titulo", "—"))
    st.markdown("**Última actualización CV**  \n" + m.get("ultima_actualizacion", "—"))
    st.markdown("</div>", unsafe_allow_html=True)

    st.write("")
    st.subheader("CV")
    if row["_is_pdf"]:
      pdf_viewer_embed(row["_bytes"], height=420)
    else:
      st.text_area("Contenido (TXT)", row.get("_text",""), height=260)

    cbtn1, cbtn2 = st.columns(2)
    with cbtn1:
      if st.button("Añadir nota 'Buen encaje'"):
        st.success("Nota agregada.")
    with cbtn2:
      if st.button("Mover a ‘Entrevista (Gerencia)’"):
        ss.section = "interview"
        st.rerun()

    if row["_is_pdf"]:
      st.download_button("Descargar CV (PDF)", data=row["_bytes"], file_name=row["Name"], mime="application/pdf")
    else:
      st.download_button("Descargar CV (TXT)", data=row.get("_text","").encode("utf-8"), file_name=row["Name"], mime="text/plain")

def page_interview():
  st.header("Entrevista (Gerencia)")
  st.write("Use la rúbrica para calificar y decidir movimiento del candidato.")
  with st.form("iv_form"):
    cand = st.text_input("Candidato/a", ss.get("selected_cand", ""))
    tecnica = st.slider("Técnico (0-10)", 0, 10, 7)
    cultura = st.slider("Cultura (0-10)", 0, 10, 7)
    comp = st.slider("Compensación (0-10)", 0, 10, 6)
    notas = st.text_area("Notas")
    submitted = st.form_submit_button("Guardar evaluación")
    if submitted:
      st.success("Evaluación guardada.")
  c1, c2 = st.columns(2)
  with c1:
    if st.button("Mover a Oferta"):
      ss.section = "offer"; st.rerun()
  with c2:
    if st.button("Descartar con feedback"):
      st.warning("Marcado como descartado.")

def _ensure_offer_record(cand_name: str):
  if "offers" not in ss: ss.offers = {}
  if cand_name not in ss.offers:
    ss.offers[cand_name] = {
      "puesto": "", "ubicacion": "", "modalidad": "Presencial",
      "salario": "", "beneficios": "",
      "fecha_inicio": date.today() + timedelta(days=14),
      "caducidad": date.today() + timedelta(days=7),
      "aprobadores": "Gerencia, Legal, Finanzas", "estado": "Borrador"
    }

def page_offer():
  st.header("Oferta")
  if "selected_cand" not in ss:
    st.info("Selecciona un candidato en Pipeline o Entrevista.")
    return
  cand = ss["selected_cand"]
  _ensure_offer_record(cand)
  offer = ss.offers[cand]

  with st.form("offer_form"):
    c1, c2 = st.columns(2)
    with c1:
      offer["puesto"] = st.text_input("Puesto", offer["puesto"])
      offer["ubicacion"] = st.text_input("Ubicación", offer["ubicacion"])
      offer["modalidad"] = st.selectbox("Modalidad", ["Presencial","Híbrido","Remoto"],
                                        index=["Presencial","Híbrido","Remoto"].index(offer["modalidad"]))
      offer["salario"] = st.text_input("Salario (rango y neto)", offer["salario"])
    with c2:
      offer["beneficios"] = st.text_area("Bonos/beneficios", offer["beneficios"], height=100)
      offer["fecha_inicio"] = st.date_input("Fecha de inicio", value=offer["fecha_inicio"])
      offer["caducidad"] = st.date_input("Caducidad de oferta", value=offer["caducidad"])
      offer["aprobadores"] = st.text_input("Aprobadores", offer["aprobadores"])
    saved = st.form_submit_button("Guardar oferta")
    if saved:
      ss.offers[cand] = offer
      st.success("Oferta guardada.")

  c1, c2, c3 = st.columns(3)
  if c1.button("Enviar"):
    offer["estado"] = "Enviada"; ss.offers[cand] = offer
    st.success("Oferta enviada.")
  if c2.button("Registrar contraoferta"):
    offer["estado"] = "Contraoferta"; ss.offers[cand] = offer
    st.info("Contraoferta registrada.")
  if c3.button("Marcar aceptada"):
    offer["estado"] = "Aceptada"; ss.offers[cand] = offer
    st.success("¡Felicitaciones! Propuesta aceptada. Se generan tareas de Onboarding automáticamente.")
  st.write(f"**Estado actual:** {ss.offers[cand]['estado']}")

def page_onboarding():
  st.header("Onboarding")
  st.write("Checklist y responsables tras aceptar la oferta.")
  data = {
    "Tarea":["Contrato firmado","Documentos completos","Usuario/email creado","Acceso SAP IS-H","Examen médico",
             "Inducción día 1","EPP/Uniforme entregado","Plan 30-60-90 cargado"],
    "SLA":["48 h","72 h","24 h","24–48 h","según agenda","día 1","día 1","primer semana"],
    "Responsable":["RR.HH.","RR.HH.","TI","TI","Salud Ocup.","RR.HH.","RR.HH.","Jefe/Tutor"]
  }
  st.dataframe(pd.DataFrame(data), use_container_width=True, height=260)

def page_hh_tasks():
  st.header("Tareas del Headhunter")
  cand = st.text_input("Candidata/o", ss.get("selected_cand",""))
  col1, col2, col3 = st.columns(3)
  with col1: st.checkbox("✅ Contacto hecho")
  with col2: st.checkbox("✅ Entrevista agendada")
  with col3: st.checkbox("✅ Feedback recibido")
  st.text_area("Notas (3 fortalezas, 2 riesgos, pretensión, disponibilidad)", height=120)
  st.file_uploader("Adjuntos (BLS/ACLS, colegiatura, etc.)", accept_multiple_files=True)
  c1, c2 = st.columns(2)
  if c1.button("Guardar"): st.success("Checklist y notas guardadas.")
  if c2.button("Enviar a Comité"): st.info("Bloqueo de edición del HH y acta breve generada.")

def page_agents():
  st.header("Agentes")

  # ---------- GALERÍA (cards) ----------
  st.markdown("### Tus agentes")
  if not ss.agents:
    st.info("Aún no hay agentes. Crea el primero en el formulario de abajo.")
  else:
    cols_per_row = 3
    for i in range(0, len(ss.agents), cols_per_row):
      row = ss.agents[i:i+cols_per_row]
      cols = st.columns(cols_per_row)
      for idx, ag in enumerate(row):
        with cols[idx]:
          img_url = ag.get("image") or AGENT_DEFAULT_IMAGES.get(ag.get("rol","Headhunter"))
          st.markdown('<div class="agent-card">', unsafe_allow_html=True)
          st.markdown(
            f"""
            <div style="background:#fff;border:1px solid #E3EDF6;border-radius:16px;padding:16px;text-align:center;">
              <img src="{img_url}" alt="avatar" style="width:120px;height:120px;border-radius:999px;object-fit:cover;border:4px solid #F1F7FD;">
              <div style="height:8px"></div>
              <div style="font-weight:800;color:{TITLE_DARK};font-size:18px">{ag.get('rol','—')}</div>
              <div style="font-size:13px;opacity:.8;margin-top:6px">{ag.get('objetivo','—')}</div>
            </div>
            """,
            unsafe_allow_html=True
          )
          c1, c2, c3, c4 = st.columns([1,1,1,1])
          with c1:
            if st.button("👁️ Ver", key=f"ag_view_{i+idx}"):
              ss["agent_view_idx"] = i+idx
          with c2:
            if st.button("✏️ Edit", key=f"ag_edit_{i+idx}"):
              ss["agent_edit_idx"] = i+idx
              ss["agent_view_idx"] = i+idx
          with c3:
            if st.button("🧬 Clone", key=f"ag_clone_{i+idx}"):
              clone = dict(ag)
              clone["rol"] = f"{ag.get('rol','Agente')} (copia)"
              ss.agents.append(clone)
              save_agents(ss.agents)
              st.success("Agente clonado.")
          with c4:
            if st.button("🗑️ Del", key=f"ag_del_{i+idx}"):
              ss["agent_delete_idx"] = i+idx
          st.markdown('</div>', unsafe_allow_html=True)

  st.markdown("---")

  # ---------- DETALLE (vista) ----------
  v_idx = ss.get("agent_view_idx", None)
  if v_idx is not None and 0 <= v_idx < len(ss.agents):
    ag = ss.agents[v_idx]
    st.subheader("Detalle del agente")
    st.markdown('<div class="agent-detail">', unsafe_allow_html=True)
    c1, c2 = st.columns([0.42, 0.58])
    with c1:
      img_url = ag.get("image") or AGENT_DEFAULT_IMAGES.get(ag.get("rol","Headhunter"))
      st.image(img_url, width=200, caption=None, use_column_width=False)
      st.write("")
      st.caption("Modelo LLM (simulado)")
      st.markdown(f"<div class='badge'>🧠 {ag.get('llm_model','gpt-4o-mini')}</div>", unsafe_allow_html=True)
    with c2:
      st.text_input("Role*", value=ag.get("rol",""), disabled=True)
      st.text_input("Goal*", value=ag.get("objetivo",""), disabled=True)
      st.text_area("Backstory*", value=ag.get("backstory",""), height=160, disabled=True)
      st.text_area("Guardrails", value=ag.get("guardrails",""), height=90, disabled=True)
      st.caption("Herramientas habilitadas")
      st.write(", ".join(ag.get("herramientas", [])) or "—")
    st.markdown('</div>', unsafe_allow_html=True)

  # ---------- Confirmación borrado ----------
  if "agent_delete_idx" in ss:
    di = ss["agent_delete_idx"]
    if 0 <= di < len(ss.agents):
      st.warning(f"¿Eliminar agente **{ss.agents[di].get('rol','Agente')}**? Esta acción no se puede deshacer.")
      cc1, cc2 = st.columns(2)
      with cc1:
        if st.button("Sí, eliminar definitivamente"):
          ss.agents.pop(di)
          save_agents(ss.agents)
          ss.pop("agent_delete_idx", None)
          st.success("Agente eliminado.")
      with cc2:
        if st.button("Cancelar"):
          ss.pop("agent_delete_idx", None)

  # ---------- FORM alta/edición ----------
  st.subheader("Crear / Editar agente")

  edit_idx = ss.get("agent_edit_idx", None)
  options = ["Nuevo"] + [f"{i} — {ss.agents[i]['rol']}" for i in range(len(ss.agents))]
  default_idx = 0 if (edit_idx is None or not isinstance(edit_idx,int)) else min(len(options)-1, edit_idx+1)
  pick = st.selectbox("Selecciona para editar (o 'Nuevo')", options=options, index=default_idx)
  current_idx = None
  if pick != "Nuevo":
    current_idx = int(pick.split(" — ")[0])
    base = ss.agents[current_idx]
  else:
    base = {"rol":"Headhunter","objetivo":"Identificar a los mejores profesionales para el cargo definido en el JD"}

  with st.form("agent_form"):
    c1, c2 = st.columns(2)
    with c1:
      rol_options = ["Headhunter","Coordinador RR.HH.","Admin RR.HH."]
      rol = st.selectbox("Rol*", rol_options, index=_safe_index(rol_options, base.get("rol","Headhunter"), 0))
      objetivo = st.text_input("Objetivo*", base.get("objetivo",""))
      backstory = st.text_area("Backstory*", base.get("backstory","Eres un analista de RR.HH. con experiencia en análisis de documentos, CV y currículums."), height=120)
      guardrails = st.text_area("Guardrails", base.get("guardrails","No compartas datos sensibles. Cita la fuente (CV o JD) al argumentar."), height=90)
    with c2:
      herramientas = st.multiselect("Herramientas habilitadas",
                                    ["Parser de PDF","Recomendador de skills","Comparador JD-CV"],
                                    default=base.get("herramientas", ["Parser de PDF","Recomendador de skills"]))
      llm_model = st.selectbox("Modelo LLM (simulado)", LLM_MODELS,
                               index=_safe_index(LLM_MODELS, base.get("llm_model", LLM_MODELS[0]), 0))
      st.caption("Imagen del agente")
      default_img = base.get("image", AGENT_DEFAULT_IMAGES.get(base.get("rol","Headhunter"), ""))
      img_src = st.text_input("URL de imagen (opcional)", value=default_img)
      up = st.file_uploader("…o sube una imagen", type=["png","jpg","jpeg","webp"])
      if up is not None:
        data_uri = _file_to_data_uri(up)
        if data_uri: img_src = data_uri

    ok = st.form_submit_button("Guardar/Actualizar Agente")
    if ok:
      record = {
        "rol": rol, "objetivo": objetivo, "backstory": backstory, "guardrails": guardrails,
        "herramientas": herramientas, "llm_model": llm_model, "image": img_src,
        "ts": datetime.utcnow().isoformat()
      }
      if current_idx is None:
        ss.agents.append(record)
      else:
        ss.agents[current_idx] = record
      save_agents(ss.agents)
      st.success("Agente guardado (con imagen y modelo).")

  st.markdown("---")
  c1, c2, c3 = st.columns([1,1,2])
  with c1:
    if st.button("💾 Guardar en disco ahora"):
      save_agents(ss.agents); st.success("Guardado en data/agents.json")
  with c2:
    if ss.agents:
      st.download_button("⬇️ Exportar agentes (JSON)",
                         data=json.dumps(ss.agents, ensure_ascii=False, indent=2).encode("utf-8"),
                         file_name="agents_export.json", mime="application/json")
  with c3:
    up_json = st.file_uploader("⬆️ Importar agentes (JSON)", type=["json"], key="import_agents_json")
    if up_json is not None:
      try:
        imported = json.loads(up_json.read().decode("utf-8"))
        if isinstance(imported, list):
          ss.agents = imported
          save_agents(ss.agents)
          st.success(f"Importados {len(imported)} agentes.")
        else:
          st.error("El archivo debe contener una lista JSON.")
      except Exception as e:
        st.error(f"No se pudo importar: {e}")

def page_flows():
  st.header("Flujos")
  st.write("Define y documenta flujos (demo).")

def page_agent_tasks():
  st.header("Tareas de Agente")
  st.write("Bandeja de tareas para asistentes (demo).")

def page_analytics():
  st.header("Analytics")
  total_cands = len(ss.candidates)
  avg_score = round(pd.Series([c.get("Score",0) for c in ss.candidates]).mean(), 1) if ss.candidates else 0
  high_match = sum(1 for c in ss.candidates if c.get("Score",0) >= 60)
  open_positions = int(ss.positions[ss.positions["Estado"]=="Abierto"].shape[0]) if not ss.positions.empty else 0
  avg_days_open = round(ss.positions["Días Abierto"].mean(), 1) if not ss.positions.empty else 0

  c1, c2, c3, c4, c5 = st.columns(5)
  with c1: st.markdown(f'<div class="k-card"><div class="badge">📄</div><h4>Total CVs</h4><h2>{total_cands}</h2></div>', unsafe_allow_html=True)
  with c2: st.markdown(f'<div class="k-card"><div class="badge">🏷️</div><h4>Score promedio</h4><h2>{avg_score}</h2></div>', unsafe_allow_html=True)
  with c3: st.markdown(f'<div class="k-card"><div class="badge">✅</div><h4>Matches ≥60%</h4><h2>{high_match}</h2></div>', unsafe_allow_html=True)
  with c4: st.markdown(f'<div class="k-card"><div class="badge">🧩</div><h4>Puestos abiertos</h4><h2>{open_positions}</h2></div>', unsafe_allow_html=True)
  with c5: st.markdown(f'<div class="k-card"><div class="badge">⏱️</div><h4>Días abiertos (prom.)</h4><h2>{avg_days_open}</h2></div>', unsafe_allow_html=True)

  st.write("")
  left, right = st.columns(2)
  with left:
    st.subheader("Distribución de puntajes (keywords)")
    if ss.candidates:
      df_scores = pd.DataFrame([{"Candidato": c["Name"], "Score": c.get("Score",0)} for c in ss.candidates])
      fig_hist = px.histogram(df_scores, x="Score", nbins=10, title="Histograma de Score")
      fig_hist.update_layout(plot_bgcolor="#FFFFFF", paper_bgcolor="rgba(0,0,0,0)",
                             font=dict(color=TITLE_DARK), xaxis_title=None, yaxis_title="Cantidad")
      st.plotly_chart(fig_hist, use_container_width=True)
    else:
      st.info("Aún no hay CVs cargados.")
  with right:
    st.subheader("Top Puestos por Leads")
    if not ss.positions.empty:
      df_pos = ss.positions.sort_values("Leads", ascending=False).head(5)
      fig_pos = px.bar(df_pos, x="Puesto", y="Leads", title="Puestos con más Leads")
      fig_pos.update_traces(hovertemplate="%{x}<br>Leads: %{y}")
      fig_pos.update_layout(plot_bgcolor="#FFFFFF", paper_bgcolor="rgba(0,0,0,0)",
                            font=dict(color=TITLE_DARK), xaxis_title=None, yaxis_title="Leads")
      st.plotly_chart(fig_pos, use_container_width=True)
    else:
      st.info("Sin datos de puestos.")

  st.write("")
  st.subheader("Ofertas (estado actual)")
  df_off = _offers_to_df(ss.offers)
  if not df_off.empty:
    st.dataframe(df_off, use_container_width=True, height=220)
    counts = df_off["Estado"].value_counts().reset_index()
    counts.columns = ["Estado", "Cantidad"]
    fig_off = px.bar(counts, x="Estado", y="Cantidad", title="Ofertas por estado")
    fig_off.update_layout(plot_bgcolor="#FFFFFF", paper_bgcolor="rgba(0,0,0,0)",
                          font=dict(color=TITLE_DARK), xaxis_title=None, yaxis_title=None)
    st.plotly_chart(fig_off, use_container_width=True)
  else:
    st.info("No hay ofertas registradas aún.")

  st.write("")
  b1, b2, b3 = st.columns(3)
  with b1:
    if st.button("Ir a Carga de CVs"): ss.section = "def_carga"; st.rerun()
  with b2:
    if st.button("Ir a Pipeline"): ss.section = "pipeline"; st.rerun()
  with b3:
    if st.button("Ir a Ofertas"): ss.section = "offer"; st.rerun()

def page_create_task():
  st.header("Crear tarea")
  with st.form("t_form"):
    titulo = st.text_input("Título")
    desc = st.text_area("Descripción", height=150)
    due = st.date_input("Fecha límite", value=date.today())
    ok = st.form_submit_button("Guardar")
    if ok:
      ss.tasks.append({"titulo":titulo,"desc":desc,"due":str(due)})
      st.success("Tarea creada.")

# =========================================================
# ROUTER
# =========================================================
ROUTES = {
  "def_carga": page_def_carga,
  "puestos": page_puestos,
  "eval": page_eval,
  "pipeline": page_pipeline,
  "interview": page_interview,
  "offer": page_offer,
  "onboarding": page_onboarding,
  "hh_tasks": page_hh_tasks,
  "agents": page_agents,
  "flows": page_flows,
  "agent_tasks": page_agent_tasks,
  "analytics": page_analytics,
  "create_task": page_create_task,
}

ROUTES.get(ss.section, page_def_carga)()
