# app.py
# -*- coding: utf-8 -*-

import io
import base64
import re
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

# Instrucción tipo “asistente” para la Ficha de Evaluación
EVAL_INSTRUCTION = (
  "Debes analizar los CVs de postulantes y calificarlos de 0% a 100% según el nivel de coincidencia con el JD. "
  "Incluye un análisis breve que explique por qué califica o no el postulante, destacando habilidades must-have, "
  "nice-to-have, brechas y hallazgos relevantes."
)

# =========================================================
# CSS — (botones a la IZQUIERDA + branding alineado)
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
"""

# Chips/badges de match + pills de skills
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
# ESTADO
# =========================================================
ss = st.session_state
if "section" not in ss: ss.section = "def_carga"
if "tasks" not in ss: ss.tasks = []
if "candidates" not in ss: ss.candidates = []
if "offers" not in ss: ss.offers = {}
if "agents" not in ss: ss.agents = []
if "positions" not in ss:
  ss.positions = pd.DataFrame([
      {"ID":"10,645,194","Puesto":"Desarrollador/a Backend (Python)","Días Abierto":3,
       "Leads":1800,"Nuevos":115,"Recruiter Screen":35,"HM Screen":7,
       "Entrevista Telefónica":14,"Entrevista Presencial":15,"Ubicación":"Lima, Perú",
       "Hiring Manager":"Rivers Brykson","Estado":"Abierto",
       "Experiencia Min":3,"MustHave":"Python, APIs REST, SQL","NiceToHave":"AWS, Docker","JD":"Construcción de APIs y servicios backend."},
      {"ID":"10,376,415","Puesto":"VP de Marketing","Días Abierto":28,
       "Leads":8100,"Nuevos":1,"Recruiter Screen":15,"HM Screen":35,
       "Entrevista Telefónica":5,"Entrevista Presencial":7,"Ubicación":"Santiago, Chile",
       "Hiring Manager":"Angela Cruz","Estado":"Abierto",
       "Experiencia Min":8,"MustHave":"Performance, SEO, CRM","NiceToHave":"B2B SaaS, RevOps","JD":"Liderar estrategia de marketing y crecimiento."},
      {"ID":"10,376,646","Puesto":"Planner de Demanda","Días Abierto":28,
       "Leads":2300,"Nuevos":26,"Recruiter Screen":3,"HM Screen":8,
       "Entrevista Telefónica":6,"Entrevista Presencial":3,"Ubicación":"Ciudad de México, MX",
       "Hiring Manager":"Rivers Brykson","Estado":"Abierto",
       "Experiencia Min":4,"MustHave":"Forecasting, Excel, SQL","NiceToHave":"Python, Power BI","JD":"Planificación de la demanda y análisis de inventario."}
  ])

# =========================================================
# TAXONOMÍA DE SKILLS (demo sin IA)
# =========================================================
SKILL_SYNONYMS = {
  # Clínico / hospitalario
  "HIS": ["his", "hospital information system"],
  "SAP IS-H": ["sap is-h", "sap is h", "sap hospital"],
  "BLS": ["bls", "basic life support"],
  "ACLS": ["acls", "advanced cardiac life support"],
  "IAAS": ["iaas", "infecciones asociadas a la atención", "infecciones nosocomiales"],
  "Educación al paciente": ["educación al paciente", "patient education"],
  "Seguridad del paciente": ["seguridad del paciente", "patient safety"],
  "Protocolos": ["protocolos", "protocol"],
  # Tech genéricas
  "Python": ["python"],
  "APIs REST": ["api rest", "apis rest", "rest api", "restful"],
  "SQL": ["sql", "postgres", "mysql", "t-sql"],
  "Docker": ["docker", "containers"],
  "AWS": ["aws", "amazon web services"],
  "Power BI": ["power bi"],
  "Excel": ["excel", "xlsx"],
  "Forecasting": ["forecasting", "pronóstico", "demand planning", "planificación de la demanda"],
  # Marketing
  "SEO": ["seo", "search engine optimization"],
  "CRM": ["crm", "salesforce", "hubspot"],
  "Performance": ["performance marketing", "paid media", "sem", "ads", "campañas"],
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
    try: years = max(years, int(m.group(1)))
    except: pass
  if years == 0 and ("años" in text_low or "experiencia" in text_low or "years" in text_low):
    years = 5
  return years

def extract_meta(cv_text: str) -> dict:
  text_low = cv_text.lower()
  universidad = ""
  uni_match = re.search(r'(universidad|university)\s+([^\n,;]+)', text_low)
  if uni_match: universidad = (uni_match.group(0) or "").strip().title()
  anios_exp = _max_years(text_low)
  titulo = ""
  for key in ["licenciado", "bachiller", "ingeniero", "enfermera", "enfermero", "qu\u00edmico", "m\u00e9dico", "tecn\u00f3logo"]:
    if key in text_low: titulo = key.title(); break
  ubicacion = ""
  ciudades = ["lima","santiago","bogot\u00e1","ciudad de m\u00e9xico","mexico city","quito","buenos aires","montevideo","la paz"]
  for c in ciudades:
    if c in text_low: ubicacion = c.title(); break
  return {
    "universidad": universidad or "—",
    "anios_exp": anios_exp,
    "titulo": titulo or "—",
    "ubicacion": ubicacion or "—",
    "ultima_actualizacion": datetime.today().date().isoformat()
  }

def simple_score(cv_text: str, jd: str, keywords: str) -> tuple[int, str]:
  base = 0; reasons = []
  text_low = cv_text.lower(); jd_low = jd.lower()
  hits = 0; kws = [k.strip().lower() for k in keywords.split(",") if k.strip()]
  for k in kws:
    if k and k in text_low: hits += 1
  if kws:
    pct_k = hits/len(kws); base += int(pct_k*70)
    reasons.append(f"{hits}/{len(kws)} keywords encontradas — Coincidencias: {', '.join([k for k in kws if k in text_low])[:120]}")
  jd_terms = [t for t in set(jd_low.split()) if len(t) > 3]
  match_terms = sum(1 for t in jd_terms if t in text_low)
  if jd_terms:
    pct_jd = match_terms/len(jd_terms); base += int(pct_jd*30)
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

# ===== Portales (demo) =====
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
  text = _dummy_cv_text(query or "Profesional de Salud", location or "Lima")
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

# ====== Generación de 20 CVs de muestra (demo) ======
FIRST_NAMES = ["Ana","Bruno","Carla","Daniel","Elena","Fernando","Gabriela","Hugo","Irene","Javier","Karina","Luis","María","Nicolás","Olga","Pablo","Rocío","Sofía","Tomás","Valeria"]
LAST_NAMES  = ["Rojas","García","Quispe","Torres","Muñoz","Pérez","Salas","Vargas","Huamán","Ramírez","Castro","Mendoza","Flores","López","Fernández","Cortez","Ramos","Díaz","Campos","Navarro"]

def _synth_cv_text(role: str, pool_skills: list[str], city: str, years: int) -> str:
  picked = random.sample(pool_skills, k=min(len(pool_skills), random.randint(4,7)))
  txt = (
    f"Resumen profesional — {role} en {city}. "
    f"Experiencia: {years} años. Manejo de {', '.join(picked)}. "
    f"Universidad Nacional Mayor de San Marcos. Participación en proyectos de mejora continua y protocolos. "
    f"Certificaciones: BLS, ACLS. Responsabilidades: soporte, documentación y educación al paciente."
  )
  return txt

def generate_20_sample_cvs(jd_text: str) -> list[dict]:
  jd_sk = list(infer_skills(jd_text) or {"HIS","Protocolos","Educación al paciente","Seguridad del paciente","IAAS"})
  cities = ["Lima, Perú","Santiago, Chile","Bogotá, Colombia","Quito, Ecuador","Ciudad de México, MX"]
  role = "Profesional de Salud"
  out = []
  for i in range(20):
    name = f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"
    years = random.choice([1,2,3,4,5,6,7,8,10,12])
    city = random.choice(cities)
    text = _synth_cv_text(role, jd_sk + ["SAP IS-H","Excel","Power BI","SQL"], city, years)
    meta = extract_meta(text)
    meta["anios_exp"] = years
    file_name = f"CV_Muestra_{i+1:02d}_{name.replace(' ','_')}.txt"
    out.append({
      "Name": file_name,
      "Score": 0,  # se calcula el Fit real en evaluación/pipeline
      "Reasons": "",
      "_bytes": text.encode("utf-8"),
      "_is_pdf": False,
      "_text": text,
      "meta": meta
    })
  return out

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
  puesto = st.selectbox(
      "Puesto",
      ["Enfermera/o Asistencial", "Tecnólogo/a Médico", "Recepcionista de Admisión",
       "Médico/a General", "Químico/a Farmacéutico/a"],
      index=0
  )
  jd_text = st.text_area("Descripción / JD", height=180,
                         placeholder="Objetivo del puesto, responsabilidades, protocolos y habilidades deseadas.")
  kw_text = st.text_area("Palabras clave (coma separada)", height=100,
                         value="HIS, SAP IS-H, BLS, ACLS, IAAS, educación al paciente, seguridad del paciente, protocolos")
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
      qty = st.number_input("Cantidad por portal", min_value=1, max_value=20, value=5, step=1)
    with col2:
      search_q = st.text_input("Búsqueda", value="Enfermera/o Asistencial")
      location = st.text_input("Ubicación", value="Lima, Perú")
    with col3:
      posted_since = st.date_input("Publicado desde", value=date.today() - timedelta(days=15))
    st.caption("Nota: Integración simulada para demo (sin scraping real).")
    if st.button("Traer CVs (demo)"):
      imported = []
      for board in sources:
        for i in range(1, int(qty)+1):
          imported.append(_make_candidate_from_board(board, i, jd_text, kw_text, search_q, location))
      ss.candidates = (ss.candidates or []) + imported
      st.success(f"Importados {len(imported)} CVs simulados desde: {', '.join(sources)}.")

  with st.expander("🧪 Generar 20 CVs de muestra (demo)"):
    st.caption("Crea 20 CVs sintéticos para probar toda la app, con textos y habilidades variadas.")
    if st.button("Generar CVs de muestra"):
      ss.candidates = generate_20_sample_cvs(ss.get("last_jd_text",""))
      st.success("Se generaron 20 CVs de muestra.")

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
                             index=options.index(preselect) if preselect in options else 0,
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
        "Puesto": job_title, "Días Abierto": 0,
        "Leads": 0, "Nuevos": 0, "Recruiter Screen": 0, "HM Screen": 0,
        "Entrevista Telefónica": 0, "Entrevista Presencial": 0,
        "Ubicación": location, "Hiring Manager": hiring_manager or recruiter,
        "Estado": "Abierto",
        "Departamento": department, "Tipo Empleo": emp_type, "Seniority": seniority,
        "Modalidad": work_model, "Vacantes": openings, "Recruiter": recruiter,
        "Razón": reason, "Moneda": currency, "Salario Min": sal_min, "Salario Max": sal_max,
        "Turno": shift, "Idiomas": languages, "Educación": education,
        "Experiencia Min": years_exp, "Prioridad": priority,
        "Fecha Objetivo": str(target_date), "Expira": str(expiry_date),
        "Aprobadores": approvers, "JD": jd, "MustHave": must, "NiceToHave": nice,
        "Beneficios": benefits, "Screening Qs": screening, "Publicaciones": post_urls,
        "Requiere Aprobación": require_approval,
        "Estado Aprobación": approval_status,
        "Aprobado Por": approved_by if approval_status == "Aprobado" else "",
        "Fecha Aprobación": str(approval_date) if approval_status == "Aprobado" else "",
        "Notas Aprobación": approval_notes,
        "Estado Publicación": "Borrador", "Fecha Publicación": "", "Publicado En": ""
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
          st.info("Aprobado, pero no hay URLs de publicación. Quedó como 'Listo para publicar'.")
      else:
        new_row["Estado Publicación"] = "Pendiente de aprobación"
      ss.positions = pd.concat([pd.DataFrame([new_row]), ss.positions], ignore_index=True)
      st.success("Puesto creado.")

def page_eval():
  st.header("Resultados de evaluación")
  if not ss.candidates:
    st.info("Carga CVs en **Definición & Carga**.")
    return

  jd_text = ss.get("last_jd_text", "") or ""
  jd_text = st.text_area("JD para matching por skills (opcional)", jd_text, height=140)

  with st.expander("Configurar skills objetivo (opcional)"):
    c1, c2 = st.columns(2)
    with c1: must_default = st.text_area("Must-have (coma separada)", value="")
    with c2: nice_default = st.text_area("Nice-to-have (coma separada)", value="")
  must_list = [s.strip() for s in (must_default or "").split(",") if s.strip()]
  nice_list = [s.strip() for s in (nice_default or "").split(",") if s.strip()]

  enriched = []
  for cand in ss.candidates:
    cv_text = cand.get("_text") or (cand.get("_bytes") or b"").decode("utf-8","ignore")
    fit, explain = score_fit_by_skills(jd_text, must_list, nice_list, cv_text or "")
    enriched.append({
      "Name": cand["Name"], "Fit": fit,
      "Must (ok/total)": f"{len(explain['matched_must'])}/{explai

