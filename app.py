# app.py
import base64
import io
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st
from PyPDF2 import PdfReader
from streamlit.components.v1 import html

# =========================
# Paleta / tema (colores)
# =========================
PRIMARY_GREEN = "#00CD78"
SIDEBAR_BG = "#10172A"
BOX_DARK = "#132840"
BOX_DARK_HOV = "#193355"
TEXT_LIGHT = "#FFFFFF"
MAIN_BG = "#F7FBFF"
BOX_LIGHT = "#F1F7FD"
BOX_LIGHT_B = "#E3EDF6"
TITLE_DARK = "#142433"

# Colores gráfico
BAR_BASE = "#E9F3FF"
BAR_HIGHLIGHT = "#33FFAC"  # >= 60

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

/* Inputs sidebar */
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
[data-testid="stSidebar"] [data-testid="stFileUploaderFile"] {{
  background: var(--box) !important;
  border: 1px solid var(--box) !important;
  color: var(--text) !important;
}}

/* Botón */
.stButton > button {{
  background: var(--green) !important;
  color: #082017 !important;
  border-radius: 10px !important;
  border: none !important;
  padding: .45rem .9rem !important;
  font-weight: 600 !important;
}}
.stButton > button:hover {{ filter: brightness(0.95); }}

/* Títulos cuerpo */
h1, h2, h3 {{ color: var(--title-dark); }}
h1 strong, h2 strong, h3 strong {{ color: var(--green); }}

/* Inputs cuerpo */
.block-container [data-testid="stSelectbox"] > div > div,
.block-container [data-baseweb="select"],
.block-container [data-testid="stTextInput"] input,
.block-container [data-testid="stTextArea"] textarea {{
  background: var(--box-light) !important;
  color: var(--title-dark) !important;
  border: 1.5px solid var(--box-light-border) !important;
  border-radius: 10px !important;
}}

/* Tabla */
.block-container table {{
  background: #fff !important;
  border: 1px solid var(--box-light-border) !important;
  border-radius: 8px !important;
}}
.block-container thead th {{
  background: var(--box-light) !important;
  color: var(--title-dark) !important;
}}

/* Expander */
[data-testid="stExpander"] {{
  background: #fff !important;
  border: 1px solid var(--box-light-border) !important;
  border-radius: 12px !important;
}}
[data-testid="stExpander"] [data-testid="stExpanderHeader"] p {{
  color: var(--title-dark) !important;
}}

/* Selectores visor PDF */
#pdf_candidate, #pdf_candidate_alt {{
  background: var(--box-light) !important;
  border: 1.5px solid var(--box-light-border) !important;
  color: var(--title-dark) !important;
  border-radius: 10px !important;
}}
"""

st.set_page_config(page_title="SelektIA", page_icon="🧠", layout="wide")
st.markdown(f"<style>{CSS}</style>", unsafe_allow_html=True)

# ======================
# utilidades de lectura
# ======================
def extract_text_from_file(uploaded_file) -> str:
    """Extrae texto de un PDF (PyPDF2) o un TXT sin perder bytes del archivo."""
    try:
        suffix = Path(uploaded_file.name).suffix.lower()
        if suffix == ".pdf":
            data = uploaded_file.getvalue()  # no mueve el puntero
            reader = PdfReader(io.BytesIO(data))
            text = ""
            for page in reader.pages:
                text += page.extract_text() or ""
            return text
        else:
            return uploaded_file.getvalue().decode("utf-8", errors="ignore")
    except Exception as e:
        st.error(f"Error al leer '{uploaded_file.name}': {e}")
        return ""

def analyze_locally(jd: str, kw_text: str, files):
    """Puntaje simple por coincidencia de palabras clave."""
    candidates = []
    kw_list = [k.strip().lower() for k in kw_text.split(",") if k.strip()]
    total_kw = max(len(kw_list), 1)

    for f in files:
        file_bytes = f.getvalue()  # bytes seguros para visor
        text = extract_text_from_file(f)
        lower_text = text.lower()

        matched = [k for k in kw_list if k and k in lower_text]
        score = int(round(100 * len(matched) / total_kw))
        preview_kw = ", ".join(matched[:12]) if matched else "sin coincidencias"
        reasons = f"{len(matched)}/{total_kw} keywords encontradas — Coincidencias: {preview_kw}"

        candidates.append({
            "Nombre": f.name,
            "Score": score,
            "Razones": reasons,
            "PDF_text": len(text),
            "file_bytes": file_bytes,
            "is_pdf": Path(f.name).suffix.lower() == ".pdf",
        })

    return candidates

# ======================
#        SIDEBAR
# ======================
with st.sidebar:
    st.image("assets/logo-wayki.png", width=170)
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
        "Describe objetivo, responsabilidades y protocolos.",
        height=120,
        key="jd",
        label_visibility="collapsed",
    )

    st.markdown("### Palabras clave del perfil\n*(ajústalas si es necesario)*")
    kw_text = st.text_area(
        "Ej.: HIS, SAP IS-H, BLS, ACLS, IAAS, educación al paciente, seguridad del paciente, protocolos",
        value="HIS, SAP IS-H, BLS, ACLS, IAAS, educación al paciente, seguridad del paciente, protocolos",
        height=110,
        key="kw",
        label_visibility="collapsed",
    )

    st.markdown("### Subir CVs (PDF o TXT)")
    files = st.file_uploader(
        "Arrastra y suelta (PDF/TXT)",
        type=["pdf", "txt"],
        accept_multiple_files=True,
        label_visibility="collapsed",
    )

    st.divider()
    if st.button("Limpiar Lista", use_container_width=True):
        st.session_state.pop("candidates", None)
        st.rerun()

# ======================
#      CUERPO (UI)
# ======================
st.markdown(f"## <span style='color:{PRIMARY_GREEN}'>SelektIA – Resultados de evaluación</span>", unsafe_allow_html=True)

# Disparador automático
if files and (jd_text.strip() or kw_text.strip()):
    st.session_state.candidates = analyze_locally(jd_text, kw_text, files)

if "candidates" not in st.session_state or not st.session_state.candidates:
    st.info("Define el puesto, ajusta las palabras clave y sube 1 o más CVs (PDF/TXT). El análisis se hace automáticamente.")
else:
    df = pd.DataFrame(st.session_state.candidates)
    df_sorted = df.sort_values("Score", ascending=False)

    st.markdown("### Ranking de candidatos")
    show = df_sorted[["Nombre", "Score", "Razones", "PDF_text"]].rename(
        columns={"Nombre": "Nombre", "Score": "Score", "Razones": "Razones", "PDF_text": "PDF_text"}
    )
    st.dataframe(show, use_container_width=True, height=240)

    st.markdown("### Comparación de puntajes")
    bar_colors = [BAR_HIGHLIGHT if s >= 60 else BAR_BASE for s in df_sorted["Score"]]
    fig = px.bar(df_sorted, x="Nombre", y="Score", title="")
    fig.update_traces(marker_color=bar_colors, marker_line_color="#CBE2FF", marker_line_width=1.5)
    fig.update_layout(
        plot_bgcolor="#FFFFFF",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color=TITLE_DARK),
        xaxis_title=None,
        yaxis_title="Score",
    )
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("### Visor de CV (PDF/TXT)")
    nombres = df_sorted["Nombre"].tolist()
    selected_name = st.selectbox(
        "Selecciona un candidato:",
        nombres,
        key="pdf_candidate",
        label_visibility="collapsed",
    )

    if selected_name:
        cand = next(c for c in st.session_state.candidates if c["Nombre"] == selected_name)
        if cand["is_pdf"] and cand["file_bytes"]:
            data_b64 = base64.b64encode(cand["file_bytes"]).decode("utf-8")
            html(
                f"""
                <div style="border:1px solid {BOX_LIGHT_B}; border-radius:12px; overflow:hidden; background:#fff;">
                  <iframe
                    src="data:application/pdf;base64,{data_b64}#zoom=page-width"
                    style="width:100%; height:750px; border:0;"
                    title="Visor PDF">
                  </iframe>
                </div>
                """,
                height=770,
            )
            st.download_button(
                f"Descargar {selected_name}",
                data=cand["file_bytes"],
                file_name=selected_name,
                mime="application/pdf",
            )
        else:
            st.info(f"'{selected_name}' es un archivo de texto. Mostrando contenido:")
            try:
                txt_content = cand["file_bytes"].decode("utf-8", errors="ignore")
            except Exception:
                txt_content = "(No se pudo decodificar el contenido del TXT)"
            st.text_area("Contenido del TXT:", value=txt_content, height=600, disabled=True)
