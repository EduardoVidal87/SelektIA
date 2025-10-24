# app.py
import io
import re
import base64
from datetime import date
from pathlib import Path

import streamlit as st
import pandas as pd
import plotly.express as px
from PyPDF2 import PdfReader

# =========================
# Paleta y estilos globales
# =========================
PRIMARY_GREEN = "#00CD78"
SIDEBAR_BG = "#10172A"          # fondo columna izquierda
BOX_DARK = "#132840"            # contenedores del sidebar
BOX_DARK_HOV = "#193355"        # hover/focus
TEXT_LIGHT = "#FFFFFF"
MAIN_BG = "#F7FBFF"             # fondo claro principal
BOX_LIGHT = "#F1F7FD"
BOX_LIGHT_B = "#E3EDF6"
TITLE_DARK = "#142433"

BARS_LOW = "#E9F3FF"            # < 60%
BARS_HIGH = "#33FFAC"           # >= 60%

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
.block-container {{
  background: transparent !important;
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

/* ---- BOXES del sidebar con diseño tipo pastilla ---- */
.sidebar-pill > div > div {{
  background: var(--box) !important;
  color: var(--text) !important;
  border: 1.5px solid var(--box) !important;
  border-radius: 14px !important;
  box-shadow: none !important;
}}
.sidebar-pill input,
.sidebar-pill textarea {{
  background: var(--box) !important;
  color: var(--text) !important;
  border: 1.5px solid var(--box) !important;
  border-radius: 14px !important;
}}
.sidebar-pill input:hover,
.sidebar-pill textarea:hover,
.sidebar-pill input:focus,
.sidebar-pill textarea:focus {{
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
/* Pills de archivos */
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

/* Títulos del cuerpo */
h1, h2, h3 {{ color: var(--title-dark); }}
h1 strong, h2 strong, h3 strong {{ color: var(--green); }}

/* Inputs claros en el cuerpo */
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

/* Chips / Badges */
.badge {{
  display:inline-block;
  padding: .15rem .5rem;
  border-radius: 999px;
  font-size: .78rem;
  border:1px solid #dbe7f3;
  background:#f8fbff;
  color:#29506b;
}}
.badge-green {{
  background:#eafff6;border-color:#b7f3de;color:#0a7652;
}}
"""

st.set_page_config(page_title="SelektIA", page_icon="🧠", layout="wide")
st.markdown(f"<style>{CSS}</style>", unsafe_allow_html=True)

# ======================
# Helpers / utilidades
# ======================
def extract_text_from_file(uploaded_file) -> str:
    """Extrae texto de PDF o TXT con tolerancia a errores."""
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

def score_by_keywords(text: str, keywords: list[str]) -> tuple[int, str]:
    """Devuelve (score, reasons) según ocurrencias simples de keywords."""
    if not text or not keywords:
        return 0, "Sin coincidencias"
    text_low = text.lower()
    hits = []
    for kw in keywords:
        kw_clean = kw.strip().lower()
        if not kw_clean:
            continue
        if re.search(rf"\\b{re.escape(kw_clean)}\\b", text_low):
            hits.append(kw_clean)
    score = int(round(100 * len(hits) / max(1, len([k for k in keywords if k.strip()]))))
    reasons = f"{len(hits)}/{len([k for k in keywords if k.strip()])} keywords encontradas — Coincidencias: {', '.join(hits) or 'ninguna'}"
    return score, reasons

def color_for_score(v):
    try:
        return BARS_HIGH if float(v) >= 60 else BARS_LOW
    except:
        return BARS_LOW

def ensure_session_keys():
    for k, v in {
        "candidates": [],
        "pipeline": None
    }.items():
        if k not in st.session_state:
            st.session_state[k] = v

ensure_session_keys()

# ================
#  SIDEBAR (oscuro)
# ================
with st.sidebar:
    st.image("assets/logo-wayki.png", use_column_width=True)

    st.markdown("### Definición del puesto", unsafe_allow_html=True)
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
        label_visibility="collapsed"
    )
    # Select con estilo pastilla
    st.markdown('<div class="sidebar-pill">', unsafe_allow_html=True)
    st.selectbox(" ", options=[puesto], index=0, key="puesto_dummy", label_visibility="collapsed")
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("### Descripción del puesto (texto libre)")
    st.markdown('<div class="sidebar-pill">', unsafe_allow_html=True)
    jd_text = st.text_area(
        " ",
        height=120,
        key="jd",
        value="",
        label_visibility="collapsed",
    )
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("### Palabras clave del perfil\n*(ajústalas si es necesario)*")
    st.markdown('<div class="sidebar-pill">', unsafe_allow_html=True)
    kw_text = st.text_area(
        " ",
        value="HIS, SAP IS-H, BLS, ACLS, IAAS, educación al paciente, seguridad del paciente, protocolos",
        height=110,
        key="kw",
        label_visibility="collapsed",
    )
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("### Subir CVs (PDF o TXT)")
    files = st.file_uploader(
        "Drag and drop files here",
        type=["pdf", "txt"],
        accept_multiple_files=True,
        label_visibility="collapsed",
        key="files"
    )

    if 'candidates' in st.session_state and st.session_state.candidates:
        if st.button("Limpiar Lista", use_container_width=True):
            st.session_state.candidates = []
            st.session_state.pipeline = None
            st.success("Resultados limpiados.")
            st.rerun()

# =====================================
#  Procesar archivos (sin IA, por reglas)
# =====================================
# Cuando subes/actualizas archivos, recalculamos
if files:
    # Reset candidatos si cambian los archivos
    st.session_state.candidates = []
    kws = [k.strip() for k in kw_text.split(",") if k.strip()]
    progress = st.progress(0, "Analizando CVs...")
    for i, f in enumerate(files):
        raw = f.read()
        f.seek(0)
        text = extract_text_from_file(f)
        score, reasons = score_by_keywords(text, kws)
        st.session_state.candidates.append({
            "Name": f.name,
            "Score": score,
            "Reasons": reasons,
            "_bytes": raw,
            "_is_pdf": Path(f.name).suffix.lower() == ".pdf",
            "PDF_text_chars": len(text or "")
        })
        progress.progress((i+1)/len(files), f"Procesado: {f.name}")
    progress.empty()

# ===================
#  UI PRINCIPAL (claro)
# ===================
st.markdown(f"## <span style='color:{PRIMARY_GREEN}'>SelektIA – Resultados de evaluación</span>", unsafe_allow_html=True)
st.caption("Define el puesto/JD, edita las palabras clave y sube algunos CVs (PDF o TXT) para evaluar.")

if not st.session_state.candidates:
    st.info("Sube CVs en la barra lateral para iniciar.", icon="ℹ️")

if st.session_state.candidates:
    df = pd.DataFrame(st.session_state.candidates)
    df_sorted = df.sort_values("Score", ascending=False)

    # ===== Tabla tipo ranking resumida =====
    with st.container(border=True):
        st.markdown("#### Ranking de candidatos")
        show = df_sorted[["Name", "Score", "Reasons", "PDF_text_chars"]].rename(columns={
            "Name": "Nombre", "Score": "Score", "Reasons": "Razones", "PDF_text_chars":"PDF_text"
        })
        st.dataframe(show, use_container_width=True, hide_index=True)

    # ===== Gráfico con colores (≥60 verde) =====
    st.markdown("### Comparación de puntajes")
    df_sorted = df_sorted.copy()
    df_sorted["Color"] = df_sorted["Score"].apply(color_for_score)
    fig = px.bar(
        df_sorted,
        x="Name", y="Score",
        title=None,
        text="Score"
    )
    fig.update_traces(marker_color=df_sorted["Color"], textposition="outside")
    fig.update_layout(
        plot_bgcolor="#FFFFFF",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color=TITLE_DARK),
        xaxis_title=None, yaxis_title="Score",
        margin=dict(l=10, r=10, t=10, b=10),
        height=320
    )
    st.plotly_chart(fig, use_container_width=True)

    # =======================================================
    #   NUEVO: Pipeline de candidatos (estilo sourcing, ES)
    # =======================================================
    st.markdown("### Pipeline de candidatos")
    st.caption("Avanza etapas, registra contacto, fuente y notas. (Se guarda en memoria de la sesión).")

    # inicializar pipeline a partir de candidatos si no existe
    if st.session_state.pipeline is None:
        pipe = pd.DataFrame({
            "Candidato": df_sorted["Name"],
            "Match_%": df_sorted["Score"],
            "Etapa": "Leads",
            "Último_contacto": pd.NaT,
            "Fuente": ["CV"]*len(df_sorted),
            "Notas": ["" for _ in range(len(df_sorted))],
        })
        st.session_state.pipeline = pipe

    pipe = st.session_state.pipeline

    # Opciones de etapas
    etapas = ["Leads", "Contactado", "Aplicante", "Entrevista (Gerencia)", "Oferta", "Archivado"]

    # Configuración visual del data_editor
    pipe_view = st.data_editor(
        pipe,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Match_%": st.column_config.NumberColumn(
                "Match (%)", help="Puntaje de coincidencia", min_value=0, max_value=100, step=1, format="%d"
            ),
            "Etapa": st.column_config.SelectboxColumn(
                "Etapa", options=etapas, help="Etapa del pipeline"
            ),
            "Último_contacto": st.column_config.DateColumn(
                "Último contacto", help="Fecha del último contacto"
            ),
            "Fuente": st.column_config.TextColumn(
                "Fuente", help="Origen del candidato (CV, Referral, Job Board, LinkedIn…)"
            ),
            "Notas": st.column_config.TextColumn(
                "Notas", help="Comentarios rápidos"
            ),
        },
        key="pipeline_editor"
    )
    # Guardar cambios
    st.session_state.pipeline = pipe_view

    # Botones rápidos
    c1, c2, c3 = st.columns([1,1,2])
    with c1:
        if st.button("Marcar contacto hoy (seleccionados)"):
            # Para simplificar: marcar contacto hoy a todos en ‘Contactado’
            pipe_view.loc[pipe_view["Etapa"] == "Contactado", "Último_contacto"] = pd.to_datetime(date.today())
            st.session_state.pipeline = pipe_view
            st.success("Se marcó ‘Último contacto’ con la fecha de hoy para los candidatos en ‘Contactado’.")
            st.rerun()
    with c2:
        if st.button("Mover Leads → Contactado"):
            mask = pipe_view["Etapa"] == "Leads"
            pipe_view.loc[mask, "Etapa"] = "Contactado"
            st.session_state.pipeline = pipe_view
            st.success("Se movieron los Leads a ‘Contactado’.")
            st.rerun()

    # Resumen por etapa
    with st.expander("Resumen por etapa"):
        resumen = pipe_view.groupby("Etapa").size().reset_index(name="Candidatos")
        st.dataframe(resumen, hide_index=True, use_container_width=True)

    # ==============
    #  Visor de CV
    # ==============
    st.markdown("### Visor de CV (PDF/TXT)  <span class='badge'>elige un candidato</span>", unsafe_allow_html=True)

    all_names = df.sort_values("Name")["Name"].tolist()
    selected_name = st.selectbox("Elige un candidato", all_names, index=0, label_visibility="collapsed")

    if selected_name:
        cand = next(c for c in st.session_state.candidates if c["Name"] == selected_name)
        if cand["_is_pdf"] and cand["_bytes"]:
            data_b64 = base64.b64encode(cand["_bytes"]).decode("utf-8")
            st.markdown(
                f"""
                <div style="border:1px solid {BOX_LIGHT_B}; border-radius:12px; overflow:hidden; background:#fff;">
                  <iframe src="data:application/pdf;base64,{data_b64}#toolbar=1&navpanes=0&scrollbar=1" 
                          style="width:100%; height:520px; border:0;"
                          title="PDF Viewer"></iframe>
                </div>
                """,
                unsafe_allow_html=True,
            )
            st.download_button(
                f"Descargar {selected_name}",
                data=cand["_bytes"],
                file_name=selected_name,
                mime="application/pdf"
            )
        else:
            st.info(f"'{selected_name}' es un archivo de texto. Mostrando contenido:")
            txt_content = cand["_bytes"].decode("utf-8", errors="ignore")
            st.text_area("Contenido del TXT:", value=txt_content, height=500, disabled=True)
