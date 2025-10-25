# app.py
# -*- coding: utf-8 -*-

import io, base64, re, json, random, zipfile
from pathlib import Path
from datetime import datetime, date, timedelta

import streamlit as st
import pandas as pd
import plotly.express as px
from PyPDF2 import PdfReader

# =========================================================
# PALETA / CONST
# =========================================================
PRIMARY    = "#00CD78"
SIDEBAR_BG = "#0E192B"     # fondo panel izquierdo
SIDEBAR_TX = "#B9C7DF"     # texto gris azulado
BODY_BG    = "#F7FBFF"
CARD_BG    = "#0E192B"     # mismo color que sidebar
TITLE_DARK = "#142433"

BAR_DEFAULT = "#E9F3FF"
BAR_GOOD    = "#33FFAC"

JOB_BOARDS  = ["laborum.pe","Computrabajo","Bumeran","Indeed","LinkedIn Jobs"]

EVAL_INSTRUCTION = (
  "Debes analizar los CVs de postulantes y calificarlos de 0% a 100% según el nivel de coincidencia con el JD. "
  "Incluye un análisis breve que explique por qué califica o no el postulante, destacando habilidades must-have, "
  "nice-to-have, brechas y hallazgos relevantes."
)

# ===== Login simulado (usuarios de demo) =====
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

# ===== Presets de puestos (precargados) =====
ROLE_PRESETS = {
  "Asistente Administrativo": {
    "jd": "Brindar soporte administrativo: gestión documental, agenda, compras menores, logística de reuniones y reportes para las áreas internas. Atención a proveedores y coordinación de requerimientos; manejo de caja chica y apoyo en facturación básica. Se valora comunicación clara, orden y manejo de prioridades.",
    "keywords": "Excel, Word, PowerPoint, gestión documental, atención a proveedores, compras, logística, caja chica, facturación, redacción",
    "must": ["Excel","Gestión documental","Redacción"], "nice": ["Facturación","Caja"],
    "synth_skills": ["Excel","Word","PowerPoint","Gestión documental","Redacción","Facturación","Caja","Atención al cliente"]
  },
  "Business Analytics": {
    "jd": "Recolectar, transformar y analizar datos para generar insights que mejoren KPIs de negocio. Desarrollar dashboards en Power BI/Tableau, SQL avanzado para modelado y extracción; storytelling con datos; coordinación con stakeholders para definir métricas.",
    "keywords": "SQL, Power BI, Tableau, ETL, KPI, storytelling, Excel avanzado, Python, A/B testing, métricas de negocio",
    "must": ["SQL","Power BI"], "nice": ["Tableau","Python","ETL"],
    "synth_skills": ["SQL","Power BI","Tableau","Excel","ETL","KPIs","Storytelling","Python","A/B testing"]
  },
  "Diseñador/a UX": {
    "jd": "Responsable de research, definición de flujos, wireframes y prototipos de alta fidelidad en Figma. Aplicar heurísticas de usabilidad, accesibilidad y diseño centrado en el usuario. Colaborar con producto y engineering en design systems.",
    "keywords": "Figma, UX research, prototipado, wireframes, heurísticas, accesibilidad, design system, usabilidad, tests con usuarios",
    "must": ["Figma","UX Research","Prototipado"], "nice":["Heurísticas","Accesibilidad","Design System"],
    "synth_skills":["Figma","UX Research","Prototipado","Wireframes","Accesibilidad","Heurísticas","Design System","Analytics"]
  },
  "Ingeniero/a de Proyectos": {
    "jd":"Planificar, ejecutar y controlar proyectos de ingeniería. MS Project, AutoCAD/BIM, elaboración de presupuestos y cronogramas, gestión de riesgos y cambios. Deseable PMBOK/Agile.",
    "keywords":"MS Project, AutoCAD, BIM, presupuestos, cronogramas, control de cambios, riesgos, PMBOK, Agile, KPI, licitaciones",
    "must":["MS Project","AutoCAD","Presupuestos"], "nice":["BIM","PMBOK","Agile"],
    "synth_skills":["MS Project","AutoCAD","BIM","Presupuestos","Cronogramas","Riesgos","PMBOK","Agile","Excel","Power BI"]
  },
  "Enfermera/o Asistencial": {
    "jd":"Brindar atención segura y de calidad, registrar en HIS/SAP IS-H, educación al paciente, cumplimiento IAAS. BLS/ACLS vigentes.",
    "keywords":"HIS, SAP IS-H, BLS, ACLS, IAAS, educación al paciente, seguridad del paciente, protocolos, triage, signos vitales, curaciones, vía periférica, administración de medicamentos, registro clínico",
    "must":["HIS","BLS","ACLS","IAAS","Seguridad del paciente"], "nice":["SAP IS-H","Educación al paciente","Protocolos"],
    "synth_skills":["HIS","BLS","ACLS","IAAS","Educación al paciente","Seguridad del paciente","Protocolos","Excel"]
  },
  "Recepcionista de Admisión": {
    "jd": "Recepción de pacientes, registro, coordinación de citas, manejo de caja y facturación. Orientación al cliente y comunicación efectiva.",
    "keywords": "admisión, caja, facturación, SAP, HIS, atención al cliente, citas, recepción",
    "must": ["Atención al cliente","Registro","Caja"], "nice": ["Facturación","SAP","HIS"],
    "synth_skills": ["Atención al cliente","Registro","Caja","Facturación","SAP","HIS","Comunicación"]
  }
}

# =========================================================
# CSS (sidebar, login, estilos) — BLOQUE 1
# =========================================================
CSS = f"""
:root {{
  --green: {PRIMARY};
  --sb-bg: {SIDEBAR_BG};
  --sb-tx: {SIDEBAR_TX};
  --body: {BODY_BG};
  --sb-card: {CARD_BG};
  --content-top: 4px;   /* ← ajusta 0–12px para alinear h1 con el logo */
}}
html, body, [data-testid="stAppViewContainer"] {{ background: var(--body) !important; }}
.block-container {{ background: transparent !important; padding-top: var(--content-top) !important; }}

/* Ocultar menú/toolbar superior Streamlit */
#MainMenu {{visibility:hidden;}}
[data-testid="stToolbar"] {{ display:none !important; }}
header[data-testid="stHeader"] {{ height:0 !important; min-height:0 !important; }}

/* ---------- Sidebar ---------- */
[data-testid="stSidebar"] {{ background: var(--sb-bg) !important; color: var(--sb-tx) !important; }}
[data-testid="stSidebar"] * {{ color: var(--sb-tx) !important; }}

/* Títulos del sidebar al verde original */
[data-testid="stSidebar"] h4, [data-testid="stSidebar"] .stMarkdown h4 {{ color: var(--green) !important; }}

/* Botones del sidebar — pegados a la izquierda y compactos */
[data-testid="stSidebar"] .stButton{{ margin:0 !important; padding:0 !important; }}
[data-testid="stSidebar"] .stButton>button {{
  width: 100% !important; display:flex !important; justify-content:flex-start !important; align-items:center !important; text-align:left !important;
  gap:8px !important; background: var(--sb-card) !important; border:1px solid var(--sb-bg) !important; color:#fff !important;
  border-radius:12px !important; padding:9px 12px !important; margin: 0 8px 6px 0 !important; font-weight:600 !important; padding-left:8px !important;
}}

/* Botones del body */
.block-container .stButton>button {{
  width:auto !important; display:flex !important; justify-content:flex-start !important; align-items:center !important; text-align:left !important;
  background: var(--green) !important; color:#082017 !important; border-radius:10px !important; border:none !important; padding:.50rem .90rem !important; font-weight:700 !important;
}}
.block-container .stButton>button:hover {{ filter: brightness(.96); }}

/* Tipografía */
h1, h2, h3 {{ color: {TITLE_DARK}; }}
h1 strong, h2 strong, h3 strong {{ color: var(--green); }}

/* Inputs generales */
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

/* Agentes */
.agent-wrap .stButton>button{{background:var(--body)!important;color:{TITLE_DARK}!important;border:1px solid #E3EDF6!important;border-radius:10px!important;font-weight:700!important;padding:6px 10px!important}}
.agent-wrap .stButton>button:hover{{background:#fff!important}}
.agent-detail{{background:#fff;border:2px solid #E3EDF6;border-radius:16px;padding:16px;box-shadow:0 6px 18px rgba(14,25,43,.08)}}
.agent-detail input:disabled, .agent-detail textarea:disabled{{background:#EEF5FF!important;color:{TITLE_DARK}!important;border:1.5px solid #D7E7FB!important;opacity:1!important}}

/* Workflows */
.step-num{{width:26px;height:26px;border-radius:999px;border:2px solid #DDE7F5;display:flex;align-items:center;justify-content:center;font-weight:800;color:#345;}}
.step{{display:flex;gap:10px;align-items:center;margin:8px 0}}
.status-chip{{display:inline-flex;gap:8px;align-items:center;border:1px solid #E3EDF6;background:#F6FAFF;border-radius:999px;padding:4px 10px;font-size:12px}}
"""

# =========================================================
# CSS (marca + alineación h1) — BLOQUE 2
# =========================================================
CSS += """
/* Marca en sidebar */
.sidebar-brand {
  display:flex;
  flex-direction:column;
  align-items:center;
  justify-content:center;
  padding:0 0 2px;
  margin-top:0;
  text-align:center;
}
.sidebar-brand .brand-title{
  color: var(--green) !important;
  font-weight:800 !important;
  font-size:55px !important;
  line-height:1.05 !important;
}
/* "Powered by Wayki Consulting" — tamaño/color/negrita */
.sidebar-brand .brand-sub{
  color: var(--green) !important;
  font-size:12px !important;
  line-height:1.2 !important;
  font-weight:700 !important;
  opacity:.95 !important;
  margin-top:4px !important;
}

/* Quita margen arriba del 1er título del panel derecho */
.block-container h1:first-child,
.block-container h2:first-child,
.block-container h3:first-child{
  margin-top: 0 !important;
}
"""

st.set_page_config(page_title="SelektIA", page_icon="🧠", layout="wide")
st.markdown(f"<style>{CSS}</style>", unsafe_allow_html=True)
st.markdown("""
<style>
/* ===== TÍTULO STICKY EN EL PANEL DERECHO =====
   Usa la misma referencia de separación superior que ya definiste: --content-top
   Si ves que tapa algo, sube/baja el +8px.  */
.block-container h1:first-of-type,
.block-container h2:first-of-type{
  position: sticky;
  top: calc(var(--content-top) + 8px); /* ↑ afina 4–12px según tu logo/espaciado */
  z-index: 20;
  background: var(--body);             /* mantiene fondo sólido bajo el título */
  display: block;
  padding: 6px 0 10px 0;
  margin-top: 0 !important;
  border-bottom: 1px solid #E3EDF6;    /* (opcional) línea sutil bajo el título */
  box-shadow: 0 8px 10px -10px rgba(0,0,0,.06); /* (opcional) sombra sutil */
}

/* Un poco de aire entre el título y el primer bloque de contenido */
.block-container h1:first-of-type + *,
.block-container h2:first-of-type + *{
  margin-top: 12px !important;
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<style>
/* ===== Alinear alturas logo (izq) y título (der) ===== */

/* 1) Sube el contenido del panel derecho un poco (ajusta 0–12px) */
:root{
  --content-top: 6px;   /* prueba 4, 6, 8, … hasta que calce con tu logo */
}
.block-container{
  padding-top: var(--content-top) !important;
}

/* 2) Sube el logo del sidebar (offset negativo). 
      Ajusta -2, -4, -6 … hasta que coincida con el título. */
.sidebar-brand{
  position: relative;
  top: -20px !important;     /* mueve hacia arriba; valores típicos: -16 a -20 */
  margin-top: 0 !important; /* sin margen extra arriba */
}

/* (Opcional) elimina acolchado superior residual en el contenedor del sidebar */
[data-testid="stSidebar"] > div:first-child{
  padding-top: 0 !important;
}

/* Mantén compacto el espacio inmediatamente bajo el logo */
.sidebar-brand + [data-testid="stVerticalBlock"]{
  margin-top: 4px !important;
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<style>
/* ===== Sidebar ultra-compacto: títulos, párrafos y botones pegados ===== */
[data-testid="stSidebar"] [data-testid="stVerticalBlock"]{
  gap: 2px !important;                 /* espacio entre bloques del sidebar */
}
[data-testid="stSidebar"] [data-testid="stVerticalBlock"] > div{
  margin: 0 !important;                /* quita margen fantasma de cada widget */
  padding: 0 !important;
}

/* Títulos (h4) con margen mínimo */
[data-testid="stSidebar"] h4,
[data-testid="stSidebar"] .stMarkdown h4{
  margin: 2px 8px 2px !important;      /* arriba | lados | abajo */
  line-height: 1 !important;
}

/* Párrafos (items de texto simples) más pegados */
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p{
  margin: 2px 8px !important;
}

/* Botones: sin separación vertical y alineados a la izquierda */
[data-testid="stSidebar"] .stButton{
  margin: 0 !important;
  padding: 0 !important;
}
[data-testid="stSidebar"] .stButton > button{
  margin: 0 8px 6px 0 !important;      /* 0 a la izquierda */
  padding-left: 8px !important;        /* acerca el texto al borde */
  display: flex !important;
  justify-content: flex-start !important;
  align-items: center !important;
  text-align: left !important;
}

/* Menos aire bajo el logo */
.sidebar-brand{
  margin-bottom: 10px !important;
}
</style>
""", unsafe_allow_html=True)


# =========================================================
# Persistencia (Agentes / Flujos / Roles)
# =========================================================
DATA_DIR = Path("data"); DATA_DIR.mkdir(exist_ok=True)
AGENTS_FILE = DATA_DIR/"agents.json"
WORKFLOWS_FILE = DATA_DIR/"workflows.json"

# ---- Persistencia de roles ----
ROLES_FILE = DATA_DIR / "roles.json"
DEFAULT_ROLES = ["Headhunter", "Coordinador RR.HH.", "Admin RR.HH."]

def load_roles():
  """Carga roles guardados (además de los default)."""
  if ROLES_FILE.exists():
    try:
      roles = json.loads(ROLES_FILE.read_text(encoding="utf-8"))
      roles = sorted(list({*(DEFAULT_ROLES), *(r.strip() for r in roles if r.strip())}))
      return roles
    except:
      pass
  return DEFAULT_ROLES.copy()

def save_roles(roles: list):
  """Guarda sólo los no-default para no duplicar el archivo innecesariamente."""
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
if "section" not in ss:  ss.section = "def_carga"
if "tasks" not in ss:    ss.tasks = []
if "candidates" not in ss: ss.candidates = []
if "offers" not in ss:  ss.offers = {}
if "roles" not in ss: ss.roles = load_roles()
if "agents_loaded" not in ss:
  ss.agents = load_agents()
  ss.agents_loaded = True
if "workflows_loaded" not in ss:
  ss.workflows = load_workflows()
  ss.workflows_loaded = True
if "agent_view_open" not in ss: ss.agent_view_open = {}
if "agent_edit_open" not in ss: ss.agent_edit_open = {}
if "positions" not in ss:
  ss.positions = pd.DataFrame([
      {"ID":"10,645,194","Puesto":"Desarrollador/a Backend (Python)","Días Abierto":3,
       "Leads":1800,"Nuevos":115,"Recruiter Screen":35,"HM Screen":7,
       "Entrevista Telefónica":14,"Entrevista Presencial":15,"Ubicación":"Lima, Perú",
       "Hiring Manager":"Rivers Brykson","Estado":"Abierto"},
      {"ID":"10,376,415","Puesto":"VP de Marketing","Días Abierto":28,
       "Leads":8100,"Nuevos":1,"Recruiter Screen":15,"HM Screen":35,
       "Entrevista Telefónica":5,"Entrevista Presencial":7,"Ubicación":"Santiago, Chile",
       "Hiring Manager":"Angela Cruz","Estado":"Abierto"},
      {"ID":"10,376,646","Puesto":"Planner de Demanda","Días Abierto":28,
       "Leads":2300,"Nuevos":26,"Recruiter Screen":3,"HM Screen":8,
       "Entrevista Telefónica":6,"Entrevista Presencial":3,"Ubicación":"Ciudad de México, MX",
       "Hiring Manager":"Rivers Brykson","Estado":"Abierto"}
  ])

# =========================================================
# UTILS
# =========================================================
SKILL_SYNONYMS = {
  "Excel":["excel","xlsx"], "Gestión documental":["gestión documental","document control"], "Redacción":["redacción","writing"],
  "Facturación":["facturación","billing"], "Caja":["caja","cash"], "SQL":["sql","postgres","mysql"], "Power BI":["power bi"],
  "Tableau":["tableau"], "ETL":["etl"], "KPIs":["kpi","kpis"], "MS Project":["ms project"], "AutoCAD":["autocad"],
  "BIM":["bim","revit"], "Presupuestos":["presupuesto","presupuestos"], "Figma":["figma"], "UX Research":["ux research","investigación de usuarios"],
  "Prototipado":["prototipado","prototype"],
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
  b64=base64.b64encode(file_bytes).decode("utf-8")
  st.components.v1.html(
    f'<embed src="data:application/pdf;base64,{b64}" type="application/pdf" width="100%" height="{height}px"/>',
    height=height
  )

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
    if suffix == ".pdf":
      pdf_reader = PdfReader(io.BytesIO(uploaded_file.read()))
      text = ""
      for page in pdf_reader.pages:
        text += page.extract_text() or ""
      return text
    elif suffix == ".docx":
      return _extract_docx_bytes(uploaded_file.read())
    else:
      return uploaded_file.read().decode("utf-8", errors="ignore")
  except Exception as e:
    st.error(f"Error al leer '{uploaded_file.name}': {e}")
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

# =========================================================
# LOGIN
# =========================================================
def login_screen():
  st.markdown('<div style="display:flex;min-height:100vh;align-items:center;justify-content:center;background:#0E192B">', unsafe_allow_html=True)
  st.markdown('<div class="login-card">', unsafe_allow_html=True)
  st.markdown('<div class="login-logo-wrap" style="display:flex;align-items:center;justify-content:center;margin-bottom:14px">', unsafe_allow_html=True)
  st.markdown("</div>", unsafe_allow_html=True)
  st.markdown('<div class="login-sub" style="color:#9fb2d3;text-align:center;margin:0 0 18px 0;font-size:12.5px">Acceso a SelektIA — Demo</div>', unsafe_allow_html=True)
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
    login_screen()
    return False
  return True

# =========================================================
# SIDEBAR (navegación + logout)
# =========================================================
def render_sidebar():
  with st.sidebar:
    st.markdown(
      """
      <div class="sidebar-brand">
        <div class="brand-title">SelektIA</div>
        <div class="brand-sub">Powered by Wayki Consulting</div>
      </div>
      """,
      unsafe_allow_html=True
    )

    # DASHBOARD
    st.markdown("#### DASHBOARD")
    if st.button("Analytics", key="sb_analytics"):
      ss.section = "analytics"

    # ASISTENTE IA
    st.markdown("#### ASISTENTE IA")
    for txt, sec in [("Flujos","flows"), ("Agentes","agents"), ("Tareas de Agente","agent_tasks")]:
      if st.button(txt, key=f"sb_{sec}"):
        ss.section = sec

    # PROCESO DE SELECCIÓN
    st.markdown("#### PROCESO DE SELECCIÓN")
    for txt, sec in [
      ("Definición & Carga","def_carga"),
      ("Puestos","puestos"),
      ("Evaluación de CVs","eval"),
      ("Pipeline de Candidatos","pipeline"),
      ("Entrevista (Gerencia)","interview"),
      ("Tareas del Headhunter","hh_tasks"),
      ("Oferta","offer"),
      ("Onboarding","onboarding"),
    ]:
      if st.button(txt, key=f"sb_{sec}"):
        ss.section = sec

    # ACCIONES
    st.markdown("#### ACCIONES")
    if st.button("Crear tarea", key="sb_task"):
      ss.section = "create_task"

    # Cerrar sesión (sin título “SESIÓN”)
    if st.button("Cerrar sesión", key="sb_logout"):
      ss.auth = None
      st.rerun()

# =========================================================
# PÁGINAS
# =========================================================
def page_def_carga():
  st.header("Definición & Carga")
  role_names = list(ROLE_PRESETS.keys())
  puesto = st.selectbox("Puesto", role_names, index=0)
  preset = ROLE_PRESETS[puesto]

  jd_text = st.text_area("Descripción / JD", height=180, value=preset["jd"])
  kw_text = st.text_area("Palabras clave (coma separada)", height=100, value=preset["keywords"])

  ss["last_role"] = puesto
  ss["last_jd_text"] = jd_text
  ss["last_kw_text"] = kw_text

  files = st.file_uploader("Subir CVs (PDF / DOCX / TXT)", type=["pdf","docx","txt"], accept_multiple_files=True)
  if files and st.button("Procesar CVs cargados"):
    ss.candidates = []
    for f in files:
      b = f.read(); f.seek(0)
      text = extract_text_from_file(f)
      score, reasons = simple_score(text, jd_text, kw_text)
      ss.candidates.append({
        "Name": f.name, "Score": score, "Reasons": reasons,
        "_bytes": b, "_is_pdf": Path(f.name).suffix.lower()==".pdf",
        "_text": text, "meta": extract_meta(text)
      })
    st.success("CVs cargados y analizados.")
    st.rerun()

  with st.expander("🔌 Importar desde portales (demo)"):
    srcs=st.multiselect("Portales", JOB_BOARDS, default=["laborum.pe"])
    qty=st.number_input("Cantidad por portal",1,30,6)
    search_q=st.text_input("Búsqueda", value=puesto)
    location=st.text_input("Ubicación", value="Lima, Perú")
    if st.button("Traer CVs (demo)"):
      for board in srcs:
        for i in range(1,int(qty)+1):
          txt=f"{puesto} — {search_q} en {location}. Experiencia 5 años. Excel, SQL, gestión documental."
          ss.candidates.append({
            "Name":f"{board}_Candidato_{i:02d}.txt","Score":60,"Reasons":"demo",
            "_bytes":txt.encode(),"__":None,"_is_pdf":False,"_text":txt,"meta":extract_meta(txt)
          })
      st.success("Importados CVs simulados.")
      st.rerun()

def page_puestos():
  st.header("Puestos")
  st.dataframe(
    ss.positions[
      ["Puesto","Días Abierto","Leads","Nuevos","Recruiter Screen","HM Screen",
       "Entrevista Telefónica","Entrevista Presencial","Ubicación","Hiring Manager","Estado","ID"]
    ].sort_values(["Estado","Días Abierto","Leads"], ascending=[True,True,False]),
    use_container_width=True, height=380
  )

def page_eval():
  st.header("Resultados de evaluación")
  if not ss.candidates:
    st.info("Carga CVs en **Definición & Carga**.")
    return

  jd_text = st.text_area("JD para matching por skills (opcional)", ss.get("last_jd_text",""), height=140)
  preset = ROLE_PRESETS.get(ss.get("last_role",""), {})
  col1,col2 = st.columns(2)
  with col1: must_default = st.text_area("Must-have (coma separada)", value=", ".join(preset.get("must",[])))
  with col2: nice_default = st.text_area("Nice-to-have (coma separada)", value=", ".join(preset.get("nice",[])))
  must = [s.strip() for s in (must_default or "").split(",") if s.strip()]
  nice = [s.strip() for s in (nice_default or "").split(",") if s.strip()]

  enriched=[]
  for c in ss.candidates:
    cv=c.get("_text") or (c.get("_bytes") or b"").decode("utf-8","ignore")
    fit,exp=score_fit_by_skills(jd_text,must,nice,cv or "")
    enriched.append({
      "Name":c["Name"],"Fit":fit,
      "Must (ok/total)":f"{len(exp['matched_must'])}/{exp['must_total']}",
      "Nice (ok/total)":f"{len(exp['matched_nice'])}/{exp['nice_total']}",
      "Extras":", ".join(exp["extras"])[:60],
      "_exp":exp,"_is_pdf":c["_is_pdf"],"_bytes":c["_bytes"],"_text":cv,"meta":c.get("meta",{})
    })

  df=pd.DataFrame(enriched).sort_values("Fit", ascending=False).reset_index(drop=True)
  st.subheader("Ranking por Fit de Skills")
  st.dataframe(df[["Name","Fit","Must (ok/total)","Nice (ok/total)","Extras"]], use_container_width=True, height=250)

  st.subheader("Detalle y explicación")
  selected = st.selectbox("Elige un candidato", df["Name"].tolist())
  row=df[df["Name"]==selected].iloc[0]; exp=row["_exp"]

  c1,c2=st.columns([1.1,0.9])
  with c1:
    fig=px.bar(pd.DataFrame([{"Candidato":row["Name"],"Fit":row["Fit"]}]), x="Candidato", y="Fit", title="Fit por skills")
    fig.update_traces(marker_color=BAR_GOOD if row["Fit"]>=60 else BAR_DEFAULT, hovertemplate="%{x}<br>Fit: %{y}%")
    fig.update_layout(plot_bgcolor="#FFFFFF", paper_bgcolor="rgba(0,0,0,0)",
                      font=dict(color=TITLE_DARK), xaxis_title=None, yaxis_title="Fit")
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("**Explicación**")
    st.markdown(f"- **Must-have:** {len(exp['matched_must'])}/{exp['must_total']}")
    if exp["matched_must"]: st.markdown("  - ✓ " + ", ".join(exp["matched_must"]))
    if exp["gaps_must"]:   st.markdown("  - ✗ Faltantes: " + ", ".join(exp["gaps_must"]))
    st.markdown(f"- **Nice-to-have:** {len(exp['matched_nice'])}/{exp['nice_total']}")
    if exp["matched_nice"]: st.markdown("  - ✓ " + ", ".join(exp["matched_nice"]))
    if exp["gaps_nice"]:    st.markdown("  - ✗ Faltantes: " + ", ".join(exp["gaps_nice"]))
    if exp["extras"]:        st.markdown("- **Extras:** " + ", ".join(exp["extras"]))
  with c2:
    st.markdown("**CV (visor)**")
    if row["_is_pdf"]: pdf_viewer_embed(row["_bytes"], height=420)
    else: st.text_area("Contenido (TXT)", row["_text"], height=260)

def page_pipeline():
  st.header("Pipeline de Candidatos")
  if not ss.candidates:
    st.info("Primero carga CVs en **Definición & Carga**.")
    return
  jd=ss.get("last_jd_text","")
  preset=ROLE_PRESETS.get(ss.get("last_role",""), {})
  must, nice = preset.get("must",[]), preset.get("nice",[])
  ranked=[]
  for c in ss.candidates:
    txt=c.get("_text") or (c.get("_bytes") or b"").decode("utf-8","ignore")
    fit,ex=score_fit_by_skills(jd,must,nice,txt or "")
    ranked.append((fit,c,ex))
  ranked.sort(key=lambda x:x[0], reverse=True)

  c1, c2 = st.columns([1.2, 1])
  with c1:
    table=[{"Candidato":c["Name"],"Fit":fit,"Años Exp.":c.get("meta",{}).get("anios_exp",0),"Actualizado":c.get("meta",{}).get("ultima_actualizacion","—")} for fit,c,_ in ranked]
    df=pd.DataFrame(table).sort_values(["Fit","Años Exp."], ascending=[False,False])
    st.dataframe(df, use_container_width=True, height=300)
    names=df["Candidato"].tolist()
    pre=ss.get("selected_cand", names[0] if names else "")
    selected = st.radio("Selecciona un candidato", names, index=names.index(pre) if pre in names else 0)
    ss["selected_cand"] = selected
  with c2:
    t=next((t for t in ranked if t[1]["Name"]==ss["selected_cand"]), None)
    if not t: st.caption("Candidato no encontrado."); return
    fit,row,exp=t; m=row.get("meta",{})
    st.markdown(f"**{row['Name']}**")
    st.markdown('<div class="k-card">', unsafe_allow_html=True)
    st.markdown(f"**Match por skills:** {'✅ Alto' if fit>=70 else ('🟡 Medio' if fit>=40 else '🔴 Bajo')}  \n**Puntuación:** {fit}%")
    st.markdown("---"); st.markdown("**Instrucción**"); st.caption(EVAL_INSTRUCTION)
    st.markdown("**Análisis (resumen)**"); st.write(build_analysis_text(row["Name"], exp))
    st.markdown("---")
    st.markdown(f"**Años de experiencia:** {m.get('anios_exp',0)}")
    st.markdown(f"**Última actualización CV:** {m.get('ultima_actualizacion','—')}")
    st.markdown("</div>", unsafe_allow_html=True)
    st.subheader("CV")
    if row["_is_pdf"]: pdf_viewer_embed(row["_bytes"], height=420)
    else: st.text_area("Contenido (TXT)", row.get("_text",""), height=260)

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
  if cand_name not in ss.offers:
    ss.offers[cand_name] = {
      "puesto": "",
      "ubicacion": "",
      "modalidad": "Presencial",
      "salario": "",
      "beneficios": "",
      "fecha_inicio": date.today() + timedelta(days=14),
      "caducidad": date.today() + timedelta(days=7),
      "aprobadores": "Gerencia, Legal, Finanzas",
      "estado": "Borrador"
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
      offer["modalidad"] = st.selectbox("Modalidad", ["Presencial","Híbrido","Remoto"], index=["Presencial","Híbrido","Remoto"].index(offer["modalidad"]))
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
  with col1:
    st.checkbox("✅ Contacto hecho")
  with col2:
    st.checkbox("✅ Entrevista agendada")
  with col3:
    st.checkbox("✅ Feedback recibido")
  st.text_area("Notas (3 fortalezas, 2 riesgos, pretensión, disponibilidad)", height=120)
  st.file_uploader("Adjuntos (BLS/ACLS, colegiatura, etc.)", accept_multiple_files=True)

  c1, c2 = st.columns(2)
  if c1.button("Guardar"):
    st.success("Checklist y notas guardadas.")
  if c2.button("Enviar a Comité"):
    st.info("Bloqueo de edición del HH y acta breve generada.")

# ===================== AGENTES =====================
def page_agents():
  st.header("Agentes")
  st.markdown("### Tus agentes")
  can_edit_any = (ss.auth["role"] == "Administrador")

  if not ss.agents:
    st.info("Aún no hay agentes. Crea el primero en el formulario de abajo.")
  else:
    cols_per_row=2
    for i in range(0,len(ss.agents),cols_per_row):
      r=ss.agents[i:i+cols_per_row]
      cols=st.columns(cols_per_row)
      for j,ag in enumerate(r):
        idx=i+j
        with cols[j]:
          img=AGENT_DEFAULT_IMAGES.get(ag.get("rol","Headhunter"))  # sin campo URL (eliminado)
          st.markdown(f"""
          <div style="background:#fff;border:1px solid #E3EDF6;border-radius:16px;padding:16px;text-align:center;">
            <img src="{img}" style="width:120px;height:120px;border-radius:999px;object-fit:cover;border:4px solid #F1F7FD;">
            <div style="height:8px"></div>
            <div style="font-weight:800;color:{TITLE_DARK};font-size:18px">{ag.get('rol','—')}</div>
            <div style="font-size:13px;opacity:.8;margin-top:6px">{ag.get('objetivo','—')}</div>
          </div>""", unsafe_allow_html=True)

          allowed_roles = ag.get("perms", ["Supervisor","Administrador"])
          st.markdown('<div class="agent-wrap">', unsafe_allow_html=True)
          c1,c2,c3,c4=st.columns([1,1,1,1])
          # Etiquetas fijas pero comportamiento toggle
          with c1:
            is_open=ss.agent_view_open.get(idx, False)
            if st.button("Ver", key=f"ag_view_{idx}"):
              ss.agent_view_open[idx]=not is_open; st.rerun()
          with c2:
            can_edit = can_edit_any or (ss.auth["role"] in allowed_roles)
            if can_edit:
              is_edit=ss.agent_edit_open.get(idx, False)
              if st.button("Editar", key=f"ag_edit_{idx}"):
                ss.agent_edit_open[idx]=not is_edit; st.rerun()
            else:
              st.caption("Sin permiso")
          with c3:
            if (can_edit_any or (ss.auth["role"] in allowed_roles)) and st.button("Clonar", key=f"ag_clone_{idx}"):
              clone=dict(ag); clone["rol"]=f"{ag.get('rol','Agente')} (copia)"
              ss.agents.append(clone); save_agents(ss.agents); st.success("Agente clonado."); st.rerun()
          with c4:
            if (can_edit_any or (ss.auth["role"] in allowed_roles)) and st.button("Eliminar", key=f"ag_del_{idx}"):
              ss.agents.pop(idx); save_agents(ss.agents); st.success("Agente eliminado."); st.rerun()
          st.markdown('</div>', unsafe_allow_html=True)

        if ss.agent_view_open.get(idx, False):
          st.subheader("Detalle del agente")
          st.markdown('<div class="agent-detail">', unsafe_allow_html=True)
          c1,c2=st.columns([0.42,0.58])
          with c1:
            st.image(AGENT_DEFAULT_IMAGES.get(ag.get("rol","Headhunter")), width=200)
            st.caption("Modelo LLM (simulado)")
            st.markdown(f"<div class='badge'>🧠 {ag.get('llm_model','gpt-4o-mini')}</div>", unsafe_allow_html=True)
          with c2:
            st.text_input("Role*", value=ag.get("rol",""), disabled=True)
            st.text_area("Objetivo*", value=ag.get("objetivo",""), height=120, disabled=True)
            st.text_area("Backstory*", value=ag.get("backstory",""), height=160, disabled=True)
            st.text_area("Guardrails", value=ag.get("guardrails",""), height=90, disabled=True)
            st.caption("Permisos"); st.write(", ".join(ag.get("perms",[])) or "—")
          st.markdown('</div>', unsafe_allow_html=True)

        if ss.agent_edit_open.get(idx, False):
          st.info(f"Editando: {ag.get('rol')}")
          with st.form(f"agent_edit_{idx}"):
            # Selector de rol con opción Nuevo…
            opciones = ss.roles + ["Nuevo…"]
            rol_sel = st.selectbox("Rol*", opciones, index=opciones.index(ag.get("rol", opciones[0])) if ag.get("rol") in opciones else len(opciones)-1)
            rol_nuevo = ""
            if rol_sel == "Nuevo…":
              rol_nuevo = st.text_input("Nombre del nuevo rol*", value=ag.get("rol",""))
            objetivo  = st.text_area("Objetivo*", value=ag.get("objetivo",""), height=120)
            backstory = st.text_area("Backstory*", value=ag.get("backstory",""), height=160)
            guardrails= st.text_area("Guardrails", value=ag.get("guardrails",""), height=90)
            llm_model   = st.selectbox("Modelo LLM (simulado)", LLM_MODELS, index=max(0, LLM_MODELS.index(ag.get("llm_model","gpt-4o-mini"))))
            perms       = st.multiselect("Permisos (quién puede editar)", ["Colaborador","Supervisor","Administrador"], default=ag.get("perms",["Supervisor","Administrador"]))
            if st.form_submit_button("Guardar cambios"):
              rol_final = (rol_nuevo.strip() or "Agente") if rol_sel=="Nuevo…" else rol_sel
              ag.update({"rol":rol_final,"objetivo":objetivo,"backstory":backstory,"guardrails":guardrails,"llm_model":llm_model,"perms":perms})
              # Actualiza catálogo de roles si corresponde
              if rol_sel=="Nuevo…" and rol_nuevo.strip():
                if rol_nuevo.strip() not in ss.roles:
                  ss.roles.append(rol_nuevo.strip())
                  save_roles(ss.roles)
              save_agents(ss.agents); st.success("Agente actualizado."); st.rerun()

  st.markdown("---")
  st.subheader("Crear / Editar agente")
  with st.form("agent_form"):
    # Selector de rol con opción Nuevo…
    opciones = ss.roles + ["Nuevo…"]
    rol_sel = st.selectbox("Rol*", opciones, index=0)
    rol_nuevo = ""
    if rol_sel == "Nuevo…":
      rol_nuevo = st.text_input("Nombre del nuevo rol*")

    objetivo  = st.text_area("Objetivo*", "Identificar a los mejores profesionales para el cargo definido en el JD", height=120)
    backstory = st.text_area("Backstory*", "Eres un analista de RR.HH. con experiencia en análisis de documentos, CV y currículums.", height=160)
    guardrails= st.text_area("Guardrails", "No compartas datos sensibles. Cita la fuente (CV o JD) al argumentar.", height=90)
    llm_model   = st.selectbox("Modelo LLM (simulado)", LLM_MODELS, index=0)
    perms       = st.multiselect("Permisos (quién puede editar)", ["Colaborador","Supervisor","Administrador"], default=["Supervisor","Administrador"])
    ok = st.form_submit_button("Guardar/Actualizar Agente")
    if ok:
      rol_final = (rol_nuevo.strip() or "Agente") if rol_sel=="Nuevo…" else rol_sel
      # Crear registro
      ss.agents.append({
        "rol": rol_final, "objetivo": objetivo, "backstory": backstory,
        "guardrails": guardrails, "llm_model": llm_model, "perms": perms,
        "ts": datetime.utcnow().isoformat()
      })
      # Actualizar catálogo de roles si se creó uno nuevo
      if rol_sel=="Nuevo…" and rol_nuevo.strip():
        if rol_nuevo.strip() not in ss.roles:
          ss.roles.append(rol_nuevo.strip())
          save_roles(ss.roles)
      save_agents(ss.agents)
      st.success("Agente guardado.")
      st.rerun()

# ===================== FLUJOS (Workflows) =====================
def page_flows():
    # --- Título "Flujos" fijo al hacer scroll ---
st.markdown("""
<style>
  /* Título fijo solo en la página Flujos */
  #flows-title{
    position: sticky;
    top: calc(var(--content-top, 0px) + 8px);  /* ajusta 4–12px a gusto */
    z-index: 40;
    background: var(--body, #F7FBFF);
    padding: 6px 0 10px;
    margin: 0 0 8px 0;
    border-bottom: 1px solid #E3EDF6;          /* opcional */
    box-shadow: 0 8px 10px -10px rgba(0,0,0,.06); /* opcional */
  }
  /* Un poco de aire al primer bloque tras el título */
  #flows-title + div { margin-top: 10px !important; }
</style>
""", unsafe_allow_html=True)
st.markdown('<h1 id="flows-title">Flujos</h1>', unsafe_allow_html=True)


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
        ag_label = "—"
        ai = wf.get("agent_idx",-1)
        if 0 <= ai < len(ss.agents):
          ag_label = ss.agents[ai].get("rol","Agente")
        rows.append({
          "ID": wf["id"], "Nombre": wf["name"], "Puesto": wf.get("role","—"),
          "Agente": ag_label, "Estado": wf.get("status","Borrador"),
          "Programado": wf.get("schedule_at","—")
        })
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
              clone["status"]="Borrador"; clone["approved_by"]=""; clone["approved_at"]=""
              ss.workflows.insert(0, clone); save_workflows(ss.workflows); st.success("Flujo duplicado."); st.rerun()
          with c2:
            if st.button("🗑 Eliminar"):
              ss.workflows = [w for w in ss.workflows if w["id"]!=wf["id"]]; save_workflows(ss.workflows)
              st.success("Flujo eliminado."); st.rerun()
          with c3:
            st.markdown(f"<div class='status-chip'>Estado: <b>{wf.get('status','Borrador')}</b></div>", unsafe_allow_html=True)
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
      st.markdown("<div class='step'><div class='step-num'>1</div><div><b>Task</b><br><span style='opacity:.75'>Describe la tarea</span></div></div>", unsafe_allow_html=True)
      name = st.text_input("Name*", value="Analizar CV")
      role = st.selectbox("Puesto objetivo", list(ROLE_PRESETS.keys()), index=2)
      desc = st.text_area("Description*", value=EVAL_INSTRUCTION, height=110)
      expected = st.text_area("Expected output*", value="- Puntuación 0 a 100 según coincidencia con JD\n- Resumen del CV justificando el puntaje", height=80)

      st.markdown("**Job Description (elige una opción)**")
      jd_text = st.text_area("JD en texto", value=ROLE_PRESETS[role]["jd"], height=140)
      jd_file = st.file_uploader("…o sube JD en PDF/TXT/DOCX", type=["pdf","txt","docx"], key="wf_jd_file")
      jd_from_file = ""
      if jd_file is not None:
        jd_from_file = extract_text_from_file(jd_file)
        st.caption("Vista previa del JD extraído (solo texto):")
        st.text_area("Preview", jd_from_file[:4000], height=160)

      st.markdown("---")
      st.markdown("<div class='step'><div class='step-num'>2</div><div><b>Staff in charge</b><br><span style='opacity:.75'>Agente asignado</span></div></div>", unsafe_allow_html=True)
      if ss.agents:
        agent_opts = [f"{i} — {a.get('rol','Agente')} ({a.get('llm_model','model')})" for i,a in enumerate(ss.agents)]
        agent_pick = st.selectbox("Asigna un agente", agent_opts, index=0)
        agent_idx = int(agent_pick.split(" — ")[0])
      else:
        st.info("No hay agentes. Crea uno en la pestaña **Agentes**.")
        agent_idx = -1

      st.markdown("---")
      st.markdown("<div class='step'><div class='step-num'>3</div><div><b>Guardar</b><br><span style='opacity:.75'>Aprobación y programación</span></div></div>", unsafe_allow_html=True)
      run_date = st.date_input("Fecha de ejecución", value=date.today()+timedelta(days=1))
      run_time = st.time_input("Hora de ejecución", value=datetime.now().time().replace(second=0, microsecond=0))
      col_a, col_b, col_c = st.columns(3)
      save_draft     = col_a.form_submit_button("💾 Guardar borrador")
      send_approval  = col_b.form_submit_button("📝 Enviar a aprobación")
      schedule       = col_c.form_submit_button("📅 Guardar y Programar")

    if save_draft or send_approval or schedule:
      jd_final = jd_from_file if jd_from_file else jd_text
      if not jd_final.strip():
        st.error("Debes proporcionar un JD (texto o archivo).")
      elif agent_idx < 0:
        st.error("Debes asignar un agente.")
      else:
        wf = {
          "id": f"WF-{int(datetime.now().timestamp())}",
          "name": name, "role": role,
          "description": desc, "expected_output": expected,
          "jd_text": jd_final[:200000],
          "agent_idx": agent_idx,
          "created_at": datetime.now().isoformat(),
          "status": "Borrador", "approved_by": "", "approved_at": "", "schedule_at": ""
        }
        if send_approval:
          wf["status"] = "Pendiente de aprobación"
          st.success("Flujo enviado a aprobación. Supervisor/Administrador debe aprobarlo.")
        if schedule:
          if puede_aprobar:
            wf["status"] = "Programado"
            wf["schedule_at"] = f"{run_date} {run_time.strftime('%H:%M')}"
            st.success("Flujo programado.")
          else:
            wf["status"] = "Pendiente de aprobación"
            wf["schedule_at"] = f"{run_date} {run_time.strftime('%H:%M')}"
            st.info("Guardado y **pendiente de aprobación** por Supervisor/Administrador.")
        if save_draft:
          st.success("Borrador guardado.")

        ss.workflows.insert(0, wf)
        save_workflows(ss.workflows)
        st.rerun()

# ===================== ANALYTICS =====================
def page_analytics():
  st.header("Analytics")

  total_puestos = len(ss.positions)
  total_cvs = len(ss.candidates)
  avg_fit = None
  if total_cvs:
    jd = ss.get("last_jd_text","")
    preset = ROLE_PRESETS.get(ss.get("last_role",""), {})
    must, nice = preset.get("must",[]), preset.get("nice",[])
    fits=[]
    for c in ss.candidates:
      txt=c.get("_text") or (c.get("_bytes") or b"").decode("utf-8","ignore")
      f,_=score_fit_by_skills(jd,must,nice,txt or "")
      fits.append(f)
    avg_fit = round(sum(fits)/len(fits),1)

  c1,c2,c3 = st.columns(3)
  c1.metric("Puestos activos", total_puestos)
  c2.metric("CVs en bandeja", total_cvs)
  c3.metric("Fit promedio (skills)", avg_fit if avg_fit is not None else "—")

  st.markdown("---")

  if total_cvs:
    bins = []
    jd = ss.get("last_jd_text","")
    preset = ROLE_PRESETS.get(ss.get("last_role",""), {})
    must, nice = preset.get("must",[]), preset.get("nice",[])
    for c in ss.candidates:
      txt=c.get("_text") or (c.get("_bytes") or b"").decode("utf-8","ignore")
      f,_=score_fit_by_skills(jd,must,nice,txt or "")
      label = "Alto (>=70)" if f>=70 else ("Medio (40-69)" if f>=40 else "Bajo (<40)")
      bins.append(label)
    df=pd.DataFrame({"Fit band":bins})
    fig=px.histogram(df, x="Fit band", title="Distribución de Fit por skills")
    fig.update_layout(plot_bgcolor="#FFFFFF", paper_bgcolor="rgba(0,0,0,0)", font=dict(color=TITLE_DARK))
    st.plotly_chart(fig, use_container_width=True)

  dfp = ss.positions[["Puesto","Días Abierto"]].copy()
  fig2 = px.bar(dfp, x="Puesto", y="Días Abierto", title="Días abiertos por puesto")
  fig2.update_layout(plot_bgcolor="#FFFFFF", paper_bgcolor="rgba(0,0,0,0)", font=dict(color=TITLE_DARK), xaxis_tickangle=-20)
  st.plotly_chart(fig2, use_container_width=True)

  if total_cvs:
    skill_counts={}
    for c in ss.candidates:
      txt=c.get("_text") or (c.get("_bytes") or b"").decode("utf-8","ignore")
      for s in infer_skills(txt):
        skill_counts[s]=skill_counts.get(s,0)+1
    if skill_counts:
      dfskills=pd.DataFrame(sorted(skill_counts.items(), key=lambda x:x[1], reverse=True), columns=["Skill","Frecuencia"])
      st.subheader("Skills detectadas en CVs (Top)")
      st.dataframe(dfskills.head(20), use_container_width=True, height=300)
    else:
      st.info("No se detectaron skills en los CVs actuales.")

# ===================== OTRAS =====================
def page_agent_tasks():
  st.header("Tareas de Agente")
  st.write("Bandeja de tareas para asistentes (demo).")

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

# =========================================================
# APP
# =========================================================
if require_auth():
  render_sidebar()
  ROUTES.get(ss.section, page_def_carga)()
