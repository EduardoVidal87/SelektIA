# app.py
# -*- coding: utf-8 -*-

import io
import base64
from pathlib import Path
from datetime import date, datetime, timedelta
from html import escape  # para sanitizar chips

import streamlit as st
import pandas as pd
import plotly.express as px
from PyPDF2 import PdfReader

# ======================================================================================
# TEMA / COLORES
# ======================================================================================
PRIMARY_GREEN = "#00CD78"
SIDEBAR_BG = "#10172A"
BOX_DARK = "#132840"
BOX_DARK_HOV = "#193355"
TEXT_LIGHT = "#FFFFFF"
MAIN_BG = "#F7FBFF"
BOX_LIGHT = "#F1F7FD"
BOX_LIGHT_B = "#E3EDF6"
TITLE_DARK = "#142433"
BAR_DEFAULT = "#E9F3FF"
BAR_GOOD = "#33FFAC"

CSS = f"""
:root {{
  --green: {PRIMARY_GREEN};
  --sidebar-bg: {SIDEBAR_BG};
  --box: {BOX_DARK};
  --box-hover: {BOX_DARK_HOV};
  --text: {TEXT_LIGHT};
  --main-bg: {MAIN_BG};
  --box-light: {BOX_LIGHT};
  --box-light-border: {BOX_LIGHT_B};
  --title-dark: {TITLE_DARK};
}}

/* Fondo general */
html, body, [data-testid="stAppViewContainer"] {{
  background: var(--main-bg) !important;
}}
.block-container {{ background: transparent !important; }}

/* Sidebar */
[data-testid="stSidebar"] {{
  background: var(--sidebar-bg) !important;
  color: var(--text) !important;
}}
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3,
[data-testid="stSidebar"] h4,
[data-testid="stSidebar"] h5,
[data-testid="stSidebar"] h6,
[data-testid="stSidebar"] .stMarkdown p strong {{
  color: var(--green) !important;
}}
[data-testid="stSidebar"] label, 
[data-testid="stSidebar"] p, 
[data-testid="stSidebar"] span {{
  color: var(--text) !important;
}}

/* 4 boxes del panel izquierdo */
[data-testid="stSidebar"] [data-testid="stSelectbox"] > div > div,
[data-testid="stSidebar"] [data-baseweb="select"],
[data-testid="stSidebar"] [data-testid="stTextArea"] textarea,
[data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] {{
  background: var(--box) !important;
  color: var(--text) !important;
  border: 1.5px solid var(--box) !important;
  border-radius: 14px !important;
  box-shadow: none !important;
}}
[data-testid="stSidebar"] [data-testid="stTextArea"] textarea:hover,
[data-testid="stSidebar"] [data-testid="stTextArea"] textarea:focus,
[data-testid="stSidebar"] [data-testid="stSelectbox"] > div > div:hover,
[data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"]:hover {{
  border-color: var(--box-hover) !important;
}}
[data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] * {{ color: var(--text) !important; }}
[data-testid="stSidebar"] [data-testid="stFileUploaderFile"] {{
  background: var(--box) !important;
  border: 1px solid var(--box) !important;
  color: var(--text) !important;
}}

/* Botón verde */
.stButton > button {{
  background: var(--green) !important;
  color: #082017 !important;
  border-radius: 10px !important;
  border: none !important;
  padding: .45rem .9rem !important;
  font-weight: 600 !important;
}}
.stButton > button:hover {{ filter: brightness(0.95); }}

/* Títulos del cuerpo */
h1, h2, h3 {{ color: var(--title-dark); }}
h1 strong, h2 strong, h3 strong {{ color: var(--green); }}

/* Inputs claros del cuerpo */
.block-container [data-testid="stSelectbox"] > div > div,
.block-container [data-baseweb="select"],
.block-container [data-testid="stTextInput"] input,
.block-container [data-testid="stTextArea"] textarea {{
  background: var(--box-light) !important;
  color: var(--title-dark) !important;
  border: 1.5px solid var(--box-light-border) !important;
  border-radius: 10px !important;
}}

/* Tabla clara */
.block-container table {{
  background: #fff !important;
  border: 1px solid var(--box-light-border) !important;
  border-radius: 8px !important;
}}
.block-container thead th {{
  background: var(--box-light) !important;
  color: var(--title-dark) !important;
}}

/* Selector visor */
#pdf_candidate {{
  background: var(--box-light) !important;
  border: 1.5px solid var(--box-light-border) !important;
  color: var(--title-dark) !important;
  border-radius: 10px !important;
}}

/* Contenedor visor PDF */
.pdf-frame {{
  border: 1px solid var(--box-light-border);
  border-radius: 12px;
  overflow: hidden;
  background: #fff;
}}

/* --- TABS VISIBLES --- */
[data-baseweb="tab-list"] [role="tab"] {{
  color: #1f2937 !important;
  font-weight: 700 !important;
  padding: 6px 10px !important;
  margin-right: 10px !important;
  border-bottom: 3px solid transparent !important;
}}
[data-baseweb="tab-list"] [role="tab"][aria-selected="true"] {{
  color: var(--green) !important;
  border-bottom-color: var(--green) !important;
}}
[data-baseweb="tab-list"] [role="tab"] span {{
  color: inherit !important;
}}

/* Chips */
.badge {{
  display: inline-block;
  padding: 2px 8px;
  border-radius: 12px;
  font-size: 12px;
  margin-right: 6px;
  margin-bottom: 6px;
  border: 1px solid #e3edf6;
}}
.badge-green {{ background:#E9FFF5; color:#0F5132; border-color:#BFEFD9; }}
.badge-amber {{ background:#FFF9E6; color:#614700; border-color:#FFE8A3; }}
.badge-red   {{ background:#FFECEC; color:#7A1E1E; border-color:#FFC2C2; }}
.badge-gray  {{ background:#F1F5F9; color:#334155; }}
"""

st.set_page_config(page_title="SelektIA", page_icon="🧠", layout="wide")
st.markdown(f"<style>{CSS}</style>", unsafe_allow_html=True)

# ======================================================================================
# UTILIDADES
# ======================================================================================

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

def simple_score(cv_text: str, jd: str, keywords: str):
    base = 0
    reasons = []
    text_low = cv_text.lower()
    jd_low = jd.lower()

    hits = 0
    kws = [k.strip().lower() for k in keywords.split(",") if k.strip()]
    validated = []
    for k in kws:
        if k and k in text_low:
            hits += 1
            validated.append(k)

    if kws:
        pct_k = hits / len(kws)
        base += int(pct_k * 70)
        reasons.append(
            f"{hits}/{len(kws)} keywords encontradas — Coincidencias: {', '.join([k for k in kws if k in text_low])[:120]}"
        )

    jd_terms = [t for t in set(jd_low.split()) if len(t) > 3]
    match_terms = sum(1 for t in jd_terms if t in text_low)
    if jd_terms:
        pct_jd = match_terms / len(jd_terms)
        base += int(pct_jd * 30)
        reasons.append("Coincidencias con el JD (aprox.)")

    base = max(0, min(100, base))
    to_validate = [k for k in kws if k not in validated][:6]
    likely = []
    return base, " — ".join(reasons), validated, likely, to_validate

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

def chips(items, cls):
    if not items:
        return "<span class='badge badge-gray'>—</span>"
    safe = []
    for it in items:
        label = escape(str(it)) if it is not None else "—"
        safe.append(f"<span class='badge {cls}'>{label}</span>")
    return " ".join(safe)

# ======================================================================================
# ESTADO INICIAL
# ======================================================================================
if "candidates" not in st.session_state:
    st.session_state.candidates = []
if "uploader_key" not in st.session_state:
    st.session_state.uploader_key = "u1"
if "positions" not in st.session_state:
    st.session_state.positions = pd.DataFrame([
        {
            "ID": "10,645,194",
            "Puesto": "Desarrollador/a Backend (Python)",
            "Ubicación": "Lima, Perú",
            "Leads": 1800,
            "Nuevos": 115,
            "Recruiter Screen": 35,
            "HM Screen": 7,
            "Entrevista Telefónica": 14,
            "Entrevista Presencial": 15,
            "Días Abierto": 3,
            "Hiring Manager": "Rivers Brykson",
            "Estado": "Abierto",
        },
        {
            "ID": "10,376,415",
            "Puesto": "VP de Marketing",
            "Ubicación": "Santiago, Chile",
            "Leads": 8100,
            "Nuevos": 1,
            "Recruiter Screen": 15,
            "HM Screen": 35,
            "Entrevista Telefónica": 5,
            "Entrevista Presencial": 7,
            "Días Abierto": 28,
            "Hiring Manager": "Angela Cruz",
            "Estado": "Abierto",
        },
        {
            "ID": "10,376,646",
            "Puesto": "Planner de Demanda",
            "Ubicación": "Ciudad de México, MX",
            "Leads": 2300,
            "Nuevos": 26,
            "Recruiter Screen": 3,
            "HM Screen": 8,
            "Entrevista Telefónica": 6,
            "Entrevista Presencial": 3,
            "Días Abierto": 28,
            "Hiring Manager": "Rivers Brykson",
            "Estado": "Abierto",
        },
    ])
if "pipeline_selected" not in st.session_state:
    st.session_state.pipeline_selected = None
if "gerencia_list" not in st.session_state:
    st.session_state.gerencia_list = []
if "hh_tasks" not in st.session_state:
    st.session_state.hh_tasks = {}
if "ofertas" not in st.session_state:
    st.session_state.ofertas = []
if "metrics" not in st.session_state:
    st.session_state.metrics = {}
if "onboarding" not in st.session_state:
    st.session_state.onboarding = {}
# NUEVO: rol y flags
if "current_role" not in st.session_state:
    st.session_state.current_role = "Coordinador RR.HH."
if "feature_flags" not in st.session_state:
    st.session_state.feature_flags = {"crear_oferta": True, "aprobar_oferta": False, "mover_pipeline": True}
if "audit_log" not in st.session_state:
    st.session_state.audit_log = []  # lista de dicts

# ======================================================================================
# SIDEBAR
# ======================================================================================
with st.sidebar:
    st.image("assets/logo-wayki.png", use_column_width=True)
    st.markdown("### Definición del puesto")

    puesto = st.selectbox(
        "Puesto",
        [
            "Enfermera/o Asistencial",
            "Tecnólogo/a Médico",
            "Recepcionista de Admisión",
            "Médico/a General",
            "Químico/a Farmacéutico/a",
        ],
        index=0,
        key="puesto",
    )

    st.markdown("### Descripción del puesto (texto libre)")
    jd_text = st.text_area(
        "Resume el objetivo del puesto, responsabilidades, protocolos y habilidades deseadas.",
        height=120,
        key="jd",
        label_visibility="collapsed",
    )

    st.markdown("### Palabras clave del perfil\n*(ajústalas si es necesario)*")
    kw_text = st.text_area(
        "HIS, SAP IS-H, BLS, ACLS, IAAS, educación al paciente, seguridad…",
        value="HIS, SAP IS-H, BLS, ACLS, IAAS, educación al paciente, seguridad del paciente, protocolos",
        height=110,
        key="kw",
        label_visibility="collapsed",
    )

    st.markdown("### Subir CVs (PDF o TXT)")
    files = st.file_uploader(
        "Drag and drop files here",
        key=st.session_state.uploader_key,
        type=["pdf", "txt"],
        accept_multiple_files=True,
        label_visibility="collapsed",
    )

    if files:
        st.session_state.candidates = []
        for f in files:
            b = f.read()
            f.seek(0)
            text = extract_text_from_file(f)
            score, reasons, v_sk, l_sk, t_sk = simple_score(text, jd_text, kw_text)
            first_seen = datetime.utcnow().isoformat()
            st.session_state.candidates.append({
                "Name": f.name,
                "Score": score,
                "Reasons": reasons,
                "_bytes": b,
                "_is_pdf": Path(f.name).suffix.lower() == ".pdf",
                "_validated": v_sk,
                "_likely": l_sk,
                "_to_validate": t_sk,
                "_first_seen": first_seen,
            })
            st.session_state.metrics.setdefault(f.name, {})["first_seen"] = first_seen

    st.divider()
    if st.button("Limpiar Lista", use_container_width=True):
        st.session_state.candidates = []
        st.session_state.uploader_key = f"u{pd.Timestamp.utcnow().value}"
        st.rerun()

# ======================================================================================
# TABS
# ======================================================================================
tab_puestos, tab_eval, tab_pipe, tab_ger, tab_hh, tab_oferta, tab_onb, tab_ai = st.tabs(
    [
        "📄 Puestos",
        "🧪 Evaluación de CVs",
        "👥 Pipeline de Candidatos",
        "👔 Entrevista (Gerencia)",
        "🧰 Tareas del Headhunter",
        "📑 Oferta",
        "📦 Onboarding",
        "🤖 Asistente IA",   # NUEVO
    ]
)

# --------------------------------------------------------------------------------------
# TAB 1: PUESTOS
# --------------------------------------------------------------------------------------
with tab_puestos:
    st.markdown("## SelektIA – **Puestos**")
    col_top_l, col_top_c, col_top_r = st.columns([1.8, 1, 1])
    with col_top_l:
        q = st.text_input("Buscar (puesto, ubicación, ID, hiring manager…)", placeholder="Ej: Lima, 10645194, Angela Cruz")
    with col_top_c:
        st.text("")
        show_filters = st.checkbox("Mostrar filtros", value=False)
    with col_top_r:
        st.metric("Puestos totales", len(st.session_state.positions))

    df_pos = st.session_state.positions.copy()
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
                dias_abierto = st.slider("Días abierto (máx)", min_value=0, max_value=60, value=60)
        if show_filters:
            if ubic: df_pos = df_pos[df_pos["Ubicación"].isin(ubic)]
            if hm: df_pos = df_pos[df_pos["Hiring Manager"].isin(hm)]
            if estado: df_pos = df_pos[df_pos["Estado"].isin(estado)]
            df_pos = df_pos[df_pos["Días Abierto"] <= dias_abierto]

    if q:
        ql = q.lower()
        df_pos = df_pos[
            df_pos["Puesto"].str.lower().str.contains(ql) |
            df_pos["Ubicación"].str.lower().str.contains(ql) |
            df_pos["Hiring Manager"].str.lower().str.contains(ql) |
            df_pos["ID"].astype(str).str.contains(ql)
        ]

    st.caption(f"Mostrando **{len(df_pos)}** posiciones")
    st.dataframe(
        df_pos[
            [
                "Puesto", "Días Abierto", "Leads", "Nuevos", "Recruiter Screen",
                "HM Screen", "Entrevista Telefónica", "Entrevista Presencial",
                "Ubicación", "Hiring Manager", "Estado", "ID"
            ]
        ].sort_values(["Estado","Días Abierto","Leads"], ascending=[True, True, False]),
        use_container_width=True,
        height=400,
    )

# --------------------------------------------------------------------------------------
# TAB 2: EVALUACIÓN DE CVS
# --------------------------------------------------------------------------------------
with tab_eval:
    st.markdown("## SelektIA – **Resultados de evaluación**")

    if not st.session_state.candidates:
        st.info("Carga CVs en la barra lateral. El análisis se ejecuta automáticamente.")
    else:
        df = pd.DataFrame(st.session_state.candidates)
        df_sorted = df.sort_values("Score", ascending=False)

        st.markdown("### Ranking de Candidatos")
        st.dataframe(
            df_sorted[["Name", "Score", "Reasons"]],
            use_container_width=True,
            height=240
        )

        st.markdown("### Comparación de puntajes")
        bar_colors = [BAR_GOOD if s >= 60 else BAR_DEFAULT for s in df_sorted["Score"]]
        fig = px.bar(df_sorted, x="Name", y="Score", title="Comparación de puntajes (todos los candidatos)")
        fig.update_traces(marker_color=bar_colors, hovertemplate="%{x}<br>Score: %{y}")
        fig.update_layout(plot_bgcolor="#FFFFFF", paper_bgcolor="rgba(0,0,0,0)", font=dict(color=TITLE_DARK), xaxis_title=None, yaxis_title="Score")
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("### Visor de CV (PDF/TXT)  ↪️")
        all_names = df_sorted["Name"].tolist()
        selected_name = st.selectbox("Elige un candidato", all_names, index=0, key="pdf_candidate", label_visibility="collapsed")
        cand = df.loc[df["Name"] == selected_name].iloc[0]
        if cand["_is_pdf"] and cand["_bytes"]:
            pdf_viewer_pdfjs(cand["_bytes"], height=480, scale=1.10)
            st.download_button(f"Descargar {selected_name}", data=cand["_bytes"], file_name=selected_name, mime="application/pdf")
        else:
            st.info(f"'{selected_name}' es un TXT. Mostrando contenido abajo:")
            with st.expander("Ver contenido TXT", expanded=True):
                try:
                    txt = cand["_bytes"].decode("utf-8", errors="ignore")
                except Exception:
                    txt = "(No se pudo decodificar)"
                st.text_area("Contenido", value=txt, height=400, label_visibility="collapsed")

# --------------------------------------------------------------------------------------
# TAB 3: PIPELINE
# --------------------------------------------------------------------------------------
with tab_pipe:
    st.markdown("## SelektIA – **Pipeline de Candidatos**")
    if not st.session_state.candidates:
        st.info("Primero sube CVs en la barra lateral para armar el pipeline.")
    else:
        df = pd.DataFrame(st.session_state.candidates).sort_values("Score", ascending=False)
        c_l, c_r = st.columns([1.35, 1])
        with c_l:
            st.markdown("**Candidatos detectados (clic para ver detalle):**")
            show = df[["Name", "Score"]].copy()
            show.rename(columns={"Name": "Candidato", "Score": "Match (%)"}, inplace=True)
            st.dataframe(show, use_container_width=True, height=260)

            default_idx = 0
            if st.session_state.pipeline_selected and st.session_state.pipeline_selected in df["Name"].tolist():
                default_idx = df["Name"].tolist().index(st.session_state.pipeline_selected)
            selected_name = st.selectbox("Selecciona para detalle", df["Name"].tolist(), index=default_idx)
            st.session_state.pipeline_selected = selected_name

            st.markdown("**Acciones rápidas**")
            colA, colB = st.columns(2)
            with colA:
                if st.button("Mover a ‘Entrevista (Gerencia)’", use_container_width=True):
                    if selected_name not in st.session_state.gerencia_list:
                        st.session_state.gerencia_list.append(selected_name)
                    st.success(f"{selected_name} movido a Entrevista (Gerencia).")
            with colB:
                if st.button("Añadir nota ‘Buen encaje’", use_container_width=True):
                    st.info("Nota guardada (demo).")

        with c_r:
            st.markdown("### Detalle del candidato")
            cand = df.loc[df["Name"] == st.session_state.pipeline_selected].iloc[0]
            st.caption(cand["Name"])
            score = int(cand["Score"])
            badge = "<span class='badge badge-green'>Match estimado: Alto</span>" if score>=70 else "<span class='badge badge-amber'>Match estimado: Medio</span>" if score>=60 else "<span class='badge badge-gray'>Match estimado: Bajo</span>"
            st.markdown(badge, unsafe_allow_html=True)
            st.markdown("**Validated Skills**")
            st.markdown(chips(cand["_validated"], "badge-green"), unsafe_allow_html=True)
            st.markdown("**Likely Skills**")
            st.markdown(chips(cand["_likely"], "badge-amber"), unsafe_allow_html=True)
            st.markdown("**Skills to Validate**")
            st.markdown(chips(cand["_to_validate"], "badge-gray"), unsafe_allow_html=True)

# --------------------------------------------------------------------------------------
# TAB 4: ENTREVISTA (GERENCIA)
# --------------------------------------------------------------------------------------
with tab_ger:
    st.markdown("## SelektIA – **Entrevista (Gerencia)**")
    if not st.session_state.gerencia_list:
        st.info("Aún no hay candidatos en esta etapa. Muévelos desde ‘Pipeline de Candidatos’.")
    else:
        st.markdown("**Candidatos en entrevista (gerencia):**")
        for n in st.session_state.gerencia_list:
            st.markdown(f"- {n}")
        st.markdown("---")
        st.markdown("### Asignar headhunter")
        hh = st.selectbox("Headhunter asignado", ["Carla P.", "Luis M.", "Andrea G."], index=0)
        if st.button("Asignar / Reasignar"):
            st.success(f"Headhunter asignado: {hh}")

# --------------------------------------------------------------------------------------
# TAB 5: TAREAS DEL HEADHUNTER
# --------------------------------------------------------------------------------------
with tab_hh:
    st.markdown("## SelektIA – **Tareas del Headhunter**")
    if not st.session_state.gerencia_list:
        st.info("No hay candidatos en ‘Entrevista (Gerencia)’.")
    else:
        candidate = st.selectbox("Candidata/o", st.session_state.gerencia_list, index=0, key="hh_sel")
        data = st.session_state.hh_tasks.get(candidate, {
            "check_contacto": False, "check_agenda": False, "check_feedback": False,
            "fortalezas": "", "riesgos": "", "pretension": "", "disponibilidad": "",
            "due_date": (datetime.utcnow() + timedelta(days=1)).date().isoformat(), "enviado_comite": False,
        })

        c1, c2, c3 = st.columns(3)
        with c1: data["check_contacto"] = st.checkbox("✅ Contacto hecho", value=data["check_contacto"])
        with c2: data["check_agenda"] = st.checkbox("✅ Entrevista agendada", value=data["check_agenda"])
        with c3: data["check_feedback"] = st.checkbox("✅ Feedback recibido", value=data["check_feedback"])

        st.markdown("**Notas obligatorias**")
        data["fortalezas"] = st.text_input("3 fortalezas (breve)", value=data["fortalezas"])
        data["riesgos"] = st.text_input("2 riesgos (breve)", value=data["riesgos"])
        c4, c5 = st.columns(2)
        with c4: data["pretension"] = st.text_input("Pretensión salarial", value=data["pretension"], placeholder="S/ 3,500")
        with c5: data["disponibilidad"] = st.text_input("Disponibilidad", value=data["disponibilidad"], placeholder="Inmediata / 2 semanas")

        st.markdown("**Adjuntos (BLS/ACLS, colegiatura, etc.)**")
        _ = st.file_uploader("Sube PDFs o imágenes", type=["pdf","png","jpg","jpeg"], accept_multiple_files=True, key=f"hh_up_{candidate}")

        colD, colE = st.columns(2)
        with colD: data["due_date"] = st.date_input("Fecha límite (SLA)", value=pd.to_datetime(data["due_date"]))
        with colE:
            due = pd.to_datetime(data["due_date"]); now = pd.to_datetime(datetime.utcnow().date())
            delta = (due - now).days
            if delta < 0: st.markdown("<span class='badge badge-red'>SLA vencido</span>", unsafe_allow_html=True)
            elif delta <= 1: st.markdown("<span class='badge badge-amber'>SLA ≤ 24h</span>", unsafe_allow_html=True)
            else: st.markdown("<span class='badge badge-green'>En plazo</span>", unsafe_allow_html=True)

        st.session_state.hh_tasks[candidate] = data
        st.markdown("---")
        colF, colG = st.columns([1,1])
        with colF:
            if st.button("Guardar", use_container_width=True):
                st.session_state.hh_tasks[candidate] = data
                st.success("Tareas guardadas.")
        with colG:
            disabled_send = not (data["check_contacto"] and data["check_agenda"] and data["check_feedback"] and data["fortalezas"] and data["riesgos"])
            if st.button("Enviar a Comité", use_container_width=True, disabled=disabled_send):
                data["enviado_comite"] = True
                st.session_state.hh_tasks[candidate] = data
                if candidate not in st.session_state.gerencia_list:
                    st.session_state.gerencia_list.append(candidate)
                st.success("Enviado a Comité. Checklists bloqueados.")
        if data.get("enviado_comite"):
            st.info("Checklists bloqueados por envío a Comité.")

# --------------------------------------------------------------------------------------
# Helper onboarding
# --------------------------------------------------------------------------------------
def _default_onboarding_tasks(inicio_fecha: date):
    today = datetime.utcnow().date()
    return {
        "contrato_firmado": {"label":"Contrato firmado","done":False,"due": today + timedelta(days=2),"resp":"RR.HH.","files":[]},
        "docs_completos": {"label":"Documentos completos (DNI, colegiatura, BLS/ACLS, 2 referencias, cuenta)","done":False,"due": today + timedelta(days=3),"resp":"RR.HH.","files":[]},
        "usuario_email": {"label":"Usuario/email creado","done":False,"due": today + timedelta(days=1),"resp":"TI","files":[]},
        "acceso_sap": {"label":"Acceso SAP IS-H","done":False,"due": today + timedelta(days=2),"resp":"TI","files":[]},
        "examen_medico": {"label":"Examen médico de ingreso","done":False,"due": today + timedelta(days=5),"resp":"Salud Ocupacional","files":[]},
        "induccion_dia1": {"label":"Inducción día 1 (agenda)","done":False,"due": inicio_fecha,"resp":"RR.HH.","files":[]},
        "epp_uniforme": {"label":"EPP/Uniforme entregado","done":False,"due": inicio_fecha,"resp":"Seguridad/Almacén","files":[]},
        "plan_30_60_90": {"label":"Plan 30-60-90 cargado","done":False,"due": inicio_fecha + timedelta(days=7),"resp":"Jefe Directo","files":[]},
        "asignaciones": {"jefe_directo":"", "tutor":"","rrhh_resp":"","ti_resp":""},
    }

def _sla_badge(due_date):
    due = pd.to_datetime(due_date); now = pd.to_datetime(datetime.utcnow().date())
    delta = (due - now).days
    if delta < 0: return "<span class='badge badge-red'>Vencido</span>"
    elif delta <= 1: return "<span class='badge badge-amber'>≤ 24h</span>"
    else: return "<span class='badge badge-green'>En plazo</span>"

# --------------------------------------------------------------------------------------
# TAB 6: OFERTA
# --------------------------------------------------------------------------------------
with tab_oferta:
    st.markdown("## SelektIA – **Oferta**")
    if not st.session_state.gerencia_list:
        st.info("No hay candidatos en etapa final.")
    else:
        cand = st.selectbox("Candidata/o para oferta", st.session_state.gerencia_list, index=0)
        accepted = [o for o in st.session_state.ofertas if o["candidato"]==cand and o["estado"]=="Aceptada"]
        if accepted:
            o = accepted[-1]
            st.success("Propuesta aceptada. Edición bloqueada (solo lectura).")
            colA, colB, colC = st.columns(3)
            with colA: st.text_input("Puesto", value=o["puesto"], disabled=True)
            with colB: st.text_input("Ubicación", value=o["ubicacion"], disabled=True)
            with colC: st.text_input("Modalidad", value=o["modalidad"], disabled=True)
            colD, colE, colF = st.columns(3)
            with colD: st.text_input("Contrato", value=o["contrato"], disabled=True)
            with colE: st.text_input("Salario (rango/neto)", value=o["salario"], disabled=True)
            with colF: st.text_input("Beneficios", value=o["beneficios"], disabled=True)
            colG, colH = st.columns(2)
            with colG: st.text_input("Inicio", value=o["inicio"], disabled=True)
            with colH: st.text_input("Caducidad", value=o["caducidad"], disabled=True)
            st.text_input("Aprobadores", value=", ".join(o["aprobadores"]), disabled=True)
            if cand in st.session_state.metrics:
                m = st.session_state.metrics[cand]
                ttostr = f"TTO: {m.get('tto_days','-')} días • TTF: {m.get('ttf_days','-')} días"
                st.info(ttostr)
        else:
            with st.form("form_oferta"):
                c1, c2, c3 = st.columns(3)
                with c1: puesto_o = st.text_input("Puesto", value=st.session_state.get("puesto",""))
                with c2: ubic_o = st.selectbox("Ubicación", ["Lima, Perú","Santiago, Chile","Ciudad de México, MX","Remoto LATAM"])
                with c3: modalidad_o = st.selectbox("Modalidad", ["Presencial","Híbrido","Remoto"])
                c4, c5, c6 = st.columns(3)
                with c4: contrato_o = st.selectbox("Tipo de contrato", ["Indeterminado","Plazo fijo","Servicio (honorarios)"])
                with c5: salario_o = st.text_input("Salario (rango y neto)", placeholder="S/ 4,500 neto")
                with c6: beneficios_o = st.text_input("Bonos/beneficios", placeholder="Bono anual, EPS…")
                c7, c8 = st.columns(2)
                with c7: inicio_o = st.date_input("Fecha de inicio", value=datetime.utcnow().date() + timedelta(days=14))
                with c8: caduca_o = st.date_input("Caducidad de oferta", value=datetime.utcnow().date() + timedelta(days=7))
                aprobadores = st.multiselect("Aprobadores", ["Gerencia","Legal","Finanzas"], default=["Gerencia","Legal","Finanzas"])
                submitted = st.form_submit_button("Generar oferta (PDF) + Registrar")
                if submitted:
                    st.session_state.ofertas.append({
                        "candidato": cand, "puesto": puesto_o, "ubicacion": ubic_o, "modalidad": modalidad_o,
                        "contrato": contrato_o, "salario": salario_o, "beneficios": beneficios_o,
                        "inicio": str(inicio_o), "caducidad": str(caduca_o), "aprobadores": aprobadores,
                        "estado": "Enviada", "historial": [f"{datetime.utcnow().isoformat()} - Generada y enviada"],
                        "generated_at": datetime.utcnow().isoformat(),
                    })
                    st.session_state.metrics.setdefault(cand, {})["offer_generated_at"] = st.session_state.ofertas[-1]["generated_at"]
                    st.success("Oferta generada y registrada (demo).")

        if st.session_state.ofertas:
            st.markdown("### Ofertas registradas")
            df_o = pd.DataFrame(st.session_state.ofertas)
            st.dataframe(df_o, use_container_width=True, height=260)
            st.markdown("**Acciones**")
            idx = st.number_input("Índice de oferta", min_value=0, max_value=len(st.session_state.ofertas)-1, value=0, step=1)
            colH, colI, colJ = st.columns(3)
            with colH:
                if st.button("Marcar aceptada"):
                    st.session_state.ofertas[idx]["estado"] = "Aceptada"
                    st.session_state.ofertas[idx]["historial"].append(f"{datetime.utcnow().isoformat()} - Aceptada")
                    candX = st.session_state.ofertas[idx]["candidato"]
                    st.session_state.metrics.setdefault(candX, {})
                    st.session_state.metrics[candX]["offer_accepted_at"] = datetime.utcnow().isoformat()
                    gen_at = st.session_state.metrics[candX].get("offer_generated_at")
                    if gen_at:
                        tto = (pd.to_datetime(st.session_state.metrics[candX]["offer_accepted_at"]) - pd.to_datetime(gen_at)).days
                        st.session_state.metrics[candX]["tto_days"] = int(tto)
                    first_seen = st.session_state.metrics[candX].get("first_seen")
                    if first_seen:
                        ttf = (pd.to_datetime(st.session_state.metrics[candX]["offer_accepted_at"]) - pd.to_datetime(first_seen)).days
                        st.session_state.metrics[candX]["ttf_days"] = int(ttf)
                    inicio_dt = pd.to_datetime(st.session_state.ofertas[idx]["inicio"]).date()
                    if candX not in st.session_state.onboarding:
                        st.session_state.onboarding[candX] = _default_onboarding_tasks(inicio_dt)
                    st.success("Oferta aceptada y tareas de Onboarding generadas.")
            with colI:
                if st.button("Registrar contraoferta"):
                    st.session_state.ofertas[idx]["estado"] = "Contraoferta"
                    st.session_state.ofertas[idx]["historial"].append(f"{datetime.utcnow().isoformat()} - Contraoferta")
                    st.info("Contraoferta registrada.")
            with colJ:
                if st.button("Marcar rechazada"):
                    st.session_state.ofertas[idx]["estado"] = "Rechazada"
                    st.session_state.ofertas[idx]["historial"].append(f"{datetime.utcnow().isoformat()} - Rechazada")
                    st.warning("Oferta rechazada.")

# --------------------------------------------------------------------------------------
# TAB 7: ONBOARDING
# --------------------------------------------------------------------------------------
with tab_onb:
    st.markdown("## SelektIA – **Onboarding**")
    accepted_cands = [o["candidato"] for o in st.session_state.ofertas if o["estado"]=="Aceptada"]
    if not accepted_cands:
        st.info("Aún no hay ofertas aceptadas. Marca una oferta como Aceptada para iniciar onboarding.")
    else:
        cand = st.selectbox("Candidata/o", sorted(set(accepted_cands)), index=0)
        if cand not in st.session_state.onboarding:
            off = [o for o in st.session_state.ofertas if o["candidato"]==cand and o["estado"]=="Aceptada"]
            inicio_dt = pd.to_datetime(off[-1]["inicio"]).date() if off else datetime.utcnow().date() + timedelta(days=14)
            st.session_state.onboarding[cand] = _default_onboarding_tasks(inicio_dt)
        data = st.session_state.onboarding[cand]
        if cand in st.session_state.metrics:
            m = st.session_state.metrics[cand]
            st.info(f"TTO: {m.get('tto_days','-')} días • TTF: {m.get('ttf_days','-')} días")

        st.markdown("### Checklist con SLA")
        task_keys = ["contrato_firmado","docs_completos","usuario_email","acceso_sap","examen_medico","induccion_dia1","epp_uniforme","plan_30_60_90"]
        for k in task_keys:
            row = data[k]
            col1, col2, col3, col4 = st.columns([0.6, 0.2, 0.2, 0.6])
            with col1: row["done"] = st.checkbox(row["label"], value=row["done"], key=f"onb_done_{cand}_{k}")
            with col2: row["due"] = st.date_input("Vence", value=row["due"], key=f"onb_due_{cand}_{k}")
            with col3:
                opts = ["RR.HH.","TI","Salud Ocupacional","Seguridad/Almacén","Jefe Directo"]
                row["resp"] = st.selectbox("Resp.", opts, index=opts.index(row["resp"]) if row["resp"] in opts else 0, key=f"onb_resp_{cand}_{k}")
            with col4:
                st.markdown(_sla_badge(row["due"]), unsafe_allow_html=True)
                up = st.file_uploader("Adjuntos", type=["pdf","png","jpg","jpeg"], accept_multiple_files=True, key=f"onb_up_{cand}_{k}")
                if up: row["files"] = [u.name for u in up]
            data[k] = row
            st.divider()

        st.markdown("### Asignaciones")
        colA, colB, colC, colD = st.columns(4)
        with colA: data["asignaciones"]["jefe_directo"] = st.text_input("Jefe directo", value=data["asignaciones"].get("jefe_directo",""))
        with colB: data["asignaciones"]["tutor"] = st.text_input("Tutor/Buddy", value=data["asignaciones"].get("tutor",""))
        with colC: data["asignaciones"]["rrhh_resp"] = st.text_input("RR.HH. responsable", value=data["asignaciones"].get("rrhh_resp",""))
        with colD: data["asignaciones"]["ti_resp"] = st.text_input("TI responsable", value=data["asignaciones"].get("ti_resp",""))
        st.session_state.onboarding[cand] = data
        st.markdown("---")
        colX, colY, colZ = st.columns(3)
        with colX:
            if st.button("Guardar Onboarding", use_container_width=True): st.success("Onboarding guardado.")
        with colY:
            if st.button("Generar Carta de bienvenida (PDF)", use_container_width=True): st.info("Carta de bienvenida generada (demo).")
        with colZ:
            if st.button("Exportar a Payroll/HRIS", use_container_width=True): st.success("Exportado (demo).")

# --------------------------------------------------------------------------------------
# TAB 8: 🤖 ASISTENTE IA (ROLES Y PERMISOS)  — NUEVO
# --------------------------------------------------------------------------------------
with tab_ai:
    st.markdown("## SelektIA – **Asistente IA / Roles y Permisos**")

    # Selector de rol (solo demostrativo; no bloquea otras pestañas aún)
    roles = [
        "Admin RR.HH. (Owner)","Coordinador RR.HH.","Headhunter","Hiring Manager (HM)",
        "Gerencia/Comité","Legal","Finanzas","TI / Onboarding","Solo lectura"
    ]
    st.session_state.current_role = st.selectbox("Tu rol actual (demo):", roles, index=roles.index(st.session_state.current_role) if st.session_state.current_role in roles else 1)

    st.markdown("### Reglas clave")
    st.markdown("""
- **RLS (Row-Level Security):** cada rol ve solo sus puestos/candidatos asignados (HH y HM por posición).
- **Action-Level:** separar *crear/enviar oferta* de *aprobar oferta*.
- **Adjuntos sensibles:** visibles para RR.HH., Gerencia y Legal; HH solo ve/sube los suyos.
- **Auditoría:** todas las transiciones (quién/cuándo, IP) y descargas de adjuntos.
- **SLA/Recordatorios:** por rol (HH: contacto/feedback; HM: calificar entrevista; Legal/Finanzas: aprobar oferta; TI: accesos día 1).
- **Export:** solo Admin/Coord pueden CSV completos; otros un recorte.
    """)

    st.markdown("### Permisos por pestaña (resumen)")
    perm = pd.DataFrame([
        ["Puestos","E","E","V","V","V","V","V","V"],
        ["Evaluación de CVs","E","E","V","-","-","-","-","-"],
        ["Pipeline","E","E","E","E","V","V","V","V"],
        ["Tareas HH","E","E","E","-","V","V","V","V"],
        ["Entrevista (Gerencia)","E","E","V","E","E","V","V","V"],
        ["Oferta (crear/enviar)","E","E","V","V","V","V","V","V"],
        ["Oferta (aprobar)","A","A","-","-","A","A","-","-"],
        ["Onboarding","E","E","V","V","V","V","E","V"],
        ["Reportes/Export","E","E","V","V","V","V","V","V"],
    ], columns=["Pestaña","Admin","Coord","HH","HM","Gerencia","Legal","Finanzas","TI/Solo lectura"])
    st.dataframe(perm, use_container_width=True, height=330)

    st.markdown("### Recomendaciones de implementación")
    st.markdown("""
- **RBAC** en la capa de datos (roles + permisos + *scope* por puesto).
- **Feature flags** por acción (ej.: `crear_oferta`, `aprobar_oferta`, `mover_pipeline_x`).
- **Guardias de UI:** deshabilitar botón y *tooltip* (“No tienes permiso para aprobar ofertas”).
- **Plantillas de auditoría:** `user_id`, `role`, `action`, `object_id`, `before/after`, `ts`, `ip`.
    """)

    st.markdown("### Demo rápida de feature flags (local)")
    ff = st.session_state.feature_flags
    colf1, colf2, colf3 = st.columns(3)
    with colf1: ff["crear_oferta"] = st.checkbox("crear_oferta", value=ff.get("crear_oferta", True))
    with colf2: ff["aprobar_oferta"] = st.checkbox("aprobar_oferta", value=ff.get("aprobar_oferta", False))
    with colf3: ff["mover_pipeline"] = st.checkbox("mover_pipeline", value=ff.get("mover_pipeline", True))
    st.session_state.feature_flags = ff

    st.markdown("### Auditoría (demo)")
    if st.button("Registrar evento de auditoría (demo)"):
        event = {
            "ts": datetime.utcnow().isoformat(),
            "user_role": st.session_state.current_role,
            "action": "view_permissions",
            "object_id": "asistente_ia",
            "before": None,
            "after": {"feature_flags": ff},
            "ip": "0.0.0.0",
        }
        st.session_state.audit_log.append(event)
        st.success("Evento registrado (demo).")

    if st.session_state.audit_log:
        st.markdown("**Eventos recientes**")
        st.dataframe(pd.DataFrame(st.session_state.audit_log).tail(5), use_container_width=True, height=180)
