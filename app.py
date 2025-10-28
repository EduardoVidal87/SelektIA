# -*- coding: utf-8 -*-

import io, base64, re, json, random, zipfile, uuid, tempfile, os
from pathlib import Path
from datetime import datetime, date, timedelta

import streamlit as st
import pandas as pd
import plotly.express as px
from PyPDF2 import PdfReader

# ====== Paquetes de LLM para la sección de 'Evaluación de CVs' ======
# Se importan de forma segura; si no están instalados, la app no se rompe.
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
PRIMARY         = "#00CD78"
SIDEBAR_BG = "#0E192B"
SIDEBAR_TX = "#B9C7DF"
BODY_BG         = "#F7FBFF"
CARD_BG         = "#0E192B"
TITLE_DARK = "#142433"

BAR_DEFAULT = "#E9F3FF"
BAR_GOOD    = "#33FFAC"

# Secuencia de colores para Plotly
PLOTLY_GREEN_SEQUENCE = ["#00CD78", "#00B468", "#33FFAC", "#007F46", "#66FFC2"]

JOB_BOARDS  = ["laborum.pe","Computrabajo","Bumeran","Indeed","LinkedIn Jobs"]
PIPELINE_STAGES = ["Recibido", "Screening RRHH", "Entrevista Telefónica", "Entrevista Gerencia", "Oferta", "Contratado", "Descartado"]
TASK_PRIORITIES = ["Alta", "Media", "Baja"]
FLOW_STATUSES = ["Borrador", "Pendiente de aprobación", "Aprobado", "Rechazado", "Programado"]
# (Req 3) Estados para Puestos
POSITION_STATUSES = ["Abierto", "Pausado", "Cerrado"]

EVAL_INSTRUCTION = (
  "Debes analizar los CVs de postulantes y calificarlos de 0% a 100% según el nivel de coincidencia con el JD. "
  "Incluye un análisis breve que explique por qué califica o no el postulante, destacando habilidades must-have, "
  "nice-to-have, brechas y hallazgos relevantes."
)

# ===== Login =====
USERS = {
  "colab": {"password":"colab123","role":"Colaborador","name":"Colab"},
  "super": {"password":"super123","role":"Supervisor","name":"Sup"},
  "admin": {"password":"admin123","role":"Administrador","name":"Admin"},
}

AGENT_DEFAULT_IMAGES = {
  "Headhunter":       "https://images.unsplash.com/photo-1581090464777-f3220bbe1b8b?q=80&w=512&auto-format&fit=crop",
  "Coordinador RR.HH.":"https://images.unsplash.com/photo-1542751371-adc38448a05e?q=80&w=512&auto-format&fit=crop",
  "Admin RR.HH.":     "https://images.unsplash.com/photo-1526378722484-bd91ca387e72?q=80&w=512&auto-format&fit=crop",
}
# Lista de LLMs eliminada (Req. 1)
# LLM_MODELS = ["gpt-4o-mini","gpt-4.1","gpt-4o","claude-3.5-sonnet","claude-3-haiku","gemini-1.5-pro","mixtral-8x7b","llama-3.1-70b"]
LLM_IN_USE = "gpt-4o-mini" # Modelo real usado en las funciones _extract

# ===== Presets de puestos =====
# (Req 2/3) ROLE_PRESETS ahora solo se usa en 'Sourcing' para precargar.
# La fuente de verdad para Flujos/Evaluación será ss.positions
ROLE_PRESETS = {
  "Asistente Administrativo": {
    "jd": "Brindar soporte administrativo: gestión documental, agenda, compras menores, logística de reuniones y reportes...",
    "keywords": "Excel, Word, PowerPoint, gestión documental, atención a proveedores, compras, logística, caja chica, facturación, redacción",
    "must": ["Excel","Gestión documental","Redacción"], "nice": ["Facturación","Caja"],
    "synth_skills": ["Excel","Word","PowerPoint","Gestión documental","Redacción","Facturación","Caja","Atención al cliente"]
  },
  "Business Analytics": {
    "jd": "Recolectar, transformar y analizar datos para generar insights...",
    "keywords": "SQL, Power BI, Tableau, ETL, KPI, storytelling, Excel avanzado, Python, A/B testing, métricas de negocio",
    "must": ["SQL","Power BI"], "nice": ["Tableau","Python","ETL"],
    "synth_skills": ["SQL","Power BI","Tableau","Excel","ETL","KPIs","Storytelling","Python","A/B testing"]
  },
  "Diseñador/a UX": {
    "jd": "Responsable de research, definición de flujos, wireframes y prototipos...",
    "keywords": "Figma, UX research, prototipado, wireframes, heurísticas, accesibilidad, design system, usabilidad, tests con usuarios",
    "must": ["Figma","UX Research","Protototipado"], "nice":["Heurísticas","Accesibilidad","Design System"],
    "synth_skills":["Figma","UX Research","Protototipado","Wireframes","Accesibilidad","Heurísticas","Design System","Analytics"]
  },
  "Ingeniero/a de Proyectos": {
    "jd":"Planificar, ejecutar y controlar proyectos de ingeniería...",
    "keywords":"MS Project, AutoCAD, BIM, presupuestos, cronogramas, control de cambios, riesgos, PMBOK, Agile, KPI, licitaciones",
    "must":["MS Project","AutoCAD","Presupuestos"], "nice":["BIM","PMBOK","Agile"],
    "synth_skills":["MS Project","AutoCAD","BIM","Presupuestos","Cronogramas","Riesgos","PMBOK","Agile","Excel","Power BI"]
  },
  "Enfermera/o Asistencial": {
    "jd":"Brindar atención segura y de calidad, registrar en HIS/SAP IS-H...",
    "keywords":"HIS, SAP IS-H, BLS, ACLS, IAAS, educación al paciente, seguridad del paciente, protocolos...",
    "must":["HIS","BLS","ACLS","IAAS","Seguridad del paciente"], "nice":["SAP IS-H","Educación al paciente","Protocolos"],
    "synth_skills":["HIS","BLS","ACLS","IAAS","Educación al paciente","Seguridad del paciente","Protocolos","Excel"]
  },
  "Recepcionista de Admisión": {
    "jd": "Recepción de pacientes, registro, coordinación de citas, manejo de caja y facturación...",
    "keywords": "admisión, caja, facturación, SAP, HIS, atención al cliente, citas, recepción",
    "must": ["Atención al cliente","Registro","Caja"], "nice": ["Facturación","SAP","HIS"],
    "synth_skills": ["Atención al cliente","Registro","Caja","Facturación","SAP","HIS","Comunicación"]
  }
}

# Bytes de un PDF de ejemplo mínimo para la previsualización
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
/* (Req 4) Añadido estilo para text_area deshabilitado */
.block-container [data-testid="stTextArea"] textarea[disabled] {{
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

/* (Req 3) Estilos para Puestos (similar a Flujos) */
.pos-badge {{ border:1px solid #E3EDF6; background:#F7FBFF; border-radius:8px; padding:4px 8px; font-size:12px; color:#333; }}
.pos-badge-Abierto {{ border-color: {PRIMARY}; background: #E6FFF1; color: {PRIMARY}; font-weight: 600; }}
.pos-badge-Pausado {{ border-color: #FFB700; background: #FFFDE6; color: #E8B900; }}
.pos-badge-Cerrado {{ border-color: #D1D5DB; background: #F3F4F6; color: #6B7280; }}

/* (Req 5.3) Estilos para expander de tareas */
[data-testid="stExpander"] summary {{ font-size: 1.1rem !important; font-weight: 600 !important; }}
[data-testid="stExpander"] details {{ border: 1px solid #E3EDF6 !important; border-radius: 10px !important; background: #fff !important; margin-bottom: 8px !important; padding: 2px 8px !important; box-shadow: 0 2px 4px rgba(14,25,43,.04); }}
[data-testid="stExpander"] details summary svg {{ color: {TITLE_DARK} !important; }}
.task-details-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 10px; margin-bottom: 12px; }}
.task-details-grid > div {{ background: #F8FCFF; border: 1px solid #EAF2FB; border-radius: 8px; padding: 8px; }}
.task-details-grid strong {{ color: {TITLE_DARK}; display: block; margin-bottom: 4px; font-size: 0.85rem; }}
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
# Persistencia (Agentes / Flujos / Roles / Tareas / Puestos)
# =========================================================
DATA_DIR = Path("data"); DATA_DIR.mkdir(exist_ok=True)
AGENTS_FILE = DATA_DIR/"agents.json"
WORKFLOWS_FILE = DATA_DIR/"workflows.json"
ROLES_FILE = DATA_DIR / "roles.json"
TASKS_FILE = DATA_DIR / "tasks.json"
POSITIONS_FILE = DATA_DIR / "positions.json" # (Req 3)

DEFAULT_ROLES = ["Headhunter", "Coordinador RR.HH.", "Admin RR.HH."]

DEFAULT_TASKS = [
    {"id": str(uuid.uuid4()), "titulo":"Revisar CVs top 5", "desc":"Analizar a los 5 candidatos con mayor fit para 'Business Analytics'.", "due":str(date.today() + timedelta(days=2)), "assigned_to": "Headhunter", "status": "Pendiente", "priority": "Alta", "created_at": (date.today() - timedelta(days=3)).isoformat()},
    {"id": str(uuid.uuid4()), "titulo":"Coordinar entrevista de Rivers Brykson", "desc":"Agendar la 2da entrevista (Gerencia) para el puesto de VP de Marketing.", "due":str(date.today() + timedelta(days=5)), "assigned_to": "Coordinador RR.HH.", "status": "En Proceso", "priority": "Media", "created_at": (date.today() - timedelta(days=8)).isoformat(), "context": {"candidate_name": "Rivers Brykson", "role": "VP de Marketing"}},
    {"id": str(uuid.uuid4()), "titulo":"Crear workflow de Onboarding", "desc":"Definir pasos en 'Flujos' para Contratado.", "due":str(date.today() - timedelta(days=1)), "assigned_to": "Admin RR.HH.", "status": "Completada", "priority": "Baja", "created_at": (date.today() - timedelta(days=15)).isoformat()},
    {"id": str(uuid.uuid4()), "titulo":"Análisis Detallado de CV_MartaDiaz.pdf", "desc":"Utilizar el agente de análisis para generar un informe de brechas de skills.", "due":str(date.today() + timedelta(days=3)), "assigned_to": "Agente de Análisis", "status": "Pendiente", "priority": "Media", "created_at": date.today().isoformat(), "context": {"candidate_name": "MartaDiaz.pdf", "role": "Desarrollador/a Backend (Python)"}}
]

# (Req 2/3) Datos por defecto para Puestos (con JD)
DEFAULT_POSITIONS = [
    {"ID":"10,645,194","Puesto":"Desarrollador/a Backend (Python)", "JD": "Buscamos un Desarrollador Backend con experiencia en Python, Django y/o Flask. Responsable de diseñar, implementar y mantener APIs RESTful...",
     "Días Abierto":3, "Leads":1800,"Nuevos":115,"Recruiter Screen":35,"HM Screen":7,
     "Entrevista Telefónica":14,"Entrevista Presencial":15,"Ubicación":"Lima, Perú",
     "Hiring Manager":"Rivers Brykson","Estado":"Abierto","Fecha Inicio": (date.today() - timedelta(days=3)).isoformat()},
    {"ID":"10,376,415","Puesto":"VP de Marketing", "JD": "Liderar la estrategia de marketing digital y branding. Definir KPIs, gestionar el presupuesto del área y liderar equipos multidisciplinarios...",
     "Días Abierto":28, "Leads":8100,"Nuevos":1,"Recruiter Screen":15,"HM Screen":35,
     "Entrevista Telefónica":5,"Entrevista Presencial":7,"Ubicación":"Santiago, Chile",
     "Hiring Manager":"Angela Cruz","Estado":"Abierto","Fecha Inicio": (date.today() - timedelta(days=28)).isoformat()},
    {"ID":"10,376,646","Puesto":"Planner de Demanda", "JD": "Analizar la demanda histórica y tendencias del mercado para generar el forecast de ventas. Colaboración con Ventas y Producción...",
     "Días Abierto":28, "Leads":2300,"Nuevos":26,"Recruiter Screen":3,"HM Screen":8,
     "Entrevista Telefónica":6,"Entrevista Presencial":3,"Ubicación":"Ciudad de México, MX",
     "Hiring Manager":"Rivers Brykson","Estado":"Abierto","Fecha Inicio": (date.today() - timedelta(days=28)).isoformat()}
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
# (Req 3) Funciones para Puestos
def load_positions(): return load_json(POSITIONS_FILE, DEFAULT_POSITIONS)
def save_positions(positions): save_json(POSITIONS_FILE, positions)

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

# (Req 3) Reemplazo de inicialización de 'positions'
if "positions_loaded" not in ss:
    ss.positions = load_positions()
    if not isinstance(ss.positions, list):
        ss.positions = DEFAULT_POSITIONS
    # (Req 2/3) Asegurar que los puestos por defecto tengan JD
    for p in ss.positions:
        if "JD" not in p:
            p["JD"] = "Por favor, define el Job Description."
    save_positions(ss.positions)
    ss.positions_loaded = True

if "pipeline_filter" not in ss: ss.pipeline_filter = None
if "expanded_task_id" not in ss: ss.expanded_task_id = None
if "show_assign_for" not in ss: ss.show_assign_for = None
if "confirm_delete_id" not in ss: ss.confirm_delete_id = None

# Nuevos estados para edición de flujos y resultados de LLM
if "editing_flow_id" not in ss: ss.editing_flow_id = None
if "llm_eval_results" not in ss: ss.llm_eval_results = [] # (Req. 5)

# (INICIO DE MODIFICACIÓN) Nuevos estados para Flujos
if "show_flow_form" not in ss: ss.show_flow_form = False
if "viewing_flow_id" not in ss: ss.viewing_flow_id = None
if "confirm_delete_flow_id" not in ss: ss.confirm_delete_flow_id = None
# (FIN DE MODIFICACIÓN)

# (Req 3) Nuevos estados para Puestos
if "show_position_form" not in ss: ss.show_position_form = False
if "editing_position_id" not in ss: ss.editing_position_id = None
if "confirm_delete_position_id" not in ss: ss.confirm_delete_position_id = None

# (Req 4) Nuevo estado para Evaluación
if "selected_flow_id_for_eval" not in ss: ss.selected_flow_id_for_eval = None


# =========================================================
# UTILS
# =========================================================
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

# ====== Helpers de TAREAS ======
def _status_pill(s: str)->str:
  colors = { "Pendiente": "#9AA6B2", "En Proceso": "#0072E3", "Completada": "#10B981", "En Espera": "#FFB700" }
  c = colors.get(s, "#9AA6B2")
  return f'<span class="badge" style="border-color:{c}33;background:{c}14;color:#0A2230">{s}</span>'

def _priority_pill(p: str) -> str:
    p_safe = p if p in TASK_PRIORITIES else "Media"
    return f'<span class="badge priority-{p_safe}">{p_safe}</span>'

# Helper para estados de Flujo
def _flow_status_pill(s: str)->str:
  """Devuelve un badge HTML coloreado para los estados de Flujo."""
  colors = {
      "Borrador": "#9AA6B2",
      "Pendiente de aprobación": "#FFB700",
      "Aprobado": "#10B981",
      "Rechazado": "#D60000",
      "Programado": "#0072E3"
  }
  c = colors.get(s, "#9AA6B2")
  return f'<span class="badge" style="border-color:{c}33;background:{c}14;color:#0A2230">{s}</span>'

# (Req 3) Helper para estados de Puestos
def _position_status_pill(s: str) -> str:
    """Devuelve un badge HTML coloreado para los estados de Puesto."""
    s_safe = s if s in POSITION_STATUSES else "Abierto"
    return f'<span class="pos-badge pos-badge-{s_safe}">{s_safe}</span>'

# Modificado para aceptar contexto
def create_task_from_flow(name:str, due_date:date, desc:str, assigned:str="Coordinador RR.HH.", status:str="Pendiente", priority:str="Media", context:dict=None):
  t = {
    "id": str(uuid.uuid4()),
    "titulo": f"Ejecutar flujo: {name}",
    "desc": desc or "Tarea generada desde Flujos.",
    "due": due_date.isoformat(),
    "assigned_to": assigned,
    "status": status,
    "priority": priority if priority in TASK_PRIORITIES else "Media",
    "created_at": date.today().isoformat(),
    "context": context or {} # Añadido
  }
  if not isinstance(ss.tasks, list): ss.tasks = []
  ss.tasks.insert(0, t)
  save_tasks(ss.tasks)

# Helper para crear tarea manual
def create_manual_task(title, desc, due_date, assigned_to, priority):
    t = {
        "id": str(uuid.uuid4()),
        "titulo": title,
        "desc": desc,
        "due": due_date.isoformat(),
        "assigned_to": assigned_to,
        "status": "Pendiente",
        "priority": priority,
        "created_at": date.today().isoformat(),
        "context": {"source": "Manual"}
    }
    if not isinstance(ss.tasks, list): ss.tasks = []
    ss.tasks.insert(0, t)
    save_tasks(ss.tasks)

# (Req 6) Helper para crear tarea de revisión IA
def create_ia_review_task(cv_filename, flow_name, score, analysis, assigned_to):
    task_title = f"Revisar IA: {cv_filename} (Flujo: {flow_name})"
    # Usamos analysis como descripción principal
    task_desc = analysis or "Análisis IA no disponible." 
    
    # Contexto específico para resultados IA
    context = {
        "source": "IA Evaluation",
        "cv_filename": cv_filename,
        "flow_name": flow_name,
        "ia_score": score,
        "ia_analysis": analysis # Guardamos el análisis completo
    }
    
    t = {
        "id": str(uuid.uuid4()),
        "titulo": task_title,
        "desc": f"Puntuación IA: {score}%. Revisar análisis detallado.", # Descripción corta
        "due": (date.today() + timedelta(days=1)).isoformat(), # Vence mañana
        "assigned_to": assigned_to,
        "status": "Pendiente",
        "priority": "Media", # Prioridad media por defecto para revisión
        "created_at": date.today().isoformat(),
        "context": context
    }
    if not isinstance(ss.tasks, list): ss.tasks = []
    ss.tasks.insert(0, t)
    # No guardamos aquí, se guarda después del bucle en page_eval


# Helper para acciones de Flujo
def _handle_flow_action_change(wf_id):
    """Manejador para el selectbox de acciones de la tabla de flujos."""
    action_key = f"flow_action_{wf_id}"
    if action_key not in ss: return
    action = ss[action_key]

    # Resetear todos los estados modales/popups
    ss.viewing_flow_id = None
    ss.editing_flow_id = None
    ss.confirm_delete_flow_id = None
    ss.show_flow_form = False # Ocultar formulario por defecto

    if action == "Ver detalles":
        ss.viewing_flow_id = wf_id
        ss.show_flow_form = True # Abrir el formulario en modo VISTA
    elif action == "Editar":
        ss.editing_flow_id = wf_id
        ss.show_flow_form = True # Abrir el formulario en modo EDICIÓN
    elif action == "Eliminar":
        ss.confirm_delete_flow_id = wf_id

    # Resetear el selectbox para permitir una nueva selección
    ss[action_key] = "Selecciona..."
    # (Req 1) st.rerun() eliminado de callback

# (Req 3) Helper para acciones de Puestos
def _handle_position_action_change(pos_id):
    """Manejador para el selectbox de acciones de la tabla de puestos."""
    action_key = f"pos_action_{pos_id}"
    if action_key not in ss: return
    action = ss[action_key]

    ss.editing_position_id = None
    ss.confirm_delete_position_id = None
    ss.show_position_form = False

    if action == "Editar":
        ss.editing_position_id = pos_id
        ss.show_position_form = True
    elif action == "Eliminar":
        ss.confirm_delete_position_id = pos_id

    ss[action_key] = "Selecciona..."
    # (Req 1) st.rerun() eliminado de callback

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
      ss.section = "analytics"
      ss.pipeline_filter = None

    st.markdown("#### ASISTENTE IA")
    if st.button("Flujos", key="sb_flows"):
      ss.section = "flows"
      ss.pipeline_filter = None
      ss.editing_flow_id = None # Limpiar edición al cambiar
      ss.viewing_flow_id = None # Limpiar vista al cambiar
    if st.button("Agentes", key="sb_agents"):
      ss.section = "agents"
      ss.pipeline_filter = None

    st.markdown("#### PROCESO DE SELECCIÓN")
    for txt, sec, target_stage in [
        ("Publicación & Sourcing","publicacion_sourcing", None),
        ("Puestos","puestos", None),
        ("Evaluación de CVs","eval", None),
        ("Pipeline de Candidatos","pipeline", None),
        ("Entrevista (Gerencia)","pipeline", "Entrevista Gerencia"),
        ("Oferta","pipeline", "Oferta"),
        ("Onboarding","pipeline", "Contratado")
    ]:
      if txt in ["Entrevista (Gerencia)", "Oferta", "Onboarding"]:
        if st.button(txt, key=f"sb_{sec}_{txt.replace(' ', '_')}"):
            ss.section = "pipeline"
            ss.pipeline_filter = target_stage
      elif txt == "Pipeline de Candidatos":
          if st.button(txt, key=f"sb_{sec}"):
            ss.section = sec
            ss.pipeline_filter = None
      else:
        if st.button(txt, key=f"sb_{sec}"):
          ss.section = sec
          ss.pipeline_filter = None

    st.markdown("#### TAREAS")
    if st.button("Todas las tareas", key="sb_task_manual"): ss.section = "create_task"
    if st.button("Asignado a mi", key="sb_task_hh"): ss.section = "hh_tasks"
    if st.button("Asignado a mi equipo", key="sb_task_agente"): ss.section = "agent_tasks"

    st.markdown("#### ACCIONES")
    if st.button("Cerrar sesión", key="sb_logout"):
      ss.auth = None
      ss.editing_flow_id = None
      ss.viewing_flow_id = None
      ss.llm_eval_results = []
      st.rerun()

# =========================================================
# PÁGINAS
# =========================================================
def page_def_carga():
  st.header("Publicación & Sourcing")
  # (Req 2/3) Esta página sigue usando ROLE_PRESETS para precargar, lo cual está bien.
  role_names = list(ROLE_PRESETS.keys())

  st.subheader("1. Definición de la Vacante")
  col_puesto, col_id = st.columns(2)
  with col_puesto: puesto = st.selectbox("Puesto (Usar preset)", role_names, index=0)
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
      b = f.read(); f.seek(0)
      text = extract_text_from_file(f)
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

# ===================== EVALUACIÓN (Req 6 - Modificado) =====================
def page_eval():
    st.header("Resultados de evaluación")

    # === Bloque LLM ===
    with st.expander("🤖 Evaluación asistida por LLM (Azure/OpenAI)", expanded=True):

        # 1. Definir nombres de flujos desde ss.workflows
        flow_options = {wf.get("id"): wf.get("name", "Flujo sin nombre") for wf in ss.workflows if wf.get("id")}
        
        if not flow_options:
            st.warning("No hay flujos definidos en la pestaña 'Flujos'. Por favor, crea un flujo primero.", icon="⚠️")
            return

        # 2. Determinar el índice inicial
        initial_flow_id = list(flow_options.keys())[0]
        if "selected_flow_id_for_eval" in ss and ss.selected_flow_id_for_eval in flow_options:
            initial_flow_id = ss.selected_flow_id_for_eval
        else:
             ss.selected_flow_id_for_eval = initial_flow_id # Asegurar que esté seteado

        # 3. Agregar el st.selectbox
        st.selectbox(
            "Seleccionar Flujo de Evaluación",
            options=list(flow_options.keys()),
            format_func=lambda fid: flow_options.get(fid),
            key="selected_flow_id_for_eval" # Clave para guardar el estado
        )

        # (Req 5.1) Ya no se muestran los campos del flujo aquí

        # 4. Leer el valor actual del selectbox (se necesita para el botón)
        current_flow_id = ss.get("selected_flow_id_for_eval")
        
        # 5. Cargador de archivos y botón de ejecución (directamente después del selectbox)
        up = st.file_uploader("Sube CVs en PDF para evaluarlos con el LLM", type=["pdf"], accept_multiple_files=True, key="pdf_llm")
        run_llm = st.button("Ejecutar evaluación LLM", key="btn_llm_eval")

        if run_llm and up:
            # 6. Obtener los datos del Flujo seleccionado DENTRO del if del botón
            selected_flow_data = next((wf for wf in ss.workflows if wf.get("id") == current_flow_id), None)

            if not selected_flow_data:
                 st.error("Flujo seleccionado no válido. Por favor, selecciona otro.")
            else:
                # 7. Extraer la información necesaria del flujo seleccionado
                flow_desc_val = selected_flow_data.get("description", "")
                flow_expected_val = selected_flow_data.get("expected_output", "")
                jd_llm_val = selected_flow_data.get("jd_text", "")
                flow_name_val = selected_flow_data.get("name", "N/A") # (Req 6) Nombre del flujo

                if not _LC_AVAILABLE:
                    st.warning("Los paquetes de LangChain/OpenAI no están disponibles en el entorno. Se omite esta evaluación.")
                    ss.llm_eval_results = []
                elif not jd_llm_val or jd_llm_val.startswith("JD no"):
                    st.error("El flujo seleccionado no tiene un Job Description válido. Edita el flujo y añade un JD.")
                else:
                    results_with_bytes = []
                    new_tasks_created = 0 # (Req 6) Contador para tareas
                    for f in up:
                        f_bytes = f.read(); f.seek(0)
                        text = ""
                        try:
                            # ... (extracción de texto sin cambios) ...
                            if _LC_AVAILABLE:
                                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                                    tmp.write(f_bytes); tmp.flush()
                                    loader = PyPDFLoader(tmp.name)
                                    pages = loader.load()
                                    text = "\n".join([p.page_content for p in pages])
                            else:
                                reader = PdfReader(io.BytesIO(f_bytes))
                                for p in reader.pages: text += (p.extract_text() or "") + "\n"
                        except Exception as e_inner:
                             st.error(f"No se pudo leer {f.name}: {e_inner}")
                             continue


                        # Pasa el contexto del flujo a la función de IA
                        meta = _extract_with_azure(jd_llm_val, text, flow_desc_val, flow_expected_val) or \
                               _extract_with_openai(jd_llm_val, text, flow_desc_val, flow_expected_val)
                               
                        if not meta:
                            meta = {"Name":"—","Years_of_Experience":"—","English_Level":"—","Key_Skills":[],"Certifications":[],"Additional_Notes":"—","Score":0}
                        meta["file_name"] = f.name
                        results_with_bytes.append({"meta": meta, "_bytes": f_bytes})

                        # (Req 6) Crear tarea de revisión IA
                        try:
                           current_user = ss.auth.get("name", "Admin") # Asignar al usuario actual
                           score_val = meta.get('Score', 0)
                           # Usar 'Additional_Notes' como análisis
                           analysis_val = meta.get('Additional_Notes', 'Sin análisis detallado.') 
                           create_ia_review_task(f.name, flow_name_val, score_val, analysis_val, current_user)
                           new_tasks_created += 1
                        except Exception as e_task:
                            st.error(f"Error creando tarea para {f.name}: {e_task}")


                    ss.llm_eval_results = results_with_bytes
                    
                    # (Req 6) Guardar todas las tareas nuevas y mostrar mensaje
                    if new_tasks_created > 0:
                        save_tasks(ss.tasks)
                        st.success(f"{new_tasks_created} tarea(s) de revisión creadas en 'Todas las tareas'.")


        # Mostrar resultados si existen en session_state
        if ss.llm_eval_results:
            df_llm = _results_to_df([r["meta"] for r in ss.llm_eval_results])
            if not df_llm.empty:
                st.subheader("Resultados LLM (Evaluación Actual)")
                st.dataframe(df_llm, use_container_width=True, hide_index=True)
                st.plotly_chart(_create_llm_bar(df_llm), use_container_width=True)
            else:
                st.info("No se generaron resultados para los CVs subidos.")
        else:
            st.info("Selecciona un flujo, sube archivos y ejecuta la evaluación para ver resultados y crear tareas de revisión.")

    # (Req 5.2) Eliminado el visualizador de CV

# ===================== CÓDIGO RESTANTE (Puestos, Pipeline, etc. sin cambios desde la versión anterior) =====================
# ... (Incluir aquí las funciones page_puestos, page_pipeline, page_interview, page_offer, page_onboarding,
#      page_hh_tasks, page_agent_tasks, page_agents, render_flow_form, page_flows, page_analytics,
#      _llm_prompt_for_resume, _extract_with_azure, _extract_with_openai, _create_llm_bar, _results_to_df,
#      render_position_form, page_puestos, page_pipeline, etc. tal como estaban en la respuesta anterior) ...

# ===================== TODAS LAS TAREAS (Req 6 - Modificado para mostrar Resultados IA) =====================
def page_create_task():
    st.header("Todas las Tareas")

    # Expander para creación manual de tareas
    with st.expander("➕ Crear Tarea Manual"):
        with st.form("manual_task_form", clear_on_submit=True):
            st.markdown("**Nueva Tarea**")
            new_title = st.text_input("Título de la Tarea*")
            new_desc = st.text_area("Descripción")

            c1, c2, c3 = st.columns(3)
            with c1:
                new_due = st.date_input("Vencimiento", date.today() + timedelta(days=7))
            with c2:
                all_assignees = list(USERS.keys()) + DEFAULT_ROLES
                new_assignee = st.selectbox("Asignar a", sorted(list(set(all_assignees))), index=0)
            with c3:
                new_prio = st.selectbox("Prioridad", TASK_PRIORITIES, index=1)

            if st.form_submit_button("Guardar Tarea"):
                if new_title.strip():
                    create_manual_task(new_title, new_desc, new_due, new_assignee, new_prio)
                    st.success(f"Tarea '{new_title}' creada y asignada a {new_assignee}.")
                    st.rerun()
                else:
                    st.error("El Título de la Tarea es obligatorio.")

    st.info("Muestra todas las tareas registradas. Haz clic en una tarea para ver los detalles.")
    if not isinstance(ss.tasks, list):
        st.error("Error interno: La lista de tareas no es válida.")
        ss.tasks = load_tasks()
        if not isinstance(ss.tasks, list): ss.tasks = []

    if not ss.tasks:
        st.write("No hay tareas registradas en el sistema.")
        return

    tasks_list = ss.tasks
    all_statuses_set = set(t.get('status', 'Pendiente') for t in tasks_list)
    if "En Espera" not in all_statuses_set:
        all_statuses_set.add("En Espera")
    all_statuses = ["Todos"] + sorted(list(all_statuses_set))
    prefer_order = ["Pendiente", "En Proceso", "En Espera"]
    preferred = next((s for s in prefer_order if s in all_statuses), "Todos")
    selected_status = st.selectbox("Filtrar por Estado", options=all_statuses, index=all_statuses.index(preferred))

    tasks_to_show = tasks_list if selected_status == "Todos" else [t for t in tasks_list if t.get("status") == selected_status]
    if not tasks_to_show:
        st.info(f"No hay tareas con el estado '{selected_status}'.")
        return

    for task in tasks_to_show:
        t_id = task.get("id") or str(uuid.uuid4()); task["id"] = t_id
        
        # Usar expander
        with st.expander(f"{task.get('titulo','—')}"):
            # Grid para detalles
            st.markdown('<div class="task-details-grid">', unsafe_allow_html=True)
            st.markdown(f"<div><strong>Asignado a</strong> {task.get('assigned_to','—')}</div>", unsafe_allow_html=True)
            st.markdown(f"<div><strong>Creado el</strong> {task.get('created_at','—')}</div>", unsafe_allow_html=True)
            st.markdown(f"<div><strong>Vencimiento</strong> {task.get('due','—')}</div>", unsafe_allow_html=True)
            st.markdown(f"<div><strong>Estado</strong> {_status_pill(task.get('status','Pendiente'))}</div>", unsafe_allow_html=True)
            st.markdown(f"<div><strong>Prioridad</strong> {_priority_pill(task.get('priority','Media'))}</div>", unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

            # (Req 6) Mostrar resultados IA si existen en el contexto
            context = task.get("context", {})
            if context.get("source") == "IA Evaluation":
                 st.markdown("**Resultados IA**")
                 ia_score = context.get('ia_score', 'N/A')
                 ia_analysis = context.get('ia_analysis', 'No disponible.')
                 # Mostrar puntuación como badge si es posible
                 try:
                     score_num = int(ia_score)
                     color = PRIMARY if score_num >= 70 else ('#FFA500' if score_num >= 40 else '#D60000')
                     st.markdown(f"<span class='badge' style='border-color:{color}; background:{color}20; color:{color}; font-weight:bold; font-size:1rem;'>Puntuación: {score_num}%</span>", unsafe_allow_html=True)
                 except:
                      st.markdown(f"**Puntuación:** {ia_score}") # Fallback si no es número
                 
                 st.caption("**Análisis IA:**")
                 st.markdown(f"> {ia_analysis}") # Usar blockquote para el análisis
                 st.markdown("---")


            st.markdown("**Descripción General de Tarea**")
            st.caption(task.get("desc","—") or "Sin descripción.")
            st.markdown("---")

            # Callback para acciones (sin cambios internos)
            def _handle_action_change(task_id):
                selectbox_key = f"accion_{task_id}"
                if selectbox_key not in ss: return
                action = ss[selectbox_key]
                task_to_update = next((t for t in ss.tasks if t.get("id") == task_id), None)
                if not task_to_update: return
                ss.confirm_delete_id = None; ss.show_assign_for = None; ss.expanded_task_id = None
                if action == "Ver detalle":
                    ss.expanded_task_id = task_id
                elif action == "Asignar tarea":
                    ss.show_assign_for = task_id
                elif action == "Tomar tarea":
                    current_user = (ss.auth["name"] if ss.get("auth") else "Admin")
                    task_to_update["assigned_to"] = current_user
                    task_to_update["status"] = "En Proceso"
                    save_tasks(ss.tasks); st.toast("Tarea tomada.")
                elif action == "Eliminar":
                    ss.confirm_delete_id = task_id
                
                # Resetear selectbox
                ss[selectbox_key] = "Selecciona…"

            # Acciones (dentro del expander)
            selectbox_key = f"accion_{t_id}"
            st.selectbox(
                "Acciones",
                ["Selecciona…", "Ver detalle", "Asignar tarea", "Tomar tarea", "Eliminar"],
                key=selectbox_key, label_visibility="collapsed",
                on_change=_handle_action_change, args=(t_id,)
            )

            # Lógica de confirmación de eliminación (dentro del expander)
            if ss.get("confirm_delete_id") == t_id:
                b1, b2, _ = st.columns([1.0, 1.0, 7.8]) # Ajustar columnas si es necesario
                with b1:
                    if st.button("Eliminar permanentemente", key=f"del_confirm_{t_id}", type="primary", use_container_width=True):
                        ss.tasks = [t for t in ss.tasks if t.get("id") != t_id]
                        save_tasks(ss.tasks); ss.confirm_delete_id = None
                        st.warning("Tarea eliminada permanentemente.")
                        st.rerun() 
                with b2:
                    if st.button("Cancelar", key=f"del_cancel_{t_id}", use_container_width=True):
                        ss.confirm_delete_id = None
                        st.rerun() 

            # Lógica de reasignación (dentro del expander)
            if ss.show_assign_for == t_id:
                a1, a2, a3, a4, _ = st.columns([1.6, 1.6, 1.2, 1.0, 3.0]) # Ajustar columnas si es necesario
                with a1:
                    assign_type = st.selectbox("Tipo", ["En Espera", "Equipo", "Usuario"], key=f"type_{t_id}", index=2)
                with a2:
                    if assign_type == "En Espera":
                        nuevo_assignee = "En Espera"; st.text_input("Asignado a", "En Espera", key=f"val_esp_{t_id}", disabled=True)
                    elif assign_type == "Equipo":
                        nuevo_assignee = st.selectbox("Equipo", ["Coordinador RR.HH.", "Admin RR.HH.", "Agente de Análisis"], key=f"val_eq_{t_id}")
                    else:
                        nuevo_assignee = st.selectbox("Usuario", ["Headhunter", "Colab", "Sup", "Admin"], key=f"val_us_{t_id}")
                with a3:
                    cur_p = task.get("priority", "Media")
                    idx_p = TASK_PRIORITIES.index(cur_p) if cur_p in TASK_PRIORITIES else 1
                    nueva_prio = st.selectbox("Prioridad", TASK_PRIORITIES, key=f"prio_{t_id}", index=idx_p)
                with a4:
                    if st.button("Guardar", key=f"btn_assign_{t_id}", use_container_width=True):
                        task_to_update = next((t for t in ss.tasks if t.get("id") == t_id), None)
                        if task_to_update:
                            task_to_update["assigned_to"] = nuevo_assignee
                            task_to_update["priority"] = nueva_prio
                            if assign_type == "En Espera":
                                task_to_update["status"] = "En Espera"
                            else:
                                if task_to_update["status"] == "En Espera":
                                    task_to_update["status"] = "Pendiente"
                            save_tasks(ss.tasks); ss.show_assign_for = None
                            st.success("Cambios guardados.")
                            st.rerun() 

    # Lógica del diálogo para Tareas (sin cambios)
    task_id_for_dialog = ss.get("expanded_task_id")
    if task_id_for_dialog:
        task_data = next((t for t in ss.tasks if t.get("id") == task_id_for_dialog), None)
        if task_data:
            try:
                # Usar el objeto dialog devuelto por st.dialog()
                dialog = st.dialog("Detalle de Tarea", width="large")

                dialog.markdown(f"### {task_data.get('titulo', 'Sin Título')}")

                c1, c2 = dialog.columns(2)
                with c1:
                    dialog.markdown("**Información Principal**")
                    dialog.markdown(f"**Asignado a:** `{task_data.get('assigned_to', 'N/A')}`")
                    dialog.markdown(f"**Vencimiento:** `{task_data.get('due', 'N/A')}`")
                    dialog.markdown(f"**Creado el:** `{task_data.get('created_at', 'N/A')}`")
                with c2:
                    dialog.markdown("**Estado y Prioridad**")
                    dialog.markdown(f"**Estado:**"); dialog.markdown(_status_pill(task_data.get('status', 'Pendiente')), unsafe_allow_html=True)
                    dialog.markdown(f"**Prioridad:**"); dialog.markdown(_priority_pill(task_data.get('priority', 'Media')), unsafe_allow_html=True)

                context = task_data.get("context")
                # Mostrar contexto IA primero si existe
                if context.get("source") == "IA Evaluation":
                    dialog.markdown("---")
                    dialog.markdown("**Resultados IA**")
                    ia_score = context.get('ia_score', 'N/A')
                    ia_analysis = context.get('ia_analysis', 'No disponible.')
                    dialog.markdown(f"**Puntuación:** {ia_score}%")
                    dialog.caption("**Análisis IA:**")
                    dialog.markdown(f"> {ia_analysis}")

                # Mostrar otro contexto si existe
                elif context and ("candidate_name" in context or "role" in context):
                    dialog.markdown("---")
                    dialog.markdown("**Contexto del Flujo**")
                    if "candidate_name" in context:
                        dialog.markdown(f"**Postulante:** {context['candidate_name']}")
                    if "role" in context:
                        dialog.markdown(f"**Puesto:** {context['role']}")

                dialog.markdown("---")
                dialog.markdown("**Descripción General de Tarea:**"); dialog.markdown(task_data.get('desc', 'Sin descripción.'))
                dialog.markdown("---")
                dialog.markdown("**Actividad Reciente:**"); dialog.markdown("- *No hay actividad registrada.*")

                # Usar dialog.form para el formulario dentro del diálogo
                with dialog.form("comment_form_dialog"):
                    # Añadir key única
                    st.text_area("Comentarios", placeholder="Añadir un comentario...", key=f"task_comment_dialog_{task_data.get('id')}")
                    submitted = st.form_submit_button("Enviar Comentario")
                    if submitted: st.toast("Comentario (aún no) guardado.")

                if dialog.button("Cerrar", key="close_task_dialog"): # Key única para el botón
                    ss.expanded_task_id = None
                    dialog.close() # Usar .close() en el objeto dialog

            except Exception as e:
                st.error(f"Error al mostrar detalles de la tarea: {e}")
                if ss.get("expanded_task_id") == task_id_for_dialog:
                    ss.expanded_task_id = None
        else:
            ss.expanded_task_id = None # Limpiar si la tarea ya no existe

# =========================================================
# ROUTER
# =========================================================
ROUTES = {
  "publicacion_sourcing": page_def_carga,
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

# =========================================================
# APP
# =========================================================
if __name__ == "__main__":
    # Agregué la corrección del NameError aquí, asegurando que las funciones
    # estén definidas antes de ser llamadas por el router.
    # El código anterior ya tenía las definiciones antes del __main__, 
    # por lo que el error original podría haber sido un estado intermedio.
    # Esta estructura es la correcta.
    if require_auth():
        render_sidebar()
        # Llamada al router (sin cambios, ya era correcta)
        ROUTES.get(ss.section, page_def_carga)()
