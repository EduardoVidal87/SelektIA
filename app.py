# app.py
# -*- coding: utf-8 -*-

import io, base64, re, json, random
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

# ===== Presets de puestos (recortado para brevedad: mismos de la versión anterior) =====
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
:root {{
  --green:{PRIMARY}; --sb-bg:{SIDEBAR_BG}; --sb-tx:{SIDEBAR_TX}; --body:{BODY_BG}; --sb-card:{CARD_BG};
}}
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

/* Pills & cards */
.k-card{{background:#fff;border:1px solid #E3EDF6;border-radius:12px;padding:14px}}
.badge{{display:inline-flex;align-items:center;gap:6px;background:#F1F7FD;border:1px solid #E3EDF6;border-radius:24px;padding:4px 10px;font-size:12px;color:#1B2A3C}}

/* —— Agentes — ghost buttons + detail contrast —— */
.agent-wrap .stButton>button{{background:var(--body)!important;color:{TITLE_DARK}!important;border:1px solid #E3EDF6!important;border-radius:10px!important;font-weight:700!important;padding:6px 10px!important}}
.agent-wrap .stButton>button:hover{{background:#fff!important}}
.agent-detail{{background:#fff;border:2px solid #E3EDF6;border-radius:16px;padding:16px;box-shadow:0 6px 18px rgba(14,25,43,.08)}}
.agent-detail input:disabled, .agent-detail textarea:disabled{{background:#EEF5FF!important;color:{TITLE_DARK}!important;border:1.5px solid #D7E7FB!important;opacity:1!important}}

/* Match chips */
.match-chip{{display:inline-flex;align-items:center;gap:8px;border-radius:999px;padding:6px 12px;font-weight:700;font-size:12.5px;border:1px solid #E3EDF6;background:#F1F7FD;color:#1B2A3C}}
.match-dot{{width:10px;height:10px;border-radius:999px;display:inline-block}}
.match-strong{{background:#33FFAC}} .match-good{{background:#A7F3D0}} .match-ok{{background:#E9F3FF}}
.skill-pill{{display:inline-flex;align-items:center;gap:6px;margin:4px 6px 0 0;padding:6px 10px;border-radius:999px;border:1px solid #E3EDF6;background:#FFFFFF;color:#1B2A3C;font-size:12px}}
.skill-pill.checked{{background:#F1F7FD;border-color:#E3EDF6}}
"""

st.set_page_config(page_title="SelektIA", page_icon="🧠", layout="wide")
st.markdown(f"<style>{CSS}</style>", unsafe_allow_html=True)

# =========================================================
# Persistencia agentes
# =========================================================
DATA_DIR = Path("data"); DATA_DIR.mkdir(exist_ok=True)
AGENTS_FILE = DATA_DIR/"agents.json"

def load_agents():
  if AGENTS_FILE.exists():
    try: return json.loads(AGENTS_FILE.read_text(encoding="utf-8"))
    except: return []
  return []

def save_agents(agents: list):
  AGENTS_FILE.write_text(json.dumps(agents, ensure_ascii=False, indent=2), encoding="utf-8")

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
if "agent_view_open" not in ss: ss.agent_view_open = {}   # idx -> bool
if "agent_edit_open" not in ss: ss.agent_edit_open = {}   # idx -> bool

# =========================================================
# Skill taxonomía + helpers (igual a versión anterior, abreviado)
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
def extract_text_from_file(f):
  try:
    if Path(f.name).suffix.lower()==".pdf":
      reader=PdfReader(io.BytesIO(f.read())); txt=""; 
      for p in reader.pages: txt+=p.extract_text() or ""
      return txt
    return f.read().decode("utf-8","ignore")
  except Exception as e:
    st.error(f"Error al leer '{f.name}': {e}"); return ""
def _max_years(t): 
  t=t.lower(); years=0
  for m in re.finditer(r'(\d{{1,2}})\s*(años|year|years)', t):
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
# Sidebar (igual)
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
# Páginas (se muestran solo las modificadas respecto a tu petición: Agents)
# =========================================================

def page_agents():
  st.header("Agentes")

  # ---- GALERÍA ----
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

        # Vista detalle si está abierta
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

  # ---- FORM ALTA / EDICIÓN (persistente) ----
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
    ok = st.form_submit_button("Guardar/Actualizar Agente")
    if ok:
      ss.agents.append({"rol":rol,"objetivo":objetivo,"backstory":backstory,"guardrails":guardrails,"herramientas":herramientas,"llm_model":llm_model,"image":img_src,"ts":datetime.utcnow().isoformat()})
      save_agents(ss.agents)
      st.success("Agente guardado.")
      st.rerun()

def page_def_carga():
  st.header("Definición & Carga")
  roles=list(ROLE_PRESETS.keys()); role=st.selectbox("Puesto", roles, index=0)
  jd_text=st.text_area("Descripción / JD", height=180, value=ROLE_PRESETS[role]["jd"])
  kw_text=st.text_area("Palabras clave (coma separada)", height=100, value=ROLE_PRESETS[role]["keywords"])
  ss["last_role"]=role; ss["last_jd_text"]=jd_text; ss["last_kw_text"]=kw_text

  files=st.file_uploader("Subir CVs (PDF o TXT)", type=["pdf","txt"], accept_multiple_files=True)
  if files and st.button("Procesar CVs cargados"):
    ss.candidates=[]
    for f in files:
      b=f.read(); f.seek(0)
      txt=extract_text_from_file(f)
      score,_=simple_score(txt,jd_text,kw_text)
      ss.candidates.append({"Name":f.name,"Score":score,"Reasons":"","_bytes":b,"_is_pdf":Path(f.name).suffix.lower()==".pdf","_text":txt,"meta":extract_meta(txt)})
    st.success("CVs cargados y analizados."); st.rerun()

  with st.expander("🔌 Importar desde portales (demo)"):
    srcs=st.multiselect("Portales", JOB_BOARDS, default=["laborum.pe"]); qty=st.number_input("Cantidad por portal",1,30,6)
    search_q=st.text_input("Búsqueda", value=role); location=st.text_input("Ubicación", value="Lima, Perú")
    if st.button("Traer CVs (demo)"):
      for board in srcs:
        for i in range(1,int(qty)+1):
          txt=f"{role} — {search_q} en {location}. Experiencia 5 años. Excel, SQL, gestión documental."
          ss.candidates.append({"Name":f"{board}_Candidato_{i:02d}.txt","Score":60,"Reasons":"demo","_bytes":txt.encode(),"__":None,"_is_pdf":False,"_text":txt,"meta":extract_meta(txt)})
      st.success("Importados CVs simulados."); st.rerun()

def page_eval():
  st.header("Resultados de evaluación")
  if not ss.candidates:
    st.info("Carga o genera CVs en **Definición & Carga**."); return
  jd_text=st.text_area("JD para matching por skills (opcional)", ss.get("last_jd_text",""), height=140)
  preset=ROLE_PRESETS.get(ss.get("last_role",""), {})
  col1,col2=st.columns(2)
  with col1: must_default=st.text_area("Must-have (coma separada)", value=", ".join(preset.get("must",[])))
  with col2: nice_default=st.text_area("Nice-to-have (coma separada)", value=", ".join(preset.get("nice",[])))
  must=[s.strip() for s in (must_default or "").split(",") if s.strip()]
  nice=[s.strip() for s in (nice_default or "").split(",") if s.strip()]

  enriched=[]
  for c in ss.candidates:
    cv=c.get("_text") or (c.get("_bytes") or b"").decode("utf-8","ignore")
    fit,exp=score_fit_by_skills(jd_text,must,nice,cv or "")
    enriched.append({"Name":c["Name"],"Fit":fit,"Must (ok/total)":f"{len(exp['matched_must'])}/{exp['must_total']}",
                     "Nice (ok/total)":f"{len(exp['matched_nice'])}/{exp['nice_total']}",
                     "Extras":", ".join(exp["extras"])[:60],"_exp":exp,"_is_pdf":c["_is_pdf"],"_bytes":c["_bytes"],"_text":cv,"meta":c.get("meta",{})})
  df=pd.DataFrame(enriched).sort_values("Fit", ascending=False).reset_index(drop=True)
  st.subheader("Ranking por Fit de Skills")
  st.dataframe(df[["Name","Fit","Must (ok/total)","Nice (ok/total)","Extras"]], use_container_width=True, height=250)

  st.subheader("Detalle y explicación")
  sel=st.selectbox("Elige un candidato", df["Name"].tolist())
  row=df[df["Name"]==sel].iloc[0]; exp=row["_exp"]
  c1,c2=st.columns([1.1,0.9])
  with c1:
    fig=px.bar(pd.DataFrame([{"Candidato":row["Name"],"Fit":row["Fit"]}]), x="Candidato", y="Fit", title="Fit por skills")
    fig.update_traces(marker_color=BAR_GOOD if row["Fit"]>=60 else BAR_DEFAULT, hovertemplate="%{x}<br>Fit: %{y}%")
    fig.update_layout(plot_bgcolor="#FFFFFF", paper_bgcolor="rgba(0,0,0,0)", font=dict(color=TITLE_DARK), xaxis_title=None, yaxis_title="Fit")
    st.plotly_chart(fig, use_container_width=True)
    st.markdown("**Explicación**")
    st.markdown(f"- **Must-have:** {len(exp['matched_must'])}/{exp['must_total']}  \n  - ✓ " + ", ".join(exp["matched_must"]) if exp["matched_must"] else "- **Must-have:** 0")
    if exp["gaps_must"]: st.markdown("  - ✗ Faltantes: " + ", ".join(exp["gaps_must"]))
    st.markdown(f"- **Nice-to-have:** {len(exp['matched_nice'])}/{exp['nice_total']}")
    if exp["matched_nice"]: st.markdown("  - ✓ " + ", ".join(exp["matched_nice"]))
    if exp["gaps_nice"]: st.markdown("  - ✗ Faltantes: " + ", ".join(exp["gaps_nice"]))
    if exp["extras"]: st.markdown("- **Extras:** " + ", ".join(exp["extras"]))
  with c2:
    st.markdown("**CV (visor)**")
    if row["_is_pdf"]: pdf_viewer_embed(row["_bytes"], height=420)
    else: st.text_area("Contenido (TXT)", row["_text"], height=260)

def page_pipeline():
  st.header("Pipeline de Candidatos")
  if not ss.candidates:
    st.info("Primero carga o genera CVs en **Definición & Carga**."); return
  jd=ss.get("last_jd_text","")
  preset=ROLE_PRESETS.get(ss.get("last_role",""), {})
  must, nice = preset.get("must",[]), preset.get("nice",[])
  ranked=[]
  for c in ss.candidates:
    txt=c.get("_text") or (c.get("_bytes") or b"").decode("utf-8","ignore")
    fit,ex=score_fit_by_skills(jd,must,nice,txt or "")
    ranked.append((fit,c,ex))
  ranked.sort(key=lambda x:x[0], reverse=True)

  c1,c2=st.columns([1.2,1])
  with c1:
    table=[{"Candidato":c["Name"],"Fit":fit,"Años Exp.":c.get("meta",{}).get("anios_exp",0),"Actualizado":c.get("meta",{}).get("ultima_actualizacion","—")} for fit,c,_ in ranked]
    df=pd.DataFrame(table).sort_values(["Fit","Años Exp."], ascending=[False,False])
    st.dataframe(df, use_container_width=True, height=300)
    names=df["Candidato"].tolist(); pre=ss.get("selected_cand", names[0] if names else "")
    sel=st.radio("Selecciona un candidato", names, index=names.index(pre) if pre in names else 0); ss["selected_cand"]=sel
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

def page_flows(): st.header("Flujos"); st.write("Define y documenta flujos (demo).")
def page_agent_tasks(): st.header("Tareas de Agente"); st.write("Bandeja de tareas para asistentes (demo).")
def page_interview(): st.header("Entrevista (Gerencia)"); st.write("Use la rúbrica (demo).")
def page_offer(): st.header("Oferta"); st.write("Gestión de oferta (demo).")
def page_onboarding(): st.header("Onboarding"); st.write("Checklist (demo).")
def page_puestos(): st.header("Puestos"); st.write("Vista de puestos (sin cambios sustanciales en esta entrega).")
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
