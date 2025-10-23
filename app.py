import streamlit as st
import pandas as pd
import plotly.express as px
from io import BytesIO

# ---------- PDF parser (simple) ----------
from pdfminer.high_level import extract_text

def pdf_to_text(file) -> str:
    try:
        return extract_text(file)
    except Exception:
        return ""

# ---------- Scoring sencillo y explicable ----------
def score_candidate(raw_text: str, jd_keywords: list) -> tuple[int, str]:
    text = " ".join(raw_text.split()).lower()
    kws = [k.strip().lower() for k in jd_keywords if k.strip()]
    hits = sum(1 for k in kws if k in text)
    ratio = hits / max(1, len(kws))
    score = round(100 * ratio)
    reasons = f"{hits}/{len(kws)} keywords del JD encontradas"
    return score, reasons

# ---------- Excel export ----------
def build_excel(shortlist_df: pd.DataFrame, all_df: pd.DataFrame) -> bytes:
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as xw:
        shortlist_df.to_excel(xw, index=False, sheet_name="Selected")
        all_df.to_excel(xw, index=False, sheet_name="All_Scores")
    buf.seek(0)
    return buf.read()

# ---------- UI ----------
st.set_page_config(page_title="SelektIA", layout="wide")
st.sidebar.header("Job Description")
jd_text = st.sidebar.text_area(
    "Keywords (coma separada):",
    "Excel, Power BI, SAP, CRM, Ventas, Python",
    height=100
)
jd_keywords = [k.strip() for k in jd_text.split(",") if k.strip()]

st.sidebar.header("Upload CVs (PDF o TXT)")
files = st.sidebar.file_uploader("Arrastra aquí", type=["pdf","txt"], accept_multiple_files=True)

st.title("SelektIA – Evaluation Results")

rows = []
if files:
    for f in files:
        if f.type == "text/plain":
            raw = f.read().decode("utf-8", errors="ignore")
        else:
            raw = pdf_to_text(f)

        score, reason = score_candidate(raw, jd_keywords)

        rows.append({
            "Name": f.name.replace(".pdf","").replace("_"," ").title(),
            "Score": score,
            "Reasons": reason
        })

    df = pd.DataFrame(rows).sort_values("Score", ascending=False)

    st.dataframe(df, use_container_width=True)

    st.header("Score Comparison")
    fig = px.bar(df, x="Name", y="Score", text="Score")
    fig.update_traces(
        textposition="outside",
        customdata=df[["Reasons"]].values,
        hovertemplate="<b>%{x}</b><br>Score: %{y}<br>%{customdata[0]}<extra></extra>"
    )
    fig.update_layout(yaxis_title="Score", xaxis_title=None, margin=dict(t=70, r=20, b=80, l=40))
    st.plotly_chart(fig, use_container_width=True)

    # Shortlist y descarga Excel
    threshold = st.slider("Umbral de selección", 0, 100, 70, 1)
    selected = df[df["Score"] >= threshold]
    excel_bytes = build_excel(selected, df)

    c1, c2 = st.columns(2)
    with c1:
        st.download_button(
            "⬇️ Descargar Excel (Selected + All)",
            data=excel_bytes,
            file_name="SelektIA_Selection.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    with c2:
        st.success(f"Seleccionados: {len(selected)} / {len(df)}")
else:
    st.info("Sube algunos CVs (PDF o TXT) para evaluar.")
