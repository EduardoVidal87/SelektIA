# app.py
# ──────────────────────────────────────────────────────────────────────────────
# SelektIA – Evaluación de CVs (sin IA externa)
# - Colores y estilos corporativos
# - Análisis automático cuando se suben archivos
# - Gráfico con colores: base #E9F3FF y ≥60% en #33FFAC
# - Visor de PDF compacto y nítido (zoom configurable)
# ──────────────────────────────────────────────────────────────────────────────

import io
import base64
from pathlib import Path

import streamlit as st
import pandas as pd
import plotly.express as px
from PyPDF2 import PdfReader

# =============================================================================
# Colores / tema
# =============================================================================
PRIMARY_GREEN = "#00CD78"
SIDEBAR_BG = "#10172A"
BOX_DARK = "#132840"
BOX_DARK_HOV = "#193355"
TEXT_LIGHT = "#FFFFFF"
MAIN_BG = "#F7FBFF"
BOX_LIGHT = "#F1F7FD"
BOX_LIGHT_B = "#E3EDF6"
TITLE_DARK = "#142433"

# Colores del gráfico solicitados
BAR_BASE = "#E9F3FF"
BAR_HIGHLIGHT = "#33FFAC"  # ≥60%

# =============================================================================
# Configuración de página
# =============================================================================
st.set_page_config(
    page_title="SelektIA – Resultados de evaluación",
    page_icon="🧠",
    layout="wide",
)

# =============================================================================
# CSS
# =============================================================================
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

/* Inputs del sidebar */
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

/* Botones */
.stButton > button {{
  background: var(--green) !important;
  color: #082017 !important;
  border-radius: 10px !important;
  border: none !important;
  padding: .45rem .9rem !important;
  font-weight: 600 !important;
}}
.stButton > button:hover {{ filter: brightness(0.95); }}

/* Títulos en el cuerpo */
h1, h2, h3 {{ color: var(--title-dark); }}
h1 strong, h2 strong, h3 strong {{ color: var(--green); }}

/* Controles del área principal */
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

/* Select de visor */
#pdf_candidate {{
  background: var(--box-light) !important;
  border: 1.5px solid var(--box-light-border) !important;
  color: var(--title-dark) !important;
  border-radius: 10px !important;
}}
"""
st.markdown(f"<style>{CSS}</style>", unsafe_allow_html=True)

# =============================================================================
# Utilidades
# =============================================================================
def extract_text(uploaded_file) -> str:
    """Extrae texto de PDF o TXT."""
    try:
        suffix = Path(uploaded_file.name).suffix.lower()
        content = uploaded_file.read()
        uploaded_file.seek(0)
        if suffix == ".pdf":
            reader = PdfReader(io.BytesIO(content))
            text = ""
            for page in reader.pages:
                text += page.extract_text() or ""
            return text
        else:
            return content.decode("utf-8", errors="ignore")
    except Exception as e:
        st.error(f"Error al leer '{uploaded_file.name}': {e}")
        return ""

def score_and_reasons(text: str, keywords: list[str]) -> tuple[int, str]:
    """Puntaje simple por coincidencias de keywords + razones."""
    if not text:
        return 0, "Sin texto extraído."
    text_low = text.lower()
    kws = [k.strip().lower() for k in keywords if k.strip()]
    hits = [k for k in kws if k in text_low]
    n_hits = len(hits)
    n_total = max(len(kws), 1)
    # Score 0..100
    score = round(100 * n_hits / n_total)
    reasons = f"{n_hits}/{n_total} keywords encontradas — Coincidencias: {', '.join(hits) if hits else '—'}"
    return score, reasons

def analyze(files, jd_text, kw_text):
    """Devuelve DataFrame + caché de bytes para visor."""
    data = []
    cache = {}  # name -> dict(bytes,is_pdf)
    kw_list = [k.strip() for k in kw_text.split(",") if k.strip()]

    for f in files:
        raw = f.read()
        f.seek(0)
        is_pdf = Path(f.name).suffix.lower() == ".pdf"
        txt = extract_text(f)
        score, reasons = score_and_reasons(txt, kw_list)
        data.append({
            "Name": f.name,
            "Score": score,
            "Reasons": reasons,
            "PDF_text": len(txt),
        })
        cache[f.name] = {"_bytes": raw, "_is_pdf": is_pdf}

    df = pd.DataFrame(data) if data else pd.DataFrame(columns=["Name","Score","Reasons","PDF_text"])
    return df, cache

# =============================================================================
# Sidebar (oscuro)
# =============================================================================
with st.sidebar:
    st.image("assets/logo-wayki.png", use_column_width=True)

    st.markdown("### Definición del puesto")
    puesto = st.selectbox(
        "Puesto",
        ["Enfermera/o Asistencial", "Tecnólogo Médico", "Recepcionista de Admisión", "Médico General", "Químico Farmacéutico"],
        index=0,
        key="puesto",
    )

    st.markdown("### Descripción del puesto (texto libre)")
    jd_text = st.text_area(
        "Resume el objetivo del puesto, responsabilidades, protocolos y habilidades deseadas.",
        height=120,
        label_visibility="collapsed",
        key="jd",
    )

    st.markdown("### Palabras clave del perfil *(ajústalas si es necesario)*")
    kw_text = st.text_area(
        "HIS, SAP IS-H, BLS, ACLS, IAAS, educación al paciente, seguridad del paciente, protocolos",
        value="HIS, SAP IS-H, BLS, ACLS, IAAS, educación al paciente, seguridad del paciente, protocolos",
        height=110,
        label_visibility="collapsed",
        key="kw",
    )

    st.markdown("### Subir CVs (PDF o TXT)")
    files = st.file_uploader(
        "Drag and drop files here",
        type=["pdf", "txt"],
        accept_multiple_files=True,
        label_visibility="collapsed",
        key="files",
    )

    if st.button("Limpiar Lista", use_container_width=True):
        st.session_state.pop("df", None)
        st.session_state.pop("blob_cache", None)
        st.rerun()

# =============================================================================
# Área principal
# =============================================================================
st.markdown(f"## <span style='color:{PRIMARY_GREEN}'>SelektIA – Resultados de evaluación</span>", unsafe_allow_html=True)
st.info("Define el puesto/JD, edita palabras clave y sube CVs (PDF o TXT) para evaluar.")

# Análisis automático cuando se suben archivos
if files:
    df, blob_cache = analyze(files, jd_text, kw_text)
    st.session_state["df"] = df
    st.session_state["blob_cache"] = blob_cache

if "df" not in st.session_state or st.session_state["df"].empty:
    st.warning("Sube algunos CVs para ver el ranking, el gráfico y el visor.")
    st.stop()

df = st.session_state["df"].copy()
blob_cache = st.session_state["blob_cache"]

# ===================== Tabla Ranking =====================
st.markdown("### Ranking de candidatos")
show = df[["Name", "Score", "Reasons", "PDF_text"]].rename(
    columns={"Name": "Nombre", "Score": "Score", "Reasons": "Razones", "PDF_text": "PDF_text"}
)
st.dataframe(
    show,
    use_container_width=True,
    hide_index=True
)

# ===================== Gráfico =====================
st.markdown("### Comparación de puntajes")

# Construir colores barra a barra
bar_colors = [BAR_HIGHLIGHT if s >= 60 else BAR_BASE for s in df["Score"].tolist()]

fig = px.bar(
    df,
    x="Name",
    y="Score",
)
fig.update_traces(marker_color=bar_colors, hovertemplate="<b>%{x}</b><br>Score: %{y}")
fig.update_layout(
    title=None,
    plot_bgcolor="#FFFFFF",
    paper_bgcolor="rgba(0,0,0,0)",
    font=dict(color=TITLE_DARK),
    xaxis_title=None,
    yaxis_title="Score",
    margin=dict(l=10, r=10, t=10, b=10),
)
st.plotly_chart(fig, use_container_width=True)

# ===================== Visor compactado de PDF/TXT =====================
st.markdown("### Visor de CV (PDF/TXT)  <sup>↪</sup>", unsafe_allow_html=True)

all_names = df["Name"].tolist()
selected_name = st.selectbox("Elige un candidato", all_names, index=0, key="pdf_candidate")

candidate_meta = blob_cache.get(selected_name, {})
is_pdf = candidate_meta.get("_is_pdf", False)
blob = candidate_meta.get("_bytes", b"")

PDF_BORDER = BOX_LIGHT_B
VIEW_HEIGHT = 520  # altura más compacta
# Opciones de zoom mayor para una percepción de nitidez sin ocupar todo el alto
PDF_ZOOM = 125  # 125%

if is_pdf and blob:
    b64 = base64.b64encode(blob).decode("utf-8")
    # Intentamos forzar un zoom cómodo y vista adaptada al ancho
    pdf_src = f"data:application/pdf;base64,{b64}#zoom={PDF_ZOOM}&view=FitH&toolbar=0&navpanes=0"
    st.markdown(
        f"""
        <div style="border:1px solid {PDF_BORDER}; border-radius:12px; overflow:hidden; background:#fff;">
          <iframe src="{pdf_src}"
                  style="width:100%; height:{VIEW_HEIGHT}px; border:0;"
                  title="Visor PDF"></iframe>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.download_button(
        f"Descargar {selected_name}",
        data=blob,
        file_name=selected_name,
        mime="application/pdf",
        use_container_width=False,
    )
else:
    # Fallback para TXT u otros
    if blob:
        try:
            txt = blob.decode("utf-8", errors="ignore")
        except Exception:
            txt = "(No se pudo decodificar el archivo como texto)."
    else:
        txt = "(No hay datos del archivo en memoria)."

    st.text_area("Contenido del archivo:", value=txt, height=VIEW_HEIGHT, disabled=True)
    st.download_button(
        f"Descargar {selected_name}",
        data=blob,
        file_name=selected_name,
        mime="text/plain",
        use_container_width=False,
    )
