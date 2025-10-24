# -*- coding: utf-8 -*-
import io
import re
import base64
import unicodedata
from typing import List, Tuple, Dict

import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# ==== Intenta usar PyMuPDF; si no, cae a pdfminer.six ====
try:
    import fitz  # PyMuPDF
    HAS_FITZ = True
except Exception:
    HAS_FITZ = False

try:
    from pdfminer.high_level import extract_text as pdfminer_extract_text
    HAS_PDFMINER = True
except Exception:
    HAS_PDFMINER = False

# ==== Intenta el visor de PDFs ====
try:
    from streamlit_pdf_viewer import pdf_viewer  # pip install streamlit-pdf-viewer
    HAS_PDF_VIEWER = True
except Exception:
    HAS_PDF_VIEWER = False


# ==========================================
#                 CONSTANTES
# ==========================================
PRIMARY     = "#00CD78"    # acentos y títulos
SIDEBAR_BG  = "#10172A"    # panel izquierdo
BOX_BG      = "#132840"    # fondo de cajas en sidebar
BOX_BORDER  = "#132840"    # borde de cajas en sidebar
MAIN_BG     = "#F6F8FB"    # fondo sutil claro
CARD_BG     = "#E9F1FF"    # cards/info
TEXT_MAIN   = "#0B1220"    # texto principal
MUTED       = "#667085"
SUCCESS     = PRIMARY
WARNING     = "#F4A100"
ERROR       = "#FF4D4F"


# ==========================================
#                UTILIDADES
# ==========================================
def remove_accents(s: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn"
    )


def normalize_text(s: str) -> str:
    s = s.lower()
    s = remove_accents(s)
    s = re.sub(r"[^a-z0-9\s\-\/\+\.]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def extract_text_from_bytes(file_bytes: bytes, file_name: str) -> str:
    """Extrae texto de un PDF o TXT a partir de bytes."""
    name_lower = file_name.lower()
    if name_lower.endswith(".txt"):
        for enc in ("utf-8", "latin-1"):
            try:
                return file_bytes.decode(enc, errors="ignore")
            except Exception:
                pass
        return ""

    if name_lower.endswith(".pdf"):
        # 1) PyMuPDF
        if HAS_FITZ:
            text_parts = []
            try:
                with fitz.open(stream=file_bytes, filetype="pdf") as doc:
                    for page in doc:
                        text_parts.append(page.get_text() or "")
                return "\n".join(text_parts)
            except Exception:
                pass
        # 2) pdfminer.six
        if HAS_PDFMINER:
            try:
                data = io.BytesIO(file_bytes)
                return pdfminer_extract_text(data) or ""
            except Exception:
                pass
        return ""
    return ""


def tokenize(text: str) -> List[str]:
    text = normalize_text(text)
    return text.split()


def suggest_keywords_from_jd(jd_text: str) -> List[str]:
    """Sugiere keywords desde el JD."""
    base_health = [
        "his", "sap is-h", "bls", "acls",
        "iaas", "indicadores",
        "educacion al paciente", "seguridad del paciente",
        "protocolos", "bombas de infusion", "curacion avanzada",
        "excel basico", "registro clinico"
    ]
    stop = set("""
        de la las los y e a o del en para con por un una unas unos al el lo le les se que
        por sobre entre hacia contra sin tras como donde cuando mientras durante
        los-las sus su sus al del
    """.split())

    toks = tokenize(jd_text)
    freq: Dict[str, int] = {}
    for t in toks:
        if len(t) < 3:
            continue
        if t in stop:
            continue
        freq[t] = freq.get(t, 0) + 1

    top = [w for w, _ in sorted(freq.items(), key=lambda x: x[1], reverse=True)[:12]]
    merged = []
    for w in base_health + top:
        if w not in merged:
            merged.append(w)
    return merged[:20]


def score_document(doc_text: str, keywords: List[str]) -> Tuple[int, str, int]:
    """Calcula score simple por coincidencias de keywords."""
    normalized = normalize_text(doc_text)
    hits = []
    total = len(keywords)
    if total == 0:
        return (0, "0/0 keywords; sin definición", len(normalized))

    for k in keywords:
        k_norm = normalize_text(k)
        if not k_norm:
            continue
        if k_norm in normalized:
            hits.append(k)

    reasons = f"{len(hits)}/{total} keywords encontradas — Coincidencias: " + ", ".join(hits) if hits else f"0/{total} keywords encontradas"
    score_simple = len(hits)
    return (score_simple, reasons, len(normalized))


def get_download_button(data: bytes, file_name: str, label="Descargar archivo"):
    b64 = base64.b64encode(data).decode()
    href = f'<a download="{file_name}" href="data:application/octet-stream;base64,{b64}">{label}</a>'
    return href


# ==========================================
#                 ESTILOS
# ==========================================
def inject_css():
    st.markdown(f"""
    <style>
    /* Fondo global */
    .stApp {{
        background: {MAIN_BG};
        color: {TEXT_MAIN};
    }}

    /* Títulos */
    h1, h2, h3, .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {{
        color: {PRIMARY} !important;
        font-weight: 800 !important;
        letter-spacing: .2px;
    }}

    /* Banda informativa */
    .pill {{
        background: {CARD_BG};
        border: 1px solid #D8E6FF;
        color: #0B2447;
        padding: 10px 14px;
        border-radius: 10px;
        margin: 4px 0 14px 0;
    }}

    /* Selects e inputs del MAIN (claro) */
    .stSelectbox > div > div,
    .stMultiSelect > div > div,
    .stTextInput > div > div > input,
    textarea {{
        background-color: #F3F6FA !important;
        border: 1px solid #D0D8E0 !important;
        color: {TEXT_MAIN} !important;
        border-radius: 8px !important;
    }}
    .stSelectbox > div > div:focus,
    .stMultiSelect > div > div:focus,
    .stTextInput > div > div > input:focus,
    textarea:focus {{
        outline: none !important;
        border: 1px solid #C5CED6 !important;
        box-shadow: 0 0 0 2px {PRIMARY}33 !important;
    }}

    /* ==== SIDEBAR ==== */
    [data-testid="stSidebar"] {{
        background: {SIDEBAR_BG};
    }}

    /* Titulares del sidebar */
    [data-testid="stSidebar"] h1, 
    [data-testid="stSidebar"] h2, 
    [data-testid="stSidebar"] h3 {{
        color: {PRIMARY} !important;
        font-weight: 800 !important;
    }}

    /* Labels del sidebar */
    [data-testid="stSidebar"] [data-testid="stWidgetLabel"] p {{
        color: {PRIMARY} !important;
        font-weight: 700;
    }}

    /* ====== FORZAR TODOS LOS INPUTS/SELECTS EN EL SIDEBAR ====== */
    [data-testid="stSidebar"] input,
    [data-testid="stSidebar"] textarea,
    [data-testid="stSidebar"] select,
    [data-testid="stSidebar"] .stTextInput > div > div > input,
    [data-testid="stSidebar"] .stTextArea textarea,
    [data-testid="stSidebar"] .stNumberInput input,
    [data-testid="stSidebar"] .stSelectbox > div > div,
    [data-testid="stSidebar"] .stMultiSelect > div > div,
    [data-testid="stSidebar"] div[data-baseweb="select"] > div {{
        background-color: {BOX_BG} !important;
        border: 1px solid {BOX_BORDER} !important;
        color: #FFFFFF !important;
        border-radius: 8px !important;
    }}

    [data-testid="stSidebar"] ::placeholder {{
        color: #C9D1D9 !important;
        opacity: .9 !important;
    }}

    [data-testid="stSidebar"] input:focus,
    [data-testid="stSidebar"] textarea:focus,
    [data-testid="stSidebar"] .stSelectbox > div > div:focus,
    [data-testid="stSidebar"] .stMultiSelect > div > div:focus,
    [data-testid="stSidebar"] div[data-baseweb="select"] > div:focus {{
        outline: none !important;
        border: 1px solid {BOX_BORDER} !important;
        box-shadow: 0 0 0 2px {PRIMARY}33 !important;
    }}

    /* ====== FILE UPLOADER EN SIDEBAR ====== */
    /* Dropzone */
    [data-testid="stSidebar"] .stFileUploader div[data-testid="stFileUploadDropzone"] {{
        background-color: {BOX_BG} !important;
        border: 1px dashed {BOX_BORDER} !important;
        color: #FFFFFF !important;
        border-radius: 10px !important;
    }}
    [data-testid="stSidebar"] .stFileUploader div[data-testid="stFileUploadDropzone"] * {{
        color: #FFFFFF !important;
    }}

    /* Botón "Browse files" */
    [data-testid="stSidebar"] .stFileUploader div[role="button"] {{
        background: {PRIMARY} !important;
        color: #0B1220 !important;
        border: 1px solid {PRIMARY} !important;
        font-weight: 700;
        border-radius: 8px !important;
    }}

    /* Lista de archivos subidos (chips/filas) */
    [data-testid="stSidebar"] div[data-testid="stFileUploaderFile"] {{
        background: #0F1B30 !important;
        border: 1px solid {BOX_BORDER} !important;
        color: #FFFFFF !important;
        border-radius: 8px !important;
        padding: 6px 8px !important;
        margin-bottom: 6px !important;
    }}
    [data-testid="stSidebar"] div[data-testid="stFileUploaderFile"] * {{
        color: #FFFFFF !important;
    }}
    [data-testid="stSidebar"] div[data-testid="stFileUploaderFile"] svg path {{
        fill: #FFFFFF !important;
        stroke: #FFFFFF !important;
    }}

    /* Botones */
    .stButton > button {{
        background: {PRIMARY} !important;
        color: #0B1220 !important;
        border: 1px solid {PRIMARY} !important;
        font-weight: 700;
        border-radius: 10px !important;
    }}
    .stButton > button:hover {{
        filter: brightness(1.05) !important;
    }}

    /* Aclarar el select principal del visor (barra clara) */
    .viewer-select .stSelectbox > div > div {{
        background-color: #F6F9FC !important;
        border: 1px solid #D7E1EC !important;
        color: {TEXT_MAIN} !important;
    }}
    </style>
    """, unsafe_allow_html=True)


# ==========================================
#                 APLICACIÓN
# ==========================================
def main():
    st.set_page_config(page_title="SelektIA – Evaluation", page_icon="✅", layout="wide")
    inject_css()

    # ====== Sidebar ======
    try:
        st.sidebar.image("assets/logo-wayki.png", use_column_width=True)
    except Exception:
        st.sidebar.markdown(f"<h3 style='color:{PRIMARY}'>Wayki Consulting</h3>", unsafe_allow_html=True)

    st.sidebar.markdown("### Definición del puesto")

    puesto = st.sidebar.selectbox(
        "Puesto",
        [
            "Enfermera/o Asistencial – Hospitalización / UCI intermedia",
            "Enfermera/o Asistencial – Emergencias",
            "Enfermera/o Asistencial – Centro Quirúrgico",
            "Otro"
        ],
        index=0
    )

    jd_text = st.sidebar.text_area(
        "Descripción del puesto (texto libre)",
        value=(
            "Resume el objetivo del puesto, responsabilidades clave, "
            "competencias y certificaciones. Incluye sistemas/tecnologías (p.ej., HIS / SAP IS-H), "
            "protocolos (IAAS), y lineamientos de seguridad del paciente."
        ),
        height=100
    )

    st.sidebar.markdown("#### Palabras clave del perfil\n*(ajústalas si es necesario)*")
    if "keywords" not in st.session_state:
        st.session_state["keywords"] = [
            "HIS", "SAP IS-H", "BLS", "ACLS",
            "IAAS", "educacion al paciente", "seguridad del paciente",
            "protocolos", "bombas de infusion"
        ]

    if st.sidebar.button("Sugerir keywords"):
        st.session_state["keywords"] = suggest_keywords_from_jd(jd_text)

    kw_text = st.sidebar.text_area(
        "Palabras clave",
        value=", ".join(st.session_state["keywords"]),
        height=120
    )
    keywords = [k.strip() for k in kw_text.split(",") if k.strip()]
    st.session_state["keywords"] = keywords

    st.sidebar.markdown("### Subir CVs (PDF o TXT)")
    files = st.sidebar.file_uploader("Arrastra aquí", type=["pdf", "txt"], accept_multiple_files=True)

    # ====== Main ======
    st.markdown("# SelektIA – Evaluation Results")
    st.markdown(
        "<div class='pill'>Define el puesto/JD, sugiere (o edita) keywords y sube algunos CVs (PDF o TXT) para evaluar.</div>",
        unsafe_allow_html=True
    )

    rows = []
    file_store = {}

    if files:
        for f in files:
            raw_bytes = f.read()
            file_store[f.name] = raw_bytes
            raw_text = extract_text_from_bytes(raw_bytes, f.name)
            score, reasons, txt_len = score_document(raw_text, keywords)
            rows.append({
                "Name": f.name,
                "Score": score,
                "Reasons": reasons,
                "PDF_text": f"{txt_len} chars"
            })

    if rows:
        df = pd.DataFrame(rows).sort_values("Score", ascending=False).reset_index(drop=True)
        st.dataframe(df, use_container_width=True, hide_index=True)

        st.markdown("### Score Comparison")
        names = df["Name"].tolist()
        scores = df["Score"].tolist()

        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=names, y=scores,
            marker_color=[PRIMARY] + ["#C9D7E8"]*(len(scores)-1),
            hovertemplate="<b>%{x}</b><br>Score: %{y}<extra></extra>"
        ))
        fig.update_layout(
            height=420,
            margin=dict(l=20, r=20, t=10, b=60),
            yaxis=dict(title="Score", gridcolor="#E5ECF6"),
            xaxis=dict(title="Name", tickangle=-30)
        )
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("### Visor de CV (PDF)")
        col_select, col_alt = st.columns([0.7, 0.3])
        with col_select:
            st.markdown("**Elige un candidato**")
            selected = st.selectbox(
                "",
                options=names,
                index=0,
                key="viewer_select",
                label_visibility="collapsed"
            )
        with col_alt:
            with st.expander("Elegir candidato (opción alternativa)"):
                selected_alt = st.selectbox("Candidato", names, index=0, key="viewer_select_alt")
                if selected_alt != selected:
                    selected = selected_alt

        st.caption(f"Mostrando: {selected}")

        if selected in file_store:
            pdf_bytes = file_store[selected]
            if selected.lower().endswith(".pdf") and HAS_PDF_VIEWER:
                pdf_viewer(pdf_bytes, width=1200)
            else:
                st.warning("No se pudo previsualizar el archivo. Puedes descargarlo a continuación.")
                st.markdown(get_download_button(pdf_bytes, selected, "Descargar CV"), unsafe_allow_html=True)

        st.markdown("----")
        st.markdown("**Descargar Excel (Selected + All)**")
        out = io.BytesIO()
        with pd.ExcelWriter(out, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Resultados")
        st.download_button(
            "Descargar Excel",
            data=out.getvalue(),
            file_name="selektia_resultados.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.info("Sube algunos CVs para ver el demo.")


if __name__ == "__main__":
    main()
