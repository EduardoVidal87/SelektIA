# app.py
# -*- coding: utf-8 -*-

import io, base64, re, json, random, zipfile, uuid
from pathlib import Path
from datetime import datetime, date, timedelta

import streamlit as st
import pandas as pd
import plotly.express as px
from PyPDF2 import PdfReader

# =========================================================
# PALETA / CONST
# =========================================================
PRIMARY       = "#00CD78" 
SIDEBAR_BG = "#0E192B"
SIDEBAR_TX = "#B9C7DF"
BODY_BG     = "#F7FBFF"
CARD_BG     = "#0E192B"
TITLE_DARK = "#142433"

PIPELINE_STAGES = ["Recibido", "Screening RRHH", "Entrevista Telefónica", "Entrevista Gerencia", "Oferta", "Contratado", "Descartado"]

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
  "Headhunter":        "https://images.unsplash.com/photo-1581090464777-f3220bbe1b8b?q=80&w=512&auto=format&fit=crop",
  "Coordinador RR.HH.":"https://images.unsplash.com/photo-1542751371-adc38448a05e?q=80&w=512&auto=format&fit=crop",
  "Admin RR.HH.":      "https://images.unsplash.com/photo-1526378722484-bd91ca387e72?q=80&w=512&auto=format&fit=crop",
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
h1, h2, h3 {{ color: {TITLE_DARK}; }}
h1 strong, h2 strong, h3 strong {{ color: var(--green); }}
.block-container [data-testid="stSelectbox"]>div>div,
.block-container [data-baseweb="select"],
.block-container [data-testid="stTextInput"] input,
.block-container [data-testid="stTextArea"] textarea {{
  background:#F1F7FD !important; color:{TITLE_DARK} !important; border:1.5px solid #E3EDF6 !important; border-radius:10px !important;
}}
.block-container table {{ background:#fff !important; border:1px solid #E3EDF6 !important; border-radius:8px !important; }}
.block-container thead th {{ background:#F1F7FD !important; color:{TITLE_DARK} !important; }}
.k-card {{ background:#fff;border:1px solid #E3EDF6;border-radius:12px;padding:14px; }}
.badge {{ display:inline-flex;align-items:center;gap:6px;background:#F1F7FD;border:1px solid #E3EDF6;border-radius:24px;padding:4px 10px;font-size:12px;color:#1B2A3C; }}
"""
st.set_page_config(page_title="SelektIA", page_icon="🧠", layout="wide")
st.markdown(f"<style>{CSS}</style>", unsafe_allow_html=True)

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
# Persistencia (Agentes / Flujos / Roles / Puestos / Tareas)
# =========================================================
DATA_DIR = Path("data"); DATA_DIR.mkdir(exist_ok=True)
AGENTS_FILE = DATA_DIR/"agents.json"
WORKFLOWS_FILE = DATA_DIR/"workflows.json"
ROLES_FILE = DATA_DIR / "roles.json"

# Puestos
POSITIONS_FILE = DATA_DIR / "positions.json"
def load_positions():
  if POSITIONS_FILE.exists():
    try:
      return pd.DataFrame(json.loads(POSITIONS_FILE.read_text(encoding="utf-8")))
    except: pass
  return pd.DataFrame()
def save_positions(df: pd.DataFrame):
  POSITIONS_FILE.write_text(json.dumps(df.to_dict(orient="records"), ensure_ascii=False, indent=2), encoding="utf-8")

# Tareas
TASKS_FILE = DATA_DIR / "tasks.json"
def load_tasks():
  if TASKS_FILE.exists():
    try:
      return json.loads(TASKS_FILE.read_text(encoding="utf-8"))
    except: pass
  return []
def save_tasks(tasks: list):
  TASKS_FILE.write_text(json.dumps(tasks, ensure_ascii=False, indent=2), encoding="utf-8")

DEFAULT_ROLES = ["Headhunter", "Coordinador RR.HH.", "Admin RR.HH."]

def load_roles():
  if ROLES_FILE.exists():
    try:
      roles = json.loads(ROLES_FILE.read_text(encoding="utf-8"))
      roles = sorted(list({*DEFAULT_ROLES, *(r.strip() for r in roles if r.strip())}))
      return roles
    except: pass
  return DEFAULT_ROLES.copy()
def save_roles(roles: list):
  roles_clean = sorted(list({r.strip() for r in roles if r.strip()}))
  custom_only = [r for r in roles_clean if r not in DEFAULT_ROLES]
  ROLES_FILE.write_text(json.dumps(custom_only, ensure_ascii=False, indent=2), encoding="utf-8")

def load_json(path: Path, default):
  if path.exists():
    try: return json.loads(path.read_text(encoding="utf-8"))
    except: return default
  return default
def save_json(path: Path, data):
  path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
def load_agents(): return load_json(AGENTS_FILE, [])
def save_agents(agents): save_json(AGENTS_FILE, agents)
def load_workflows(): return load_json(WORKFLOWS_FILE, [])
def save_workflows(wfs): save_json(WORKFLOWS_FILE, wfs)

# =========================================================
# ESTADO
# =========================================================
ss = st.session_state
if "auth" not in ss: ss.auth = None
if "section" not in ss:  ss.section = "publicacion_sourcing" 
if "pipeline_filter" not in ss: ss.pipeline_filter = None
if "agent_view_idx" not in ss: ss.agent_view_idx = None
if "agent_edit_idx" not in ss: ss.agent_edit_idx = None
if "new_role_mode" not in ss: ss.new_role_mode = False

# Cargar agentes / flujos / roles
if "agents_loaded" not in ss:
  ss.agents = load_agents(); ss.agents_loaded = True
if "workflows_loaded" not in ss:
  ss.workflows = load_workflows(); ss.workflows_loaded = True
if "roles" not in ss: ss.roles = load_roles()

# Puestos: cargar o sembrar
if "positions" not in ss:
  df_loaded = load_positions()
  if df_loaded.empty:
    df_loaded = pd.DataFrame([
      {"ID":"P-10645194","Puesto":"Desarrollador/a Backend (Python)","Ubicación":"Lima, Perú","Hiring Manager":"Rivers Brykson","Estado":"Abierto","Fecha Inicio": (date.today() - timedelta(days=3)).isoformat(),"Leads":1800,"Nuevos":115,"Recruiter Screen":35,"HM Screen":7,"Entrevista Telefónica":14,"Entrevista Presencial":15},
      {"ID":"P-10376415","Puesto":"VP de Marketing","Ubicación":"Santiago, Chile","Hiring Manager":"Angela Cruz","Estado":"Abierto","Fecha Inicio": (date.today() - timedelta(days=28)).isoformat(),"Leads":8100,"Nuevos":1,"Recruiter Screen":15,"HM Screen":35,"Entrevista Telefónica":5,"Entrevista Presencial":7},
      {"ID":"P-10376646","Puesto":"Planner de Demanda","Ubicación":"Ciudad de México, MX","Hiring Manager":"Rivers Brykson","Estado":"Abierto","Fecha Inicio": (date.today() - timedelta(days=28)).isoformat(),"Leads":2300,"Nuevos":26,"Recruiter Screen":3,"HM Screen":8,"Entrevista Telefónica":6,"Entrevista Presencial":3},
    ])
    save_positions(df_loaded)
  ss.positions = df_loaded

# Tareas: cargar de disco; si no hay, seed y guardar
if "tasks" not in ss:
  loaded_tasks = load_tasks()
  if not loaded_tasks:
    loaded_tasks = [
      {"id": str(uuid.uuid4()), "titulo":"Revisar CVs top 5", "desc":"Analizar a los 5 candidatos con mayor fit para 'Business Analytics'.", "due":str(date.today() + timedelta(days=2)), "assigned_to": "Headhunter", "status": "Pendiente", "created_at": (date.today() - timedelta(days=3)).isoformat(), "priority":"Alta"},
      {"id": str(uuid.uuid4()), "titulo":"Coordinar entrevista de Rivers Brykson", "desc":"Agendar la 2da entrevista (Gerencia) para el puesto de VP de Marketing.", "due":str(date.today() + timedelta(days=5)), "assigned_to": "Coordinador RR.HH.", "status": "En Proceso", "created_at": (date.today() - timedelta(days=8)).isoformat(), "priority":"Media"},
      {"id": str(uuid.uuid4()), "titulo":"Crear workflow de Onboarding", "desc":"Definir pasos en 'Flujos' para Contratado.", "due":str(date.today() - timedelta(days=1)), "assigned_to": "Admin RR.HH.", "status": "Completada", "created_at": (date.today() - timedelta(days=15)).isoformat(), "priority":"Baja"}
    ]
    save_tasks(loaded_tasks)
  ss.tasks = loaded_tasks
if "expanded_task_id" not in ss: ss.expanded_task_id = None
if "show_assign_for" not in ss: ss.show_assign_for = None

# Candidatos demo
if "candidates" not in ss:
  ss.candidates = []
if "candidate_init" not in ss:
  initial_candidates = [
    {"Name": "CV_AnaLopez.pdf", "Score": 85, "Role": "Business Analytics", "source": "LinkedIn Jobs"},
    {"Name": "CV_LuisGomez.pdf", "Score": 42, "Role": "Business Analytics", "source": "Computrabajo"},
    {"Name": "CV_MartaDiaz.pdf", "Score": 91, "Role": "Desarrollador/a Backend (Python)", "source": "Indeed"},
    {"Name": "CV_JaviRuiz.pdf", "Score": 30, "Role": "Diseñador/a UX", "source": "laborum.pe"},
  ]
  for i, c in enumerate(initial_candidates):
    c["id"] = f"C{i+1}-{random.randint(1000, 9999)}"
    c["stage"] = PIPELINE_STAGES[random.choice([0, 1, 1, 2, 6])]
    c["load_date"] = (date.today() - timedelta(days=random.randint(5, 30))).isoformat()
    c["_bytes"] = "Contenido de CV simulado".encode()
    c["_is_pdf"] = True
    c["_text"] = f"Simulación de CV. Experiencia 5 años. SQL, Power BI, Python, Excel. Candidato {c['Name']}."
    ss.candidates.append(c)
  ss.candidate_init = True

# =========================================================
# UTILS
# =========================================================
SKILL_SYNONYMS = {
  "Excel":["excel","xlsx"], "Gestión documental":["gestión documental","document control"], "Redacción":["redacción","writing"],
  "Facturación":["facturación","billing"], "Caja":["caja","cash"], "SQL":["sql","postgres","mysql"], "Power BI":["power bi"],
  "Tableau":["tableau"], "ETL":["etl"], "KPIs":["kpi","kpis"], "MS Project":["ms project"], "AutoCAD":["autocad"],
  "BIM":["bim","revit"], "Presupuestos":["presupuesto","presupuestos"], "Figma":["figma"], "UX Research":["ux research","investigación de usuarios"],
  "Prototipado":["prototipado","prototype"], "Python":["python"], "Agile":["agile","scrum","kanban"]
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

def pdf_viewer_embed(file_bytes: bytes, height=520):
  if not file_bytes:
    st.info("Sin adjuntos.")
    return
  try:
    b64=base64.b64encode(file_bytes).decode("utf-8")
    st.components.v1.html(
      f'<embed src="data:application/pdf;base64,{b64}" type="application/pdf" width="100%" height="{height}px"/>',
      height=height
    )
  except Exception:
    st.info("No se pudo previsualizar el PDF, pero puedes descargarlo.")

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
  except: pass
  st.markdown('<div class="login-sub">Acceso a SelektIA</div>', unsafe_allow_html=True)
  with st.form("login_form", clear_on_submit=False):
    u = st.text_input("Usuario"); p = st.text_input("Contraseña", type="password")
    ok = st.form_submit_button("Ingresar")
    if ok:
      if u in USERS and USERS[u]["password"] == p:
        st.session_state.auth = {"username":u, "role": USERS[u]["role"], "name": USERS[u]["name"]}
        st.success("Bienvenido."); st.rerun()
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
    if st.button("Analytics", key="sb_analytics"): ss.section = "analytics"; ss.pipeline_filter = None

    st.markdown("#### ASISTENTE IA")
    if st.button("Flujos", key="sb_flows"): ss.section = "flows"; ss.pipeline_filter = None
    if st.button("Agentes", key="sb_agents"): ss.section = "agents"; ss.pipeline_filter = None

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
                ss.section = "pipeline"; ss.pipeline_filter = target_stage
        elif txt == "Pipeline de Candidatos":
              if st.button(txt, key=f"sb_{sec}"): ss.section = sec; ss.pipeline_filter = None
        else:
            if st.button(txt, key=f"sb_{sec}"): ss.section = sec; ss.pipeline_filter = None

    st.markdown("#### TAREAS") 
    if st.button("Todas las tareas", key="sb_task_manual"): ss.section = "create_task"
    if st.button("Asignado a mi", key="sb_task_hh"): ss.section = "hh_tasks"
    if st.button("Asignado a mi equipo", key="sb_task_agente"): ss.section = "agent_tasks"

    st.markdown("#### ACCIONES")
    if st.button("Cerrar sesión", key="sb_logout"):
      ss.auth = None; st.rerun()

# =========================================================
# HELPER TAREAS (detalles + acciones)
# =========================================================
def _status_pill(s: str)->str:
  colors = {"Pendiente": "#9AA6B2","En Proceso": "#0072E3","Completada": "#10B981"}
  c = colors.get(s, "#9AA6B2")
  return f'<span class="badge" style="border-color:{c}33;background:{c}14;color:#0A2230">{s}</span>'

def _priority_pill(p: str)->str:
  colors = {"Alta":"#E11D48","Media":"#F59E0B","Baja":"#6B7280"}
  c = colors.get(p, "#6B7280")
  return f'<span class="badge" style="border-color:{c}33;background:{c}14;color:#0A2230">{p}</span>'

def task_detail_panel(task: dict):
  left, right = st.columns([0.45, 0.55])
  with left:
    st.markdown("#### Información")
    st.write(f"**Id**: {task.get('id','—')}")
    st.write(f"**Creation date**: {task.get('created_at','—')}")
    st.write(f"**Due date**: {task.get('due','—')}")
    st.write(f"**Priority**: {task.get('priority','Media')}")
    ext = task.get("external_eval") or task.get("score")
    if ext is not None: st.write(f"**External evaluation result**: {ext}%")
    st.markdown("#### Business Data"); st.caption(task.get("business_data","—"))
    st.markdown("#### Custom Data"); st.caption(task.get("custom_data","—"))
  with right:
    st.markdown("#### Curriculum / Adjuntos")
    pdf_bytes = task.get("pdf_bytes"); pdf_name = task.get("pdf_name","adjunto.pdf")
    if pdf_bytes:
      pdf_viewer_embed(pdf_bytes, height=520)
      st.download_button("Descargar PDF", data=pdf_bytes, file_name=pdf_name, use_container_width=True)
    else:
      st.info("Sin adjuntos.")

def save_tasks_and_refresh():
  save_tasks(ss.tasks)
  st.rerun()

def render_task_row(task: dict):
  t_id = task.get("id") or f"T-{int(datetime.now().timestamp())}"
  task["id"] = t_id
  task.setdefault("priority","Media")

  col1,col2,col3,col4,col5,col6 = st.columns([2.2,1.0,1.3,1.3,1.1,1.6])
  with col1:
    st.markdown(f"**{task.get('titulo','—')}**")
    st.caption(task.get("desc","—"))
  with col2:
    st.markdown(_status_pill(task.get("status","Pendiente")), unsafe_allow_html=True)
  with col3:
    st.markdown(f"**Vence:** {task.get('due','—')}")
  with col4:
    st.markdown(f"**Asignado a:** {task.get('assigned_to','—')}")
  with col5:
    st.markdown(_priority_pill(task.get("priority","Media")), unsafe_allow_html=True)

  with col6:
    accion = st.selectbox(
      "Acciones",
      ["Selecciona…","Ver detalle","Asignar tarea","Tomar tarea","Eliminar"],
      key=f"accion_{t_id}", label_visibility="collapsed"
    )

    if accion == "Ver detalle":
      ss.expanded_task_id = t_id; ss.show_assign_for = None

    elif accion == "Asignar tarea":
      ss.show_assign_for = t_id; ss.expanded_task_id = None

    elif accion == "Tomar tarea":
      current_user = (ss.auth["name"] if ss.get("auth") else "Admin")
      task["assigned_to"] = current_user; task["status"] = "En Proceso"
      ss.show_assign_for = None; ss.expanded_task_id = None
      save_tasks_and_refresh()

    elif accion == "Eliminar":
      ss.tasks = [t for t in ss.tasks if t.get("id") != t_id]
      ss.show_assign_for = None; ss.expanded_task_id = None
      save_tasks_and_refresh()

  # Asignación (Espera / Equipo / Usuario)
  if ss.show_assign_for == t_id:
    with st.container():
      c1,c2,c3 = st.columns([1.2,1.8,0.8])
      with c1:
        scope = st.selectbox("Destino", ["Espera","Equipo","Usuario"], key=f"assign_scope_{t_id}")
      with c2:
        if scope == "Usuario":
          user = st.selectbox("Usuario", ["Headhunter","Coordinador RR.HH.","Admin RR.HH.","Agente de Análisis","Colab","Sup","Admin"],
                              index=0, key=f"assign_user_{t_id}")
        else:
          user = None
      with c3:
        if st.button("Guardar", key=f"btn_assign_{t_id}", use_container_width=True):
          if scope == "Espera":
            task["assigned_to"] = "—"; task["status"] = "Pendiente"
          elif scope == "Equipo":
            task["assigned_to"] = "Coordinador RR.HH."; task["status"] = "Pendiente"
            ss.section = "agent_tasks"
          elif scope == "Usuario":
            task["assigned_to"] = user; task["status"] = "Pendiente"
          ss.show_assign_for = None
          save_tasks_and_refresh()

  if ss.expanded_task_id == t_id:
    with st.container():
      st.markdown('<div class="k-card" style="margin-top:8px;">', unsafe_allow_html=True)
      task_detail_panel(task)
      st.markdown('</div>', unsafe_allow_html=True)

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
      text = ""
      try:  # extraer texto en función del tipo
        suffix = Path(f.name).suffix.lower()
        if suffix == ".pdf":
          pdf_reader = PdfReader(io.BytesIO(b)); text="".join([(p.extract_text() or "") for p in pdf_reader.pages])
        elif suffix == ".docx":
          with zipfile.ZipFile(io.BytesIO(b)) as z:
            xml = z.read("word/document.xml").decode("utf-8", "ignore")
            text = re.sub(r"<.*?>", " ", xml); text = re.sub(r"\s+", " ", text).strip()
        else:
          text = b.decode("utf-8", errors="ignore")
      except Exception:
        text = ""

      must_list = [s.strip() for s in (preset.get("must",[]) or []) if s.strip()]
      nice_list = [s.strip() for s in (preset.get("nice",[]) or []) if s.strip()]
      score, exp = score_fit_by_skills(jd_text, must_list, nice_list, text)
      c = {"id": f"C{len(ss.candidates)+len(new_candidates)+1}-{int(datetime.now().timestamp())}", 
            "Name": f.name, "Score": score, "Role": puesto, "Role_ID": id_puesto,
            "_bytes": b, "_is_pdf": Path(f.name).suffix.lower()==".pdf", "_text": text,
            "stage": PIPELINE_STAGES[0], "load_date": date.today().isoformat(), "_exp": exp, "source": "Carga Manual"}
      new_candidates.append(c)
    for c in new_candidates:
        if c["Score"] < 35: c["stage"] = "Descartado"
        ss.candidates.append(c)
    st.success(f"CVs cargados, analizados y {len(new_candidates)} enviados al Pipeline.")
    st.rerun()

def _auto_pos_id(): return f"P-{random.randint(10_000_000, 99_999_999)}"
def _calc_dias_abierto(fecha_iso: str, estado: str) -> int:
  try: fi = datetime.fromisoformat(fecha_iso).date()
  except: return 0
  return max(0, (date.today() - fi).days) if estado=="Abierto" else 0

def page_puestos():
  st.header("Puestos")
  # Filtros
  colf1, colf2, colf3 = st.columns([0.5, 0.3, 0.2])
  with colf1: q = st.text_input("Buscar (puesto, manager, ubicación)", value="")
  with colf2: est = st.selectbox("Estado", ["Todos","Abierto","Cerrado"], index=0)
  with colf3:
    if st.button("🔄 Refrescar"): st.rerun()
  df = ss.positions.copy()
  for c in ["Leads","Nuevos","Recruiter Screen","HM Screen","Entrevista Telefónica","Entrevista Presencial"]:
    if c not in df.columns: df[c] = 0
  if q.strip():
    ql=q.lower()
    mask=(df["Puesto"].str.lower().str.contains(ql,na=False)|df["Ubicación"].str.lower().str.contains(ql,na=False)|
          df["Hiring Manager"].str.lower().str.contains(ql,na=False)|df["ID"].str.lower().str.contains(ql,na=False))
    df=df[mask]
  if est!="Todos": df=df[df["Estado"]==est]
  df["Días Abierto"] = df.apply(lambda r: _calc_dias_abierto(r.get("Fecha Inicio",""), r.get("Estado","Abierto")), axis=1)
  df["Time to Hire (promedio)"] = df["Días Abierto"].apply(lambda d: f"{max(d,1)+18} días")

  # Crear
  with st.expander("➕ Crear nuevo puesto", expanded=False):
    with st.form("new_pos_form"):
      c1,c2,c3 = st.columns(3)
      with c1: new_id = st.text_input("ID", value=_auto_pos_id()); new_title = st.text_input("Puesto*")
      with c2: new_loc = st.text_input("Ubicación*", value="Lima, Perú"); new_hm  = st.text_input("Hiring Manager*", value="Nombre y Apellido")
      with c3: new_state = st.selectbox("Estado*", ["Abierto","Cerrado"], index=0); new_start = st.date_input("Fecha Inicio*", value=date.today())
      c4,c5,c6,c7,c8 = st.columns(5)
      with c4: leads = st.number_input("Leads", 0, 1_000_000, 0, step=10)
      with c5: nuevos = st.number_input("Nuevos", 0, 1_000_000, 0, step=1)
      with c6: rs = st.number_input("Recruiter Screen", 0, 1_000_000, 0, step=1)
      with c7: hms = st.number_input("HM Screen", 0, 1_000_000, 0, step=1)
      with c8: et = st.number_input("Entrevista Telefónica", 0, 1_000_000, 0, step=1)
      ep = st.number_input("Entrevista Presencial", 0, 1_000_000, 0, step=1, key="new_ep")
      if st.form_submit_button("Guardar puesto"):
        if not new_title.strip(): st.error("Debes completar el campo **Puesto**.")
        else:
          row={"ID": new_id.strip() or _auto_pos_id(),"Puesto": new_title.strip(),"Ubicación": new_loc.strip(),
               "Hiring Manager": new_hm.strip(),"Estado": new_state,"Fecha Inicio": new_start.isoformat(),
               "Leads": int(leads),"Nuevos": int(nuevos),"Recruiter Screen": int(rs),"HM Screen": int(hms),
               "Entrevista Telefónica": int(et),"Entrevista Presencial": int(ep)}
          ss.positions = pd.concat([ss.positions, pd.DataFrame([row])], ignore_index=True); save_positions(ss.positions)
          st.success("Puesto creado."); st.rerun()

  st.markdown("---"); st.subheader("Listado de puestos")
  df_display = df[["Puesto","Días Abierto","Time to Hire (promedio)","Leads","Ubicación","Hiring Manager","Estado","ID","Fecha Inicio","Nuevos","Recruiter Screen","HM Screen","Entrevista Telefónica","Entrevista Presencial"]]
  st.markdown("""
  <table style="width:100%; border-spacing:0 8px;">
    <thead>
      <tr style="text-align:left; color:#1B2A3C;">
        <th style="width:26%;">Puesto</th><th style="width:10%;">Días</th><th style="width:12%;">Time to Hire</th>
        <th style="width:10%;">Leads</th><th style="width:10%;">Ubicación</th><th style="width:12%;">Hiring Manager</th>
        <th style="width:8%;">Estado</th><th style="width:12%;">Acciones</th>
      </tr>
    </thead>
  </table>
  """, unsafe_allow_html=True)

  for _, row in df_display.sort_values(["Estado","Días Abierto","Leads"], ascending=[True,True,False]).iterrows():
    rid=row["ID"]; st.markdown('<div class="k-card">', unsafe_allow_html=True)
    c1,c2,c3,c4,c5,c6,c7,c8 = st.columns([0.26,0.10,0.12,0.10,0.10,0.12,0.08,0.12])
    with c1: st.markdown(f"**{row['Puesto']}**  \n<span style='opacity:.7;font-size:12px'>ID: {rid}</span>", unsafe_allow_html=True)
    with c2: st.write(row["Días Abierto"])
    with c3: st.write(row["Time to Hire (promedio)"])
    with c4: st.write(int(row["Leads"]))
    with c5: st.write(row["Ubicación"])
    with c6: st.write(row["Hiring Manager"])
    with c7: st.write(row["Estado"])
    with c8:
      act = st.selectbox("Acción", ["Selecciona…","Editar","Duplicar","Abrir/Cerrar","Eliminar"], key=f"pos_act_{rid}", label_visibility="collapsed")
      if act == "Duplicar":
        new_row = dict(row); new_row["ID"] = _auto_pos_id()
        ss.positions = pd.concat([ss.positions, pd.DataFrame([new_row])], ignore_index=True); save_positions(ss.positions)
        st.success("Puesto duplicado."); st.rerun()
      elif act == "Abrir/Cerrar":
        i_real = ss.positions.index[ss.positions["ID"]==rid][0]
        ss.positions.at[i_real,"Estado"]="Cerrado" if ss.positions.at[i_real,"Estado"]=="Abierto" else "Abierto"
        save_positions(ss.positions); st.success("Estado actualizado."); st.rerun()
      elif act == "Eliminar":
        ss.positions = ss.positions[ss.positions["ID"] != rid].reset_index(drop=True); save_positions(ss.positions)
        st.warning("Puesto eliminado."); st.rerun()
      elif act == "Editar":
        with st.expander(f"Editar: {row['Puesto']}"):
          with st.form(f"edit_pos_{rid}"):
            e1,e2,e3 = st.columns(3)
            with e1: eid = st.text_input("ID", value=row["ID"]); etitle = st.text_input("Puesto*", value=row["Puesto"])
            with e2: eloc = st.text_input("Ubicación*", value=row["Ubicación"]); ehm  = st.text_input("Hiring Manager*", value=row["Hiring Manager"])
            with e3:
              estate = st.selectbox("Estado*", ["Abierto","Cerrado"], index=0 if row["Estado"]=="Abierto" else 1)
              estart = st.date_input("Fecha Inicio*", value=datetime.fromisoformat(row["Fecha Inicio"]).date() if row["Fecha Inicio"] else date.today())
            m1,m2,m3,m4,m5,m6 = st.columns(6)
            with m1: eleads = st.number_input("Leads", 0, 1_000_000, int(row["Leads"]), step=10, key=f"eleads_{rid}")
            with m2: enuevos = st.number_input("Nuevos", 0, 1_000_000, int(row["Nuevos"]), step=1, key=f"enew_{rid}")
            with m3: ers = st.number_input("Recruiter Screen", 0, 1_000_000, int(row["Recruiter Screen"]), step=1, key=f"ers_{rid}")
            with m4: ehms = st.number_input("HM Screen", 0, 1_000_000, int(row["HM Screen"]), step=1, key=f"ehms_{rid}")
            with m5: eet = st.number_input("Entrevista Telefónica", 0, 1_000_000, int(row["Entrevista Telefónica"]), step=1, key=f"eet_{rid}")
            with m6: eep = st.number_input("Entrevista Presencial", 0, 1_000_000, int(row["Entrevista Presencial"]), step=1, key=f"eep_{rid}")
            if st.form_submit_button("Guardar cambios"):
              i_real = ss.positions.index[ss.positions["ID"]==rid][0]
              ss.positions.at[i_real,"ID"]=eid.strip() or row["ID"]
              ss.positions.at[i_real,"Puesto"]=etitle.strip()
              ss.positions.at[i_real,"Ubicación"]=eloc.strip()
              ss.positions.at[i_real,"Hiring Manager"]=ehm.strip()
              ss.positions.at[i_real,"Estado"]=estate
              ss.positions.at[i_real,"Fecha Inicio"]=estart.isoformat()
              ss.positions.at[i_real,"Leads"]=int(eleads); ss.positions.at[i_real,"Nuevos"]=int(enuevos)
              ss.positions.at[i_real,"Recruiter Screen"]=int(ers); ss.positions.at[i_real,"HM Screen"]=int(ehms)
              ss.positions.at[i_real,"Entrevista Telefónica"]=int(eet); ss.positions.at[i_real,"Entrevista Presencial"]=int(eep)
              save_positions(ss.positions); st.success("Puesto actualizado."); st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

  st.markdown("---"); st.subheader("Candidatos por Puesto")
  pos_list = ss.positions["Puesto"].tolist()
  if pos_list:
    selected_pos = st.selectbox("Selecciona un puesto para ver candidatos del Pipeline", pos_list)
    candidates_for_pos = [c for c in ss.candidates if c.get("Role") == selected_pos]
    if candidates_for_pos:
      df_cand = pd.DataFrame(candidates_for_pos)
      st.dataframe(df_cand[["Name", "Score", "stage", "load_date"]].rename(columns={"Name":"Candidato", "Score":"Fit", "stage":"Fase"}), use_container_width=True, hide_index=True)
    else:
      st.info(f"No hay candidatos activos para **{selected_pos}**.")
  else:
    st.info("No hay puestos.")

# --------------------- EVALUACIÓN ---------------------
def page_eval():
  st.header("Resultados de evaluación")
  if not ss.candidates:
    st.info("Carga CVs en **Publicación & Sourcing**."); return 
  jd_text = st.text_area("JD para matching por skills (opcional)", ss.get("last_jd_text",""), height=140)
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
    enriched.append({"id": c["id"],"Name": c["Name"],"Fit": fit,
                     "Must (ok/total)":f"{len(exp['matched_must'])}/{exp['must_total']}",
                     "Nice (ok/total)":f"{len(exp['matched_nice'])}/{exp['nice_total']}",
                     "Extras":", ".join(exp["extras"])[:60]})
  df = pd.DataFrame(enriched).sort_values("Fit", ascending=False).reset_index(drop=True)
  st.subheader("Ranking por Fit de Skills")
  st.dataframe(df[["Name","Fit","Must (ok/total)","Nice (ok/total)","Extras"]], use_container_width=True, height=250)

  st.subheader("Detalle y explicación")
  if not df.empty:
    selected_name = st.selectbox("Elige un candidato", df["Name"].tolist())
    selected_id = df[df["Name"] == selected_name]["id"].iloc[0]
    candidate_obj = next((c for c in ss.candidates if c["id"] == selected_id), None)
    if candidate_obj:
      fit = candidate_obj["Score"]; exp = candidate_obj["_exp"]
      cv_bytes = candidate_obj.get("_bytes", b""); cv_text = candidate_obj.get("_text", ""); is_pdf = candidate_obj.get("_is_pdf", False)
      c1,c2=st.columns([1.1,0.9])
      with c1:
        fig=px.bar(pd.DataFrame([{"Candidato":selected_name,"Fit":fit}]), x="Candidato", y="Fit", title="Fit por skills", color_discrete_sequence=[PRIMARY])
        fig.update_traces(hovertemplate="%{x}<br>Fit: %{y}%")
        fig.update_layout(plot_bgcolor="#FFFFFF", paper_bgcolor="rgba(0,0,0,0)",font=dict(color=TITLE_DARK),xaxis_title=None,yaxis_title="Fit")
        st.plotly_chart(fig, use_container_width=True)
        st.markdown("**Explicación**")
        st.markdown(f"- **Must-have:** {len(exp['matched_must'])}/{exp['must_total']}")
        if exp["matched_must"]: st.markdown(" - ✓ " + ", ".join(exp["matched_must"]))
        if exp["gaps_must"]: st.markdown(" - ✗ Faltantes: " + ", ".join(exp["gaps_must"]))
        st.markdown(f"- **Nice-to-have:** {len(exp['matched_nice'])}/{exp['nice_total']}")
        if exp["matched_nice"]: st.markdown(" - ✓ " + ", ".join(exp["matched_nice"]))
        if exp["gaps_nice"]: st.markdown(" - ✗ Faltantes: " + ", ".join(exp["gaps_nice"]))
        if exp["extras"]: st.markdown("- **Extras:** " + ", ".join(exp["extras"]))
      with c2:
        st.markdown("**CV (visor)**")
        if is_pdf and cv_bytes: pdf_viewer_embed(cv_bytes, height=420)
        else: st.text_area("Contenido (TXT)", cv_text, height=260)
    else:
      st.error("No se encontraron los detalles del candidato en la sesión.")
  else:
    st.info("No hay candidatos para mostrar detalles.")

def page_pipeline():
  filter_stage = ss.get("pipeline_filter")
  if filter_stage:
    st.header(f"Pipeline: Candidatos en Fase '{filter_stage}'")
    candidates_to_show = [c for c in ss.candidates if c.get("stage") == filter_stage]
  else:
    st.header("Pipeline de Candidatos (Vista Kanban)")
    candidates_to_show = ss.candidates
  st.caption("Arrastra los candidatos a través de las etapas para avanzar el proceso.")
  if not candidates_to_show and filter_stage:
    st.info(f"No hay candidatos en la fase **{filter_stage}**."); return
  elif not ss.candidates:
    st.info("No hay candidatos activos. Carga CVs en **Publicación & Sourcing**."); return

  candidates_by_stage = {stage: [] for stage in PIPELINE_STAGES}
  for c in candidates_to_show: candidates_by_stage[c["stage"]].append(c)
  cols = st.columns(len(PIPELINE_STAGES))
  for i, stage in enumerate(PIPELINE_STAGES):
    with cols[i]:
      st.markdown(f"**{stage} ({len(candidates_by_stage[stage])})**", unsafe_allow_html=True)
      st.markdown("---")
      for c in candidates_by_stage[stage]:
        card_name = c["Name"].split('_')[-1].replace('.pdf', '').replace('.txt', '')
        st.markdown(f"""
        <div class="k-card" style="margin-bottom: 10px; border-left: 4px solid {PRIMARY if c['Score'] >= 70 else ('#FFA500' if c['Score'] >= 40 else '#D60000')}">
          <div style="font-weight:700; color:{TITLE_DARK};">{card_name}</div>
          <div style="font-size:12px; opacity:.8;">{c.get("Role", "Puesto Desconocido")}</div>
          <div style="font-size:14px; font-weight:700; margin-top:8px;">Fit: <span style="color:{PRIMARY};">{c["Score"]}%</span></div>
          <div style="font-size:10px; opacity:.6; margin-top:4px;">Fuente: {c.get("source", "N/A")}</div>
        </div>""", unsafe_allow_html=True)
        with st.form(key=f"form_move_{c['id']}", clear_on_submit=False):
          current_stage_index = PIPELINE_STAGES.index(stage)
          available_stages = [s for s in PIPELINE_STAGES if s != stage]
          try:
            default_index = available_stages.index(PIPELINE_STAGES[min(current_stage_index + 1, len(PIPELINE_STAGES) - 1)])
          except ValueError:
            default_index = 0
          new_stage = st.selectbox("Mover a:", available_stages, key=f"select_move_{c['id']}", index=default_index, label_visibility="collapsed")
          if st.form_submit_button("Mover Candidato"):
            c["stage"] = new_stage
            if new_stage == "Descartado":
              st.success(f"📧 Email de rechazo automático enviado a {card_name}.")
            elif new_stage == "Entrevista Telefónica":
              st.info(f"📅 Tarea de programación de entrevista generada para {card_name}.")
              # crear tarea desde flujo + persistir
              t = {
                "id": f"T-{int(datetime.now().timestamp())}",
                "titulo": f"Flujo: Programar entrevista - {card_name}",
                "desc": "Coordinar entrevista telefónica con el candidato.",
                "due": (date.today()+timedelta(days=2)).isoformat(),
                "assigned_to": "Headhunter",
                "status": "Pendiente",
                "priority": "Alta" if c.get("Score",0) >= 70 else "Media",
                "created_at": date.today().isoformat(),
                "pdf_bytes": (c.get("_bytes") if c.get("_is_pdf") else None),
                "pdf_name": c.get("Name","CV.pdf"),
                "score": c.get("Score")
              }
              ss.tasks.insert(0, t); save_tasks(ss.tasks)
            elif new_stage == "Contratado":
              st.balloons(); st.success(f"🎉 ¡Éxito! Flujo de Onboarding disparado para {card_name}.")
            if filter_stage and new_stage != filter_stage:
              ss.pipeline_filter = None; st.info("Se quitó el filtro al mover al candidato.")
            st.rerun()

def page_interview():
  st.header("Entrevista (Gerencia)")
  st.write("Esta página redirige al **Pipeline** con el filtro **Entrevista Gerencia**.")
  ss.section = "pipeline"; ss.pipeline_filter = "Entrevista Gerencia"; st.rerun()

def page_offer():
  st.header("Oferta")
  st.write("Esta página redirige al **Pipeline** con el filtro **Oferta**.")
  ss.section = "pipeline"; ss.pipeline_filter = "Oferta"; st.rerun()

def page_onboarding():
  st.header("Onboarding")
  st.write("Esta página redirige al **Pipeline** con el filtro **Contratado**.")
  ss.section = "pipeline"; ss.pipeline_filter = "Contratado"; st.rerun()

def page_hh_tasks():
  st.header("Tareas Asignadas a Mí")
  if not ss.tasks: st.info("No tienes tareas asignadas."); return
  df_tasks = pd.DataFrame(ss.tasks)
  my_name = ss.auth["name"] if ss.get("auth") else "Colab"
  my_tasks = df_tasks[df_tasks["assigned_to"].isin(["Headhunter", "Colaborador", my_name])]
  all_statuses = ["Todos"] + sorted(my_tasks["status"].unique())
  selected_status = st.selectbox("Filtrar por Estado", all_statuses, index=all_statuses.index("Pendiente") if "Pendiente" in all_statuses else 0)
  my_tasks_filtered = my_tasks if selected_status=="Todos" else my_tasks[my_tasks["status"] == selected_status]
  if not my_tasks_filtered.empty:
    st.dataframe(
      my_tasks_filtered.rename(columns={"titulo":"Título", "desc":"Descripción", "due":"Vencimiento", "assigned_to": "Asignado a", "status": "Estado", "created_at": "Fecha de Creación"})
      [["Título","Descripción","Estado","Vencimiento","Fecha de Creación"]],
      use_container_width=True, hide_index=True
    )
  else:
    st.info(f"No hay tareas en el estado '{selected_status}'.")

def page_agent_tasks():
  st.header("Tareas Asignadas a mi Equipo")
  if not ss.tasks: st.write("No hay tareas pendientes en el equipo."); return
  df_tasks = pd.DataFrame(ss.tasks)
  team_tasks = df_tasks[df_tasks["assigned_to"].isin(["Coordinador RR.HH.", "Admin RR.HH.", "Agente de Análisis"])]
  all_statuses = ["Todos"] + sorted(team_tasks["status"].unique())
  selected_status = st.selectbox("Filtrar por Estado", all_statuses, index=all_statuses.index("Pendiente") if "Pendiente" in all_statuses else 0, key="agent_task_filter")
  team_tasks_filtered = team_tasks if selected_status=="Todos" else team_tasks[team_tasks["status"] == selected_status]
  if not team_tasks_filtered.empty:
    st.dataframe(
      team_tasks_filtered.rename(columns={"titulo":"Título", "desc":"Descripción", "due":"Vencimiento", "assigned_to": "Asignado a", "status": "Estado", "created_at": "Fecha de Creación"})
      [["Título","Descripción","Asignado a","Estado","Vencimiento","Fecha de Creación"]],
      use_container_width=True, hide_index=True
    )
  else:
    st.info(f"No hay tareas en el estado '{selected_status}' asignadas al equipo.")

# ===================== FLUJOS =====================
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
        img_src    = st.text_input("URL de imagen (opcional)", value=AGENT_DEFAULT_IMAGES.get("Headhunter",""))
        perms      = st.multiselect("Permisos (quién puede editar)", ["Colaborador","Supervisor","Administrador"], default=["Supervisor","Administrador"])
      saved = st.form_submit_button("Guardar/Actualizar Agente")
      if saved:
        rn = (role_name or "").strip()
        if not rn: st.error("El campo Rol* es obligatorio.")
        else:
          ss.agents.append({"rol": rn, "objetivo": objetivo, "backstory": backstory,"guardrails": guardrails,"herramientas": herramientas,
                            "llm_model": llm_model, "image": img_src, "perms": perms,"ts": datetime.utcnow().isoformat()})
          save_agents(ss.agents); roles_new = sorted(list({*ss.roles, rn})); ss.roles = roles_new; save_roles(roles_new)
          st.success("Agente creado."); ss.new_role_mode = False; st.rerun()

  st.subheader("Tus agentes")
  if not ss.agents:
    st.info("Aún no hay agentes. Crea el primero con **➕ Nuevo**."); return
  cols_per_row = 5
  for i in range(0, len(ss.agents), cols_per_row):
    row_agents = ss.agents[i:i+cols_per_row]; cols = st.columns(cols_per_row)
    for j, ag in enumerate(row_agents):
      idx = i + j
      with cols[j]:
        img = ag.get("image") or AGENT_DEFAULT_IMAGES.get(ag.get("rol","Headhunter"))
        st.markdown(f"""<div class="agent-card"><img src="{img}"><div class="agent-title">{ag.get('rol','—')}</div>
                        <div class="agent-sub">{ag.get('objetivo','—')}</div></div>""", unsafe_allow_html=True)
        st.markdown('<div class="toolbar">', unsafe_allow_html=True)
        c1, c2, c3, c4 = st.columns(4)
        with c1:
          if st.button("👁", key=f"ag_v_{idx}", help="Ver"):
            ss.agent_view_idx = (None if ss.agent_view_idx == idx else idx); ss.agent_edit_idx = None; st.rerun()
        with c2:
          if st.button("✏", key=f"ag_e_{idx}", help="Editar"):
            ss.agent_edit_idx = (None if ss.agent_edit_idx == idx else idx); ss.agent_view_idx = None; st.rerun()
        with c3:
          if st.button("🧬", key=f"ag_c_{idx}", help="Clonar"):
            clone = dict(ag); clone["rol"] = f"{ag.get('rol','Agente')} (copia)"; ss.agents.append(clone); save_agents(ss.agents); st.success("Agente clonado."); st.rerun()
        with c4:
          if st.button("🗑", key=f"ag_d_{idx}", help="Eliminar"):
            ss.agents.pop(idx); save_agents(ss.agents); st.success("Agente eliminado."); st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

  if ss.agent_view_idx is not None and 0 <= ss.agent_view_idx < len(ss.agents):
    ag = ss.agents[ss.agent_view_idx]
    st.markdown("### Detalle del agente")
    st.markdown('<div class="agent-detail">', unsafe_allow_html=True)
    c1, c2 = st.columns([0.42, 0.58])
    with c1:
      safe_img = (ag.get("image") or AGENT_DEFAULT_IMAGES.get(ag.get("rol","Headhunter")))
      st.markdown(f"""<div style="text-align:center;margin:6px 0 12px">
                         <img src="{safe_img}" style="width:180px;height:180px;border-radius:999px;object-fit:cover;border:4px solid #F1F7FD;">
                       </div>""", unsafe_allow_html=True)
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
      objetivo  = st.text_input("Objetivo*", value=ag.get("objetivo",""))
      backstory = st.text_area("Backstory*", value=ag.get("backstory",""), height=120)
      guardrails= st.text_area("Guardrails", value=ag.get("guardrails",""), height=90)
      herramientas = st.multiselect("Herramientas habilitadas", ["Parser de PDF","Recomendador de skills","Comparador JD-CV"], default=ag.get("herramientas",["Parser de PDF","Recomendador de skills"]))
      llm_model   = st.selectbox("Modelo LLM", LLM_MODELS, index=max(0, LLM_MODELS.index(ag.get("llm_model","gpt-4o-mini"))))
      img_src     = st.text_input("URL de imagen", value=ag.get("image",""))
      perms       = st.multiselect("Permisos (quién puede editar)", ["Colaborador","Supervisor","Administrador"], default=ag.get("perms",["Supervisor","Administrador"]))
      if st.form_submit_button("Guardar cambios"):
        ag.update({"objetivo":objetivo,"backstory":backstory,"guardrails":guardrails,"herramientas":herramientas,"llm_model":llm_model,"image":img_src,"perms":perms})
        save_agents(ss.agents); st.success("Agente actualizado."); st.rerun()

def page_flows():
  st.header("Flujos")
  vista_como = ss.auth["role"]; puede_aprobar = vista_como in ("Supervisor","Administrador")
  left, right = st.columns([0.9, 1.1])
  with left:
    st.subheader("Mis flujos")
    if not ss.workflows: st.info("No hay flujos aún. Crea uno a la derecha.")
    else:
      rows=[]
      for wf in ss.workflows:
        ag_label="—"; ai=wf.get("agent_idx",-1)
        if 0 <= ai < len(ss.agents): ag_label = ss.agents[ai].get("rol","Agente")
        rows.append({"ID": wf["id"], "Nombre": wf["name"], "Puesto": wf.get("role","—"),"Agente": ag_label,"Estado": wf.get("status","Borrador"),"Programado": wf.get("schedule_at","—")})
      df=pd.DataFrame(rows); st.dataframe(df, use_container_width=True, height=260)
      if rows:
        sel = st.selectbox("Selecciona un flujo", [r["ID"] for r in rows], format_func=lambda x: next((r["Nombre"] for r in rows if r["ID"]==x), x))
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
              ss.workflows = [w for w in ss.workflows if w["id"]!=wf["id"]]; save_workflows(ss.workflows); st.success("Flujo eliminado."); st.rerun()
          with c3:
            st.markdown(f"<div class='badge'>Estado: <b>{wf.get('status','Borrador')}</b></div>", unsafe_allow_html=True)
            if wf.get("status")=="Pendiente de aprobación" and puede_aprobar:
              a1,a2 = st.columns(2)
              with a1:
                if st.button("✅ Aprobar"):
                  wf["status"]="Aprobado"; wf["approved_by"]=vista_como; wf["approved_at"]=datetime.now().isoformat()
                  save_workflows(ss.workflows); st.success("Aprobado.")
                  # tarea de seguimiento
                  ss.tasks.insert(0, {"id": f"T-{int(datetime.now().timestamp())}","titulo": f"{wf['name']} (aprobado)","desc": "Ejecutar flujo aprobado.","due": (date.today()+timedelta(days=2)).isoformat(),"assigned_to": "Coordinador RR.HH.","status": "Pendiente","priority":"Media","created_at":date.today().isoformat()})
                  save_tasks(ss.tasks); st.rerun()
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
      jd_text = st.text_area("JD en texto", value=ROLE_PRESETS[role]["jd"], height=140)
      agent_idx = -1
      if ss.agents:
        agent_opts = [f"{i} — {a.get('rol','Agente')} ({a.get('llm_model','model')})" for i,a in enumerate(ss.agents)]
        agent_pick = st.selectbox("Asigna un agente", agent_opts, index=0)
        agent_idx = int(agent_pick.split(" — ")[0])
      st.markdown("---")
      run_date = st.date_input("Fecha de ejecución", value=date.today()+timedelta(days=1))
      run_time = st.time_input("Hora de ejecución", value=datetime.now().time().replace(second=0, microsecond=0))
      col_a, col_b, col_c = st.columns(3)
      save_draft    = col_a.form_submit_button("💾 Guardar borrador")
      send_approval = col_b.form_submit_button("📝 Enviar a aprobación")
      schedule      = col_c.form_submit_button("📅 Guardar y Programar")
      if save_draft or send_approval or schedule:
        if not jd_text.strip(): st.error("Debes proporcionar un JD.")
        elif agent_idx < 0: st.error("Debes asignar un agente.")
        else:
          wf = {"id": f"WF-{int(datetime.now().timestamp())}","name": name,"role": role,"description": desc,"expected_output": expected,
                "jd_text": jd_text[:200000],"agent_idx": agent_idx,"created_at": datetime.now().isoformat(),
                "status": "Borrador","approved_by": "","approved_at": "","schedule_at": ""}
          if send_approval:
            wf["status"] = "Pendiente de aprobación"; st.success("Flujo enviado a aprobación.")
            ss.tasks.insert(0, {"id": f"T-{int(datetime.now().timestamp())}","titulo": f"{name} (aprobación)","desc":"Dar seguimiento a aprobación del flujo.","due": (date.today()+timedelta(days=2)).isoformat(),"assigned_to":"Admin RR.HH.","status":"Pendiente","priority":"Media","created_at":date.today().isoformat()})
            save_tasks(ss.tasks)
          if schedule:
            wf["schedule_at"]=f"{run_date} {run_time.strftime('%H:%M')}"
            if puede_aprobar:
              wf["status"]="Programado"; st.success("Flujo programado.")
              ss.tasks.insert(0, {"id": f"T-{int(datetime.now().timestamp())}","titulo": f"{name} (programado)","desc": f"Ejecutar flujo el {run_date} a las {run_time.strftime('%H:%M')}.","due": str(run_date),"assigned_to":"Coordinador RR.HH.","status":"Pendiente","priority":"Media","created_at":date.today().isoformat()})
              save_tasks(ss.tasks)
            else:
              wf["status"]="Pendiente de aprobación"; st.info("Pendiente de aprobación.")
          if save_draft:
            st.success("Borrador guardado.")
          ss.workflows.insert(0, wf); save_workflows(ss.workflows); st.rerun()

# ===================== ANALYTICS =====================
def page_analytics():
  st.header("Analytics y KPIs Estratégicos")
  if not ss.candidates:
    total_cvs = 0; avg_fit = 0; time_to_hire = "—"; source_counts = {}
  else:
    jd = ss.get("last_jd_text",""); preset = ROLE_PRESETS.get(ss.get("last_role",""), {})
    must, nice = preset.get("must", []), preset.get("nice", [])
    fits = []
    for c in ss.candidates:
      txt=c.get("_text") or (c.get("_bytes") or b"").decode("utf-8","ignore")
      f,_=score_fit_by_skills(jd,must,nice,txt or ""); fits.append(f)
    avg_fit = round(sum(fits)/len(fits),1) if fits else 0
    time_to_hire = "—"; source_counts = {}
    for c in ss.candidates: source_counts[c.get("source","Carga Manual")] = source_counts.get(c.get("source","Carga Manual"),0)+1
    total_cvs=len(ss.candidates)
  total_puestos = len(ss.positions)
  c1,c2,c3,c4 = st.columns(4)
  c1.metric("Puestos activos", total_puestos)
  c2.metric("CVs en Pipeline", total_cvs)
  c3.metric("Fit promedio (skills)", f"{avg_fit}%")
  c4.metric("Tiempo a Contratar", time_to_hire, delta="12% mejor vs. benchmark")

def page_create_task():
  st.header("Todas las Tareas")
  st.info("Muestra todas las tareas pendientes creadas en el sistema, incluyendo las asignadas manualmente y por flujos.")
  if not ss.tasks:
    st.write("No hay tareas registradas en el sistema."); return
  df_tasks = pd.DataFrame(ss.tasks)
  all_statuses = ["Todos"] + sorted(df_tasks["status"].unique())
  selected_status = st.selectbox("Estado", all_statuses, index=0)
  tasks_to_show = df_tasks if selected_status=="Todos" else df_tasks[df_tasks["status"] == selected_status]
  st.markdown("""
  <table style="width:100%; border-spacing:0 8px;">
    <thead>
      <tr style="text-align:left; color:#1B2A3C;">
        <th style="width:18%;">ID</th><th style="width:32%;">Título</th><th style="width:15%;">Asignado a</th>
        <th style="width:15%;">Vencimiento</th><th style="width:10%;">Prioridad</th><th style="width:10%;">Acciones</th>
      </tr>
    </thead>
  </table>
  """, unsafe_allow_html=True)
  for _, row in tasks_to_show.iterrows():
    task = dict(row); st.markdown('<div class="k-card">', unsafe_allow_html=True); render_task_row(task); st.markdown('</div>', unsafe_allow_html=True)

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
