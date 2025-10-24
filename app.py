import io
import base64
import re
from pathlib import Path

import streamlit as st
import pandas as pd
import plotly.express as px
from PyPDF2 import PdfReader

# =========================
# Variables de tema/colores
# =========================
PRIMARY_GREEN = "#00CD78"
SIDEBAR_BG    = "#10172A"  # fondo columna izquierda
BOX_DARK      = "#132840"  # fondo y borde de boxes del sidebar
BOX_DARK_HOV  = "#193355"  # borde en hover/focus del sidebar
TEXT_LIGHT    = "#FFFFFF"  # texto blanco
MAIN_BG       = "#F7FBFF"  # fondo del cuerpo (claro)
BOX_LIGHT     = "#F1F7FD"  # fondo claro de inputs principales
BOX_LIGHT_B   = "#E3EDF6"  # borde claro de inputs principales
TITLE_DARK    = "#142433"  # texto títulos principales

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

/* Sidebar fondo + texto */
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
[data-testid="stSidebar"] h6 {{
  color: var(--green) !important;
  margin-bottom: .25rem !important;
}}
/* Subtítulos/markdown del sidebar */
[data-testid="stSidebar"] .stMarkdown p strong,
[data-testid="stSidebar"] .stMarkdown p em {{
  color: var(--green) !important;
}}
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
/* Hover/focus */
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
h1, h2, h3 {{
  color: var(--title-dark) !important;
}}
h1 strong, h2 strong, h3 strong {{
  color: var(--green) !important;
}}

/* Inputs del área principal (claros) */
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
#pdf_candidate {{
  background: var(--box-light) !important;
  border: 1.5px solid var(--box-light-border) !important;
  color: var(--title-dark) !important;
  border-radius: 10px !important;
}}
"""

# Inyectar CSS
st.set_page_config(page_title="SelektIA", page_icon="🧠", layout="wide")
st.markdown(f"<style>{CSS}</style>", unsafe_allow_html=True)

# =================================
#  FUNCIONES DE PROCESAMIENTO
# =================================

def extract_text_from_file_bytes(file_name: str, file_bytes: bytes) -> str:
    """Extrae texto de PDF (PyPDF2) o TXT usando bytes."""
    try:
        if Path(file_name).suffix.lower() == ".pdf":
            pdf_reader = PdfReader(io.BytesIO(file_bytes))
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() or ""
            return text
        else:
            return file_bytes.decode("utf-8", errors="ignore")
    except Exception as e:
        st.error(f"Error al leer '{file_name}': {e}")
        return ""

def score_by_keywords(text: str, keywords_text: str) -> tuple[int, list[str]]:
    """
    Calcula score por coincidencia simple de keywords.
    Devuelve (score_0_100, lista_keywords_encontradas).
    """
    text_l = text.lower()
    # Separar por coma/; y saltos de línea
    raw = re.split(r"[,\n;]+", keywords_text)
    kws = [k.strip().lower() for k in raw if k.strip()]
    if not kws:
        return 0, []

    found = []
    for kw in kws:
        # Coincidencia sencilla por substring
        if kw and kw in text_l:
            found.append(kw)
    score = int(round(100 * len(found) / len(kws)))
    return score, found

def analyze_cvs_simple(jd_text: str, keywords_text: str, files):
    """
    Analiza CVs sin IA: ranking por coincidencia de keywords.
    Guarda resultados en st.session_state.candidates (para tabla, gráfico y visor).
    """
    st.session_state.candidates = []
    for file in files:
        file_bytes = file.getvalue()  # bytes del archivo
        text = extract_text_from_file_bytes(file.name, file_bytes)
        if not text:
            continue

        score, found = score_by_keywords(text, keywords_text)
        reasons = f"{len(found)}/{len(re.split(r'[\\n,;]+', keywords_text.strip()))} keywords encontradas — Coincidencias: " \
                  f"{', '.join(found) if found else 'ninguna'}"

        st.session_state.candidates.append({
            "Name": file.name,
            "Score": score,
            "Reasons": reasons,
            "PDF_text": len(text),           # cantidad de caracteres del texto
            "file_bytes": file_bytes,        # para visor/descarga
            "is_pdf": Path(file.name).suffix.lower() == ".pdf"
        })

    # Ordenar por score desc
    st.session_state.candidates.sort(key=lambda x: x["Score"], reverse=True)
    st.success(f"¡Análisis completo! {len(st.session_state.candidates)} CV(s) procesados.")
    st.rerun()

# ================
#  SIDEBAR (oscuro)
# ================
with st.sidebar:
    st.image("assets/logo-wayki.png", use_column_width=True)
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
        height=120,
        key="jd",
        label_visibility="collapsed",
    )

    st.markdown("### Palabras clave del perfil\n*(ajústalas si es necesario)*")
    kw_text = st.text_area(
        "HIS, SAP IS-H, BLS, ACLS, IAAS, educación al paciente, seguridad del paciente, protocolos",
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
        key="files_uploader"
    )

    if st.button("Analizar CVs", type="primary", use_container_width=True):
        if not files:
            st.error("¡Por favor, sube al menos un CV!")
        else:
            analyze_cvs_simple(jd_text, kw_text, files)

    st.divider()
    if st.session_state.get("candidates"):
        if st.button("Limpiar Lista", use_container_width=True):
            st.session_state.candidates = []
            st.success("Resultados limpiados.")
            st.rerun()

# ===================
#  UI PRINCIPAL (claro)
# ===================
st.markdown(f"## <span style='color:{PRIMARY_GREEN}'>SelektIA – Evaluation Results</span>", unsafe_allow_html=True)
st.markdown(
    f"<div style='padding:.6rem 1rem; background:{BOX_LIGHT}; border:1px solid {BOX_LIGHT_B}; border-radius:10px;'>"
    "Define el puesto/JD, sugiere (o edita) keywords y sube algunos CVs (PDF o TXT) para evaluar."
    "</div>",
    unsafe_allow_html=True
)

if not st.session_state.get("candidates"):
    st.info("Carga CVs en la barra lateral y pulsa **Analizar CVs** para ver el ranking.", icon="ℹ️")
else:
    # DataFrame para tabla y gráfico (como en la 2da imagen)
    df = pd.DataFrame(st.session_state.candidates)

    # ---------- Tabla (Ranking por score) ----------
    st.markdown("### Ranking de Candidatos")
    df_table = df[["Name", "Score", "Reasons", "PDF_text"]].copy()
    df_table = df_table.rename(columns={"Name": "Name", "Score": "Score", "Reasons": "Reasons", "PDF_text": "PDF_text"})
    # Mostrar la tabla en estilo claro
    st.dataframe(
        df_table,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Score": st.column_config.NumberColumn("Score", help="Puntaje 0-100", format="%d"),
            "PDF_text": st.column_config.NumberColumn("PDF_text", help="Cantidad de caracteres", format="%d chars")
        }
    )

    # ---------- Gráfico ----------
    st.markdown("### Score Comparison")
    fig = px.bar(
        df.sort_values("Score", ascending=False),
        x="Name", y="Score",
        color="Score",
        color_continuous_scale=px.colors.sequential.Greens_r,
        title=None
    )
    fig.update_layout(
        plot_bgcolor="#FFFFFF",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color=TITLE_DARK),
        xaxis_title=None,
        yaxis_title="Score",
        margin=dict(l=10, r=10, t=10, b=10),
        coloraxis_showscale=False
    )
    st.plotly_chart(fig, use_container_width=True)

    # ---------- Visor de PDF ----------
    st.markdown(f"### <span style='color:{PRIMARY_GREEN}'>Visor de CV (PDF)</span>", unsafe_allow_html=True)
    st.caption("Elige un candidato de la lista para ver su CV original.")

    names = df["Name"].tolist()
    selected_name = st.selectbox(
        "Elige un candidato",
        names,
        key="pdf_candidate",
        label_visibility="collapsed"
    )

    if selected_name:
        cand = next(c for c in st.session_state.candidates if c["Name"] == selected_name)

        if cand["is_pdf"] and cand["file_bytes"]:
            data_b64 = base64.b64encode(cand["file_bytes"]).decode("utf-8")
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
            st.download_button(
                f"Descargar {selected_name}",
                data=cand["file_bytes"],
                file_name=selected_name,
                mime="application/pdf"
            )
        else:
            st.info(f"'{selected_name}' es un TXT. Mostrando contenido:")
            txt = cand["file_bytes"].decode("utf-8", errors="ignore")
            st.text_area("Contenido del TXT:", value=txt, height=600, disabled=True)
