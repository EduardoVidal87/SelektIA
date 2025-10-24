# app.py
import io
import base64
import re
import unicodedata
from pathlib import Path

import streamlit as st
import pandas as pd
import plotly.express as px
from PyPDF2 import PdfReader


# =========================
# Configuración inicial
# =========================
st.set_page_config(
    page_title="SelektIA",
    page_icon="🧠",
    layout="wide",
)

# =========================
# Variables de tema/colores
# =========================
PRIMARY_GREEN = "#00CD78"
SIDEBAR_BG    = "#10172A"    # fondo columna izquierda
BOX_DARK      = "#132840"    # fondo y borde de boxes del sidebar
BOX_DARK_HOV  = "#193355"    # borde en hover/focus del sidebar
TEXT_LIGHT    = "#FFFFFF"    # texto blanco
MAIN_BG       = "#F7FBFF"    # fondo del cuerpo (claro)
BOX_LIGHT     = "#F1F7FD"    # fondo claro de inputs principales (panel derecho)
BOX_LIGHT_B   = "#E3EDF6"    # borde claro de inputs principales
TITLE_DARK    = "#142433"    # texto títulos principales

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
/* Elimina fondo blanco interno */
.block-container {{
  background: transparent !important;
}}

/* Sidebar */
[data-testid="stSidebar"] {{
  background: var(--sidebar-bg) !important;
  color: var(--text) !important;
}}
/* Títulos del sidebar en verde */
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3,
[data-testid="stSidebar"] h4,
[data-testid="stSidebar"] h5,
[data-testid="stSidebar"] h6,
[data-testid="stSidebar"] .stMarkdown p strong {{
  color: var(--green) !important;
}}
/* Texto del sidebar */
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
/* Chips de archivos subidos */
[data-testid="stSidebar"] [data-testid="stFileUploaderFile"] {{
  background: var(--box) !important;
  border: 1px solid var(--box) !important;
  color: var(--text) !important;
}}

/* Botones verdes */
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
h1, h2, h3 {{ color: var(--title-dark) !important; }}
h1 strong, h2 strong, h3 strong {{ color: var(--green) !important; }}

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

/* Selector del visor de PDF */
#pdf_candidate, #pdf_candidate_alt {{
  background: var(--box-light) !important;
  border: 1.5px solid var(--box-light-border) !important;
  color: var(--title-dark) !important;
  border-radius: 10px !important;
}}
"""
st.markdown(f"<style>{CSS}</style>", unsafe_allow_html=True)

# =========================
# Utilidades (texto y score)
# =========================
def _normalize_text(s: str) -> str:
    if not s:
        return ""
    s = s.lower()
    s = "".join(
        c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn"
    )
    return s

def extract_text_from_bytes(name: str, data: bytes) -> str:
    """Extrae texto de PDF (PyPDF2) o TXT a partir de bytes."""
    try:
        ext = Path(name).suffix.lower()
        if ext == ".pdf":
            reader = PdfReader(io.BytesIO(data))
            text = ""
            for page in reader.pages:
                text += page.extract_text() or ""
            return text
        else:
            return data.decode("utf-8", errors="ignore")
    except Exception as e:
        st.error(f"Error al leer '{name}': {e}")
        return ""

def score_by_keywords(jd_text: str, kw_text: str, cv_text: str) -> tuple[int, list, list, int]:
    """
    Devuelve (score 0-100, pros(list), cons(list), coincidencias).
    Score simple por coincidencia de palabras clave dentro del CV.
    """
    jd_norm = _normalize_text(jd_text)
    kw_norm = _normalize_text(kw_text)
    cv_norm = _normalize_text(cv_text)

    # KeyWords base: separa por coma y por espacios/punctuation
    kw_items = [k.strip() for k in re.split(r"[,\n;]", kw_norm) if k.strip()]
    # Evita duplicados y vacíos
    kw_items = list({k for k in kw_items if k})

    if not kw_items:
        return 0, ["No se definieron palabras clave."], ["Agrega keywords para evaluar."], 0

    total = len(kw_items)
    hits = [k for k in kw_items if k and k in cv_norm]
    n_hits = len(hits)

    score = int(min(100, round((n_hits / total) * 100))) if total else 0

    pros = [
        f"Coincidencias: {n_hits}/{total} keywords.",
        "Alineación general con el perfil (según keywords).",
    ]
    if hits:
        pros.append("Palabras clave encontradas: " + ", ".join(hits[:8]) + ("..." if len(hits) > 8 else ""))

    cons = []
    missing = [k for k in kw_items if k not in hits]
    if missing:
        cons.append("Palabras clave faltantes: " + ", ".join(missing[:8]) + ("..." if len(missing) > 8 else ""))
    if score < 50:
        cons.append("Baja coincidencia global con el perfil definido.")

    return score, pros, cons, n_hits


# =========================
# Lógica de análisis (sin IA)
# =========================
def analyze_cvs(jd, keywords, cv_files):
    st.session_state.candidates = []
    progress = st.progress(0, "Analizando CVs...")

    files = list(cv_files)  # aseguramos lista para len()
    for i, file in enumerate(files):
        file_bytes = file.getvalue()  # bytes inmutables del archivo
        cv_text = extract_text_from_bytes(file.name, file_bytes)

        if not cv_text.strip():
            st.warning(f"No se pudo extraer texto de '{file.name}'. Omitiendo.")
            progress.progress((i + 1) / len(files), f"Omitido: {file.name}")
            continue

        score, pros, cons, matches = score_by_keywords(jd, keywords, cv_text)

        st.session_state.candidates.append({
            "Name": file.name,
            "Score": int(score),
            "Pros": "• " + "\n• ".join(pros),
            "Cons": "• " + "\n• ".join(cons),
            "Matches": matches,
            "file_bytes": file_bytes,
            "is_pdf": Path(file.name).suffix.lower() == ".pdf"
        })
        progress.progress((i + 1) / len(files), f"Procesado: {file.name}")

    progress.empty()
    if st.session_state.candidates:
        st.success(f"¡Listo! {len(st.session_state.candidates)} CV(s) analizados.")
    else:
        st.warning("No se pudo analizar ningún CV.")


# ================
#  SIDEBAR (oscuro)
# ================
with st.sidebar:
    st.image("assets/logo-wayki.png", use_container_width=True)  # ← sin deprecación
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
        "HIS, SAP IS-H, BLS, ACLS, IAAS, educación al paciente, seguridad...",
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

    if st.button("Analizar CVs", type="primary", use_container_width=True):
        if not files:
            st.error("¡Por favor, sube al menos un CV!")
        else:
            analyze_cvs(jd_text, kw_text, files)

    st.divider()
    if st.session_state.get("candidates"):
        if st.button("Limpiar Lista", use_container_width=True):
            st.session_state.candidates = []
            st.rerun()


# ===================
#  UI PRINCIPAL (claro)
# ===================
st.markdown(f"## <span style='color:{PRIMARY_GREEN}'>SelektIA – Evaluation Results</span>", unsafe_allow_html=True)

if not st.session_state.get("candidates"):
    st.info("Define el puesto, ajusta keywords y sube CVs. Luego presiona **Analizar CVs** en la barra lateral.", icon="ℹ️")
else:
    df = pd.DataFrame(st.session_state.candidates)
    df_sorted = df.sort_values("Score", ascending=False)

    tabs = st.tabs(["🏆 Ranking de Candidatos", "📄 Visor de CV"])
    with tabs[0]:
        st.markdown(f"##### Ranking de Candidatos")
        show = df_sorted[["Name", "Score", "Matches"]].rename(
            columns={"Name": "Candidato", "Score": "Score", "Matches": "Keywords"}
        )
        st.dataframe(show, use_container_width=True, hide_index=True)

        st.markdown("#### Comparativa General")
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

        st.markdown("#### Detalle (pros/cons)")
        for _, r in df_sorted.iterrows():
            with st.expander(f"{r['Name']}  (Score: {r['Score']}/100)"):
                st.markdown("**✅ A favor (Pros):**")
                st.markdown(r["Pros"])
                st.markdown("**⚠️ A mejorar (Cons):**")
                st.markdown(r["Cons"])

    with tabs[1]:
        st.markdown(f"#### <span style='color:{PRIMARY_GREEN}'>Visor de CV</span>", unsafe_allow_html=True)
        all_names = df_sorted["Name"].tolist()
        col1, col2 = st.columns([1,1])

        with col1:
            selected_name = st.selectbox(
                "Selecciona un candidato:",
                all_names,
                key="pdf_candidate",
                label_visibility="collapsed",
            )

        with col2:
            st.selectbox(
                "Elegir candidato (opción alternativa)",
                all_names,
                index=all_names.index(selected_name) if selected_name in all_names else 0,
                key="pdf_candidate_alt",
                label_visibility="visible",
            )

        # Visor PDF (con respaldo)
        if selected_name:
            cdata = next(c for c in st.session_state.candidates if c["Name"] == selected_name)
            if cdata["is_pdf"] and cdata["file_bytes"]:
                data_b64 = base64.b64encode(cdata["file_bytes"]).decode("utf-8")

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

                # Respaldo si el navegador no renderiza el iframe base64
                st.components.v1.iframe(src=f"data:application/pdf;base64,{data_b64}",
                                        width=None, height=750, scrolling=True)

                st.download_button(
                    f"Descargar {selected_name}",
                    data=cdata["file_bytes"],
                    file_name=selected_name,
                    mime="application/pdf"
                )
            else:
                st.info(f"'{selected_name}' es un archivo de texto. Mostrando contenido:")
                txt_content = cdata["file_bytes"].decode("utf-8", errors="ignore")
                st.text_area("Contenido del TXT:", value=txt_content, height=600, disabled=True)
