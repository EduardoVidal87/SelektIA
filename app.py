# app.py
import io
import base64
import re
from pathlib import Path

import streamlit as st
import pandas as pd
import plotly.express as px
from PyPDF2 import PdfReader  # Lector PDF

# =========================
# Variables de tema/colores
# =========================
PRIMARY_GREEN = "#00CD78"
SIDEBAR_BG = "#10172A"   # fondo columna izquierda
BOX_DARK = "#132840"     # fondo y borde de boxes del sidebar
BOX_DARK_HOV = "#193355" # borde en hover/focus del sidebar
TEXT_LIGHT = "#FFFFFF"   # texto blanco
MAIN_BG = "#F7FBFF"      # fondo del cuerpo (claro)
BOX_LIGHT = "#F1F7FD"    # fondo claro de inputs principales
BOX_LIGHT_B = "#E3EDF6"  # borde claro de inputs principales
TITLE_DARK = "#142433"   # texto títulos principales

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

/* --- TÍTULOS DEL SIDEBAR EN VERDE (#00CD78) --- */
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
.stButton > button:hover {{ filter: brightness(0.95); }}

/* Títulos del cuerpo */
h1, h2, h3 {{ color: var(--title-dark); }}
h1 strong, h2 strong, h3 strong {{ color: var(--green); }}

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
#pdf_candidate, #pdf_candidate_alt {{
  background: var(--box-light) !important;
  border: 1.5px solid var(--box-light-border) !important;
  color: var(--title-dark) !important;
  border-radius: 10px !important;
}}
"""

# Inyectar CSS y configurar página
st.set_page_config(page_title="SelektIA", page_icon="🧠", layout="wide")
st.markdown(f"<style>{CSS}</style>", unsafe_allow_html=True)

# =================================
#  FUNCIONES (sin IA)
# =================================
def extract_text_from_pdf_bytes(pdf_bytes: bytes) -> str:
    """Extrae texto de un PDF usando PyPDF2."""
    try:
        reader = PdfReader(io.BytesIO(pdf_bytes))
        text = ""
        for page in reader.pages:
            text += page.extract_text() or ""
        return text
    except Exception:
        return ""

def extract_text_from_file(uploaded_file) -> tuple[str, bytes, bool]:
    """
    Devuelve (texto, bytes, es_pdf).
    - Si es TXT: lee texto directo.
    - Si es PDF: devuelve texto extraído y bytes para visor.
    """
    raw = uploaded_file.read()
    suffix = Path(uploaded_file.name).suffix.lower()
    if suffix == ".txt":
        txt = raw.decode("utf-8", errors="ignore")
        return txt, raw, False
    elif suffix == ".pdf":
        txt = extract_text_from_pdf_bytes(raw)
        return txt, raw, True
    else:
        # Otros tipos: tratarlos como texto si posible
        try:
            txt = raw.decode("utf-8", errors="ignore")
        except Exception:
            txt = ""
        return txt, raw, False

def normalize(s: str) -> str:
    s = s.lower()
    s = re.sub(r"[^a-z0-9áéíóúüñ\s]", " ", s)
    return re.sub(r"\s+", " ", s).strip()

def simple_match_score(text: str, keywords: list[str]) -> tuple[int, list[str], list[str]]:
    """Cuenta coincidencias de keywords en el texto (normalizado)."""
    nt = normalize(text)
    found, missing = [], []
    for kw in keywords:
        k = normalize(kw)
        if not k:
            continue
        if re.search(rf"\b{k}\b", nt):
            found.append(kw)
        else:
            missing.append(kw)
    score = int(round(100 * (len(found) / max(1, len(keywords)))))
    return score, found, missing

def pros_cons_from_matches(found: list[str], missing: list[str], top_n: int = 4) -> tuple[str, str]:
    """Genera bullets simples de pros/cons basados en keywords encontradas/faltantes."""
    pros_items = [f"- Coincide con: {kw}" for kw in found[:top_n]] or ["- Coincidencias básicas con el perfil."]
    cons_items = [f"- Falta: {kw}" for kw in missing[:top_n]] or ["- Sin brechas críticas detectadas."]
    return "\n".join(pros_items), "\n".join(cons_items)

def analyze_cvs_locally(jd: str, keywords_csv: str, cv_files):
    """Analiza CVs sin IA. Llena st.session_state.candidates."""
    kws = [k.strip() for k in re.split(r"[;,/\n]+", keywords_csv) if k.strip()]
    if not kws:
        st.error("Por favor, define al menos una palabra clave.")
        return

    st.session_state.candidates = []
    progress = st.progress(0, "Analizando CVs...")

    for i, f in enumerate(cv_files):
        text, file_bytes, is_pdf = extract_text_from_file(f)
        score, found, missing = simple_match_score(text, kws)
        pros, cons = pros_cons_from_matches(found, missing)

        st.session_state.candidates.append({
            "Name": f.name,
            "Score": score,
            "Pros": pros,
            "Cons": cons,
            "file_bytes": file_bytes,
            "is_pdf": is_pdf
        })

        progress.progress((i + 1) / len(cv_files), f"Analizando: {f.name}")

    progress.empty()
    st.success(f"¡Análisis completo! {len(st.session_state.candidates)} CV(s) procesado(s).")
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

    # Botón de análisis (SIN IA)
    if st.button("Analizar CVs", type="primary", use_container_width=True):
        if not files:
            st.error("¡Por favor, sube al menos un CV!")
        else:
            analyze_cvs_locally(jd_text, kw_text, files)

    st.divider()

    # Limpiar lista
    if 'candidates' in st.session_state and st.session_state.candidates:
        if st.button("Limpiar Lista", use_container_width=True):
            st.session_state.candidates = []
            st.success("Resultados limpiados.")
            st.rerun()

# ===================
#  UI PRINCIPAL (claro)
# ===================
st.markdown(f"## <span style='color:{PRIMARY_GREEN}'>SelektIA – Evaluation Results</span>", unsafe_allow_html=True)

if not ('candidates' in st.session_state and st.session_state.candidates):
    st.info("Define el puesto, ajusta keywords y sube CVs. Luego presiona **Analizar CVs** en la barra lateral.", icon="ℹ️")

# Si hay candidatos, mostramos ranking + visor
if 'candidates' in st.session_state and st.session_state.candidates:
    df = pd.DataFrame(st.session_state.candidates)
    df_sorted = df.sort_values("Score", ascending=False)

    st.markdown(f"### <span style='color:{PRIMARY_GREEN}'>Ranking de Candidatos</span>", unsafe_allow_html=True)
    tab_ranking, tab_visor = st.tabs(["🏆 Ranking Top 5", "📄 Visor de CV"])

    with tab_ranking:
        st.write("Estos son los 5 candidatos con mayor puntuación según coincidencia de keywords.")

        top_5 = df_sorted.head(5).to_dict('records')
        for i, candidate in enumerate(top_5):
            rank = i + 1
            emoji = "🥇" if rank == 1 else "🥈" if rank == 2 else "🥉" if rank == 3 else f"#{rank}"
            with st.expander(f"{emoji} {candidate['Name']}  (Score: {candidate['Score']}/100)", expanded=(rank==1)):
                st.markdown("**✅ A favor (Pros):**")
                st.markdown(candidate['Pros'])
                st.markdown("**⚠️ A mejorar (Cons):**")
                st.markdown(candidate['Cons'])

        st.markdown("---")
        st.markdown("#### Comparativa General de Puntuaciones")
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

    with tab_visor:
        st.markdown(f"#### <span style='color:{PRIMARY_GREEN}'>Visor de CV</span>", unsafe_allow_html=True)
        st.caption("Elige un candidato de la lista para ver su archivo original.")
        all_names = df_sorted["Name"].tolist()

        selected_name = st.selectbox(
            "Selecciona un candidato:",
            all_names,
            key="pdf_candidate",
            label_visibility="collapsed",
        )

        if selected_name:
            candidate_data = next(c for c in st.session_state.candidates if c['Name'] == selected_name)
            file_bytes = candidate_data.get("file_bytes", b"")
            is_pdf = candidate_data.get("is_pdf", False)

            if is_pdf and file_bytes:
                data_b64 = base64.b64encode(file_bytes).decode("utf-8")
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
                    data=file_bytes,
                    file_name=selected_name,
                    mime="application/pdf"
                )
            else:
                st.info(f"'{selected_name}' es un archivo de texto. Mostrando contenido:")
                txt_content = file_bytes.decode("utf-8", errors="ignore")
                st.text_area("Contenido del TXT:", value=txt_content, height=600, disabled=True)
