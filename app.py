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
    b'JVBERi0xLjAKMSAwIG9iajw8L1R5cGUvQ2F0YWxvZy9QYWdlcyAyIDAgUj4+ZW5kb2JqCjIgMCBvYmo8PC9UeXBlL1BhZ2VzL0NvdW50IDEvS2lkc1szIDAgUl0+PmVuZG9iagozIDAgb2JqPDwvVHlwZS9QYWdlL01lZGlhQm94WzAgMCAzMCAzMF0vUGFyZW50IDIgMCBSPj5lbmRvYmoKeHJlZgowIDQKMDAwMDAwMDAwMCA2NTUzNSBmIAowMDAwMDAwMDA5IDAwMDAwIG4gCjAwMDAwMDAwNTIgMDAwMDAgbiAKMDAwMDAwMDA5OSAwMDAwMCBuIAp0cmFpbGVyPDwvU1l6ZSA0L1Jvb3QgMSAwIFI+PgpzdGFydHhyZWYKMTQ3CiUlRU9G'
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

st.markdown("""<style>
[data-testid="stSidebar"] .sidebar-brand .brand-sub{ font-size: 12px !important; line-height: 1.2 !important; margin-top: 4px !important; opacity: .95 !important; }
[data-testid="stSidebar"] .sidebar-brand{ margin-top:0 !important; padding-bottom:0 !important; margin-bottom:55px !important; }
[data-testid="stSidebar"] [data-testid="stVerticalBlock"]{ gap:2px !important; } [data-testid="stSidebar"] [data-testid="stVerticalBlock"]>div{ margin:0 !important; padding:0 !important; }
[data-testid="stSidebar"] h4, [data-testid="stSidebar"] .stMarkdown h4{ margin:2px 8px 2px !important; line-height:1 !important; }
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p{ margin:2px 8px !important; }
[data-testid="stSidebar"] .stButton{ margin:0 !important; padding:0 !important; }
[data-testid="stSidebar"] .stButton>button{ margin:0 8px 6px 0 !important; padding-left:8px !important; line-height:1.05 !important; gap:6px !important; }
</style>""", unsafe_allow_html=True)

# =========================================================
# Persistencia
# =========================================================
DATA_DIR = Path("data"); DATA_DIR.mkdir(exist_ok=True)
AGENTS_FILE = DATA_DIR/"agents.json"; WORKFLOWS_FILE = DATA_DIR/"workflows.json"
ROLES_FILE = DATA_DIR / "roles.json"; TASKS_FILE = DATA_DIR / "tasks.json"
EVALS_FILE = DATA_DIR / "evaluations.json"

DEFAULT_ROLES = ["Headhunter", "Coordinador RR.HH.", "Admin RR.HH."]
DEFAULT_TASKS = [
    {"id": str(uuid.uuid4()), "titulo":"Revisar CVs top 5", "desc":"Analizar top 5 para 'Business Analytics'.", "due":str(date.today() + timedelta(days=2)), "assigned_to": "Headhunter", "status": "Pendiente", "priority": "Alta", "created_at": (date.today() - timedelta(days=3)).isoformat()},
    {"id": str(uuid.uuid4()), "titulo":"Coordinar entrevista R. Brykson", "desc":"Agendar 2da entrevista (Gerencia) para VP Mkt.", "due":str(date.today() + timedelta(days=5)), "assigned_to": "Coordinador RR.HH.", "status": "En Proceso", "priority": "Media", "created_at": (date.today() - timedelta(days=8)).isoformat(), "context": {"candidate_name": "Rivers Brykson", "role": "VP de Marketing"}},
    {"id": str(uuid.uuid4()), "titulo":"Crear workflow Onboarding", "desc":"Definir pasos en 'Flujos'.", "due":str(date.today() - timedelta(days=1)), "assigned_to": "Admin RR.HH.", "status": "Completada", "priority": "Baja", "created_at": (date.today() - timedelta(days=15)).isoformat()},
    {"id": str(uuid.uuid4()), "titulo":"Análisis Detallado CV M.Diaz", "desc":"Usar agente IA para informe de brechas.", "due":str(date.today() + timedelta(days=3)), "assigned_to": "Agente de Análisis", "status": "Pendiente", "priority": "Media", "created_at": date.today().isoformat(), "context": {"candidate_name": "MartaDiaz.pdf", "role": "Desarrollador/a Backend (Python)"}}
]

def load_roles():
  if ROLES_FILE.exists():
    try: roles = json.loads(ROLES_FILE.read_text(encoding="utf-8")); return sorted(list({*DEFAULT_ROLES, *(r.strip() for r in roles if r.strip())}))
    except: pass
  return DEFAULT_ROLES.copy()

def save_roles(roles: list):
  roles_clean = sorted(list({r.strip() for r in roles if r.strip()})); custom_only = [r for r in roles_clean if r not in DEFAULT_ROLES]
  ROLES_FILE.write_text(json.dumps(custom_only, ensure_ascii=False, indent=2), encoding="utf-8")

def load_json(path: Path, default):
  if path.exists():
    try: return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"Error reading {path}: {e}")
        try:
            if default is not None: save_json(path, default); return default
        except Exception as e_save: print(f"Error saving default to {path}: {e_save}")
        return default if isinstance(default, (list, dict)) else []
  if default is not None:
      try: save_json(path, default)
      except Exception as e: print(f"Error creating default {path}: {e}")
  return default if isinstance(default, (list, dict)) else []

def save_json(path: Path, data):
  try: path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
  except Exception as e: print(f"Error saving to {path}: {e}")

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
if "tasks_loaded" not in ss: ss.tasks = load_tasks(); ss.tasks_loaded = True
if "candidates" not in ss: ss.candidates = []
if "offers" not in ss:  ss.offers = {}
if "agents_loaded" not in ss: ss.agents = load_agents(); ss.agents_loaded = True
if "workflows_loaded" not in ss: ss.workflows = load_workflows(); ss.workflows_loaded = True
if "agent_view_idx" not in ss: ss.agent_view_idx = None
if "agent_edit_idx" not in ss: ss.agent_edit_idx = None
if "new_role_mode" not in ss: ss.new_role_mode = False
if "roles" not in ss: ss.roles = load_roles()
if "positions" not in ss:
  ss.positions = pd.DataFrame([
      {"ID":"10645194","Puesto":"Desarrollador/a Backend (Python)","Días Abierto":3,"Leads":1800,"Nuevos":115,"Recruiter Screen":35,"HM Screen":7,"Entrevista Telefónica":14,"Entrevista Presencial":15,"Ubicación":"Lima, Perú","Hiring Manager":"R. Brykson","Estado":"Abierto","Fecha Inicio": date.today() - timedelta(days=3)},
      {"ID":"10376415","Puesto":"VP de Marketing","Días Abierto":28,"Leads":8100,"Nuevos":1,"Recruiter Screen":15,"HM Screen":35,"Entrevista Telefónica":5,"Entrevista Presencial":7,"Ubicación":"Santiago, Chile","Hiring Manager":"A. Cruz","Estado":"Abierto","Fecha Inicio": date.today() - timedelta(days=28)},
      {"ID":"10376646","Puesto":"Planner de Demanda","Días Abierto":28,"Leads":2300,"Nuevos":26,"Recruiter Screen":3,"HM Screen":8,"Entrevista Telefónica":6,"Entrevista Presencial":3,"Ubicación":"CDMX, MX","Hiring Manager":"R. Brykson","Estado":"Abierto","Fecha Inicio": date.today() - timedelta(days=28)}
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
DEFAULT_EVAL_LLM_ROLE = ss.get("last_role", DEFAULT_FLOW_ROLE)
if "eval_llm_role" not in ss: ss.eval_llm_role = DEFAULT_EVAL_LLM_ROLE
if "eval_llm_jd" not in ss or not ss.eval_llm_jd: ss.eval_llm_jd = ROLE_PRESETS.get(ss.eval_llm_role, {}).get("jd", "")

# =========================================================
# UTILS
# =========================================================
def update_flow_fields_from_preset():
    new_role = ss.flow_form_role; preset = ROLE_PRESETS.get(new_role)
    if preset: ss.flow_form_desc = preset.get("jd", EVAL_INSTRUCTION); ss.flow_form_expected = DEFAULT_EXPECTED_OUTPUT; ss.flow_form_jd = preset.get("jd", "")

def update_eval_llm_jd_from_preset():
    new_role = ss.eval_llm_role; preset = ROLE_PRESETS.get(new_role)
    if preset: ss.eval_llm_jd = preset.get("jd", "")

SKILL_SYNONYMS = { "Excel":["excel","xlsx"], "SQL":["sql"], "Power BI":["power bi"], "Tableau":["tableau"], "Python":["python"], "Figma":["figma"], "UX Research":["ux research"], "Prototipado":["prototipado"], "Agile":["agile", "scrum"], }
def _normalize(t:str)->str: return re.sub(r"\s+"," ",(t or "")).strip().lower()
def infer_skills(text:str)->set: t=_normalize(text); out=set(); [out.add(k) for k,syns in SKILL_SYNONYMS.items() if any(s in t for s in syns)]; return out
def score_fit_by_skills(jd_text, must_list, nice_list, cv_text):
  jd_skills=infer_skills(jd_text); must=set([m.strip() for m in must_list if m.strip()]) or jd_skills; nice=set([n.strip() for n in nice_list if n.strip()])-must; cv=infer_skills(cv_text)
  mm=sorted(list(must&cv)); mn=sorted(list(nice&cv)); gm=sorted(list(must-cv)); gn=sorted(list(nice-cv)); extras=sorted(list((cv&(jd_skills|must|nice))-set(mm)-set(mn)))
  cov_m=len(mm)/len(must) if must else 0; cov_n=len(mn)/len(nice) if nice else 0; sc=int(round(100*(0.65*cov_m+0.20*cov_n+0.15*min(len(extras),5)/5)))
  return sc, {"matched_must":mm,"matched_nice":mn,"gaps_must":gm,"gaps_nice":gn,"extras":extras,"must_total":len(must),"nice_total":len(nice)}
def build_analysis_text(name,ex): ok_m=", ".join(ex["matched_must"]) or "ninguno"; ok_n=", ".join(ex["matched_nice"]) or "—"; gaps=", ".join(ex["gaps_must"][:3]) or "ninguna"; extras=", ".join(ex["extras"][:3]) or "—"; return f"{name}: Must ({ok_m}). Nice ({ok_n}). Brechas ({gaps}). Extras ({extras})."

# --- Función pdf_viewer_embed CORREGIDA ---
def pdf_viewer_embed(b: bytes, h=520):
    try:
        b64 = base64.b64encode(b).decode("utf-8")
        st.components.v1.html(f'<embed src="data:application/pdf;base64,{b64}" type="application/pdf" width="100%" height="{h}px"/>', height=h)
    except Exception as e:
        st.error(f"Error PDF: {e}")
# --- Fin de la corrección ---

# --- Función _extract_docx_bytes CORREGIDA ---
def _extract_docx_bytes(b: bytes) -> str:
    try:
        with zipfile.ZipFile(io.BytesIO(b)) as z:
            xml = z.read("word/document.xml").decode("utf-8", "ignore")
            text = re.sub(r"<.*?>", " ", xml)
            return re.sub(r"\s+", " ", text).strip()
    except Exception:
        return ""
# --- Fin de la corrección ---

def extract_text_from_file(up_file) -> str:
  try:
    suf = Path(up_file.name).suffix.lower(); b = up_file.read(); up_file.seek(0)
    if suf == ".pdf": reader = PdfReader(io.BytesIO(b)); return "\n".join([(p.extract_text() or "") for p in reader.pages])
    elif suf == ".docx": return _extract_docx_bytes(b)
    else: return b.decode("utf-8", errors="ignore")
  except Exception as e: print(f"Error extract {up_file.name}: {e}"); return ""
def _max_years(t): t=t.lower(); y=0; [y:=max(y, int(m.group(1))) for m in re.finditer(r'(\d{1,2})\s*(años|year)', t)]; return y if y>0 else 5 if any(w in t for w in ["años","experiencia"]) else 0
def extract_meta(t): y=_max_years(t); return {"anios_exp":y, "ultima_actualizacion":date.today().isoformat()}
def _status_pill(s: str)->str: c={"Pendiente": "#9AA6B2", "En Proceso": "#0072E3", "Completada": "#10B981", "En Espera": "#FFB700"}.get(s, "#9AA6B2"); return f'<span class="badge" style="border-color:{c}33;background:{c}14;color:#0A2230">{s}</span>'
def _priority_pill(p: str) -> str: p_safe = p if p in TASK_PRIORITIES else "Media"; return f'<span class="badge priority-{p_safe}">{p_safe}</span>'
def create_task_from_flow(name:str, due_date:date, desc:str, assigned:str="Coordinador RR.HH.", status:str="Pendiente", priority:str="Media", context:dict=None):
  t = { "id": str(uuid.uuid4()), "titulo": f"Ejecutar flujo: {name}", "desc": desc or "Tarea de Flujo.", "due": due_date.isoformat(), "assigned_to": assigned, "status": status, "priority": priority if priority in TASK_PRIORITIES else "Media", "created_at": date.today().isoformat(), "context": context or {} }
  if not isinstance(ss.tasks, list): ss.tasks = []
  ss.tasks.insert(0, t); save_tasks(ss.tasks)
def create_manual_task(title, desc, due_date, assigned_to, priority):
  t = { "id": str(uuid.uuid4()), "titulo": title, "desc": desc, "due": due_date.isoformat(), "assigned_to": assigned_to, "status": "Pendiente", "priority": priority, "created_at": date.today().isoformat(), "context": {"source": "Manual"} }
  if not isinstance(ss.tasks, list): ss.tasks = []
  ss.tasks.insert(0, t); save_tasks(ss.tasks)

# =========================================================
# LOGIN + SIDEBAR
# =========================================================
def asset_logo_wayki(): local = Path("assets/logo-wayki.png"); return str(local) if local.exists() else "https://raw.githubusercontent.com/wayki-consulting/.dummy/main/logo-wayki.png"
def login_screen():
  st.markdown('<div class="login-bg"><div class="login-card">', unsafe_allow_html=True)
  try: st.markdown('<div class="login-logo-wrap">', unsafe_allow_html=True); st.image(asset_logo_wayki(), width=120); st.markdown("</div>", unsafe_allow_html=True)
  except: pass
  st.markdown('<div class="login-sub">Acceso a SelektIA</div>', unsafe_allow_html=True)
  with st.form("login_form"):
    u = st.text_input("Usuario"); p = st.text_input("Contraseña", type="password"); ok = st.form_submit_button("Ingresar")
    if ok:
      if u in USERS and USERS[u]["password"] == p: ss.auth = {"username":u, "role": USERS[u]["role"], "name": USERS[u]["name"]}; st.success("Bienvenido."); st.rerun()
      else: st.error("Usuario o contraseña incorrectos.")
  st.markdown("</div></div>", unsafe_allow_html=True)

# --- Función require_auth CORREGIDA ---
def require_auth():
  if ss.auth is None:
    login_screen()
    return False
  return True
# --- Fin de la corrección ---

def render_sidebar():
  with st.sidebar:
    st.markdown('<div class="sidebar-brand"><div class="brand-title">SelektIA</div><div class="brand-sub">Powered by Wayki Consulting</div></div>', unsafe_allow_html=True)
    st.markdown("#### DASHBOARD");  if st.button("Analytics", key="sb_analytics"): ss.section = "analytics"; ss.pipeline_filter = None
    st.markdown("#### ASISTENTE IA"); if st.button("Flujos", key="sb_flows"): ss.section = "flows"; ss.pipeline_filter = None; ss.editing_flow_id = None; ss.form_loaded_from_edit = False;
    if st.button("Agentes", key="sb_agents"): ss.section = "agents"; ss.pipeline_filter = None
    st.markdown("#### PROCESO DE SELECCIÓN"); btns = [("Publicación & Sourcing","publicacion_sourcing", None), ("Puestos","puestos", None), ("Evaluación de CVs","eval", None), ("Pipeline de Candidatos","pipeline", None), ("Entrevista (Gerencia)","pipeline", "Entrevista Gerencia"), ("Oferta","pipeline", "Oferta"), ("Onboarding","pipeline", "Contratado")]
    for txt, sec, pf in btns:
        is_pf_btn = txt in ["Entrevista (Gerencia)", "Oferta", "Onboarding"]
        key = f"sb_{sec}" + (f"_{txt.replace(' ', '_')}" if is_pf_btn else "")
        if st.button(txt, key=key): ss.section = sec; ss.pipeline_filter = pf
    st.markdown("#### TAREAS"); if st.button("Todas las tareas", key="sb_task_manual"): ss.section = "create_task";
    if st.button("Asignado a mi", key="sb_task_hh"): ss.section = "hh_tasks"; if st.button("Asignado a mi equipo", key="sb_task_agente"): ss.section = "agent_tasks"
    st.markdown("#### ACCIONES"); if st.button("Cerrar sesión", key="sb_logout"): ss.auth = None; ss.editing_flow_id = None; ss.last_llm_batch = []; ss.form_loaded_from_edit = False; st.rerun()

# =========================================================
# PÁGINAS
# =========================================================
# --- page_def_carga ---
def page_def_carga():
  st.header("Publicación & Sourcing"); role_names = list(ROLE_PRESETS.keys())
  st.subheader("1. Definición de la Vacante"); c1,c2=st.columns(2); with c1: puesto=st.selectbox("Puesto", role_names, index=0); with c2: id_puesto=st.text_input("ID Puesto", value=f"P-{random.randint(1000,9999)}")
  preset = ROLE_PRESETS[puesto]; jd_text = st.text_area("Descripción / JD", height=180, value=preset["jd"]); kw_text = st.text_area("Keywords", height=100, value=preset["keywords"], help="Scoring.")
  ss.update(last_role=puesto, last_jd_text=jd_text, last_kw_text=kw_text)
  st.subheader("2. Carga Manual CVs"); files = st.file_uploader("Subir (PDF/DOCX/TXT)", type=["pdf","docx","txt"], accept_multiple_files=True)
  if files and st.button("Procesar CVs (Carga Manual)"):
    new_cand = []; must = [s.strip() for s in (preset.get("must",[]) or []) if s.strip()]; nice = [s.strip() for s in (preset.get("nice",[]) or []) if s.strip()]
    for f in files: b=f.read(); f.seek(0); text=extract_text_from_file(f); score,exp=score_fit_by_skills(jd_text,must,nice,text); idx=len(ss.candidates)+len(new_cand)+1
      new_cand.append({"id": f"C{idx}-{int(datetime.now().timestamp())}", "Name": f.name, "Score": score, "Role": puesto, "Role_ID": id_puesto, "_bytes": b, "_is_pdf": Path(f.name).suffix.lower()==".pdf", "_text": text, "meta": extract_meta(text), "stage": PIPELINE_STAGES[0], "load_date": date.today().isoformat(), "_exp": exp, "source": "Carga Manual"})
    [c.update(stage="Descartado") for c in new_cand if c["Score"] < 35]; ss.candidates.extend(new_cand); st.success(f"{len(new_cand)} CVs cargados."); st.rerun()
  st.subheader("3. Sourcing Portales"); with st.expander("🔌 Integración Portales"):
    srcs=st.multiselect("Portales", JOB_BOARDS, default=["laborum.pe"], key="portal_srcs"); qty=st.number_input("Cantidad",1,30,6, key="portal_qty"); search_q=st.text_input("Búsqueda", value=puesto, key="portal_search_q"); location=st.text_input("Ubicación", value="Lima, Perú", key="portal_location")
    if st.button("Traer CVs"):
      new_cand=[]; must = [s.strip() for s in (preset.get("must",[]) or []) if s.strip()]; nice = [s.strip() for s in (preset.get("nice",[]) or []) if s.strip()]
      for board in srcs:
        for i in range(1,int(qty)+1): txt=f"CV {board} {puesto}. Exp {random.randint(2, 10)} años. Skills: SQL, Python."; score, exp = score_fit_by_skills(jd_text, must, nice, txt); idx=len(ss.candidates)+len(new_cand)+1
          new_cand.append({"id": f"C{idx}-{int(datetime.now().timestamp())}", "Name":f"{board}_Cand_{i:02d}.pdf", "Score": score, "Role": puesto, "Role_ID": id_puesto, "_bytes": DUMMY_PDF_BYTES, "_is_pdf": True, "_text": txt, "meta": extract_meta(txt), "stage": PIPELINE_STAGES[0], "load_date": date.today().isoformat(), "_exp": exp, "source": board})
      [c.update(stage="Descartado") for c in new_cand if c["Score"] < 35]; ss.candidates.extend(new_cand); st.success(f"{len(new_cand)} CVs importados."); st.rerun()

# --- page_puestos ---
def page_puestos():
  st.header("Puestos"); df_pos = ss.positions.copy()
  df_pos["Time to Hire (promedio)"] = df_pos["Días Abierto"].apply(lambda d: f"{d+random.randint(10, 40)} días" if d < 30 else f"{d} días")
  st.dataframe(df_pos[["Puesto","Días Abierto","Time to Hire (promedio)","Leads","Nuevos","Recruiter Screen","HM Screen","Entrevista Telefónica","Entrevista Presencial","Ubicación","Hiring Manager","Estado","ID"]].sort_values(["Estado","Días Abierto","Leads"], ascending=[True,True,False]), use_container_width=True, height=380, hide_index=True)
  st.subheader("Candidatos por Puesto"); pos_list = df_pos["Puesto"].tolist(); selected_pos = st.selectbox("Selecciona un puesto", pos_list)
  if selected_pos:
    candidates_for_pos = [c for c in ss.candidates if c.get("Role") == selected_pos]
    if candidates_for_pos: df_cand = pd.DataFrame(candidates_for_pos); st.dataframe(df_cand[["Name", "Score", "stage", "load_date"]].rename(columns={"Name":"Candidato", "Score":"Fit", "stage":"Fase"}), use_container_width=True, hide_index=True)
    else: st.info(f"No hay candidatos para **{selected_pos}**.")

# --- page_eval ---
def page_eval():
    st.header("Resultados de evaluación")
    with st.expander("🤖 Evaluación asistida por LLM (Azure/OpenAI)", expanded=True):
        role_options = list(ROLE_PRESETS.keys()); role_index = role_options.index(ss.eval_llm_role) if ss.eval_llm_role in role_options else 0
        st.selectbox("Puesto objetivo", role_options, index=role_index, key="eval_llm_role", on_change=update_eval_llm_jd_from_preset)
        jd_llm = st.text_area("Job Description para el LLM", value=ss.eval_llm_jd, key="eval_llm_jd_input", height=120)
        up = st.file_uploader("Sube CVs en PDF", type=["pdf"], accept_multiple_files=True, key="pdf_llm")
        c1, c2 = st.columns([1, 0.4]); with c1: run_llm = st.button("Ejecutar evaluación LLM", key="btn_llm_eval")
        with c2: st.button("🗑️ Limpiar Historial", key="btn_clear_evals", help="Borra historial guardado.", on_click=lambda: (ss.update(all_evaluations=[], last_llm_batch=[]), save_evals([]), st.success("Historial limpiado.")))
        if run_llm and up:
            if not _LC_AVAILABLE: st.warning("Paquetes LLM no disponibles."); ss.last_llm_batch = []; return
            results_with_bytes = []; new_meta_to_save = []; current_jd_for_eval = ss.eval_llm_jd
            for f in up:
                f_bytes = f.read(); f.seek(0); text = "";
                try:
                    if _LC_AVAILABLE:
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp: tmp.write(f_bytes); tmp.flush(); loader = PyPDFLoader(tmp.name); pages = loader.load(); text = "\n".join([p.page_content for p in pages])
                    else: reader = PdfReader(io.BytesIO(f_bytes)); text = "\n".join([(p.extract_text() or "") for p in reader.pages])
                except Exception as e: st.error(f"Error leer {f.name}: {e}"); continue
                meta = _extract_with_azure(current_jd_for_eval, text) or _extract_with_openai(current_jd_for_eval, text)
                meta = meta or {"Name":"—","Score":0}; meta["file_name"] = f.name
                results_with_bytes.append({"meta": meta, "_bytes": f_bytes}); new_meta_to_save.append(meta)
            ss.last_llm_batch = results_with_bytes; ss.all_evaluations.extend(new_meta_to_save); save_evals(ss.all_evaluations)
            st.success(f"Evaluación completada. {len(new_meta_to_save)} resultados guardados."); st.rerun()
        if ss.last_llm_batch:
            df_llm = _results_to_df([r["meta"] for r in ss.last_llm_batch])
            if not df_llm.empty: st.subheader("Resultados Última Evaluación"); st.dataframe(df_llm, use_container_width=True, hide_index=True); st.plotly_chart(_create_llm_bar(df_llm), use_container_width=True)
        else: st.info("Sube archivos y ejecuta evaluación.")
        st.markdown(f"**Total evaluaciones en historial:** `{len(ss.all_evaluations)}`")
    if ss.last_llm_batch:
        st.markdown("---"); st.subheader("Visualizar CV (Último Batch)")
        file_names = [r["meta"]["file_name"] for r in ss.last_llm_batch]; selected_file_name = st.selectbox("Selecciona CV", file_names)
        if selected_file_name:
            selected_file_data = next((r for r in ss.last_llm_batch if r["meta"]["file_name"] == selected_file_name), None)
            if selected_file_data and selected_file_data.get("_bytes"): pdf_viewer_embed(selected_file_data["_bytes"], height=500)
            else: st.error("No se encontró PDF.")

# --- page_pipeline ---
def page_pipeline():
    filter_stage = ss.get("pipeline_filter")
    if filter_stage: st.header(f"Pipeline: Fase '{filter_stage}'"); candidates_to_show = [c for c in ss.candidates if c.get("stage") == filter_stage]
    else: st.header("Pipeline de Candidatos"); candidates_to_show = ss.candidates
    st.caption("Mueve candidatos entre etapas.");
    if not candidates_to_show and filter_stage: st.info(f"No hay candidatos en **{filter_stage}**."); return
    elif not ss.candidates: st.info("No hay candidatos activos."); return
    candidates_by_stage = {stage: [] for stage in PIPELINE_STAGES}; [candidates_by_stage[c["stage"]].append(c) for c in candidates_to_show]
    cols = st.columns(len(PIPELINE_STAGES))
    for i, stage in enumerate(PIPELINE_STAGES):
        with cols[i]:
            st.markdown(f"**{stage} ({len(candidates_by_stage[stage])})**"); st.markdown("---")
            for c in candidates_by_stage[stage]:
                card_name = c["Name"].split('_')[-1].replace('.pdf', '').replace('.txt', '')
                color = PRIMARY if c['Score'] >= 70 else ('#FFA500' if c['Score'] >= 40 else '#D60000')
                st.markdown(f'<div class="k-card" style="margin-bottom:10px; border-left:4px solid {color}"><div style="font-weight:700;">{card_name}</div><div style="font-size:12px;opacity:.8;">{c.get("Role", "N/A")}</div><div style="font-size:14px;font-weight:700;margin-top:8px;">Fit: <span style="color:{PRIMARY};">{c["Score"]}%</span></div><div style="font-size:10px;opacity:.6;margin-top:4px;">Fuente: {c.get("source", "N/A")}</div></div>', unsafe_allow_html=True)
                with st.form(key=f"form_move_{c['id']}"):
                    current_idx = PIPELINE_STAGES.index(stage); available = [s for s in PIPELINE_STAGES if s != stage]; default_idx=0
                    try: default_idx = available.index(PIPELINE_STAGES[min(current_idx + 1, len(PIPELINE_STAGES) - 1)])
                    except ValueError: pass
                    new_stage = st.selectbox("Mover a:", available, key=f"select_move_{c['id']}", index=default_idx, label_visibility="collapsed")
                    if st.form_submit_button("Mover"):
                        c["stage"] = new_stage
                        if new_stage == "Descartado": st.success(f"📧 Email rechazo enviado a {card_name}.")
                        elif new_stage == "Entrevista Telefónica": st.info(f"📅 Tarea agendar entrevista creada para {card_name}."); ctx = {"candidate_name": card_name, "candidate_id": c["id"], "role": c.get("Role", "N/A")}; create_task_from_flow(f"Programar entrevista - {card_name}", date.today()+timedelta(days=2), "Coordinar entrevista.", assigned="Headhunter", context=ctx)
                        elif new_stage == "Contratado": st.balloons(); st.success(f"🎉 ¡Éxito! Onboarding disparado para {card_name}.")
                        if filter_stage and new_stage != filter_stage: ss.pipeline_filter = None; st.info("Filtro removido.")
                        st.rerun()
                st.markdown("<br>", unsafe_allow_html=True)

# --- page_interview ---
def page_interview():
  st.header("Entrevista (Gerencia)"); st.write("Redirige a Pipeline [Filtro: Entrevista Gerencia].")
  st.info("Usa Pipeline + filtro lateral."); ss.section = "pipeline"; ss.pipeline_filter = "Entrevista Gerencia"; st.rerun()

# --- _ensure_offer_record ---
def _ensure_offer_record(cand_name: str):
  if cand_name not in ss.offers: ss.offers[cand_name] = { "puesto": "", "salario": "", "estado": "Borrador", "fecha_inicio": date.today() + timedelta(days=14), "caducidad": date.today() + timedelta(days=7)}

# --- page_offer ---
def page_offer():
  st.header("Oferta"); st.write("Redirige a Pipeline [Filtro: Oferta].")
  st.info("Usa Pipeline + filtro lateral."); ss.section = "pipeline"; ss.pipeline_filter = "Oferta"; st.rerun()

# --- page_onboarding ---
def page_onboarding():
  st.header("Onboarding"); st.write("Redirige a Pipeline [Filtro: Contratado].")
  st.info("Usa Pipeline + filtro lateral."); ss.section = "pipeline"; ss.pipeline_filter = "Contratado"; st.rerun()

# --- page_hh_tasks ---
def page_hh_tasks():
    st.header("Tareas Asignadas a Mí"); st.write("Tareas asignadas a tu rol.")
    if not isinstance(ss.tasks, list) or not ss.tasks: st.info("No tienes tareas."); return
    df_tasks = pd.DataFrame(ss.tasks); my_name = ss.auth["name"] if ss.get("auth") else "Colab"
    my_tasks = df_tasks[df_tasks["assigned_to"].isin(["Headhunter", "Colaborador", my_name])]
    all_statuses = ["Todos"] + sorted(my_tasks["status"].unique()); pref = ["Pendiente", "En Proceso"]; preferred = next((s for s in pref if s in all_statuses), "Todos")
    sel_status = st.selectbox("Filtrar Estado", all_statuses, index=all_statuses.index(preferred))
    my_tasks_filtered = my_tasks if sel_status=="Todos" else my_tasks[my_tasks["status"] == sel_status]
    if not my_tasks_filtered.empty: st.dataframe(my_tasks_filtered.rename(columns={"titulo":"Título", "desc":"Desc", "due":"Vence", "status": "Estado", "priority": "Prio"})[["Título", "Desc", "Estado", "Prio", "Vence"]], use_container_width=True, hide_index=True)
    else: st.info(f"No hay tareas '{sel_status}'.")

# --- page_agent_tasks ---
def page_agent_tasks():
    st.header("Tareas Asignadas Equipo"); st.write("Tareas generadas por Flujos y asignadas a roles.")
    if not isinstance(ss.tasks, list) or not ss.tasks: st.info("No hay tareas de equipo."); return
    df_tasks = pd.DataFrame(ss.tasks); team_tasks = df_tasks[df_tasks["assigned_to"].isin(HR_ROLES + ["Agente de Análisis"])]
    all_statuses = ["Todos"] + sorted(team_tasks["status"].unique()); pref = ["Pendiente", "En Proceso"]; preferred = next((s for s in pref if s in all_statuses), "Todos")
    sel_status = st.selectbox("Filtrar Estado", all_statuses, index=all_statuses.index(preferred), key="agent_task_filter")
    team_tasks_filtered = team_tasks if sel_status=="Todos" else team_tasks[team_tasks["status"] == sel_status]
    if not team_tasks_filtered.empty: st.dataframe(team_tasks_filtered.rename(columns={"titulo":"Título", "desc":"Desc", "due":"Vence", "assigned_to": "Asignado", "status": "Estado", "priority": "Prio"})[["Título", "Desc", "Asignado", "Estado", "Prio", "Vence"]], use_container_width=True, hide_index=True)
    else: st.info(f"No hay tareas '{sel_status}'.")

# --- page_flows ---
def page_flows():
  st.header("Flujos"); vista_como = ss.auth["role"]; puede_aprobar = vista_como in ("Supervisor","Administrador")
  left, right = st.columns([0.9, 1.1])
  with left:
    st.subheader("Mis flujos");
    if not ss.workflows: st.info("No hay flujos.")
    else:
      rows = [];
      for wf in ss.workflows: ag_label="—"; ai=wf.get("agent_idx",-1); ag_label=ss.agents[ai].get("rol","Agente") if 0<=ai<len(ss.agents) else "—"; rows.append({"ID": wf["id"], "Nombre": wf["name"], "Puesto": wf.get("role","—"), "Agente": ag_label, "Estado": wf.get("status","Borrador"), "Programado": wf.get("schedule_at","—")})
      df = pd.DataFrame(rows); st.dataframe(df, use_container_width=True, height=260)
      if rows:
        sel_options = [r["ID"] for r in rows]; sel_format_func = lambda x: next((r["Nombre"] for r in rows if r["ID"]==x), x); sel_index = 0
        try: sel_index = sel_options.index(ss.editing_flow_id)
        except ValueError: ss.editing_flow_id = None
        sel = st.selectbox("Selecciona flujo", sel_options, index=sel_index, format_func=sel_format_func, key="flow_selector")
        if st.button("Cargar para Editar", key="load_flow_edit"): ss.editing_flow_id = sel; ss.form_loaded_from_edit = False; st.rerun()
        wf = next((w for w in ss.workflows if w["id"]==sel), None)
        if wf:
          c1,c2,c3 = st.columns(3)
          with c1: if st.button("🧬 Duplicar"): clone=dict(wf); clone["id"]=f"WF-{int(datetime.now().timestamp())}"; clone["status"]="Borrador"; ss.workflows.insert(0, clone); save_workflows(ss.workflows); st.success("Duplicado."); ss.editing_flow_id = None; ss.form_loaded_from_edit = False; st.rerun()
          with c2: if st.button("🗑 Eliminar"): ss.workflows = [w for w in ss.workflows if w["id"]!=wf["id"]]; save_workflows(ss.workflows); st.success("Eliminado."); if ss.editing_flow_id == wf["id"]: ss.editing_flow_id = None; ss.form_loaded_from_edit = False; st.rerun()
          with c3: st.markdown(f"<div class='badge'>Estado: <b>{wf.get('status','Borrador')}</b></div>", unsafe_allow_html=True)
            if wf.get("status")=="Pendiente de aprobación" and puede_aprobar:
              a1,a2=st.columns(2)
              with a1: if st.button("✅ Aprobar"): wf["status"]="Aprobado"; wf["approved_by"]=vista_como; wf["approved_at"]=datetime.now().isoformat(); save_workflows(ss.workflows); st.success("Aprobado."); st.rerun()
              with a2: if st.button("❌ Rechazar"): wf["status"]="Rechazado"; wf["approved_by"]=vista_como; wf["approved_at"]=datetime.now().isoformat(); save_workflows(ss.workflows); st.warning("Rechazado."); st.rerun()
  with right:
    editing_wf = None
    if ss.editing_flow_id: editing_wf = next((w for w in ss.workflows if w["id"] == ss.editing_flow_id), None)
    if editing_wf and not ss.form_loaded_from_edit: ss.flow_form_name = editing_wf.get("name", "Analizar CV"); ss.flow_form_role = editing_wf.get("role", DEFAULT_FLOW_ROLE); ss.flow_form_desc = editing_wf.get("description", EVAL_INSTRUCTION); ss.flow_form_expected = editing_wf.get("expected_output", DEFAULT_EXPECTED_OUTPUT); ss.flow_form_jd = editing_wf.get("jd_text", ""); ss.flow_form_agent_idx = editing_wf.get("agent_idx", 0); ss.form_loaded_from_edit = True
    st.subheader("Crear Flujo" if not editing_wf else f"Editando: {editing_wf.get('name')}")
    if editing_wf:
        if st.button("✖ Cancelar Edición"): ss.editing_flow_id = None; ss.form_loaded_from_edit = False; ss.flow_form_name = "Analizar CV"; ss.flow_form_role = DEFAULT_FLOW_ROLE; update_flow_fields_from_preset(); ss.flow_form_agent_idx = 0; st.rerun()
    with st.form("wf_form"):
      st.markdown("<div class='badge'>Task</div>", unsafe_allow_html=True); name = st.text_input("Name*", value=ss.flow_form_name, key="flow_form_name_input")
      role_options = list(ROLE_PRESETS.keys()); role_index = role_options.index(ss.flow_form_role) if ss.flow_form_role in role_options else 0
      role = st.selectbox("Puesto objetivo", role_options, index=role_index, key="flow_form_role", on_change=update_flow_fields_from_preset)
      desc = st.text_area("Description*", value=ss.flow_form_desc, key="flow_form_desc_input", height=110); expected = st.text_area("Expected output*", value=ss.flow_form_expected, key="flow_form_expected_input", height=80)
      st.markdown("**Job Description**"); jd_text = st.text_area("JD en texto", value=ss.flow_form_jd, key="flow_form_jd_input", height=140); jd_file = st.file_uploader("...o sube JD", type=["pdf","txt","docx"], key="wf_jd_file"); jd_from_file = ""
      if jd_file: jd_from_file = extract_text_from_file(jd_file); st.caption("Preview JD:"); st.text_area("Preview", jd_from_file[:1000], height=100)
      st.markdown("---"); st.markdown("<div class='badge'>Agente</div>", unsafe_allow_html=True)
      if ss.agents: agent_opts = [f"{i} — {a.get('rol','Agente')}" for i,a in enumerate(ss.agents)]; agent_idx_val = ss.flow_form_agent_idx if 0 <= ss.flow_form_agent_idx < len(ss.agents) else 0; agent_pick = st.selectbox("Asigna agente", agent_opts, index=agent_idx_val, key="flow_form_agent_idx_input"); agent_idx = int(agent_pick.split(" — ")[0])
      else: st.info("No hay agentes."); agent_idx = -1
      st.markdown("---"); st.markdown("<div class='badge'>Guardar</div>", unsafe_allow_html=True); run_date = st.date_input("Fecha ejecución", value=date.today()+timedelta(days=1)); run_time = st.time_input("Hora ejecución", value=datetime.now().time().replace(second=0, microsecond=0))
      if editing_wf: update_flow = st.form_submit_button("💾 Actualizar Flujo"); save_draft=send_approval=schedule=False
      else: update_flow=False; col_a,col_b,col_c = st.columns(3); save_draft=col_a.form_submit_button("💾 Guardar borrador"); send_approval=col_b.form_submit_button("📝 Enviar aprobación"); schedule=col_c.form_submit_button("📅 Guardar y Programar")
      if save_draft or send_approval or schedule or update_flow:
        jd_final = jd_from_file if jd_from_file.strip() else ss.flow_form_jd_input
        if not jd_final.strip(): st.error("JD es obligatorio."); return
        if agent_idx < 0: st.error("Agente es obligatorio."); return
        wf_data = { "name": ss.flow_form_name_input, "role": ss.flow_form_role, "description": ss.flow_form_desc_input, "expected_output": ss.flow_form_expected_input, "jd_text": jd_final[:200000], "agent_idx": agent_idx }
        if update_flow: editing_wf.update(wf_data); editing_wf["status"] = "Borrador"; save_workflows(ss.workflows); st.success("Actualizado."); ss.editing_flow_id=None; ss.form_loaded_from_edit=False; st.rerun()
        else:
            wf = wf_data.copy(); wf.update({"id": f"WF-{int(datetime.now().timestamp())}", "created_at": datetime.now().isoformat(), "status": "Borrador", "approved_by": "", "approved_at": "", "schedule_at": ""})
            if send_approval: wf["status"] = "Pendiente de aprobación"; st.success("Enviado.")
            if schedule: wf["status"] = "Programado" if puede_aprobar else "Pendiente de aprobación"; wf["schedule_at"]=f"{run_date} {run_time:%H:%M}"; st.success("Programado." if puede_aprobar else "Pendiente aprobación.")
            if save_draft: st.success("Borrador guardado.")
            ss.workflows.insert(0, wf); save_workflows(ss.workflows); ss.form_loaded_from_edit=False; st.rerun()

# --- page_agents ---
def page_agents():
  st.header("Agentes"); st.subheader("Crear / Editar agente"); left, _ = st.columns([0.25, 0.75])
  with left:
    if st.button(("➕ Nuevo" if not ss.new_role_mode else "✖ Cancelar"), key="toggle_new_role"): ss.new_role_mode = not ss.new_role_mode; ss.agent_view_idx = None; ss.agent_edit_idx = None; st.rerun()
  if ss.new_role_mode:
    st.info("Crear nuevo agente."); with st.form("agent_new_form"):
      c1, c2 = st.columns(2);
      with c1: role_name=st.text_input("Rol*"); objetivo=st.text_input("Objetivo*"); backstory=st.text_area("Backstory*", height=120); guardrails=st.text_area("Guardrails", height=90)
      with c2: st.text_input("LLM", value=LLM_IN_USE, disabled=True); img_src=st.text_input("URL imagen"); perms=st.multiselect("Permisos", ["Colaborador","Supervisor","Admin"], default=["Supervisor","Admin"])
      if st.form_submit_button("Guardar Agente"):
        rn = (role_name or "").strip();
        if not rn: st.error("Rol es obligatorio.")
        else: ss.agents.append({"rol": rn, "objetivo": objetivo, "backstory": backstory, "guardrails": guardrails, "herramientas": [], "llm_model": LLM_IN_USE, "image": img_src, "perms": perms, "ts": datetime.utcnow().isoformat()}); save_agents(ss.agents); roles_new = sorted(list({*ss.roles, rn})); ss.roles = roles_new; save_roles(roles_new); st.success("Agente creado."); ss.new_role_mode = False; st.rerun()
  st.subheader("Tus agentes");
  if not ss.agents: st.info("No hay agentes."); return
  cols_per_row = 5
  for i in range(0, len(ss.agents), cols_per_row):
    row_agents = ss.agents[i:i+cols_per_row]; cols = st.columns(cols_per_row)
    for j, ag in enumerate(row_agents):
      idx = i + j; with cols[j]:
        img = ag.get("image") or AGENT_DEFAULT_IMAGES.get(ag.get("rol","Headhunter")); st.markdown(f'<div class="agent-card"><img src="{img}"><div class="agent-title">{ag.get("rol","—")}</div><div class="agent-sub">{ag.get("objetivo","—")}</div></div>', unsafe_allow_html=True)
        st.markdown('<div class="toolbar">', unsafe_allow_html=True); c1, c2, c3, c4 = st.columns(4)
        with c1: if st.button("👁", key=f"ag_v_{idx}", help="Ver"): ss.agent_view_idx = (None if ss.agent_view_idx == idx else idx); ss.agent_edit_idx = None; st.rerun()
        with c2: if st.button("✏", key=f"ag_e_{idx}", help="Editar"): ss.agent_edit_idx = (None if ss.agent_edit_idx == idx else idx); ss.agent_view_idx = None; st.rerun()
        with c3: if st.button("🧬", key=f"ag_c_{idx}", help="Clonar"): clone = dict(ag); clone["rol"] = f"{ag.get('rol','Agente')} (copia)"; ss.agents.append(clone); save_agents(ss.agents); st.success("Clonado."); st.rerun()
        with c4: if st.button("🗑", key=f"ag_d_{idx}", help="Eliminar"): ss.agents.pop(idx); save_agents(ss.agents); st.success("Eliminado."); st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
  if ss.agent_view_idx is not None and 0 <= ss.agent_view_idx < len(ss.agents):
    ag = ss.agents[ss.agent_view_idx]; st.markdown("### Detalle agente"); st.markdown('<div class="agent-detail">', unsafe_allow_html=True)
    c1, c2 = st.columns([0.42, 0.58]); with c1: raw_img = ag.get("image") or ""; safe_img = (raw_img.strip() if raw_img.strip() else AGENT_DEFAULT_IMAGES.get(ag.get("rol","Headhunter"))); st.markdown(f'<div style="text-align:center;"><img src="{safe_img}" style="width:180px;height:180px;border-radius:999px;object-fit:cover;"></div>', unsafe_allow_html=True); st.caption("LLM"); st.markdown(f"<div class='badge'>🧠 {ag.get('llm_model',LLM_IN_USE)}</div>", unsafe_allow_html=True)
    with c2: st.text_input("Role*", value=ag.get("rol",""), disabled=True); st.text_input("Objetivo*", value=ag.get("objetivo",""), disabled=True); st.text_area("Backstory*", value=ag.get("backstory",""), height=120, disabled=True); st.text_area("Guardrails", value=ag.get("guardrails",""), height=90, disabled=True); st.caption("Permisos"); st.write(", ".join(ag.get("perms",[])) or "—")
    st.markdown('</div>', unsafe_allow_html=True)
  if ss.agent_edit_idx is not None and 0 <= ss.agent_edit_idx < len(ss.agents):
    ag = ss.agents[ss.agent_edit_idx]; st.markdown("### Editar agente"); with st.form(f"agent_edit_{ss.agent_edit_idx}"):
      objetivo=st.text_input("Objetivo*", value=ag.get("objetivo","")); backstory=st.text_area("Backstory*", value=ag.get("backstory",""), height=120); guardrails=st.text_area("Guardrails", value=ag.get("guardrails",""), height=90)
      st.text_input("LLM", value=ag.get('llm_model', LLM_IN_USE), disabled=True); img_src=st.text_input("URL imagen", value=ag.get("image","")); perms=st.multiselect("Permisos", ["Colaborador","Supervisor","Admin"], default=ag.get("perms",["Supervisor","Admin"]))
      if st.form_submit_button("Guardar cambios"): ag.update({"objetivo":objetivo,"backstory":backstory,"guardrails":guardrails, "llm_model":ag.get('llm_model', LLM_IN_USE),"image":img_src,"perms":perms}); save_agents(ss.agents); st.success("Actualizado."); st.rerun()

# --- page_analytics ---
def page_analytics():
    st.header("Analytics y KPIs"); st.subheader("Visión General")
    c1, c2, c3, c4 = st.columns(4); c1.metric("Costo/Hire", "S/ 4.2k", "-8%"); c2.metric("Time to Hire (P50)", "28d", "+2d"); c3.metric("Conversión Oferta>Cont.", "81%", "+3%"); c4.metric("Exactitud IA", "92%", "v2.1")
    st.markdown("---"); col_funnel, col_time = st.columns(2)
    with col_funnel: st.subheader("Embudo"); df_f = pd.DataFrame({"Fase": ["Recibido", "Screening", "Entrevista G", "Oferta", "Contratado"], "N": [1200, 350, 80, 25, 20]}); df_f = df_f[df_f["N"] > 0]; fig_f = px.funnel(df_f, x='N', y='Fase'); fig_f.update_traces(marker=dict(color=PRIMARY)); fig_f.update_layout(plot_bgcolor="#FFFFFF", paper_bgcolor="rgba(0,0,0,0)", font=dict(color=TITLE_DARK), yaxis_title=None); st.plotly_chart(fig_f, use_container_width=True)
    with col_time: st.subheader("Tiempos Proceso"); df_t = pd.DataFrame({"Métrica": ["TT Interview", "TT Offer", "TT Hire"], "P50": [12, 22, 28], "P90": [20, 31, 42]}); df_tm = df_t.melt(id_vars="Métrica", var_name="P", value_name="Días"); fig_t = px.bar(df_tm, x="Métrica", y="Días", color="P", barmode="group", color_discrete_sequence=PLOTLY_GREEN_SEQUENCE); fig_t.update_layout(plot_bgcolor="#FFFFFF", paper_bgcolor="rgba(0,0,0,0)", font=dict(color=TITLE_DARK), yaxis_title="Días"); st.plotly_chart(fig_t, use_container_width=True)
    st.markdown("---"); col_prod, col_cost_ia = st.columns(2)
    with col_prod: st.subheader("Productividad Reclutador"); df_p = pd.DataFrame({"Rec": ["Ad", "Su", "Co", "Hh"], "Cont.(90d)": [8, 5, 12, 9]}); fig_p = px.bar(df_p, x="Rec", y="Cont.(90d)", color_discrete_sequence=PLOTLY_GREEN_SEQUENCE); fig_p.update_layout(plot_bgcolor="#FFFFFF", paper_bgcolor="rgba(0,0,0,0)", font=dict(color=TITLE_DARK)); st.plotly_chart(fig_p, use_container_width=True)
    with col_cost_ia: st.subheader("Exactitud IA"); df_ia = pd.DataFrame({"Puesto": ["BA", "UX", "Ing", "Enf"], "N": [120, 85, 200, 310], "Fit IA": [82, 75, 88, 79]}); fig_ia = px.scatter(df_ia, x="N", y="Fit IA", size="N", color="Puesto", color_discrete_sequence=PLOTLY_GREEN_SEQUENCE); fig_ia.update_layout(plot_bgcolor="#FFFFFF", paper_bgcolor="rgba(0,0,0,0)", font=dict(color=TITLE_DARK)); st.plotly_chart(fig_ia, use_container_width=True)

# --- page_create_task ---
def page_create_task():
    st.header("Todas las Tareas"); with st.expander("➕ Crear Tarea Manual"):
        with st.form("manual_task_form", clear_on_submit=True):
            st.markdown("**Nueva Tarea**"); nt = st.text_input("Título*"); nd = st.text_area("Desc."); c1,c2,c3=st.columns(3); with c1: ndue=st.date_input("Vence", date.today()+timedelta(days=7)); with c2: aa=list(USERS.keys())+DEFAULT_ROLES; nass=st.selectbox("Asignar a", sorted(list(set(aa)))); with c3: npr=st.selectbox("Prio", TASK_PRIORITIES, index=1)
            if st.form_submit_button("Guardar"):
                if nt.strip(): create_manual_task(nt, nd, ndue, nass, npr); st.success(f"Tarea '{nt}' creada."); st.rerun()
                else: st.error("Título es obligatorio.")
    st.info("Tareas registradas."); tasks_list = ss.tasks;
    if not isinstance(tasks_list, list): st.error("Error lista tareas."); tasks_list = []
    if not tasks_list: st.write("No hay tareas."); return
    st.markdown("---"); fc1, fc2 = st.columns([1, 1.5]); with fc1: fcat = st.selectbox("Filtrar", ["Todas", "Cola", "HR"], key="task_category_filter", label_visibility="collapsed"); with fc2: fsrch = st.text_input("Buscar", key="task_search_filter", placeholder="Buscar...", label_visibility="collapsed")
    tasks_to_show = tasks_list
    if fcat == "Cola": tasks_to_show = [t for t in tasks_to_show if t.get("status") in ["Pendiente", "En Proceso"]]
    elif fcat == "HR": tasks_to_show = [t for t in tasks_to_show if t.get("assigned_to") in HR_ROLES]
    if fsrch: sl = fsrch.lower(); tasks_to_show = [t for t in tasks_to_show if sl in (t.get("titulo") or "").lower()]
    if not tasks_to_show: st.info(f"No hay tareas que coincidan."); return
    col_w = [0.9, 2.2, 2.4, 1.6, 1.4, 1.6, 1.0, 1.2, 1.6]; headers = ["Id", "Nombre", "Desc.", "Asignado", "Creado", "Vence", "Prio", "Estado", "Acciones"]; h_cols = st.columns(col_w); [h_cols[i].markdown(f"**{h}**") for i, h in enumerate(headers)]; st.markdown("<hr style='border:1px solid #E3EDF6; opacity:.6;'/>", unsafe_allow_html=True)
    for task in tasks_to_show:
        t_id = task.get("id") or str(uuid.uuid4()); task["id"] = t_id; c_cols = st.columns(col_w)
        with c_cols[0]: short = (t_id[:5] + "…") if len(t_id) > 6 else t_id; st.caption(short)
        with c_cols[1]: st.markdown(f"**{task.get('titulo','—')}**")
        with c_cols[2]: st.caption(task.get("desc","—")[:60]+ ('...' if len(task.get('desc',''))>60 else ''))
        with c_cols[3]: st.markdown(f"`{task.get('assigned_to','—')}`")
        with c_cols[4]: st.markdown(task.get("created_at","—"))
        with c_cols[5]: st.markdown(task.get("due","—"))
        with c_cols[6]: st.markdown(_priority_pill(task.get("priority","Media")), unsafe_allow_html=True)
        with c_cols[7]: st.markdown(_status_pill(task.get("status","Pendiente")), unsafe_allow_html=True)
        def _handle_action_change(tid): action = ss[f"accion_{tid}"]; task_upd = next((t for t in ss.tasks if t.get("id") == tid), None); ss.confirm_delete_id=ss.show_assign_for=ss.expanded_task_id=None;
            if not task_upd: return;
            if action=="Ver detalle": ss.expanded_task_id=tid;
            elif action=="Asignar": ss.show_assign_for=tid;
            elif action=="Tomar": cur_usr=(ss.auth["name"] if ss.auth else "Admin"); task_upd["assigned_to"]=cur_usr; task_upd["status"]="En Proceso"; save_tasks(ss.tasks); st.toast("Tomada."); st.rerun();
            elif action=="Eliminar": ss.confirm_delete_id=tid;
        with c_cols[8]: st.selectbox("Acciones", ["...", "Ver detalle", "Asignar", "Tomar", "Eliminar"], key=f"accion_{t_id}", label_visibility="collapsed", on_change=_handle_action_change, args=(t_id,))
        if ss.get("confirm_delete_id") == t_id: b1, b2, _ = st.columns([1, 1, 8]); with b1: if st.button("Eliminar!", key=f"del_c_{t_id}", type="primary"): ss.tasks = [t for t in ss.tasks if t.get("id")!=t_id]; save_tasks(ss.tasks); ss.confirm_delete_id=None; st.warning("Eliminada."); st.rerun(); with b2: if st.button("Cancelar", key=f"del_k_{t_id}"): ss.confirm_delete_id=None; st.rerun();
        if ss.show_assign_for == t_id:
            a1, a2, a3, a4, _ = st.columns([1.6, 1.6, 1.2, 1.0, 3.0]); with a1: atyp = st.selectbox("Tipo", ["Espera", "Equipo", "Usuario"], key=f"t_{t_id}", index=2)
            with a2:
                if atyp=="Espera": nass="En Espera"; st.text_input("Asignado", nass, key=f"ve_{t_id}", disabled=True)
                elif atyp=="Equipo": nass=st.selectbox("Equipo", HR_ROLES + ["Agente de Análisis"], key=f"ve_{t_id}")
                else: nass=st.selectbox("Usuario", ["Headhunter", "Colab", "Sup", "Admin"], key=f"vu_{t_id}")
            with a3: curp=task.get("priority","Media"); idxp=TASK_PRIORITIES.index(curp) if curp in TASK_PRIORITIES else 1; nprio=st.selectbox("Prio", TASK_PRIORITIES, key=f"p_{t_id}", index=idxp)
            with a4: if st.button("Guardar", key=f"ba_{t_id}"): task_upd = next((t for t in ss.tasks if t.get("id") == t_id), None); if task_upd: task_upd["assigned_to"]=nass; task_upd["priority"]=nprio; task_upd["status"] = "En Espera" if atyp=="Espera" else ("Pendiente" if task_upd["status"]=="En Espera" else task_upd["status"]); save_tasks(ss.tasks); ss.show_assign_for=None; st.success("Guardado."); st.rerun();
        st.markdown("<hr style='border:1px solid #E3EDF6; opacity:.35;'/>", unsafe_allow_html=True)
    task_id_for_dialog = ss.get("expanded_task_id");
    if task_id_for_dialog:
        task_data = next((t for t in ss.tasks if t.get("id") == task_id_for_dialog), None)
        if task_data:
            try:
                with st.dialog("Detalle Tarea", width="large"):
                    st.markdown(f"### {task_data.get('titulo', 'Sin Título')}"); c1,c2=st.columns(2)
                    with c1: st.markdown("**Info Principal**"); st.markdown(f"**Asignado:** `{task_data.get('assigned_to', 'N/A')}`"); st.markdown(f"**Vence:** `{task_data.get('due', 'N/A')}`"); st.markdown(f"**Creado:** `{task_data.get('created_at', 'N/A')}`")
                    with c2: st.markdown("**Estado/Prio**"); st.markdown(f"**Estado:**"); st.markdown(_status_pill(task_data.get('status', 'Pendiente')), unsafe_allow_html=True); st.markdown(f"**Prioridad:**"); st.markdown(_priority_pill(task_data.get('priority', 'Media')), unsafe_allow_html=True)
                    context = task_data.get("context");
                    if context and ("candidate_name" in context or "role" in context): st.markdown("---"); st.markdown("**Contexto**"); [st.markdown(f"**{k.replace('_',' ').title()}:** {v}") for k,v in context.items()]
                    st.markdown("---"); st.markdown("**Descripción:**"); st.markdown(task_data.get('desc', 'N/A'))
                    st.markdown("---"); st.markdown("**Actividad:**"); st.markdown("- *No registrada.*")
                    with st.form("comment_form"): st.text_area("Comentarios", key="task_comment"); submitted = st.form_submit_button("Enviar"); #if submitted: st.toast("Comentario no guardado.")
                    if st.button("Cerrar", key="close_dialog"): ss.expanded_task_id = None; st.rerun()
            except Exception as e: st.error(f"Error diálogo: {e}"); ss.expanded_task_id = None
        else: ss.expanded_task_id = None

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
