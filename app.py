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
PRIMARY    = "#00CD78"         # <- color marca (usado en los charts)
SIDEBAR_BG = "#0E192B"
SIDEBAR_TX = "#B9C7DF"
BODY_BG    = "#F7FBFF"
CARD_BG    = "#0E192B"
TITLE_DARK = "#142433"

BAR_DEFAULT = "#E9F3FF"
BAR_GOOD    = "#33FFAC"

JOB_BOARDS  = ["laborum.pe","Computrabajo","Bumeran","Indeed","LinkedIn Jobs"]

EVAL_INSTRUCTION = (
  "Debes analizar los CVs de postulantes y calificarlos de 0% a 100% según el nivel de coincidencia con el JD. "
  "Incluye un análisis breve que explique por qué califica o no el postulante, destacando habilidades must-have, "
  "nice-to-have, brechas y hallazgos relevantes."
)

# ===== Login simulado =====
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

/* ---- Tarjeta de agente (compacta) ---- */
.agent-card{{background:#fff;border:1px solid #E3EDF6;border-radius:14px;padding:10px;text-align:center;min-height:178px}}
.agent-card img{{width:84px;height:84px;border-radius:999px;object-fit:cover;border:4px solid #F1F7FD}}
.agent-title{{font-weight:800;color:{TITLE_DARK};font-size:15px;margin-top:6px}}
.agent-sub{{font-size:12px;opacity:.8;margin-top:4px;min-height:30px}}

/* Toolbar de iconos integrada en la tarjeta */
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
# Persistencia (Agentes / Flujos / Roles)
# =========================================================
DATA_DIR = Path("data"); DATA_DIR.mkdir(exist_ok=True)
AGENTS_FILE = DATA_DIR/"agents.json"
WORKFLOWS_FILE = DATA_DIR/"workflows.json"

ROLES_FILE = DATA_DIR / "roles.json"
DEFAULT_ROLES = ["Headhunter", "Coordinador RR.HH.", "Admin RR.HH."]

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
  st.markdown('<div class="login-sub">Acceso a SelektIA — Demo</div>', unsafe_allow_html=True)
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
    for txt, sec in [("Flujos","flows"), ("Agentes","agents"), ("Tareas de Agente","agent_tasks")]:
      if st.button(txt, key=f"sb_{sec}"): ss.section = sec

    st.markdown("#### PROCESO DE SELECCIÓN")
    for txt, sec in [("Definición & Carga","def_carga"), ("Puestos","puestos"), ("Evaluación de CVs","eval"),
                     ("Pipeline de Candidatos","pipeline"), ("Entrevista (Gerencia)","interview"),
                     ("Tareas del Headhunter","hh_tasks"), ("Oferta","offer"), ("Onboarding","onboarding")]:
      if st.button(txt, key=f"sb_{sec}"): ss.section = sec

    st.markdown("#### ACCIONES")
    if st.button("Crear tarea", key="sb_task"): ss.section = "create_task"

    if st.button("Cerrar sesión", key="sb_logout"):
      ss.auth = None; st.rerun()

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
  ss["last_role"] = puesto; ss["last_jd_text"] = jd_text; ss["last_kw_text"] = kw_text

  files = st.file_uploader("Subir CVs (PDF / DOCX / TXT)", type=["pdf","docx","txt"], accept_multiple_files=True)
  if files and st.button("Procesar CVs cargados"):
    ss.candidates = []
    for f in files:
      b = f.read(); f.seek(0)
      text = extract_text_from_file(f)
      score, reasons = simple_score(text, jd_text, kw_text)
      ss.candidates.append({"Name": f.name, "Score": score, "Reasons": reasons, "_bytes": b,
                            "_is_pdf": Path(f.name).suffix.lower()==".pdf", "_text": text,
                            "meta": extract_meta(text)})
    st.success("CVs cargados y analizados."); st.rerun()

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
            "Name":f"{board}_Candidato_{i:02d}.txt","Score":60,"Reasons":"demo","_bytes":txt.encode(),
            "_is_pdf":False,"_text":txt,"meta":extract_meta(txt)
          })
      st.success("Importados CVs simulados."); st.rerun()

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
    st.info("Carga CVs en **Definición & Carga**."); return
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
    enriched.append({"Name":c["Name"],"Fit":fit,"Must (ok/total)":f"{len(exp['matched_must'])}/{exp['must_total']}",
                     "Nice (ok/total)":f"{len(exp['matched_nice'])}/{exp['nice_total']}",
                     "Extras":", ".join(exp["extras"])[:60],"_exp":exp,"_is_pdf":c["_is_pdf"],
                     "_bytes":c["_bytes"],"_text":cv,"meta":c.get("meta",{})})
  df=pd.DataFrame(enriched).sort_values("Fit", ascending=False).reset_index(drop=True)
  st.subheader("Ranking por Fit de Skills")
  st.dataframe(df[["Name","Fit","Must (ok/total)","Nice (ok/total)","Extras"]], use_container_width=True, height=250)

  st.subheader("Detalle y explicación")
  selected = st.selectbox("Elige un candidato", df["Name"].tolist())
  row=df[df["Name"]==selected].iloc[0]; exp=row["_exp"]

  c1,c2=st.columns([1.1,0.9])
  with c1:
    fig=px.bar(pd.DataFrame([{"Candidato":row["Name"],"Fit":row["Fit"]}]), x="Candidato", y="Fit", title="Fit por skills",
               color_discrete_sequence=[PRIMARY])
    fig.update_traces(hovertemplate="%{x}<br>Fit: %{y}%")
    fig.update_layout(plot_bgcolor="#FFFFFF", paper_bgcolor="rgba(0,0,0,0)",font=dict(color=TITLE_DARK),xaxis_title=None,yaxis_title="Fit")
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

  # ---------- CREAR NUEVO (arriba) ----------
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
        llm_model    = st.selectbox("Modelo LLM (simulado)", LLM_MODELS, index=0)
        img_src      = st.text_input("URL de imagen (opcional)", value=AGENT_DEFAULT_IMAGES.get("Headhunter",""))
        perms        = st.multiselect("Permisos (quién puede editar)", ["Colaborador","Supervisor","Administrador"], default=["Supervisor","Administrador"])
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

  # ---------- GRID de agentes (5 por fila) ----------
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
        st.markdown(
          f"""
          <div class="agent-card">
            <img src="{img}">
            <div class="agent-title">{ag.get('rol','—')}</div>
            <div class="agent-sub">{ag.get('objetivo','—')}</div>
          </div>
          """, unsafe_allow_html=True
        )
        # Toolbar centrada y mimética (dentro del card)
        st.markdown('<div class="toolbar">', unsafe_allow_html=True)
        c1, c2, c3, c4 = st.columns(4)
        with c1:
          if st.button("👁", key=f"ag_v_{idx}", help="Ver"):
            ss.agent_view_idx = (None if ss.agent_view_idx == idx else idx)
            ss.agent_edit_idx = None
            st.rerun()
        with c2:
          if st.button("✏", key=f"ag_e_{idx}", help="Editar"):
            ss.agent_edit_idx = (None if ss.agent_edit_idx == idx else idx)
            ss.agent_view_idx = None
            st.rerun()
        with c3:
          if st.button("🧬", key=f"ag_c_{idx}", help="Clonar"):
            clone = dict(ag); clone["rol"] = f"{ag.get('rol','Agente')} (copia)"
            ss.agents.append(clone); save_agents(ss.agents); st.success("Agente clonado."); st.rerun()
        with c4:
          if st.button("🗑", key=f"ag_d_{idx}", help="Eliminar"):
            ss.agents.pop(idx); save_agents(ss.agents); st.success("Agente eliminado."); st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

  # ---------- Detalle debajo de la grilla ----------
  if ss.agent_view_idx is not None and 0 <= ss.agent_view_idx < len(ss.agents):
    ag = ss.agents[ss.agent_view_idx]
    st.markdown("### Detalle del agente")

    st.markdown('<div class="agent-detail">', unsafe_allow_html=True)
    c1, c2 = st.columns([0.42, 0.58])
    with c1:
      # imagen segura usando <img> (evita validaciones de PIL/GIF)
      raw_img = ag.get("image") or ""
      safe_img = (raw_img.strip() if isinstance(raw_img, str) and raw_img.strip()
                  else AGENT_DEFAULT_IMAGES.get(ag.get("rol","Headhunter"), AGENT_DEFAULT_IMAGES["Headhunter"]))
      st.markdown(
        f"""
        <div style="text-align:center;margin:6px 0 12px">
          <img src="{safe_img}"
               style="width:180px;height:180px;border-radius:999px;
                      object-fit:cover;border:4px solid #F1F7FD;">
        </div>
        """, unsafe_allow_html=True
      )
      st.caption("Modelo LLM (simulado)")
      st.markdown(f"<div class='badge'>🧠 {ag.get('llm_model','gpt-4o-mini')}</div>", unsafe_allow_html=True)
    with c2:
      st.text_input("Role*", value=ag.get("rol",""), disabled=True)
      st.text_input("Objetivo*", value=ag.get("objetivo",""), disabled=True)
      st.text_area("Backstory*", value=ag.get("backstory",""), height=120, disabled=True)
      st.text_area("Guardrails", value=ag.get("guardrails",""), height=90, disabled=True)
      st.caption("Herramientas habilitadas"); st.write(", ".join(ag.get("herramientas",[])) or "—")
      st.caption("Permisos"); st.write(", ".join(ag.get("perms",[])) or "—")
    st.markdown('</div>', unsafe_allow_html=True)

  # ---------- Edición debajo ----------
  if ss.agent_edit_idx is not None and 0 <= ss.agent_edit_idx < len(ss.agents):
    ag = ss.agents[ss.agent_edit_idx]
    st.markdown("### Editar agente")
    with st.form(f"agent_edit_{ss.agent_edit_idx}"):
      objetivo  = st.text_input("Objetivo*", value=ag.get("objetivo",""))
      backstory = st.text_area("Backstory*", value=ag.get("backstory",""), height=120)
      guardrails= st.text_area("Guardrails", value=ag.get("guardrails",""), height=90)
      herramientas = st.multiselect("Herramientas habilitadas", ["Parser de PDF","Recomendador de skills","Comparador JD-CV"], default=ag.get("herramientas",["Parser de PDF","Recomendador de skills"]))
      llm_model   = st.selectbox("Modelo LLM (simulado)", LLM_MODELS, index=max(0, LLM_MODELS.index(ag.get("llm_model","gpt-4o-mini"))))
      img_src     = st.text_input("URL de imagen", value=ag.get("image",""))
      perms       = st.multiselect("Permisos (quién puede editar)", ["Colaborador","Supervisor","Administrador"], default=ag.get("perms",["Supervisor","Administrador"]))
      if st.form_submit_button("Guardar cambios"):
        ag.update({"objetivo":objetivo,"backstory":backstory,"guardrails":guardrails,"herramientas":herramientas,
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
      if not jd_final.strip(): st.error("Debes proporcionar un JD (texto o archivo).")
      elif agent_idx < 0:     st.error("Debes asignar un agente.")
      else:
        wf = {"id": f"WF-{int(datetime.now().timestamp())}","name": name,"role": role,"description": desc,"expected_output": expected,
              "jd_text": jd_final[:200000],"agent_idx": agent_idx,"created_at": datetime.now().isoformat(),
              "status": "Borrador","approved_by": "","approved_at": "","schedule_at": ""}
        if send_approval: wf["status"] = "Pendiente de aprobación"; st.success("Flujo enviado a aprobación.")
        if schedule:
          if puede_aprobar:
            wf["status"]="Programado"; wf["schedule_at"]=f"{run_date} {run_time.strftime('%H:%M')}"; st.success("Flujo programado.")
          else:
            wf["status"]="Pendiente de aprobación"; wf["schedule_at"]=f"{run_date} {run_time.strftime('%H:%M')}"; st.info("Pendiente de aprobación.")
        if save_draft: st.success("Borrador guardado.")
        ss.workflows.insert(0, wf); save_workflows(ss.workflows); st.rerun()

# ===================== ANALYTICS =====================
def page_analytics():
  st.header("Analytics")

  # Métricas top
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

  m1, m2, m3 = st.columns(3)
  m1.metric("Puestos activos", total_puestos)
  m2.metric("CVs en bandeja", total_cvs)
  m3.metric("Fit promedio (skills)", avg_fit if avg_fit is not None else "—")

  st.markdown("---")

  # Charts demo usando color de marca
  # 1) Distribución Fit
  if total_cvs:
    bins = []
    jd = ss.get("last_jd_text","")
    preset = ROLE_PRESETS.get(ss.get("last_role",""), {})
    must, nice = preset.get("must",[]), preset.get("nice",[])
    for c in ss.candidates:
      txt=c.get("_text") or (c.get("_bytes") or b"").decode("utf-8","ignore")
      f,_=score_fit_by_skills(jd,must,nice,txt or "")
      bins.append("Alto (>=70)" if f>=70 else ("Medio (40-69)" if f>=40 else "Bajo (<40)"))
    df=pd.DataFrame({"Fit band":bins})
    fig=px.histogram(df, x="Fit band", title="Distribución de Fit por skills",
                     color_discrete_sequence=[PRIMARY])
    fig.update_layout(plot_bgcolor="#FFFFFF", paper_bgcolor="rgba(0,0,0,0)", font=dict(color=TITLE_DARK))
    st.plotly_chart(fig, use_container_width=True)

  # 2) Días abiertos por puesto
  dfp = ss.positions[["Puesto","Días Abierto"]].copy()
  fig2 = px.bar(dfp, x="Puesto", y="Días Abierto", title="Días abiertos por puesto",
                color_discrete_sequence=[PRIMARY])
  fig2.update_layout(plot_bgcolor="#FFFFFF", paper_bgcolor="rgba(0,0,0,0)", font=dict(color=TITLE_DARK), xaxis_tickangle=-20)
  st.plotly_chart(fig2, use_container_width=True)

  # 3) Top skills detectadas
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
