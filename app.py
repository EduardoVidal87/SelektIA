# app.py
import io
import base64
from pathlib import Path

import streamlit as st
import pandas as pd
import plotly.express as px
from PyPDF2 import PdfReader  # Para extraer texto de PDFs

# =========================
# Variables de tema/colores
# =========================
PRIMARY_GREEN = "#00CD78"

# Sidebar oscuro (se mantiene)
SIDEBAR_BG = "#10172A"
BOX_DARK = "#132840"
BOX_DARK_HOV = "#193355"
TEXT_LIGHT = "#FFFFFF"

# Panel derecho (nuevo esquema claro azul – como tu captura)
MAIN_BG = "#F7FBFF"          # fondo general
TITLE_DARK = "#0F2B46"       # títulos en azul profundo
PANEL_STRIP = "#E7F0FF"      # franja/avisos celeste
PANEL_STRIP_BORDER = "#BFD6FF"  # borde celeste
TABLE_HEAD_BG = "#EAF3FF"    # cabecera tabla celeste claro
TABLE_BORDER = "#D7E6FF"     # borde suave
SURFACE_LIGHT = "#FFFFFF"    # tarjetas/fondos blancos

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
  --title-dark: {TITLE_DARK};

  --panel-strip: {PANEL_STRIP};
  --panel-strip-border: {PANEL_STRIP_BORDER};
  --table-head-bg: {TABLE_HEAD_BG};
  --table-border: {TABLE_BORDER};
  --surface: {SURFACE_LIGHT};
}}

/* ====== Lienzo general ====== */
html, body, [data-testid="stAppViewContainer"] {{
  background: var(--main-bg) !important;
}}
.block-container {{
  background: transparent !important;
}}

/* ====== SIDEBAR (oscuro) ====== */
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
[data-testid="stSidebar"] [data-testid="stSelectbox"] > div > div,
[data-testid="stSidebar"] [data-baseweb="select"],
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
[data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] {{
  background: var(--box) !important;
  border: 1.5px dashed var(--box) !important;
  border-radius: 14px !important;
}}
[data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] * {{
  color: var(--text) !important;
}}
[data-testid="stSidebar"] [data-testid="stFileUploaderFile"] {{
  background: var(--box) !important;
  border: 1px solid var(--box) !important;
  color: var(--text) !important;
}}

/* ====== Botones (global) ====== */
.stButton > button {{
  background: var(--green) !important;
  color: #082017 !important;
  border-radius: 10px !important;
  border: none !important;
  padding: .45rem .9rem !important;
  font-weight: 600 !important;
}}
.stButton > button:hover {{ filter: brightness(0.95); }}

/* ====== Títulos y franja del panel derecho ====== */
h1, h2, h3 {{ color: var(--title-dark) !important; }}
h1 strong, h2 strong, h3 strong {{ color: var(--green) !important; }}

/* Franja informativa bajo el título */
.section-strip {{
  background: var(--panel-strip);
  border: 1px solid var(--panel-strip-border);
  color: var(--title-dark);
  padding: .5rem .75rem;
  border-radius: 8px;
}}

/* ====== Componentes claros del panel derecho ====== */
.block-container [data-testid="stTextInput"] input,
.block-container [data-testid="stTextArea"] textarea,
.block-container [data-testid="stSelectbox"] > div > div,
.block-container [data-baseweb="select"],
.block-container [data-baseweb="textarea"],
.block-container [data-baseweb="input"] {{
  background: var(--surface) !important;
  color: var(--title-dark) !important;
  border: 1.5px solid var(--table-border) !important;
  border-radius: 10px !important;
  box-shadow: none !important;
}}
.block-container [data-testid="stTextInput"] input:hover,
.block-container [data-testid="stTextInput"] input:focus,
.block-container [data-testid="stTextArea"] textarea:hover,
.block-container [data-testid="stTextArea"] textarea:focus,
.block-container [data-testid="stSelectbox"] > div > div:hover,
.block-container [data-baseweb="select"]:hover {{
  border-color: var(--green) !important;
}}

/* Tabla clara con header celeste */
.block-container table {{
  background: var(--surface) !important;
  border: 1px solid var(--table-border) !important;
  border-radius: 8px !important;
}}
.block-container thead th {{
  background: var(--table-head-bg) !important;
  color: var(--title-dark) !important;
  border-bottom: 1px solid var(--table-border) !important;
}}
.block-container tbody td {{
  border-top: 1px solid var(--table-border) !important;
}}

/* Expander claro */
[data-testid="stExpander"] {{
  background: var(--surface) !important;
  border: 1px solid var(--table-border) !important;
  border-radius: 12px !important;
}}
[data-testid="stExpander"] [data-testid="stExpanderHeader"] p {{
  color: var(--title-dark) !important;
}}

/* Scrollbar claro */
.block-container ::-webkit-scrollbar {{ height: 10px; width: 10px; }}
.block-container ::-webkit-scrollbar-thumb {{
  background: var(--table-border);
  border-radius: 8px;
}}
.block-container ::-webkit-scrollbar-thumb:hover {{ background: var(--green); }}

/* Slider umbral (verde) */
[data-testid="stSlider"] [role="slider"] {{
  background: var(--green) !important;
  border: 2px solid #089f5e !important;
}}
[data-testid="stSlider"] .st-b3 {{
  background: linear-gradient(90deg, var(--green), var(--green)) !important;
}}

/* Select del visor PDF (claro) */
#pdf_candidate, #pdf_candidate_alt {{
  background: var(--surface) !important;
  border: 1.5px solid var(--table-border) !important;
  color: var(--title-dark) !important;
  border-radius: 10px !important;
}}
"""

# Inyectar CSS
st.markdown(f"<style>{CSS}</style>", unsafe_allow_html=True)

st.set_page_config(
    page_title="SelektIA",
    page_icon="🧠",
    layout="wide",
)

# =================================
#  FUNCIONES (sin IA, por keywords)
# =================================
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

def normalize_text(s: str) -> str:
    return " ".join(s.lower().split())

def analyze_cvs_by_keywords(jd_text: str, kw_text: str, cv_files):
    """
    Analiza coincidencias simples de keywords separadas por comas.
    Score = % de keywords encontradas en el texto.
    """
    st.session_state.candidates = []

    kws = [k.strip().lower() for k in kw_text.split(",") if k.strip()]
    kws = list(dict.fromkeys(kws))
    if not kws:
        st.warning("No hay palabras clave válidas. Escribe algunas separadas por comas.")
        return

    progress_bar = st.progress(0.0, "Analizando CVs...")

    for i, file in enumerate(cv_files):
        file_bytes = file.read()
        file.seek(0)
        text = extract_text_from_file(file)
        plain = normalize_text(text)

        found = [kw for kw in kws if kw in plain]
        score = round(100 * (len(found) / len(kws))) if kws else 0

        reasons = (
            f"{len(found)}/{len(kws)} keywords encontradas — "
            f"Coincidencias: {', '.join(found) if found else '—'}"
        )

        is_pdf = Path(file.name).suffix.lower() == ".pdf"
        st.session_state.candidates.append({
            "Name": file.name,
            "Score": score,
            "Reasons": reasons,
            "PDF_text_chars": len(text),
            "file_bytes": file_bytes,
            "is_pdf": is_pdf
        })

        progress_bar.progress((i + 1) / len(cv_files), f"Analizando: {file.name}")

    progress_bar.empty()
    st.success(f"¡Listo! {len(st.session_state.candidates)} CV(s) procesado(s).")

# ================
#  SIDEBAR
# ================
with st.sidebar:
    st.image("assets/logo-wayki.png", use_container_width=True)

    st.markdown("### Definición del puesto")

    _ = st.selectbox(
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
        height=120,
        key="jd",
        label_visibility="collapsed",
    )

    st.markdown("### Palabras clave del perfil\n*(ajústalas si es necesario)*")
    kw_text = st.text_area(
        "HIS, SAP IS-H, BLS, ACLS, IAAS, educación al paciente, seguridad, protocolos…",
        value="HIS, SAP IS-H, BLS, ACLS, IAAS, educación al paciente, seguridad del paciente, protocolos",
        height=110,
        key="kw",
        label_visibility="collapsed",
    )

    st.markdown("### Subir CVs (PDF o TXT)")
    files = st.file_uploader(
        "Arrastra y suelta archivos aquí",
        type=["pdf", "txt"],
        accept_multiple_files=True,
        label_visibility="collapsed",
    )

    if st.button("Analizar CVs", type="primary", use_container_width=True):
        if not files:
            st.error("¡Por favor, sube al menos un CV!")
        else:
            analyze_cvs_by_keywords(jd_text, kw_text, files)

    st.divider()

    if 'candidates' in st.session_state and st.session_state.candidates:
        if st.button("Limpiar lista", use_container_width=True):
            st.session_state.candidates = []
            st.success("Resultados limpiados.")
            st.rerun()

# ===================
#  PANEL DERECHO
# ===================
st.markdown(f"## <span style='color:{PRIMARY_GREEN}'>SelektIA – Resultados de evaluación</span>", unsafe_allow_html=True)
st.markdown(
    "<div class='section-strip'>Define el puesto/JD, edita las palabras clave y sube CVs (PDF o TXT) para evaluar.</div>",
    unsafe_allow_html=True
)
st.write("")  # pequeño respiro

if 'candidates' not in st.session_state or not st.session_state.candidates:
    st.info("Carga CVs en la barra lateral y pulsa **Analizar CVs** para ver el ranking.")
else:
    df = pd.DataFrame(st.session_state.candidates)
    df_sorted = df.sort_values("Score", ascending=False)

    # Ranking tabla
    st.markdown("### Ranking de candidatos")
    show = df_sorted[["Name", "Score", "Reasons", "PDF_text_chars"]].rename(
        columns={{
            "Name": "Nombre",
            "Score": "Puntaje",
            "Reasons": "Razones",
            "PDF_text_chars": "PDF_texto (caracteres)"
        }}
    )
    st.dataframe(show, use_container_width=True, hide_index=True)

    # Gráfico
    st.markdown("### Comparación de puntajes")
    fig = px.bar(
        df_sorted,
        x="Name",
        y="Score",
        title="Comparación de puntajes (todos los candidatos)",
        color="Score",
        color_continuous_scale=px.colors.sequential.Greens_r
    )
    fig.update_layout(
        plot_bgcolor="#FFFFFF",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color=TITLE_DARK),
        xaxis_title=None,
        yaxis_title="Puntaje",
    )
    st.plotly_chart(fig, use_container_width=True)

    # Visor de CV
    st.markdown(f"### <span style='color:{PRIMARY_GREEN}'>Visor de CV (PDF)</span>", unsafe_allow_html=True)
    st.caption("Elige un candidato para ver su CV original.")

    all_names = df_sorted["Name"].tolist()
    selected_name = st.selectbox(
        "Selecciona un candidato",
        all_names,
        key="pdf_candidate",
        label_visibility="collapsed",
    )

    if selected_name:
        cand = next(c for c in st.session_state.candidates if c["Name"] == selected_name)
        if cand["is_pdf"] and cand["file_bytes"]:
            data_b64 = base64.b64encode(cand["file_bytes"]).decode("utf-8")
            st.markdown(
                f"""
                <div style="border:1px solid var(--table-border); border-radius:12px; overflow:hidden; background:var(--surface);">
                  <iframe src="data:application/pdf;base64,{data_b64}"
                          style="width:100%; height:750px; border:0;"
                          title="PDF Viewer"></iframe>
                </div>
                """,
                unsafe_allow_html=True,
            )
            st.download_button(
                f"Descargar {selected_name}",
                data=cand["file_bytes"],
                file_name=selected_name,
                mime="application/pdf",
            )
        else:
            st.info(f"'{selected_name}' es un archivo de texto. Mostrando contenido:")
            txt_content = cand["file_bytes"].decode("utf-8", errors="ignore")
            st.text_area("Contenido del TXT", value=txt_content, height=600, disabled=True)
