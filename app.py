import streamlit as st
import pandas as pd
import plotly.express as px
from io import BytesIO
from pdfminer.high_level import extract_text
import base64
import unicodedata, re

# ------------------- utilidades -------------------
def _norm(s: str) -> str:
    s = s.lower()
    s = ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')
    return s

SYNONYMS = {
    "his": ["sistema hospitalario", "registro clinico", "erp salud"],
    "sap is-h": ["sap ish", "sap is h", "sap hospital"],
    "bombas de infusion": ["infusion pumps"],
    "bls": ["soporte vital basico"],
    "acls": ["soporte vital avanzado"],
    "uci intermedia": ["uci", "cuidados intermedios"],
}

def expand_keywords(kws):
    out = []
    for k in kws:
        k2 = _norm(k)
        out.append(k2)
        for syn in SYNONYMS.get(k2, []):
            out.append(_norm(syn))
    return list(dict.fromkeys(out))

def pdf_to_text(file_like) -> str:
    try:
        return extract_text(file_like)
    except Exception:
        return ""

def score_candidate(raw_text: str, jd_keywords: list) -> tuple[int, str]:
    text = _norm(" ".join(raw_text.split()))
    base_kws = [k.strip() for k in jd_keywords if k.strip()]
    kws = expand_keywords(base_kws)
    hits = sum(1 for k in kws if re.search(rf"\b{re.escape(_norm(k))}\b", text))
    ratio = min(hits / max(1, len(base_kws)), 1.0)
    score = round(100 * ratio)
    return score, f"{hits}/{len(base_kws)} keywords del JD (incl. sinónimos) encontradas"

def build_excel(shortlist_df: pd.DataFrame, all_df: pd.DataFrame) -> bytes:
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as xw:
        shortlist_df.to_excel(xw, index=False, sheet_name="Selected")
        all_df.to_excel(xw, index=False, sheet_name="All_Scores")
    buf.seek(0); return buf.read()

def show_pdf(file_bytes: bytes, height: int = 820):
    b64 = base64.b64encode(file_bytes).decode()
    st.markdown(
        f'<iframe src="data:application/pdf;base64,{b64}" width="100%" height="{height}" type="application/pdf"></iframe>',
        unsafe_allow_html=True
    )

# ------------------- UI -------------------
st.set_page_config(page_title="SelektIA", layout="wide")

st.sidebar.header("Job Description")
jd_text = st.sidebar.text_area(
    "Keywords (coma separada):",
    "HIS, SAP IS-H, bombas de infusión, 5 correctos, IAAS, bundles VAP, BRC, CAUTI, curación avanzada, "
    "educación al paciente, BLS, ACLS, hospitalización, UCI intermedia",
    height=120
)
jd_keywords = [k.strip() for k in jd_text.split(",") if k.strip()]

st.sidebar.header("Upload CVs (PDF o TXT)")
files = st.sidebar.file_uploader("Arrastra aquí", type=["pdf","txt"], accept_multiple_files=True)

st.title("SelektIA – Evaluation Results")

# ------------------- lógica principal -------------------
rows, file_store = [], {}

if files:
    for f in files:
        data = f.read()  # guardo bytes para luego mostrar el PDF
        file_store[f.name] = {"bytes_
