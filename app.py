# app.py
# -*- coding: utf-8 -*-

import io
import base64
from pathlib import Path
from datetime import datetime, date, timedelta

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

# =========================================================
# CSS — (botones siempre a la IZQUIERDA + branding alineado)
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

/* Branding (logo centrado, grande y alineado con títulos del cuerpo) */
.sidebar-brand {{
  display:flex; flex-direction:column;
  align-items:center; justify-content:center;
  padding: 0 0 2px;
  margin-top: 14px;                 /* alinea la altura del logo con los títulos del cuerpo */
  text-align:center;
}}
.sidebar-brand .brand-title {{
  color: var(--green) !important;
  font-weight: 800 !important;
  font-size: 44px !important;       /* LOGO grande */
  line-height: 1.05 !important;
}}
.sidebar-brand .brand-sub {{
  margin-top: 2px !important;
  color: var(--green) !important;   /* mismo color del logo */
  font-size: 11.5px !important;
  opacity: .95 !important;
}}
@media (min-height: 800px) {{
  .sidebar-brand {{ margin-top: 18px; }}
}}

/* Títulos de sección del sidebar (verde) + compacidad */
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3,
[data-testid="stSidebar"] h4,
[data-testid="stSidebar"] h5,
[data-testid="stSidebar"] h6 {{
  color: var(--green) !important;
  letter-spacing: .5px;
  margin: 12px 10px 6px !important;   /* menos espacio */
  line-height: 1.05 !important;
}}

/* Botones del sidebar (texto a la izquierda y compactos) */
[data-testid="stSidebar"] .stButton > button {{
  width: 100% !important;
  display: flex !important;
  justify-content: flex-start !important;  /* IZQUIERDA */
  align-items: center !important;
  text-align: left !important;
  gap: 8px !important;

  background: var(--sb-card) !important;
  border: 1px solid var(--sb-bg) !important;  /* borde mismo color del panel */
  color: #ffffff !important;
  border-radius: 12px !important;
  padding: 9px 12px !important;              /* más compacto */
  margin: 6px 8px !important;                /* menor separación vertical */
  font-weight: 600 !important;
}}
[data-testid="stSidebar"] .stButton > button * {{
  text-align: left !important;
}}

/* ====== CUERPO: Botones alineados a la izquierda ====== */
.block-container .stButton > button {{
  width: auto !important;
  display: flex !important;
  justify-content: flex-start !important;  /* IZQUIERDA */
  align-items: center !important;
  text-align: left !important;

  background: var(--green) !important;
  color: #082017 !important;
  border-radius: 10px !important;
  border: none !important;
  padding: .50rem .90rem !important;
  font-weight: 700 !important;
}}
.block-container .stButton > button:hover {{
  filter: brightness(.96);
}}

/* Títulos del cuerpo */
h1, h2, h3 {{
  color: {TITLE_DARK};
}}
h1 strong, h2 strong, h3 strong {{
  color: var(--green);
}}

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

/* Tarjeta derecha pipeline */
.k-card {{
  background:#fff;border:1px solid #E3EDF6;border-radius:12px;padding:14px;
}}
.badge {{
  display:inline-flex;align-items:center;gap:6px;
  background:#F1F7FD;border:1px solid #E3EDF6;border-radius:24px;
  padding:4px 10px;font-size:12px;color:#1B2A3C;
}}
"""

# =========================================================
st.set_page_config(page_title="SelektIA", page_icon="🧠", layout="wide")
st.markdown(f"<style>{CSS}</style>", unsafe_allow_html=True)

# =========================================================
# ESTADO
# =========================================================
ss = st.session_state
if "section" not in ss:
  ss.section = "def_carga"   # sección inicial
if "tasks" not in ss:
  ss.tasks = []
if "candidates" not in ss:
  ss.candidates = []         # [{Name, Score, Reasons, _bytes, _is_pdf, meta: dict}]
if "offers" not in ss:
  ss.offers = {}             # {candidate_name: {...}}
if "agents" not in ss:
  ss.agents = []             # [{rol, objetivo, backstory, guardrails, herramientas}]
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
def pdf_viewer_pdfjs(file_bytes: bytes, height=520, scale=1.1):
  b64 = base64.b64encode(file_bytes).decode("utf-8")
  pdfjs = "https://mozilla.github.io/pdf.js/web/viewer.html?file="
  src = f"{pdfjs}data:application/pdf;base64,{b64}#zoom={int(scale*100)}"
  st.markdown(
      f"""<div class="pdf-frame">
            <iframe src="{src}" style="width:100%; height:{height}px; border:0;" title="PDF Viewer"></iframe>
          </div>""",
      unsafe_allow_html=True,
  )

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

def simple_score(cv_text: str, jd: str, keywords: str) -> tuple[int, str]:
  base = 0
  reasons = []
  text_low = cv_text.lower()
  jd_low = jd.lower()

  hits = 0
  kws = [k.strip().lower() for k in keywords.split(",") if k.strip()]
  for k in kws:
    if k and k in text_low:
      hits += 1
  if kws:
    pct_k = hits/len(kws)
    base += int(pct_k*70)
    reasons.append(f"{hits}/{len(kws)} keywords encontradas — Coincidencias: {', '.join([k for k in kws if k in text_low])[:120]}")

  jd_terms = [t for t in set(jd_low.split()) if len(t) > 3]
  match_terms = sum(1 for t in jd_terms if t in text_low)
  if jd_terms:
    pct_jd = match_terms/len(jd_terms)
    base += int(pct_jd*30)
    reasons.append("Coincidencias con el JD (aprox.)")

  base = max(0, min(100, base))
  return base, " — ".join(reasons)

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
  cols = [
    ("Flujos", "flows"),
    ("Agentes", "agents"),
    ("Tareas de Agente", "agent_tasks")
  ]
  for txt, sec in cols:
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
  # Inputs JD
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

  files = st.file_uploader("Subir CVs (PDF o TXT)", type=["pdf", "txt"], accept_multiple_files=True)
  if files:
    ss.candidates = []
    for f in files:
      f_bytes = f.read()
      f.seek(0)
      text = extract_text_from_file(f)
      score, reasons = simple_score(text, jd_text, kw_text)
      # Meta simple (demo): años exp por heurística
      years = 0
      for token in ["years", "años", "experiencia"]:
        if token in text.lower():
          years = max(years, 5)
      ss.candidates.append({
        "Name": f.name,
        "Score": score,
        "Reasons": reasons,
        "_bytes": f_bytes,
        "_is_pdf": Path(f.name).suffix.lower()==".pdf",
        "meta": {
          "anios_exp": years,
          "ultima_actualizacion": datetime.today().date().isoformat()
        }
      })
    st.success("CVs cargados y analizados.")

def page_puestos():
  st.header("Puestos")
  st.dataframe(
    ss.positions[
      ["Puesto","Días Abierto","Leads","Nuevos","Recruiter Screen",
       "HM Screen","Entrevista Telefónica","Entrevista Presencial","Ubicación",
       "Hiring Manager","Estado","ID"]
    ].sort_values(["Estado","Días Abierto","Leads"], ascending=[True,True,False]),
    use_container_width=True, height=380
  )

def page_eval():
  st.header("Resultados de evaluación")
  if not ss.candidates:
    st.info("Carga CVs en **Definición & Carga**.")
    return
  df = pd.DataFrame(ss.candidates)
  df_sorted = df.sort_values("Score", ascending=False)
  st.subheader("Ranking de Candidatos")
  st.dataframe(df_sorted[["Name","Score","Reasons"]], use_container_width=True, height=230)

  st.subheader("Comparación de puntajes")
  bar_colors = [BAR_GOOD if s >= 60 else BAR_DEFAULT for s in df_sorted["Score"]]
  fig = px.bar(df_sorted, x="Name", y="Score", title="Comparación de puntajes (todos los candidatos)")
  fig.update_traces(marker_color=bar_colors, hovertemplate="%{x}<br>Score: %{y}")
  fig.update_layout(plot_bgcolor="#FFFFFF", paper_bgcolor="rgba(0,0,0,0)",
                    font=dict(color=TITLE_DARK), xaxis_title=None, yaxis_title="Score")
  st.plotly_chart(fig, use_container_width=True)

  st.subheader("Visor de CV (PDF/TXT)")
  selected = st.selectbox("Elige un candidato", df_sorted["Name"].tolist())
  cand = df[df["Name"]==selected].iloc[0]
  if cand["_is_pdf"]:
    pdf_viewer_pdfjs(cand["_bytes"], height=480, scale=1.10)
  else:
    st.info(f"'{selected}' es TXT.")
    st.text_area("Contenido", cand["_bytes"].decode("utf-8","ignore"), height=380)

def page_pipeline():
  st.header("Pipeline de Candidatos")
  if not ss.candidates:
    st.info("Primero carga CVs en **Definición & Carga**.")
    return
  df = pd.DataFrame(ss.candidates).sort_values("Score", ascending=False)

  c1, c2 = st.columns([1.2, 1])
  with c1:
    st.markdown("**Candidatos (haz clic para ver detalles)**")
    # Lista simple de candidatos
    for i, row in df.iterrows():
      label = f"{row['Name']} — {row['Score']}%"
      if st.button(label, key=f"pi_{i}"):
        ss["selected_cand"] = row["Name"]

  with c2:
    st.markdown("**Detalle del candidato**")
    if "selected_cand" not in ss:
      st.caption("Selecciona un candidato de la lista.")
      return
    sel = ss["selected_cand"]
    row = df[df["Name"]==sel].iloc[0]
    st.markdown(f"**{sel}**")
    st.markdown('<div class="k-card">', unsafe_allow_html=True)
    st.markdown("**Match estimado**  \n" + ("✅ Alto" if row["Score"]>=60 else "🟡 Medio"))
    st.markdown("**Validated Skills**  \n- HIS")
    st.markdown("**Likely Skills**  \n- IAAS")
    st.markdown("**Skills to Validate**  \n- SAP IS-H  \n- BLS  \n- ACLS  \n- educación al paciente")
    st.markdown("---")
    st.markdown(f"**Años de experiencia:** {row['meta'].get('anios_exp',0)}")
    st.markdown(f"**Última actualización CV:** {row['meta'].get('ultima_actualizacion','—')}")
    st.markdown("</div>", unsafe_allow_html=True)
    st.write("")
    cbtn1, cbtn2 = st.columns(2)
    with cbtn1:
      if st.button("Añadir nota 'Buen encaje'"):
        st.success("Nota agregada.")
    with cbtn2:
      if st.button("Mover a ‘Entrevista (Gerencia)’"):
        ss.section = "interview"
        st.rerun()

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
    ch1 = st.checkbox("✅ Contacto hecho")
  with col2:
    ch2 = st.checkbox("✅ Entrevista agendada")
  with col3:
    ch3 = st.checkbox("✅ Feedback recibido")
  notas = st.text_area("Notas (3 fortalezas, 2 riesgos, pretensión, disponibilidad)", height=120)
  adj = st.file_uploader("Adjuntos (BLS/ACLS, colegiatura, etc.)", accept_multiple_files=True)

  c1, c2 = st.columns(2)
  if c1.button("Guardar"):
    st.success("Checklist y notas guardadas.")
  if c2.button("Enviar a Comité"):
    st.info("Bloqueo de edición del HH y acta breve generada.")

def page_agents():
  st.header("Agentes")
  # Form de configuración de asistente IA (se guarda en ss.agents)
  with st.form("agent_form"):
    rol = st.selectbox("Rol*", ["Headhunter","Coordinador RR.HH.","Admin RR.HH."], index=0)
    objetivo = st.text_input("Objetivo*", "Identificar a los mejores profesionales para el cargo definido en el JD")
    backstory = st.text_area("Backstory*", "Eres un analista de RR.HH. con experiencia en análisis de documentos, CV y currículums.")
    guardrails = st.text_area("Guardrails", "No compartas datos sensibles. Cita la fuente (CV o JD) al argumentar.")
    herramientas = st.multiselect("Herramientas habilitadas", ["Parser de PDF","Recomendador de skills","Comparador JD-CV"], default=["Parser de PDF","Recomendador de skills"])
    ok = st.form_submit_button("Crear/Actualizar Asistente")
    if ok:
      ss.agents.append({
        "rol": rol, "objetivo": objetivo, "backstory": backstory,
        "guardrails": guardrails, "herramientas": herramientas, "ts": datetime.utcnow().isoformat()
      })
      st.success("Asistente guardado. Esta configuración guiará la evaluación de CVs.")

  if ss.agents:
    st.subheader("Asistentes configurados")
    st.dataframe(pd.DataFrame(ss.agents), use_container_width=True, height=240)

def page_flows():
  st.header("Flujos")
  st.write("Define y documenta flujos (demo).")

def page_agent_tasks():
  st.header("Tareas de Agente")
  st.write("Bandeja de tareas para asistentes (demo).")

def page_analytics():
  st.header("Analytics")
  st.write("Panel de métricas (demo).")

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

ROUTES.get(ss.section, page_def_carga)()
