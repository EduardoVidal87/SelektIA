# app.py
# -*- coding: utf-8 -*-

import io, base64, re, json, random, zipfile
from xml.etree import ElementTree as ET
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
SIDEBAR_BG = "#0E192B"
SIDEBAR_TX = "#B9C7DF"
BODY_BG    = "#F7FBFF"
CARD_BG    = "#0E192B"
TITLE_DARK = "#142433"
BAR_DEFAULT = "#E9F3FF"
BAR_GOOD    = "#33FFAC"

DEPARTMENTS = ["Tecnología","Marketing","Operaciones","Finanzas","RR.HH.","Atención al cliente","Ventas","Salud"]
EMP_TYPES   = ["Tiempo completo","Medio tiempo","Prácticas","Temporal","Consultoría"]
SENIORITIES = ["Junior","Semi Senior","Senior","Lead","Manager","Director"]
WORK_MODELS = ["Presencial","Híbrido","Remoto"]
SHIFTS      = ["Diurno","Nocturno","Rotativo"]
PRIORITIES  = ["Alta","Media","Baja"]
CURRENCIES  = ["USD","PEN","EUR","CLP","MXN","COP","ARS"]
JOB_BOARDS  = ["laborum.pe","Computrabajo","Bumeran","Indeed","LinkedIn Jobs"]

EVAL_INSTRUCTION = (
  "Debes analizar los CVs de postulantes y calificarlos de 0% a 100% según el nivel de coincidencia con el JD. "
  "Incluye un análisis breve que explique por qué califica o no el postulante, destacando habilidades must-have, "
  "nice-to-have, brechas y hallazgos relevantes."
)

AGENT_DEFAULT_IMAGES = {
  "Headhunter":        "https://images.unsplash.com/photo-1581090464777-f3220bbe1b8b?q=80&w=512&auto=format&fit=crop",
  "Coordinador RR.HH.":"https://images.unsplash.com/photo-1542751371-adc38448a05e?q=80&w=512&auto=format&fit=crop",
  "Admin RR.HH.":      "https://images.unsplash.com/photo-1526378722484-bd91ca387e72?q=80&w=512&auto=format&fit=crop",
}
LLM_MODELS = ["gpt-4o-mini","gpt-4.1","gpt-4o","claude-3.5-sonnet","claude-3-haiku","gemini-1.5-pro","mixtral-8x7b","llama-3.1-70b"]

# ===== Presets de puestos (resumen) =====
ROLE_PRESETS = {
  "Asistente Administrativo": {
    "jd": "Brindar soporte administrativo: gestión documental, agenda, compras menores, logística de reuniones y reportes…",
    "keywords": "Excel, Word, PowerPoint, gestión documental, atención a proveedores, compras, logística, caja chica, facturación, redacción",
    "must": ["Excel","Gestión documental","Redacción"], "nice": ["Facturación","Caja"],
    "synth_skills": ["Excel","Word","PowerPoint","Gestión documental","Redacción","Facturación","Caja","Atención al cliente"]
  },
  "Business Analytics": {
    "jd": "Recolectar, transformar y analizar datos para generar insights. Dashboards Power BI/Tableau, SQL avanzado…",
    "keywords": "SQL, Power BI, Tableau, ETL, KPI, storytelling, Excel avanzado, Python, A/B testing, métricas de negocio",
    "must": ["SQL","Power BI"], "nice": ["Tableau","Python","ETL"],
    "synth_skills": ["SQL","Power BI","Tableau","Excel","ETL","KPIs","Storytelling","Python","A/B testing"]
  },
  "Diseñador/a UX": {
    "jd": "Research, flujos, wireframes y prototipos. Figma, heurísticas, accesibilidad y design systems…",
    "keywords": "Figma, UX research, prototipado, wireframes, heurísticas, accesibilidad, design system, usabilidad, tests con usuarios",
    "must": ["Figma","UX Research","Prototipado"], "nice":["Heurísticas","Accesibilidad","Design System"],
    "synth_skills":["Figma","UX Research","Prototipado","Wireframes","Accesibilidad","Heurísticas","Design System","Analytics"]
  },
  "Ingeniero/a de Proyectos": {
    "jd":"Planificar, ejecutar y controlar proyectos. MS Project, AutoCAD/BIM, presupuestos, riesgos. PMBOK/Agile…",
    "keywords":"MS Project, AutoCAD, BIM, presupuestos, cronogramas, control de cambios, riesgos, PMBOK, Agile, KPI, licitaciones",
    "must":["MS Project","AutoCAD","Presupuestos"], "nice":["BIM","PMBOK","Agile"],
    "synth_skills":["MS Project","AutoCAD","BIM","Presupuestos","Cronogramas","Riesgos","PMBOK","Agile","Excel","Power BI"]
  },
  "Enfermera/o Asistencial": {
    "jd":"Atención segura y de calidad… registrar en HIS / SAP IS-H… BLS/ACLS vigentes.",
    "keywords":"HIS, SAP IS-H, BLS, ACLS, IAAS, educación al paciente, seguridad del paciente, protocolos, triage, signos vitales, curaciones, vía periférica, administración de medicamentos, registro clínico",
    "must":["HIS","BLS","ACLS","IAAS","Seguridad del paciente"], "nice":["SAP IS-H","Educación al paciente","Protocolos"],
    "synth_skills":["HIS","BLS","ACLS","IAAS","Educación al paciente","Seguridad del paciente","Protocolos","Excel"]
  },
}

# =========================================================
# CSS
# =========================================================
CSS = f"""
:root {{ --green:{PRIMARY}; --sb-bg:{SIDEBAR_BG}; --sb-tx:{SIDEBAR_TX}; --body:{BODY_BG}; --sb-card:{CARD_BG}; }}
html, body, [data-testid="stAppViewContainer"] {{ background:var(--body)!important; }}
.block-container {{ background:transparent!important; padding-top:1.25rem!important; }}

/* Sidebar */
[data-testid="stSidebar"] {{ background:var(--sb-bg)!important; color:var(--sb-tx)!important; }}
[data-testid="stSidebar"] * {{ color:var(--sb-tx)!important; }}
.sidebar-brand{{display:flex;flex-direction:column;align-items:center;justify-content:center;margin-top:-10px;top:-2px;position:relative}}
.sidebar-brand .brand-title{{color:var(--green)!important;font-weight:800!important;font-size:44px!important;line-height:1.05!important}}
.sidebar-brand .brand-sub{{margin-top:2px!important;color:var(--green)!important;font-size:11.5px!important;opacity:.95!important}}
[data-testid="stSidebar"] h1,[data-testid="stSidebar"] h2,[data-testid="stSidebar"] h3,[data-testid="stSidebar"] h4,[data-testid="stSidebar"] h5,[data-testid="stSidebar"] h6{{color:var(--green)!important;letter-spacing:.5px;margin:12px 10px 6px!important;line-height:1.05!important}}
[data-testid="stSidebar"] .stButton>button{{width:100%!important;display:flex!important;justify-content:flex-start!important;gap:8px!important;background:var(--sb-card)!important;border:1px solid var(--sb-bg)!important;color:#fff!important;border-radius:12px!important;padding:9px 12px!important;margin:6px 8px!important;font-weight:600!important}}

/* Body buttons */
.block-container .stButton>button{{background:var(--green)!important;color:#082017!important;border-radius:10px!important;border:none!important;padding:.5rem .9rem!important;font-weight:700!important}}
.block-container .stButton>button:hover{{filter:brightness(.96)}}

/* Headings */
h1,h2,h3{{color:{TITLE_DARK};}} h1 strong,h2 strong,h3 strong{{color:var(--green)}}

/* Inputs */
.block-container [data-testid="stSelectbox"]>div>div,
.block-container [data-baseweb="select"],
.block-container [data-testid="stTextInput"] input,
.block-container [data-testid="stTextArea"] textarea{{background:#F1F7FD!important;color:{TITLE_DARK}!important;border:1.5px solid #E3EDF6!important;border-radius:10px!important}}

/* Tables */
.block-container table{{background:#fff!important;border:1px solid #E3EDF6!important;border-radius:8px!important}}
.block-container thead th{{background:#F1F7FD!important;color:{TITLE_DARK}!important}}

/* Cards / Pills */
.k-card{{background:#fff;border:1px solid #E3EDF6;border-radius:12px;padding:14px}}
.badge{{display:inline-flex;align-items:center;gap:6px;background:#F1F7FD;border:1px solid #E3EDF6;border-radius:24px;padding:4px 10px;font-size:12px;color:#1B2A3C}}
.agent-wrap .stButton>button{{background:var(--body)!important;color:{TITLE_DARK}!important;border:1px solid #E3EDF6!important;border-radius:10px!important;font-weight:700!important;padding:6px 10px!important}}
.agent-wrap .stButton>button:hover{{background:#fff!important}}
.agent-detail{{background:#fff;border:2px solid #E3EDF6;border-radius:16px;padding:16px;box-shadow:0 6px 18px rgba(14,25,43,.08)}}
.agent-detail input:disabled, .agent-detail textarea:disabled{{background:#EEF5FF!important;color:{TITLE_DARK}!important;border:1.5px solid #D7E7FB!important;opacity:1!important}}

.match-chip{{display:inline-flex;align-items:center;gap:8px;border-radius:999px;padding:6px 12px;font-weight:700;font-size:12.5px;border:1px solid #E3EDF6;background:#F1F7FD;color:#1B2A3C}}
.match-dot{{width:10px;height:10px;border-radius:999px;display:inline-block}}
.match-strong{{background:#33FFAC}} .match-good{{background:#A7F3D0}} .match-ok{{background:#E9F3FF}}
.skill-pill{{display:inline-flex;align-items:center;gap:6px;margin:4px 6px 0 0;padding:6px 10px;border-radius:999px;border:1px solid #E3EDF6;background:#FFFFFF;color:#1B2A3C;font-size:12px}}
.skill-pill.checked{{background:#F1F7FD;border-color:#E3EDF6}}

/* Workflow */
.step-num{{width:26px;height:26px;border-radius:999px;border:2px solid #DDE7F5;display:flex;align-items:center;justify-content:center;font-weight:800;color:#345;}}
.step{{display:flex;gap:10px;align-items:center;margin:8px 0}}
.status-chip{{display:inline-flex;gap:8px;align-items:center;border:1px solid #E3EDF6;background:#F6FAFF;border-radius:999px;padding:4px 10px;font-size:12px}}
"""

st.set_page_config(page_title="SelektIA", page_icon="🧠", layout="wide")
st.markdown(f"<style>{CSS}</style>", unsafe_allow_html=True)

# =========================================================
# Persistencia (agentes + flujos)
# =========================================================
DATA_DIR = Path("data"); DATA_DIR.mkdir(exist_ok=True)
AGENTS_FILE = DATA_DIR/"agents.json"
WORKFLOWS_FILE = DATA_DIR/"workflows.json"

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
# Estado
# =========================================================
ss = st.session_state
if "section" not in ss: ss.section = "def_carga"
if "tasks" not in ss: ss.tasks = []
if "candidates" not in ss: ss.candidates = []
if "offers" not in ss: ss.offers = {}
if "agents_loaded" not in ss:
  ss.agents = load_agents()
  ss.agents_loaded = True
if "workflows_loaded" not in ss:
  ss.workflows = load_workflows()
  ss.workflows_loaded = True
if "agent_view_open" not in ss: ss.agent_view_open = {}
if "agent_edit_open" not in ss: ss.agent_edit_open = {}

# =========================================================
# Skills + Utils
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
  st.components.v1.html(f'<embed src="data:application/pdf;base64,{b64}" type="application/pdf" width="100%" height="{height}px"/>', height=height)

def _extract_docx_bytes(b: bytes) -> str:
  try:
    with zipfile.ZipFile(io.BytesIO(b)) as z:
      xml = z.read("word/document.xml").decode("utf-8", "ignore")
      # texto simple
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
def simple_score(cv_text, jd, keywords):
  base=0; reasons=[]; t=cv_text.lower()
  kws=[k.strip().lower() for k in (keywords or "").split(",") if k.strip()]
  hits=sum(1 for k in kws if k in t)
  if kws: base+=int((hits/len(kws))*70); reasons.append(f"{hits}/{len(kws)} keywords encontradas")
  base=max(0,min(100,base)); return base, " — ".join(reasons)

# =========================================================
# Sidebar
# =========================================================
with st.sidebar:
  st.markdown("""<div class="sidebar-brand"><div class="brand-title">SelektIA</div><div class="brand-sub">Powered by Wayki Consulting</div></div>""", unsafe_allow_html=True)
  st.markdown("#### DASHBOARD"); 
  if st.button("Analytics", key="sb_analytics"): ss.section="analytics"
  st.markdown("#### ASISTENTE IA")
  for txt,sec in [("Flujos","flows"),("Agentes","agents"),("Tareas de Agente","agent_tasks")]:
    if st.button(txt, key=f"sb_{sec}"): ss.section=sec
  st.markdown("#### PROCESO DE SELECCIÓN")
  for txt,sec in [("Definición & Carga","def_carga"),("Puestos","puestos"),("Evaluación de CVs","eval"),("Pipeline de Candidatos","pipeline"),("Entrevista (Gerencia)","interview"),("Tareas del Headhunter","hh_tasks"),("Oferta","offer"),("Onboarding","onboarding")]:
    if st.button(txt, key=f"sb_{sec}"): ss.section=sec
  st.markdown("#### ACCIONES")
  if st.button("Crear tarea", key="sb_task"): ss.section="create_task"

# =========================================================
# PÁGINAS (se muestran completas las relevantes al flujo)
# =========================================================

# -------------------- AGENTES (igual que última entrega, recortado) --------------------
def page_agents():
  st.header("Agentes")
  st.markdown("### Tus agentes")
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
          img=ag.get("image") or AGENT_DEFAULT_IMAGES.get(ag.get("rol","Headhunter"))
          st.markdown(f"""
          <div style="background:#fff;border:1px solid #E3EDF6;border-radius:16px;padding:16px;text-align:center;">
            <img src="{img}" style="width:120px;height:120px;border-radius:999px;object-fit:cover;border:4px solid #F1F7FD;">
            <div style="height:8px"></div>
            <div style="font-weight:800;color:{TITLE_DARK};font-size:18px">{ag.get('rol','—')}</div>
            <div style="font-size:13px;opacity:.8;margin-top:6px">{ag.get('objetivo','—')}</div>
          </div>""", unsafe_allow_html=True)

          st.markdown('<div class="agent-wrap">', unsafe_allow_html=True)
          c1,c2,c3,c4=st.columns([1,1,1,1])
          with c1:
            is_open=ss.agent_view_open.get(idx, False)
            if st.button(("👁 Ocultar" if is_open else "👁 Ver"), key=f"ag_view_{idx}"):
              ss.agent_view_open[idx]=not is_open; st.rerun()
          with c2:
            is_edit=ss.agent_edit_open.get(idx, False)
            if st.button(("✏ Ocultar" if is_edit else "✏ Edit"), key=f"ag_edit_{idx}"):
              ss.agent_edit_open[idx]=not is_edit; st.rerun()
          with c3:
            if st.button("🧬 Clone", key=f"ag_clone_{idx}"):
              clone=dict(ag); clone["rol"]=f"{ag.get('rol','Agente')} (copia)"
              ss.agents.append(clone); save_agents(ss.agents); st.success("Agente clonado."); st.rerun()
          with c4:
            if st.button("🗑 Del", key=f"ag_del_{idx}"):
              ss.agents.pop(idx); save_agents(ss.agents); st.success("Agente eliminado."); st.rerun()
          st.markdown('</div>', unsafe_allow_html=True)

        if ss.agent_view_open.get(idx, False):
          st.subheader("Detalle del agente")
          st.markdown('<div class="agent-detail">', unsafe_allow_html=True)
          c1,c2=st.columns([0.42,0.58])
          with c1:
            st.image(img, width=200)
            st.caption("Modelo LLM (simulado)")
            st.markdown(f"<div class='badge'>🧠 {ag.get('llm_model','gpt-4o-mini')}</div>", unsafe_allow_html=True)
          with c2:
            st.text_input("Role*", value=ag.get("rol",""), disabled=True)
            st.text_input("Goal*", value=ag.get("objetivo",""), disabled=True)
            st.text_area("Backstory*", value=ag.get("backstory",""), height=160, disabled=True)
            st.text_area("Guardrails", value=ag.get("guardrails",""), height=90, disabled=True)
            st.caption("Herramientas habilitadas"); st.write(", ".join(ag.get("herramientas",[])) or "—")
          st.markdown('</div>', unsafe_allow_html=True)

  st.markdown("---")
  st.subheader("Crear / Editar agente")
  with st.form("agent_form"):
    rol_opts=["Headhunter","Coordinador RR.HH.","Admin RR.HH."]
    rol = st.selectbox("Rol*", rol_opts, index=0)
    objetivo  = st.text_input("Objetivo*", "Identificar a los mejores profesionales para el cargo definido en el JD")
    backstory = st.text_area("Backstory*", "Eres un analista de RR.HH. con experiencia en análisis de documentos, CV y currículums.", height=120)
    guardrails= st.text_area("Guardrails", "No compartas datos sensibles. Cita la fuente (CV o JD) al argumentar.", height=90)
    herramientas = st.multiselect("Herramientas habilitadas", ["Parser de PDF","Recomendador de skills","Comparador JD-CV"], default=["Parser de PDF","Recomendador de skills"])
    llm_model   = st.selectbox("Modelo LLM (simulado)", LLM_MODELS, index=0)
    default_img = AGENT_DEFAULT_IMAGES.get(rol, "")
    img_src     = st.text_input("URL de imagen (opcional)", value=default_img)
    if st.form_submit_button("Guardar/Actualizar Agente"):
      ss.agents.append({"rol":rol,"objetivo":objetivo,"backstory":backstory,"guardrails":guardrails,"herramientas":herramientas,"llm_model":llm_model,"image":img_src,"ts":datetime.utcnow().isoformat()})
      save_agents(ss.agents); st.success("Agente guardado."); st.rerun()

# -------------------- FLUJOS (Workflows) --------------------
def page_flows():
  st.header("Flujos")

  # Vista como (control humano)
  view_role = st.selectbox("Vista como", ["Colaborador","Administrador","Gerente"], index=0, help="Define permisos para aprobar")
  is_approver = view_role in ("Administrador","Gerente")

  # Bandeja de flujos
  st.markdown("### Mis flujos")
  left, right = st.columns([0.9, 1.1])

  with left:
    if not ss.workflows:
      st.info("Aún no hay flujos. Crea uno a la derecha.")
    else:
      items = []
      for wf in ss.workflows:
        items.append({
          "ID": wf["id"], "Nombre": wf["name"],
          "Puesto": wf.get("role","—"),
          "Agente": (ss.agents[wf["agent_idx"]]["rol"] if (0 <= wf.get("agent_idx",-1) < len(ss.agents)) else "—"),
          "Estado": wf.get("status","Borrador"),
          "Programado": wf.get("schedule_at","—")
        })
      df = pd.DataFrame(items)
      st.dataframe(df, use_container_width=True, height=260)

      # Selección
      wf_ids = [x["ID"] for x in items]
      if wf_ids:
        sel = st.selectbox("Selecciona un flujo", wf_ids, format_func=lambda x: f"{x} — {next((i['Nombre'] for i in items if i['ID']==x),'')}")
        ss["selected_wf_id"] = sel

        # Acciones rápidas
        c1,c2,c3 = st.columns(3)
        with c1:
          if st.button("🧬 Duplicar"):
            wf = next((w for w in ss.workflows if w["id"]==sel), None)
            if wf:
              clone = dict(wf); clone["id"] = f"WF-{int(datetime.now().timestamp())}"
              clone["status"]="Borrador"; clone["approved_by"]=""
              ss.workflows.insert(0, clone); save_workflows(ss.workflows); st.success("Flujo duplicado."); st.rerun()
        with c2:
          if st.button("🗑 Eliminar"):
            ss.workflows = [w for w in ss.workflows if w["id"]!=sel]; save_workflows(ss.workflows)
            st.success("Flujo eliminado."); st.rerun()
        with c3:
          wf = next((w for w in ss.workflows if w["id"]==sel), None)
          if wf:
            st.markdown(f"<div class='status-chip'>Estado: <b>{wf.get('status','Borrador')}</b></div>", unsafe_allow_html=True)
            if wf.get("status")=="Pendiente de aprobación" and is_approver:
              a1,a2=st.columns(2)
              with a1:
                if st.button("✅ Aprobar"):
                  wf["status"]="Aprobado"; wf["approved_by"]=view_role; wf["approved_at"]=datetime.now().isoformat()
                  save_workflows(ss.workflows); st.success("Aprobado."); st.rerun()
              with a2:
                if st.button("❌ Rechazar"):
                  wf["status"]="Rechazado"; wf["approved_by"]=view_role; wf["approved_at"]=datetime.now().isoformat()
                  save_workflows(ss.workflows); st.warning("Rechazado."); st.rerun()

  # Constructor
  with right:
    st.markdown("### Crear / Editar flujo")
    with st.form("wf_form"):
      # Paso 1 — Task
      st.markdown("<div class='step'><div class='step-num'>1</div><div><b>Task</b><br><span style='opacity:.75'>Describe la tarea</span></div></div>", unsafe_allow_html=True)
      name = st.text_input("Name*", value="Analizar CV")
      role = st.selectbox("Puesto objetivo", list(ROLE_PRESETS.keys()), index=2)
      desc = st.text_area("Description*", value=EVAL_INSTRUCTION, height=110)
      expected = st.text_area("Expected output*", value="- Puntuación 0 a 100 según coincidencia con JD\n- Análisis resumido del CV explicando por qué califica o no", height=80)

      st.markdown("**Job Description (elige una opción)**")
      jd_text = st.text_area("JD en texto", value=ROLE_PRESETS[role]["jd"], height=140)
      jd_file = st.file_uploader("…o sube JD en PDF/TXT/DOCX", type=["pdf","txt","docx"], key="wf_jd_file")
      jd_from_file = ""
      if jd_file is not None:
        jd_from_file = extract_text_from_file(jd_file)
        st.caption("Vista previa del JD extraído (solo texto):")
        st.text_area("Preview", jd_from_file[:4000], height=160)

      st.markdown("---")
      # Paso 2 — Staff in charge
      st.markdown("<div class='step'><div class='step-num'>2</div><div><b>Staff in charge</b><br><span style='opacity:.75'>Agente asignado</span></div></div>", unsafe_allow_html=True)
      agent_names = [f"{i} — {a.get('rol','Agente')} ({a.get('llm_model','model')})" for i,a in enumerate(ss.agents)] or ["—"]
      if ss.agents:
        agent_pick = st.selectbox("Asigna un agente", agent_names, index=0)
        agent_idx = int(agent_pick.split(" — ")[0])
      else:
        st.info("No hay agentes. Crea uno en la pestaña **Agentes**.")
        agent_idx = -1

      st.markdown("---")
      # Paso 3 — Save & Schedule
      st.markdown("<div class='step'><div class='step-num'>3</div><div><b>Guardar</b><br><span style='opacity:.75'>Aprobación y programación</span></div></div>", unsafe_allow_html=True)
      run_date = st.date_input("Fecha de ejecución", value=date.today()+timedelta(days=1))
      run_time = st.time_input("Hora de ejecución", value=datetime.now().time().replace(second=0, microsecond=0))
      action_col1, action_col2, action_col3 = st.columns(3)
      save_draft = action_col1.form_submit_button("💾 Guardar borrador")
      send_approval = action_col2.form_submit_button("📝 Enviar a aprobación")
      schedule = action_col3.form_submit_button("📅 Guardar y Programar")

    # Lógica de guardado
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
          "jd_text": jd_final[:200000],  # guardamos texto extraído
          "agent_idx": agent_idx,
          "created_at": datetime.now().isoformat(),
          "status": "Borrador",
          "approved_by": "", "approved_at": "",
          "schedule_at": ""
        }
        if send_approval:
          wf["status"] = "Pendiente de aprobación"
          st.success("Flujo enviado a aprobación. Un Administrador/Gerente debe aprobarlo.")
        if schedule:
          # Solo si aprobado
          wf["status"] = "Programado" if is_approver else "Pendiente de aprobación"
          wf["schedule_at"] = f"{run_date} {run_time.strftime('%H:%M')}"
          if not is_approver:
            st.info("Se guardó y quedó **Pendiente de aprobación**. Un Administrador/Gerente debe aprobar para ejecutar.")
          else:
            st.success("Flujo programado.")
        if save_draft:
          st.success("Borrador guardado.")

        ss.workflows.insert(0, wf)
        save_workflows(ss.workflows)
        st.rerun()

  # Ayuda
  st.markdown("---")
  st.caption("Notas: este módulo **simula** la lectura del JD y la asignación al agente. No ejecuta IA real; al aprobar/programar solo se guarda el flujo.")

# -------------------- Otras páginas (resumen) --------------------
def page_def_carga():
  st.header("Definición & Carga")
  roles=list(ROLE_PRESETS.keys()); role=st.selectbox("Puesto", roles, index=2)
  jd_text=st.text_area("Descripción / JD", height=180, value=ROLE_PRESETS[role]["jd"])
  kw_text=st.text_area("Palabras clave (coma separada)", height=100, value=ROLE_PRESETS[role]["keywords"])
  ss["last_role"]=role; ss["last_jd_text"]=jd_text; ss["last_kw_text"]=kw_text
  files=st.file_uploader("Subir CVs (PDF/TXT/DOCX)", type=["pdf","txt","docx"], accept_multiple_files=True)
  if files and st.button("Procesar CVs cargados"):
    ss.candidates=[]
    for f in files:
      b=f.read(); f.seek(0)
      txt=extract_text_from_file(f)
      score,_=simple_score(txt,jd_text,kw_text)
      ss.candidates.append({"Name":f.name,"Score":score,"Reasons":"","_bytes":b,"_is_pdf":Path(f.name).suffix.lower()==".pdf","_text":txt,"meta":extract_meta(txt)})
    st.success("CVs cargados y analizados."); st.rerun()

def page_eval(): st.header("Resultados de evaluación"); st.info("Usa el módulo previo enviado (omitido aquí por brevedad).")
def page_pipeline(): st.header("Pipeline de Candidatos"); st.info("Usa el módulo previo enviado (omitido aquí por brevedad).")
def page_interview(): st.header("Entrevista (Gerencia)"); st.write("Use la rúbrica (demo).")
def page_offer(): st.header("Oferta"); st.write("Gestión de oferta (demo).")
def page_onboarding(): st.header("Onboarding"); st.write("Checklist (demo).")
def page_puestos(): st.header("Puestos"); st.write("Vista de puestos (demo).")
def page_agent_tasks(): st.header("Tareas de Agente"); st.write("Bandeja de tareas (demo).")
def page_analytics(): st.header("Analytics"); st.write("Panel (demo).")
def page_create_task():
  st.header("Crear tarea")
  with st.form("t_form"):
    t=st.text_input("Título"); d=st.text_area("Descripción", height=150); due=st.date_input("Fecha límite", value=date.today())
    if st.form_submit_button("Guardar"): st.success("Tarea creada.")

# =========================================================
ROUTES = {
  "def_carga": page_def_carga, "puestos": page_puestos, "eval": page_eval, "pipeline": page_pipeline,
  "interview": page_interview, "offer": page_offer, "onboarding": page_onboarding, "hh_tasks": page_agent_tasks,
  "agents": page_agents, "flows": page_flows, "agent_tasks": page_agent_tasks, "analytics": page_analytics,
  "create_task": page_create_task,
}
ROUTES.get(ss.section, page_def_carga)()
