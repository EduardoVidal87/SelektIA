import base64
import io
import re
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

# ========= VISOR PDF (preferido) =========
# - Si existe streamlit-pdf-viewer se usa; si no, cae a iframe base64.
try:
    from streamlit_pdf_viewer import pdf_viewer   # pip install streamlit-pdf-viewer
    HAS_PDF_VIEWER = True
except Exception:
    HAS_PDF_VIEWER = False


# ========= LECTURA DE PDF (texto) =========
# - Intento 1: PyMuPDF (fitz) → rápido
# - Intento 2: pdfminer.six → fallback
def extract_text_from_pdf_bytes(pdf_bytes: bytes) -> str:
    text = ""
    # PyMuPDF
    try:
        import fitz  # PyMuPDF
        with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
            for page in doc:
                text += page.get_text()
        if text.strip():
            return text
    except Exception:
        pass

    # pdfminer.six
    try:
        from pdfminer.high_level import extract_text as pdfminer_extract
        text = pdfminer_extract(io.BytesIO(pdf_bytes))
        return text or ""
    except Exception:
        return ""


# ========= CONFIG BÁSICA =========
st.set_page_config(
    page_title="SelektIA",
    page_icon="📄",
    layout="wide"
)

# Paleta / Tokens
PRIMARY = "#00CD78"
SIDEBAR_BG = "#0B1A2B"
BOX_DARK = "#132840"
BOX_DARK_HOVER = "#0F223A"
TEXT = "#FFFFFF"
MAIN_BG = "#FFFFFF"
BOX_LIGHT = "#F0F5FA"
BOX_LIGHT_BORDER = "#E3EDF6"
RADIUS = "12px"

# ========= ESTILOS (CSS) =========
CSS = f"""
<style>
/*------------- Global -------------*/
:root {{
  --dark: {SIDEBAR_BG};
  --box: {BOX_DARK};
  --box-hover: {BOX_DARK_HOVER};
  --main-bg: {MAIN_BG};
  --box-light: {BOX_LIGHT};
  --box-light-border: {BOX_LIGHT_BORDER};
  --primary: {PRIMARY};
  --text: {TEXT};
}}

html, body, [data-testid="stAppViewContainer"] {{
  background: var(--main-bg) !important;
}}

/*------------- Sidebar -------------*/
[data-testid="stSidebar"] {{
  background: linear-gradient(180deg, #0B1A2B 0%, #0B1A2B 100%) !important;
  border-right: 1px solid #0B2237 !important;
}}
[data-testid="stSidebar"] * {{ color: var(--text); }}
[data-testid="stSidebar"] h3, 
[data-testid="stSidebar"] h4, 
[data-testid="stSidebar"] label, 
[data-testid="stSidebar"] p {{
  color: var(--text) !important;
}}

/* Título del contenido */
h1, h2 {{
  color: {PRIMARY} !important;
  letter-spacing: .2px;
}}

/*------------- Boxes oscuros unificados en sidebar -------------*/
/* SELECT (cerrado/abierto) */
[data-testid="stSidebar"] [data-testid="stSelectbox"] > div > div,
[data-testid="stSidebar"] [data-baseweb="select"] {{
  background: var(--box) !important;
  border: 1.5px solid var(--box) !important;
  border-radius: {RADIUS} !important;
  box-shadow: none !important;
}}
[data-testid="stSidebar"] [data-baseweb="select"]:hover,
[data-testid="stSidebar"] [data-baseweb="select"]:focus {{
  border-color: var(--box-hover) !important;
}}

/* INPUT */
[data-testid="stSidebar"] [data-testid="stTextInput"] input {{
  background: var(--box) !important;
  color: var(--text) !important;
  border: 1.5px solid var(--box) !important;
  border-radius: {RADIUS} !important;
  box-shadow: none !important;
}}
[data-testid="stSidebar"] [data-testid="stTextInput"] input:hover,
[data-testid="stSidebar"] [data-testid="stTextInput"] input:focus {{
  border-color: var(--box-hover) !important;
}}

/* TEXTAREA */
[data-testid="stSidebar"] [data-testid="stTextArea"] textarea {{
  background: var(--box) !important;
  color: var(--text) !important;
  border: 1.5px solid var(--box) !important;
  border-radius: {RADIUS} !important;
  box-shadow: none !important;
}}
[data-testid="stSidebar"] [data-testid="stTextArea"] textarea:hover,
[data-testid="stSidebar"] [data-testid="stTextArea"] textarea:focus {{
  border-color: var(--box-hover) !important;
}}
[data-testid="stSidebar"] [data-testid="stTextArea"] textarea::-webkit-resizer {{
  background: var(--box) !important;
}}

/* FILE DROPPER */
[data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] {{
  background: var(--box) !important;
  border: 1.5px solid var(--box) !important;
  border-radius: {RADIUS} !important;
  box-shadow: none !important;
}}
[data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"]:hover {{
  border-color: var(--box-hover) !important;
}}
[data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] button {{
  background: var(--primary) !important;
  color: #021 !important;
  border: 1px solid var(--primary) !important;
  border-radius: {RADIUS} !important;
  font-weight: 800 !important;
}}

/* Tarjetas archivo subido */
[data-testid="stSidebar"] [data-testid="stFileUploader"] .uploadedFile {{
  background: var(--box) !important;
  border: 1.5px solid var(--box) !important;
  border-radius: {RADIUS} !important;
  color: var(--text) !important;
}}
.uploadedFileName, .uploadedFileSize {{ color: var(--text) !important; }}
[data-testid="stSidebar"] [data-testid="stFileUploader"] .uploadedFile::before{{
  content: "PDF";
  display:inline-flex; align-items:center; justify-content:center;
  width:28px; height:28px; margin-right:.6rem;
  background:#FF5252; color:#fff; font-weight:900; border-radius:6px;
}}

/* Botones genéricos */
[data-testid="stSidebar"] button {{
  border-radius: 100px !important;
  font-weight: 800 !important;
}}
[data-testid="stSidebar"] .stButton>button {{
  background: var(--primary) !important; 
  color: #011014 !important;
}}

/*------------- Boxes claros en el main -------------*/
.block-container [data-testid="stTextArea"] textarea,
.block-container [data-testid="stTextInput"] input,
.block-container [data-testid="stSelectbox"] > div > div,
.block-container [data-baseweb="select"] {{
  background: var(--box-light) !important;
  color: #142433 !important;
  border: 1.5px solid var(--box-light-border) !important;
  border-radius: {RADIUS} !important;
  box-shadow: none !important;
}}
.block-container [data-baseweb="select"]:hover,
.block-container [data-baseweb="select"]:focus {{
  border-color: #C9D9EA !important;
}}

[data-testid="stExpander"] div[role="button"] {{
  background: var(--box-light) !important;
  color: #123 !important;
  border: 1.5px solid var(--box-light-border) !important;
  border-radius: {RADIUS} !important;
}}
[data-testid="stExpander"] .streamlit-expanderContent {{
  background: #FAFCFF !important;
  border: 1.5px solid var(--box-light-border) !important;
  border-top: none !important;
  border-radius: 0 0 {RADIUS} {RADIUS} !important;
}}

/* Tablas */
[data-testid="stTable"] {{
  border-radius: {RADIUS};
  overflow: hidden;
  border: 1px solid var(--box-light-border);
}}
thead tr {{
  background: #EAF3FF !important; 
  color: #0B2545 !important;
}}

/* Títulos secundarios */
h3, h4, h5 {{
  color: {PRIMARY} !important;
}}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


# ========= LOGO =========
with st.sidebar:
    logo_path = Path("logo-wayki.png")
    if logo_path.exists():
        st.image(str(logo_path), use_container_width=True)
    st.markdown("### Definición del puesto")

# ========= SIDEBAR: inputs =========
with st.sidebar:
    puesto = st.selectbox("Puesto", ["Enfermera/o Asistencial – Hospitalización / UCI Intermedia"], index=0)

    jd_text = st.text_area("Descripción del puesto (texto libre)",
                           "Resume el objetivo del puesto, responsabilidades, protocolos y requisitos clave.",
                           height=110)

    st.markdown("### Palabras clave del perfil\n*(ajústalas si es necesario)*")
    kw_default = "HIS, SAP IS-H, BLS, ACLS, IAAS, educación al paciente, seguridad del paciente, bombas de infusión"
    kw_text = st.text_area("",
                           kw_default,
                           help="Se usarán para evaluar coincidencias en los CVs.",
                           height=110)

    st.markdown("### Subir CVs (PDF o TXT)")
    files = st.file_uploader("Drag and drop files here", type=["pdf", "txt"], accept_multiple_files=True)

# ========= PROCESAMIENTO =========
# Guardamos en memoria: nombre -> (bytes, texto)
file_store = {}
rows = []

if files:
    for f in files:
        raw = f.read()
        name = f.name
        if name.lower().endswith(".pdf"):
            txt = extract_text_from_pdf_bytes(raw)
        else:
            # .txt
            try:
                txt = raw.decode("utf-8", errors="ignore")
            except Exception:
                txt = ""
        file_store[name] = {"bytes": raw, "text": txt}

    # Keywords
    # guardamos como lista, normalizando a minúsculas
    kw_tokens = [k.strip().lower() for k in re.split(r"[;,/\n]+", kw_text) if k.strip()]
    # Score rápido: cantidad de keywords encontradas (no exacta, pero suficiente para demo)
    for name, blob in file_store.items():
        text = blob["text"].lower()
        found = [k for k in kw_tokens if k and k in text]
        score = len(found)
        rows.append({
            "Name": name,
            "Score": score,
            "Reasons": f"{score}/{len(kw_tokens)} keywords encontradas — Coincidencias: {', '.join(found[:6]) or '—'}",
            "PDF_text": f"{len(text)} chars"
        })

df = pd.DataFrame(rows) if rows else pd.DataFrame(columns=["Name", "Score", "Reasons", "PDF_text"])

# ========= MAIN CONTENT =========
st.title("SelektIA – Evaluation Results")
st.info("Define el puesto/JD, sugiere (o edita) keywords y sube algunos CVs (PDF o TXT) para evaluar.")

if df.empty:
    st.warning("Sube algunos CVs para ver resultados.")
    st.stop()

# Tabla
st.table(df)

# Chart
st.subheader("Score Comparison")
threshold = st.slider("Umbral de selección", 0, max(1, df["Score"].max()),  max(1, df["Score"].max()//2 or 1))
fig = px.bar(df, x="Name", y="Score", color=df["Score"] >= threshold,
             color_discrete_map={True: PRIMARY, False: "#D9E4F2"})
fig.update_layout(showlegend=False, height=380, margin=dict(l=10, r=10, t=10, b=0))
st.plotly_chart(fig, use_container_width=True)

# ========= VISOR PDF =========
st.subheader("Visor de CV (PDF)")

colL, colR = st.columns([1, 1])

with colL:
    # selector principal
    names = list(df["Name"])
    main_choice = st.selectbox("Elige un candidato", names, index=0)
    st.caption(f"Mostrando: {main_choice}")

with colR:
    with st.expander("Elegir candidato (opción alternativa)"):
        alt_choice = st.selectbox("Candidato", names, key="alt_sel")
        # Si el alternativo difiere, usamos ese
        if alt_choice and alt_choice != main_choice:
            main_choice = alt_choice

# Botón descargar
pdf_bytes = file_store.get(main_choice, {}).get("bytes", b"")
c1, c2 = st.columns([0.15, 0.85])
with c1:
    if pdf_bytes:
        st.download_button("Descargar PDF", pdf_bytes, file_name=Path(main_choice).name, type="primary")

# Viewer
# 1) si tenemos el viewer
if pdf_bytes and Path(main_choice).suffix.lower() == ".pdf" and HAS_PDF_VIEWER:
    pdf_viewer(input=pdf_bytes, width=1200, height=750, render_text=True, pages_to_render=[1, 9999])
# 2) Fallback iframe base64
elif pdf_bytes and Path(main_choice).suffix.lower() == ".pdf":
    b64 = base64.b64encode(pdf_bytes).decode("utf-8")
    st.markdown(
        f"""
        <iframe src="data:application/pdf;base64,{b64}" 
                width="100%" height="750px" style="border:1px solid {BOX_LIGHT_BORDER}; border-radius:{RADIUS};">
        </iframe>
        """,
        unsafe_allow_html=True
    )
else:
    st.info("El archivo seleccionado no es PDF o está vacío.")
