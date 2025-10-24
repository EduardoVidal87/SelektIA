# app.py — SelektIA (ranking + gráfico + Excel + visor PDF con fallback)
import streamlit as st
import pandas as pd
import plotly.express as px
from io import BytesIO
from pdfminer.high_level import extract_text
import base64, unicodedata, re

# ------------------- utilidades -------------------
def _norm(s: str) -> str:
    s = s.lower()
    s = ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')
    return s

# Sinónimos mínimos (ajústalos a tu realidad)
SYNONYMS = {
    "his": ["sistema hospitalario", "registro clinico", "erp salud"],
    "sap is-h": ["sap ish", "sap is h", "sap hospital"],
    "bombas de infusion": ["infusion pumps"],
    "bls": ["soporte vital basico"],
    "acls": ["soporte vital avanzado"],
    "uci intermedia": ["uci", "cuidados intermedios"],
    "educacion al paciente": ["educacion a pacientes", "educacion al usuario"],
}

def expand_keywords(kws):
    out = []
    for k in kws:
        k2 = _norm(k)
        if not k2:
            continue
        out.append(k2)
        for syn in SYNONYMS.get(k2, []):
            out.append(_norm(syn))
    # únicos, mantiene orden
    return list(dict.fromkeys(out))

def pdf_to_text(file_like) -> str:
    try:
        return extract_text(file_like)
    except Exception:
        return ""

def smart_keywords_parse(jd_text: str) -> list[str]:
    """Acepta coma, punto y coma, salto de línea, ' / ' y ' y '."""
    # 1) separa por coma, punto y coma o salto de línea
    parts = [x.strip() for x in re.split(r'[,\n;]+', jd_text) if x.strip()]
    # 2) divide por "/" y por ' y '
    out = []
    for p in parts:
        sub = [s.strip() for s in re.split(r'/|\\by\\b', p, flags=re.IGNORECASE) if s.strip()]
        out.extend(sub if sub else [p])
    # 3) elimina palabras de relleno
    STOP_PHRASES = ["manejo de", "vigente", "vigentes"]
    cleaned = []
    for k in out:
        kk = k
        for sp in STOP_PHRASES:
            kk = re.sub(rf'\\b{sp}\\b', '', kk, flags=re.I)
        kk = kk.strip(" .")
        if kk:
            cleaned.append(kk)
    return cleaned

def score_candidate(raw_text: str, jd_keywords: list) -> tuple[int, str]:
    text = _norm(" ".join(raw_text.split()))
    base_kws = [k.strip() for k in jd_keywords if k.strip()]
    kws = expand_keywords(base_kws)
    hits = sum(1 for k in kws if re.search(rf"\\b{re.escape(_norm(k))}\\b", text))
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
    """Visor PDF con fallback a descarga si el navegador no lo renderiza."""
    b64 = base64.b64encode(file_bytes).decode()
    html_code = f"""
    <object data="data:application/pdf;base64,{b64}" type="application/pdf" width="100%" height="{height}">
        <p>No se pudo previsualizar el PDF.
        <a download="cv.pdf" href="data:application/pdf;base64,{b64}">Descargar CV</a></p>
    </object>
    """
    st.components.v1.html(html_code, height=height, scrolling=True)

# ------------------- UI -------------------
st.set_page_config(page_title="SelektIA", layout="wide")

st.sidebar.header("Job Description")
default_kws = (
    "HIS, SAP IS-H, bombas de infusión, 5 correctos, IAAS, bundles VAP, BRC, CAUTI, "
    "curación avanzada, educación al paciente, BLS, ACLS, hospitalización, UCI intermedia"
)
jd_text = st.sidebar.text_area("Keywords (coma separada):", default_kws, height=120)

# parsing robusto de keywords
jd_keywords = smart_keywords_parse(jd_text)

st.sidebar.header("Upload CVs (PDF o TXT)")
files = st.sidebar.file_uploader("Arrastra aquí", type=["pdf","txt"], accept_multiple_files=True)

st.title("SelektIA – Evaluation Results")

# ------------------- lógica principal -------------------
rows, file_store = [], {}

if files:
    for f in files:
        data = f.read()  # guardo bytes para visor
        file_store[f.name] = {"bytes": data, "type": f.type}

        # texto para scoring
        if f.type == "text/plain":
            raw = data.decode("utf-8", errors="ignore")
        else:
            raw = pdf_to_text(BytesIO(data))

        score, reason = score_candidate(raw, jd_keywords)
        rows.append({
            "Name": f.name.replace(".pdf","").replace("_"," ").title(),
            "FileName": f.name,
            "Score": score,
            "Reasons": reason
        })

    df = pd.DataFrame(rows).sort_values("Score", ascending=False)

    left, right = st.columns([0.58, 0.42])
    with left:
        st.dataframe(df[["Name","Score","Reasons"]], use_container_width=True)

        st.subheader("Score Comparison")
        threshold = st.slider("Umbral de selección", 0, 100, 70, 1)

        fig = px.bar(df, x="Name", y="Score", text="Score",
                     color=(df["Score"] >= threshold).map({True: "Seleccionado", False: "Revisión"}),
                     color_discrete_map={"Seleccionado": "#00A36C", "Revisión": "#1f77b4"})
        fig.update_traces(
            textposition="outside",
            customdata=df[["Reasons"]].values,
            hovertemplate="<b>%{x}</b><br>Score: %{y}<br>%{customdata[0]}<extra></extra>"
        )
        fig.add_hline(y=threshold, line_dash="dot", opacity=0.6)
        fig.update_layout(yaxis_title="Score", xaxis_title=None, margin=dict(t=70, r=20, b=80, l=40))
        st.plotly_chart(fig, use_container_width=True)

        selected_df = df[df["Score"] >= threshold]
        excel_bytes = build_excel(selected_df, df)
        st.download_button(
            "⬇️ Descargar Excel (Selected + All)",
            data=excel_bytes,
            file_name="SelektIA_Selection.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        st.caption(f"Seleccionados: {len(selected_df)} / {len(df)}")

    with right:
        st.subheader("Visor de CV (PDF)")
        choice = st.selectbox("Elige un candidato", options=df["Name"].tolist())
        file_name = df.loc[df["Name"] == choice, "FileName"].iloc[0]
        meta = file_store.get(file_name)
        if meta and meta["type"] == "application/pdf":
            show_pdf(meta["bytes"])
        elif meta:
            st.info("Este archivo no es PDF; muestro el texto:")
            st.text(meta["bytes"][:2000].decode("utf-8","ignore"))
else:
    st.info("Sube algunos CVs (PDF o TXT) para evaluar.")
