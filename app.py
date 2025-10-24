# app.py
import io
import base64
import re
from pathlib import Path
from uuid import uuid4

import streamlit as st
import pandas as pd
import plotly.express as px
from PyPDF2 import PdfReader
import streamlit.components.v1 as components

# =========================
# Variables de tema/colores
# =========================
PRIMARY_GREEN = "#00CD78"
SIDEBAR_BG = "#10172A"          # fondo columna izquierda
BOX_DARK = "#132840"            # fondo y borde de boxes del sidebar
BOX_DARK_HOV = "#193355"        # borde en hover/focus del sidebar
TEXT_LIGHT = "#FFFFFF"          # texto blanco
MAIN_BG = "#F7FBFF"             # fondo del cuerpo (claro)
BOX_LIGHT = "#F1F7FD"           # fondo claro de inputs principales
BOX_LIGHT_B = "#E3EDF6"         # borde claro de inputs principales
TITLE_DARK = "#142433"          # texto títulos principales

# Colores del gráfico
BAR_DEFAULT = "#E9F3FF"         # barras por defecto
BAR_GOOD = "#33FFAC"            # barras con score >= 60

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
/* Contenedor */
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
[data-testid="stSidebar"] h6 {{
  color: var(--green) !important;
}}
[data-testid="stSidebar"] label, 
[data-testid="stSidebar"] p, 
[data-testid="stSidebar"] span {{
  color: var(--text) !important;
}}

/* ===== DISEÑO DE LOS 4 BOXES IZQUIERDA ===== */
/* Select (Puesto) */
[data-testid="stSidebar"] [data-testid="stSelectbox"] > div > div,
[data-testid="stSidebar"] [data-baseweb="select"] {{
  background: var(--box) !important;
  color: var(--text) !important;
  border: 1.5px solid var(--box) !important;
  border-radius: 14px !important;
  box-shadow: none !important;
}}
/* Textareas */
[data-testid="stSidebar"] [data-testid="stTextArea"] textarea {{
  background: var(--box) !important;
  color: var(--text) !important;
  border: 1.5px solid var(--box) !important;
  border-radius: 14px !important;
  box-shadow: none !important;
}}

/* Hover/Focus para los 4 boxes */
[data-testid="stSidebar"] [data-testid="stTextArea"] textarea:hover,
[data-testid="stSidebar"] [data-testid="stTextArea"] textarea:focus,
[data-testid="stSidebar"] [data-testid="stSelectbox"] > div > div:hover,
[data-testid="stSidebar"] [data-testid="stSelectbox"] > div > div:focus {{
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
.stButton > button:hover {{
  filter: brightness(0.95);
}}

/* Títulos cuerpo */
h1, h2, h3 {{
  color: var(--title-dark);
}}
h1 strong, h2 strong, h3 strong {{
  color: var(--green);
}}

/* Controles área principal (claros) */
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

/* Selector del visor de PDF/TXT (claro) */
#pdf_candidate {{
  background: var(--box-light) !important;
  border: 1.5px solid var(--box-light-border) !important;
  color: var(--title-dark) !important;
  border-radius: 10px !important;
}}
"""

st.set_page_config(page_title="SelektIA", page_icon="🧠", layout="wide")
st.markdown(f"<style>{CSS}</style>", unsafe_allow_html=True)

# =========================
# Funciones utilitarias
# =========================
def normalize_text(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip().lower()

def extract_text_from_file(uploaded_file) -> str:
    """
    Extrae texto de PDF (PyPDF2) o de TXT.
    """
    try:
        suffix = Path(uploaded_file.name).suffix.lower()
        if suffix == ".pdf":
            data = uploaded_file.read()
            uploaded_file.seek(0)
            pdf_reader = PdfReader(io.BytesIO(data))
            text = ""
            for page in pdf_reader.pages:
                # Puede devolver None si no logra extraer esa página
                text += page.extract_text() or ""
            return text
        else:
            return uploaded_file.read().decode("utf-8", errors="ignore")
    except Exception as e:
        st.error(f"Error al leer '{uploaded_file.name}': {e}")
        return ""

def score_cv(jd_text: str, kw_text: str, cv_text: str):
    """
    Scoring simple por keywords (coincidencias, normalizado a 100).
    """
    jd_n = normalize_text(jd_text)
    cv_n = normalize_text(cv_text)
    # Lista de keywords (limpieza básica)
    kws = [k.strip().lower() for k in re.split(r"[,\n;]", kw_text) if k.strip()]
    if not kws:
        return 0, 0, "Sin palabras clave"

    matches = sum(1 for k in kws if k in cv_n or k in jd_n)
    score = int(round((matches / max(len(kws), 1)) * 100))
    razones = f"{matches}/{len(kws)} keywords encontradas — Coincidencias: " + ", ".join([k for k in kws if k in cv_n or k in jd_n][:8])
    return score, matches, razones

def pdf_viewer_pdfjs(data_b64: str, height: int = 520, scale: float = 1.1):
    """
    Muestra un PDF con pdf.js (desde base64) para evitar fallos de iframes con data-uri.
    Renderiza todas las páginas dentro de un contenedor con scroll.
    """
    html = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8" />
<style>
  body {{ margin:0; background:#fff; }}
  #viewer {{ height:{height}px; overflow:auto; background:#fff; }}
  .pageCanvas {{ display:block; margin: 0 auto 12px auto; box-shadow: 0 2px 8px rgba(0,0,0,.08); }}
</style>
<script src="https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js"></script>
<script>
  const pdfData = atob("{data_b64}");
  const pdfjsLib = window['pdfjs-dist/build/pdf'];
  pdfjsLib.GlobalWorkerOptions.workerSrc = "https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js";

  const uint8Array = new Uint8Array(pdfData.length);
  for (let i = 0; i < pdfData.length; i++) {{
      uint8Array[i] = pdfData.charCodeAt(i);
  }}

  document.addEventListener("DOMContentLoaded", async () => {{
      try {{
          const loadingTask = pdfjsLib.getDocument({{data: uint8Array}});
          const pdf = await loadingTask.promise;
          const viewer = document.getElementById("viewer");

          for (let pageNum = 1; pageNum <= pdf.numPages; pageNum++) {{
              const page = await pdf.getPage(pageNum);
              const viewport = page.getViewport({{ scale: {scale} }});
              const canvas = document.createElement("canvas");
              canvas.className = "pageCanvas";
              const context = canvas.getContext("2d");
              canvas.height = viewport.height;
              canvas.width = viewport.width;
              viewer.appendChild(canvas);

              await page.render({{ canvasContext: context, viewport: viewport }}).promise;
          }}
      }} catch (err) {{
          const el = document.getElementById("viewer");
          el.innerHTML = "<div style='padding:16px;color:#b00;font-family:sans-serif'>No se pudo renderizar el PDF.</div>";
          console.error(err);
      }}
  }});
</script>
</head>
<body>
  <div id="viewer"></div>
</body>
</html>
"""
    components.html(html, height=height + 16, scrolling=False)

# Estado inicial
if "candidates" not in st.session_state:
    st.session_state.candidates = []
if "uploader_key" not in st.session_state:
    st.session_state.uploader_key = str(uuid4())

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
        "HIS, SAP IS-H, BLS, ACLS, IAAS, educación al paciente, seguridad del paciente, protocolos…",
        value="HIS, SAP IS-H, BLS, ACLS, IAAS, educación al paciente, seguridad del paciente, protocolos",
        height=110,
        key="kw",
        label_visibility="collapsed",
    )

    st.markdown("### Subir CVs (PDF o TXT)")
    files = st.file_uploader(
        "Arrastra o selecciona archivos",
        type=["pdf", "txt"],
        accept_multiple_files=True,
        key=st.session_state.uploader_key,
        label_visibility="collapsed",
    )

    # Botón de limpiar lista
    if st.button("Limpiar Lista", use_container_width=True):
        st.session_state.candidates = []
        # Cambiar clave del uploader para limpiarlo
        st.session_state.uploader_key = str(uuid4())
        st.success("Resultados y lista de archivos limpiados.")
        st.rerun()

# ===================
#  UI PRINCIPAL (claro)
# ===================
st.markdown(f"## <span style='color:{PRIMARY_GREEN}'>SelektIA – Resultados de evaluación</span>", unsafe_allow_html=True)

# Análisis automático al subir archivos
if files:
    candidates = []
    for f in files:
        raw_bytes = f.read()
        f.seek(0)
        text = extract_text_from_file(f)
        score, matches, razones = score_cv(jd_text, kw_text, text)

        candidates.append(
            {
                "Name": f.name,
                "Score": int(score),
                "Matches": int(matches),
                "Reasons": razones,
                "_bytes": raw_bytes,
                "_is_pdf": Path(f.name).suffix.lower() == ".pdf",
                "chars": len(text),
            }
        )
    st.session_state.candidates = candidates

# Mostrar ranking/tabla y gráfico
if st.session_state.candidates:
    df = pd.DataFrame(st.session_state.candidates)
    df_sorted = df.sort_values("Score", ascending=False, kind="stable")

    # ===== Tabla =====
    st.markdown("#### Ranking de candidatos")
    show = df_sorted[["Name", "Score", "Reasons", "chars"]].rename(
        columns={"Name": "Nombre", "Score": "Score", "Reasons": "Razones", "chars": "PDF_text"}
    )
    st.dataframe(show, use_container_width=True, hide_index=True)

    # ===== Gráfico =====
    st.markdown("#### Comparación de puntajes")
    bar_colors = [BAR_GOOD if s >= 60 else BAR_DEFAULT for s in df_sorted["Score"]]
    fig = px.bar(
        df_sorted,
        x="Name",
        y="Score",
        title=None,
    )
    fig.update_traces(marker_color=bar_colors)
    fig.update_layout(
        plot_bgcolor="#FFFFFF",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color=TITLE_DARK),
        xaxis_title=None,
        yaxis_title="Score",
        margin=dict(l=20, r=20, t=30, b=10),
        height=300,
    )
    st.plotly_chart(fig, use_container_width=True)

    # ===== Visor de CV =====
    st.markdown("#### Visor de CV (PDF/TXT)  <a id='visor'></a>", unsafe_allow_html=True)

    all_names = df_sorted["Name"].tolist()
    selected_name = st.selectbox(
        "Elige un candidato",
        all_names,
        index=0,
        key="pdf_candidate",
        label_visibility="collapsed",
    )

    candidate = df.loc[df["Name"] == selected_name].iloc[0]
    if candidate["_is_pdf"] and candidate["_bytes"]:
        b64 = base64.b64encode(candidate["_bytes"]).decode("utf-8")
        # Visor pdf.js (más estable que data:iframe)
        pdf_viewer_pdfjs(b64, height=520, scale=1.1)
        st.download_button(
            f"Descargar {selected_name}",
            data=candidate["_bytes"],
            file_name=selected_name,
            mime="application/pdf",
        )
    else:
        # TXT
        st.info(f"'{selected_name}' es un archivo de texto. Mostrando contenido:")
        try:
            txt_content = candidate["_bytes"].decode("utf-8", errors="ignore")
        except Exception:
            txt_content = ""
        st.text_area("Contenido (solo lectura):", value=txt_content, height=420, disabled=True)
        st.download_button(
            f"Descargar {selected_name}",
            data=candidate["_bytes"],
            file_name=selected_name,
            mime="text/plain",
        )
else:
    st.info("Carga CVs (PDF o TXT) desde la barra lateral para ver el ranking, el gráfico y el visor.", icon="ℹ️")
