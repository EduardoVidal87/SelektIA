# app.py
import io
import re
import base64
import uuid
from pathlib import Path

import streamlit as st
import pandas as pd
import plotly.express as px
from PyPDF2 import PdfReader
import streamlit.components.v1 as components

# ======================================================
# CONFIGURACIÓN BÁSICA
# ======================================================
st.set_page_config(
    page_title="SelektIA – Resultados de evaluación",
    page_icon="🧠",
    layout="wide",
)

# ======================================================
# PALETA / TEMA (sidebar + principal)
# ======================================================
PRIMARY_GREEN = "#00CD78"
SIDEBAR_BG = "#10172A"    # fondo columna izquierda
BOX_DARK = "#132840"      # fondo y borde de boxes del sidebar
BOX_DARK_HOV = "#193355"  # borde en hover/focus del sidebar
TEXT_LIGHT = "#FFFFFF"    # texto blanco
MAIN_BG = "#F7FBFF"       # fondo del cuerpo
BOX_LIGHT = "#F1F7FD"     # fondo claro de inputs principales
BOX_LIGHT_B = "#E3EDF6"   # borde claro de inputs principales
TITLE_DARK = "#142433"    # títulos
BAR_BASE = "#E9F3FF"      # barras base del gráfico
BAR_HIGHLIGHT = "#33FFAC" # barras score >= 60

# ======================================================
# CSS GLOBAL (incluye el DISEÑO PILL para los 4 boxes de la izquierda)
# ======================================================
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
  --bar-base: {BAR_BASE};
  --bar-highlight: {BAR_HIGHLIGHT};
}}

html, body, [data-testid="stAppViewContainer"] {{
  background: var(--main-bg) !important;
}}
.block-container {{
  background: transparent !important;
}}

/* ==================== SIDEBAR ==================== */
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

/* === 1) SELECT "Puesto" – estilo pill === */
[data-testid="stSidebar"] [data-testid="stSelectbox"] > div > div,
[data-testid="stSidebar"] [data-baseweb="select"] {{
  background: var(--box) !important;
  color: var(--text) !important;
  border: 1.5px solid var(--box) !important;
  border-radius: 18px !important;        /* pill */
  box-shadow: none !important;
  min-height: 42px;
}}
[data-testid="stSidebar"] [data-baseweb="select"] svg {{
  fill: var(--text) !important;
  opacity: .7;
}}
[data-testid="stSidebar"] [data-testid="stSelectbox"] > div > div:hover,
[data-testid="stSidebar"] [data-baseweb="select"]:focus-within {{
  border-color: var(--box-hover) !important;
}}

/* === 2) & 3) TEXTAREA – estilo pill === */
[data-testid="stSidebar"] [data-testid="stTextArea"] textarea {{
  background: var(--box) !important;
  color: var(--text) !important;
  border: 1.5px solid var(--box) !important;
  border-radius: 18px !important;        /* pill */
  box-shadow: none !important;
  resize: vertical;
}}
[data-testid="stSidebar"] [data-testid="stTextArea"] textarea:hover,
[data-testid="stSidebar"] [data-testid="stTextArea"] textarea:focus {{
  border-color: var(--box-hover) !important;
}}

/* === 4) DROPZONE – estilo pill === */
[data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] {{
  background: var(--box) !important;
  border: 1.5px solid var(--box) !important;
  border-radius: 18px !important;        /* pill */
  color: var(--text) !important;
  min-height: 64px;
  box-shadow: none !important;
}}
[data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] * {{
  color: var(--text) !important;
  opacity: .88;
}}
[data-testid="stSidebar"] [data-testid="stFileUploaderFile"] {{
  background: var(--box) !important;
  border: 1px solid var(--box) !important;
  color: var(--text) !important;
  border-radius: 12px !important;
}}

[data-testid="stSidebar"] .stButton > button {{
  background: var(--green) !important;
  color: #082017 !important;
  border: none !important;
  border-radius: 12px !important;
  font-weight: 600 !important;
  padding: .5rem 1rem !important;
}}
[data-testid="stSidebar"] .stButton > button:hover {{
  filter: brightness(.95);
}}

[data-testid="stSidebar"] input::placeholder,
[data-testid="stSidebar"] textarea::placeholder {{
  color: rgba(255,255,255,.75) !important;
}}

/* ==================== MAIN ==================== */
h1, h2, h3 {{
  color: var(--title-dark);
}}
h1 strong, h2 strong, h3 strong {{
  color: var(--green);
}}

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

/* Tabla */
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
"""
st.markdown(f"<style>{CSS}</style>", unsafe_allow_html=True)

# ======================================================
# UTILS: EXTRACCIÓN DE TEXTO
# ======================================================
def count_keyword_matches(text: str, keywords: list[str]) -> int:
    """Cuenta cuántas keywords aparecen al menos 1 vez en el texto."""
    if not text:
        return 0
    tokens = re.findall(r"[A-Za-zÁÉÍÓÚáéíóúñÑ0-9\-/+_.]+", text.lower())
    tokenset = set(tokens)
    matches = 0
    for kw in keywords:
        kw = kw.strip().lower()
        if not kw:
            continue
        if " " in kw:  # frase
            if kw in text.lower():
                matches += 1
        else:  # palabra única
            if kw in tokenset:
                matches += 1
    return matches

# ======================================================
# SIDEBAR
# ======================================================
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

    st.markdown("### Palabras clave del perfil *(ajústalas si es necesario)*")
    kw_text = st.text_area(
        "Ej.: HIS, SAP IS-H, BLS, ACLS, IAAS, educación al paciente, seguridad del paciente, protocolos",
        value="HIS, SAP IS-H, BLS, ACLS, IAAS, educación al paciente, seguridad del paciente, protocolos",
        height=110,
        key="kw",
        label_visibility="collapsed",
    )

    st.markdown("### Subir CVs (PDF o TXT)")
    files = st.file_uploader(
        "Arrastra aquí o **Browse files**",
        type=["pdf", "txt"],
        accept_multiple_files=True,
        label_visibility="collapsed",
    )

    st.divider()
    if st.button("Limpiar Lista", use_container_width=True):
        st.session_state.pop("candidates", None)
        st.experimental_rerun()

# ======================================================
# PROCESAMIENTO AUTOMÁTICO (sin botón)
# ======================================================
kw_list = [x.strip() for x in kw_text.split(",") if x.strip()]
candidates = []

if files:
    for f in files:
        raw = f.read()
        ext = Path(f.name).suffix.lower()

        # Extraer texto:
        text = ""
        try:
            if ext == ".pdf":
                reader = PdfReader(io.BytesIO(raw))
                text = "\n".join([(p.extract_text() or "") for p in reader.pages])
            else:
                text = raw.decode("utf-8", errors="ignore")
        except Exception as e:
            st.warning(f"No se pudo extraer texto de '{f.name}': {e}")

        matches = count_keyword_matches(text, kw_list)
        score = int(round(100 * (matches / max(1, len(kw_list)))))

        candidates.append({
            "Name": f.name,
            "Score": score,
            "Matches": f"{matches}/{len(kw_list)} keywords encontradas",
            "PDF_text chars": len(text),
            "_bytes": raw,
            "_is_pdf": (ext == ".pdf"),
        })

if candidates:
    st.session_state["candidates"] = candidates

# ======================================================
# CABECERA
# ======================================================
st.markdown("## <span style='color:#00CD78'>SelektIA – Resultados de evaluación</span>", unsafe_allow_html=True)
st.info("Define el puesto/JD, edita las palabras clave y sube CVs (PDF o TXT) para evaluar.", icon="ℹ️")

# ======================================================
# SI NO HAY RESULTADOS AÚN
# ======================================================
if "candidates" not in st.session_state or not st.session_state["candidates"]:
    st.warning("Aún no hay resultados. Sube CVs en la barra lateral para comenzar.", icon="🗂️")
    st.stop()

# ======================================================
# RANKING + GRÁFICO
# ======================================================
df = pd.DataFrame(st.session_state["candidates"]).sort_values("Score", ascending=False).reset_index(drop=True)

st.markdown("### Ranking de candidatos")
show_cols = df[["Name", "Score", "Matches", "PDF_text chars"]].rename(columns={
    "Name": "Nombre",
    "Score": "Score",
    "Matches": "Razones",
    "PDF_text chars": "PDF_text",
})
st.dataframe(show_cols, use_container_width=True, height=240)

# Gráfico
st.markdown("### Comparación de puntajes")
colors = [BAR_HIGHLIGHT if s >= 60 else BAR_BASE for s in df["Score"]]
fig = px.bar(df, x="Name", y="Score", labels={"Name": "Nombre", "Score": "Score"})
fig.update_traces(marker_color=colors)
fig.update_layout(
    plot_bgcolor="#FFFFFF",
    paper_bgcolor="rgba(0,0,0,0)",
    font=dict(color=TITLE_DARK),
    xaxis_title=None,
    yaxis_title="Score",
    showlegend=False
)
st.plotly_chart(fig, use_container_width=True)

# ======================================================
# VISOR DE CV (PDF/TXT) — usando BLOB en el navegador
# ======================================================
st.markdown("### Visor de CV (PDF/TXT)")
all_names = df["Name"].tolist()
selected_name = st.selectbox("Elige un candidato", all_names, index=0, label_visibility="collapsed")

candidate = df.loc[df["Name"] == selected_name].iloc[0]
viewer_height = 520  # más contenido y limpio

def render_pdf_blob(pdf_bytes: bytes, height: int = 520):
    """
    Renderiza un PDF seguro en un iframe usando un Blob (evita bloqueos de data:).
    """
    b64 = base64.b64encode(pdf_bytes).decode("utf-8")
    frame_id = f"pdf_iframe_{uuid.uuid4().hex}"
    html = f"""
    <div style="border:1px solid {BOX_LIGHT_B}; border-radius:12px; overflow:hidden; background:#fff;">
      <iframe id="{frame_id}" width="100%" height="{height}px" style="border:0;"></iframe>
    </div>
    <script>
      (function() {{
        try {{
          const b64 = "{b64}";
          const byteChars = atob(b64);
          const byteNumbers = new Array(byteChars.length);
          for (let i = 0; i < byteChars.length; i++) {{
            byteNumbers[i] = byteChars.charCodeAt(i);
          }}
          const byteArray = new Uint8Array(byteNumbers);
          const blob = new Blob([byteArray], {{type: "application/pdf"}});
          const url = URL.createObjectURL(blob);
          const iframe = document.getElementById("{frame_id}");
          if (iframe) {{
            iframe.src = url;
          }}
        }} catch (e) {{
          console.error("Fallo al preparar blob PDF:", e);
        }}
      }})();
    </script>
    """
    components.html(html, height=height + 10, scrolling=False)

if candidate["_is_pdf"] and candidate["_bytes"]:
    # Intento principal: blob en navegador
    render_pdf_blob(candidate["_bytes"], height=viewer_height)

    # Botón de descarga siempre como respaldo
    st.download_button(
        f"Descargar {selected_name}",
        data=candidate["_bytes"],
        file_name=selected_name,
        mime="application/pdf",
        use_container_width=False
    )
else:
    # TXT u otro caso
    if not candidate["_is_pdf"]:
        try:
            txt = candidate["_bytes"].decode("utf-8", errors="ignore")
        except Exception:
            txt = "(No se pudo leer el contenido de texto.)"
        st.text_area("Contenido del TXT (solo lectura):", txt, height=viewer_height)
        st.download_button(
            f"Descargar {selected_name}",
            data=candidate["_bytes"],
            file_name=selected_name,
            mime="text/plain",
            use_container_width=False
        )
    else:
        st.warning("No se detectaron bytes del PDF. Sube nuevamente el archivo.", icon="⚠️")
