import io
import re
import base64
import fitz  # PyMuPDF
import pandas as pd
import streamlit as st
from pdfminer.high_level import extract_text
from streamlit_pdf_viewer import pdf_viewer

# -----------------------------
# Configuración general y tema
# -----------------------------
LOGO_PATH = "assets/logo-wayki.png"  # si lo cambias, ajusta aquí

st.set_page_config(
    page_title="SelektIA",
    page_icon=LOGO_PATH,
    layout="wide",
)

# === Brand / Theme colors ===
PRIMARY     = "#00CD78"   # títulos y acentos
SIDEBAR_BG  = "#10172A"
BOX_BG      = "#132840"   # tono más claro que el sidebar
BOX_BORDER  = "#132840"   # mismo color que la caja
BODY_BG     = "#F6F8FC"   # fondo claro del body
LIGHT_INPUT = "#F3F7FB"   # inputs claros en el main
LIGHT_BRDR  = "#D0D7E2"   # bordes claros en el main
TEXT_COLOR  = "#0B1220"   # texto principal

# -----------------------------
# Estilos
# -----------------------------
st.markdown(f"""
<style>

/* Fondo general del body */
main blockquote, .stApp {{
  background: {BODY_BG};
}}

/* Sidebar bg */
[data-testid="stSidebar"] {{
  background: {SIDEBAR_BG};
}}

/* Títulos del sidebar y del body */
[data-testid="stSidebar"] h1, 
[data-testid="stSidebar"] h2, 
[data-testid="stSidebar"] h3, 
h1, h2, h3 {{
  color: {PRIMARY} !important;
}}

/* Etiquetas/labels SOLO en el sidebar */
[data-testid="stSidebar"] [data-testid="stWidgetLabel"] p {{
  color: {PRIMARY} !important;
  font-weight: 600;
}}

/* Etiquetas del body (zona principal) */
section [data-testid="stWidgetLabel"] p {{
  color: {TEXT_COLOR} !important;
  font-weight: 600;
}}

/* Inputs del sidebar: select, text, textarea, number */
[data-testid="stSidebar"] .stTextInput>div>div>input,
[data-testid="stSidebar"] textarea,
[data-testid="stSidebar"] .stNumberInput input,
[data-testid="stSidebar"] .stSelectbox > div > div,
[data-testid="stSidebar"] .stMultiSelect > div > div {{
  background-color: {BOX_BG} !important;
  border: 1px solid {BOX_BORDER} !important;
  color: #FFFFFF !important;
  border-radius: 8px !important;
}}

/* Placeholder en sidebar */
[data-testid="stSidebar"] ::placeholder {{
  color: #C9D1D9 !important;
  opacity: .9 !important;
}}

/* Focus halo en inputs del sidebar */
[data-testid="stSidebar"] input:focus,
[data-testid="stSidebar"] textarea:focus {{
  outline: none !important;
  box-shadow: 0 0 0 2px {PRIMARY}33 !important;
}}

/* Botones del sidebar */
[data-testid="stSidebar"] .stButton > button {{
  background: {PRIMARY} !important;
  color: #0B1220 !important;
  border: 1px solid {PRIMARY} !important;
  font-weight: 700;
  border-radius: 10px;
}}
[data-testid="stSidebar"] .stButton > button:hover {{
  filter: brightness(1.05);
}}

/* --- ZONA PRINCIPAL (body) --- */

/* Selects/inputs del body en fondo CLARO */
section .stSelectbox > div > div,
section .stTextInput>div>div>input,
section textarea,
section .stNumberInput input {{
  background: {LIGHT_INPUT} !important;
  border: 1px solid {LIGHT_BRDR} !important;
  color: {TEXT_COLOR} !important;
  border-radius: 8px !important;
}}

/* Expander header claro */
section .streamlit-expanderHeader {{
  background: {LIGHT_INPUT} !important;
  border: 1px solid {LIGHT_BRDR} !important;
  color: {TEXT_COLOR} !important;
  border-radius: 8px !important;
}}

</style>
""", unsafe_allow_html=True)

# -----------------------------
# Utilidades
# -----------------------------
def clean_text(s: str) -> str:
    s = s.replace("\n", " ")
    s = re.sub(r"\s+", " ", s)
    return s.strip()

def pdf_to_text_bytes(pdf_bytes: bytes) -> str:
    """Extrae texto de un PDF (bytes) usando PyMuPDF; si falla, intenta pdfminer."""
    try:
        with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
            text = []
            for page in doc:
                text.append(page.get_text())
        return clean_text(" ".join(text))
    except Exception:
        # fallback
        try:
            text = extract_text(io.BytesIO(pdf_bytes))
            return clean_text(text or "")
        except Exception:
            return ""

def get_keywords_from_text(text: str) -> list[str]:
    """Divide por coma o salto de línea; normaliza a minúsculas y quita vacíos."""
    raw = re.split(r"[,\n]", text)
    words = [w.strip().lower() for w in raw if w.strip()]
    # eliminar duplicados respetando orden
    seen, out = set(), []
    for w in words:
        if w not in seen:
            seen.add(w)
            out.append(w)
    return out

def score_cv(cv_text: str, keywords: list[str]) -> tuple[int, list[str]]:
    """Devuelve (score_normalizado_0_100, coincidencias_encontradas)."""
    if not keywords:
        return 0, []
    found = []
    text_l = " " + cv_text.lower() + " "
    for kw in keywords:
        # búsqueda simple por palabra/frase
        if kw and kw.lower() in text_l:
            found.append(kw)
    score = round(100 * len(found) / len(keywords))
    return score, found

# -----------------------------
# SIDEBAR
# -----------------------------
with st.sidebar:
    st.image(LOGO_PATH, use_container_width=True)

    st.header("Definición del puesto")

    puesto = st.selectbox(
        "Puesto",
        options=[
            "Enfermera/o Asistencial – Hospitalización/UCI intermedia",
            "Enfermera/o UCI",
            "Enfermera/o Emergencias",
            "Otro",
        ],
        index=0,
    )

    jd_text = st.text_area(
        "Descripción del puesto (texto libre)",
        height=110,
        placeholder=(
            "Resume el objetivo del puesto, responsabilidades clave, protocolos, "
            "y contexto del servicio…"
        ),
        value=st.session_state.get("jd_text", ""),
    )

    keywords_text = st.text_area(
        "Palabras clave del perfil (ajústalas si es necesario)",
        height=110,
        placeholder=(
            "Ej.: HIS, SAP IS-H, 5 correctos, IAAS, bundles VAP/BRC/CAUTI, "
            "curación avanzada, bombas de infusión, educación al paciente…"
        ),
        value=st.session_state.get("keywords_text", "HIS, SAP IS-H, bombas de infusión, 5 correctos, IAAS, bundles VAP/BRC/CAUTI"),
    )

    st.caption("Arrastra y suelta los CVs en PDF o TXT para evaluar")
    files = st.file_uploader(
        "Upload CVs (PDF o TXT)", 
        type=["pdf", "txt"],
        accept_multiple_files=True,
        label_visibility="collapsed",
    )

# Guardar en sesión lo escrito por si recarga
st.session_state["jd_text"] = jd_text
st.session_state["keywords_text"] = keywords_text

# -----------------------------
# CUERPO
# -----------------------------
st.markdown(
    f"<h1 style='margin-top:0'>SelektIA – Evaluation Results</h1>",
    unsafe_allow_html=True
)

st.info("Define el puesto/JD, sugiere (o edita) keywords y sube algunos CVs (PDF o TXT) para evaluar.")

# Construcción de keywords a partir del JD + input explícito
jd_kw = get_keywords_from_text(jd_text)
extra_kw = get_keywords_from_text(keywords_text)
all_keywords = jd_kw + [k for k in extra_kw if k not in jd_kw]

# Procesamiento de CVs
rows = []
file_store = {}  # name -> dict(bytes, text)
if files:
    for f in files:
        if f.type == "text/plain":
            raw_text = f.getvalue().decode("utf-8", errors="ignore")
            cv_text = clean_text(raw_text)
            pdf_bytes = None
        else:
            pdf_bytes = f.getvalue()
            cv_text = pdf_to_text_bytes(pdf_bytes)

        sc, hits = score_cv(cv_text, all_keywords)
        rows.append({
            "Name": f.name.replace("_", " ").replace("-", " "),
            "Score": sc,
            "Reasons": f"{len(hits)}/{len(all_keywords)} keywords encontradas — Coincidencias: {', '.join(hits) if hits else '—'}",
            "PDF_text": f"{len(cv_text)} chars",
        })
        file_store[f.name] = {"bytes": pdf_bytes, "text": cv_text}

# Tabla de resultados
if rows:
    df = pd.DataFrame(rows).sort_values(by="Score", ascending=False).reset_index(drop=True)
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True
    )

    # Gráfico simple
    st.subheader("Score Comparison")
    import plotly.express as px
    fig = px.bar(
        df, x="Name", y="Score",
        color=df["Score"] >= 50,
        color_discrete_map={True: PRIMARY, False: "#6E7B8B"},
        labels={"color": "color"}
    )
    fig.add_hline(y=50, line_dash="dot", line_color="#566370")
    fig.update_layout(showlegend=False, height=300, margin=dict(l=8,r=8,b=30,t=10))
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("----")

    # ---------------- PDF VIEWER ----------------
    st.subheader("Visor de CV (PDF)")
    col_left, col_right = st.columns([1, 2], gap="large")

    with col_left:
        st.write("Elige un candidato")
        # Nombre de archivo -> lista
        pdf_candidates = [n for n, meta in file_store.items() if meta["bytes"]]
        # El select ahora es CLARO por CSS (zona principal)
        selected_name = st.selectbox(
            label="",
            options=pdf_candidates,
            index=0 if pdf_candidates else None,
            placeholder="Selecciona un CV en PDF…",
            label_visibility="collapsed"
        )

        with st.expander("Elegir candidato (opción alternativa)"):
            alt = st.radio("Candidatos PDF:", pdf_candidates, label_visibility="collapsed") if pdf_candidates else None
            if alt:
                selected_name = alt

    with col_right:
        if selected_name:
            st.caption(f"Mostrando: **{selected_name}**")
            b = file_store[selected_name]["bytes"]
            if b:
                # Visor PDF
                pdf_viewer(input=b, width=900, height=780)
            else:
                st.warning("Este CV no es PDF o no tiene bytes disponibles.")

else:
    st.warning("Sube algunos CVs (PDF o TXT) para ver resultados y el visor de PDF.")
