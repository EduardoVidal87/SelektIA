# app.py
# -*- coding: utf-8 -*-

import io
import base64
from pathlib import Path
from datetime import date

import streamlit as st
import pandas as pd
import plotly.express as px
from PyPDF2 import PdfReader
from streamlit.components.v1 import html

# ======================================================================================
# TEMA / COLORES
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

html, body, [data-testid="stAppViewContainer"] {{
  background: var(--main-bg) !important;
}}
.block-container {{
  padding-top: 1.2rem !important;
  background: transparent !important;
}}

/* ====== Sidebar ====== */
[data-testid="stSidebar"] {{
  background: var(--sidebar-bg) !important;
  color: var(--text) !important;
}}
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3,
[data-testid="stSidebar"] h4,
[data-testid="stSidebar"] h5,
[data-testid="stSidebar"] h6 {{
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
.stButton > button {{
  background: var(--green) !important;
  color: #082017 !important;
  border-radius: 10px !important;
  border: none !important;
  padding: .45rem .9rem !important;
  font-weight: 600 !important;
}}
.stButton > button:hover {{ filter: brightness(0.95); }}

/* ====== Títulos del cuerpo ====== */
.section-title {{
  font-size: 1.95rem;
  font-weight: 800;
  letter-spacing: .2px;
  color: var(--title-dark);
}}
.section-title .hl {{
  color: var(--green);
}}

/* ====== Inputs claros del cuerpo ====== */
.block-container [data-testid="stSelectbox"] > div > div,
.block-container [data-baseweb="select"],
.block-container [data-testid="stTextInput"] input,
.block-container [data-testid="stTextArea"] textarea {{
  background: var(--box-light) !important;
  color: var(--title-dark) !important;
  border: 1.5px solid var(--box-light-border) !important;
  border-radius: 10px !important;
}}

/* ====== Tabla clara ====== */
.block-container table {{
  background: #fff !important;
  border: 1px solid var(--box-light-border) !important;
  border-radius: 8px !important;
}}
.block-container thead th {{
  background: var(--box-light) !important;
  color: var(--title-dark) !important;
}}

/* ====== Tabs estilo visible ====== */
[data-baseweb="tab-list"] {{
  gap: 10px;
  border-bottom: 2px solid #dcecfb;
  margin-bottom: .6rem;
}}
[data-baseweb="tab"] {{
  background: transparent !important;
  color: #73809a !important;
  padding: .45rem .9rem !important;
  border-radius: 10px 10px 0 0 !important;
  font-weight: 700 !important;
}}
[data-baseweb="tab"][aria-selected="true"] {{
  color: var(--green) !important;
  border-bottom: 3px solid var(--green) !important;
}}
/* Visor */
#pdf_candidate {{
  background: var(--box-light) !important;
  border: 1.5px solid var(--box-light-border) !important;
  color: var(--title-dark) !important;
  border-radius: 10px !important;
}}
.pdf-frame {{
  border: 1px solid var(--box-light-border);
  border-radius: 12px;
  overflow: hidden;
  background: #fff;
}}
"""

st.set_page_config(page_title="SelektIA", page_icon="🧠", layout="wide")
st.markdown(f"<style>{CSS}</style>", unsafe_allow_html=True)

# ======================================================================================
# UTILIDADES
# ======================================================================================

def h1_title(left: str, right_emphasis: str):
    st.markdown(f'<div class="section-title">{left} – <span class="hl">{right_emphasis}</span></div>', unsafe_allow_html=True)

def extract_text_from_file(uploaded_file) -> str:
    """Extrae texto de PDF (PyPDF2) o TXT."""
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
    """Score simple por coincidencia de palabras clave y términos del JD."""
    base = 0
    reasons = []
    text_low = cv_text.lower()
    jd_low = jd.lower()

    # palabras clave
    hits = 0
    kws = [k.strip().lower() for k in keywords.split(",") if k.strip()]
    for k in kws:
        if k and k in text_low:
            hits += 1
    if kws:
        pct_k = hits / len(kws)
        base += int(pct_k * 70)  # 70% del score
        reasons.append(f"{hits}/{len(kws)} keywords encontradas — Coincidencias: {', '.join([k for k in kws if k in text_low])[:120]}")

    # JD match (palabras únicas largas)
    jd_terms = [t for t in set(jd_low.split()) if len(t) > 3]
    match_terms = sum(1 for t in jd_terms if t in text_low)
    if jd_terms:
        pct_jd = match_terms / len(jd_terms)
        base += int(pct_jd * 30)  # 30% del score
        reasons.append("Coincidencias con el JD (aprox.)")

    base = max(0, min(100, base))
    return base, " — ".join(reasons)

def pdf_viewer_pdfjs(file_bytes: bytes, height=520, zoom=110):
    """Visor usando pdf.js (más estable en Streamlit Cloud)."""
    try:
        b64 = base64.b64encode(file_bytes).decode("utf-8")
        viewer = f"""
        <div class="pdf-frame">
          <iframe
            src="https://mozilla.github.io/pdf.js/web/viewer.html?file=data:application/pdf;base64,{b64}#zoom={zoom}"
            style="width:100%;height:{height}px;border:0;"
            allow="fullscreen"
          ></iframe>
        </div>
        """
        html(viewer, height=height + 8, scrolling=False)
    except Exception:
        st.warning("No se pudo embeber el PDF. Descárgalo y ábrelo localmente.")
        st.download_button("Descargar PDF", data=file_bytes, file_name="cv.pdf", mime="application/pdf")

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
            "ID": 10645194,
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
            "Creado": date.today(),
        },
        {
            "ID": 10376646,
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
            "Creado": date.today(),
        },
        {
            "ID": 10376415,
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
            "Creado": date.today(),
        },
    ])
if "interview_queue" not in st.session_state:
    # candidatos movidos a 'Entrevista (Gerencia)'
    st.session_state.interview_queue = []
if "headhunter_map" not in st.session_state:
    st.session_state.headhunter_map = {}  # {candidate: headhunter}

# ======================================================================================
# SIDEBAR (4 boxes fijos)
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

    # Proceso automático: cada vez que subes archivos, analizamos
    if files:
        st.session_state.candidates = []  # reset
        for f in files:
            raw = f.read()
            # guardamos bytes y texto por separado
            suffix = Path(f.name).suffix.lower()
            text = ""
            try:
                if suffix == ".pdf":
                    pdf_reader = PdfReader(io.BytesIO(raw))
                    for page in pdf_reader.pages:
                        text += page.extract_text() or ""
                else:
                    text = raw.decode("utf-8", errors="ignore")
            except Exception:
                text = ""
            score, reasons = simple_score(text, jd_text, kw_text)
            st.session_state.candidates.append({
                "Name": f.name,
                "Score": score,
                "Reasons": reasons,
                "_bytes": raw,
                "_is_pdf": suffix == ".pdf",
                "_text": text,
            })

    st.divider()
    if st.button("Limpiar Lista", use_container_width=True):
        st.session_state.candidates = []
        st.session_state.uploader_key = f"u{pd.Timestamp.utcnow().value}"  # reset uploader
        st.rerun()

# ======================================================================================
# TABS (Puestos, Evaluación, Pipeline, Entrevista)
# ======================================================================================
tabs = st.tabs(
    [
        "🗂️ Puestos",
        "🧪 Evaluación de CVs",
        "👥 Pipeline de Candidatos",
        "📁 Entrevista (Gerencia)",
    ]
)

# --------------------------------------------------------------------------------------
# TAB 1: PUESTOS
# --------------------------------------------------------------------------------------
with tabs[0]:
    h1_title("SelektIA", "Puestos")

    col_top_l, col_top_c, col_top_r = st.columns([1.8, 1, 1])
    with col_top_l:
        q = st.text_input("Buscar (puesto, ubicación, ID, hiring manager…)", placeholder="Ej: Lima, 10645194, Angela Cruz")
    with col_top_c:
        st.text("")
        show_filters = st.checkbox("Mostrar filtros", value=False)
    with col_top_r:
        st.metric("Puestos totales", len(st.session_state.positions))

    # Filtros
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

    # Aplicar búsqueda + filtros
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
        if ubic:
            df_pos = df_pos[df_pos["Ubicación"].isin(ubic)]
        if hm:
            df_pos = df_pos[df_pos["Hiring Manager"].isin(hm)]
        if estado:
            df_pos = df_pos[df_pos["Estado"].isin(estado)]
        df_pos = df_pos[df_pos["Días Abierto"] <= dias_abierto]

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
        height=420,
    )

# --------------------------------------------------------------------------------------
# TAB 2: EVALUACIÓN
# --------------------------------------------------------------------------------------
with tabs[1]:
    h1_title("SelektIA", "Resultados de evaluación")

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
        fig = px.bar(
            df_sorted,
            x="Name",
            y="Score",
            title="Comparación de puntajes (todos los candidatos)",
        )
        fig.update_traces(marker_color=bar_colors, hovertemplate="%{x}<br>Score: %{y}")
        fig.update_layout(
            plot_bgcolor="#FFFFFF",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color=TITLE_DARK),
            xaxis_title=None,
            yaxis_title="Score",
        )
        st.plotly_chart(fig, use_container_width=True)

        # Visor de CV
        st.markdown("### Visor de CV (PDF/TXT) ↪️")
        all_names = df_sorted["Name"].tolist()
        selected_name = st.selectbox("Elige un candidato", all_names, index=0, key="pdf_candidate", label_visibility="collapsed")

        cand = df.loc[df["Name"] == selected_name].iloc[0]
        if cand["_is_pdf"] and cand["_bytes"]:
            pdf_viewer_pdfjs(cand["_bytes"], height=520, zoom=110)
            st.download_button(
                f"Descargar {selected_name}",
                data=cand["_bytes"],
                file_name=selected_name,
                mime="application/pdf",
            )
        else:
            st.info(f"'{selected_name}' es un TXT. Mostrando contenido abajo:")
            with st.expander("Ver contenido TXT", expanded=True):
                st.text_area("Contenido", value=cand.get("_text",""), height=400, label_visibility="collapsed")

# --------------------------------------------------------------------------------------
# TAB 3: PIPELINE (solo lectura + selector)
# --------------------------------------------------------------------------------------
with tabs[2]:
    h1_title("SelektIA", "Pipeline de Candidatos")

    if not st.session_state.candidates:
        st.info("Primero sube CVs en la barra lateral.")
    else:
        df = pd.DataFrame(st.session_state.candidates).sort_values("Score", ascending=False)

        colL, colR = st.columns([1.2, 1])
        with colL:
            st.markdown("#### Candidatos detectados (elige para ver detalle)")
            cand_name = st.selectbox(
                "Selecciona",
                df["Name"].tolist(),
                index=0,
                label_visibility="collapsed"
            )
            st.dataframe(
                df[["Name", "Score"]].rename(columns={"Name":"Candidato", "Score":"Match (%)"}),
                use_container_width=True,
                height=210
            )

        with colR:
            st.markdown("#### Detalle del candidato")
            c = df[df["Name"] == cand_name].iloc[0]
            st.write(f"**{cand_name}**")
            stars = "●" * max(1, int(c["Score"] / 20))
            st.caption(f"Match estimado: {c['Score']}  {stars}")
            st.write("**Razones (extraídas del CV/JD)**")
            st.info(c["Reasons"] or "No se detectaron coincidencias")

            # Etiquetas simples
            st.write("**Validated Skills**")
            st.write("his")
            st.write("**Likely Skills**")
            st.caption("No se detectaron sinónimos relevantes.")
            st.write("**Skills to Validate**")
            st.write("sap is-h, bls, acls, iaas, educación al paciente, seguridad del paciente, protocolos")

            st.markdown("#### Acciones rápidas")
            if st.button("Añadir nota 'Buen encaje'"):
                st.success("Nota añadida.")
            if st.button("Mover a ‘Entrevista (Gerencia)’"):
                if cand_name not in st.session_state.interview_queue:
                    st.session_state.interview_queue.append(cand_name)
                st.success("Candidato movido a ‘Entrevista (Gerencia)’. Revisa la pestaña correspondiente.")

# --------------------------------------------------------------------------------------
# TAB 4: ENTREVISTA (GERENCIA)
# --------------------------------------------------------------------------------------
with tabs[3]:
    h1_title("SelektIA", "Entrevista (Gerencia)")

    if not st.session_state.interview_queue:
        st.info("Aún no se han movido candidatos desde el Pipeline.")
    else:
        df_int = pd.DataFrame({"Candidato": st.session_state.interview_queue})
        st.dataframe(df_int, use_container_width=True, height=220)

        st.markdown("#### Asignar Headhunter")
        hh_opts = ["— Seleccionar —", "María Torres", "Luis Pérez", "Andrea Silva", "Carlos Gómez"]
        for cand in st.session_state.interview_queue:
            col1, col2 = st.columns([2, 1])
            with col1:
                st.write(f"**{cand}**")
            with col2:
                current = st.session_state.headhunter_map.get(cand, "— Seleccionar —")
                sel = st.selectbox(
                    "Headhunter",
                    hh_opts,
                    index=hh_opts.index(current) if current in hh_opts else 0,
                    key=f"hh_{cand}"
                )
                if sel != "— Seleccionar —":
                    st.session_state.headhunter_map[cand] = sel

        st.markdown("#### Asignaciones")
        if st.session_state.headhunter_map:
            assigned_df = pd.DataFrame(
                [{"Candidato": k, "Headhunter": v} for k, v in st.session_state.headhunter_map.items()]
            )
            st.dataframe(assigned_df, use_container_width=True, height=220)
        else:
            st.caption("Sin asignaciones aún.")
