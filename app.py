# app.py
# -*- coding: utf-8 -*-

# =========================================================
# IMPORTS
# =========================================================
import io, base64, re, json, random, zipfile, uuid, tempfile, os
from pathlib import Path
from datetime import datetime, date, timedelta

import streamlit as st
import pandas as pd
import plotly.express as px
from PyPDF2 import PdfReader

# ====== (LLM / LangChain) - usados SOLO en “Evaluación de CVs > Resultados LLM” ======
_LC_AVAILABLE = True
try:
    from langchain_core.output_parsers import JsonOutputParser
    from langchain_core.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate
    from langchain_community.document_loaders import PyPDFLoader
    from langchain_openai import AzureChatOpenAI
except Exception:
    _LC_AVAILABLE = False

# =========================================================
# PALETA / CONST (NO CAMBIAR LOOK & FEEL)
# =========================================================
PRIMARY       = "#00CD78"
SIDEBAR_BG    = "#0E192B"
SIDEBAR_TX    = "#B9C7DF"
BODY_BG       = "#F7FBFF"
CARD_BG       = "#0E192B"
TITLE_DARK    = "#142433"

BAR_DEFAULT   = "#E9F3FF"
BAR_GOOD      = "#33FFAC"

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
  "Admin RR.HH.":      "https://images.unsplash.com/photo-1526378722484-bd91ca387e72?q=80&w=512&auto-format&fit=crop",
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

# ---------------------------------------------------------
# Bytes PDF dummy
# ---------------------------------------------------------
DUMMY_PDF_BYTES = base64.b64decode(
    b'JVBERi0xLjAKMSAwIG9iajw8L1R5cGUvQ2F0YWxvZy9QYWdlcyAyIDAgUj4+ZW5kb2JqCjIgMCBvYmo8PC9UeXBlL1BhZ2VzL0NvdW50IDEvS2lkc1szIDAgUl0+PmVuZG9iagozIDAgb2JqPDwvVHlwZS9QYWdlL01lZGlhQm94WzAgMCAzMCAzMF0vUGFyZW50IDIgMCBSPj5lbmRvYmoKeHJlZgowIDQKMDAwMDAwMDAwMCA2NTUzNSBmIAowMDAwMDAwMDA5IDAwMDAwIG4gCjAwMDAwMDAwNTIgMDAwMDAgbiAKMDAwMDAwMDA5OSAwMDAwMCBuIAp0cmFpbGVyPDwvU2l6ZSA0L1Jvb3QgMSAwIFI+PgpzdGFydHhyZWYKMTQ3CiUlRU9G'
)

# =========================================================
# CSS (NO CAMBIAR ESTILO GLOBAL)
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
"""
st.set_page_config(page_title="SelektIA", page_icon="🧠", layout="wide")
st.markdown(f"<style>{CSS}</style>", unsafe_allow_html=True)

# =========================================================
# Persistencia
# =========================================================
DATA_DIR = Path("data"); DATA_DIR.mkdir(exist_ok=True)
AGENTS_FILE     = DATA_DIR/"agents.json"
WORKFLOWS_FILE  = DATA_DIR/"workflows.json"
ROLES_FILE      = DATA_DIR/"roles.json"
TASKS_FILE      = DATA_DIR/"tasks.json"

DEFAULT_ROLES = ["Headhunter", "Coordinador RR.HH.", "Admin RR.HH."]

DEFAULT_TASKS = [
    {"id": str(uuid.uuid4()), "titulo":"Revisar CVs top 5", "desc":"Analizar a los 5 candidatos con mayor fit para 'Business Analytics'.", "due":str(date.today() + timedelta(days=2)), "assigned_to": "Headhunter", "status": "Pendiente", "priority": "Alta", "created_at": (date.today() - timedelta(days=3)).isoformat()},
    {"id": str(uuid.uuid4()), "titulo":"Coordinar entrevista de Rivers Brykson", "desc":"Agendar la 2da entrevista (Gerencia) para el puesto de VP de Marketing.", "due":str(date.today() + timedelta(days=5)), "assigned_to": "Coordinador RR.HH.", "status": "En Proceso", "priority": "Media", "created_at": (date.today() - timedelta(days=8)).isoformat()},
    {"id": str(uuid.uuid4()), "titulo":"Crear workflow de Onboarding", "desc":"Definir pasos en 'Flujos' para Contratado.", "due":str(date.today() - timedelta(days=1)), "assigned_to": "Admin RR.HH.", "status": "Completada", "priority": "Baja", "created_at": (date.today() - timedelta(days=15)).isoformat()}
]

def load_json(path: Path, default):
  if path.exists():
    try: return json.loads(path.read_text(encoding="utf-8"))
    except: pass
  try: path.write_text(json.dumps(default, ensure_ascii=False, indent=2), encoding="utf-8")
  except: pass
  return json.loads(json.dumps(default))

def save_json(path: Path, data):
  try: path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
  except: pass

def load_roles():
  roles = load_json(ROLES_FILE, [])
  roles = sorted(list({*DEFAULT_ROLES, *(r.strip() for r in roles if str(r).strip())}))
  return roles

def save_roles(roles: list):
  custom_only = [r for r in roles if r not in DEFAULT_ROLES]
  save_json(ROLES_FILE, custom_only)

def load_agents(): return load_json(AGENTS_FILE, [])
def save_agents(v): save_json(AGENTS_FILE, v)
def load_workflows(): return load_json(WORKFLOWS_FILE, [])
def save_workflows(v): save_json(WORKFLOWS_FILE, v)
def load_tasks(): return load_json(TASKS_FILE, DEFAULT_TASKS)
def save_tasks(v): save_json(TASKS_FILE, v)

# =========================================================
# ESTADO
# =========================================================
ss = st.session_state
if "auth" not in ss: ss.auth = None
if "section" not in ss:  ss.section = "publicacion_sourcing"

if "tasks_loaded" not in ss:
    ss.tasks = load_tasks()
    if not isinstance(ss.tasks, list): ss.tasks = DEFAULT_TASKS
    ss.tasks_loaded = True

if "candidates" not in ss: ss.candidates = []
if "offers" not in ss:     ss.offers = {}
if "agents_loaded" not in ss:
  ss.agents = load_agents(); ss.agents_loaded = True
if "workflows_loaded" not in ss:
  ss.workflows = load_workflows(); ss.workflows_loaded = True
if "agent_view_idx" not in ss: ss.agent_view_idx = None
if "agent_edit_idx" not in ss: ss.agent_edit_idx = None
if "new_role_mode" not in ss: ss.new_role_mode = False
if "roles" not in ss: ss.roles = load_roles()
if "pipeline_filter" not in ss: ss.pipeline_filter = None
if "confirm_delete_id" not in ss: ss.confirm_delete_id = None
if "llm_results" not in ss: ss.llm_results = []
if "eval_llm_busy" not in ss: ss.eval_llm_busy = False

# Data de Puestos
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

# Inicialización candidatos demo
if "candidate_init" not in ss:
  initial_candidates = [
    {"Name": "CV_AnaLopez.pdf", "Score": 85, "Role": "Business Analytics", "source": "LinkedIn Jobs"},
    {"Name": "CV_LuisGomez.pdf", "Score": 42, "Role": "Business Analytics", "source": "Computrabajo"},
    {"Name": "CV_MartaDiaz.pdf", "Score": 91, "Role": "Desarrollador/a Backend (Python)", "source": "Indeed"},
    {"Name": "CV_JaviRuiz.pdf", "Score": 30, "Role": "Diseñador/a UX", "source": "laborum.pe"},
  ]
  out=[]
  for i, c in enumerate(initial_candidates):
    c["id"] = f"C{i+1}-{random.randint(1000,9999)}"
    c["stage"] = PIPELINE_STAGES[random.choice([0, 1, 1, 2, 6])]
    c["load_date"] = (date.today() - timedelta(days=random.randint(5, 30))).isoformat()
    c["_bytes"] = DUMMY_PDF_BYTES
    c["_is_pdf"] = True
    c["_text"] = f"CV de {c['Name']}. Experiencia 5 años. Skills: SQL, Power BI, Python, Excel. Candidato {c['Name']}."
    out.append(c)
  ss.candidates = out
  ss.candidate_init = True

# =========================================================
# UTILS de análisis
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
  must=set([m.strip() for m in must_list if str(m).strip()]) or jd_skills
  nice=set([n.strip() for n in nice_list if str(n).strip()])-must
  cv=infer_skills(cv_text)
  mm=sorted(list(must&cv)); mn=sorted(list(nice&cv))
  gm=sorted(list(must-cv)); gn=sorted(list(nice-cv))
  extras=sorted(list((cv&(jd_skills|must|nice))-set(mm)-set(mn)))
  cov_m=len(mm)/len(must) if must else 0
  cov_n=len(mn)/len(nice) if nice else 0
  sc=int(round(100*(0.65*cov_m+0.20*cov_n+0.15*min(len(extras),5)/5)))
  return sc, {"matched_must":mm,"matched_nice":mn,"gaps_must":gm,"gaps_nice":gn,"extras":extras,"must_total":len(must),"nice_total":len(nice)}

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
          if page_text: text += page_text + "\n"
        except: pass
      return text
    elif suffix == ".docx":
      return _extract_docx_bytes(file_bytes)
    else:
      return file_bytes.decode("utf-8", errors="ignore")
  except:
    return ""

# =========================================================
# LLM helpers (del bloque original del usuario)
# =========================================================
def _setup_azure_env_from_secrets():
    """Carga credenciales desde st.secrets['llm'] a variables de entorno (sin tocar el código base)."""
    try:
        llmsec = st.secrets["llm"]
        if "AZURE_OPENAI_API_KEY" not in os.environ and "azure_openai_api_key" in llmsec:
            os.environ["AZURE_OPENAI_API_KEY"] = llmsec["azure_openai_api_key"]
        if "AZURE_OPENAI_ENDPOINT" not in os.environ and "azure_openai_endpoint" in llmsec:
            os.environ["AZURE_OPENAI_ENDPOINT"] = llmsec["azure_openai_endpoint"]
    except Exception:
        pass

def _get_prompt_for_cv(resume_content: str) -> ChatPromptTemplate:
    json_object_structure = """{{
        "Name": "Full Name",
        "Last_position": "The most recent position in which the candidate worked",
        "Years_of_Experience": "Number (in years)",
        "English_Level": "Beginner/Intermediate/Advanced/Fluent/Native",
        "Key_Skills": ["Skill 1", "Skill 2", "Skill 3"],
        "Certifications": ["Certification 1", "Certification 2"],
        "Additional_Notes": "Optional details inferred or contextually relevant information.",
        "Score": "0-100"
    }}"""
    json_object_example = """{{
        "Name": "Jane Smith",
        "Last_position": "Data Engineer",
        "Years_of_Experience": 8,
        "English_Level": "Fluent",
        "Key_Skills": ["Project Management", "Data Analysis", "Python", "SQL"],
        "Certifications": ["PMP Certification", "Google Data Analytics Certificate"],
        "Additional_Notes": "Led multiple cross-functional teams.",
        "Score": "87"
    }}"""
    system_template = f"""
    ### Objective:
    - Extract structured info from the resume below and return a JSON object with the specified fields.
    - Given a job description, also return a 0-100 match **Score**.

    ### CV Content:
    {resume_content}

    ### Deliverable JSON shape:
    {json_object_structure}

    ### Example:
    {json_object_example}

    Job description:
    """
    return ChatPromptTemplate.from_messages([
        SystemMessagePromptTemplate.from_template(system_template),
        HumanMessagePromptTemplate.from_template("{job_description}")
    ])

def _extract_with_azure(job_description: str, resume_text: str) -> dict:
    """Usa AzureChatOpenAI + JsonOutputParser (como tu bloque original)."""
    _setup_azure_env_from_secrets()
    llm = AzureChatOpenAI(
        azure_deployment=st.secrets["llm"]["azure_deployment"],
        api_version=st.secrets["llm"]["azure_api_version"],
        temperature=0
    )
    parser = JsonOutputParser()
    prompt = _get_prompt_for_cv(resume_text)
    chain = prompt | llm | parser
    analysis = chain.invoke({"job_description": job_description})
    return analysis

def _create_dataframe_llm(results: list) -> pd.DataFrame:
    df = pd.DataFrame(results)
    if "Score" in df.columns:
        try: df["Score"] = df["Score"].astype(int)
        except: pass
    return df.sort_values(by="Score", ascending=False)

def _create_barchart_llm(df: pd.DataFrame):
    fig = px.bar(df, x='file_name', y='Score', text='Score', title='Comparativa de Puntajes (LLM)')
    fig.update_traces(hovertemplate="%{x}<br>Score: %{y}%")
    fig.update_layout(plot_bgcolor="#FFFFFF", paper_bgcolor="rgba(0,0,0,0)",
                      font=dict(color=TITLE_DARK), xaxis_title=None, yaxis_title="Score (%)")
    return fig

# =========================================================
# LOGIN + SIDEBAR
# =========================================================
def login_screen():
  st.markdown('<div class="login-bg" style="background:#0E192B;position:fixed;inset:0;display:flex;align-items:center;justify-content:center">', unsafe_allow_html=True)
  st.markdown('<div class="login-card" style="background:transparent;border:none;box-shadow:none;padding:0;width:min(600px,92vw);">', unsafe_allow_html=True)
  st.markdown('<div class="login-logo-wrap" style="display:flex;align-items:center;justify-content:center;margin-bottom:14px">', unsafe_allow_html=True)
  st.markdown("</div>", unsafe_allow_html=True)
  st.markdown('<div class="login-sub" style="color:#9fb2d3;text-align:center;margin:0 0 18px 0;font-size:12.5px">Acceso a SelektIA</div>', unsafe_allow_html=True)
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
    if st.button("Analytics", key="sb_analytics"): ss.section = "analytics"

    st.markdown("#### ASISTENTE IA")
    if st.button("Flujos", key="sb_flows"): ss.section = "flows"
    if st.button("Agentes", key="sb_agents"): ss.section = "agents"

    st.markdown("#### PROCESO DE SELECCIÓN")
    if st.button("Publicación & Sourcing", key="sb_pub"): ss.section = "publicacion_sourcing"
    if st.button("Puestos", key="sb_puestos"): ss.section = "puestos"
    if st.button("Evaluación de CVs", key="sb_eval"): ss.section = "eval"
    if st.button("Pipeline de Candidatos", key="sb_pipe"): ss.section = "pipeline"
    if st.button("Entrevista (Gerencia)", key="sb_int"): ss.section = "interview"
    if st.button("Oferta", key="sb_off"): ss.section = "offer"
    if st.button("Onboarding", key="sb_onb"): ss.section = "onboarding"

    st.markdown("#### TAREAS")
    if st.button("Todas las tareas", key="sb_task_all"): ss.section = "create_task"
    if st.button("Asignado a mi", key="sb_task_me"): ss.section = "hh_tasks"
    if st.button("Asignado a mi equipo", key="sb_task_team"): ss.section = "agent_tasks"

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
           "meta": {}, "stage": PIPELINE_STAGES[0], "load_date": date.today().isoformat(),
           "_exp": exp, "source": "Carga Manual"}
      new_candidates.append(c)
    for c in new_candidates:
      if c["Score"] < 35: c["stage"] = "Descartado"
      ss.candidates.append(c)
    st.success(f"CVs cargados, analizados y {len(new_candidates)} enviados al Pipeline.")
    st.rerun()

  st.subheader("3. Sourcing desde Portales")
  with st.expander("🔌 Integración con Portales de Empleo (Laborum, LinkedIn, etc.)"):
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
               "_bytes": DUMMY_PDF_BYTES, "_is_pdf": True, "_text": txt, "meta": {},
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
  df_pos["Time to Hire (promedio)"] = df_pos["Días Abierto"].apply(lambda d: f"{d+random.randint(10, 40)} días" if d < 30 else f"{d} días")
  st.dataframe(
    df_pos[
      ["Puesto","Días Abierto","Time to Hire (promedio)","Leads","Nuevos","Recruiter Screen","HM Screen",
       "Entrevista Telefónica","Entrevista Presencial","Ubicación","Hiring Manager","Estado","ID"]
    ].sort_values(["Estado","Días Abierto","Leads"], ascending=[True,True,False]),
    use_container_width=True, height=380, hide_index=True
  )

# ===================== EVALUACIÓN =====================
def page_eval():
    st.header("Resultados de evaluación")

    if not ss.candidates:
        st.info("Carga CVs en **Publicación & Sourcing**."); return

    # Configuración de ranking (manteniendo vista)
    jd_text = st.text_area("JD para matching por skills", ss.get("last_jd_text",""), height=140)
    preset = ROLE_PRESETS.get(ss.get("last_role",""), {})
    col1,col2 = st.columns(2)
    with col1: must_default = st.text_area("Must-have (coma separada)", value=", ".join(preset.get("must",[])))
    with col2: nice_default = st.text_area("Nice-to-have (coma separada)", value=", ".join(preset.get("nice",[])))
    must = [s.strip() for s in (must_default or "").split(",") if s.strip()]
    nice = [s.strip() for s in (nice_default or "").split(",") if s.strip()]

    enriched = []
    for c in ss.candidates:
        cv = c.get("_text") or (c.get("_bytes") or b"").decode("utf-8","ignore")
        fit, exp = score_fit_by_skills(jd_text, must, nice, cv or "")
        c["Score"] = fit; c["_exp"] = exp
        enriched.append({
            "Name": c["Name"],
            "Fit": fit,
            "Must (ok/total)":f"{len(exp['matched_must'])}/{exp['must_total']}",
            "Nice (ok/total)":f"{len(exp['matched_nice'])}/{exp['nice_total']}",
            "Extras":", ".join(exp["extras"])[:60]
        })
    df = pd.DataFrame(enriched).sort_values("Fit", ascending=False).reset_index(drop=True)

    st.subheader("Ranking por Fit de Skills")
    st.dataframe(df[["Name","Fit","Must (ok/total)","Nice (ok/total)","Extras"]],
                 use_container_width=True, height=260, hide_index=True)

    # ------- Sección LLM real (Azure) con loader conservando look & feel -------
    st.markdown("---")
    with st.expander("Resultados LLM", expanded=True):
        if not _LC_AVAILABLE:
            st.warning("Para evaluar con IA debes instalar las dependencias de LangChain y reiniciar la app.")
            return

        uploaded_files = st.file_uploader(
            "Subir CVs (PDF) para evaluación con IA",
            type=["pdf"], accept_multiple_files=True, key="llm_upl_eval"
        )

        loader_slot = st.empty()
        def _render_loader(show: bool):
            if not show:
                loader_slot.empty(); return
            loader_slot.markdown(f"""
            <div style="display:flex;align-items:center;gap:10px;padding:10px 12px;border:1px solid #E3EDF6;border-radius:12px;background:#FFFFFF;max-width:280px;">
              <div style="width:16px;height:16px;border:3px solid #E3EDF6;border-top-color:{PRIMARY};border-radius:50%;animation:spin .9s linear infinite"></div>
              <div style="font-weight:600;color:{TITLE_DARK};">Analizando CVs…</div>
            </div>
            <style>@keyframes spin{{to{{transform:rotate(360deg)}}}}</style>
            """, unsafe_allow_html=True)

        btn_disabled = ss.eval_llm_busy
        if st.button("Ejecutar evaluación LLM", disabled=btn_disabled, key="btn_llm_run_eval"):
            if not uploaded_files:
                st.warning("Sube al menos un PDF.")
            else:
                try:
                    ss.eval_llm_busy = True; _render_loader(True)
                    results = []
                    job_desc = jd_text or preset.get("jd","")
                    for uf in uploaded_files:
                        # Cargar páginas del PDF con PyPDFLoader (idéntico a tu snippet)
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
                            temp_file.write(uf.read()); pdf_path = temp_file.name
                        pages = PyPDFLoader(pdf_path).load()
                        cv_text = "\n".join([p.page_content for p in pages])

                        meta = _extract_with_azure(job_desc, cv_text)  # <-- AzureChatOpenAI real
                        # Normalizamos “Score” como int y añadimos filename
                        try: meta["Score"] = int(meta.get("Score", 0))
                        except: pass
                        meta["file_name"] = uf.name
                        if "Name" not in meta or not str(meta["Name"]).strip():
                            meta["Name"] = uf.name.replace(".pdf","")
                        results.append(meta)

                    ss.llm_results = results
                    st.success("Evaluación LLM completada.")
                except Exception as e:
                    st.error(f"Ocurrió un error al evaluar: {e}")
                finally:
                    ss.eval_llm_busy = False; _render_loader(False); st.rerun()

        if ss.llm_results:
            df_llm = _create_dataframe_llm(ss.llm_results)
            st.dataframe(df_llm, use_container_width=True, hide_index=True)
            st.plotly_chart(_create_barchart_llm(df_llm), use_container_width=True)

def page_pipeline():
    st.header("Pipeline de Candidatos (Vista Kanban)")
    if not ss.candidates:
        st.info("No hay candidatos activos. Carga CVs en **Publicación & Sourcing**."); return
    candidates_by_stage = {stage: [] for stage in PIPELINE_STAGES}
    for c in ss.candidates: candidates_by_stage[c["stage"]].append(c)
    cols = st.columns(len(PIPELINE_STAGES))
    for i, stage in enumerate(PIPELINE_STAGES):
        with cols[i]:
            st.markdown(f"**{stage} ({len(candidates_by_stage[stage])})**")
            st.markdown("---")
            for c in candidates_by_stage[stage]:
                card_name = c["Name"].split('_')[-1].replace('.pdf', '').replace('.txt', '')
                st.markdown(f"""
                <div class="k-card" style="margin-bottom: 10px; border-left: 4px solid {PRIMARY if c['Score'] >= 70 else ('#FFA500' if c['Score'] >= 40 else '#D60000')}">
                    <div style="font-weight:700; color:{TITLE_DARK};">{card_name}</div>
                    <div style="font-size:12px; opacity:.8;">{c.get("Role", "Puesto")}</div>
                    <div style="font-size:14px; font-weight:700; margin-top:8px;">Fit: <span style="color:{PRIMARY};">{c["Score"]}%</span></div>
                    <div style="font-size:10px; opacity:.6; margin-top:4px;">Fuente: {c.get("source", "N/A")}</div>
                </div>
                """, unsafe_allow_html=True)
                with st.form(key=f"form_move_{c['id']}", clear_on_submit=False):
                    available_stages = [s for s in PIPELINE_STAGES if s != stage]
                    new_stage = st.selectbox("Mover a:", available_stages, key=f"select_move_{c['id']}", index=available_stages.index(PIPELINE_STAGES[min(PIPELINE_STAGES.index(stage)+1, len(PIPELINE_STAGES)-1)]), label_visibility="collapsed")
                    if st.form_submit_button("Mover Candidato"):
                        c["stage"] = new_stage
                        if new_stage == "Contratado": st.balloons()
                        st.rerun()
                st.markdown("<br>", unsafe_allow_html=True)

def page_interview():
  st.header("Entrevista (Gerencia)")
  st.write("Usa el **Pipeline** con el filtro correspondiente para gestionar esta etapa.")
  ss.section = "pipeline"; st.rerun()

def page_offer():
  st.header("Oferta")
  st.write("Usa el **Pipeline** con el filtro **Oferta**.")
  ss.section = "pipeline"; st.rerun()

def page_onboarding():
  st.header("Onboarding")
  st.write("Usa el **Pipeline** con el filtro **Contratado**.")
  ss.section = "pipeline"; st.rerun()

def page_hh_tasks():
    st.header("Tareas Asignadas a Mí")
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
        img_src    = st.text_input("URL de imagen (si deseas)", value=AGENT_DEFAULT_IMAGES.get("Headhunter",""))
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
      img_src      = st.text_input("URL de imagen (si deseas)", value=ag.get("image",""))
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
        if 0 <= ai < len(ss.agents): ag_label = ss.agents[ai].get("rol","Agente")
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
              ss.workflows.insert(0, clone); save_workflows(ss.workflows); st.success("Flujo duplicado."); st.rerun()
          with c2:
            if st.button("🗑 Eliminar"):
              ss.workflows = [w for w in ss.workflows if w["id"]!=wf["id"]]; save_workflows(ss.workflows)
              st.success("Flujo eliminado."); st.rerun()
          with c3:
            st.markdown(f"<div class='badge'>Estado: <b>{wf.get('status','Borrador')}</b></div>", unsafe_allow_html=True)
            if wf.get("status")=="Pendiente de aprobación" and puede_aprobar:
              a1,a2 = st.columns(2)
              with a1:
                if st.button("✅ Aprobar"):
                  wf["status"]="Aprobado"; wf["approved_by"]=vista_como; wf["approved_at"]=datetime.now().isoformat()
                  save_workflows(ss.workflows); st.success("Aprobado."); st.rerun()
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

      st.markdown("**Job Description (elige una opción)**")
      jd_text = st.text_area("JD en texto", value=ROLE_PRESETS[role]["jd"], height=140)

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
        jd_final = jd_text
        if not jd_final.strip(): st.error("Debes proporcionar un JD.")
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
          if save_draft: st.success("Borrador guardado.")
          ss.workflows.insert(0, wf); save_workflows(ss.workflows); st.rerun()

# ===================== ANALYTICS =====================
def _calc_analytics_full():
    stage_counts = {s: 0 for s in PIPELINE_STAGES}
    for c in ss.candidates: stage_counts[c.get("stage", PIPELINE_STAGES[0])] += 1
    funnel_df = pd.DataFrame({"Fase": list(stage_counts.keys()), "Candidatos": list(stage_counts.values())})

    days_open = []
    for c in ss.candidates:
        try:
            ld = datetime.fromisoformat(c.get("load_date", date.today().isoformat()))
            days_open.append((datetime.now() - ld).days)
        except: pass
    if days_open:
        days_sorted = sorted(days_open)
        p50 = days_sorted[len(days_sorted)//2]
        p90 = days_sorted[int(len(days_sorted)*0.9)-1 if len(days_sorted)>1 else 0]
        ttx = {"P50": f"{p50} días", "P90": f"{p90} días"}
    else:
        ttx = {"P50": "—", "P90": "—"}

    conv = []
    for i in range(len(PIPELINE_STAGES)-1):
        a = stage_counts[PIPELINE_STAGES[i]] or 1
        b = stage_counts[PIPELINE_STAGES[i+1]]
        conv.append({"De": PIPELINE_STAGES[i], "A": PIPELINE_STAGES[i+1], "Conversión": round(100*b/a,1)})
    conv_df = pd.DataFrame(conv)

    src_counts = {}
    for c in ss.candidates:
        src = c.get("source","Carga Manual")
        src_counts[src] = src_counts.get(src,0)+1
    prod_df = pd.DataFrame(list(src_counts.items()), columns=["Fuente","Candidatos"])

    hires = stage_counts.get("Contratado",0)
    costo_total = 300 * len(ss.candidates)
    cph = f"${round(costo_total / max(1, hires), 2)}" if hires>0 else "—"

    pairs=[]
    for c in ss.candidates:
        s1=c.get("Score"); s2=c.get("Score_LLM")
        if isinstance(s1,int) and isinstance(s2,int): pairs.append((s1,s2))
    if len(pairs)>=2:
        s1=[p[0] for p in pairs]; s2=[p[1] for p in pairs]
        try:
            import math
            m1=sum(s1)/len(s1); m2=sum(s2)/len(s2)
            num=sum((a-m1)*(b-m2) for a,b in pairs)
            den=math.sqrt(sum((a-m1)**2 for a in s1)*sum((b-m2)**2 for b in s2)) or 1
            corr=round(num/den,2)
        except:
            corr="—"
    else:
        corr="—"

    return funnel_df, ttx, conv_df, prod_df, cph, corr

def page_analytics():
    st.header("Analytics y KPIs Estratégicos")
    funnel_df, ttx, conv_df, prod_df, cph, corr = _calc_analytics_full()

    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Puestos activos", len(ss.positions))
    c2.metric("CVs en Pipeline", len(ss.candidates))
    c3.metric("Tiempo a X (P50/P90)", f"{ttx['P50']} / {ttx['P90']}")
    c4.metric("Exactitud IA (proxy)", corr)

    st.markdown("---")
    a,b = st.columns(2)
    with a:
        st.subheader("Embudo por etapa")
        df_f = funnel_df[funnel_df["Candidatos"]>0]
        fig = px.funnel(df_f, x='Candidatos', y='Fase', title=None)
        fig.update_layout(plot_bgcolor="#FFFFFF", paper_bgcolor="rgba(0,0,0,0)", font=dict(color=TITLE_DARK), yaxis_title=None)
        st.plotly_chart(fig, use_container_width=True)
    with b:
        st.subheader("Conversión por etapa")
        fig2 = px.bar(conv_df, x="De", y="Conversión", color="A", barmode="group")
        fig2.update_layout(plot_bgcolor="#FFFFFF", paper_bgcolor="rgba(0,0,0,0)", font=dict(color=TITLE_DARK), xaxis_title=None, yaxis_title="%")
        st.plotly_chart(fig2, use_container_width=True)

    st.markdown("---")
    c,d = st.columns(2)
    with c:
        st.subheader("Productividad por fuente")
        fig3 = px.pie(prod_df, names="Fuente", values="Candidatos", title=None)
        fig3.update_layout(plot_bgcolor="#FFFFFF", paper_bgcolor="rgba(0,0,0,0)", font=dict(color=TITLE_DARK))
        st.plotly_chart(fig3, use_container_width=True)
    with d:
        st.subheader("Costo por hire (proxy)")
        st.metric("Costo por hire", cph)

# ===================== TODAS LAS TAREAS =====================
def _status_pill(s: str)->str:
  colors = { "Pendiente": "#9AA6B2", "En Proceso": "#0072E3", "Completada": "#10B981", "En Espera": "#FFB700" }
  c = colors.get(s, "#9AA6B2")
  return f'<span class="badge" style="border-color:{c}33;background:{c}14;color:#0A2230">{s}</span>'

def _priority_pill(p: str) -> str:
    p_safe = p if p in TASK_PRIORITIES else "Media"
    return f'<span class="badge priority-{p_safe}">{p_safe}</span>'

def page_create_task():
    st.header("Todas las Tareas")
    if not isinstance(ss.tasks, list): ss.tasks = load_tasks()
    if not ss.tasks:
        st.write("No hay tareas registradas en el sistema."); return

    tasks_list = ss.tasks
    all_statuses = ["Todos"] + sorted(list({t.get('status','Pendiente') for t in tasks_list}))
    prefer_order = ["Pendiente","En Proceso","En Espera"]
    preferred = next((s for s in prefer_order if s in all_statuses), "Todos")
    selected_status = st.selectbox("Filtrar por Estado", options=all_statuses, index=all_statuses.index(preferred))

    tasks_to_show = tasks_list if selected_status=="Todos" else [t for t in tasks_list if t.get("status")==selected_status]
    if not tasks_to_show:
        st.info(f"No hay tareas con el estado '{selected_status}'."); return

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
        with c_nom:  st.markdown(f"**{task.get('titulo','—')}**")
        with c_desc: st.caption(task.get("desc","—"))
        with c_asg:  st.markdown(f"`{task.get('assigned_to','—')}`")
        with c_cre:  st.markdown(task.get("created_at","—"))
        with c_due:  st.markdown(task.get("due","—"))
        with c_pri:  st.markdown(_priority_pill(task.get("priority","Media")), unsafe_allow_html=True)
        with c_est:  st.markdown(_status_pill(task.get("status","Pendiente")), unsafe_allow_html=True)

        def _handle_action_change(task_id):
            selectbox_key = f"accion_{task_id}"
            if selectbox_key not in ss: return
            action = ss[selectbox_key]
            task_to_update = next((t for t in ss.tasks if t.get("id") == task_id), None)
            if not task_to_update: return
            if action == "Tomar tarea":
                current_user = (ss.auth["name"] if ss.get("auth") else "Admin")
                task_to_update["assigned_to"] = current_user
                task_to_update["status"] = "En Proceso"
                save_tasks(ss.tasks); st.toast("Tarea tomada."); st.rerun()
            elif action == "Eliminar":
                ss.tasks = [t for t in ss.tasks if t.get("id") != task_id]; save_tasks(ss.tasks); st.rerun()

        with c_acc:
            selectbox_key = f"accion_{t_id}"
            st.selectbox("Acciones", ["Selecciona…", "Tomar tarea", "Eliminar"], key=selectbox_key, label_visibility="collapsed",
                         on_change=_handle_action_change, args=(t_id,))

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
  "analytics": page_analytics,
  "create_task": page_create_task,
}

# =========================================================
# APP
# =========================================================
if require_auth():
    render_sidebar()
    ROUTES.get(ss.section, page_def_carga)()
