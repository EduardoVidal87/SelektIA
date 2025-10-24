# app.py
import io
import base64
from pathlib import Path

import streamlit as st
import pandas as pd
import plotly.express as px

# =========================
# Variables de tema/colores
# =========================
PRIMARY_GREEN = "#00CD78"
SIDEBAR_BG    = "#10172A"   # fondo columna izquierda
BOX_DARK      = "#132840"   # fondo y borde de boxes del sidebar
BOX_DARK_HOV  = "#193355"   # borde en hover/focus del sidebar
TEXT_LIGHT    = "#FFFFFF"   # texto blanco
MAIN_BG       = "#F7FBFF"   # fondo del cuerpo (claro)
BOX_LIGHT     = "#F1F7FD"   # fondo claro de inputs principales
BOX_LIGHT_B   = "#E3EDF6"   # borde claro de inputs principales
TITLE_DARK    = "#142433"   # texto títulos principales

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

# Inyectar CSS
st.markdown(f"<style>{CSS}</style>", unsafe_allow_html=True)

st.set_page_config(
    page_title="SelektIA",
    page_icon="🧠",
    layout="wide",
)

# ================
#  SIDEBAR (oscuro)
# ================
with st.sidebar:
    st.image("logo-wayki.png", use_column_width=True)
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
        "HIS, SAP IS-H, BLS, ACLS, IAAS, educación al paciente, seguridad, protocolos…",
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

# ===================
#  PROCESAMIENTO MVP
# ===================
def extract_text_from_file(uploaded_file) -> str:
    """MVP: si es txt leemos texto directo; si es pdf, nos quedamos con el binario para mostrar."""
    if uploaded_file.type == "text/plain":
        return uploaded_file.read().decode("utf-8", errors="ignore")
    else:
        # Para PDF, devolvemos un marcador (el texto crudo no se usa para visualizar)
        return f"[PDF] {uploaded_file.name}"

def simple_match_score(text, keywords) -> tuple[int, str]:
    """Cuenta cuántas keywords aparecen; devuelve score y detalle."""
    text_l = text.lower()
    matches = 0
    found = []
    for kw in keywords:
        k = kw.strip().lower()
        if not k:
            continue
        if k in text_l:
            matches += 1
            found.append(k)
    return matches * 10, f"{matches}/{len(keywords)} keywords encontradas — Coincidencias: {', '.join(found) if found else '—'}"

# palabras clave
keywords = [k.strip() for k in kw_text.split(",") if k.strip()]

# Construimos un dataframe sencillo
rows = []
pdf_buffers = {}  # para visualizar luego
if files:
    for f in files:
        raw = f.read()
        f.seek(0)  # volvemos al inicio para reutilizar
        ext = Path(f.name).suffix.lower()

        if ext == ".txt":
            txt = raw.decode("utf-8", errors="ignore")
            score, reason = simple_match_score(txt, keywords)
            rows.append(
                {
                    "Name": f.name,
                    "Score": score,
                    "Reasons": reason,
                    "PDF_text": f"{len(txt)} chars",
                    "is_pdf": False,
                }
            )
        else:
            # guardamos raw para visor
            pdf_buffers[f.name] = raw
            pseudo_text = f"[pdf:{len(raw)}]"
            score, reason = simple_match_score(pseudo_text, keywords)
            rows.append(
                {
                    "Name": f.name,
                    "Score": score,
                    "Reasons": reason,
                    "PDF_text": f"{len(raw)} bytes",
                    "is_pdf": True,
                }
            )

df = pd.DataFrame(rows) if rows else pd.DataFrame(columns=["Name", "Score", "Reasons", "PDF_text", "is_pdf"])

# ===================
#  UI PRINCIPAL (claro)
# ===================
st.markdown(f"## <span style='color:{PRIMARY_GREEN}'>SelektIA – Evaluation Results</span>", unsafe_allow_html=True)

st.info("Define el puesto/JD, ajusta (o edita) keywords y sube algunos CVs (PDF o TXT) para evaluar.", icon="ℹ️")

# Tabla
if not df.empty:
    st.dataframe(
        df[["Name", "Score", "Reasons", "PDF_text"]],
        use_container_width=True,
        hide_index=True,
    )

    # Gráfico simple
    fig = px.bar(
        df.sort_values("Score", ascending=False),
        x="Name",
        y="Score",
        title="Score Comparison",
    )
    fig.update_layout(
        plot_bgcolor="#FFFFFF",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color=TITLE_DARK),
        xaxis_title=None,
        yaxis_title="Score",
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.warning("Sube algunos CVs (PDF o TXT) para ver resultados.", icon="📄")

st.markdown(f"### <span style='color:{PRIMARY_GREEN}'>Visor de CV (PDF)</span>", unsafe_allow_html=True)

col1, col2 = st.columns([1, 1], gap="large")
with col1:
    st.caption("Elige un candidato")
    cand = st.selectbox(
        "",
        df["Name"].tolist() if not df.empty else [],
        key="pdf_candidate",
        label_visibility="collapsed",
    )

with col2:
    with st.expander("Elegir candidato (opción alternativa)", expanded=False):
        cand_alt = st.selectbox(
            "Candidato",
            df["Name"].tolist() if not df.empty else [],
            key="pdf_candidate_alt",
        )

# Elegimos el que tenga valor
selected = cand_alt if cand_alt else cand

# Visor PDF claro (embed)
if selected and not df.empty:
    row = df.loc[df["Name"] == selected].iloc[0]
    if bool(row["is_pdf"]) and selected in pdf_buffers:
        data_b64 = base64.b64encode(pdf_buffers[selected]).decode("utf-8")
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
        st.download_button("Descargar PDF", data=pdf_buffers[selected], file_name=selected, mime="application/pdf")
    else:
        st.info("El candidato seleccionado no es PDF o no tiene contenido PDF. Sube un PDF para previsualizar.", icon="📎")
