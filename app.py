# app.py
# -*- coding: utf-8 -*-

import io, base64, re, json, random, zipfile, uuid, tempfile, os
from pathlib import Path
from datetime import datetime, date, timedelta

import streamlit as st
import pandas as pd
import plotly.express as px
from PyPDF2 import PdfReader

# ====== Paquetes de LLM ======
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    load_dotenv = lambda: None

try:
    from langchain_core.output_parsers import JsonOutputParser
    from langchain_core.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate
    from langchain_community.document_loaders import PyPDFLoader
    from langchain_openai import ChatOpenAI, AzureChatOpenAI
    _LC_AVAILABLE = True
except Exception:
    _LC_AVAILABLE = False

# =========================================================
# PALETA / CONST
# =========================================================
PRIMARY        = "#00CD78"
SIDEBAR_BG = "#0E192B"
SIDEBAR_TX = "#B9C7DF"
BODY_BG        = "#F7FBFF"
CARD_BG        = "#0E192B"
TITLE_DARK = "#142433"

BAR_DEFAULT = "#E9F3FF"
BAR_GOOD    = "#33FFAC"
PLOTLY_GREEN_SEQUENCE = ["#00CD78", "#00B468", "#33FFAC", "#007F46", "#66FFC2"]

JOB_BOARDS  = ["laborum.pe","Computrabajo","Bumeran","Indeed","LinkedIn Jobs"]
PIPELINE_STAGES = ["Recibido", "Screening RRHH", "Entrevista Telefónica", "Entrevista Gerencia", "Oferta", "Contratado", "Descartado"]
TASK_PRIORITIES = ["Alta", "Media", "Baja"]
HR_ROLES = ["Coordinador RR.HH.", "Admin RR.HH."]

EVAL_INSTRUCTION = (
  "Debes analizar los CVs de postulantes y calificarlos de 0% a 100% según el nivel de coincidencia con el JD. "
  "Incluye un análisis breve que explique por qué califica o no el postulante, destacando habilidades must-have, "
  "nice-to-have, brechas y hallazgos relevantes."
)
DEFAULT_EXPECTED_OUTPUT = "- Puntuación 0 a 100 según coincidencia con JD\n- Resumen del CV explicando por qué califica o no el postulante."

# ===== Login =====
USERS = {
  "colab": {"password":"colab123","role":"Colaborador","name":"Colab"},
  "super": {"password":"super123","role":"Supervisor","name":"Sup"},
  "admin": {"password":"admin123","role":"Administrador","name":"Admin"},
}

AGENT_DEFAULT_IMAGES = {
  "Headhunter":        "https://images.unsplash.com/photo-1581090464777-f3220bbe1b8b?q=80&w=512&auto-format&fit=crop",
  "Coordinador RR.HH.":"https://images.unsplash.com/photo-1542751371-adc38448a05e?q=80&w=512&auto-format&fit=crop",
  "Admin RR.HH.":      "https://images.unsplash.com/photo-1526378722484-bd91ca387e72?q=80&w=512&auto-format&fit=crop",
}
LLM_IN_USE = "gpt-4o-mini"

# ===== Presets de puestos =====
ROLE_PRESETS = {
  "Asistente Administrativo": {
    "jd": "Brindar soporte administrativo integral a las áreas internas: gestión documental, coordinación con proveedores y compras menores, logística de reuniones y elaboración de reportes ejecutivos. Deberá manejar Excel (tablas dinámicas y gráficos), Word y PowerPoint, y apoyar en facturación y caja chica (según políticas). Se valoran conocimientos de SharePoint/Google Drive y uso básico de ERP (SAP/Oracle/CONCAR).",
    "keywords": "Excel, Word, PowerPoint, gestión documental, atención a proveedores, compras, logística, caja chica, facturación, redacción",
    "must": ["Excel","Gestión documental","Redacción"], "nice": ["Facturación","Caja"],
    "synth_skills": ["Excel","Word","PowerPoint","Gestión documental","Redacción","Facturación","Caja","Atención al cliente"]
  },
  "Business Analytics": {
    "jd": "Recolectar, transformar y analizar datos para generar insights que apoyen la toma de decisiones. Desarrollar y mantener dashboards en Power BI y Tableau. Realizar consultas complejas en SQL, automatizar reportes (Python deseable) y presentar hallazgos a stakeholders.",
    "keywords": "SQL, Power BI, Tableau, ETL, KPI, storytelling, Excel avanzado, Python, A/B testing, métricas de negocio",
    "must": ["SQL","Power BI"], "nice": ["Tableau","Python","ETL"],
    "synth_skills": ["SQL","Power BI","Tableau","Excel","ETL","KPIs","Storytelling","Python","A/B testing"]
  },
  "Diseñador/a UX": {
    "jd": "Responsable de research, definición de flujos de usuario, wireframes y prototipos de alta fidelidad en Figma. Deberá conducir pruebas de usabilidad, analizar métricas y colaborar con equipos de Producto y Desarrollo para asegurar la implementación de un Design System coherente.",
    "keywords": "Figma, UX research, prototipado, wireframes, heurísticas, accesibilidad, design system, usabilidad, tests con usuarios",
    "must": ["Figma","UX Research","Prototipado"], "nice":["Heurísticas","Accesibilidad","Design System"],
    "synth_skills":["Figma","UX Research","Prototipado","Wireframes","Accesibilidad","Heurísticas","Design System","Analytics"]
  },
  "Ingeniero/a de Proyectos": {
    "jd":"Planificar, ejecutar y controlar proyectos de ingeniería, asegurando el cumplimiento de plazos, costos y calidad. Manejo de MS Project para cronogramas, AutoCAD para revisión de planos y gestión de presupuestos. Deseable conocimiento de metodologías PMBOK o Agile.",
    "keywords":"MS Project, AutoCAD, BIM, presupuestos, cronogramas, control de cambios, riesgos, PMBOK, Agile, KPI, licitaciones",
    "must":["MS Project","AutoCAD","Presupuestos"], "nice":["BIM","PMBOK","Agile"],
    "synth_skills":["MS Project","AutoCAD","BIM","Presupuestos","Cronogramas","Riesgos","PMBOK","Agile","Excel","Power BI"]
  },
  "Enfermera/o Asistencial": {
    "jd":"Brindar atención segura y de calidad al paciente hospitalizado, administrar tratamientos, y registrar evoluciones en el sistema HIS. Cumplir con protocolos de bioseguridad (IAAS) y soporte vital (BLS, ACLS). Colaborar con el equipo médico y educar al paciente y familia.",
    "keywords":"HIS, SAP IS-H, BLS, ACLS, IAAS, educación al paciente, seguridad del paciente, protocolos...",
    "must":["HIS","BLS","ACLS","IAAS","Seguridad del paciente"], "nice":["SAP IS-H","Educación al paciente","Protocolos"],
    "synth_skills":["HIS","BLS","ACLS","IAAS","Educación al paciente","Seguridad del paciente","Protocolos","Excel"]
  },
  "Recepcionista de Admisión": {
    "jd": "Recepción de pacientes, registro en sistema (HIS o SAP), coordinación de citas, manejo de caja, emisión de facturas y boletas. Brindar excelente atención al cliente, orientar sobre servicios y gestionar la sala de espera. Requiere alta vocación de servicio y orden.",
    "keywords": "admisión, caja, facturación, SAP, HIS, atención al cliente, citas, recepción",
    "must": ["Atención al cliente","Registro","Caja"], "nice": ["Facturación","SAP","HIS"],
    "synth_skills": ["Atención al cliente","Registro","Caja","Facturación","SAP","HIS","Comunicación"]
  }
}

DUMMY_PDF_BYTES = base64.b64decode(
    b'JVBERi0xLjAKMSAwIG9iajw8L1R5cGUvQ2F0YWxvZy9QYWdlcyAyIDAgUj4+ZW5kb2JqCjIgMCBvYmo8PC9UeXBlL1BhZ2VzL0NvdW50IDEvS2lkc1szIDAgUl0+PmVuZG9iagozIDAgb2JqPDwvVHlwZS9QYWdlL01lZGlhQm94WzAgMCAzMCAzMF0vUGFyZW50IDIgMCBSPj5lbmRvYmoKeHJlZgowIDQKMDAwMDAwMDAwMCA2NTUzNSBmIAowMDAwMDAwMDA5IDAwMDAwIG4gCjAwMDAwMDAwNTIgMDAwMDAgbiAKMDAwMDAwMDA5OSAwMDAwMCBuIAp0cmFpbGVyPDwvU2l6ZSA0L1Jvb3QgMSAwIFI+PgpzdGFydHhyZWYKMTQ3CiUlRU9G'
)

# =========================================================
# CSS & CONFIG
# =========================================================
CSS = f"""
:root {{ --green: {PRIMARY}; --sb-bg: {SIDEBAR_BG}; --sb-tx: {SIDEBAR_TX}; --body: {BODY_BG}; --sb-card: {CARD_BG}; }}
html, body, [data-testid="stAppViewContainer"] {{ background: var(--body) !important; }}
.block-container {{ background: transparent !important; padding-top: 1.25rem !important; }}

#MainMenu {{visibility:hidden;}}
[data-testid="stToolbar"] {{ display:none !important; }}
header[data-testid="stHeader"] {{ height:0 !important; min-height:0 !important; }}

[data-testid="stSidebar"] {{ background: var(--sb-bg) !important; color: var(--sb-tx) !important; }}
[data-testid="stSidebar"] * {{ color: var(--sb-tx) !important; }}
[data-testid="stSidebar"] h4, [data-testid="stSidebar"] .stMarkdown h4 {{ color: var(--green) !important; }}

.sidebar-brand {{ display:flex; flex-direction:column; align-items:center; justify-content:center; padding:0 0 2px; margin-top:0; text-align:center; }}
.sidebar-brand .brand-title {{ color: var(--green) !important; font-weight:800 !important; font-size:55px !important; line-height:1.05 !important; }}
.sidebar-brand .brand-sub {{ margin-top:4px !important; color: var(--green) !important; font-size:12px !important; opacity:.95 !important; }}

[data-testid="stSidebar"] .stButton>button {{
  width: 100% !important; display:flex !important; justify-content:flex-start !important; align-items:center !important; text-align:left !important;
  gap:8px !important; background: var(--sb-card) !important; border:1px solid var(--sb-bg) !important; color:#fff !important;
  border-radius:12px !important; padding:9px 12px !important; margin:6px 8px !important; font-weight:600 !important;
}}

.block-container .stButton>button {{
  width:auto !important; display:flex !important; justify-content:center !important; align-items:center !important; text-align:center !important;
  background: var(--green) !important; color:#082017 !important; border-radius:10px !important; border:none !important; padding:.50rem .90rem !important; font-weight:700 !important;
}}
.block-container .stButton>button:hover {{ filter: brightness(.96); }}

.block-container .stButton>button.delete-eval-btn {{
    background: #D60000 !important; color: white !important;
    padding: .35rem .8rem !important; font-weight: 600 !important;
}}

.block-container .stButton>button.delete-confirm-btn {{ background: #D60000 !important; color: white !important; }}
.block-container .stButton>button.cancel-btn {{ background: #e0e0e0 !important; color: #333 !important; }}

h1, h2, h3 {{ color: {TITLE_DARK}; }}
h1 strong, h2 strong, h3 strong {{ color: var(--green); }}

.block-container [data-testid="stSelectbox"]>div>div,
.block-container [data-baseweb="select"],
.block-container [data-testid="stTextInput"] input,
.block-container [data-testid="stDateInput"] input,
.block-container [data-testid="stTextArea"] textarea {{
  background:#F1F7FD !important; color:{TITLE_DARK} !important; border:1.5px solid #E3EDF6 !important; border-radius:10px !important;
}}
.block-container [data-testid="stTextInput"] input[disabled] {{
  background: #E9F3FF !important;
  color: #555 !important;
}}

.block-container table {{ background:#fff !important; border:1px solid #E3EDF6 !important; border-radius:8px !important; }}
.block-container thead th {{ background:#F1F7FD !important; color:{TITLE_DARK} !important; }}
.k-card {{ background:#fff;border:1px solid #E3EDF6;border-radius:12px;padding:14px; }}
.badge {{ display:inline-flex;align-items:center;gap:6px;background:#F1F7FD;border:1px solid #E3EDF6;border-radius:24px;padding:4px 10px;font-size:12px;color:#1B2A3C; }}

.priority-Alta {{ border-color: #FFA500 !important; background: #FFF5E6 !important; color: #E88E00 !important; font-weight: 600;}}
.priority-Media {{ border-color: #B9C7DF !important; background: #F1F7FD !important; color: #0E192B !important; }}
.priority-Baja {{ border-color: #D1D5DB !important; background: #F3F4F6 !important; color: #6B7280 !important; }}

.agent-card{{background:#fff;border:1px solid #E3EDF6;border-radius:14px;padding:10px;text-align:center;min-height:178px}}
.agent-card img{{width:84px;height:84px;border-radius:999px;object-fit:cover;border:4px solid #F1F7FD}}
.agent-title{{font-weight:800;color:{TITLE_DARK};font-size:15px;margin-top:6px}}
.agent-sub{{font-size:12px;opacity:.8;margin-top:4px;min-height:30px}}

.toolbar{{display:flex;align-items:center;justify-content:center;gap:8px;margin-top:8px}}
.toolbar .stButton>button{{
  background:#fff !important; color:#2b3b4d !important; border:1px solid #E3EDF6 !important;
  border-radius:10px !important; padding:6px 8px !important; min-width:36px !important;
}}
.toolbar .stButton>button:hover{{ background:#F7FBFF !important; }}

.agent-detail{{background:#fff;border:2px solid #E3EDF6;border-radius:16px;padding:16px;box-shadow:0 6px 18px rgba(14,25,43,.08)}}

.login-bg{{background:{SIDEBAR_BG};position:fixed;inset:0;display:flex;align-items:center;justify-content:center}}
.login-card{{background:transparent;border:none;box-shadow:none;padding:0;width:min(600px,92vw);}}
.login-logo-wrap{{display:flex;align-items:center;justify-content:center;margin-bottom:14px}}
.login-sub{{color:#9fb2d3;text-align:center;margin:0 0 18px 0;font-size:12.5px}}
.login-card [data-testid="stTextInput"] input {{
  background:#10283f !important; color:#E7F0FA !important; border:1.5px solid #1d3a57 !important;
  border-radius:24px !important; height:48px !important; padding:0 16px !important;
}}
.login-card .stButton>button{{ width:160px !important; border-radius:24px !important; }}

.status-Contratado {{ background-color: #E6FFF1 !important; color: {PRIMARY} !important; border-color: #98E8BF !important; }}
.status-Descartado {{ background-color: #FFE6E6 !important; color: #D60000 !important; border-color: #FFB3B3 !important; }}
.status-Oferta {{ background-color: #FFFDE6 !important; color: #E8B900 !important; border-color: #FFE066 !important; }}
"""
st.set_page_config(page_title="SelektIA", page_icon="🧠", layout="wide")
st.markdown(f"<style>{CSS}</style>", unsafe_allow_html=True)

# Powered by size
st.markdown("""
<style>
[data-testid="stSidebar"] .sidebar-brand .brand-sub{
  font-size: 12px !important; line-height: 1.2 !important; margin-top: 4px !important; opacity: .95 !important;
}
</style>
""", unsafe_allow_html=True)

# Sidebar spacing compact
st.markdown("""
<style>
[data-testid="stSidebar"] .sidebar-brand{ margin-top:0 !important; padding-bottom:0 !important; margin-bottom:55px !important; }
[data-testid="stSidebar"] [data-testid="stVerticalBlock"]{ gap:2px !important; }
[data-testid="stSidebar"] [data-testid="stVerticalBlock"]>div{ margin:0 !important; padding:0 !important; }
[data-testid="stSidebar"] h4, [data-testid="stSidebar"] .stMarkdown h4{ margin:2px 8px 2px !important; line-height:1 !important; }
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p{ margin:2px 8px !important; }
[data-testid="stSidebar"] .stButton{ margin:0 !important; padding:0 !important; }
[data-testid="stSidebar"] .stButton>button{ margin:0 8px 6px 0 !important; padding-left:8px !important; line-height:1.05 !important; gap:6px !important; }
</style>
""", unsafe_allow_html=True)

# =========================================================
# Persistencia
# =========================================================
DATA_DIR = Path("data"); DATA_DIR.mkdir(exist_ok=True)
AGENTS_FILE = DATA_DIR/"agents.json"
WORKFLOWS_FILE = DATA_DIR/"workflows.json"
ROLES_FILE = DATA_DIR / "roles.json"
TASKS_FILE = DATA_DIR / "tasks.json"
EVALS_FILE = DATA_DIR / "evaluations.json"

DEFAULT_ROLES = ["Headhunter", "Coordinador RR.HH.", "Admin RR.HH."]
DEFAULT_TASKS = [
    {"id": str(uuid.uuid4()), "titulo":"Revisar CVs top 5", "desc":"Analizar a los 5 candidatos con mayor fit para 'Business Analytics'.", "due":str(date.today() + timedelta(days=2)), "assigned_to": "Headhunter", "status": "Pendiente", "priority": "Alta", "created_at": (date.today() - timedelta(days=3)).isoformat()},
    {"id": str(uuid.uuid4()), "titulo":"Coordinar entrevista de Rivers Brykson", "desc":"Agendar la 2da entrevista (Gerencia) para el puesto de VP de Marketing.", "due":str(date.today() + timedelta(days=5)), "assigned_to": "Coordinador RR.HH.", "status": "En Proceso", "priority": "Media", "created_at": (date.today() - timedelta(days=8)).isoformat(), "context": {"candidate_name": "Rivers Brykson", "role": "VP de Marketing"}},
    {"id": str(uuid.uuid4()), "titulo":"Crear workflow de Onboarding", "desc":"Definir pasos en 'Flujos' para Contratado.", "due":str(date.today() - timedelta(days=1)), "assigned_to": "Admin RR.HH.", "status": "Completada", "priority": "Baja", "created_at": (date.today() - timedelta(days=15)).isoformat()},
    {"id": str(uuid.uuid4()), "titulo":"Análisis Detallado de CV_MartaDiaz.pdf", "desc":"Utilizar el agente de análisis para generar un informe de brechas de skills.", "due":str(date.today() + timedelta(days=3)), "assigned_to": "Agente de Análisis", "status": "Pendiente", "priority": "Media", "created_at": date.today().isoformat(), "context": {"candidate_name": "MartaDiaz.pdf", "role": "Desarrollador/a Backend (Python)"}}
]

def load_roles():
  if ROLES_FILE.exists():
    try:
      roles = json.loads(ROLES_FILE.read_text(encoding="utf-8"))
      roles = sorted(list({*DEFAULT_ROLES, *(r.strip() for r in roles if r.strip())}))
      return roles
    except:
      pass
  return DEFAULT_ROLES.copy()

def save_roles(roles: list):
  roles_clean = sorted(list({r.strip() for r in roles if r.strip()}))
  custom_only = [r for r in roles_clean if r not in DEFAULT_ROLES]
  ROLES_FILE.write_text(json.dumps(custom_only, ensure_ascii=False, indent=2), encoding="utf-8")

def load_json(path: Path, default):
  if path.exists():
    try: return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"Error reading JSON from {path}: {e}")
        try:
            if default is not None: save_json(path, default)
            return default
        except Exception as e_save:
            print(f"Error saving default JSON to {path}: {e_save}")
            return default if isinstance(default, (list, dict)) else []
  if default is not None:
      try: save_json(path, default)
      except Exception as e: print(f"Error creating default file {path}: {e}")
  return default if isinstance(default, (list, dict)) else []

def save_json(path: Path, data):
  try:
      path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
  except Exception as e:
      print(f"Error saving JSON to {path}: {e}")

def load_agents(): return load_json(AGENTS_FILE, [])
def save_agents(agents): save_json(AGENTS_FILE, agents)
def load_workflows(): return load_json(WORKFLOWS_FILE, [])
def save_workflows(wfs): save_json(WORKFLOWS_FILE, wfs)
def load_tasks(): return load_json(TASKS_FILE, DEFAULT_TASKS)
def save_tasks(tasks): save_json(TASKS_FILE, tasks)
def load_evals(): return load_json(EVALS_FILE, [])
def save_evals(evals): save_json(EVALS_FILE, evals)

# =========================================================
# ESTADO
# =========================================================
ss = st.session_state
if "auth" not in ss: ss.auth = None
if "section" not in ss:  ss.section = "publicacion_sourcing"

if "tasks_loaded" not in ss:
    ss.tasks = load_tasks()
    if not isinstance(ss.tasks, list):
        ss.tasks = DEFAULT_TASKS
        save_tasks(ss.tasks)
    ss.tasks_loaded = True

if "candidates" not in ss: ss.candidates = []
if "offers" not in ss:  ss.offers = {}
if "agents_loaded" not in ss:
  ss.agents = load_agents()
  ss.agents_loaded = True
if "workflows_loaded" not in ss:
  ss.workflows = load_workflows()
  ss.workflows_loaded = True
if "agent_view_idx" not in ss: ss.agent_view_idx = None
if "agent_edit_idx" not in ss: ss.agent_edit_idx = None
if "new_role_mode" not in ss: ss.new_role_mode = False
if "roles" not in ss: ss.roles = load_roles()
if "positions" not in ss:
  ss.positions = pd.DataFrame([
      {"ID":"10,645,194","Puesto":"Desarrollador/a Backend (Python)","Días Abierto":3,
       "Leads":1800,"Nuevos":115,"Recruiter Screen":35,"HM Screen":7,
       "Entrevista Telefónica":14,"Entrevista Presencial":15,"Ubicación":"Lima, Perú",
       "Hiring Manager":"Rivers Brykson","Estado":"Abierto","Fecha Inicio": date.today() - timedelta(days=3)},
      {"ID":"10,376,415","Puesto":"VP de Marketing","Días Abierto":28,
       "Leads":8100,"Nuevos":1,"Recruiter Screen":15,"HM Screen":35,
       "Entrevista Telefónica":5,"Entrevista Presencial":7,"Ubicación":"Santiago, Chile",
       "Hiring Manager":"Angela Cruz","Estado":"Abierto","Fecha Inicio": date.today() - timedelta(days=28)},
      {"ID":"10,376,646","Puesto":"Planner de Demanda","Días Abierto":28,
       "Leads":2300,"Nuevos":26,"Recruiter Screen":3,"HM Screen":8,
       "Entrevista Telefónica":6,"Entrevista Presencial":3,"Ubicación":"Ciudad de México, MX",
       "Hiring Manager":"Rivers Brykson","Estado":"Abierto","Fecha Inicio": date.today() - timedelta(days=28)}
  ])
if "pipeline_filter" not in ss: ss.pipeline_filter = None
if "expanded_task_id" not in ss: ss.expanded_task_id = None
if "show_assign_for" not in ss: ss.show_assign_for = None
if "confirm_delete_id" not in ss: ss.confirm_delete_id = None
if "editing_flow_id" not in ss: ss.editing_flow_id = None
if "all_evaluations" not in ss: ss.all_evaluations = load_evals()
if "last_llm_batch" not in ss: ss.last_llm_batch = []

DEFAULT_FLOW_ROLE = "Asistente Administrativo"
if "flow_form_name" not in ss: ss.flow_form_name = "Analizar CV"
if "flow_form_role" not in ss: ss.flow_form_role = DEFAULT_FLOW_ROLE
if "flow_form_desc" not in ss: ss.flow_form_desc = ROLE_PRESETS[DEFAULT_FLOW_ROLE].get("jd", EVAL_INSTRUCTION)
if "flow_form_expected" not in ss: ss.flow_form_expected = DEFAULT_EXPECTED_OUTPUT
if "flow_form_jd" not in ss: ss.flow_form_jd = ROLE_PRESETS[DEFAULT_FLOW_ROLE].get("jd", "")
if "flow_form_agent_idx" not in ss: ss.flow_form_agent_idx = 0
if "form_loaded_from_edit" not in ss: ss.form_loaded_from_edit = False

# Nuevo estado para Evaluación LLM
DEFAULT_EVAL_LLM_ROLE = ss.get("last_role", DEFAULT_FLOW_ROLE)
if "eval_llm_role" not in ss: ss.eval_llm_role = DEFAULT_EVAL_LLM_ROLE
if "eval_llm_jd" not in ss: ss.eval_llm_jd = ROLE_PRESETS[DEFAULT_EVAL_LLM_ROLE].get("jd", "")

# =========================================================
# UTILS
# =========================================================

# Callback para actualizar formulario de flujos
def update_flow_fields_from_preset():
    new_role = ss.flow_form_role
    if new_role in ROLE_PRESETS:
        preset = ROLE_PRESETS[new_role]
        # Actualizar campos del formulario de flujo
        ss.flow_form_desc = preset.get("jd", EVAL_INSTRUCTION)
        ss.flow_form_expected = DEFAULT_EXPECTED_OUTPUT
        ss.flow_form_jd = preset.get("jd", "")

# Callback para actualizar JD en Evaluación LLM
def update_eval_llm_jd_from_preset():
    new_role = ss.eval_llm_role
    if new_role in ROLE_PRESETS:
        preset = ROLE_PRESETS[new_role]
        ss.eval_llm_jd = preset.get("jd", "") # Actualiza el JD para LLM

# Resto de funciones Utils...
SKILL_SYNONYMS = {
  "Excel":["excel","xlsx"], "Gestión documental":["gestión documental","document control"], "Redacción":["redacción","writing"],
  "Facturación":["facturación","billing"], "Caja":["caja","cash"], "SQL":["sql","postgres","mysql"], "Power BI":["power bi"],
  "Tableau":["tableau"], "ETL":["etl"], "KPIs":["kpi","kpis"], "MS Project":["ms project"], "AutoCAD":["autocad"],
  "BIM":["bim","revit"], "Presupuestos":["presupuesto","presupuestos"], "Figma":["figma"], "UX Research":["ux research","investigación de usuarios"],
  "Prototipado":["prototipado","prototype"], "Python":["python"], "Agile":["agile", "scrum", "kanban"]
}
def _normalize(t:str)->str: return re.sub(r"\s+"," ",(t or "")).strip().lower()
def infer_skills(text:str)->set:
  t=_normalize(text); out=set()
  for k,syns in SKILL_SYNONYMS.items():
    if any(s in t for s in syns): out.add(k)
  return out

def score_fit_by_skills(jd_text, must_list, nice_list, cv_text):
  jd_skills = infer_skills(jd_text)
  must=set([m.strip() for m in must_list if m.strip()]) or jd_skills
  nice=set([n.strip() for n in nice_list if n.strip()])-must
  cv=infer_skills(cv_text)
  mm=sorted(list(must&cv)); mn=sorted(list(nice&cv))
  gm=sorted(list(must-cv)); gn=sorted(list(nice-cv))
  extras=sorted(list((cv&(jd_skills|must|nice))-set(mm)-set(mn)))
  cov_m=len(mm)/len(must) if must else 0
  cov_n=len(mn)/len(nice) if nice else 0
  sc=int(round(100*(0.65*cov_m+0.20*cov_n+0.15*min(len(extras),5)/5)))
  return sc, {"matched_must":mm,"matched_nice":mn,"gaps_must":gm,"gaps_nice":gn,"extras":extras,"must_total":len(must),"nice_total":len(nice)}

def build_analysis_text(name,ex):
  ok_m=", ".join(ex["matched_must"]) if ex["matched_must"] else "sin must-have claros"
  ok_n=", ".join(ex["matched_nice"]) if ex["matched_nice"] else "—"
  gaps=", ".join(ex["gaps_must"][:3]) if ex["gaps_must"] else "sin brechas críticas"
  extras=", ".join(ex["extras"][:3]) if ex["extras"] else "—"
  return f"{name} evidencia buen encaje en must-have ({ok_m}). En nice-to-have: {ok_n}. Brechas: {gaps}. Extras: {extras}."

def pdf_viewer_embed(file_bytes: bytes, height=520):
  try:
      b64=base64.b64encode(file_bytes).decode("utf-8")
      st.components.v1.html(
        f'<embed src="data:application/pdf;base64,{b64}" type="application/pdf" width="100%" height="{height}px"/>',
        height=height
      )
  except Exception as e:
      st.error(f"Error al mostrar PDF: {e}")

def _extract_docx_bytes(b: bytes) -> str:
  try:
    with zipfile.ZipFile(io.BytesIO(b)) as z:
      xml = z.read("word/document.xml").decode("utf-8", "ignore")
      text = re.sub(r"<.*?>", " ", xml)
      return re.sub(r"\s+", " ", text).strip()
  except Exception:
    return ""

def extract_text_from_file(uploaded_file) -> str:
  try:
    suffix = Path(uploaded_file.name).suffix.lower()
    file_bytes = uploaded_file.read(); uploaded_file.seek(0)
    if suffix == ".pdf":
      pdf_reader = PdfReader(io.BytesIO(file_bytes))
      text = ""
      for page in pdf_reader.pages:
        try:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
        except Exception as page_e:
             print(f"Error extracting text from PDF page: {page_e}")
      return text
    elif suffix == ".docx":
      return _extract_docx_bytes(file_bytes)
    else:
      return file_bytes.decode("utf-8", errors="ignore")
  except Exception as e:
    print(f"Error extracting text from file {uploaded_file.name}: {e}")
    return ""

def _max_years(t):
  t=t.lower(); years=0
  for m in re.finditer(r'(\d{1,2})\s*(años|year|years)', t):
    years=max(years, int(m.group(1)))
  if years==0 and any(w in t for w in ["años","experiencia","years"]): years=5
  return years

def extract_meta(text):
  t=text.lower(); years=_max_years(t)
  return {"universidad":"—","anios_exp":years,"titulo":"—","ubicacion":"—","ultima_actualizacion":date.today().isoformat()}

def simple_score(cv_text: str, jd: str, keywords: str) -> tuple[int, str]:
  base = 0; reasons = []
  text_low = (cv_text or "").lower()
  kws = [k.strip().lower() for k in (keywords or "").split(",") if k.strip()]
  hits = sum(1 for k in kws if k in text_low)
  if kws:
    base += int((hits/len(kws))*70)
    reasons.append(f"{hits}/{len(kws)} keywords encontradas")
  base = max(0, min(100, base))
  return base, " — ".join(reasons)

def calculate_analytics(candidates):
  if not candidates: return {"avg_fit": 0, "time_to_hire": "—", "source_counts": {}, "funnel_data": pd.DataFrame()}
  jd = ss.get("last_jd_text", ""); preset = ROLE_PRESETS.get(ss.get("last_role", ""), {})
  must, nice = preset.get("must", []), preset.get("nice", [])
  fits = []; source_counts = {}; stage_counts = {stage: 0 for stage in PIPELINE_STAGES}; tths = []
  for c in candidates:
    txt = c.get("_text") or (c.get("_bytes") or b"").decode("utf-8", "ignore")
    f, _ = score_fit_by_skills(jd, must, nice, txt or "")
    fits.append(f)
    source = c.get("source", "Carga Manual"); source_counts[source] = source_counts.get(source, 0) + 1
    stage_counts[c.get("stage", PIPELINE_STAGES[0])] += 1
    if c.get("stage") == "Contratado" and c.get("load_date"):
        try:
            load_date = datetime.fromisoformat(c["load_date"]); hire_date = datetime.now()
            tths.append((hire_date - load_date).days)
        except ValueError:
            print(f"Invalid date format for candidate {c.get('id')}: {c.get('load_date')}")
  avg_fit = round(sum(fits) / len(fits), 1) if fits else 0
  time_to_hire = f"{round(sum(tths) / len(tths), 1)} días" if tths else "—"
  funnel_data = pd.DataFrame({"Fase": PIPELINE_STAGES, "Candidatos": [stage_counts.get(stage, 0) for stage in PIPELINE_STAGES]})
  return {"avg_fit": avg_fit, "time_to_hire": time_to_hire, "funnel_data": funnel_data, "source_counts": source_counts}

def _status_pill(s: str)->str:
  colors = { "Pendiente": "#9AA6B2", "En Proceso": "#0072E3", "Completada": "#10B981", "En Espera": "#FFB700" }
  c = colors.get(s, "#9AA6B2")
  return f'<span class="badge" style="border-color:{c}33;background:{c}14;color:#0A2230">{s}</span>'

def _priority_pill(p: str) -> str:
    p_safe = p if p in TASK_PRIORITIES else "Media"
    return f'<span class="badge priority-{p_safe}">{p_safe}</span>'

def create_task_from_flow(name:str, due_date:date, desc:str, assigned:str="Coordinador RR.HH.", status:str="Pendiente", priority:str="Media", context:dict=None):
  t = {
    "id": str(uuid.uuid4()), "titulo": f"Ejecutar flujo: {name}", "desc": desc or "Tarea generada desde Flujos.",
    "due": due_date.isoformat(), "assigned_to": assigned, "status": status, "priority": priority if priority in TASK_PRIORITIES else "Media",
    "created_at": date.today().isoformat(), "context": context or {}
  }
  if not isinstance(ss.tasks, list): ss.tasks = []
  ss.tasks.insert(0, t); save_tasks(ss.tasks)

def create_manual_task(title, desc, due_date, assigned_to, priority):
    t = {
        "id": str(uuid.uuid4()), "titulo": title, "desc": desc, "due": due_date.isoformat(), "assigned_to": assigned_to,
        "status": "Pendiente", "priority": priority, "created_at": date.today().isoformat(), "context": {"source": "Manual"}
    }
    if not isinstance(ss.tasks, list): ss.tasks = []
    ss.tasks.insert(0, t); save_tasks(ss.tasks)

# =========================================================
# INICIALIZACIÓN DE CANDIDATOS
# =========================================================
if "candidate_init" not in ss:
  initial_candidates = [
    {"Name": "CV_AnaLopez.pdf", "Score": 85, "Role": "Business Analytics", "source": "LinkedIn Jobs"},
    {"Name": "CV_LuisGomez.pdf", "Score": 42, "Role": "Business Analytics", "source": "Computrabajo"},
    {"Name": "CV_MartaDiaz.pdf", "Score": 91, "Role": "Desarrollador/a Backend (Python)", "source": "Indeed"},
    {"Name": "CV_JaviRuiz.pdf", "Score": 30, "Role": "Diseñador/a UX", "source": "laborum.pe"},
  ]
  candidates_list = []
  for i, c in enumerate(initial_candidates):
    c["id"] = f"C{i+1}-{random.randint(1000, 9999)}"
    c["stage"] = PIPELINE_STAGES[random.choice([0, 1, 1, 2, 6])]
    c["load_date"] = (date.today() - timedelta(days=random.randint(5, 30))).isoformat()
    c["_bytes"] = DUMMY_PDF_BYTES
    c["_is_pdf"] = True
    c["_text"] = f"CV de {c['Name']}. Experiencia 5 años. Skills: SQL, Power BI, Python, Excel. Candidato {c['Name']}."
    c["meta"] = extract_meta(c["_text"])
    if c["stage"] == "Descartado": c["Score"] = random.randint(20, 34)
    if c["stage"] == "Contratado": c["Score"] = 95
    candidates_list.append(c)
  ss.candidates = candidates_list
  ss.candidate_init = True

# =========================================================
# LOGIN + SIDEBAR
# =========================================================
def asset_logo_wayki():
  local = Path("assets/logo-wayki.png")
  if local.exists(): return str(local)
  return "https://raw.githubusercontent.com/wayki-consulting/.dummy/main/logo-wayki.png"

def login_screen():
  st.markdown('<div class="login-bg"><div class="login-card">', unsafe_allow_html=True)
  try:
    st.markdown('<div class="login-logo-wrap">', unsafe_allow_html=True)
    st.image(asset_logo_wayki(), width=120)
    st.markdown("</div>", unsafe_allow_html=True)
  except:
    pass
  st.markdown('<div class="login-sub">Acceso a SelektIA</div>', unsafe_allow_html=True)
  with st.form("login_form", clear_on_submit=False):
    u = st.text_input("Usuario")
    p = st.text_input("Contraseña", type="password")
    ok = st.form_submit_button("Ingresar")
    if ok:
      if u in USERS and USERS[u]["password"] == p:
        st.session_state.auth = {"username":u, "role": USERS[u]["role"], "name": USERS[u]["name"]}
        st.success("Bienvenido.")
        st.rerun()
      else:
        st.error("Usuario o contraseña incorrectos.")
  st.markdown("</div></div>", unsafe_allow_html=True)

def require_auth():
  if ss.auth is None:
    login_screen(); return False
  return True

def render_sidebar():
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
      ss.section = "analytics"; ss.pipeline_filter = None

    st.markdown("#### ASISTENTE IA")
    if st.button("Flujos", key="sb_flows"):
      ss.section = "flows"; ss.pipeline_filter = None; ss.editing_flow_id = None; ss.form_loaded_from_edit = False
    if st.button("Agentes", key="sb_agents"):
      ss.section = "agents"; ss.pipeline_filter = None

    st.markdown("#### PROCESO DE SELECCIÓN")
    for txt, sec, target_stage in [
        ("Publicación & Sourcing","publicacion_sourcing", None), ("Puestos","puestos", None),
        ("Evaluación de CVs","eval", None), ("Pipeline de Candidatos","pipeline", None),
        ("Entrevista (Gerencia)","pipeline", "Entrevista Gerencia"), ("Oferta","pipeline", "Oferta"),
        ("Onboarding","pipeline", "Contratado")
    ]:
      if txt in ["Entrevista (Gerencia)", "Oferta", "Onboarding"]:
        if st.button(txt, key=f"sb_{sec}_{txt.replace(' ', '_')}"):
            ss.section = "pipeline"; ss.pipeline_filter = target_stage
      elif txt == "Pipeline de Candidatos":
          if st.button(txt, key=f"sb_{sec}"):
            ss.section = sec; ss.pipeline_filter = None
      else:
        if st.button(txt, key=f"sb_{sec}"):
            ss.section = sec; ss.pipeline_filter = None

    st.markdown("#### TAREAS")
    if st.button("Todas las tareas", key="sb_task_manual"): ss.section = "create_task"
    if st.button("Asignado a mi", key="sb_task_hh"): ss.section = "hh_tasks"
    if st.button("Asignado a mi equipo", key="sb_task_agente"): ss.section = "agent_tasks"

    st.markdown("#### ACCIONES")
    if st.button("Cerrar sesión", key="sb_logout"):
      ss.auth = None; ss.editing_flow_id = None; ss.last_llm_batch = []; ss.form_loaded_from_edit = False; st.rerun()

# =========================================================
# PÁGINAS
# =========================================================
def page_def_carga():
  st.header("Publicación & Sourcing")
  role_names = list(ROLE_PRESETS.keys())

  st.subheader("1. Definición de la Vacante")
  col_puesto, col_id = st.columns(2)
  with col_puesto: puesto = st.selectbox("Puesto", role_names, index=0)
  with col_id: id_puesto = st.text_input("ID de Puesto", value=f"P-{random.randint(1000,9999)}")
  preset = ROLE_PRESETS[puesto]
  jd_text = st.text_area("Descripción / JD", height=180, value=preset["jd"])
  kw_text = st.text_area("Palabras clave (coma separada)", height=100, value=preset["keywords"], help="Usadas por el sistema para el Scoring.")

  ss["last_role"] = puesto; ss["last_jd_text"] = jd_text; ss["last_kw_text"] = kw_text

  st.subheader("2. Carga Manual de CVs")
  files = st.file_uploader("Subir CVs (PDF / DOCX / TXT)", type=["pdf","docx","txt"], accept_multiple_files=True)

  if files and st.button("Procesar CVs y Enviar a Pipeline (Carga Manual)"):
    new_candidates = []
    for f in files:
      b = f.read(); f.seek(0); text = extract_text_from_file(f)
      must_list = [s.strip() for s in (preset.get("must",[]) or []) if s.strip()]
      nice_list = [s.strip() for s in (preset.get("nice",[]) or []) if s.strip()]
      score, exp = score_fit_by_skills(jd_text, must_list, nice_list, text)
      c = {"id": f"C{len(ss.candidates)+len(new_candidates)+1}-{int(datetime.now().timestamp())}",
           "Name": f.name, "Score": score, "Role": puesto, "Role_ID": id_puesto,
           "_bytes": b, "_is_pdf": Path(f.name).suffix.lower()==".pdf", "_text": text,
           "meta": extract_meta(text), "stage": PIPELINE_STAGES[0], "load_date": date.today().isoformat(),
           "_exp": exp, "source": "Carga Manual"}
      new_candidates.append(c)
    for c in new_candidates:
      if c["Score"] < 35: c["stage"] = "Descartado"
      ss.candidates.append(c)
    st.success(f"CVs cargados, analizados y {len(new_candidates)} enviados al Pipeline.")
    st.rerun()

  st.subheader("3. Sourcing desde Portales")
  with st.expander("🔌 Integración con Portales de Empleo"):
    srcs=st.multiselect("Portales", JOB_BOARDS, default=["laborum.pe"], key="portal_srcs")
    qty=st.number_input("Cantidad por portal",1,30,6, key="portal_qty")
    search_q=st.text_input("Búsqueda", value=puesto, key="portal_search_q")
    location=st.text_input("Ubicación", value="Lima, Perú", key="portal_location")
    if st.button("Traer CVs (con Scoring)"):
      new_candidates = []
      for board in srcs:
        for i in range(1,int(qty)+1):
          txt=f"CV extraído de {board} para {puesto}. Skills: SQL, Python, Excel. Años de experiencia: {random.randint(2, 10)}."
          must_list = [s.strip() for s in (preset.get("must",[]) or []) if s.strip()]
          nice_list = [s.strip() for s in (preset.get("nice",[]) or []) if s.strip()]
          score, exp = score_fit_by_skills(jd_text, must_list, nice_list, txt)
          c = {"id": f"C{len(ss.candidates)+len(new_candidates)+1}-{int(datetime.now().timestamp())}",
               "Name":f"{board}_Candidato_{i:02d}.pdf", "Score": score, "Role": puesto, "Role_ID": id_puesto,
               "_bytes": DUMMY_PDF_BYTES, "_is_pdf": True, "_text": txt, "meta": extract_meta(txt),
               "stage": PIPELINE_STAGES[0], "load_date": date.today().isoformat(), "_exp": exp, "source": board}
          new_candidates.append(c)
      for c in new_candidates:
        if c["Score"] < 35: c["stage"] = "Descartado"
        ss.candidates.append(c)
      st.success(f"Importados {len(new_candidates)} CVs de portales. Enviados al Pipeline.")
      st.rerun()

def _llm_setup_credentials():
    """Coloca credenciales desde st.secrets si existen."""
    try:
        if "AZURE_OPENAI_API_KEY" not in os.environ and "llm" in st.secrets and "azure_openai_api_key" in st.secrets["llm"]:
            os.environ["AZURE_OPENAI_API_KEY"] = st.secrets["llm"]["azure_openai_api_key"]
        if "AZURE_OPENAI_ENDPOINT" not in os.environ and "llm" in st.secrets and "azure_openai_endpoint" in st.secrets["llm"]:
            os.environ["AZURE_OPENAI_ENDPOINT"] = st.secrets["llm"]["azure_openai_endpoint"]
    except Exception: pass

def _llm_prompt_for_resume(resume_content: str):
    """Construye un prompt estructurado para extracción JSON."""
    if not _LC_AVAILABLE: return None
    json_object_structure = """{{
        "Name": "Full Name", "Last_position": "The most recent position", "Years_of_Experience": "Number (in years)",
        "English_Level": "Beginner/Intermediate/Advanced/Fluent/Native", "Key_Skills": ["Skill 1", "Skill 2"],
        "Certifications": ["Cert 1"], "Additional_Notes": "Optional details.", "Score": "0-100" }}"""
    system_template = f"Extract structured data from CV content (below) and compute a match percentage vs JD.\nCV Content:\n{resume_content}\n\nReturn a JSON with the structure:\n{json_object_structure}"
    return ChatPromptTemplate.from_messages([
        SystemMessagePromptTemplate.from_template(system_template),
        HumanMessagePromptTemplate.from_template("Job description:\n{job_description}")
    ])

def _extract_with_azure(job_description: str, resume_content: str) -> dict:
    """Intenta usar AzureChatOpenAI."""
    if not _LC_AVAILABLE: return {}
    _llm_setup_credentials()
    try:
        llm = AzureChatOpenAI(
            azure_deployment=st.secrets["llm"]["azure_deployment"], api_version=st.secrets["llm"]["azure_api_version"], temperature=0
        )
        parser = JsonOutputParser(); prompt = _llm_prompt_for_resume(resume_content)
        if prompt is None: return {}
        chain = prompt | llm | parser
        out = chain.invoke({"job_description": job_description})
        return out if isinstance(out, dict) else {}
    except Exception as e:
        st.warning(f"Azure LLM no disponible: {e}"); return {}

def _extract_with_openai(job_description: str, resume_content: str) -> dict:
    """Fallback con ChatOpenAI."""
    if not _LC_AVAILABLE: return {}
    try: api_key = st.secrets["llm"]["openai_api_key"]
    except Exception: return {}
    try:
        chat = ChatOpenAI(temperature=0, model=LLM_IN_USE, openai_api_key=api_key)
        json_object_structure = """{ "Name": "Full Name", "Last_position": "The most recent position", "Years_of_Experience": "Number (in years)",
            "English_Level": "Beginner/Intermediate/Advanced/Fluent/Native", "Key_Skills": ["Skill 1"],
            "Certifications": ["Cert 1"], "Additional_Notes": "Optional details.", "Score": "0-100" }"""
        prompt = f"Extract structured JSON from the following CV and compute a 0-100 match vs the JD.\n\nJob description:\n{job_description}\n\nCV Content:\n{resume_content}\n\nReturn JSON with this structure:\n{json_object_structure}"
        resp = chat.invoke(prompt)
        txt = resp.content.strip().replace('```json','').replace('```','')
        return json.loads(txt)
    except Exception as e:
        st.warning(f"OpenAI LLM no disponible: {e}"); return {}

def _create_llm_bar(df: pd.DataFrame):
    fig = px.bar(df, x='file_name', y='Score', text='Score', title='Comparativa de Puntajes (LLM)', color_discrete_sequence=PLOTLY_GREEN_SEQUENCE)
    for _, row in df.iterrows():
        fig.add_annotation(x=row['file_name'], y=row['Score'], text=row.get('Name',''), showarrow=True, arrowhead=1, ax=0, ay=-20)
    fig.update_layout(plot_bgcolor="#FFFFFF", paper_bgcolor="rgba(0,0,0,0)", font=dict(color=TITLE_DARK))
    return fig

def _results_to_df(results: list) -> pd.DataFrame:
    if not results: return pd.DataFrame()
    df = pd.DataFrame(results).copy()
    if "Score" in df.columns:
        try: df["Score"] = df["Score"].astype(int)
        except: pass
        df = df.sort_values(by="Score", ascending=False)
    return df

def page_puestos():
  st.header("Puestos")
  df_pos = ss.positions.copy()
  df_pos["Time to Hire (promedio)"] = df_pos["Días Abierto"].apply(lambda d: f"{d+random.randint(10, 40)} días" if d < 30 else f"{d} días")
  st.dataframe(
    df_pos[["Puesto","Días Abierto","Time to Hire (promedio)","Leads","Nuevos","Recruiter Screen","HM Screen",
            "Entrevista Telefónica","Entrevista Presencial","Ubicación","Hiring Manager","Estado","ID"]]
    .sort_values(["Estado","Días Abierto","Leads"], ascending=[True,True,False]),
    use_container_width=True, height=380, hide_index=True
  )
  st.subheader("Candidatos por Puesto")
  pos_list = df_pos["Puesto"].tolist()
  selected_pos = st.selectbox("Selecciona un puesto para ver el Pipeline asociado", pos_list)
  if selected_pos:
    candidates_for_pos = [c for c in ss.candidates if c.get("Role") == selected_pos]
    if candidates_for_pos:
      df_cand = pd.DataFrame(candidates_for_pos)
      st.dataframe(df_cand[["Name", "Score", "stage", "load_date"]].rename(columns={"Name":"Candidato", "Score":"Fit", "stage":"Fase"}),
                    use_container_width=True, hide_index=True)
    else: st.info(f"No hay candidatos activos para el puesto **{selected_pos}**.")

def page_eval():
    st.header("Resultados de evaluación")

    with st.expander("🤖 Evaluación asistida por LLM (Azure/OpenAI)", expanded=True):
        
        # --- Selector de Puesto Objetivo (Nuevo) ---
        role_options = list(ROLE_PRESETS.keys())
        try:
            role_index = role_options.index(ss.eval_llm_role)
        except ValueError:
            role_index = 0 # Fallback
            ss.eval_llm_role = role_options[0] # Asegurar que el estado sea válido
            ss.eval_llm_jd = ROLE_PRESETS[ss.eval_llm_role].get("jd", "") # Actualizar JD

        st.selectbox("Puesto objetivo", 
                     role_options, 
                     index=role_index,
                     key="eval_llm_role", # Clave para el estado
                     on_change=update_eval_llm_jd_from_preset) # Callback para actualizar JD

        # --- Área de Texto del JD (Ahora usa estado) ---
        jd_llm = st.text_area("Job Description para el LLM", 
                              value=ss.eval_llm_jd, # Bindeado al estado
                              key="eval_llm_jd_input", # Clave del widget
                              height=120)
                              
        # --- Resto del formulario ---
        up = st.file_uploader("Sube CVs en PDF para evaluarlos con el LLM", type=["pdf"], accept_multiple_files=True, key="pdf_llm")
        
        c1, c2 = st.columns([1, 0.4])
        with c1:
            run_llm = st.button("Ejecutar evaluación LLM", key="btn_llm_eval")
        with c2:
            st.button("🗑️ Limpiar Historial de Evaluaciones", key="btn_clear_evals", 
                      help="Borra todas las evaluaciones guardadas en data/evaluations.json",
                      on_click=lambda: (
                          ss.update(all_evaluations=[], last_llm_batch=[]),
                          save_evals([]),
                          st.success("Historial de evaluaciones limpiado.")
                      ))

        if run_llm and up:
            if not _LC_AVAILABLE:
                st.warning("Paquetes LangChain/OpenAI no disponibles. Se omite evaluación.")
                ss.last_llm_batch = []
            
            results_with_bytes = []
            new_meta_to_save = []
            # Usar el JD del estado (ss.eval_llm_jd) que fue actualizado por el selectbox
            current_jd_for_eval = ss.eval_llm_jd 
            
            for f in up:
                f_bytes = f.read(); f.seek(0); text = ""
                try: # Extracción de texto
                    if _LC_AVAILABLE:
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                            tmp.write(f_bytes); tmp.flush(); loader = PyPDFLoader(tmp.name); pages = loader.load()
                            text = "\n".join([p.page_content for p in pages])
                    else:
                        reader = PdfReader(io.BytesIO(f_bytes)); text = "\n".join([(p.extract_text() or "") for p in reader.pages])
                except Exception as e:
                    st.error(f"No se pudo leer {f.name}: {e}"); continue

                # Pasar el JD actual al LLM
                meta = _extract_with_azure(current_jd_for_eval, text) or _extract_with_openai(current_jd_for_eval, text)
                if not meta:
                    meta = {"Name":"—","Years_of_Experience":"—","English_Level":"—","Key_Skills":[],"Certifications":[],"Additional_Notes":"—","Score":0}
                meta["file_name"] = f.name
                
                results_with_bytes.append({"meta": meta, "_bytes": f_bytes})
                new_meta_to_save.append(meta)

            ss.last_llm_batch = results_with_bytes
            ss.all_evaluations.extend(new_meta_to_save)
            save_evals(ss.all_evaluations)
            st.success(f"Evaluación completada. {len(new_meta_to_save)} resultados guardados.")
            st.rerun()

        if ss.last_llm_batch:
            df_llm = _results_to_df([r["meta"] for r in ss.last_llm_batch])
            if not df_llm.empty:
                st.subheader("Resultados de la Última Evaluación")
                st.dataframe(df_llm, use_container_width=True, hide_index=True)
                st.plotly_chart(_create_llm_bar(df_llm), use_container_width=True)
        else: st.info("Sube archivos y ejecuta la evaluación para ver resultados.")
        
        st.markdown(f"**Total de evaluaciones en historial:** `{len(ss.all_evaluations)}`")
            
    if ss.last_llm_batch:
        st.markdown("---"); st.subheader("Visualizar CV (Último Batch)")
        file_names = [r["meta"]["file_name"] for r in ss.last_llm_batch]
        selected_file_name = st.selectbox("Selecciona un CV para visualizar", file_names)
        if selected_file_name:
            selected_file_data = next((r for r in ss.last_llm_batch if r["meta"]["file_name"] == selected_file_name), None)
            if selected_file_data and selected_file_data.get("_bytes"):
                pdf_viewer_embed(selected_file_data["_bytes"], height=500)
            else: st.error("No se encontró el PDF correspondiente.")

# ... (El resto de las funciones page_*, _extract_*, etc. permanecen igual que en la versión anterior) ...

# ===================== FLUJOS (Se mantiene igual que la versión anterior) =====================
def page_flows():
  st.header("Flujos")
  vista_como = ss.auth["role"]
  puede_aprobar = vista_como in ("Supervisor","Administrador")

  left, right = st.columns([0.9, 1.1])
  with left:
    st.subheader("Mis flujos")
    if not ss.workflows:
      st.info("No hay flujos aún. Crea uno a la derecha.")
    else:
      rows = []
      for wf in ss.workflows:
        ag_label = "—"; ai = wf.get("agent_idx",-1)
        if 0 <= ai < len(ss.agents):
          ag_label = ss.agents[ai].get("rol","Agente")
        rows.append({"ID": wf["id"], "Nombre": wf["name"], "Puesto": wf.get("role","—"),
                     "Agente": ag_label, "Estado": wf.get("status","Borrador"),
                     "Programado": wf.get("schedule_at","—")})
      df = pd.DataFrame(rows)
      st.dataframe(df, use_container_width=True, height=260)
      
      if rows:
        sel_options = [r["ID"] for r in rows]
        sel_format_func = lambda x: next((r["Nombre"] for r in rows if r["ID"]==x), x)
        
        try: sel_index = sel_options.index(ss.editing_flow_id)
        except ValueError: sel_index = 0; ss.editing_flow_id = None 

        sel = st.selectbox("Selecciona un flujo para ver o editar", sel_options,
                           index=sel_index, format_func=sel_format_func, key="flow_selector")

        if st.button("Cargar Flujo para Editar", key="load_flow_edit"):
            ss.editing_flow_id = sel
            ss.form_loaded_from_edit = False 
            st.rerun()

        wf = next((w for w in ss.workflows if w["id"]==sel), None)
        if wf:
          c1,c2,c3 = st.columns(3)
          with c1:
            if st.button("🧬 Duplicar"):
              clone = dict(wf); clone["id"] = f"WF-{int(datetime.now().timestamp())}"; clone["status"]="Borrador"; clone["approved_by"]=""; clone["approved_at"]=""; clone["schedule_at"]=""
              ss.workflows.insert(0, clone); save_workflows(ss.workflows); st.success("Flujo duplicado.")
              ss.editing_flow_id = None; ss.form_loaded_from_edit = False; st.rerun()
          with c2:
            if st.button("🗑 Eliminar"):
              ss.workflows = [w for w in ss.workflows if w["id"]!=wf["id"]]; save_workflows(ss.workflows); st.success("Flujo eliminado.")
              if ss.editing_flow_id == wf["id"]: ss.editing_flow_id = None; ss.form_loaded_from_edit = False
              st.rerun()
          with c3:
            st.markdown(f"<div class='badge'>Estado: <b>{wf.get('status','Borrador')}</b></div>", unsafe_allow_html=True)
            if wf.get("status")=="Pendiente de aprobación" and puede_aprobar:
              a1,a2 = st.columns(2)
              with a1:
                if st.button("✅ Aprobar"):
                  wf["status"]="Aprobado"; wf["approved_by"]=vista_como; wf["approved_at"]=datetime.now().isoformat(); save_workflows(ss.workflows); st.success("Aprobado."); st.rerun()
              with a2:
                if st.button("❌ Rechazar"):
                  wf["status"]="Rechazado"; wf["approved_by"]=vista_como; wf["approved_at"]=datetime.now().isoformat(); save_workflows(ss.workflows); st.warning("Rechazado."); st.rerun()

  with right:
    editing_wf = None
    if ss.editing_flow_id:
        editing_wf = next((w for w in ss.workflows if w["id"] == ss.editing_flow_id), None)
        if editing_wf and not ss.form_loaded_from_edit:
            ss.flow_form_name = editing_wf.get("name", "Analizar CV")
            ss.flow_form_role = editing_wf.get("role", DEFAULT_FLOW_ROLE)
            ss.flow_form_desc = editing_wf.get("description", EVAL_INSTRUCTION)
            ss.flow_form_expected = editing_wf.get("expected_output", DEFAULT_EXPECTED_OUTPUT)
            ss.flow_form_jd = editing_wf.get("jd_text", "")
            ss.flow_form_agent_idx = editing_wf.get("agent_idx", 0)
            ss.form_loaded_from_edit = True
    
    st.subheader("Crear Flujo" if not editing_wf else f"Editando Flujo: {editing_wf.get('name')}")
    
    if editing_wf:
        if st.button("✖ Cancelar Edición"):
            ss.editing_flow_id = None; ss.form_loaded_from_edit = False
            ss.flow_form_name = "Analizar CV"; ss.flow_form_role = DEFAULT_FLOW_ROLE
            ss.flow_form_desc = ROLE_PRESETS[DEFAULT_FLOW_ROLE].get("jd", EVAL_INSTRUCTION)
            ss.flow_form_expected = DEFAULT_EXPECTED_OUTPUT
            ss.flow_form_jd = ROLE_PRESETS[DEFAULT_FLOW_ROLE].get("jd", "")
            ss.flow_form_agent_idx = 0; st.rerun()

    with st.form("wf_form"):
      st.markdown("<div class='badge'>Task · Describe la tarea</div>", unsafe_allow_html=True)
      name = st.text_input("Name*", value=ss.flow_form_name, key="flow_form_name_input")
      role_options = list(ROLE_PRESETS.keys())
      try: role_index = role_options.index(ss.flow_form_role)
      except ValueError: role_index = role_options.index(DEFAULT_FLOW_ROLE)
      role = st.selectbox("Puesto objetivo", role_options, index=role_index, key="flow_form_role", on_change=update_flow_fields_from_preset)
      desc = st.text_area("Description*", value=ss.flow_form_desc, key="flow_form_desc_input", height=110)
      expected = st.text_area("Expected output*", value=ss.flow_form_expected, key="flow_form_expected_input", height=80)

      st.markdown("**Job Description (elige una opción)**")
      jd_text = st.text_area("JD en texto", value=ss.flow_form_jd, key="flow_form_jd_input", height=140)
      jd_file = st.file_uploader("...o sube/reemplaza JD (PDF/TXT/DOCX)", type=["pdf","txt","docx"], key="wf_jd_file")
      jd_from_file = ""
      if jd_file is not None:
        jd_from_file = extract_text_from_file(jd_file)
        st.caption("Vista previa del JD extraído:"); st.text_area("Preview", jd_from_file[:4000], height=160)

      st.markdown("---"); st.markdown("<div class='badge'>Staff in charge · Agente asignado</div>", unsafe_allow_html=True)
      if ss.agents:
        agent_opts = [f"{i} — {a.get('rol','Agente')} ({a.get('llm_model',LLM_IN_USE)})" for i,a in enumerate(ss.agents)]
        agent_idx_val = ss.flow_form_agent_idx
        if not (0 <= agent_idx_val < len(ss.agents)): agent_idx_val = 0
        agent_pick = st.selectbox("Asigna un agente", agent_opts, index=agent_idx_val, key="flow_form_agent_idx_input")
        agent_idx = int(agent_pick.split(" — ")[0])
      else: st.info("No hay agentes."); agent_idx = -1

      st.markdown("---"); st.markdown("<div class='badge'>Guardar · Aprobación y programación</div>", unsafe_allow_html=True)
      run_date = st.date_input("Fecha de ejecución", value=date.today()+timedelta(days=1))
      run_time = st.time_input("Hora de ejecución", value=datetime.now().time().replace(second=0, microsecond=0))
      
      if editing_wf:
          update_flow = st.form_submit_button("💾 Actualizar Flujo")
          save_draft = False; send_approval = False; schedule = False
      else:
          update_flow = False
          col_a, col_b, col_c = st.columns(3)
          save_draft    = col_a.form_submit_button("💾 Guardar borrador")
          send_approval = col_b.form_submit_button("📝 Enviar a aprobación")
          schedule      = col_c.form_submit_button("📅 Guardar y Programar")

      if save_draft or send_approval or schedule or update_flow:
        jd_final = jd_from_file if jd_from_file.strip() else ss.flow_form_jd_input
        if not jd_final.strip(): st.error("Debes proporcionar un JD (texto o archivo).")
        elif agent_idx < 0:      st.error("Debes asignar un agente.")
        else:
          wf_data = {
              "name": ss.flow_form_name_input, "role": ss.flow_form_role, "description": ss.flow_form_desc_input,
              "expected_output": ss.flow_form_expected_input, "jd_text": jd_final[:200000], "agent_idx": agent_idx
          }
          if update_flow:
              editing_wf.update(wf_data); editing_wf["status"] = "Borrador" 
              save_workflows(ss.workflows); st.success("Flujo actualizado.")
              ss.editing_flow_id = None; ss.form_loaded_from_edit = False; st.rerun()
          else:
              wf = wf_data.copy(); wf.update({"id": f"WF-{int(datetime.now().timestamp())}", "created_at": datetime.now().isoformat(), "status": "Borrador", "approved_by": "", "approved_at": "", "schedule_at": ""})
              if send_approval: wf["status"] = "Pendiente de aprobación"; st.success("Flujo enviado a aprobación.")
              if schedule:
                if puede_aprobar: wf["status"]="Programado"; wf["schedule_at"]=f"{run_date} {run_time.strftime('%H:%M')}"; st.success("Flujo programado.")
                else: wf["status"]="Pendiente de aprobación"; wf["schedule_at"]=f"{run_date} {run_time.strftime('%H:%M')}"; st.info("Pendiente de aprobación.")
              if save_draft: st.success("Borrador guardado.")
              ss.workflows.insert(0, wf); save_workflows(ss.workflows); ss.form_loaded_from_edit = False; st.rerun()

# ===================== ANALYTICS, AGENTES, TODAS LAS TAREAS, etc... =====================
# (El resto de las funciones page_* permanecen iguales que en la versión anterior)
# page_analytics(), page_agents(), page_create_task(), etc.

# --- Pegar aquí el resto de las funciones page_* desde la versión anterior ---
# page_analytics, page_agents, page_create_task, page_hh_tasks, page_agent_tasks,
# page_pipeline, page_interview, page_offer, page_onboarding

# ... (código omitido por brevedad, es el mismo que en la respuesta anterior) ...

# =========================================================
# ROUTER
# =========================================================
ROUTES = {
  "publicacion_sourcing": page_def_carga, "puestos": page_puestos, "eval": page_eval,
  "pipeline": page_pipeline, "interview": page_interview, "offer": page_offer,
  "onboarding": page_onboarding, "hh_tasks": page_hh_tasks, "agents": page_agents,
  "flows": page_flows, "agent_tasks": page_agent_tasks, "analytics": page_analytics,
  "create_task": page_create_task,
}

# =========================================================
# APP
# =========================================================
if __name__ == "__main__":
    if require_auth():
        render_sidebar()
        ROUTES.get(ss.section, page_def_carga)()
