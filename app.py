# app.py
# -*- coding: utf-8 -*-

import io, base64, re, json, random, zipfile, uuid, statistics # statistics added for P50/P90
from pathlib import Path
from datetime import datetime, date, timedelta

import streamlit as st
import pandas as pd
import plotly.express as px
from PyPDF2 import PdfReader

# =========================================================
# PALETA / CONST
# =========================================================
PRIMARY        = "#00CD78"
SIDEBAR_BG = "#0E192B"
SIDEBAR_TX = "#B9C7DF"
BODY_BG      = "#F7FBFF"
CARD_BG      = "#0E192B"
TITLE_DARK = "#142433"

BAR_DEFAULT = "#E9F3FF"
BAR_GOOD    = "#33FFAC"

JOB_BOARDS  = ["laborum.pe","Computrabajo","Bumeran","Indeed","LinkedIn Jobs"]
PIPELINE_STAGES = ["Recibido", "Screening RRHH", "Entrevista Telefónica", "Entrevista Gerencia", "Oferta", "Contratado", "Descartado"]
TASK_PRIORITIES = ["Alta", "Media", "Baja"]

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
  "Headhunter":        "https://images.unsplash.com/photo-1581090464777-f3220bbe1b8b?q=80&w=512&auto-format&fit=crop",
  "Coordinador RR.HH.":"https://images.unsplash.com/photo-1542751371-adc38448a05e?q=80&w=512&auto-format&fit=crop",
  "Admin RR.HH.":      "https://images.unsplash.com/photo-1526378722484-bd_91ca387e72?q=80&w=512&auto-format&fit=crop",
}
LLM_MODELS = ["gpt-4o-mini","gpt-4.1","gpt-4o","claude-3.5-sonnet","claude-3-haiku","gemini-1.5-pro","mixtral-8x7b","llama-3.1-70b"]

# ===== Presets de puestos =====
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
    "must": ["Figma","UX Research","Prototipado"], "nice":["Heurísticas","Accesibilidad","Design System"],
    "synth_skills":["Figma","UX Research","Prototipado","Wireframes","Accesibilidad","Heurísticas","Design System","Analytics"]
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

# Bytes de un PDF de ejemplo mínimo (preview)
DUMMY_PDF_BYTES = base64.b64decode(
    b'JVBERi0xLjAKMSAwIG9iajw8L1R5cGUvQ2F0YWxvZy9QYWdlcyAyIDAgUj4+ZW5kb2JqCjIgMCBvYmo8PC9UeXBlL1BhZ2VzL0NvdW50IDEvS2lkc1szIDAgUl0+PmVuZG9iagozIDAgb2JqPDwvVHlwZS9QYWdlL01lZGlhQm94WzAgMCAzMCAzMF0vUGFyZW50IDIgMCBSPj5lbmRvYmoKeHJlZgowIDQKMDAwMDAwMDAwMCA2NTUzNSBmIAowMDAwMDAwMDA5IDAwMDAwIG4gCjAwMDAwMDAwNTIgMDAwMDAgbiAKMDAwMDAwMDA5OSAwMDAwMCBuIAp0cmFpbGVyPDwvU2l6ZSA0L1Jvb3QgMSAwIFI+PgpzdGFydHhyZWYKMTQ3CiUlRU9G'
)

# =========================================================
# CSS
# =========================================================
CSS = f"""
:root {{
  --green: {PRIMARY};
  --sb-bg: {SIDEBAR_BG};
  --sb-tx: {SIDEBAR_TX};
  --body: {BODY_BG};
  --sb-card: {CARD_BG};
}}
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

/* Botón del sidebar */
[data-testid="stSidebar"] .stButton>button {{
  width: 100% !important; display:flex !important; justify-content:flex-start !important; align-items:center !important; text-align:left !important;
  gap:8px !important; background: var(--sb-card) !important; border:1px solid var(--sb-bg) !important; color:#fff !important;
  border-radius:12px !important; padding:9px 12px !important; margin:6px 8px !important; font-weight:600 !important;
}}

/* Botones del body */
.block-container .stButton>button {{
  width:auto !important; display:flex !important; justify-content:center !important; align-items:center !important; text-align:center !important;
  background: var(--green) !important; color:#082017 !important; border-radius:10px !important; border:none !important; padding:.50rem .90rem !important; font-weight:700 !important;
}}
.block-container .stButton>button:hover {{ filter: brightness(.96); }}

/* Botones de confirmación eliminación */
.block-container .stButton>button.delete-confirm-btn {{ background: #D60000 !important; color: white !important; }}
.block-container .stButton>button.cancel-btn {{ background: #e0e0e0 !important; color: #333 !important; }}

/* Tipografía */
h1, h2, h3 {{ color: {TITLE_DARK}; }}
h1 strong, h2 strong, h3 strong {{ color: var(--green); }}

/* Inputs */
.block-container [data-testid="stSelectbox"]>div>div,
.block-container [data-baseweb="select"],
.block-container [data-testid="stTextInput"] input,
.block-container [data-testid="stTextArea"] textarea {{
  background:#F1F7FD !important; color:{TITLE_DARK} !important; border:1.5px solid #E3EDF6 !important; border-radius:10px !important;
}}

/* Tablas y tarjetas */
.block-container table {{ background:#fff !important; border:1px solid #E3EDF6 !important; border-radius:8px !important; }}
.block-container thead th {{ background:#F1F7FD !important; color:{TITLE_DARK} !important; }}
.k-card {{ background:#fff;border:1px solid #E3EDF6;border-radius:12px;padding:14px; }}
.badge {{ display:inline-flex;align-items:center;gap:6px;background:#F1F7FD;border:1px solid #E3EDF6;border-radius:24px;padding:4px 10px;font-size:12px;color:#1B2A3C; }}

/* Prioridad */
.priority-Alta {{ border-color: #FFA500 !important; background: #FFF5E6 !important; color: #E88E00 !important; font-weight: 600;}}
.priority-Media {{ border-color: #B9C7DF !important; background: #F1F7FD !important; color: #0E192B !important; }}
.priority-Baja {{ border-color: #D1D5DB !important; background: #F3F4F6 !important; color: #6B7280 !important; }}

/* Tarjeta de agente */
.agent-card{{background:#fff;border:1px solid #E3EDF6;border-radius:14px;padding:10px;text-align:center;min-height:178px}}
.agent-card img{{width:84px;height:84px;border-radius:999px;object-fit:cover;border:4px solid #F1F7FD}}
.agent-title{{font-weight:800;color:{TITLE_DARK};font-size:15px;margin-top:6px}}
.agent-sub{{font-size:12px;opacity:.8;margin-top:4px;min-height:30px}}

/* Toolbar en tarjeta */
.toolbar{{display:flex;align-items:center;justify-content:center;gap:8px;margin-top:8px}}
.toolbar .stButton>button{{
  background:#fff !important; color:#2b3b4d !important; border:1px solid #E3EDF6 !important;
  border-radius:10px !important; padding:6px 8px !important; min-width:36px !important;
}}
.toolbar .stButton>button:hover{{ background:#F7FBFF !important; }}

/* Detalle/edición */
.agent-detail{{background:#fff;border:2px solid #E3EDF6;border-radius:16px;padding:16px;box-shadow:0 6px 18px rgba(14,25,43,.08)}}

/* Login */
.login-bg{{background:{SIDEBAR_BG};position:fixed;inset:0;display:flex;align-items:center;justify-content:center}}
.login-card{{background:transparent;border:none;box-shadow:none;padding:0;width:min(600px,92vw);}}
.login-logo-wrap{{display:flex;align-items:center;justify-content:center;margin-bottom:14px}}
.login-sub{{color:#9fb2d3;text-align:center;margin:0 0 18px 0;font-size:12.5px}}
.login-card [data-testid="stTextInput"] input {{
  background:#10283f !important; color:#E7F0FA !important; border:1.5px solid #1d3a57 !important;
  border-radius:24px !important; height:48px !important; padding:0 16px !important;
}}
.login-card .stButton>button{{ width:160px !important; border-radius:24px !important; }}

/* Chips por estado en Pipeline */
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
# Persistencia (Agentes / Flujos / Roles / Tareas)
# =========================================================
DATA_DIR = Path("data"); DATA_DIR.mkdir(exist_ok=True)
AGENTS_FILE = DATA_DIR/"agents.json"
WORKFLOWS_FILE = DATA_DIR/"workflows.json"
ROLES_FILE = DATA_DIR / "roles.json"
TASKS_FILE = DATA_DIR / "tasks.json"

DEFAULT_ROLES = ["Headhunter", "Coordinador RR.HH.", "Admin RR.HH."]

DEFAULT_TASKS = [
    {"id": str(uuid.uuid4()), "titulo":"Revisar CVs top 5", "desc":"Analizar a los 5 candidatos con mayor fit para 'Business Analytics'.", "due":str(date.today() + timedelta(days=2)), "assigned_to": "Headhunter", "status": "Pendiente", "priority": "Alta", "created_at": (date.today() - timedelta(days=3)).isoformat()},
    {"id": str(uuid.uuid4()), "titulo":"Coordinar entrevista de Rivers Brykson", "desc":"Agendar la 2da entrevista (Gerencia) para el puesto de VP de Marketing.", "due":str(date.today() + timedelta(days=5)), "assigned_to": "Coordinador RR.HH.", "status": "En Proceso", "priority": "Media", "created_at": (date.today() - timedelta(days=8)).isoformat()},
    {"id": str(uuid.uuid4()), "titulo":"Crear workflow de Onboarding", "desc":"Definir pasos en 'Flujos' para Contratado.", "due":str(date.today() - timedelta(days=1)), "assigned_to": "Admin RR.HH.", "status": "Completada", "priority": "Baja", "created_at": (date.today() - timedelta(days=15)).isoformat()},
    {"id": str(uuid.uuid4()), "titulo":"Análisis Detallado de CV_MartaDiaz.pdf", "desc":"Utilizar el agente de análisis para generar un informe de brechas de skills.", "due":str(date.today() + timedelta(days=3)), "assigned_to": "Agente de Análisis", "status": "Pendiente", "priority": "Media", "created_at": date.today().isoformat()}
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
if "llm_results" not in ss: ss.llm_results = []           # resultados LLM centralizados
if "eval_llm_busy" not in ss: ss.eval_llm_busy = False    # loader Evaluación de CVs

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

# índice rápido de resultados LLM por filename
def _llm_index():
    return { (r.get("file_name") or r.get("file") or r.get("name") or "").strip(): r for r in (ss.llm_results or []) if r }

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

# ===================== Analítica global =====================
def calculate_analytics(candidates):
  """
  Unifica: Pipeline, LLM, Puestos y Tareas. Mantiene los componentes y estilo actuales.
  """
  candidates = candidates or []
  jd = ss.get("last_jd_text", "")
  preset = ROLE_PRESETS.get(ss.get("last_role", ""), {})
  must, nice = preset.get("must", []), preset.get("nice", [])

  # Skills Fit + pipeline
  fits = []
  stages = {s: 0 for s in PIPELINE_STAGES}
  sources = {}
  time_to_stage_days = []
  hired_days = []

  for c in candidates:
    # Usa el score pre-calculado si existe, sino lo calcula
    score = c.get("Score")
    if score is None:
        txt = c.get("_text") or (c.get("_bytes") or b"").decode("utf-8", "ignore")
        score, _ = score_fit_by_skills(jd, must, nice, txt or "")
    fits.append(int(score))

    stage = c.get("stage", PIPELINE_STAGES[0])
    stages[stage] = stages.get(stage, 0) + 1
    src = c.get("source", "Carga Manual")
    sources[src] = sources.get(src, 0) + 1

    # tiempos: desde load_date -> hoy (proxy) o hire_date si existe
    try:
      ld_str = c.get("load_date", date.today().isoformat())
      ld = datetime.fromisoformat(ld_str).date() # Asegura que sea date

      end_date = date.today() # Por defecto es hoy
      if stage == "Contratado" and c.get("hire_date"):
          try:
              end_date = datetime.fromisoformat(c["hire_date"]).date() # Usa hire_date si existe
          except: pass # Si hire_date es inválido, usa hoy

      days = max(0, (end_date - ld).days)
      time_to_stage_days.append(days)
      if stage == "Contratado":
        hired_days.append(days)
    except:
      pass # Ignora errores de fecha para no romper el cálculo

  avg_fit = round(sum(fits) / len(fits), 1) if fits else 0
  df_funnel = pd.DataFrame({"Fase": PIPELINE_STAGES, "Candidatos": [stages.get(s, 0) for s in PIPELINE_STAGES]})
  df_sources = pd.DataFrame(list(sources.items()), columns=["Fuente", "Candidatos"]).sort_values("Candidatos", ascending=False)

  # P50 / P90 sobre tiempos (proxy)
  def p50(vals):
      if not vals: return 0
      return int(round(statistics.median(sorted(vals))))
  def p90(vals):
      if not vals: return 0
      s=sorted(vals); idx=max(0,int(round(0.9*(len(s)-1))))
      return int(s[idx])

  ttx_p50 = p50(time_to_stage_days)
  ttx_p90 = p90(time_to_stage_days)
  tth_p50 = p50(hired_days) if hired_days else 0
  tth_p90 = p90(hired_days) if hired_days else 0

  # LLM
  llm_map = _llm_index()
  df_llm = pd.DataFrame([{
      "file_name": k,
      "Name": v.get("Name","—"),
      "Score_LLM": int(str(v.get("Score",0)).replace("%","")) if str(v.get("Score","")).strip() else 0
  } for k,v in llm_map.items()]) if llm_map else pd.DataFrame(columns=["file_name","Name","Score_LLM"])
  avg_llm = round(df_llm["Score_LLM"].mean(), 1) if not df_llm.empty else 0

  # Exactitud de IA (proxy): correlación Fit skills vs LLM cuando filename coincide
  join_rows=[]
  name_to_fit={str(c.get("Name","")).strip():c.get("Score",0) for c in candidates}
  for _,r in df_llm.iterrows():
    nm=r["file_name"]
    if nm in name_to_fit:
      join_rows.append({"file_name":nm,"Fit_Skills":name_to_fit[nm],"Score_LLM":r["Score_LLM"]})
  df_corr=pd.DataFrame(join_rows)
  corr_val = round(float(df_corr.corr(numeric_only=True).get("Fit_Skills",{}).get("Score_LLM",0)),3) if not df_corr.empty and len(df_corr) > 1 else 0.0 # Corr necesita > 1 punto

  # Puestos
  df_pos = ss.positions.copy() if isinstance(ss.get("positions"), pd.DataFrame) else pd.DataFrame()
  puestos_activos = int((df_pos["Estado"] == "Abierto").sum()) if not df_pos.empty else 0

  # Productividad del reclutador (proxy): tareas completadas por asignado
  tasks = ss.tasks if isinstance(ss.get("tasks"), list) else []
  prod_map={}
  for t in tasks:
    if t.get("status")=="Completada":
      prod_map[t.get("assigned_to","—")] = prod_map.get(t.get("assigned_to","—"),0)+1
  df_prod = pd.DataFrame(list(prod_map.items()), columns=["Usuario/Equipo","Completadas"]).sort_values("Completadas", ascending=False)

  # Costo por hire (proxy): parámetros simples
  COSTO_POR_CV = 1.5  # USD por revisión
  COSTO_ENTREVISTA = 6.0
  hires = stages.get("Contratado", 0)
  entrevistas = stages.get("Entrevista Telefónica", 0) + stages.get("Entrevista Gerencia", 0)
  costo_total = (len(candidates)*COSTO_POR_CV) + (entrevistas*COSTO_ENTREVISTA)
  costo_por_hire = round(costo_total / hires, 2) if hires>0 else 0.0

  return {
    "avg_fit_skills": avg_fit,
    "avg_llm_score": avg_llm,
    "corr_fit_vs_llm": corr_val,
    "puestos_activos": puestos_activos,
    "total_candidatos": len(candidates),
    "funnel_data": df_funnel,
    "sources_data": df_sources,
    "llm_data": df_llm,
    "corr_data": df_corr,
    "productividad": df_prod,
    "ttx_p50": ttx_p50,
    "ttx_p90": ttx_p90,
    "tth_p50": tth_p50,
    "tth_p90": tth_p90,
    "costo_hire": costo_por_hire
  }

# ====== Helpers de TAREAS ======
def _status_pill(s: str)->str:
  colors = { "Pendiente": "#9AA6B2", "En Proceso": "#0072E3", "Completada": "#10B981", "En Espera": "#FFB700" }
  c = colors.get(s, "#9AA6B2")
  return f'<span class="badge" style="border-color:{c}33;background:{c}14;color:#0A2230">{s}</span>'

def _priority_pill(p: str) -> str:
    p_safe = p if p in TASK_PRIORITIES else "Media"
    return f'<span class="badge priority-{p_safe}">{p_safe}</span>'

def create_task_from_flow(name:str, due_date:date, desc:str, assigned:str="Coordinador RR.HH.", status:str="Pendiente", priority:str="Media"):
  t = {
    "id": str(uuid.uuid4()),
    "titulo": f"Ejecutar flujo: {name}",
    "desc": desc or "Tarea generada desde Flujos.",
    "due": due_date.isoformat(),
    "assigned_to": assigned,
    "status": status,
    "priority": priority if priority in TASK_PRIORITIES else "Media",
    "created_at": date.today().isoformat(),
  }
  if not isinstance(ss.tasks, list): ss.tasks = []
  ss.tasks.insert(0, t)
  save_tasks(ss.tasks)

# =========================================================
# INICIALIZACIÓN DE CANDIDATOS
# =========================================================
if "candidate_init" not in ss:
  initial_candidates = [
    {"Name": "CV_AnaLopez.pdf", "Score": 85, "Role": "Business Analytics", "source": "LinkedIn Jobs", "load_date": (date.today() - timedelta(days=25)).isoformat()},
    {"Name": "CV_LuisGomez.pdf", "Score": 42, "Role": "Business Analytics", "source": "Computrabajo", "load_date": (date.today() - timedelta(days=18)).isoformat()},
    {"Name": "CV_MartaDiaz.pdf", "Score": 91, "Role": "Desarrollador/a Backend (Python)", "source": "Indeed", "load_date": (date.today() - timedelta(days=12)).isoformat()},
    {"Name": "CV_JaviRuiz.pdf", "Score": 30, "Role": "Diseñador/a UX", "source": "laborum.pe", "load_date": (date.today() - timedelta(days=5)).isoformat()},
  ]
  candidates_list = []
  for i, c in enumerate(initial_candidates):
    c["id"] = f"C{i+1}-{random.randint(1000, 9999)}"
    c["stage"] = PIPELINE_STAGES[random.choice([0, 1, 1, 2, 6])]
    #c["load_date"] = (date.today() - timedelta(days=random.randint(5, 30))).isoformat() # Usar las fechas predefinidas
    c["_bytes"] = DUMMY_PDF_BYTES
    c["_is_pdf"] = True
    c["_text"] = f"CV de {c['Name']}. Experiencia 5 años. Skills: SQL, Power BI, Python, Excel. Candidato {c['Name']}."
    c["meta"] = extract_meta(c["_text"])
    if c["stage"] == "Descartado": c["Score"] = random.randint(20, 34)
    if c["stage"] == "Contratado":
        c["Score"] = 95
        c["hire_date"] = (datetime.fromisoformat(c["load_date"]) + timedelta(days=random.randint(7,20))).date().isoformat() # Fecha de contratación para los de ejemplo

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

    # TAREAS
    st.markdown("#### TAREAS")
    if st.button("Todas las tareas", key="sb_task_manual"): ss.section = "create_task"
    if st.button("Asignado a mi", key="sb_task_hh"): ss.section = "hh_tasks"
    if st.button("Asignado a mi equipo", key="sb_task_agente"): ss.section = "agent_tasks"

    st.markdown("#### ACCIONES")
    if st.button("Cerrar sesión", key="sb_logout"):
      ss.auth = None; st.rerun()

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
          txt=f"CV de Candidato {board} / {puesto}. Experiencia {random.randint(2, 10)} años. Skills: SQL, Python, Excel."
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

def page_puestos():
  st.header("Puestos")
  df_pos = ss.positions.copy()
  df_pos["Time to Hire"] = df_pos["Días Abierto"].apply(lambda d: f"{d+random.randint(10, 40)} días" if d < 30 else f"{d} días") # Nombre simplificado
  st.dataframe(
    df_pos[
      ["Puesto","Días Abierto","Time to Hire","Leads","Nuevos","Recruiter Screen","HM Screen",
       "Entrevista Telefónica","Entrevista Presencial","Ubicación","Hiring Manager","Estado","ID"]
    ].sort_values(["Estado","Días Abierto","Leads"], ascending=[True,True,False]),
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
    else:
      st.info(f"No hay candidatos activos para el puesto **{selected_pos}**.")

# =========================================================
# PÁGINA EVAL (MODIFICADA CON LOADER Y REORDENADA)
# =========================================================
def page_eval():
    st.header("Resultados de evaluación")

    # --------- Bloque LLM con loader animado (MOVIDO ARRIBA) ----------
    st.subheader("Evaluación IA")
    llm_files = st.file_uploader("Subir CVs (PDF) para evaluación IA", type=["pdf"], accept_multiple_files=True, key="llm_upl")

    # Contenedor para loader
    loader_slot = st.empty()

    def _render_loader(show: bool):
        """Muestra u oculta el loader animado."""
        if not show:
            loader_slot.empty()
            return
        # Animación CSS inline
        loader_slot.markdown(f"""
        <div style="display:flex; align-items:center; gap:10px; padding:10px 12px; border:1px solid #E3EDF6; border-radius:12px; background:#FFFFFF; max-width:280px; margin-bottom:10px;">
          <div style="width:16px; height:16px; border:3px solid #E3EDF6; border-top-color:{PRIMARY}; border-radius:50%; animation:spin 0.9s linear infinite;"></div>
          <div style="font-weight:600; color:{TITLE_DARK};">Analizando CVs…</div>
        </div>
        <style>@keyframes spin {{ to {{ transform: rotate(360deg); }} }}</style>
        """, unsafe_allow_html=True)

    # Mostrar loader si está ocupado
    if ss.eval_llm_busy:
        _render_loader(True)

    # Botón de ejecución, deshabilitado si está ocupado
    # La clave 'btn_eval_llm_click' se usa para detectar el click DESPUÉS del rerun
    if st.button("Ejecutar evaluación IA", disabled=ss.eval_llm_busy, key="btn_eval_llm"):
        if not llm_files:
            st.warning("Sube al menos un PDF.")
        else:
            ss.eval_llm_busy = True
            ss.btn_eval_llm_click = True # Marca que el botón fue clickeado
            st.rerun() # Rerun para mostrar loader y deshabilitar botón

    # Lógica de procesamiento: se ejecuta DESPUÉS del rerun si el botón fue clickeado
    if ss.eval_llm_busy and ss.get("btn_eval_llm_click"):
        ss.btn_eval_llm_click = False # Resetea la marca del click
        try:
            results = []
            # --- Proxy de evaluación ---
            jd = ss.get("last_jd_text","")
            preset = ROLE_PRESETS.get(ss.get("last_role",""), {})
            must_list = preset.get("must",[]) or []
            nice_list = preset.get("nice",[]) or []

            # Usa los archivos que están actualmente en el widget uploader
            # Es importante que el key="llm_upl" sea consistente
            current_files = st.session_state.get("llm_upl", [])

            for uploaded_file in current_files:
                try:
                    # Lee el archivo (importante hacerlo aquí por si Streamlit lo limpia)
                    b = uploaded_file.read()
                    # Resetea el puntero por si se lee de nuevo
                    uploaded_file.seek(0)
                    # Extrae texto (usando la función existente)
                    text = extract_text_from_file(uploaded_file)
                    # Calcula score proxy
                    score, _ = score_fit_by_skills(jd, must_list, nice_list, text or "")
                    results.append({
                        "file_name": uploaded_file.name,
                        "Name": uploaded_file.name.replace(".pdf","").replace("_"," "), # Nombre más limpio
                        "Score": int(score) # Score proxy
                    })
                except Exception as file_e:
                    st.warning(f"Error procesando {uploaded_file.name}: {file_e}")
                    results.append({
                        "file_name": uploaded_file.name,
                        "Name": uploaded_file.name.replace(".pdf","").replace("_"," "),
                        "Score": 0,
                        "Error": str(file_e)
                    })

            ss.llm_results = results # Guarda resultados en sesión

            # Actualiza pipeline con Score_LLM
            try:
                name_to_cand = { str(c.get("Name","")).strip(): c for c in ss.candidates }
                for r in results:
                    fn = str(r.get("file_name","")).strip()
                    if fn in name_to_cand and "Error" not in r:
                        name_to_cand[fn]["Score_LLM"] = int(r.get("Score",0))
            except Exception as update_e:
                print(f"Error actualizando scores IA en pipeline: {update_e}")

            st.success("Evaluación IA completada.")

        except Exception as e:
            st.error(f"Ocurrió un error durante la evaluación: {e}")
        finally:
            ss.eval_llm_busy = False # Termina estado busy
            st.rerun() # Rerun final para quitar loader y habilitar botón

    # Mostrar resultados IA si existen
    if ss.llm_results:
        df_llm = pd.DataFrame(ss.llm_results)
        st.dataframe(df_llm.rename(columns={"Score":"Score IA"}), use_container_width=True, hide_index=True)
        try:
            df_plot = df_llm[df_llm.get("Error").isna()] if "Error" in df_llm.columns else df_llm
            if not df_plot.empty:
                fig_llm = px.bar(df_plot, x='file_name', y='Score', text='Score', title="Comparativa de Puntajes (IA)")
                fig_llm.update_traces(hovertemplate="%{x}<br>Score: %{y}%")
                fig_llm.update_layout(plot_bgcolor="#FFFFFF", paper_bgcolor="rgba(0,0,0,0)", font=dict(color=TITLE_DARK), xaxis_title=None, yaxis_title="Score IA (%)")
                st.plotly_chart(fig_llm, use_container_width=True)
        except Exception as plot_e:
            print(f"Error graficando resultados IA: {plot_e}")

    st.markdown("---") # Separador antes del ranking

    # --------- Ranking por Fit de Skills (permanece igual) --------
    st.subheader("Ranking por Fit de Skills")
    if not ss.candidates:
        st.info("Carga CVs en **Publicación & Sourcing** o usa **Evaluación IA**."); return

    # Recalcula scores de skills (puede que hayan cambiado JD/Must/Nice)
    jd_text = st.text_area("JD para matching por skills", ss.get("last_jd_text",""), height=140, key="jd_skills_eval")
    preset = ROLE_PRESETS.get(ss.get("last_role",""), {})
    col1,col2 = st.columns(2)
    with col1: must_default = st.text_area("Must-have (coma separada)", value=", ".join(preset.get("must",[])), key="must_skills_eval")
    with col2: nice_default = st.text_area("Nice-to-have (coma separada)", value=", ".join(preset.get("nice",[])), key="nice_skills_eval")
    must = [s.strip() for s in (must_default or "").split(",") if s.strip()]
    nice = [s.strip() for s in (nice_default or "").split(",") if s.strip()]

    enriched = []
    for c in ss.candidates:
        cv = c.get("_text") or (c.get("_bytes") or b"").decode("utf-8","ignore")
        fit, exp = score_fit_by_skills(jd_text, must, nice, cv or "")
        c["Score"] = fit # Actualiza el score de skills en el candidato
        c["_exp"] = exp # Guarda la explicación
        enriched.append({
            "id": c["id"],
            "Name": c["Name"],
            "Fit": fit,
            "Must (ok/total)":f"{len(exp['matched_must'])}/{exp['must_total']}",
            "Nice (ok/total)":f"{len(exp['matched_nice'])}/{exp['nice_total']}",
            "Extras":", ".join(exp["extras"])[:60]
        })
    df = pd.DataFrame(enriched).sort_values("Fit", ascending=False).reset_index(drop=True)

    st.dataframe(df[["Name","Fit","Must (ok/total)","Nice (ok/total)","Extras"]], use_container_width=True, height=250)

    # --------- Detalle y explicación (permanece igual) ----------
    st.subheader("Detalle y explicación")
    if not df.empty:
        selected_name = st.selectbox("Elige un candidato", df["Name"].tolist())
        selected_id = df[df["Name"] == selected_name]["id"].iloc[0]
        candidate_obj = next((c for c in ss.candidates if c["id"] == selected_id), None)
        if candidate_obj:
            fit = candidate_obj["Score"]; exp = candidate_obj.get("_exp", {}) # Usa la explicación guardada
            cv_bytes = candidate_obj.get("_bytes", b""); cv_text = candidate_obj.get("_text", ""); is_pdf = candidate_obj.get("_is_pdf", False)
            c1,c2=st.columns([1.1,0.9])
            with c1:
                fig=px.bar(pd.DataFrame([{"Candidato":selected_name,"Fit":fit}]), x="Candidato", y="Fit", title="Fit por skills", color_discrete_sequence=[PRIMARY])
                fig.update_traces(hovertemplate="%{x}<br>Fit: %{y}%")
                fig.update_layout(plot_bgcolor="#FFFFFF", paper_bgcolor="rgba(0,0,0,0)",font=dict(color=TITLE_DARK),xaxis_title=None,yaxis_title="Fit")
                st.plotly_chart(fig, use_container_width=True)
                st.markdown("**Explicación**")
                st.markdown(f"- **Must-have:** {len(exp.get('matched_must',[]))}/{exp.get('must_total',0)}")
                if exp.get("matched_must"): st.markdown(" - ✓ " + ", ".join(exp["matched_must"]))
                if exp.get("gaps_must"): st.markdown(" - ✗ Faltantes: " + ", ".join(exp["gaps_must"]))
                st.markdown(f"- **Nice-to-have:** {len(exp.get('matched_nice',[]))}/{exp.get('nice_total',0)}")
                if exp.get("matched_nice"): st.markdown(" - ✓ " + ", ".join(exp["matched_nice"]))
                if exp.get("gaps_nice"): st.markdown(" - ✗ Faltantes: " + ", ".join(exp["gaps_nice"]))
                if exp.get("extras"): st.markdown("- **Extras:** " + ", ".join(exp["extras"]))
            with c2:
                st.markdown("**CV (visor)**")
                if is_pdf and cv_bytes:
                    pdf_viewer_embed(cv_bytes, height=420)
                else:
                    st.text_area("Contenido (TXT)", cv_text, height=420)
        else:
            st.error("No se encontraron los detalles del candidato en la sesión.")
    else:
        st.info("No hay candidatos para mostrar detalles.")

# =========================================================
# PÁGINA PIPELINE (MODIFICADA CON HIRE_DATE y SCORE_LLM)
# =========================================================
def page_pipeline():
    filter_stage = ss.get("pipeline_filter")
    if filter_stage:
        st.header(f"Pipeline: Candidatos en Fase '{filter_stage}'")
        candidates_to_show = [c for c in ss.candidates if c.get("stage") == filter_stage]
    else:
        st.header("Pipeline de Candidatos (Vista Kanban)")
        candidates_to_show = ss.candidates
    st.caption("Mueve los candidatos a través de las etapas para avanzar el proceso.") # Texto actualizado
    if not candidates_to_show and filter_stage:
          st.info(f"No hay candidatos en la fase **{filter_stage}**."); return
    elif not ss.candidates:
          st.info("No hay candidatos activos. Carga CVs en **Publicación & Sourcing** o **Evaluación de CVs**."); return
    candidates_by_stage = {stage: [] for stage in PIPELINE_STAGES}
    for c in candidates_to_show:
        candidates_by_stage[c.get("stage", PIPELINE_STAGES[0])].append(c) # Usa .get por seguridad
    cols = st.columns(len(PIPELINE_STAGES))
    for i, stage in enumerate(PIPELINE_STAGES):
        with cols[i]:
            st.markdown(f"**{stage} ({len(candidates_by_stage[stage])})**", unsafe_allow_html=True)
            st.markdown("---")
            for c in candidates_by_stage[stage]:
                score = c.get("Score", 0) # Score de skills
                score_llm = c.get("Score_LLM") # Score de IA
                card_name = c["Name"].split('_')[-1].replace('.pdf', '').replace('.txt', '')
                extra_llm = f"<span style='font-size:11px;opacity:.7'> · IA:{int(score_llm)}%</span>" if score_llm is not None else "" # Muestra score IA si existe
                st.markdown(f"""
                <div class="k-card" style="margin-bottom: 10px; border-left: 4px solid {PRIMARY if score >= 70 else ('#FFA500' if score >= 40 else '#D60000')}">
                    <div style="font-weight:700; color:{TITLE_DARK};">{card_name}</div>
                    <div style="font-size:12px; opacity:.8;">{c.get("Role", "Puesto Desconocido")}</div>
                    <div style="font-size:14px; font-weight:700; margin-top:8px;">Fit: <span style="color:{PRIMARY};">{score}%</span>{extra_llm}</div>
                    <div style="font-size:10px; opacity:.6; margin-top:4px;">Fuente: {c.get("source", "N/A")}</div>
                </div>
                """, unsafe_allow_html=True)
                with st.form(key=f"form_move_{c['id']}", clear_on_submit=False):
                    current_stage = c.get("stage", PIPELINE_STAGES[0])
                    current_stage_index = PIPELINE_STAGES.index(current_stage)
                    available_stages = [s for s in PIPELINE_STAGES if s != current_stage]
                    try:
                        # Intenta poner la siguiente etapa como default, o la última si ya está al final
                        next_stage_candidate = PIPELINE_STAGES[min(current_stage_index + 1, len(PIPELINE_STAGES) - 1)]
                        if next_stage_candidate in available_stages:
                             default_index = available_stages.index(next_stage_candidate)
                        elif current_stage_index > 0 and PIPELINE_STAGES[current_stage_index -1] in available_stages: # fallback a la anterior si siguiente no aplica (ej: descartado)
                            default_index = available_stages.index(PIPELINE_STAGES[current_stage_index -1])
                        else: default_index = 0 # fallback a la primera
                    except ValueError:
                        default_index = 0
                    new_stage = st.selectbox("Mover a:", available_stages, key=f"select_move_{c['id']}", index=default_index, label_visibility="collapsed")
                    if st.form_submit_button("Mover Candidato"):
                        c["stage"] = new_stage
                        # Registrar fecha de contratación
                        if new_stage == "Contratado":
                            c["hire_date"] = date.today().isoformat() # <-- AÑADIDO hire_date
                            st.balloons()
                            st.success(f"🎉 **¡Éxito!** Flujo de Onboarding disparado para {card_name}.")
                        # Lógica existente
                        elif new_stage == "Descartado":
                            st.success(f"📧 **Comunicación:** Email de rechazo enviado a {card_name}.")
                        elif new_stage == "Entrevista Telefónica":
                            st.info(f"📅 **Automatización:** Tarea de programación de entrevista generada para {card_name}.")
                            create_task_from_flow(f"Programar entrevista - {card_name}", date.today()+timedelta(days=2),
                                                  "Coordinar entrevista telefónica con el candidato.", assigned="Headhunter", status="Pendiente")

                        if filter_stage and new_stage != filter_stage:
                            ss.pipeline_filter = None
                            st.info("El filtro ha sido removido al mover el candidato de fase.")
                        st.rerun()
                st.markdown("<br>", unsafe_allow_html=True)

def page_interview():
  st.header("Entrevista (Gerencia)")
  st.write("Esta página ahora redirige al **Pipeline** con el filtro **Entrevista Gerencia**.")
  st.info("Por favor, usa el **Pipeline de Candidatos** y el filtro del menú lateral para gestionar esta etapa de forma visual.")
  ss.section = "pipeline"; ss.pipeline_filter = "Entrevista Gerencia"; st.rerun()

def _ensure_offer_record(cand_name: str):
  if cand_name not in ss.offers:
    ss.offers[cand_name] = {
      "puesto": "", "ubicacion": "", "modalidad": "Presencial", "salario": "", "beneficios": "",
      "fecha_inicio": date.today() + timedelta(days=14), "caducidad": date.today() + timedelta(days=7),
      "aprobadores": "Gerencia, Legal, Finanzas", "estado": "Borrador"
    }

def page_offer():
  st.header("Oferta")
  st.write("Esta página ahora redirige al **Pipeline** con el filtro **Oferta**.")
  st.info("Por favor, usa el **Pipeline de Candidatos** y el filtro del menú lateral para gestionar esta etapa de forma visual.")
  ss.section = "pipeline"; ss.pipeline_filter = "Oferta"; st.rerun()

def page_onboarding():
  st.header("Onboarding")
  st.write("Esta página ahora redirige al **Pipeline** con el filtro **Contratado**.")
  st.info("Por favor, usa el **Pipeline de Candidatos** y el filtro del menú lateral para gestionar esta etapa de forma visual.")
  ss.section = "pipeline"; ss.pipeline_filter = "Contratado"; st.rerun()

def page_hh_tasks():
    st.header("Tareas Asignadas a Mí")
    st.write("Esta página lista las tareas asignadas a tu rol (Headhunter/Colaborador).")
    if not isinstance(ss.tasks, list) or not ss.tasks: st.info("No tienes tareas asignadas."); return
    df_tasks = pd.DataFrame(ss.tasks)
    my_name = ss.auth["name"] if ss.get("auth") else "Colab"
    my_tasks = df_tasks[df_tasks["assigned_to"].isin(["Headhunter", "Colaborador", my_name])]
    all_statuses = ["Todos"] + sorted(my_tasks["status"].unique())
    prefer_order = ["Pendiente", "En Proceso", "En Espera"]
    preferred = next((s for s in prefer_order if s in all_statuses), "Todos")
    selected_status = st.selectbox("Filtrar por Estado", all_statuses, index=all_statuses.index(preferred))
    my_tasks_filtered = my_tasks if selected_status=="Todos" else my_tasks[my_tasks["status"] == selected_status]
    if not my_tasks_filtered.empty:
        st.dataframe(
            my_tasks_filtered.rename(
                columns={"titulo":"Título", "desc":"Descripción", "due":"Vencimiento", "assigned_to": "Asignado a", "status": "Estado", "created_at": "Fecha de Creación", "priority": "Prioridad"}
            )[["Título", "Descripción", "Estado", "Prioridad", "Vencimiento", "Fecha de Creación"]],
            use_container_width=True, hide_index=True
        )
    else:
        st.info(f"No hay tareas en el estado '{selected_status}' asignadas directamente.")

def page_agent_tasks():
    st.header("Tareas Asignadas a mi Equipo")
    st.write("Esta página lista las tareas generadas por Flujos y asignadas a roles de equipo.")
    if not isinstance(ss.tasks, list) or not ss.tasks: st.write("No hay tareas pendientes en el equipo."); return
    df_tasks = pd.DataFrame(ss.tasks)
    team_tasks = df_tasks[df_tasks["assigned_to"].isin(["Coordinador RR.HH.", "Admin RR.HH.", "Agente de Análisis"])]
    all_statuses = ["Todos"] + sorted(team_tasks["status"].unique())
    prefer_order = ["Pendiente", "En Proceso", "En Espera"]
    preferred = next((s for s in prefer_order if s in all_statuses), "Todos")
    selected_status = st.selectbox("Filtrar por Estado", all_statuses, index=all_statuses.index(preferred), key="agent_task_filter")
    team_tasks_filtered = team_tasks if selected_status=="Todos" else team_tasks[team_tasks["status"] == selected_status]
    if not team_tasks_filtered.empty:
        st.dataframe(
            team_tasks_filtered.rename(
                columns={"titulo":"Título", "desc":"Descripción", "due":"Vencimiento", "assigned_to": "Asignado a", "status": "Estado", "created_at": "Fecha de Creación", "priority": "Prioridad"}
            )[["Título", "Descripción", "Asignado a", "Estado", "Prioridad", "Vencimiento", "Fecha de Creación"]],
            use_container_width=True, hide_index=True
        )
    else:
        st.info(f"No hay tareas en el estado '{selected_status}' asignadas al equipo.")

# ===================== AGENTES =====================
def page_agents():
  st.header("Agentes")
  st.subheader("Crear / Editar agente")
  left, _ = st.columns([0.25, 0.75])
  with left:
    if st.button(("➕ Nuevo" if not ss.new_role_mode else "✖ Cancelar"), key="toggle_new_role"):
      ss.new_role_mode = not ss.new_role_mode
      if ss.new_role_mode:
        ss.agent_view_idx = None; ss.agent_edit_idx = None
      st.rerun()

  if ss.new_role_mode:
    st.info("Completa el formulario para crear un nuevo rol/agente.")
    with st.form("agent_new_form"):
      c1, c2 = st.columns(2)
      with c1:
        role_name  = st.text_input("Rol*", value="")
        objetivo   = st.text_input("Objetivo*", value="Identificar a los mejores profesionales para el cargo definido en el JD")
        backstory  = st.text_area("Backstory*", value="Eres un analista de RR.HH. con experiencia en análisis de documentos, CV y currículums.", height=120)
        guardrails = st.text_area("Guardrails", value="No compartas datos sensibles. Cita la fuente (CV o JD) al argumentar.", height=90)
      with c2:
        herramientas = st.multiselect("Herramientas habilitadas", ["Parser de PDF","Recomendador de skills","Comparador JD-CV"], default=["Parser de PDF","Recomendador de skills"])
        llm_model  = st.selectbox("Modelo LLM", LLM_MODELS, index=0)
        img_src    = st.text_input("URL de imagen", value=AGENT_DEFAULT_IMAGES.get("Headhunter",""))
        perms      = st.multiselect("Permisos (quién puede editar)", ["Colaborador","Supervisor","Administrador"], default=["Supervisor","Administrador"])
      saved = st.form_submit_button("Guardar/Actualizar Agente")
      if saved:
        rn = (role_name or "").strip()
        if not rn:
          st.error("El campo Rol* es obligatorio.")
        else:
          ss.agents.append({
            "rol": rn, "objetivo": objetivo, "backstory": backstory,
            "guardrails": guardrails, "herramientas": herramientas,
            "llm_model": llm_model, "image": img_src, "perms": perms,
            "ts": datetime.utcnow().isoformat()
          })
          save_agents(ss.agents)
          roles_new = sorted(list({*ss.roles, rn})); ss.roles = roles_new; save_roles(roles_new)
          st.success("Agente creado.")
          ss.new_role_mode = False
          st.rerun()

  st.subheader("Tus agentes")
  if not ss.agents:
    st.info("Aún no hay agentes. Crea el primero con **➕ Nuevo**.")
    return

  cols_per_row = 5
  for i in range(0, len(ss.agents), cols_per_row):
    row_agents = ss.agents[i:i+cols_per_row]
    cols = st.columns(cols_per_row)
    for j, ag in enumerate(row_agents):
      idx = i + j
      with cols[j]:
        img = ag.get("image") or AGENT_DEFAULT_IMAGES.get(ag.get("rol","Headhunter"))
        st.markdown(f'<div class="agent-card"><img src="{img}"><div class="agent-title">{ag.get("rol","—")}</div><div class="agent-sub">{ag.get("objetivo","—")}</div></div>', unsafe_allow_html=True)
        st.markdown('<div class="toolbar">', unsafe_allow_html=True)
        c1, c2, c3, c4 = st.columns(4)
        with c1:
          if st.button("👁", key=f"ag_v_{idx}", help="Ver"): ss.agent_view_idx = (None if ss.agent_view_idx == idx else idx); ss.agent_edit_idx = None; st.rerun()
        with c2:
          if st.button("✏", key=f"ag_e_{idx}", help="Editar"): ss.agent_edit_idx = (None if ss.agent_edit_idx == idx else idx); ss.agent_view_idx = None; st.rerun()
        with c3:
          if st.button("🧬", key=f"ag_c_{idx}", help="Clonar"): clone = dict(ag); clone["rol"] = f"{ag.get('rol','Agente')} (copia)"; ss.agents.append(clone); save_agents(ss.agents); st.success("Agente clonado."); st.rerun()
        with c4:
          if st.button("🗑", key=f"ag_d_{idx}", help="Eliminar"): ss.agents.pop(idx); save_agents(ss.agents); st.success("Agente eliminado."); st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

  if ss.agent_view_idx is not None and 0 <= ss.agent_view_idx < len(ss.agents):
    ag = ss.agents[ss.agent_view_idx]
    st.markdown("### Detalle del agente"); st.caption("Modelo LLM")
    st.markdown('<div class="agent-detail">', unsafe_allow_html=True)
    c1, c2 = st.columns([0.42, 0.58])
    with c1:
      raw_img = ag.get("image") or ""
      safe_img = (raw_img.strip() if isinstance(raw_img, str) and raw_img.strip() else AGENT_DEFAULT_IMAGES.get(ag.get("rol","Headhunter"), AGENT_DEFAULT_IMAGES["Headhunter"]))
      st.markdown(f'<div style="text-align:center;margin:6px 0 12px"><img src="{safe_img}" style="width:180px;height:180px;border-radius:999px;object-fit:cover;border:4px solid #F1F7FD;"></div>', unsafe_allow_html=True)
      st.caption("Modelo LLM"); st.markdown(f"<div class='badge'>🧠 {ag.get('llm_model','gpt-4o-mini')}</div>", unsafe_allow_html=True)
    with c2:
      st.text_input("Role*", value=ag.get("rol",""), disabled=True)
      st.text_input("Objetivo*", value=ag.get("objetivo",""), disabled=True)
      st.text_area("Backstory*", value=ag.get("backstory",""), height=120, disabled=True)
      st.text_area("Guardrails", value=ag.get("guardrails",""), height=90, disabled=True)
      st.caption("Herramientas habilitadas"); st.write(", ".join(ag.get("herramientas",[])) or "—")
      st.caption("Permisos"); st.write(", ".join(ag.get("perms",[])) or "—")
    st.markdown('</div>', unsafe_allow_html=True)

  if ss.agent_edit_idx is not None and 0 <= ss.agent_edit_idx < len(ss.agents):
    ag = ss.agents[ss.agent_edit_idx]
    st.markdown("### Editar agente")
    with st.form(f"agent_edit_{ss.agent_edit_idx}"):
      objetivo   = st.text_input("Objetivo*", value=ag.get("objetivo",""))
      backstory  = st.text_area("Backstory*", value=ag.get("backstory",""), height=120)
      guardrails = st.text_area("Guardrails", value=ag.get("guardrails",""), height=90)
      herramientas = st.multiselect("Herramientas habilitadas", ["Parser de PDF","Recomendador de skills","Comparador JD-CV"], default=ag.get("herramientas",["Parser de PDF","Recomendador de skills"]))
      llm_model    = st.selectbox("Modelo LLM", LLM_MODELS, index=max(0, LLM_MODELS.index(ag.get("llm_model","gpt-4o-mini"))))
      img_src      = st.text_input("URL de imagen", value=ag.get("image",""))
      perms        = st.multiselect("Permisos (quién puede editar)", ["Colaborador","Supervisor","Administrador"], default=ag.get("perms",["Supervisor","Administrador"]))
      if st.form_submit_button("Guardar cambios"):
        ag.update({"objetivo":objetivo,"backstory":backstory,"guardrails":guardrails,"herramientas": herramientas,
                   "llm_model":llm_model,"image":img_src,"perms":perms})
        save_agents(ss.agents); st.success("Agente actualizado."); st.rerun()

# ===================== FLUJOS =====================
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
        sel = st.selectbox("Selecciona un flujo", [r["ID"] for r in rows],
                           format_func=lambda x: next((r["Nombre"] for r in rows if r["ID"]==x), x))
        wf = next((w for w in ss.workflows if w["id"]==sel), None)
        if wf:
          c1,c2,c3 = st.columns(3)
          with c1:
            if st.button("🧬 Duplicar"):
              clone = dict(wf); clone["id"] = f"WF-{int(datetime.now().timestamp())}"
              clone["status"]="Borrador"; clone["approved_by"]=""; clone["approved_at"]=""; clone["schedule_at"]=""
              ss.workflows.insert(0, clone); save_workflows(ss.workflows); st.success("Flujo duplicado.")
              st.rerun()
          with c2:
            if st.button("🗑 Eliminar"):
              ss.workflows = [w for w in ss.workflows if w["id"]!=wf["id"]]; save_workflows(ss.workflows)
              st.success("Flujo eliminado.")
              st.rerun()
          with c3:
            st.markdown(f"<div class='badge'>Estado: <b>{wf.get('status','Borrador')}</b></div>", unsafe_allow_html=True)
            if wf.get("status")=="Pendiente de aprobación" and puede_aprobar:
              a1,a2 = st.columns(2)
              with a1:
                if st.button("✅ Aprobar"):
                  wf["status"]="Aprobado"; wf["approved_by"]=vista_como; wf["approved_at"]=datetime.now().isoformat()
                  save_workflows(ss.workflows); st.success("Aprobado.")
                  st.rerun()
              with a2:
                if st.button("❌ Rechazar"):
                  wf["status"]="Rechazado"; wf["approved_by"]=vista_como; wf["approved_at"]=datetime.now().isoformat()
                  save_workflows(ss.workflows); st.warning("Rechazado."); st.rerun()

  with right:
    st.subheader("Crear / Editar flujo")
    with st.form("wf_form"):
      st.markdown("<div class='badge'>Task · Describe la tarea</div>", unsafe_allow_html=True)
      name = st.text_input("Name*", value="Analizar CV")
      role = st.selectbox("Puesto objetivo", list(ROLE_PRESETS.keys()), index=2)
      desc = st.text_area("Description*", value=EVAL_INSTRUCTION, height=110)
      expected = st.text_area("Expected output*", value="- Puntuación 0 a 100 según coincidencia con JD\n- Resumen del CV justificando el puntaje", height=80)

      st.markdown("**Job Description**")
      jd_text = st.text_area("JD en texto", value=ROLE_PRESETS[role]["jd"], height=140)
      jd_file = st.file_uploader("…o sube JD en PDF/TXT/DOCX", type=["pdf","txt","docx"], key="wf_jd_file")
      jd_from_file = ""
      if jd_file is not None:
        jd_from_file = extract_text_from_file(jd_file)
        st.caption("Vista previa del JD extraído:")
        st.text_area("Preview", jd_from_file[:4000], height=160)

      st.markdown("---")
      st.markdown("<div class='badge'>Staff in charge · Agente asignado</div>", unsafe_allow_html=True)
      if ss.agents:
        agent_opts = [f"{i} — {a.get('rol','Agente')} ({a.get('llm_model','model')})" for i,a in enumerate(ss.agents)]
        agent_pick = st.selectbox("Asigna un agente", agent_opts, index=0)
        agent_idx = int(agent_pick.split(" — ")[0])
      else:
        st.info("No hay agentes. Crea uno en la pestaña **Agentes**.")
        agent_idx = -1

      st.markdown("---")
      st.markdown("<div class='badge'>Guardar · Aprobación y programación</div>", unsafe_allow_html=True)
      run_date = st.date_input("Fecha de ejecución", value=date.today()+timedelta(days=1))
      run_time = st.time_input("Hora de ejecución", value=datetime.now().time().replace(second=0, microsecond=0))
      col_a, col_b, col_c = st.columns(3)
      save_draft    = col_a.form_submit_button("💾 Guardar borrador")
      send_approval = col_b.form_submit_button("📝 Enviar a aprobación")
      schedule      = col_c.form_submit_button("📅 Guardar y Programar")

      if save_draft or send_approval or schedule:
        jd_final = jd_from_file if jd_from_file else jd_text
        if not jd_final.strip(): st.error("Debes proporcionar un JD (texto o archivo).")
        elif agent_idx < 0:      st.error("Debes asignar un agente.")
        else:
          wf = {"id": f"WF-{int(datetime.now().timestamp())}","name": name,"role": role,"description": desc,"expected_output": expected,
                "jd_text": jd_final[:200000],"agent_idx": agent_idx,"created_at": datetime.now().isoformat(),
                "status": "Borrador","approved_by": "","approved_at": "","schedule_at": ""}
          if send_approval:
            wf["status"] = "Pendiente de aprobación"; st.success("Flujo enviado a aprobación.")
          if schedule:
            if puede_aprobar:
              wf["status"]="Programado"; wf["schedule_at"]=f"{run_date} {run_time.strftime('%H:%M')}"; st.success("Flujo programado.")
            else:
              wf["status"]="Pendiente de aprobación"; wf["schedule_at"]=f"{run_date} {run_time.strftime('%H:%M')}"; st.info("Pendiente de aprobación.")
          if save_draft:
            st.success("Borrador guardado.")
          ss.workflows.insert(0, wf); save_workflows(ss.workflows); st.rerun()

# ===================== ANALYTICS (nuevo módulo, no intrusivo) =====================
def page_analytics():
  st.header("Analytics y KPIs Estratégicos")

  a = calculate_analytics(ss.candidates)

  # KPIs (reutiliza cards/metric actuales)
  c1,c2,c3,c4 = st.columns(4)
  c1.metric("CVs en Pipeline", a["total_candidatos"])
  c2.metric("Fit promedio (skills)", f"{a['avg_fit_skills']}%")
  c3.metric("Score IA (prom.)", f"{a['avg_llm_score']}%")
  c4.metric("Exactitud IA (corr.)", a["corr_fit_vs_llm"])

  c5,c6,c7,c8 = st.columns(4)
  c5.metric("Puestos activos", a["puestos_activos"])
  c6.metric("Time-to-Hire P50", f"{a['tth_p50']} días") # TTH en lugar de TTX
  c7.metric("Time-to-Hire P90", f"{a['tth_p90']} días") # TTH en lugar de TTX
  c8.metric("Costo por hire", f"${a['costo_hire']}")

  st.markdown("---")

  # Grids (misma estética; usa scroll interno si no entra)
  left, right = st.columns(2)
  with left:
    st.subheader("Embudo por etapa")
    df_f = a["funnel_data"]
    wrap_funnel = st.container() # Contenedor para posible scroll
    if not df_f.empty and df_f["Candidatos"].sum() > 0:
      fig = px.funnel(df_f[df_f["Candidatos"]>0], x="Candidatos", y="Fase")
      fig.update_layout(plot_bgcolor="#FFFFFF", paper_bgcolor="rgba(0,0,0,0)", font=dict(color=TITLE_DARK), yaxis_title=None, margin=dict(l=0, r=0, t=30, b=0), height=400) # Ajusta altura/márgenes
      wrap_funnel.plotly_chart(fig, use_container_width=True)
    else:
      wrap_funnel.info("Aún no hay datos del pipeline.")

    st.subheader("Productividad del reclutador")
    df_p = a["productividad"]
    wrap_prod = st.container()
    if not df_p.empty:
      figp = px.bar(df_p, x="Usuario/Equipo", y="Completadas", text="Completadas", color_discrete_sequence=[PRIMARY])
      figp.update_layout(plot_bgcolor="#FFFFFF", paper_bgcolor="rgba(0,0,0,0)", font=dict(color=TITLE_DARK), xaxis_title=None, yaxis_title="Tareas Completadas", margin=dict(l=0, r=0, t=30, b=0), height=350)
      wrap_prod.plotly_chart(figp, use_container_width=True)
    else:
      wrap_prod.caption("Sin tareas completadas registradas.")

  with right:
    st.subheader("Conversión por etapa")
    df_f_conv = a["funnel_data"].copy()
    wrap_conv = st.container()
    if not df_f_conv.empty and df_f_conv["Candidatos"].sum() > 0:
        # Calcula conversión respecto a la etapa anterior
        df_f_conv['Prev_Candidatos'] = df_f_conv['Candidatos'].shift(1)
        # La primera etapa tiene conversión 100% sobre sí misma (o sobre 0 si no hay candidatos)
        first_stage_count = df_f_conv.loc[0, 'Candidatos']
        df_f_conv.loc[0, 'Prev_Candidatos'] = first_stage_count if first_stage_count > 0 else 1 # Evita división por cero
        df_f_conv['Conversión %'] = (df_f_conv['Candidatos'] / df_f_conv['Prev_Candidatos'].replace(0, pd.NA) * 100).fillna(0).round(1)

        figc = px.bar(df_f_conv, x="Fase", y="Conversión %", text="Conversión %", color_discrete_sequence=[PRIMARY])
        figc.update_layout(plot_bgcolor="#FFFFFF", paper_bgcolor="rgba(0,0,0,0)", font=dict(color=TITLE_DARK), xaxis_title=None, yaxis_title="% Conversión vs Etapa Anterior", margin=dict(l=0, r=0, t=30, b=0), height=400)
        wrap_conv.plotly_chart(figc, use_container_width=True)
    else:
        wrap_conv.info("Sin datos para calcular conversión.")


    st.subheader("Fuentes de talento")
    df_s = a["sources_data"]
    wrap_source = st.container()
    if not df_s.empty:
      fig_pie = px.pie(df_s, values='Candidatos', names='Fuente', title=None, color_discrete_sequence=px.colors.qualitative.Pastel) # Paleta diferente
      fig_pie.update_layout(plot_bgcolor="#FFFFFF", paper_bgcolor="rgba(0,0,0,0)", font=dict(color=TITLE_DARK), margin=dict(l=0, r=0, t=30, b=0), height=350, legend_title_text='Fuente')
      wrap_source.plotly_chart(fig_pie, use_container_width=True)
    else:
      wrap_source.caption("Sin distribución por fuentes.")

  st.markdown("---")

  # Correlación Skills vs IA
  st.subheader("Exactitud de IA (Skills vs IA)")
  df_corr = a["corr_data"]
  wrap_corr = st.container()
  if not df_corr.empty and len(df_corr) > 1: # Corr necesita > 1 punto
    fig_sc = px.scatter(df_corr, x="Fit_Skills", y="Score_LLM", trendline="ols", title=f"Correlación: {a['corr_fit_vs_llm']}", labels={'Fit_Skills':'Score Skills (%)','Score_LLM':'Score IA (%)'}, color_discrete_sequence=[PRIMARY])
    fig_sc.update_layout(plot_bgcolor="#FFFFFF", paper_bgcolor="rgba(0,0,0,0)", font=dict(color=TITLE_DARK), height=450)
    wrap_corr.plotly_chart(fig_sc, use_container_width=True)
  elif not df_corr.empty and len(df_corr) == 1:
      wrap_corr.info("Se necesita más de un CV evaluado por IA y Skills para calcular la correlación.")
  else:
    wrap_corr.info("No hay suficientes datos (CVs evaluados por ambos métodos) para calcular la correlación.")

# ===================== TODAS LAS TAREAS =====================
def page_create_task():
    st.header("Todas las Tareas")
    st.info("Muestra todas las tareas registradas en el sistema.")
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
    selected_status = st.selectbox(
        "Filtrar por Estado",
        options=all_statuses,
        index=all_statuses.index(preferred)
    )

    if selected_status == "Todos":
        tasks_to_show = tasks_list
    else:
        tasks_to_show = [t for t in tasks_list if t.get("status") == selected_status]

    if not tasks_to_show:
        st.info(f"No hay tareas con el estado '{selected_status}'.")
        return

    col_w = [0.9, 2.2, 2.4, 1.6, 1.4, 1.6, 1.0, 1.2, 1.6]
    h_id, h_nom, h_desc, h_asg, h_cre, h_due, h_pri, h_est, h_acc = st.columns(col_w)
    with h_id:   st.markdown("**Id**")
    with h_nom:  st.markdown("**Nombre**")
    with h_desc: st.markdown("**Descripción**")
    with h_asg:  st.markdown("**Asignado a**")
    with h_cre:  st.markdown("**Creado el**")
    with h_due:  st.markdown("**Vencimiento**")
    with h_pri:  st.markdown("**Prioridad**")
    with h_est:  st.markdown("**Estado**")
    with h_acc:  st.markdown("**Acciones**")

    st.markdown("<hr style='border:1px solid #E3EDF6; opacity:.6;'/>", unsafe_allow_html=True)

    for task in tasks_to_show:
        t_id = task.get("id") or str(uuid.uuid4()); task["id"] = t_id
        c_id, c_nom, c_desc, c_asg, c_cre, c_due, c_pri, c_est, c_acc = st.columns(col_w)

        with c_id:
            short = (t_id[:5] + "…") if len(t_id) > 6 else t_id
            st.caption(short)
        with c_nom:
            st.markdown(f"**{task.get('titulo','—')}**")
        with c_desc:
            st.caption(task.get("desc","—"))
        with c_asg:
            st.markdown(f"`{task.get('assigned_to','—')}`")
        with c_cre:
            st.markdown(task.get("created_at","—"))
        with c_due:
            st.markdown(task.get("due","—"))
        with c_pri:
            st.markdown(_priority_pill(task.get("priority","Media")), unsafe_allow_html=True)
        with c_est:
            st.markdown(_status_pill(task.get("status","Pendiente")), unsafe_allow_html=True)

        def _handle_action_change(task_id):
            selectbox_key = f"accion_{task_id}"
            if selectbox_key not in ss: return
            action = ss[selectbox_key]
            # Resetea la selección para permitir seleccionar la misma opción de nuevo
            ss[selectbox_key] = "Selecciona…"

            task_to_update = next((t for t in ss.tasks if t.get("id") == task_id), None)
            if not task_to_update: return

            # Resetea estados de UI específicos de acciones
            ss.confirm_delete_id = None
            ss.show_assign_for = None
            ss.expanded_task_id = None

            # Ejecuta la acción
            if action == "Ver detalle":
                ss.expanded_task_id = task_id
            elif action == "Asignar tarea":
                ss.show_assign_for = task_id
            elif action == "Tomar tarea":
                current_user = (ss.auth["name"] if ss.get("auth") else "Admin")
                task_to_update["assigned_to"] = current_user
                task_to_update["status"] = "En Proceso"
                save_tasks(ss.tasks)
                st.toast("Tarea tomada.")
            elif action == "Eliminar":
                ss.confirm_delete_id = task_id

            st.rerun() # Rerun para actualizar la UI

        with c_acc:
            selectbox_key = f"accion_{t_id}"
            # Usa "Selecciona…" como opción default y resetea a eso después de la acción
            st.selectbox(
                "Acciones",
                ["Selecciona…", "Ver detalle", "Asignar tarea", "Tomar tarea", "Eliminar"],
                index=0, # Siempre empieza en "Selecciona…"
                key=selectbox_key,
                label_visibility="collapsed",
                on_change=_handle_action_change,
                args=(t_id,)
            )

        if ss.get("confirm_delete_id") == t_id:
            b1, b2, _ = st.columns([1.0, 1.0, 7.8])
            with b1:
                if st.button("Eliminar permanentemente", key=f"del_confirm_{t_id}", type="primary", use_container_width=True):
                    ss.tasks = [t for t in ss.tasks if t.get("id") != t_id]
                    save_tasks(ss.tasks)
                    ss.confirm_delete_id = None
                    st.warning("Tarea eliminada permanentemente.")
                    st.rerun()
            with b2:
                if st.button("Cancelar", key=f"del_cancel_{t_id}", use_container_width=True):
                    ss.confirm_delete_id = None
                    st.rerun()

        if ss.show_assign_for == t_id:
            a1, a2, a3, a4, _ = st.columns([1.6, 1.6, 1.2, 1.0, 3.0])
            with a1:
                assign_type = st.selectbox("Tipo", ["En Espera", "Equipo", "Usuario"], key=f"type_{t_id}", index=2)
            with a2:
                if assign_type == "En Espera":
                    nuevo_assignee = "En Espera"
                    st.text_input("Asignado a", "En Espera", key=f"val_esp_{t_id}", disabled=True)
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
                        save_tasks(ss.tasks)
                        ss.show_assign_for = None
                        st.success("Cambios guardados.")
                        st.rerun()

        st.markdown("<hr style='border:1px solid #E3EDF6; opacity:.35;'/>", unsafe_allow_html=True)

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
  "analytics": page_analytics, # <-- Analytics añadido
  "create_task": page_create_task,
}

# =========================================================
# APP
# =========================================================
if require_auth():
    render_sidebar()

    task_id_for_dialog = ss.get("expanded_task_id")

    # Ejecuta la página actual
    ROUTES.get(ss.section, page_def_carga)()

    # Diálogo de detalle de tarea (se muestra sobre cualquier página si está activo)
    if task_id_for_dialog:
        task_data = next((t for t in ss.tasks if t.get("id") == task_id_for_dialog), None)
        if task_data:
            try:
                with st.dialog("Detalle de Tarea", width="large"):
                    st.markdown(f"### {task_data.get('titulo', 'Sin Título')}")
                    c1, c2, c3, c4 = st.columns(4)
                    with c1:
                        st.markdown("**Asignado a:**")
                        st.markdown(f"`{task_data.get('assigned_to', 'N/A')}`")
                    with c2:
                        st.markdown("**Vencimiento:**")
                        st.markdown(f"`{task_data.get('due', 'N/A')}`")
                    with c3:
                        st.markdown("**Estado:**")
                        st.markdown(_status_pill(task_data.get('status', 'Pendiente')), unsafe_allow_html=True)
                    with c4:
                        st.markdown("**Prioridad:**")
                        st.markdown(_priority_pill(task_data.get('priority', 'Media')), unsafe_allow_html=True)

                    st.markdown("---")
                    st.markdown("**Descripción:**")
                    st.markdown(task_data.get('desc', 'Sin descripción.'))
                    st.markdown("---")

                    st.markdown("**Actividad Reciente:**")
                    st.markdown(f"- Tarea creada el {task_data.get('created_at', 'N/A')}")
                    st.markdown("- *No hay más actividad registrada.*")

                    with st.form("comment_form"):
                        st.text_area("Comentarios", placeholder="Añadir un comentario...", key="task_comment")
                        submitted = st.form_submit_button("Enviar Comentario")
                        if submitted:
                            st.toast("Comentario (aún no) guardado.") # Funcionalidad placeholder

                    if st.button("Cerrar", key="close_dialog"):
                        ss.expanded_task_id = None
                        st.rerun()
            except Exception as e:
                st.error(f"Error al mostrar detalles de la tarea: {e}")
                if ss.get("expanded_task_id") == task_id_for_dialog: # Resetea si falla
                    ss.expanded_task_id = None
                    st.rerun()
        else:
             # Si el ID existe pero no se encuentra la tarea, resetea
            if ss.get("expanded_task_id") == task_id_for_dialog:
               ss.expanded_task_id = None
               # No necesita rerun aquí, simplemente no mostrará el diálogo
