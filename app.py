# app.py
# -*- coding: utf-8 -*-

import io
import re
import base64
from pathlib import Path
from datetime import date

import streamlit as st
import pandas as pd
import plotly.express as px
from PyPDF2 import PdfReader

# ======================================================================================
# TEMA / COLORES (mantenemos la base que ya te funciona)
# ======================================================================================
PRIMARY_GREEN = "#00CD78"
SIDEBAR_BG = "#10172A"        # fondo columna izquierda
BOX_DARK = "#132840"          # fondo y borde de boxes del sidebar
BOX_DARK_HOV = "#193355"      # borde en hover/focus del sidebar
TEXT_LIGHT = "#FFFFFF"        # texto blanco
MAIN_BG = "#F7FBFF"           # fondo del cuerpo (claro)
BOX_LIGHT = "#F1F7FD"         # fondo claro de inputs en el cuerpo
BOX_LIGHT_B = "#E3EDF6"       # borde claro de inputs en el cuerpo
TITLE_DARK = "#142433"        # títulos
BAR_DEFAULT = "#E9F3FF"       # color barras por defecto
BAR_GOOD = "#33FFAC"          # color barras >=60

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
.block-container {{
  background: transparent !important;
}}

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

/* 4 boxes del panel izquierdo con el mismo diseño */
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
[data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] * {{
  color: var(--text) !important;
}}
[data-testid="stSidebar"] [data-testid="stFileUploaderFile"] {{
  background: var(--box) !important;
  border: 1px solid var(--box) !important;
  color: var(--text) !important;
}}

/* Botón verde (sidebar y cuerpo) */
.stButton > button {{
  background: var(--green) !important;
  color: #082017 !important;
  border-radius: 10px !important;
  border: none !important;
  padding: .45rem .9rem !important;
  font-weight: 600 !important;
}}
.stButton > button:hover {{
  filter: brightness(0.95);
}}

/* Títulos del cuerpo */
h1, h2, h3 {{
  color: var(--title-dark);
}}
h1 strong, h2 strong, h3 strong {{
  color: var(--green);
}}

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

/* Chips */
.badge {{
  display:inline-block; padding:.22rem .5rem; border-radius:999px;
  background:#EEF5FF; border:1px solid #D6E6FF; color:#104071; font-size:.82rem; margin:.15rem .25rem;
}}
.badge.green {{
  background:#E9FFF7; border-color:#BDF3E2; color:#084735;
}}
.badge.gray {{
  background:#F3F4F6; border-color:#E5E7EB; color:#374151;
}}
.dot {{
  width:10px;height:10px;border-radius:999px;display:inline-block;margin-right:4px;background:#D1D5DB;
}}
.dot.on {{ background:#12B981; }}
"""

st.set_page_config(page_title="SelektIA", page_icon="🧠", layout="wide")
st.markdown(f"<style>{CSS}</style>", unsafe_allow_html=True)

# ======================================================================================
# UTILIDADES
# ======================================================================================

def extract_text_from_file(uploaded_file) -> str:
    """Extrae texto de PDF (PyPDF2) o TXT sin agotar el buffer que usamos para el visor."""
    try:
        suffix = Path(uploaded_file.name).suffix.lower()
        uploaded_file.seek(0)
        if suffix == ".pdf":
            pdf_reader = PdfReader(io.BytesIO(uploaded_file.read()))
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() or ""
            return text
        else:
            uploaded_file.seek(0)
            return uploaded_file.read().decode("utf-8", errors="ignore")
    except Exception as e:
        st.error(f"Error al leer '{uploaded_file.name}': {e}")
        return ""

def simple_score(cv_text: str, jd: str, keywords: str) -> tuple[int, str]:
    """Score simple por coincidencia de palabras clave y términos del JD."""
    base = 0
    reasons = []
    text_low = cv_text.lower()
    jd_low = jd.lower()
    # keywords
    hits = 0
    kws = [k.strip().lower() for k in keywords.split(",") if k.strip()]
    coincidencias = []
    for k in kws:
        if k and k in text_low:
            hits += 1
            coincidencias.append(k)
    if kws:
        pct_k = hits / len(kws)
        base += int(pct_k * 70)
        reasons.append(f"{hits}/{len(kws)} keywords encontradas — Coincidencias: {', '.join(coincidencias) or 'ninguna'}")
    # JD aprox
    jd_terms = [t for t in set(jd_low.split()) if len(t) > 3]
    match_terms = sum(1 for t in jd_terms if t in text_low)
    if jd_terms:
        pct_jd = match_terms / len(jd_terms)
        base += int(pct_jd * 30)
        reasons.append("Coincidencias con el JD (aprox.)")
    base = max(0, min(100, base))
    return base, " — ".join(reasons)

def pdf_viewer_pdfjs(file_bytes: bytes, height=520, scale=1.1):
    """Visor usando pdf.js (probado que te funciona)."""
    if not file_bytes:
        st.warning("No hay bytes para mostrar.")
        return
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

# ---- análisis de habilidades para el panel de detalles ----
SYN_MAP = {
    "his": ["hospital information system", "history information system"],
    "sap is-h": ["sap ish", "sap hospital", "sap healthcare"],
    "bls": ["basic life support"],
    "acls": ["advanced cardiac life support"],
    "iaas": ["infection", "asepsia", "esterilización"],
    "educación al paciente": ["patient education", "health education"],
    "seguridad del paciente": ["patient safety"],
    "protocolos": ["protocol", "guideline", "sop"],
}

def analyze_skills(text: str, kw_csv: str, jd: str):
    t = (text or "").lower()
    kws = [k.strip().lower() for k in kw_csv.split(",") if k.strip()]
    validated = []
    likely = set()
    for k in kws:
        if k in t:
            validated.append(k)
        # sinónimos como "likely"
        for syn in SYN_MAP.get(k, []):
            if syn in t:
                likely.add(k)
    # a validar = keywords del JD que no aparecen
    jd_terms = [k for k in kws if k not in validated]  # simple
    to_validate = [k for k in jd_terms if k not in likely][:8]
    return validated[:10], sorted(list(likely))[:10], to_validate[:10]

def detect_years(text: str) -> int | None:
    """Detecta años de experiencia muy simple."""
    if not text:
        return None
    t = text.lower()
    m = re.search(r'(\d+)\s*\+?\s*(?:years|year|años|año)\b', t)
    if m:
        try:
            return int(m.group(1))
        except:
            return None
    return None

def score_dots(score:int) -> str:
    on = min(5, max(0, round(score/20)))
    return "".join([f'<span class="dot {"on" if i<on else ""}"></span>' for i in range(5)])

# ======================================================================================
# ESTADO INICIAL
# ======================================================================================

if "candidates" not in st.session_state:
    st.session_state.candidates = []
if "uploader_key" not in st.session_state:
    st.session_state.uploader_key = "u1"
if "pipeline" not in st.session_state:
    st.session_state.pipeline = None  # DF editable del pipeline

# Datos demo de "Puestos"
if "positions" not in st.session_state:
    st.session_state.positions = pd.DataFrame([
        {"ID": 10645194, "Puesto": "Desarrollador/a Backend (Python)", "Ubicación": "Lima, Perú",
         "Leads": 1800, "Nuevos": 115, "Recruiter Screen": 35, "HM Screen": 7,
         "Entrevista Telefónica": 14, "Entrevista Presencial": 15, "Días Abierto": 3,
         "Hiring Manager": "Rivers Brykson", "Estado": "Abierto", "Creado": date.today()},
        {"ID": 10376646, "Puesto": "Planner de Demanda", "Ubicación": "Ciudad de México, MX",
         "Leads": 2300, "Nuevos": 26, "Recruiter Screen": 3, "HM Screen": 8,
         "Entrevista Telefónica": 6, "Entrevista Presencial": 3, "Días Abierto": 28,
         "Hiring Manager": "Rivers Brykson", "Estado": "Abierto", "Creado": date.today()},
        {"ID": 10376415, "Puesto": "VP de Marketing", "Ubicación": "Santiago, Chile",
         "Leads": 8100, "Nuevos": 1, "Recruiter Screen": 15, "HM Screen": 35,
         "Entrevista Telefónica": 5, "Entrevista Presencial": 7, "Días Abierto": 28,
         "Hiring Manager": "Angela Cruz", "Estado": "Abierto", "Creado": date.today()},
    ])

# ======================================================================================
# SIDEBAR (mantenemos diseño y 4 boxes)
# ======================================================================================

with st.sidebar:
    st.image("assets/logo-wayki.png", use_column_width=True)
    st.markdown("### Definición del puesto")

    puesto = st.selectbox(
        "Puesto",
        ["Enfermera/o Asistencial", "Tecnólogo/a Médico", "Recepcionista de Admisión", "Médico/a General", "Químico/a Farmacéutico/a"],
        index=0, key="puesto",
    )

    st.markdown("### Descripción del puesto (texto libre)")
    jd_text = st.text_area(
        "Resume el objetivo del puesto, responsabilidades, protocolos y habilidades deseadas.",
        height=120, key="jd", label_visibility="collapsed",
    )

    st.markdown("### Palabras clave del perfil\n*(ajústalas si es necesario)*")
    kw_text = st.text_area(
        "HIS, SAP IS-H, BLS, ACLS, IAAS, educación al paciente, seguridad…",
        value="HIS, SAP IS-H, BLS, ACLS, IAAS, educación al paciente, seguridad del paciente, protocolos",
        height=110, key="kw", label_visibility="collapsed",
    )

    st.markdown("### Subir CVs (PDF o TXT)")
    files = st.file_uploader(
        "Drag and drop files here",
        key=st.session_state.uploader_key,
        type=["pdf", "txt"],
        accept_multiple_files=True,
        label_visibility="collapsed",
    )

    # Proceso automático: cada vez que subes archivos, analizamos
    if files:
        st.session_state.candidates = []  # reset
        for f in files:
            f.seek(0)
            raw_bytes = f.read()            # bytes para visor
            f.seek(0)
            text = extract_text_from_file(f) # texto para scoring y skills
            score, reasons = simple_score(text, jd_text, kw_text)
            st.session_state.candidates.append({
                "Name": f.name,
                "Score": score,
                "Reasons": reasons,
                "_bytes": raw_bytes,
                "_is_pdf": Path(f.name).suffix.lower() == ".pdf",
                "_text": text,
            })
        st.session_state.pipeline = None

    st.divider()

    # Limpiar lista
    if st.button("Limpiar Lista", use_container_width=True):
        st.session_state.candidates = []
        st.session_state.pipeline = None
        st.session_state.uploader_key = f"u{pd.Timestamp.utcnow().value}"
        st.rerun()

# ======================================================================================
# CUERPO (Tabs: Puestos / Evaluación de CVs / Pipeline)
# ======================================================================================

tab_puestos, tab_eval, tab_pipeline = st.tabs(["📋 Puestos", "🧪 Evaluación de CVs", "👥 Pipeline de Candidatos"])

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

    if show_filters:
        with st.expander("Filtros", expanded=True):
            colf1, colf2, colf3, colf4 = st.columns(4)
            with colf1:
                ubic = st.multiselect("Ubicación", sorted(st.session_state.positions["Ubicación"].unique().tolist()))
            with colf2:
                hm = st.multiselect("Hiring Manager", sorted(st.session_state.positions["Hiring Manager"].unique().tolist()))
            with colf3:
                estado = st.multiselect("Estado", sorted(st.session_state.positions["Estado"].unique().tolist()))
            with colf4:
                dias_abierto = st.slider("Días abierto (máx)", min_value=0, max_value=60, value=60)

    df_pos = st.session_state.positions.copy()
    if 'q' in locals() and q:
        ql = q.lower()
        df_pos = df_pos[
            df_pos["Puesto"].str.lower().str.contains(ql) |
            df_pos["Ubicación"].str.lower().str.contains(ql) |
            df_pos["Hiring Manager"].str.lower().str.contains(ql) |
            df_pos["ID"].astype(str).str.contains(ql)
        ]
    if show_filters:
        if ubic: df_pos = df_pos[df_pos["Ubicación"].isin(ubic)]
        if hm: df_pos = df_pos[df_pos["Hiring Manager"].isin(hm)]
        if estado: df_pos = df_pos[df_pos["Estado"].isin(estado)]
        df_pos = df_pos[df_pos["Días Abierto"] <= dias_abierto]

    st.caption(f"Mostrando **{len(df_pos)}** posiciones")
    st.dataframe(
        df_pos[["Puesto","Días Abierto","Leads","Nuevos","Recruiter Screen","HM Screen",
                "Entrevista Telefónica","Entrevista Presencial","Ubicación","Hiring Manager","Estado","ID"]
        ].sort_values(["Estado","Días Abierto","Leads"], ascending=[True, True, False]),
        use_container_width=True, height=400,
    )

    st.markdown("---")
    st.markdown("### Crear nuevo puesto")
    with st.form("form_new_position", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        with c1:
            np_puesto = st.text_input("Puesto *", placeholder="Ej: Analista de Datos")
            np_ubi = st.text_input("Ubicación *", placeholder="Ej: Lima, Perú")
            np_hm = st.text_input("Hiring Manager *", placeholder="Nombre")
        with c2:
            np_leads = st.number_input("Leads", 0, 999999, 0, step=10)
            np_nuevos = st.number_input("Nuevos", 0, 999999, 0, step=1)
            np_dias = st.number_input("Días Abierto", 0, 999, 0, step=1)
        with c3:
            np_rs = st.number_input("Recruiter Screen", 0, 999999, 0, step=1)
            np_hms = st.number_input("HM Screen", 0, 999999, 0, step=1)
            np_tel = st.number_input("Entrevista Telefónica", 0, 999999, 0, step=1)
        c4, c5 = st.columns(2)
        with c4: np_on = st.number_input("Entrevista Presencial", 0, 999999, 0, step=1)
        with c5: np_estado = st.selectbox("Estado", ["Abierto","En pausa","Cerrado"], index=0)

        submitted = st.form_submit_button("Crear posición")
        if submitted:
            if not np_puesto or not np_ubi or not np_hm:
                st.warning("Completa los campos obligatorios (*)")
            else:
                new_row = {
                    "ID": int(pd.Timestamp.utcnow().timestamp()),
                    "Puesto": np_puesto, "Ubicación": np_ubi, "Leads": int(np_leads),
                    "Nuevos": int(np_nuevos), "Recruiter Screen": int(np_rs),
                    "HM Screen": int(np_hms), "Entrevista Telefónica": int(np_tel),
                    "Entrevista Presencial": int(np_on), "Días Abierto": int(np_dias),
                    "Hiring Manager": np_hm, "Estado": np_estado, "Creado": date.today(),
                }
                st.session_state.positions = pd.concat([st.session_state.positions, pd.DataFrame([new_row])], ignore_index=True)
                st.success("Puesto creado.")
                st.rerun()

# --------------------------------------------------------------------------------------
# TAB 2: EVALUACIÓN DE CVS (ranking + gráfico + visor PDF)
# --------------------------------------------------------------------------------------
with tab_eval:
    st.markdown("## SelektIA – **Resultados de evaluación**")

    if not st.session_state.candidates:
        st.info("Carga CVs en la barra lateral. El análisis se ejecuta automáticamente.")
    else:
        df = pd.DataFrame(st.session_state.candidates)
        df_sorted = df.sort_values("Score", ascending=False)

        st.markdown("### Ranking de Candidatos")
        st.dataframe(df_sorted[["Name", "Score", "Reasons"]], use_container_width=True, height=240)

        st.markdown("### Comparación de puntajes")
        bar_colors = [BAR_GOOD if s >= 60 else BAR_DEFAULT for s in df_sorted["Score"]]
        fig = px.bar(df_sorted, x="Name", y="Score", title="Comparación de puntajes")
        fig.update_traces(marker_color=bar_colors, hovertemplate="%{x}<br>Score: %{y}")
        fig.update_layout(plot_bgcolor="#FFFFFF", paper_bgcolor="rgba(0,0,0,0)", font=dict(color=TITLE_DARK),
                          xaxis_title=None, yaxis_title="Score", height=320)
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("### Visor de CV (PDF/TXT)  ↪️")
        names = df_sorted["Name"].tolist()
        selected = st.selectbox("Elige un candidato", names, index=0, key="pdf_candidate", label_visibility="collapsed")
        cand = df.loc[df["Name"] == selected].iloc[0]

        if cand["_is_pdf"] and cand["_bytes"]:
            pdf_viewer_pdfjs(cand["_bytes"], height=520, scale=1.10)
            st.download_button(f"Descargar {selected}", data=cand["_bytes"], file_name=selected, mime="application/pdf")
        else:
            st.info(f"'{selected}' es un TXT. Mostrando contenido abajo:")
            with st.expander("Ver contenido TXT", expanded=True):
                try:
                    txt = cand["_bytes"].decode("utf-8", errors="ignore")
                except Exception:
                    txt = "(No se pudo decodificar)"
                st.text_area("Contenido", value=txt, height=400, label_visibility="collapsed")

# --------------------------------------------------------------------------------------
# TAB 3: PIPELINE DE CANDIDATOS (nuevo, con panel de detalles estilo highlights)
# --------------------------------------------------------------------------------------
with tab_pipeline:
    st.markdown("## 👥 Pipeline de Candidatos")

    if not st.session_state.candidates:
        st.info("Primero sube CVs en la barra izquierda.")
    else:
        df = pd.DataFrame(st.session_state.candidates)
        df_sorted = df.sort_values("Score", ascending=False)

        # si aún no existe pipeline o cambió el set de nombres, lo construimos
        if st.session_state.pipeline is None or set(st.session_state.pipeline["Candidato"]) != set(df_sorted["Name"]):
            etapas = ["Leads", "Contactado", "Aplicante", "Entrevista (Gerencia)", "Oferta", "Archivado"]
            pipe = pd.DataFrame({
                "Candidato": df_sorted["Name"],
                "Match_%": df_sorted["Score"],
                "Etapa": "Leads",
                "Último_contacto": pd.NaT,
                "Fuente": ["CV"] * len(df_sorted),
                "Notas": ["" for _ in range(len(df_sorted))],
            })
            st.session_state.pipeline = pipe

        pipe = st.session_state.pipeline

        colL, colR = st.columns([1.35, 1])

        with colL:
            st.caption("Avanza etapas, registra contacto, fuente y notas. Haz clic para ver detalles a la derecha.")
            etapas = ["Leads", "Contactado", "Aplicante", "Entrevista (Gerencia)", "Oferta", "Archivado"]
            pipe_view = st.data_editor(
                pipe,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Match_%": st.column_config.NumberColumn("Match (%)", min_value=0, max_value=100, step=1, format="%d"),
                    "Etapa": st.column_config.SelectboxColumn("Etapa", options=etapas),
                    "Último_contacto": st.column_config.DateColumn("Último contacto"),
                    "Fuente": st.column_config.TextColumn("Fuente"),
                    "Notas": st.column_config.TextColumn("Notas"),
                },
                key="pipeline_editor"
            )
            st.session_state.pipeline = pipe_view

            c1, c2, _ = st.columns([1,1,2])
            with c1:
                if st.button("Mover Leads → Contactado"):
                    mask = pipe_view["Etapa"] == "Leads"
                    pipe_view.loc[mask, "Etapa"] = "Contactado"
                    st.session_state.pipeline = pipe_view
                    st.success("Se movieron los Leads a ‘Contactado’.")
                    st.rerun()
            with c2:
                if st.button("Marcar contacto hoy (en Contactado)"):
                    mask = pipe_view["Etapa"] == "Contactado"
                    pipe_view.loc[mask, "Último_contacto"] = pd.to_datetime(date.today())
                    st.session_state.pipeline = pipe_view
                    st.success("Se marcó ‘Último contacto’ (hoy) a quienes están en ‘Contactado’.")
                    st.rerun()

            with st.expander("Resumen por etapa"):
                resumen = pipe_view.groupby("Etapa").size().reset_index(name="Candidatos")
                st.dataframe(resumen, hide_index=True, use_container_width=True)

        # ---------------- Panel de detalles (tipo Highlights) ----------------
        with colR:
            st.markdown("### Detalle del candidato")
            sel_name = st.selectbox("Seleccionar", df_sorted["Name"].tolist(), index=0, key="pipeline_selected")

            sel_row = df.loc[df["Name"] == sel_name].iloc[0]
            sel_score = int(sel_row["Score"])
            sel_text = sel_row.get("_text", "") or ""

            years = detect_years(sel_text)
            validated, likely, to_validate = analyze_skills(sel_text, st.session_state.get("kw", kw_text), st.session_state.get("jd", jd_text))

            st.markdown(f"**{sel_name}**")
            st.caption("Perfil detectado a partir del CV")

            # Highlights head (dots + mensajes)
            st.markdown(
                f"""
                <div style="padding:.75rem 1rem;border:1px solid var(--box-light-border);border-radius:12px;background:#fff">
                  <div style="margin-bottom:.35rem;">{score_dots(sel_score)} <span style="color:#374151;">Match estimado</span></div>
                  <div class="badge green">Match basado en keywords/JD</div>
                  {"<div class='badge green'>10+ años de experiencia</div>" if years and years>=10 else ""}
                </div>
                """,
                unsafe_allow_html=True
            )

            st.markdown("##### Validated Skills")
            if validated:
                st.markdown("".join([f"<span class='badge'>{k}</span>" for k in validated]), unsafe_allow_html=True)
            else:
                st.caption("Sin coincidencias fuertes aún.")

            st.markdown("##### Likely Skills")
            if likely:
                st.markdown("".join([f"<span class='badge gray'>{k}</span>" for k in likely]), unsafe_allow_html=True)
            else:
                st.caption("No se detectaron sinónimos relevantes.")

            st.markdown("##### Skills to Validate")
            if to_validate:
                st.markdown("".join([f"<span class='badge'>{k}</span>" for k in to_validate]), unsafe_allow_html=True)
            else:
                st.caption("Todo parece validado respecto a tus keywords.")

            st.markdown("---")
            st.markdown("##### Acciones rápidas")
            if st.button("Añadir nota 'Buen encaje'", key="note1"):
                pr = st.session_state.pipeline
                pr.loc[pr["Candidato"] == sel_name, "Notas"] = pr.loc[pr["Candidato"] == sel_name, "Notas"].fillna("") + " | Buen encaje"
                st.session_state.pipeline = pr
                st.success("Nota agregada.")
            if st.button("Mover a ‘Entrevista (Gerencia)’", key="move_hm"):
                pr = st.session_state.pipeline
                pr.loc[pr["Candidato"] == sel_name, "Etapa"] = "Entrevista (Gerencia)"
                st.session_state.pipeline = pr
                st.success("Candidato movido.")
