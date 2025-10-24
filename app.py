# app.py
# -*- coding: utf-8 -*-

import io
import re
import base64
from pathlib import Path
from datetime import date, datetime

import streamlit as st
import pandas as pd
import plotly.express as px
from PyPDF2 import PdfReader

# ==========================================================
# THEME / COLORS
# ==========================================================
PRIMARY_GREEN = "#00CD78"   # <- verde solicitado
SIDEBAR_BG     = "#10172A"
TEXT_LIGHT     = "#FFFFFF"
TITLE_DARK     = "#142433"
MAIN_BG        = "#F7FBFF"
BOX_LIGHT      = "#F1F7FD"
BOX_LIGHT_B    = "#E3EDF6"
BAR_DEFAULT    = "#E9F3FF"
BAR_GOOD       = "#33FFAC"

CSS = f"""
:root {{
  --green: {PRIMARY_GREEN};
  --sidebar-bg: {SIDEBAR_BG};
  --text: {TEXT_LIGHT};
  --title: {TITLE_DARK};
  --main: {MAIN_BG};
  --boxl: {BOX_LIGHT};
  --boxlb: {BOX_LIGHT_B};
}}

html, body, [data-testid="stAppViewContainer"] {{
  background: var(--main) !important;
}}

/* ===== Sidebar (izquierda) ===== */
[data-testid="stSidebar"] {{
  background: var(--sidebar-bg) !important;
  color: var(--text) !important;
  border-right: 1px solid #0f1424;
}}
[data-testid="stSidebar"] * {{ color: var(--text) !important; }}

.sidebar-logo {{
  display:flex; align-items:center; justify-content:center;
  padding: 14px 8px 6px 8px;
  margin-bottom: 8px;
}}
.sidebar-logo img {{ max-width: 200px; height:auto; }}

.sidebar-section-title {{
  font-weight: 800;
  color: var(--green);
  margin: 14px 8px 6px 8px;
  letter-spacing: .2px;
  font-size: 14px;
  text-transform: uppercase;
}}

[data-testid="stSidebar"] .stButton > button {{
  width: 100%;
  border-radius: 10px !important;
  background: var(--sidebar-bg) !important;        /* mismo color del fondo */
  border: 1px solid rgba(255,255,255,.12) !important;
  color: #dde6f7 !important;
  display: flex;
  justify-content: flex-start;                      /* texto NO centrado */
  align-items: center;
  gap: 8px;
  padding: 10px 12px !important;
  box-shadow: none !important;
}}
[data-testid="stSidebar"] .stButton > button:hover {{
  border-color: rgba(255,255,255,.22) !important;
  background: rgba(255,255,255,.03) !important;
}}

/* ===== Botones del contenido (derecha) ===== */
.block-container .stButton > button,
.block-container button[kind="secondary"],
.block-container .stDownloadButton button {{
  background: var(--green) !important;
  color: #082017 !important;
  border: none !important;
  border-radius: 10px !important;
  padding: .5rem .9rem !important;
  font-weight: 700 !important;
  box-shadow: none !important;
}}
.block-container .stButton > button:hover,
.block-container .stDownloadButton button:hover {{
  filter: brightness(.96);
}}

h1, h2, h3, h4 {{
  color: var(--title);
}}
h1 strong, h2 strong, h3 strong {{
  color: var(--green);
}}

.block-container [data-testid="stSelectbox"] > div > div,
.block-container [data-testid="stTextInput"] input,
.block-container [data-testid="stTextArea"] textarea {{
  background: var(--boxl) !important;
  color: var(--title) !important;
  border: 1.5px solid var(--boxlb) !important;
  border-radius: 10px !important;
}}

table {{ border: 1px solid var(--boxlb) !important; border-radius: 6px !important; }}
thead th {{ background: var(--boxl) !important; }}

.pdf-frame {{
  border: 1px solid var(--boxlb);
  border-radius: 12px;
  overflow: hidden;
  background: #fff;
}}

/* Logos top-right */
.topbar {{
  display:flex;align-items:center;justify-content:flex-end;
  gap:18px;margin-bottom:8px;
}}
.topbar img {{ max-height: 34px; }}
"""

st.set_page_config(page_title="Selektia", page_icon="🧠", layout="wide")
st.markdown(f"<style>{CSS}</style>", unsafe_allow_html=True)

# ==========================================================
# STATE
# ==========================================================
if "page" not in st.session_state:
    st.session_state.page = "Asistente IA"

if "assistant_config" not in st.session_state:
    st.session_state.assistant_config = {
        "role": "Headhunter",
        "goal": "Identificar a los mejores profesionales para el cargo definido en el JD",
        "backstory": "Eres un analista de RR.HH. con experiencia en análisis de documentos, CV y currículums.",
        "guardrails": "No compartas datos sensibles. Cita la fuente (CV o JD) al argumentar.",
        "tools": ["Parser de PDF", "Recomendador de candidatos"]
    }

if "candidates" not in st.session_state:
    st.session_state.candidates = []

if "uploader_key" not in st.session_state:
    st.session_state.uploader_key = "u1"

if "positions" not in st.session_state:
    st.session_state.positions = pd.DataFrame([
        {
            "ID": "10,645,194", "Puesto": "Desarrollador/a Backend (Python)","Días Abierto": 3,
            "Leads": 1800, "Nuevos": 115, "Recruiter Screen": 35, "HM Screen": 7,
            "Entrevista Telefónica": 14,"Entrevista Presencial": 15, "Ubicación": "Lima, Perú",
            "Hiring Manager": "Rivers Brykson", "Estado": "Abierto", "Creado": date.today()
        },
        {
            "ID": "10,376,415","Puesto": "VP de Marketing","Días Abierto": 28,
            "Leads": 8100, "Nuevos": 1, "Recruiter Screen": 15, "HM Screen": 35,
            "Entrevista Telefónica": 5, "Entrevista Presencial": 7, "Ubicación": "Santiago, Chile",
            "Hiring Manager": "Angela Cruz", "Estado": "Abierto", "Creado": date.today()
        },
        {
            "ID": "10,376,646","Puesto": "Planner de Demanda","Días Abierto": 28,
            "Leads": 2300, "Nuevos": 26, "Recruiter Screen": 3, "HM Screen": 8,
            "Entrevista Telefónica": 6, "Entrevista Presencial": 3, "Ubicación": "Ciudad de México, MX",
            "Hiring Manager": "Rivers Brykson", "Estado": "Abierto", "Creado": date.today()
        },
    ])

# ==========================================================
# UTILS (parse CV)
# ==========================================================
def extract_text_from_file(f) -> str:
    try:
        suf = Path(f.name).suffix.lower()
        if suf == ".pdf":
            data = f.read(); f.seek(0)
            reader = PdfReader(io.BytesIO(data))
            txt = ""
            for p in reader.pages:
                txt += p.extract_text() or ""
            return txt
        else:
            return f.read().decode("utf-8", errors="ignore")
    except Exception as e:
        st.error(f"Error leyendo {f.name}: {e}")
        return ""

def guess_last_university_and_year(text):
    uline = None; uy = None
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    uni_pat = re.compile(r"(Universidad|University)[^\n]*", re.IGNORECASE)
    for l in lines:
        if uni_pat.search(l):
            yrs = re.findall(r"(?:19|20)\\d{{2}}", l)
            y = max([int(x) for x in yrs], default=None)
            uline, uy = l, y
    return uline, uy

def guess_experience_years(text):
    m = re.search(r"(\\d{{1,2}})\\+?\\s*(?:años|years)\\s*(?:de\\s*experiencia|of total experience)?", text, re.IGNORECASE)
    if m:
        try: return int(m.group(1))
        except: pass
    years = [int(x) for x in re.findall(r"\\((\\d{{1,2}})\\s*years?\\)", text, re.IGNORECASE)]
    return max(years) if years else None

def guess_roles(text):
    roles = []
    role_kw = ["Engineer","Developer","Architect","Enfermera","Tecnólogo","Medico","Recepcionista",
               "Químico","Farmacéutico","Manager","Consultant","Analyst","Especialista"]
    for line in [l.strip() for l in text.splitlines() if l.strip()]:
        if any(k.lower() in line.lower() for k in role_kw):
            roles.append(line)
    return roles[:6]

def guess_skills(text):
    skills = set()
    tokens = ["java","python","sql","gis","postgis","geoserver","oracle","css","html","sap","sap is-h",
              "his","bls","acls","iaas","protocolos","educación al paciente","seguridad del paciente"]
    for line in [l.strip() for l in text.splitlines() if l.strip()]:
        if "," in line and sum(1 for t in tokens if t in line.lower()) >= 1:
            parts = [p.strip() for p in line.split(",")]
            for p in parts:
                if len(p) <= 40:
                    skills.add(p)
    found = [t for t in tokens if t in text.lower()]
    skills.update(found)
    return list(dict.fromkeys(skills))[:12]

def guess_last_update(text):
    m = re.search(r"Updated\\s+([A-Za-z]{{3,9}}\\s+\\d{{1,2}},\\s+\\d{{4}})", text, re.IGNORECASE)
    if m: return m.group(1)
    m = re.search(r"(?:Actualizado|Actualizada)\\s+(\\d{{4}}-\\d{{2}}-\\d{{2}})", text, re.IGNORECASE)
    if m: return m.group(1)
    return None

def pdf_viewer_pdfjs(file_bytes: bytes, height=520, scale=1.1):
    b64 = base64.b64encode(file_bytes).decode("utf-8")
    pdfjs = "https://mozilla.github.io/pdf.js/web/viewer.html?file="
    src = f"{pdfjs}data:application/pdf;base64,{b64}#zoom={int(scale*100)}"
    st.markdown(
        f"""
        <div class="pdf-frame">
          <iframe src="{src}" style="width:100%; height:{height}px; border:0;" title="PDF Viewer"></iframe>
        </div>
        """,
        unsafe_allow_html=True,
    )

# ==========================================================
# TOP RIGHT (solo Wayki) & SIDEBAR NAV
# ==========================================================
def top_right_logos():
    c1, c2 = st.columns([8, 1.2])
    with c2:
        wayki_path = Path("assets/logo-wayki.png")
        if wayki_path.exists():
            st.image(str(wayki_path))

def sidebar_nav():
    # Logo SelektIA en el panel izquierdo
    sele_path = Path("assets/logo-selektia.png")
    if sele_path.exists():
        st.sidebar.markdown('<div class="sidebar-logo">', unsafe_allow_html=True)
        st.sidebar.image(str(sele_path))
        st.sidebar.markdown('</div>', unsafe_allow_html=True)

    # Orden solicitado: Bienvenido → Páginas ATS → resto
    st.sidebar.markdown('<div class="sidebar-section-title">DASHBOARD</div>', unsafe_allow_html=True)
    if st.sidebar.button("Bienvenido a Selektia", key="nav_dash"):
        st.session_state.page = "Bienvenido"

    # PÁGINAS ATS debajo de Bienvenido
    st.sidebar.markdown('<div class="sidebar-section-title">Páginas ATS</div>', unsafe_allow_html=True)
    if st.sidebar.button("Definición & Carga", key="nav_def"):
        st.session_state.page = "Definición & Carga"
    if st.sidebar.button("Puestos", key="nav_puestos"):
        st.session_state.page = "Puestos"
    if st.sidebar.button("Evaluación de CVs", key="nav_eval"):
        st.session_state.page = "Evaluación de CVs"
    if st.sidebar.button("Pipeline de Candidatos", key="nav_pipe"):
        st.session_state.page = "Pipeline de Candidatos"
    if st.sidebar.button("Entrevista (Gerencia)", key="nav_ger"):
        st.session_state.page = "Entrevista (Gerencia)"
    if st.sidebar.button("Tareas del Headhunter", key="nav_hh"):
        st.session_state.page = "Tareas del Headhunter"
    if st.sidebar.button("Oferta", key="nav_oferta"):
        st.session_state.page = "Oferta"
    if st.sidebar.button("Onboarding", key="nav_onboard"):
        st.session_state.page = "Onboarding"

    # Analytics
    st.sidebar.markdown('<div class="sidebar-section-title">Analytics</div>', unsafe_allow_html=True)
    if st.sidebar.button("Abrir Analytics", key="nav_analytics"):
        st.session_state.page = "Analytics"

    # Acciones
    st.sidebar.markdown('<div class="sidebar-section-title">Acciones</div>', unsafe_allow_html=True)
    if st.sidebar.button("Crear tarea", key="nav_task"):
        st.session_state.page = "Crear tarea"

    # Asistente IA
    st.sidebar.markdown('<div class="sidebar-section-title">Asistente IA</div>', unsafe_allow_html=True)
    if st.sidebar.button("Flujos", key="nav_flujos"):
        st.session_state.page = "Flujos"
    if st.sidebar.button("Agentes", key="nav_agentes"):
        st.session_state.page = "Asistente IA"
    if st.sidebar.button("Tareas de Agente", key="nav_tareas_ag"):
        st.session_state.page = "Tareas de Agente"

    # Tareas secciones
    st.sidebar.markdown('<div class="sidebar-section-title">Tareas</div>', unsafe_allow_html=True)
    if st.sidebar.button("Todas las tareas", key="nav_todas"):
        st.session_state.page = "Todas las tareas"
    if st.sidebar.button("Asignadas a mí", key="nav_mi"):
        st.session_state.page = "Asignadas a mí"
    if st.sidebar.button("Asignado a mi equipo", key="nav_equipo"):
        st.session_state.page = "Asignado a mi equipo"

    # Archivo
    st.sidebar.markdown('<div class="sidebar-section-title">Archivo</div>', unsafe_allow_html=True)
    if st.sidebar.button("Ver archivo", key="nav_archivo"):
        st.session_state.page = "Archivo"

# ==========================================================
# PAGES
# ==========================================================
def page_bienvenido():
    top_right_logos()
    st.markdown("## Bienvenido a Selektia")
    st.info("KPIs y accesos rápidos (placeholder).")

def page_analytics():
    top_right_logos()
    st.markdown("## Analytics")
    st.info("Espacio de dashboards/BI (placeholder).")

def page_crear_tarea():
    top_right_logos()
    st.markdown("## Crear tarea")
    with st.form("nueva_tarea"):
        t1, t2 = st.columns(2)
        with t1:
            tt = st.text_input("Título*", "")
        with t2:
            due = st.date_input("Fecha límite", value=date.today())
        desc = st.text_area("Descripción")
        ok = st.form_submit_button("Crear")
        if ok:
            st.success("Tarea creada (placeholder).")

def page_flujos():
    top_right_logos()
    st.markdown("## Flujos")
    st.info("Configura automatizaciones y flujos (placeholder).")

def page_tareas_agente():
    top_right_logos()
    st.markdown("## Tareas de Agente")
    st.info("Listado de tareas del agente IA (placeholder).")

def page_tareas_listado(nombre):
    top_right_logos()
    st.markdown(f"## {nombre}")
    st.info("Listado de tareas (placeholder).")

def page_archivo():
    top_right_logos()
    st.markdown("## Archivo")
    st.info("Histórico/archivo de procesos (placeholder).")

def page_asistente_ia():
    top_right_logos()
    st.markdown("## Asistente IA")

    c1, c2 = st.columns([2,1])
    with c1:
        role = st.selectbox("Rol*", ["Headhunter","Coordinador RR.HH.","Hiring Manager","Admin"], index=0)
        goal = st.text_input("Objetivo*", st.session_state.assistant_config.get("goal",""))
        backstory = st.text_area("Backstory*", st.session_state.assistant_config.get("backstory",""), height=120)
        guardrails = st.text_area("Guardrails", st.session_state.assistant_config.get("guardrails",""), height=80)

        tools = st.multiselect("Herramientas habilitadas", 
                               ["Parser de PDF","Recomendador de candidatos","Buscador web"],
                               default=st.session_state.assistant_config.get("tools",["Parser de PDF","Recomendador de candidatos"]))
        if st.button("Crear/Actualizar Asistente", use_container_width=True):
            st.session_state.assistant_config = {
                "role": role, "goal": goal, "backstory": backstory,
                "guardrails": guardrails, "tools": tools
            }
            st.success("Asistente guardado. Esta configuración guiará la evaluación de CVs.")
    with c2:
        st.markdown("### Permisos y alcance")
        st.write("- **RLS** por puesto: el asistente ve candidatos del puesto/rol asignado.")
        st.write("- Acciones según rol (HH no aprueba ofertas).")
        st.write("- **Auditoría**: toda acción queda registrada.")

def page_definicion_carga():
    top_right_logos()
    st.markdown("## Definición & Carga")

    st.markdown("#### Definición del puesto")
    puesto = st.selectbox(
        "Puesto",
        ["Enfermera/o Asistencial","Tecnólogo/a Médico","Recepcionista de Admisión","Médico/a General","Químico/a Farmacéutico/a"],
        index=0,
        key="puesto_def"
    )

    st.markdown("#### Descripción del puesto (texto libre)")
    jd_text = st.text_area("Descripción / JD", key="jd_def", height=140)

    st.markdown("#### Palabras clave (coma separada)")
    kw_text = st.text_area("Keywords", value="HIS, SAP IS-H, BLS, ACLS, IAAS, educación al paciente, seguridad del paciente, protocolos", key="kw_def", height=110)

    st.markdown("#### Subir CVs (PDF o TXT)")
    files = st.file_uploader("Arrastra aquí o haz clic para subir", type=["pdf","txt"], accept_multiple_files=True, key=st.session_state.uploader_key)
    if files:
        st.session_state.candidates = []
        for f in files:
            bytes_ = f.read(); f.seek(0)
            txt = extract_text_from_file(f)
            # scoring simple con keywords
            score = 0; hits = 0
            kws = [k.strip().lower() for k in kw_text.split(",") if k.strip()]
            low = txt.lower()
            for k in kws:
                if k and k in low: hits += 1
            if kws: score = int((hits/len(kws))*100)
            st.session_state.candidates.append({
                "Name": f.name, "Score": score,
                "Reasons": f"{hits}/{len(kws)} keywords encontradas — Coincidencias: {', '.join([k for k in kws if k in low])[:120]}",
                "_bytes": bytes_, "_is_pdf": Path(f.name).suffix.lower()==".pdf", "_text": txt
            })
        st.success("CVs procesados ✔️")

def page_puestos():
    top_right_logos()
    st.markdown("## Puestos")

    q = st.text_input("Buscar (puesto, ubicación, ID, hiring manager…)", placeholder="Ej: Lima, 10645194, Angela Cruz")
    show_filters = st.checkbox("Mostrar filtros", value=False)
    st.metric("Puestos totales", len(st.session_state.positions))

    df_pos = st.session_state.positions.copy()
    if q:
        ql = q.lower()
        df_pos = df_pos[
            df_pos["Puesto"].str.lower().str.contains(ql) |
            df_pos["Ubicación"].str.lower().str.contains(ql) |
            df_pos["Hiring Manager"].str.lower().str.contains(ql) |
            df_pos["ID"].astype(str).str.contains(ql)
        ]

    if show_filters:
        with st.expander("Filtros", expanded=True):
            colf1, colf2, colf3, colf4 = st.columns(4)
            with colf1:
                ubic = st.multiselect("Ubicación", sorted(df_pos["Ubicación"].unique().tolist()))
            with colf2:
                hm = st.multiselect("Hiring Manager", sorted(df_pos["Hiring Manager"].unique().tolist()))
            with colf3:
                estado = st.multiselect("Estado", sorted(df_pos["Estado"].unique().tolist()))
            with colf4:
                dias_abierto = st.slider("Días abierto (máx)", 0, 120, 60)
        if 'ubic' in locals() and ubic:
            df_pos = df_pos[df_pos["Ubicación"].isin(ubic)]
        if 'hm' in locals() and hm:
            df_pos = df_pos[df_pos["Hiring Manager"].isin(hm)]
        if 'estado' in locals() and estado:
            df_pos = df_pos[df_pos["Estado"].isin(estado)]
        df_pos = df_pos[df_pos["Días Abierto"] <= dias_abierto]

    st.dataframe(
        df_pos[["Puesto","Días Abierto","Leads","Nuevos","Recruiter Screen","HM Screen","Entrevista Telefónica","Entrevista Presencial","Ubicación","Hiring Manager","Estado","ID"]],
        use_container_width=True, height=420
    )

def page_eval():
    top_right_logos()
    st.markdown("## Resultados de evaluación")

    if not st.session_state.candidates:
        st.info("Sube CVs en **Definición & Carga** para iniciar.")
        return

    df = pd.DataFrame(st.session_state.candidates).sort_values("Score", ascending=False)
    st.markdown("### Ranking de Candidatos")
    st.dataframe(df[["Name","Score","Reasons"]], use_container_width=True, height=240)

    st.markdown("### Comparación de puntajes")
    bar_colors = [BAR_GOOD if s>=60 else BAR_DEFAULT for s in df["Score"]]
    fig = px.bar(df, x="Name", y="Score", title="Comparación de puntajes (todos los candidatos)")
    fig.update_traces(marker_color=bar_colors, hovertemplate="%{x}<br>Score: %{y}")
    fig.update_layout(plot_bgcolor="#FFFFFF", paper_bgcolor="rgba(0,0,0,0)", font=dict(color=TITLE_DARK), xaxis_title=None, yaxis_title="Score")
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("### Visor de CV (PDF/TXT)")
    selected = st.selectbox("Elige un candidato", df["Name"].tolist(), index=0, label_visibility="collapsed")
    cand = df[df["Name"]==selected].iloc[0]
    if cand["_is_pdf"] and cand["_bytes"]:
        pdf_viewer_pdfjs(cand["_bytes"], height=480, scale=1.1)
        st.download_button(f"Descargar {selected}", data=cand["_bytes"], file_name=selected, mime="application/pdf")
    else:
        st.info(f"'{selected}' es un TXT. Mostrando contenido abajo:")
        with st.expander("Contenido TXT", expanded=True):
            try:
                txt = cand["_bytes"].decode("utf-8", errors="ignore")
            except Exception:
                txt = "(No se pudo decodificar)"
            st.text_area("Contenido", value=txt, height=400, label_visibility="collapsed")

def page_pipeline():
    top_right_logos()
    st.markdown("## Pipeline de Candidatos")

    if not st.session_state.candidates:
        st.info("Sube CVs en **Definición & Carga** para ver el pipeline.")
        return

    df = pd.DataFrame(st.session_state.candidates).sort_values("Score", ascending=False)

    left, right = st.columns([1.2, 1])
    with left:
        st.markdown("#### Candidatos detectados")
        st.dataframe(df[["Name","Score"]], use_container_width=True, height=360)
        selected = st.selectbox("Selecciona un candidato", df["Name"].tolist(), index=0)
        st.session_state._pipeline_selected = selected

        st.markdown("### Acciones rápidas")
        c1, c2 = st.columns(2)
        with c1:
            st.button("Marcar contacto hoy (en Contactado)", use_container_width=True)
        with c2:
            st.button("Mover a Leads → Contactado", use_container_width=True)

    with right:
        st.markdown("### Detalle del candidato")
        cand = df[df["Name"]==st.session_state._pipeline_selected].iloc[0]
        text = cand["_text"]

        # Datos extraídos del CV
        def guess_last_university_and_year_local(txt):  # (scope local por seguridad)
            uline = None; uy = None
            lines = [l.strip() for l in txt.splitlines() if l.strip()]
            uni_pat = re.compile(r"(Universidad|University)[^\n]*", re.IGNORECASE)
            for l in lines:
                if uni_pat.search(l):
                    yrs = re.findall(r"(?:19|20)\\d{{2}}", l)
                    y = max([int(x) for x in yrs], default=None)
                    uline, uy = l, y
            return uline, uy

        exp_years = guess_experience_years(text)
        uni_line, uni_year = guess_last_university_and_year_local(text)
        roles = guess_roles(text)
        skills = guess_skills(text)
        last_update = guess_last_update(text)

        st.write(f"**Archivo:** {cand['Name']}")
        st.write(f"**Match estimado:** {'Alto' if cand['Score']>=60 else 'Medio' if cand['Score']>=40 else 'Bajo'}")
        st.caption("Perfil detectado a partir del CV (heurística).")

        s1, s2 = st.columns(2)
        with s1:
            st.write(f"**Años de experiencia:** {exp_years if exp_years is not None else 'N/D'}")
            st.write("**Cargos (últimos):**")
            if roles:
                for r in roles[:4]:
                    st.write(f"- {r}")
            else:
                st.write("- N/D")
        with s2:
            st.write(f"**Universidad (última referencia):** {uni_line or 'N/D'}")
            st.write(f"**Año:** {uni_year if uni_year else 'N/D'}")
            st.write(f"**Actualizado en CV:** {last_update or 'N/D'}")

        st.write("**Skills**")
        if skills:
            st.write(", ".join(skills))
        else:
            st.write("N/D")

        st.markdown("---")
        st.markdown("#### Acciones")
        cc1, cc2 = st.columns(2)
        with cc1:
            st.button("Añadir nota 'Buen encaje'", use_container_width=True)
        with cc2:
            st.button("Mover a ‘Entrevista (Gerencia)’", use_container_width=True)

def page_entrevista():
    top_right_logos()
    st.markdown("## Entrevista (Gerencia)")
    st.info("Rúbrica de gerencia (placeholder).")

def page_hh_tasks():
    top_right_logos()
    st.markdown("## Tareas del Headhunter")
    st.info("Checklist, adjuntos y ‘Enviar a Comité’ (placeholder).")

def page_oferta():
    top_right_logos()
    st.markdown("## Oferta")
    st.info("Generar/Enviar/Seguimiento de oferta (placeholder).")

def page_onboarding():
    top_right_logos()
    st.markdown("## Onboarding")
    st.info("Checklist con fechas, responsables, adjuntos y recordatorios (placeholder).")

# ==========================================================
# RENDER
# ==========================================================
sidebar_nav()

PAGES = {
    "Bienvenido": page_bienvenido,
    "Analytics": page_analytics,
    "Crear tarea": page_crear_tarea,
    "Flujos": page_flujos,
    "Asistente IA": page_asistente_ia,
    "Tareas de Agente": page_tareas_agente,
    "Todas las tareas": lambda: page_tareas_listado("Todas las tareas"),
    "Asignadas a mí": lambda: page_tareas_listado("Asignadas a mí"),
    "Asignado a mi equipo": lambda: page_tareas_listado("Asignado a mi equipo"),
    "Archivo": page_archivo,
    "Definición & Carga": page_definicion_carga,
    "Puestos": page_puestos,
    "Evaluación de CVs": page_eval,
    "Pipeline de Candidatos": page_pipeline,
    "Entrevista (Gerencia)": page_entrevista,
    "Tareas del Headhunter": page_hh_tasks,
    "Oferta": page_oferta,
    "Onboarding": page_onboarding,
}

PAGES.get(st.session_state.page, page_asistente_ia)()
