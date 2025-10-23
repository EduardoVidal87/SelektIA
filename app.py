import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="SelektIA", layout="wide")

st.sidebar.header("Job Description")
jd_text = st.sidebar.text_area("Keywords (coma separada):", "Excel, Power BI, SAP, CRM, Ventas, Python", height=100)

st.sidebar.header("Upload CVs (PDF o TXT para demo)")
files = st.sidebar.file_uploader("Arrastra aquí", type=["pdf","txt"], accept_multiple_files=True)

st.title("SelektIA – Evaluation Results")

rows = []
if files:
    for f in files:
        raw = f.read().decode("utf-8", errors="ignore") if f.type == "text/plain" else ""
        rows.append({
            "Name": f.name.replace(".pdf","").replace("_"," ").title(),
            "Years_of_Experience": 0,
            "English_Level": "—",
            "Key_Skills": ", ".join([k.strip() for k in jd_text.split(",")][:3]),
            "Score": 50
        })
    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True)

    st.header("Score Comparison")
    fig = px.bar(df.sort_values("Score", ascending=False), x="Name", y="Score", text="Score")
    fig.update_traces(textposition="outside",
                      hovertemplate="<b>%{x}</b><br>Score: %{y}<extra></extra>")
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Sube algunos CVs para ver el demo.")
