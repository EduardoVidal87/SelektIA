# app.py
import io
import base64
from pathlib import Path

import streamlit as st
import pandas as pd
import plotly.express as px
from PyPDF2 import PdfReader

# =========================
# Variables de tema/colores
# =========================
PRIMARY_GREEN = "#00CD78"       # verde Wayki (acento)
SIDEBAR_BG     = "#10172A"       # sidebar oscuro
SIDEBAR_BOX    = "#132840"

# ---- Colores del panel derecho como la 2da imagen ----
MAIN_BG        = "#F6FBFF"       # fondo general claro
CARD_BG        = "#E9F3FF"       # headers celestes
CARD_BORDER    = "#D1E6FF"       # borde celeste
BOX_LIGHT      = "#F4FAFF"       # inputs claros
BOX_LIGHT_B    = "#CBE2FF"       # borde inputs claros
TITLE_DARK     = "#142433"       # títulos

# ==========
#   ESTILO
# ==========
CSS = f"""
:root {{
  --green: {PRIMARY_GREEN};
  --sidebar-bg: {SIDEBAR_BG};
  --sidebar-box: {SIDEBAR_BOX};
  --main-bg: {MAIN_BG};
  --card-bg: {CARD_BG};
  --card-border: {CARD_BORDER};
  --box-light: {BOX_LIGHT};
  --box-light-border: {BOX_LIGHT_B};
  --title-dark: {TITLE_DARK};
}}

/* Fondo global */
html, body, [data-testid="stAppViewContainer"] {{
  background: var(--main-bg) !important;
}}
.block-container {{
  background: transparent !important;
  padding-top: 1.2rem !important;
}}

/* Sidebar oscuro */
[data-testid="stSidebar"] {{
  background: var(--sidebar-bg) !important;
  color: #FFFFFF !important;
}}
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3,
[data-testid="stSidebar"] h4,
[data-testid="stSidebar"] h5 {{
  color: var(--green) !important;
}}
[data-testid="stSidebar"] [data-testid="stSelectbox"] > div > div,
[data-testid="stSidebar"] [data-testid="stTextArea"] textarea,
[data-testid="stSidebar"] [data-testid="stTextInput"] input {{
  background: var(--sidebar-box) !important;
  color: #FFFFFF !important;
  border: 1.5px solid var(--sidebar-box) !important;
  border-radius: 12px !important;
}}
[data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] {{
  background: var(--sidebar-box) !important;
  border: 1.5px dashed var(--sidebar-box) !important;
  border-radius: 12px !important;
}}
[data-testid="stSidebar"] [data-testid="stFileUploaderFile"] {{
  background: var(--sidebar-box) !important;
  border: 1px solid var(--sidebar-box) !important;
  color: #FFFFFF !important;
}}

/* Títulos del cuerpo */
h1, h2, h3 {{
  color: var(--title-dark);
  margin-bottom: .3rem;
}}
h1 strong, h2 strong {{
  color: var(--green);
}}

/* Aviso superior (celeste) */
.stAlert > div {{
  background: var(--card-bg) !important;
  border: 1px solid var(--card-border) !important;
  color: var(--title-dark) !important;
}}

/* Tablas (st.table) claras con header celeste */
.block-container table {{
  background: #FFFFFF !important;
  border: 1px solid var(--card-border) !important;
  border-radius: 8px !important;
}}
.block-container thead th {{
  background: var(--card-bg) !important;
  color: var(--title-dark) !important;
  border-bottom: 1px solid var(--card-border) !important;
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

/* Expander / tarjetas claras */
[data-testid="stExpander"] {{
  background: #FFFFFF !important;
  border: 1px solid var(--card-border) !important;
  border-radius: 12px !important;
}}
[data-testid="stExpander"] [data-testid="stExpanderHeader"] p {{
  color: var(--title-dark) !important;
}}

/* Botones (verde Wayki) */
.stButton > button {{
  background: var(--green) !important;
  color: #082017 !important;
  border: none !important;
  border-radius: 10px !important;
  font-weight: 600 !important;
}}
"""

st.set_page_config(page_title="SelektIA", page_icon="🧠", layout="wide")
st.markdown(f"<style>{CSS}</style>", unsafe_allow_html=True)

# =================================
#  FUNCIONES DE PROCESAMIENTO
# =================================
def extract_text_from_file(uploaded_file) -> tuple[str, bytes, bool]:
    """Devuelve (texto, bytes, es_pdf)"""
    raw = uploaded_file.read()
    suffix = Path(uploaded_file.name).suffix.lower()
    if suffix == ".pdf":
        try:
            reader = PdfReader(io.BytesIO(raw))
            txt = ""
            for page in reader.pages:
                txt += page.extract_text() or ""
            return txt, raw, True
        except Exception:
            return "", raw, True
    else:  # .txt
        try:
            txt = raw.decode("utf-8", errors="ignore")
        except Exception:
            txt = ""
        return txt, raw, False


def analyze_candidates(jd_text: str, kw_text: str, files):
    """Scoring simple por coincidencia de keywords."""
    keywords = [k.strip().lower() for k in kw_text.split(",") if k.strip()]
    results = []
    for f in files:
        f.seek(0)
        text, file_bytes, is_pdf = extract_text_from_file(f)
        text_l = text.lower()
        found = [k for k in keywords if k in text_l] if keywords else []
        score = round(100 * (len(found) / len(keywords))) if keywords else 0
        reasons = (
            f"{len(found)}/{len(keywords)} keywords encontradas — "
            + ("Coincidencias: " + ", ".join(found[:10]) if found else "Sin coincidencias")
        )
        results.append(
            {
                "Name": f.name,
                "Score": score,
                "Reasons": reasons,
                "PDF_text": len(text),
                "_bytes": file_bytes,
                "_is_pdf": is_pdf,
                "_text": text,
            }
        )
    return results


# ================
#  SIDEBAR (oscuro)
# ================
with st.sidebar:
    # Si moviste el logo dentro de /assets, apunta a "assets/logo-wayki.png"
    st.image("logo-wayki.png", use_column_width=True)
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
        "Arrastra y suelta aquí",
        type=["pdf", "txt"],
        accept_multiple_files=True,
        label_visibility="collapsed",
    )

    if st.button("Limpiar Lista", use_container_width=True):
        st.session_state.pop("candidates", None)
        st.success("Resultados limpiados.")
        st.rerun()


# ===================
#  UI PRINCIPAL (claro)
# ===================
st.markdown(f"## <span style='color:{PRIMARY_GREEN}'>SelektIA – Resultados de evaluación</span>", unsafe_allow_html=True)
st.info("Define el puesto/JD, edita las palabras clave y sube CVs (PDF o TXT) para evaluar.")

# Analiza automáticamente cuando hay cambios
if files and ("_last_files_snapshot" not in st.session_state
              or st.session_state.get("_last_kw") != kw_text
              or st.session_state.get("_last_jd") != jd_text
              or st.session_state.get("_last_files_snapshot") != [f.name for f in files]):
    st.session_state["_last_files_snapshot"] = [f.name for f in files]
    st.session_state["_last_kw"] = kw_text
    st.session_state["_last_jd"] = jd_text
    st.session_state["candidates"] = analyze_candidates(jd_text, kw_text, files)

if "candidates" not in st.session_state or not st.session_state["candidates"]:
    st.warning("Sube al menos un CV (PDF o TXT) para ver resultados.", icon="⚠️")
    st.stop()

# Tabla (usamos st.table para que el CSS funcione)
df = pd.DataFrame(st.session_state["candidates"])
df_sorted = df.sort_values("Score", ascending=False)

st.markdown(f"### <span style='color:{TITLE_DARK}'>Ranking de candidatos</span>", unsafe_allow_html=True)
show = df_sorted[["Name", "Score", "Reasons", "PDF_text"]].rename(
    columns={"Name": "Nombre", "Score": "Score", "Reasons": "Razones", "PDF_text": "PDF_text"}
)
st.table(show)  # <- clave: st.table en vez de st.dataframe

# Gráfico (paleta celeste)
st.markdown(f"### <span style='color:{TITLE_DARK}'>Comparación de puntajes</span>", unsafe_allow_html=True)
fig = px.bar(
    df_sorted,
    x="Name",
    y="Score",
    title="",
)
fig.update_traces(marker_color="#2A8BF2")  # celeste Wayki-like
fig.update_layout(
    plot_bgcolor="#FFFFFF",
    paper_bgcolor="rgba(0,0,0,0)",
    font=dict(color=TITLE_DARK),
    xaxis_title=None,
    yaxis_title="Score",
)
st.plotly_chart(fig, use_container_width=True)

# Visor de CV
st.markdown(f"### <span style='color:{TITLE_DARK}'>Visor de CV (PDF/TXT)</span>", unsafe_allow_html=True)
all_names = df_sorted["Name"].tolist()
selected_name = st.selectbox("Elige un candidato", all_names, index=0, key="pdf_candidate", label_visibility="collapsed")

candidate = df.loc[df["Name"] == selected_name].iloc[0]
if candidate["_is_pdf"] and candidate["_bytes"]:
    b64 = base64.b64encode(candidate["_bytes"]).decode("utf-8")
    st.markdown(
        f"""
        <div style="border:1px solid {CARD_BORDER}; border-radius:12px; overflow:hidden; background:#fff;">
          <iframe src="data:application/pdf;base64,{b64}" style="width:100%; height:760px; border:0;" title="PDF Viewer"></iframe>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.download_button(
        f"Descargar {selected_name}",
        data=candidate["_bytes"],
        file_name=selected_name,
        mime="application/pdf",
    )
else:
    st.info(f"**{selected_name}** es un archivo de texto. Contenido:", icon="📝")
    st.text_area("Contenido del TXT:", value=candidate["_text"], height=600, disabled=True)
