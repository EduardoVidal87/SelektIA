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

LLM_IN_USE = "gpt-4o-mini" # Modelo real usado en las funciones _extract

# ===== Presets de puestos (Solo para Sourcing) =====
ROLE_PRESETS = {
  "Asistente Administrativo": {
    "jd": "Brindar soporte administrativo: gestión documental, agenda, compras menores, logística de reuniones y reportes...",
    "keywords": "Excel, Word, PowerPoint, gestión documental, atención a proveedores, compras, logística, caja chica, facturación, redacción",
    "must": ["Excel","Gestión documental","Redacción"], "nice": ["Facturación","Caja"],
  },
  "Business Analytics": {
    "jd": "Recolectar, transformar y analizar datos para generar insights...",
    "keywords": "SQL, Power BI, Tableau, ETL, KPI, storytelling, Excel avanzado, Python, A/B testing, métricas de negocio",
    "must": ["SQL","Power BI"], "nice": ["Tableau","Python","ETL"],
  },
  # ... (mantener los otros presets si se usan en Sourcing) ...
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

.pos-badge {{ border:1px solid #E3EDF6; background:#F7FBFF; border-radius:8px; padding:4px 8px; font-size:12px; color:#333; }}
.pos-badge-Abierto {{ border-color: {PRIMARY}; background: #E6FFF1; color: {PRIMARY}; font-weight: 600; }}
.pos-badge-Pausado {{ border-color: #FFB700; background: #FFFDE6; color: #E8B900; }}
.pos-badge-Cerrado {{ border-color: #D1D5DB; background: #F3F4F6; color: #6B7280; }}

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
POSITIONS_FILE = DATA_DIR / "positions.json"

DEFAULT_ROLES = ["Headhunter", "Coordinador RR.HH.", "Admin RR.HH."]

DEFAULT_TASKS = [
    {"id": str(uuid.uuid4()), "titulo":"Revisar CVs top 5", "desc":"Analizar a los 5 candidatos con mayor fit para 'Business Analytics'.", "due":str(date.today() + timedelta(days=2)), "assigned_to": "Headhunter", "status": "Pendiente", "priority": "Alta", "created_at": (date.today() - timedelta(days=3)).isoformat()},
    {"id": str(uuid.uuid4()), "titulo":"Coordinar entrevista de Rivers Brykson", "desc":"Agendar la 2da entrevista (Gerencia) para el puesto de VP de Marketing.", "due":str(date.today() + timedelta(days=5)), "assigned_to": "Coordinador RR.HH.", "status": "En Proceso", "priority": "Media", "created_at": (date.today() - timedelta(days=8)).isoformat(), "context": {"candidate_name": "Rivers Brykson", "role": "VP de Marketing"}},
    # ... (otros defaults si los tienes) ...
]

DEFAULT_POSITIONS = [
    {"ID":"10,645,194","Puesto":"Desarrollador/a Backend (Python)", "JD": "Buscamos un Desarrollador Backend con experiencia en Python, Django y/o Flask. Responsable de diseñar, implementar y mantener APIs RESTful...",
     "Días Abierto":3, "Leads":1800,"Nuevos":115,"Recruiter Screen":35,"HM Screen":7,
     "Entrevista Telefónica":14,"Entrevista Presencial":15,"Ubicación":"Lima, Perú",
     "Hiring Manager":"Rivers Brykson","Estado":"Abierto","Fecha Inicio": (date.today() - timedelta(days=3)).isoformat()},
    # ... (otros defaults si los tienes) ...
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

if "positions_loaded" not in ss:
    ss.positions = load_positions()
    if not isinstance(ss.positions, list):
        ss.positions = DEFAULT_POSITIONS
    for p in ss.positions: # Asegurar que tengan JD
        if "JD" not in p:
            p["JD"] = "Por favor, define el Job Description."
    save_positions(ss.positions)
    ss.positions_loaded = True

if "pipeline_filter" not in ss: ss.pipeline_filter = None
if "expanded_task_id" not in ss: ss.expanded_task_id = None
if "show_assign_for" not in ss: ss.show_assign_for = None
if "confirm_delete_id" not in ss: ss.confirm_delete_id = None

if "editing_flow_id" not in ss: ss.editing_flow_id = None
if "llm_eval_results" not in ss: ss.llm_eval_results = []

if "show_flow_form" not in ss: ss.show_flow_form = False
if "viewing_flow_id" not in ss: ss.viewing_flow_id = None
if "confirm_delete_flow_id" not in ss: ss.confirm_delete_flow_id = None

if "show_position_form" not in ss: ss.show_position_form = False
if "editing_position_id" not in ss: ss.editing_position_id = None
if "confirm_delete_position_id" not in ss: ss.confirm_delete_position_id = None

if "selected_flow_id_for_eval" not in ss: ss.selected_flow_id_for_eval = None

# =========================================================
# UTILS
# =========================================================
# ... (funciones _normalize, infer_skills, score_fit_by_skills, build_analysis_text, pdf_viewer_embed, _extract_docx_bytes, extract_text_from_file, _max_years, extract_meta, simple_score, calculate_analytics sin cambios) ...
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

# ====== Helpers de TAREAS, FLUJOS, PUESTOS ======
def _status_pill(s: str)->str:
  colors = { "Pendiente": "#9AA6B2", "En Proceso": "#0072E3", "Completada": "#10B981", "En Espera": "#FFB700" }
  c = colors.get(s, "#9AA6B2")
  return f'<span class="badge" style="border-color:{c}33;background:{c}14;color:#0A2230">{s}</span>'

def _priority_pill(p: str) -> str:
    p_safe = p if p in TASK_PRIORITIES else "Media"
    return f'<span class="badge priority-{p_safe}">{p_safe}</span>'

def _flow_status_pill(s: str)->str:
  colors = {
      "Borrador": "#9AA6B2",
      "Pendiente de aprobación": "#FFB700",
      "Aprobado": "#10B981",
      "Rechazado": "#D60000",
      "Programado": "#0072E3"
  }
  c = colors.get(s, "#9AA6B2")
  return f'<span class="badge" style="border-color:{c}33;background:{c}14;color:#0A2230">{s}</span>'

def _position_status_pill(s: str) -> str:
    s_safe = s if s in POSITION_STATUSES else "Abierto"
    return f'<span class="pos-badge pos-badge-{s_safe}">{s_safe}</span>'

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
    "context": context or {}
  }
  if not isinstance(ss.tasks, list): ss.tasks = []
  ss.tasks.insert(0, t)
  save_tasks(ss.tasks)

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

def create_ia_review_task(cv_filename, flow_name, score, analysis, assigned_to):
    task_title = f"Revisar IA: {cv_filename} (Flujo: {flow_name})"
    context = {
        "source": "IA Evaluation",
        "cv_filename": cv_filename,
        "flow_name": flow_name,
        "ia_score": score,
        "ia_analysis": analysis or "Análisis IA no disponible."
    }
    t = {
        "id": str(uuid.uuid4()),
        "titulo": task_title,
        "desc": f"Puntuación IA: {score}%. Revisar análisis detallado.",
        "due": (date.today() + timedelta(days=1)).isoformat(),
        "assigned_to": assigned_to,
        "status": "Pendiente",
        "priority": "Media",
        "created_at": date.today().isoformat(),
        "context": context
    }
    if not isinstance(ss.tasks, list): ss.tasks = []
    ss.tasks.insert(0, t)
    # Guardado se hará en bloque en page_eval

def _handle_flow_action_change(wf_id):
    action_key = f"flow_action_{wf_id}"
    if action_key not in ss: return
    action = ss[action_key]
    ss.viewing_flow_id = None
    ss.editing_flow_id = None
    ss.confirm_delete_flow_id = None
    ss.show_flow_form = False
    if action == "Ver detalles":
        ss.viewing_flow_id = wf_id
        ss.show_flow_form = True
    elif action == "Editar":
        ss.editing_flow_id = wf_id
        ss.show_flow_form = True
    elif action == "Eliminar":
        ss.confirm_delete_flow_id = wf_id
    ss[action_key] = "Selecciona..."

def _handle_position_action_change(pos_id):
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

# ... (resto de funciones de LOGIN, SIDEBAR, y páginas como page_def_carga, etc., hasta page_puestos SIN CAMBIOS DESDE LA VERSIÓN ANTERIOR) ...
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

def render_position_form():
    is_edit_mode = bool(ss.get("editing_position_id"))
    editing_pos_data = None
    if is_edit_mode:
        editing_pos_id = ss.get("editing_position_id")
        editing_pos_data = next((p for p in ss.positions if p["ID"] == editing_pos_id), None)
        if editing_pos_data:
            st.subheader(f"Editando Puesto: {editing_pos_data.get('Puesto')}")
        else:
            st.error("Error: No se encontró el puesto a editar."); ss.editing_position_id = None; return
    else:
        st.subheader("Crear Nuevo Puesto"); editing_pos_data = {}

    with st.form("position_form"):
        default_puesto = editing_pos_data.get("Puesto", ""); default_ubicacion = editing_pos_data.get("Ubicación", "Lima, Perú")
        default_hm = editing_pos_data.get("Hiring Manager", ""); default_jd = editing_pos_data.get("JD", "")
        default_estado = editing_pos_data.get("Estado", "Abierto")
        try: estado_index = POSITION_STATUSES.index(default_estado)
        except ValueError: estado_index = 0
        try: default_fecha_inicio = date.fromisoformat(editing_pos_data.get("Fecha Inicio", date.today().isoformat()))
        except: default_fecha_inicio = date.today()

        puesto = st.text_input("Nombre del Puesto*", value=default_puesto)
        jd = st.text_area("Job Description (JD)*", value=default_jd, height=200, help="Este JD se usará en 'Flujos' y 'Evaluación de CVs'.")
        c1, c2 = st.columns(2); c3, c4 = st.columns(2)
        with c1: ubicacion = st.text_input("Ubicación*", value=default_ubicacion)
        with c2: hm = st.text_input("Hiring Manager*", value=default_hm)
        with c3: estado = st.selectbox("Estado", POSITION_STATUSES, index=estado_index)
        with c4: fecha_inicio = st.date_input("Fecha de Inicio", value=default_fecha_inicio)
        st.markdown("---")
        submitted = st.form_submit_button("Guardar Puesto" if is_edit_mode else "Crear Puesto")
        if submitted:
            if not puesto.strip() or not ubicacion.strip() or not hm.strip() or not jd.strip():
                st.error("Por favor, completa todos los campos obligatorios (*), incluyendo el Job Description.")
            else:
                if is_edit_mode:
                    pos_to_update = next((p for p in ss.positions if p["ID"] == ss.editing_position_id), None)
                    if pos_to_update:
                        pos_to_update.update({"Puesto": puesto, "Ubicación": ubicacion, "Hiring Manager": hm, "Estado": estado, "Fecha Inicio": fecha_inicio.isoformat(), "JD": jd})
                    st.success("Puesto actualizado.")
                else:
                    new_pos = {"ID": f"P-{int(datetime.now().timestamp())}", "Puesto": puesto, "Ubicación": ubicacion, "Hiring Manager": hm, "Estado": estado, "Fecha Inicio": fecha_inicio.isoformat(), "JD": jd, "Días Abierto": 0, "Leads": 0, "Nuevos": 0, "Recruiter Screen": 0, "HM Screen": 0, "Entrevista Telefónica": 0, "Entrevista Presencial": 0}
                    ss.positions.insert(0, new_pos)
                    st.success("Puesto creado.")
                save_positions(ss.positions); ss.editing_position_id = None; ss.show_position_form = False; st.rerun()

def page_puestos():
    st.header("Puestos")
    if st.button("➕ Nuevo Puesto" if not ss.show_position_form else "✖ Ocultar Formulario", key="toggle_pos_form"):
        ss.show_position_form = not ss.show_position_form
        if not ss.show_position_form: ss.editing_position_id = None
        st.rerun()
    if ss.show_position_form: render_position_form()
    if not ss.show_position_form:
        st.subheader("Mis Puestos")
        if not ss.positions: st.info("No hay puestos definidos. Crea uno con **➕ Nuevo Puesto**."); return
        all_candidates_df = pd.DataFrame(ss.candidates) if ss.candidates else pd.DataFrame(columns=["Role", "stage"])
        col_w = [2.5, 2.0, 1.0, 1.0, 1.0, 1.5]
        h_puesto, h_hm, h_dias, h_leads, h_estado, h_acc = st.columns(col_w)
        with h_puesto: st.markdown("**Puesto / Ubicación**"); with h_hm: st.markdown("**Hiring Manager**"); with h_dias: st.markdown("**Días Abierto**"); with h_leads: st.markdown("**Leads (Nuevos)**"); with h_estado: st.markdown("**Estado**"); with h_acc: st.markdown("**Acciones**")
        st.markdown("<hr style='border:1px solid #E3EDF6; opacity:.6;'/>", unsafe_allow_html=True)
        positions_list = ss.positions.copy()
        for pos in positions_list:
            pos_id = pos.get("ID");
            if not pos_id: pos["ID"] = str(uuid.uuid4()); pos_id = pos["ID"]
            c_puesto, c_hm, c_dias, c_leads, c_estado, c_acc = st.columns(col_w)
            with c_puesto: st.markdown(f"**{pos.get('Puesto', '—')}**"); st.caption(f"{pos.get('Ubicación', '—')}")
            with c_hm: st.markdown(f"`{pos.get('Hiring Manager', '—')}`")
            with c_dias:
                try: load_date = date.fromisoformat(pos.get("Fecha Inicio", date.today().isoformat())); dias_abierto = (date.today() - load_date).days; st.markdown(f"**{dias_abierto}**")
                except Exception: st.markdown("—")
            with c_leads:
                pos_puesto_name = pos.get("Puesto"); cands_for_pos = all_candidates_df[all_candidates_df["Role"] == pos_puesto_name] if pos_puesto_name else pd.DataFrame()
                leads_count = len(cands_for_pos); nuevos_count = 0
                if not cands_for_pos.empty: nuevos_count = len(cands_for_pos[cands_for_pos["stage"].isin(["Recibido", "Screening RRHH"])])
                st.markdown(f"**{leads_count}** ({nuevos_count})")
            with c_estado: st.markdown(_position_status_pill(pos.get('Estado', 'Abierto')), unsafe_allow_html=True)
            with c_acc: st.selectbox("Acciones", ["Selecciona...", "Editar", "Eliminar"], key=f"pos_action_{pos_id}", label_visibility="collapsed", on_change=_handle_position_action_change, args=(pos_id,))
            if ss.get("confirm_delete_position_id") == pos_id:
                st.error(f"¿Seguro que quieres eliminar el puesto **{pos.get('Puesto')}**?")
                b1, b2, _ = st.columns([1, 1, 5])
                with b1:
                    if st.button("Sí, Eliminar", key=f"pos_del_confirm_{pos_id}", type="primary", use_container_width=True, help="Esto eliminará el puesto permanentemente"):
                        ss.positions = [p for p in ss.positions if p.get("ID") != pos_id]; save_positions(ss.positions); ss.confirm_delete_position_id = None; st.warning(f"Puesto '{pos.get('Puesto')}' eliminado."); st.rerun()
                with b2:
                    if st.button("Cancelar", key=f"pos_del_cancel_{pos_id}", use_container_width=True): ss.confirm_delete_position_id = None; st.rerun()
            st.markdown("<hr style='border:1px solid #E3EDF6; opacity:.35;'/>", unsafe_allow_html=True)
        st.markdown("---")
        st.subheader("Candidatos por Puesto")
        pos_list = [p.get("Puesto") for p in ss.positions if p.get("Puesto")]
        if not pos_list: st.info("Aún no se han creado puestos."); return
        selected_pos = st.selectbox("Selecciona un puesto para ver el Pipeline asociado", pos_list)
        if selected_pos:
            candidates_for_pos = [c for c in ss.candidates if c.get("Role") == selected_pos]
            if candidates_for_pos:
                df_cand = pd.DataFrame(candidates_for_pos)
                st.dataframe(df_cand[["Name", "Score", "stage", "load_date"]].rename(columns={"Name":"Candidato", "Score":"Fit", "stage":"Fase"}), use_container_width=True, hide_index=True)
            else: st.info(f"No hay candidatos activos para el puesto **{selected_pos}**.")

# ===================== EVALUACIÓN (Req 6 - Modificado) =====================
# ... (Funciones _llm_setup_credentials, _llm_prompt_for_resume, _extract_with_azure, _extract_with_openai, _create_llm_bar, _results_to_df SIN CAMBIOS desde la versión anterior) ...
def _llm_setup_credentials():
    try:
        if "AZURE_OPENAI_API_KEY" not in os.environ and "llm" in st.secrets and "azure_openai_api_key" in st.secrets["llm"]:
            os.environ["AZURE_OPENAI_API_KEY"] = st.secrets["llm"]["azure_openai_api_key"]
        if "AZURE_OPENAI_ENDPOINT" not in os.environ and "llm" in st.secrets and "azure_openai_endpoint" in st.secrets["llm"]:
            os.environ["AZURE_OPENAI_ENDPOINT"] = st.secrets["llm"]["azure_openai_endpoint"]
    except Exception: pass

def _llm_prompt_for_resume(resume_content: str, flow_desc: str, flow_expected: str):
    if not _LC_AVAILABLE: return None
    json_object_structure = """{{
        "Name": "Full Name", "Last_position": "The most recent position", "Years_of_Experience": "Number (in years)",
        "English_Level": "Beginner/Intermediate/Advanced/Fluent/Native", "Key_Skills": ["Skill 1", "Skill 2"],
        "Certifications": ["Cert 1", "Cert 2"], "Additional_Notes": "Optional relevant info.", "Score": "0-100"
    }}"""
    system_template = f"""### Objective\nExecute task: {flow_desc}\nExpected Output: {flow_expected}\nExtract JSON from CV, compute match % vs JD.\nCV Content:\n{resume_content}\nReturn JSON:\n{json_object_structure}"""
    return ChatPromptTemplate.from_messages([
        SystemMessagePromptTemplate.from_template(system_template),
        HumanMessagePromptTemplate.from_template("Job description:\n{job_description}")])

def _extract_with_azure(job_description: str, resume_content: str, flow_desc: str, flow_expected: str) -> dict:
    if not _LC_AVAILABLE: return {}
    _llm_setup_credentials();
    try:
        llm = AzureChatOpenAI(azure_deployment=st.secrets["llm"]["azure_deployment"], api_version=st.secrets["llm"]["azure_api_version"], temperature=0)
        parser = JsonOutputParser(); prompt = _llm_prompt_for_resume(resume_content, flow_desc, flow_expected)
        if prompt is None: return {}
        chain = prompt | llm | parser; out = chain.invoke({"job_description": job_description})
        return out if isinstance(out, dict) else {}
    except Exception as e: st.warning(f"Azure LLM no disponible: {e}"); return {}

def _extract_with_openai(job_description: str, resume_content: str, flow_desc: str, flow_expected: str) -> dict:
    if not _LC_AVAILABLE: return {}
    try: api_key = st.secrets["llm"]["openai_api_key"]
    except Exception: return {}
    try:
        chat = ChatOpenAI(temperature=0, model=LLM_IN_USE, openai_api_key=api_key)
        json_object_structure = """{"Name": "Full Name", "Last_position": "Recent position", "Years_of_Experience": "Number", "English_Level": "Level", "Key_Skills": [], "Certifications": [], "Additional_Notes": "Optional info.", "Score": "0-100"}"""
        prompt = f"""Task: {flow_desc}\nExpected: {flow_expected}\nExtract JSON from CV, compute 0-100 match vs JD.\nJD:\n{job_description}\nCV:\n{resume_content}\nReturn JSON:\n{json_object_structure}"""
        resp = chat.invoke(prompt); txt = resp.content.strip().replace('```json','').replace('```','')
        return json.loads(txt)
    except Exception as e: st.warning(f"OpenAI LLM no disponible: {e}"); return {}

def _create_llm_bar(df: pd.DataFrame):
    fig = px.bar(df, x='file_name', y='Score', text='Score', title='Comparativa de Puntajes (LLM)', color_discrete_sequence=PLOTLY_GREEN_SEQUENCE)
    for _, row in df.iterrows(): fig.add_annotation(x=row['file_name'], y=row['Score'], text=row.get('Name',''), showarrow=True, arrowhead=1, ax=0, ay=-20)
    fig.update_layout(plot_bgcolor="#FFFFFF", paper_bgcolor="rgba(0,0,0,0)", font=dict(color=TITLE_DARK)); return fig

def _results_to_df(results: list) -> pd.DataFrame:
    if not results: return pd.DataFrame()
    df = pd.DataFrame(results).copy()
    if "Score" in df.columns:
        try: df["Score"] = df["Score"].astype(int)
        except: pass
        df = df.sort_values(by="Score", ascending=False)
    return df

def page_eval():
    st.header("Resultados de evaluación")
    with st.expander("🤖 Evaluación asistida por LLM (Azure/OpenAI)", expanded=True):
        flow_options = {wf.get("id"): wf.get("name", "Flujo sin nombre") for wf in ss.workflows if wf.get("id")}
        if not flow_options: st.warning("No hay flujos definidos. Crea un flujo primero.", icon="⚠️"); return
        initial_flow_id = list(flow_options.keys())[0]
        if "selected_flow_id_for_eval" in ss and ss.selected_flow_id_for_eval in flow_options: initial_flow_id = ss.selected_flow_id_for_eval
        else: ss.selected_flow_id_for_eval = initial_flow_id
        st.selectbox("Seleccionar Flujo de Evaluación", options=list(flow_options.keys()), format_func=lambda fid: flow_options.get(fid), key="selected_flow_id_for_eval")
        current_flow_id = ss.get("selected_flow_id_for_eval")
        up = st.file_uploader("Sube CVs en PDF para evaluarlos con el LLM", type=["pdf"], accept_multiple_files=True, key="pdf_llm")
        run_llm = st.button("Ejecutar evaluación LLM", key="btn_llm_eval")
        if run_llm and up:
            selected_flow_data = next((wf for wf in ss.workflows if wf.get("id") == current_flow_id), None)
            if not selected_flow_data: st.error("Flujo seleccionado no válido."); return
            flow_desc_val = selected_flow_data.get("description", ""); flow_expected_val = selected_flow_data.get("expected_output", ""); jd_llm_val = selected_flow_data.get("jd_text", ""); flow_name_val = selected_flow_data.get("name", "N/A")
            if not _LC_AVAILABLE: st.warning("Paquetes LangChain/OpenAI no disponibles."); ss.llm_eval_results = []; return
            if not jd_llm_val or jd_llm_val.startswith("JD no"): st.error("El flujo no tiene un JD válido."); return
            results_with_bytes = []; new_tasks_created = 0
            current_user = ss.auth.get("name", "Admin")
            for f in up:
                f_bytes = f.read(); f.seek(0); text = ""
                try: text = extract_text_from_file(f) # Simplificado
                except Exception as e_inner: st.error(f"No se pudo leer {f.name}: {e_inner}"); continue
                if not text: st.warning(f"No se extrajo texto de {f.name}, se omite."); continue

                meta = _extract_with_azure(jd_llm_val, text, flow_desc_val, flow_expected_val) or _extract_with_openai(jd_llm_val, text, flow_desc_val, flow_expected_val)
                if not meta: meta = {"Name":"—","Years_of_Experience":"—","English_Level":"—","Key_Skills":[],"Certifications":[],"Additional_Notes":"—","Score":0}
                meta["file_name"] = f.name
                results_with_bytes.append({"meta": meta, "_bytes": f_bytes})
                try:
                    score_val = meta.get('Score', 0); analysis_val = meta.get('Additional_Notes', 'Sin análisis detallado.')
                    create_ia_review_task(f.name, flow_name_val, score_val, analysis_val, current_user); new_tasks_created += 1
                except Exception as e_task: st.error(f"Error creando tarea para {f.name}: {e_task}")
            ss.llm_eval_results = results_with_bytes
            if new_tasks_created > 0: save_tasks(ss.tasks); st.success(f"{new_tasks_created} tarea(s) de revisión creadas en 'Todas las tareas'.")
        if ss.llm_eval_results:
            df_llm = _results_to_df([r["meta"] for r in ss.llm_eval_results])
            if not df_llm.empty: st.subheader("Resultados LLM (Evaluación Actual)"); st.dataframe(df_llm, use_container_width=True, hide_index=True); st.plotly_chart(_create_llm_bar(df_llm), use_container_width=True)
            else: st.info("No se generaron resultados válidos.")
        else: st.info("Selecciona un flujo, sube CVs y ejecuta la evaluación.")

# ... (resto de funciones page_pipeline, page_interview, page_offer, page_onboarding, page_hh_tasks, page_agent_tasks, page_agents, render_flow_form, page_flows, page_analytics SIN CAMBIOS DESDE LA VERSIÓN ANTERIOR) ...
def page_pipeline():
    filter_stage = ss.get("pipeline_filter")
    if filter_stage:
        st.header(f"Pipeline: Candidatos en Fase '{filter_stage}'")
        candidates_to_show = [c for c in ss.candidates if c.get("stage") == filter_stage]
    else:
        st.header("Pipeline de Candidatos (Vista Kanban)")
        candidates_to_show = ss.candidates
    st.caption("Arrastra los candidatos a través de las etapas para avanzar el proceso.")
    if not candidates_to_show and filter_stage: st.info(f"No hay candidatos en la fase **{filter_stage}**."); return
    elif not ss.candidates: st.info("No hay candidatos activos."); return
    candidates_by_stage = {stage: [] for stage in PIPELINE_STAGES}
    for c in candidates_to_show: candidates_by_stage[c["stage"]].append(c)
    cols = st.columns(len(PIPELINE_STAGES))
    for i, stage in enumerate(PIPELINE_STAGES):
        with cols[i]:
            st.markdown(f"**{stage} ({len(candidates_by_stage[stage])})**", unsafe_allow_html=True); st.markdown("---")
            for c in candidates_by_stage[stage]:
                card_name = c["Name"].split('_')[-1].replace('.pdf', '').replace('.txt', '')
                st.markdown(f"""<div class="k-card" style="margin-bottom: 10px; border-left: 4px solid {PRIMARY if c['Score'] >= 70 else ('#FFA500' if c['Score'] >= 40 else '#D60000')}">
                    <div style="font-weight:700; color:{TITLE_DARK};">{card_name}</div> <div style="font-size:12px; opacity:.8;">{c.get("Role", "-")}</div>
                    <div style="font-size:14px; font-weight:700; margin-top:8px;">Fit: <span style="color:{PRIMARY};">{c["Score"]}%</span></div>
                    <div style="font-size:10px; opacity:.6; margin-top:4px;">Fuente: {c.get("source", "N/A")}</div></div>""", unsafe_allow_html=True)
                with st.form(key=f"form_move_{c['id']}", clear_on_submit=False):
                    current_stage_index = PIPELINE_STAGES.index(stage); available_stages = [s for s in PIPELINE_STAGES if s != stage]
                    try: default_index = available_stages.index(PIPELINE_STAGES[min(current_stage_index + 1, len(PIPELINE_STAGES) - 1)])
                    except ValueError: default_index = 0
                    new_stage = st.selectbox("Mover a:", available_stages, key=f"select_move_{c['id']}", index=default_index, label_visibility="collapsed")
                    if st.form_submit_button("Mover Candidato"):
                        c["stage"] = new_stage
                        if new_stage == "Descartado": st.success(f"📧 Email de rechazo enviado a {card_name}.")
                        elif new_stage == "Entrevista Telefónica":
                            st.info(f"📅 Tarea de programación generada para {card_name}.")
                            task_context = {"candidate_name": card_name, "candidate_id": c["id"], "role": c.get("Role", "N/A")}
                            create_task_from_flow(f"Programar entrevista - {card_name}", date.today()+timedelta(days=2), "Coordinar entrevista.", assigned="Headhunter", context=task_context)
                        elif new_stage == "Contratado": st.balloons(); st.success(f"🎉 Flujo de Onboarding disparado para {card_name}.")
                        if filter_stage and new_stage != filter_stage: ss.pipeline_filter = None; st.info("Filtro removido.")
                        st.rerun()
                st.markdown("<br>", unsafe_allow_html=True)

def page_interview(): st.header("Entrevista (Gerencia)"); st.info("Usa el Pipeline y el filtro del menú."); ss.section = "pipeline"; ss.pipeline_filter = "Entrevista Gerencia"; st.rerun()
def page_offer(): st.header("Oferta"); st.info("Usa el Pipeline y el filtro del menú."); ss.section = "pipeline"; ss.pipeline_filter = "Oferta"; st.rerun()
def page_onboarding(): st.header("Onboarding"); st.info("Usa el Pipeline y el filtro del menú."); ss.section = "pipeline"; ss.pipeline_filter = "Contratado"; st.rerun()

def page_hh_tasks():
    st.header("Tareas Asignadas a Mí")
    st.write("Tareas asignadas a tu rol (Headhunter/Colaborador).")
    if not isinstance(ss.tasks, list) or not ss.tasks: st.info("No tienes tareas asignadas."); return
    my_name = ss.auth.get("name", "Colab")
    my_tasks = [t for t in ss.tasks if t.get("assigned_to") in ["Headhunter", "Colaborador", my_name]]
    if not my_tasks: st.info("No tienes tareas asignadas."); return
    all_statuses = ["Todos"] + sorted(list(set(t.get("status", "Pendiente") for t in my_tasks)))
    prefer_order = ["Pendiente", "En Proceso", "En Espera"]; preferred = next((s for s in prefer_order if s in all_statuses), "Todos")
    selected_status = st.selectbox("Filtrar por Estado", all_statuses, index=all_statuses.index(preferred))
    my_tasks_filtered = my_tasks if selected_status=="Todos" else [t for t in my_tasks if t.get("status") == selected_status]
    if my_tasks_filtered: st.dataframe(pd.DataFrame(my_tasks_filtered)[["titulo", "desc", "status", "priority", "due", "created_at"]].rename(columns={"titulo":"Título", "desc":"Descripción", "status": "Estado", "priority": "Prioridad", "due":"Vencimiento", "created_at": "Creación"}), use_container_width=True, hide_index=True)
    else: st.info(f"No hay tareas '{selected_status}'.")

def page_agent_tasks():
    st.header("Tareas Asignadas a mi Equipo")
    st.write("Tareas generadas por Flujos y asignadas a roles de equipo.")
    if not isinstance(ss.tasks, list) or not ss.tasks: st.write("No hay tareas pendientes en el equipo."); return
    team_tasks = [t for t in ss.tasks if t.get("assigned_to") in ["Coordinador RR.HH.", "Admin RR.HH.", "Agente de Análisis"]]
    if not team_tasks: st.info("No hay tareas asignadas al equipo."); return
    all_statuses = ["Todos"] + sorted(list(set(t.get("status", "Pendiente") for t in team_tasks)))
    prefer_order = ["Pendiente", "En Proceso", "En Espera"]; preferred = next((s for s in prefer_order if s in all_statuses), "Todos")
    selected_status = st.selectbox("Filtrar por Estado", all_statuses, index=all_statuses.index(preferred), key="agent_task_filter")
    team_tasks_filtered = team_tasks if selected_status=="Todos" else [t for t in team_tasks if t.get("status") == selected_status]
    if team_tasks_filtered: st.dataframe(pd.DataFrame(team_tasks_filtered)[["titulo", "desc", "assigned_to", "status", "priority", "due", "created_at"]].rename(columns={"titulo":"Título", "desc":"Descripción", "assigned_to": "Asignado a", "status": "Estado", "priority": "Prioridad", "due":"Vencimiento", "created_at": "Creación"}), use_container_width=True, hide_index=True)
    else: st.info(f"No hay tareas '{selected_status}' asignadas al equipo.")

def page_agents():
  st.header("Agentes")
  st.subheader("Crear / Editar agente")
  left, _ = st.columns([0.25, 0.75])
  with left:
    if st.button(("➕ Nuevo" if not ss.new_role_mode else "✖ Cancelar"), key="toggle_new_role"):
      ss.new_role_mode = not ss.new_role_mode
      if ss.new_role_mode: ss.agent_view_idx = None; ss.agent_edit_idx = None
      st.rerun()
  if ss.new_role_mode:
    st.info("Completa el formulario para crear un nuevo rol/agente.")
    with st.form("agent_new_form"):
      c1, c2 = st.columns(2)
      with c1: role_name = st.text_input("Rol*", value=""); objetivo = st.text_input("Objetivo*", value="Identificar a los mejores profesionales..."); backstory = st.text_area("Backstory*", value="Eres un analista de RR.HH...", height=120); guardrails = st.text_area("Guardrails", value="No compartas datos sensibles...", height=90)
      with c2: st.text_input("Modelo LLM (Evaluación)", value=LLM_IN_USE, disabled=True); img_src = st.text_input("URL de imagen", value=AGENT_DEFAULT_IMAGES.get("Headhunter","")); perms = st.multiselect("Permisos", ["Colaborador","Supervisor","Administrador"], default=["Supervisor","Administrador"])
      saved = st.form_submit_button("Guardar/Actualizar Agente")
      if saved:
        rn = (role_name or "").strip()
        if not rn: st.error("El campo Rol* es obligatorio.")
        else:
          ss.agents.append({"rol": rn, "objetivo": objetivo, "backstory": backstory, "guardrails": guardrails, "herramientas": [], "llm_model": LLM_IN_USE, "image": img_src, "perms": perms, "ts": datetime.utcnow().isoformat()})
          save_agents(ss.agents); roles_new = sorted(list({*ss.roles, rn})); ss.roles = roles_new; save_roles(roles_new); st.success("Agente creado."); ss.new_role_mode = False; st.rerun()
  st.subheader("Tus agentes")
  if not ss.agents: st.info("Aún no hay agentes. Crea el primero."); return
  cols_per_row = 5
  for i in range(0, len(ss.agents), cols_per_row):
    row_agents = ss.agents[i:i+cols_per_row]; cols = st.columns(cols_per_row)
    for j, ag in enumerate(row_agents):
      idx = i + j
      with cols[j]:
        img = ag.get("image") or AGENT_DEFAULT_IMAGES.get(ag.get("rol","Headhunter")); st.markdown(f'<div class="agent-card"><img src="{img}"><div class="agent-title">{ag.get("rol","—")}</div><div class="agent-sub">{ag.get("objetivo","—")}</div></div>', unsafe_allow_html=True)
        st.markdown('<div class="toolbar">', unsafe_allow_html=True); c1, c2, c3, c4 = st.columns(4)
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
    ag = ss.agents[ss.agent_view_idx]; st.markdown("### Detalle del agente"); st.markdown('<div class="agent-detail">', unsafe_allow_html=True); c1, c2 = st.columns([0.42, 0.58])
    with c1: raw_img = ag.get("image") or ""; safe_img = (raw_img.strip() if isinstance(raw_img, str) and raw_img.strip() else AGENT_DEFAULT_IMAGES.get(ag.get("rol","Headhunter"), AGENT_DEFAULT_IMAGES["Headhunter"])); st.markdown(f'<div style="text-align:center;margin:6px 0 12px"><img src="{safe_img}" style="width:180px;height:180px;border-radius:999px;object-fit:cover;border:4px solid #F1F7FD;"></div>', unsafe_allow_html=True); st.caption("Modelo LLM"); st.markdown(f"<div class='badge'>🧠 {ag.get('llm_model',LLM_IN_USE)}</div>", unsafe_allow_html=True)
    with c2: st.text_input("Role*", value=ag.get("rol",""), disabled=True); st.text_input("Objetivo*", value=ag.get("objetivo",""), disabled=True); st.text_area("Backstory*", value=ag.get("backstory",""), height=120, disabled=True); st.text_area("Guardrails", value=ag.get("guardrails",""), height=90, disabled=True); st.caption("Permisos"); st.write(", ".join(ag.get("perms",[])) or "—")
    st.markdown('</div>', unsafe_allow_html=True)
  if ss.agent_edit_idx is not None and 0 <= ss.agent_edit_idx < len(ss.agents):
    ag = ss.agents[ss.agent_edit_idx]; st.markdown("### Editar agente")
    with st.form(f"agent_edit_{ss.agent_edit_idx}"):
      objetivo = st.text_input("Objetivo*", value=ag.get("objetivo","")); backstory = st.text_area("Backstory*", value=ag.get("backstory",""), height=120); guardrails = st.text_area("Guardrails", value=ag.get("guardrails",""), height=90); st.text_input("Modelo LLM (Evaluación)", value=ag.get('llm_model', LLM_IN_USE), disabled=True); img_src = st.text_input("URL de imagen", value=ag.get("image","")); perms = st.multiselect("Permisos", ["Colaborador","Supervisor","Administrador"], default=ag.get("perms",["Supervisor","Administrador"]))
      if st.form_submit_button("Guardar cambios"): ag.update({"objetivo":objetivo,"backstory":backstory,"guardrails":guardrails, "llm_model":ag.get('llm_model', LLM_IN_USE),"image":img_src,"perms":perms}); save_agents(ss.agents); st.success("Agente actualizado."); st.rerun()

# ... (función render_flow_form SIN CAMBIOS DESDE LA VERSIÓN ANTERIOR) ...
def render_flow_form():
    vista_como = ss.auth.get("role", "Colaborador"); puede_aprobar = vista_como in ("Supervisor", "Administrador")
    is_view_mode = bool(ss.get("viewing_flow_id")); is_edit_mode = bool(ss.get("editing_flow_id"))
    flow_id_to_load = ss.get("editing_flow_id") or ss.get("viewing_flow_id"); editing_wf = None
    if flow_id_to_load: editing_wf = next((w for w in ss.workflows if w["id"] == flow_id_to_load), None)
    is_disabled = is_view_mode
    role_options = [p.get("Puesto") for p in ss.positions if p.get("Puesto")]
    if not role_options: st.error("No hay puestos definidos."); ss.show_flow_form = False; st.rerun(); return
    default_name = editing_wf.get("name", "Analizar CV") if editing_wf else "Analizar CV"
    default_role = editing_wf.get("role", role_options[0]) if editing_wf else role_options[0]
    try: role_index = role_options.index(default_role)
    except ValueError: role_index = 0
    default_desc = editing_wf.get("description", EVAL_INSTRUCTION) if editing_wf else EVAL_INSTRUCTION
    default_expected = editing_wf.get("expected_output", "- Puntuación 0-100\n- Resumen CV") if editing_wf else "- Puntuación 0-100\n- Resumen CV"
    selected_role_from_key = ss.get("flow_form_role_select", default_role)
    if editing_wf and editing_wf.get("jd_text"): default_jd_text = editing_wf.get("jd_text")
    else: pos_data = next((p for p in ss.positions if p.get("Puesto") == selected_role_from_key), None); default_jd_text = pos_data.get("JD", "JD no encontrado.") if pos_data else "JD no encontrado."
    default_agent_idx = editing_wf.get("agent_idx", 0) if editing_wf else 0
    if not (0 <= default_agent_idx < len(ss.agents)): default_agent_idx = 0
    if is_view_mode: st.subheader(f"Viendo Flujo: {editing_wf.get('name')}")
    elif is_edit_mode: st.subheader(f"Editando Flujo: {editing_wf.get('name')}")
    else: st.subheader("Crear Flujo")
    if is_view_mode or is_edit_mode:
        if st.button("✖ Cerrar Vista"): ss.editing_flow_id = None; ss.viewing_flow_id = None; ss.show_flow_form = False; st.rerun()
    with st.form("wf_form"):
        st.markdown("<div class='badge'>Task · Describe la tarea</div>", unsafe_allow_html=True)
        name = st.text_input("Name*", value=default_name, disabled=is_disabled)
        role = st.selectbox("Puesto objetivo", role_options, index=role_index, key="flow_form_role_select", disabled=is_disabled)
        desc = st.text_area("Description*", value=default_desc, height=110, disabled=is_disabled)
        expected = st.text_area("Expected output*", value=default_expected, height=80, disabled=is_disabled)
        st.markdown("**Job Description (cargado desde 'Puestos')**")
        jd_text = st.text_area("JD en texto", value=default_jd_text, height=140, key="flow_jd_text", disabled=is_disabled)
        jd_from_file = ""
        if not is_view_mode:
            st.caption("Puedes editar el JD aquí o subir un archivo (no cambiará el JD en 'Puestos').")
            jd_file = st.file_uploader("...o sube/reemplaza JD", type=["pdf","txt","docx"], key="wf_jd_file", disabled=is_disabled)
            if jd_file is not None: jd_from_file = extract_text_from_file(jd_file); st.caption("Vista previa:"); st.text_area("Preview", jd_from_file[:4000], height=160, disabled=True)
        st.markdown("---"); st.markdown("<div class='badge'>Staff in charge · Agente asignado</div>", unsafe_allow_html=True)
        if ss.agents: agent_opts = [f"{i} — {a.get('rol','Agente')}" for i,a in enumerate(ss.agents)]; agent_pick = st.selectbox("Asigna un agente", agent_opts, index=default_agent_idx, disabled=is_disabled); agent_idx = int(agent_pick.split(" — ")[0])
        else: st.info("No hay agentes."); agent_idx = -1
        st.markdown("---"); st.markdown("<div class='badge'>Guardar · Aprobación y programación</div>", unsafe_allow_html=True)
        run_date = st.date_input("Fecha de ejecución", value=date.today()+timedelta(days=1), disabled=is_disabled)
        run_time = st.time_input("Hora de ejecución", value=datetime.now().time().replace(second=0, microsecond=0), disabled=is_disabled)
        save_draft = False; send_approval = False; schedule = False; update_flow = False
        if is_view_mode: st.caption("Estás en modo de solo lectura."); st.form_submit_button("Cerrar", disabled=True, help="Usa el botón '✖ Cerrar Vista' de arriba.")
        elif is_edit_mode: update_flow = st.form_submit_button("💾 Actualizar Flujo")
        else: col_a, col_b, col_c = st.columns(3); save_draft = col_a.form_submit_button("💾 Guardar borrador"); send_approval = col_b.form_submit_button("📝 Enviar a aprobación"); schedule = col_c.form_submit_button("📅 Guardar y Programar")
        if save_draft or send_approval or schedule or update_flow:
            if not is_view_mode:
                jd_final = jd_from_file if jd_from_file.strip() else ss.get("flow_jd_text", default_jd_text)
                if not jd_final.strip() or jd_final.startswith("JD no"): st.error("Debes proporcionar un JD."); return
                if agent_idx < 0: st.error("Debes asignar un agente."); return
                wf_data = {"name": name, "role": role, "description": desc, "expected_output": expected, "jd_text": jd_final[:200000], "agent_idx": agent_idx, "last_updated_by": ss.auth.get("name", "Admin")}
                if update_flow and is_edit_mode: editing_wf.update(wf_data); editing_wf.update({"status": "Borrador", "approved_by": "", "approved_at": "", "schedule_at": ""}); save_workflows(ss.workflows); st.success("Flujo actualizado."); ss.editing_flow_id = None; ss.show_flow_form = False; st.rerun()
                elif not is_edit_mode:
                    wf = wf_data.copy(); wf.update({"id": f"WF-{int(datetime.now().timestamp())}", "created_at": datetime.now().isoformat(), "created_by": ss.auth.get("name", "Admin"), "status": "Borrador", "approved_by": "", "approved_at": "", "schedule_at": ""})
                    if send_approval: wf["status"] = "Pendiente de aprobación"; st.success("Flujo enviado a aprobación.")
                    if schedule:
                        if puede_aprobar: wf["status"]="Programado"; wf["schedule_at"]=f"{run_date} {run_time.strftime('%H:%M')}"; st.success("Flujo programado.")
                        else: wf["status"]="Pendiente de aprobación"; wf["schedule_at"]=f"{run_date} {run_time.strftime('%H:%M')}"; st.info("Pendiente de aprobación.")
                    if save_draft: st.success("Borrador guardado.")
                    ss.workflows.insert(0, wf); save_workflows(ss.workflows); ss.show_flow_form = False; st.rerun()

# ... (función page_flows SIN CAMBIOS DESDE LA VERSIÓN ANTERIOR) ...
def page_flows():
    st.header("Flujos")
    if st.button("➕ Nuevo Flujo" if not ss.show_flow_form else "✖ Ocultar Formulario", key="toggle_flow_form"):
        ss.show_flow_form = not ss.show_flow_form
        if not ss.show_flow_form: ss.editing_flow_id = None; ss.viewing_flow_id = None
        st.rerun()
    if ss.show_flow_form: render_flow_form()
    if not ss.show_flow_form:
        st.subheader("Mis flujos")
        if not ss.workflows: st.info("No hay flujos aún. Crea uno con **➕ Nuevo Flujo**."); return
        col_w = [0.8, 1.5, 2.5, 1.2, 1.2, 1.3]; h_id, h_nom, h_desc, h_cre, h_est, h_acc = st.columns(col_w)
        with h_id: st.markdown("**Id**"); with h_nom: st.markdown("**Nombre**"); with h_desc: st.markdown("**Descripción**"); with h_cre: st.markdown("**Creado el**"); with h_est: st.markdown("**Estado**"); with h_acc: st.markdown("**Acciones**")
        st.markdown("<hr style='border:1px solid #E3EDF6; opacity:.6;'/>", unsafe_allow_html=True)
        for wf in ss.workflows:
            wf_id = wf.get("id", str(uuid.uuid4())); wf["id"] = wf_id
            c_id, c_nom, c_desc, c_cre, c_est, c_acc = st.columns(col_w)
            with c_id: st.caption(f"{wf_id[:8]}...")
            with c_nom: st.markdown(f"**{wf.get('name', '—')}**"); st.caption(f"Puesto: {wf.get('role', 'N/A')}")
            with c_desc: st.caption(f"{wf.get('description', '—')[:80]}...")
            with c_cre:
                try: creado_dt = datetime.fromisoformat(wf.get('created_at', '')); st.markdown(creado_dt.strftime('%Y-%m-%d'))
                except: st.markdown("—")
            with c_est: st.markdown(_flow_status_pill(wf.get('status', 'Borrador')), unsafe_allow_html=True)
            with c_acc: st.selectbox("Acciones", ["Selecciona...", "Ver detalles", "Editar", "Eliminar"], key=f"flow_action_{wf_id}", label_visibility="collapsed", on_change=_handle_flow_action_change, args=(wf_id,))
            if ss.get("confirm_delete_flow_id") == wf_id:
                st.error(f"¿Seguro que quieres eliminar el flujo **{wf.get('name')}**?")
                b1, b2, _ = st.columns([1, 1, 5])
                with b1:
                    if st.button("Sí, Eliminar", key=f"flow_del_confirm_{wf_id}", type="primary", use_container_width=True): ss.workflows = [w for w in ss.workflows if w.get("id") != wf_id]; save_workflows(ss.workflows); ss.confirm_delete_flow_id = None; st.warning(f"Flujo '{wf.get('name')}' eliminado."); st.rerun()
                with b2:
                    if st.button("Cancelar", key=f"flow_del_cancel_{wf_id}", use_container_width=True): ss.confirm_delete_flow_id = None; st.rerun()
            st.markdown("<hr style='border:1px solid #E3EDF6; opacity:.35;'/>", unsafe_allow_html=True)

# ... (función page_analytics SIN CAMBIOS DESDE LA VERSIÓN ANTERIOR) ...
def page_analytics():
    st.header("Analytics y KPIs Estratégicos")
    st.subheader("Visión General del Proceso")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Costo por Hire (Promedio)", "S/ 4,250", "-8% vs Q2"); c2.metric("Time to Hire (P50)", "28 días", "+2 días"); c3.metric("Conversión (Oferta > Contratado)", "81%", "+3%"); c4.metric("Exactitud de IA (Fit)", "92%", "Modelo v2.1")
    st.markdown("---")
    col_funnel, col_time = st.columns(2)
    with col_funnel:
        st.subheader("Embudo de Conversión"); df_funnel = pd.DataFrame({"Fase": ["Recibido", "Screening RRHH", "Entrevista Gerencia", "Oferta", "Contratado"], "Candidatos": [1200, 350, 80, 25, 20]})
        df_funnel = df_funnel[df_funnel["Candidatos"] > 0]; fig_funnel = px.funnel(df_funnel, x='Candidatos', y='Fase', title="Conversión Total por Fase")
        fig_funnel.update_traces(marker=dict(color=PRIMARY)); fig_funnel.update_layout(plot_bgcolor="#FFFFFF", paper_bgcolor="rgba(0,0,0,0)", font=dict(color=TITLE_DARK), yaxis_title=None); st.plotly_chart(fig_funnel, use_container_width=True)
    with col_time:
        st.subheader("Tiempos del Proceso (P50 / P90)"); df_times = pd.DataFrame({"Métrica": ["Time to Interview", "Time to Offer", "Time to Hire"], "P50 (Días)": [12, 22, 28], "P90 (Días)": [20, 31, 42]})
        df_times_melted = df_times.melt(id_vars="Métrica", var_name="Percentil", value_name="Días"); fig_time = px.bar(df_times_melted, x="Métrica", y="Días", color="Percentil", barmode="group", title="Tiempos Clave (P50 vs P90)", color_discrete_sequence=PLOTLY_GREEN_SEQUENCE)
        fig_time.update_layout(plot_bgcolor="#FFFFFF", paper_bgcolor="rgba(0,0,0,0)", font=dict(color=TITLE_DARK), yaxis_title="Días"); st.plotly_chart(fig_time, use_container_width=True)
    st.markdown("---"); col_prod, col_cost_ia = st.columns(2)
    with col_prod:
        st.subheader("Productividad del Reclutador"); df_prod = pd.DataFrame({"Reclutador": ["Admin", "Sup", "Colab", "Headhunter"], "Contratados (Últ. 90d)": [8, 5, 12, 9], "CVs Gestionados": [450, 300, 700, 620]})
        fig_prod = px.bar(df_prod, x="Reclutador", y="Contratados (Últ. 90d)", title="Contrataciones por Reclutador", color_discrete_sequence=PLOTLY_GREEN_SEQUENCE)
        fig_prod.update_layout(plot_bgcolor="#FFFFFF", paper_bgcolor="rgba(0,0,0,0)", font=dict(color=TITLE_DARK)); st.plotly_chart(fig_prod, use_container_width=True)
    with col_cost_ia:
        st.subheader("Exactitud de IA"); df_ia = pd.DataFrame({"Puesto": ["Analytics", "UX", "Ingeniero/a", "Enfermera/o"], "Candidatos": [120, 85, 200, 310], "Fit Promedio IA": [82, 75, 88, 79]})
        fig_ia = px.scatter(df_ia, x="Candidatos", y="Fit Promedio IA", size="Candidatos", color="Puesto", title="Fit Promedio (IA) por Volumen", color_discrete_sequence=PLOTLY_GREEN_SEQUENCE)
        fig_ia.update_layout(plot_bgcolor="#FFFFFF", paper_bgcolor="rgba(0,0,0,0)", font=dict(color=TITLE_DARK)); st.plotly_chart(fig_ia, use_container_width=True)


# ===================== TODAS LAS TAREAS (Req 6 - Modificado) =====================
def page_create_task():
    st.header("Todas las Tareas")
    with st.expander("➕ Crear Tarea Manual"):
        with st.form("manual_task_form", clear_on_submit=True):
            # ... (Formulario de creación manual sin cambios) ...
            st.markdown("**Nueva Tarea**"); new_title = st.text_input("Título*"); new_desc = st.text_area("Descripción")
            c1, c2, c3 = st.columns(3)
            with c1: new_due = st.date_input("Vencimiento", date.today() + timedelta(days=7))
            with c2: all_assignees = list(USERS.keys()) + DEFAULT_ROLES; new_assignee = st.selectbox("Asignar a", sorted(list(set(all_assignees))), index=0)
            with c3: new_prio = st.selectbox("Prioridad", TASK_PRIORITIES, index=1)
            if st.form_submit_button("Guardar Tarea"):
                if new_title.strip(): create_manual_task(new_title, new_desc, new_due, new_assignee, new_prio); st.success(f"Tarea '{new_title}' creada."); st.rerun()
                else: st.error("El Título es obligatorio.")

    st.info("Haz clic en una tarea para ver detalles y acciones.")
    if not isinstance(ss.tasks, list): ss.tasks = load_tasks()
    if not isinstance(ss.tasks, list) or not ss.tasks: st.write("No hay tareas registradas."); return

    tasks_list = ss.tasks
    all_statuses = ["Todos"] + sorted(list(set(t.get('status', 'Pendiente') for t in tasks_list if t.get('status')) | {"En Espera"}))
    prefer_order = ["Pendiente", "En Proceso", "En Espera"]; preferred = next((s for s in prefer_order if s in all_statuses), "Todos")
    selected_status = st.selectbox("Filtrar por Estado", options=all_statuses, index=all_statuses.index(preferred))
    tasks_to_show = tasks_list if selected_status == "Todos" else [t for t in tasks_list if t.get("status") == selected_status]
    if not tasks_to_show: st.info(f"No hay tareas con estado '{selected_status}'."); return

    for task in tasks_to_show:
        t_id = task.get("id") or str(uuid.uuid4()); task["id"] = t_id
        with st.expander(f"{task.get('titulo','—')}"):
            st.markdown('<div class="task-details-grid">', unsafe_allow_html=True)
            st.markdown(f"<div><strong>Asignado a</strong> {task.get('assigned_to','—')}</div>", unsafe_allow_html=True)
            st.markdown(f"<div><strong>Creado el</strong> {task.get('created_at','—')}</div>", unsafe_allow_html=True)
            st.markdown(f"<div><strong>Vencimiento</strong> {task.get('due','—')}</div>", unsafe_allow_html=True)
            st.markdown(f"<div><strong>Estado</strong> {_status_pill(task.get('status','Pendiente'))}</div>", unsafe_allow_html=True)
            st.markdown(f"<div><strong>Prioridad</strong> {_priority_pill(task.get('priority','Media'))}</div>", unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

            context = task.get("context", {})
            if context.get("source") == "IA Evaluation":
                 st.markdown("**Resultados IA**"); ia_score = context.get('ia_score', 'N/A'); ia_analysis = context.get('ia_analysis', 'No disponible.')
                 try: score_num = int(ia_score); color = PRIMARY if score_num >= 70 else ('#FFA500' if score_num >= 40 else '#D60000'); st.markdown(f"<span class='badge' style='border-color:{color}; background:{color}20; color:{color}; font-weight:bold; font-size:1rem;'>Puntuación: {score_num}%</span>", unsafe_allow_html=True)
                 except: st.markdown(f"**Puntuación:** {ia_score}")
                 st.caption("**Análisis IA:**"); st.markdown(f"> {ia_analysis}"); st.markdown("---")
            
            st.markdown("**Descripción General de Tarea**"); st.caption(task.get("desc","—") or "Sin descripción."); st.markdown("---")

            def _handle_action_change(task_id): # Callback sin cambios
                selectbox_key = f"accion_{task_id}"; action = ss.get(selectbox_key)
                if not action: return
                task_to_update = next((t for t in ss.tasks if t.get("id") == task_id), None)
                if not task_to_update: return
                ss.confirm_delete_id = None; ss.show_assign_for = None; ss.expanded_task_id = None
                if action == "Ver detalle": ss.expanded_task_id = task_id
                elif action == "Asignar tarea": ss.show_assign_for = task_id
                elif action == "Tomar tarea": current_user = ss.auth.get("name", "Admin"); task_to_update["assigned_to"] = current_user; task_to_update["status"] = "En Proceso"; save_tasks(ss.tasks); st.toast("Tarea tomada.")
                elif action == "Eliminar": ss.confirm_delete_id = task_id
                ss[selectbox_key] = "Selecciona…" # Resetear

            selectbox_key = f"accion_{t_id}"
            st.selectbox("Acciones", ["Selecciona…", "Ver detalle", "Asignar tarea", "Tomar tarea", "Eliminar"], key=selectbox_key, label_visibility="collapsed", on_change=_handle_action_change, args=(t_id,))

            if ss.get("confirm_delete_id") == t_id: # Confirmación de borrado
                b1, b2, _ = st.columns([1.0, 1.0, 7.8])
                with b1:
                    if st.button("Eliminar", key=f"del_confirm_{t_id}", type="primary", use_container_width=True): ss.tasks = [t for t in ss.tasks if t.get("id") != t_id]; save_tasks(ss.tasks); ss.confirm_delete_id = None; st.warning("Tarea eliminada."); st.rerun()
                with b2:
                    if st.button("Cancelar", key=f"del_cancel_{t_id}", use_container_width=True): ss.confirm_delete_id = None; st.rerun()

            if ss.show_assign_for == t_id: # Formulario de reasignación
                a1, a2, a3, a4, _ = st.columns([1.6, 1.6, 1.2, 1.0, 3.0])
                with a1: assign_type = st.selectbox("Tipo", ["En Espera", "Equipo", "Usuario"], key=f"type_{t_id}", index=2)
                with a2:
                    if assign_type == "En Espera": nuevo_assignee = "En Espera"; st.text_input("Asignado a", "En Espera", key=f"val_esp_{t_id}", disabled=True)
                    elif assign_type == "Equipo": nuevo_assignee = st.selectbox("Equipo", ["Coordinador RR.HH.", "Admin RR.HH.", "Agente de Análisis"], key=f"val_eq_{t_id}")
                    else: nuevo_assignee = st.selectbox("Usuario", ["Headhunter", "Colab", "Sup", "Admin"], key=f"val_us_{t_id}")
                with a3: cur_p = task.get("priority", "Media"); idx_p = TASK_PRIORITIES.index(cur_p) if cur_p in TASK_PRIORITIES else 1; nueva_prio = st.selectbox("Prioridad", TASK_PRIORITIES, key=f"prio_{t_id}", index=idx_p)
                with a4:
                    if st.button("Guardar", key=f"btn_assign_{t_id}", use_container_width=True):
                        task_to_update = next((t for t in ss.tasks if t.get("id") == t_id), None)
                        if task_to_update: task_to_update["assigned_to"] = nuevo_assignee; task_to_update["priority"] = nueva_prio; task_to_update["status"] = "En Espera" if assign_type == "En Espera" else ("Pendiente" if task_to_update["status"] == "En Espera" else task_to_update["status"]); save_tasks(ss.tasks); ss.show_assign_for = None; st.success("Cambios guardados."); st.rerun()

    # Lógica del diálogo para Tareas (sin cambios)
    task_id_for_dialog = ss.get("expanded_task_id")
    if task_id_for_dialog:
        task_data = next((t for t in ss.tasks if t.get("id") == task_id_for_dialog), None)
        if task_data:
            try:
                dialog = st.dialog("Detalle de Tarea", width="large")
                dialog.markdown(f"### {task_data.get('titulo', 'Sin Título')}")
                c1, c2 = dialog.columns(2)
                with c1: dialog.markdown("**Info Principal**"); dialog.markdown(f"**Asignado:** `{task_data.get('assigned_to', 'N/A')}`"); dialog.markdown(f"**Vence:** `{task_data.get('due', 'N/A')}`"); dialog.markdown(f"**Creado:** `{task_data.get('created_at', 'N/A')}`")
                with c2: dialog.markdown("**Estado/Prioridad**"); dialog.markdown(f"**Estado:**"); dialog.markdown(_status_pill(task_data.get('status', 'Pendiente')), unsafe_allow_html=True); dialog.markdown(f"**Prioridad:**"); dialog.markdown(_priority_pill(task_data.get('priority', 'Media')), unsafe_allow_html=True)
                context = task_data.get("context", {})
                if context.get("source") == "IA Evaluation":
                    dialog.markdown("---"); dialog.markdown("**Resultados IA**"); ia_score = context.get('ia_score', 'N/A'); ia_analysis = context.get('ia_analysis', 'No disponible.'); dialog.markdown(f"**Puntuación:** {ia_score}%"); dialog.caption("**Análisis IA:**"); dialog.markdown(f"> {ia_analysis}")
                elif context and ("candidate_name" in context or "role" in context):
                     dialog.markdown("---"); dialog.markdown("**Contexto Flujo**");
                     if "candidate_name" in context: dialog.markdown(f"**Postulante:** {context['candidate_name']}")
                     if "role" in context: dialog.markdown(f"**Puesto:** {context['role']}")
                dialog.markdown("---"); dialog.markdown("**Descripción:**"); dialog.markdown(task_data.get('desc', 'Sin descripción.'))
                dialog.markdown("---"); dialog.markdown("**Actividad:**"); dialog.markdown("- *Sin actividad.*")
                with dialog.form("comment_form_dialog"): st.text_area("Comentarios", key=f"task_comment_dialog_{task_data.get('id')}"); submitted = st.form_submit_button("Enviar");
                if submitted: st.toast("Comentario (aún no) guardado.")
                if dialog.button("Cerrar", key="close_task_dialog"): ss.expanded_task_id = None; dialog.close()
            except Exception as e: st.error(f"Error al mostrar detalles: {e}"); ss.expanded_task_id = None
        else: ss.expanded_task_id = None

# =========================================================
# ROUTER
# =========================================================
# Asegúrate que todas las funciones estén definidas ANTES de este diccionario
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
    if require_auth():
        render_sidebar()
        # La llamada al router usa la sección actual guardada en session_state
        ROUTES.get(ss.section, page_def_carga)()
