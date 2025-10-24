# app.py
import io
import base64
import unicodedata
from pathlib import Path

import streamlit as st
import pandas as pd
import plotly.express as px
from PyPDF2 import PdfReader

# =========================
# Paleta / tema de colores
# =========================
PRIMARY_GREEN = "#00CD78"   # Verde Wayki
SIDEBAR_BG    = "#10172A"   # Fondo columna izquierda
BOX_DARK      = "#132840"   # Boxes del sidebar
BOX_DARK_HOV  = "#193355"   # Hover/Focus Sidebar
TEXT_LIGHT    = "#FFFFFF"   # Texto claro
MAIN_BG       = "#F7FBFF"   # Fondo principal claro
BOX_LIGHT     = "#F1F7FD"   # Fondo de controles (panel derecho)
BOX_LIGHT_B   = "#E3EDF6"   # Borde de controles (panel derecho)
TITLE_DARK    = "#142433"   # Títulos panel derecho

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

html, body, [data-testid="stAppViewContainer"] {{
  background: var(--main-bg) !important;
}}
.block-container {{
  background: transparent !important;
  padding-top: 1rem !important;
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
/* Inputs del SIDEBAR */
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
/* Botón general */
.stButton > button {{
  background: var(--green) !important;
  color: #082017 !important;
  border-radius: 10px !important;
  border: none !important;
  padding: .45rem .9rem !important;
  font-weight: 600 !important;
}}
.stButton > button:hover {{ filter: brightness(0.95); }}

/* Panel derecho (claros) */
h1, h2, h3 {{ color: var(--title-dark); }}
h1 strong, h2 strong, h3 strong {{ color: var(--green); }}

.block-container [data-testid="stSelectbox"] > div > div,
.block-container [data-baseweb="select"],
.block-container [data-testid="stTextInput"] input,
.block-container [data-testid="stTextArea"] textarea {{
  background: var(--box-light) !important;
  color: var(--title-dark) !important;
  border: 1.5px solid var(--box-light-border) !important;
  border-radius: 10px !important;
}}

.block-container table {{
  background: #fff !important;
  border: 1px solid var(--box-light-border) !important;
  border-radius: 8px !important;
}}
.block-container thead th {{
  background: var(--box-light) !important;
  color: var(--title-dark) !important;
}}

[data-testid="stExpander"] {{
  background: #fff !important;
  border: 1px solid var(--box-light-border) !important;
  border-radius: 12px !important;
}}
[data-testid="stExpander"] [data-testid="stExpanderHeader"] p {{
  color: var(--title-dark) !important;
}}

#pdf_candidate, #pdf_candidate_alt {{
  background: var(--box-light) !important;
  border: 1.5px solid var(--box-light-border) !important;
  color: var(--title-dark) !important;
  border-radius: 10px !important;
}}
"""

# ========================
# Utilidades de procesamiento
# ========================

def normalize_text(text: str) -> str:
    """Normaliza texto: minúsculas, sin tildes, sin dobles espacios."""
    if not text:
        return ""
    text = text.lower()
    text = "".join(
        c for c in unicodedata.normalize("NFD", text)
        if unicodedata.category(c) != "Mn"
    )
    return " ".join(text.split())

def extract_text_from_file(uploaded_file) -> str:
    """
    Devuelve texto desde PDF o TXT.
    - PDF: usa PyPDF2 (no OCR). Si es escaneado, no habrá texto.
    - TXT: lectura directa.
    """
    try:
        suffix = Path(uploaded_file.name).suffix.lower()
        raw_bytes = uploaded_file.read()
        uploaded_file.seek(0)

        if suffix == ".pdf":
            reader = PdfReader(io.BytesIO(raw_bytes))
            text = ""
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
            return text.strip()

        elif suffix == ".txt":
            try:
                return raw_bytes.decode("utf-8", errors="ignore").strip()
            except Exception:
                return raw_bytes.decode("latin-1", errors="ignore").strip()

        else:
            return ""

    except Exception as e:
        st.error(f"Error al leer '{uploaded_file.name}': {e}")
        return ""

def split_keywords(kw_text: str):
    """
    Separa palabras clave por coma o salto de línea, normaliza y filtra vacíos.
    """
    if not kw_text:
        return []
    parts = [p.strip() for p in kw_text.replace("\n", ",").split(",")]
    parts = [normalize_text(p) for p in parts if p.strip()]
    return [p for p in parts if p]

def score_candidate(cv_text: str, keywords: list[str]) -> tuple[int, list[str]]:
    """
    Calcula el score por coincidencias de keywords dentro del CV.
    Retorna (score, coincidencias_encontradas).
    """
    if not cv_text:
        return 0, []
    text_norm = normalize_text(cv_text)
    hits = []
    for kw in keywords:
        if not kw:
            continue
        # Para KW multi-palabra, buscar como substring normalizado:
        if kw in text_norm:
            hits.append(kw)
    total = len(keywords) if keywords else 1
    score = int(round((len(hits) / total) * 100))
    return score, hits

# ========================
# Configuración general
# ========================
st.set_page_config(
    page_title="SelektIA",
    page_icon="🧠",
    layout="wide",
)
st.markdown(f"<style>{CSS}</style>", unsafe_allow_html=True)

# ========================
# Sidebar (oscuro)
# ========================
with st.sidebar:
    st.image("assets/logo-wayki.png", use_column_width=True)
    st.markdown("### Definición del puesto")

    puesto = st.selectbox(
        "Puesto",
        [
            "Enfermera/o Asistencial",
            "Tecnólogo/a Médico/a",
            "Recepcionista de Admisión",
            "Médico/a General",
            "Químico/a Farmacéutico/a",
        ],
        index=0,
        key="puesto",
    )

    st.markdown("### Descripción del puesto (texto libre)")
    jd_text = st.text_area(
        "Resumen del objetivo, responsabilidades, protocolos, habilidades deseadas.",
        height=110,
        key="jd",
        label_visibility="collapsed",
    )

    st.markdown("### Palabras clave del perfil\n*(ajústalas si es necesario)*")
    kw_text = st.text_area(
        "Ej.: HIS, SAP IS-H, BLS, ACLS, IAAS, educación al paciente, seguridad, protocolos…",
        value="HIS, SAP IS-H, BLS, ACLS, IAAS, educación al paciente, seguridad del paciente, protocolos",
        height=110,
        key="kw",
        label_visibility="collapsed",
    )

    st.markdown("### Subir CVs (PDF o TXT)")
    files = st.file_uploader(
        "Arrastra y suelta aquí",
        type=["pdf", "txt"],
        accept_multiple_files=True,
        label_visibility="collapsed",
    )

# ==========================
# Panel derecho (Resultados)
# ==========================
st.markdown(f"## <span style='color:{PRIMARY_GREEN}'>SelektIA – Resultados de evaluación</span>", unsafe_allow_html=True)
st.info("Define el puesto/JD, edita las palabras clave y sube CVs (PDF o TXT) para evaluar.")

# 1) Si hay CVs subidos, analizamos automáticamente
candidates = []
keywords = split_keywords(kw_text)

if files:
    for f in files:
        raw_bytes = f.read()
        f.seek(0)

        text = extract_text_from_file(f)
        score, hits = score_candidate(text, keywords)

        reason = f"{len(hits)}/{len(keywords)} keywords encontradas — Coincidencias: " + (", ".join(hits) if hits else "—")
        candidates.append({
            "Name": f.name,
            "Score": score,
            "Reasons": reason,
            "PDF_text": len(text),
            "file_bytes": raw_bytes,
            "is_pdf": Path(f.name).suffix.lower() == ".pdf"
        })

# 2) Mostrar resultados si hay candidatos
if candidates:
    df = pd.DataFrame(candidates)
    df_sorted = df.sort_values("Score", ascending=False).reset_index(drop=True)

    st.markdown("### Ranking de candidatos")
    show = df_sorted[["Name", "Score", "Reasons", "PDF_text"]].rename(
        columns={
            "Name": "Nombre",
            "Score": "Score",
            "Reasons": "Razones",
            "PDF_text": "PDF_text"
        }
    )
    st.dataframe(show, use_container_width=True, height=280)

    st.markdown("### Comparación de puntajes")
    fig = px.bar(
        df_sorted,
        x="Name",
        y="Score",
        title="Score Comparison",
        color="Score",
        color_continuous_scale=px.colors.sequential.Greens
    )
    fig.update_layout(
        plot_bgcolor="#FFFFFF",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color=TITLE_DARK),
        xaxis_title=None,
        yaxis_title="Score",
    )
    st.plotly_chart(fig, use_container_width=True)

    # Visor
    st.markdown(f"### <span style='color:{PRIMARY_GREEN}'>Visor de CV (PDF / TXT)</span>", unsafe_allow_html=True)
    st.caption("Elige un candidato para ver su CV original.")

    all_names = df_sorted["Name"].tolist()
    col1, col2 = st.columns([0.5, 0.5])
    with col1:
        selected_name = st.selectbox(
            "Candidato:",
            all_names,
            key="pdf_candidate",
            label_visibility="collapsed",
        )
    with col2:
        st.selectbox(
            "Elegir candidato (opción alternativa)",
            all_names,
            index=0,
            key="pdf_candidate_alt",
            label_visibility="visible"
        )

    # Mostrar visor
    if selected_name:
        cand = next(c for c in candidates if c["Name"] == selected_name)
        if cand["is_pdf"] and cand["file_bytes"]:
            data_b64 = base64.b64encode(cand["file_bytes"]).decode("utf-8")
            st.markdown(
                f"""
                <div style="border:1px solid {BOX_LIGHT_B}; border-radius:12px; overflow:hidden; background:#fff;">
                  <iframe src="data:application/pdf;base64,{data_b64}"
                          style="width:100%; height:780px; border:0;"
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
            txt = ""
            try:
                txt = cand["file_bytes"].decode("utf-8", errors="ignore")
            except Exception:
                txt = cand["file_bytes"].decode("latin-1", errors="ignore")
            st.text_area("Contenido del TXT:", value=txt, height=700, disabled=True)

else:
    st.warning("Sube uno o más CVs (PDF o TXT) y añade palabras clave para ver el ranking y el visor.", icon="📄")

