# app.py
# ======================================================================================
# SelektIA – Evaluación de CVs (sin IA externa)
# - Analiza PDFs/TXTs por coincidencia de keywords del JD (score 0–100)
# - Ranking + gráfico + visor PDF
# - Tema con sidebar oscuro y cuerpo claro
# ======================================================================================

import io
import base64
import unicodedata
from pathlib import Path

import streamlit as st
import pandas as pd
import plotly.express as px
from PyPDF2 import PdfReader


# =========================
# Variables de tema/colores
# =========================
PRIMARY_GREEN = "#00CD78"
SIDEBAR_BG   = "#10172A"    # fondo columna izquierda
BOX_DARK     = "#132840"    # fondo y borde de boxes del sidebar
BOX_DARK_HOV = "#193355"    # borde hover/focus del sidebar
TEXT_LIGHT   = "#FFFFFF"    # texto blanco
MAIN_BG      = "#F7FBFF"    # fondo del cuerpo (claro)
BOX_LIGHT    = "#F1F7FD"    # fondo claro de inputs principales
BOX_LIGHT_B  = "#E3EDF6"    # borde claro de inputs principales
TITLE_DARK   = "#142433"    # texto títulos principales


# ==========
#   ESTILO
# ==========
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
/* Fondo de la app (quita el blanco del contenedor) */
.block-container {{
  background: transparent !important;
}}

/* Sidebar fondo */
[data-testid="stSidebar"] {{
  background: var(--sidebar-bg) !important;
  color: var(--text) !important;
}}
/* --- TÍTULOS DEL SIDEBAR EN VERDE --- */
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3,
[data-testid="stSidebar"] h4,
[data-testid="stSidebar"] h5,
[data-testid="stSidebar"] h6,
[data-testid="stSidebar"] .stMarkdown p strong {{
  color: var(--green) !important;
}}

/* Etiquetas del sidebar y texto */
[data-testid="stSidebar"] label, 
[data-testid="stSidebar"] p, 
[data-testid="stSidebar"] span {{
  color: var(--text) !important;
}}

/* Inputs del SIDEBAR (select, input, textarea, dropzone) */
[data-testid="stSidebar"] [data-testid="stSelectbox"] > div > div,
[data-testid="stSidebar"] [data-baseweb="select"] {{
  background: var(--box) !important;
  color: var(--text) !important;
  border: 1.5px solid var(--box) !important;
  border-radius: 12px !important;
  box-shadow: none !important;
}}
[data-testid="stSidebar"] [data-testid="stTextInput"] input,
[data-testid="stSidebar"] [data-testid="stTextArea"] textarea {{
  background: var(--box) !important;
  color: var(--text) !important;
  border: 1.5px solid var(--box) !important;
  border-radius: 12px !important;
  box-shadow: none !important;
}}
[data-testid="stSidebar"] [data-testid="stTextInput"] input:hover,
[data-testid="stSidebar"] [data-testid="stTextInput"] input:focus,
[data-testid="stSidebar"] [data-testid="stTextArea"] textarea:hover,
[data-testid="stSidebar"] [data-testid="stTextArea"] textarea:focus,
[data-testid="stSidebar"] [data-testid="stSelectbox"] > div > div:hover {{
  border-color: var(--box-hover) !important;
}}
/* Dropzone */
[data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] {{
  background: var(--box) !important;
  border: 1.5px dashed var(--box) !important;
  border-radius: 14px !important;
}}
[data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] * {{
  color: var(--text) !important;
}}
/* Pills de archivos subidos */
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

/* Controles del área principal (claros) */
.block-container [data-testid="stSelectbox"] > div > div,
.block-container [data-baseweb="select"],
.block-container [data-testid="stTextInput"] input,
.block-container [data-testid="stTextArea"] textarea {{
  background: var(--box-light) !important;
  color: var(--title-dark) !important;
  border: 1.5px solid var(--box-light-border) !important;
  border-radius: 10px !important;
}}

/* Tabla clara (dataframe/simple table) */
.block-container table {{
  background: #fff !important;
  border: 1px solid var(--box-light-border) !important;
  border-radius: 8px !important;
}}
.block-container thead th {{
  background: var(--box-light) !important;
  color: var(--title-dark) !important;
}}

/* Expander claro */
[data-testid="stExpander"] {{
  background: #fff !important;
  border: 1px solid var(--box-light-border) !important;
  border-radius: 12px !important;
}}
[data-testid="stExpander"] [data-testid="stExpanderHeader"] p {{
  color: var(--title-dark) !important;
}}

/* Selector del visor de PDF en claro */
#pdf_candidate, #pdf_candidate_alt {{
  background: var(--box-light) !important;
  border: 1.5px solid var(--box-light-border) !important;
  color: var(--title-dark) !important;
  border-radius: 10px !important;
}}
"""


# =================
#   PAGE SETTINGS
# =================
st.set_page_config(
    page_title="SelektIA",
    page_icon="🧠",
    layout="wide",
)

st.markdown(f"<style>{CSS}</style>", unsafe_allow_html=True)


# =================================
#  UTILIDADES Y PROCESAMIENTO
# =================================
def normalize_text(s: str) -> str:
    """Normaliza texto: minúsculas y sin acentos para comparar."""
    if not s:
        return ""
    s = s.lower()
    s = "".join(
        c for c in unicodedata.normalize("NFD", s)
        if unicodedata.category(c) != "Mn"
    )
    return s


def parse_keywords(raw: str) -> list:
    """Separa keywords por coma/; o salto de línea y limpia espacios."""
    if not raw:
        return []
    parts = []
    for token in raw.replace("\n", ",").replace(";", ",").split(","):
        t = token.strip()
        if t:
            parts.append(t)
    return parts


def extract_text_from_file(uploaded_file) -> str:
    """Extrae texto de PDF (PyPDF2) o TXT. Devuelve str normalizado."""
    try:
        suffix = Path(uploaded_file.name).suffix.lower()
        if suffix == ".pdf":
            pdf_reader = PdfReader(io.BytesIO(uploaded_file.read()))
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() or ""
        else:
            text = uploaded_file.read().decode("utf-8", errors="ignore")
        return normalize_text(text)
    except Exception as e:
        st.error(f"Error al leer '{uploaded_file.name}': {e}")
        return ""


def score_cv(cv_text: str, kw_list: list) -> tuple:
    """Devuelve (matches_count, score_0_100, reasons_str)."""
    if not kw_list:
        return 0, 0, "Sin keywords definidas."

    matches = []
    text = normalize_text(cv_text)
    for kw in kw_list:
        kwn = normalize_text(kw)
        if kwn and kwn in text:
            matches.append(kw)

    matches_count = len(matches)
    total = len(kw_list)
    score = int(round((matches_count / total) * 100)) if total else 0
    reasons = (
        f"{matches_count}/{total} keywords encontradas — Coincidencias: "
        + (", ".join(matches) if matches else "Ninguna")
    )
    return matches_count, max(0, min(score, 100)), reasons


def analyze_cvs(jd_text: str, kw_text: str, files):
    """Analiza CVs (sin IA): coincidencias con keywords del JD."""
    kw_list = parse_keywords(kw_text)
    candidates = []

    progress = st.progress(0, "Analizando CVs...")
    for i, f in enumerate(files):
        # Leer bytes para guardar y luego extraer texto (volver a posicion 0)
        file_bytes = f.read()
        f.seek(0)
        cv_text = extract_text_from_file(f)

        if not cv_text:
            st.warning(f"No se pudo extraer texto de '{f.name}'. Omitiendo.")
            continue

        matches, score, reasons = score_cv(cv_text, kw_list)

        candidates.append({
            "Name": f.name,
            "Score": score,
            "Matches": matches,
            "Reasons": reasons,
            "file_bytes": file_bytes,
            "is_pdf": Path(f.name).suffix.lower() == ".pdf"
        })

        progress.progress((i + 1) / len(files), f"Analizando: {f.name}")

    progress.empty()

    st.session_state.candidates = candidates
    if not candidates:
        st.warning("No se pudo procesar ningún CV. Revisa que los archivos no estén dañados.")
    else:
        st.success(f"¡Análisis completo! {len(candidates)} CV(s) procesados.")
        st.rerun()


# ================
#  SIDEBAR (oscuro)
# ================
with st.sidebar:
    # Logo (sin use_column_width para evitar banner deprecado)
    st.image("assets/logo-wayki.png", width=170)

    st.markdown("### Definición del puesto")
    puesto = st.selectbox(
        "Puesto",
        [
            "Enfermera/o Asistencial",
            "Tecnólogo Médico",
            "Recepcionista de Admisión",
            "Médico General",
            "Químico Farmacéutico",
        ],
        index=0,
        key="puesto",
    )

    st.markdown("### Descripción del puesto (texto libre)")
    jd_text = st.text_area(
        "Resume el objetivo del puesto, responsabilidades, protocolos y habilidades deseadas.",
        height=110,
        key="jd",
        label_visibility="collapsed",
    )

    st.markdown("### Palabras clave del perfil\n*(ajústalas si es necesario)*")
    kw_text = st.text_area(
        "",
        value="HIS, SAP IS-H, BLS, ACLS, IAAS, educación al paciente, seguridad del paciente, protocolos",
        height=110,
        key="kw",
        label_visibility="collapsed",
    )

    st.markdown("### Subir CVs (PDF o TXT)")
    files = st.file_uploader(
        "Drag and drop files here",
        type=["pdf", "txt"],
        accept_multiple_files=True,
        label_visibility="collapsed",
    )

    if st.button("Analizar CVs", type="primary", use_container_width=True):
        if not files:
            st.error("¡Por favor, sube al menos un CV!")
        else:
            analyze_cvs(jd_text, kw_text, files)

    st.divider()

    if 'candidates' in st.session_state and st.session_state.candidates:
        if st.button("Limpiar Lista", use_container_width=True):
            st.session_state.candidates = []
            st.success("Resultados limpiados.")
            st.rerun()


# ===================
#  UI PRINCIPAL (claro)
# ===================
st.markdown(f"## <span style='color:{PRIMARY_GREEN}'>SelektIA – Evaluation Results</span>", unsafe_allow_html=True)

if 'candidates' not in st.session_state or not st.session_state.candidates:
    st.info("Define el puesto, ajusta keywords y sube CVs. Luego presiona **Analizar CVs** en la barra lateral.", icon="ℹ️")
else:
    # DataFrame base
    df = pd.DataFrame(st.session_state.candidates)

    # --- Normalización defensiva (evita KeyError si algo falta en memoria)
    if "Matches" not in df.columns:
        df["Matches"] = 0
    if "Reasons" not in df.columns:
        df["Reasons"] = ""
    if "file_bytes" not in df.columns:
        df["file_bytes"] = None
    if "is_pdf" not in df.columns:
        df["is_pdf"] = False

    # Orden por Score
    df_sorted = df.sort_values("Score", ascending=False)

    tab_rank, tab_viewer = st.tabs(["🏆 Ranking de Candidatos", "📄 Visor de CV"])

    # -------- Ranking --------
    with tab_rank:
        st.markdown("##### Ranking de Candidatos")
        cols = [c for c in ["Name", "Score", "Matches"] if c in df_sorted.columns]
        show = df_sorted[cols].rename(columns={"Name": "Candidato", "Score": "Score", "Matches": "Keywords"})
        st.dataframe(show, use_container_width=True, hide_index=True)

        st.markdown("#### Comparativa General")
        fig = px.bar(
            df_sorted,
            x="Name",
            y="Score",
            title="Score Comparison (Todos los candidatos)",
            color="Score",
            color_continuous_scale=px.colors.sequential.Greens_r
        )
        fig.update_layout(
            plot_bgcolor="#FFFFFF",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color=TITLE_DARK),
            xaxis_title=None,
            yaxis_title="Score",
        )
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("#### Detalle (coincidencias)")
        for _, r in df_sorted.iterrows():
            with st.expander(f"{r['Name']}  (Score: {r['Score']}/100, Keywords: {r['Matches']})"):
                st.markdown(r.get("Reasons", ""))

    # -------- Visor de CV --------
    with tab_viewer:
        st.markdown(f"#### <span style='color:{PRIMARY_GREEN}'>Visor de CV</span>", unsafe_allow_html=True)
        all_names = df_sorted["Name"].tolist()

        col1, col2 = st.columns([1, 1])
        with col1:
            selected_name = st.selectbox(
                "Selecciona un candidato:",
                all_names,
                key="pdf_candidate",
                label_visibility="collapsed",
            )
        with col2:
            st.selectbox(
                "Elegir candidato (opción alternativa)",
                all_names,
                index=all_names.index(selected_name) if selected_name in all_names else 0,
                key="pdf_candidate_alt",
                label_visibility="visible",
            )

        if selected_name:
            cdata = next(c for c in st.session_state.candidates if c["Name"] == selected_name)
            if cdata.get("is_pdf") and cdata.get("file_bytes"):
                data_b64 = base64.b64encode(cdata["file_bytes"]).decode("utf-8")

                # Embebido principal
                st.markdown(
                    f"""
                    <div style="border:1px solid {BOX_LIGHT_B}; border-radius:12px; overflow:hidden; background:#fff;">
                      <iframe src="data:application/pdf;base64,{data_b64}"
                              style="width:100%; height:750px; border:0;"
                              title="PDF Viewer"></iframe>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                # Fallback (algunos navegadores son estrictos con data: URIs)
                st.components.v1.iframe(
                    src=f"data:application/pdf;base64,{data_b64}",
                    width=None, height=750, scrolling=True
                )

                st.download_button(
                    f"Descargar {selected_name}",
                    data=cdata["file_bytes"],
                    file_name=selected_name,
                    mime="application/pdf"
                )
            else:
                st.info(f"'{selected_name}' es un archivo de texto. Mostrando contenido:")
                txt_content = (cdata.get("file_bytes") or b"").decode("utf-8", errors="ignore")
                st.text_area("Contenido del TXT:", value=txt_content, height=600, disabled=True)
