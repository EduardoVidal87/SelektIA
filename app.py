# --- util PDF inline ---
import base64
from io import BytesIO
def show_pdf(file_bytes: bytes, height: int = 820):
    b64 = base64.b64encode(file_bytes).decode()
    st.markdown(
        f'<iframe src="data:application/pdf;base64,{b64}" width="100%" height="{height}" type="application/pdf"></iframe>',
        unsafe_allow_html=True
    )

rows, file_store = [], {}

if files:
    for f in files:
        data = f.read()                      # guardo bytes para visor
        file_store[f.name] = {"bytes": data, "type": f.type}

        raw = data.decode("utf-8","ignore") if f.type=="text/plain" else pdf_to_text(BytesIO(data))
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
        fig = px.bar(df, x="Name", y="Score", text="Score")
        fig.update_traces(
            textposition="outside",
            customdata=df[["Reasons"]].values,
            hovertemplate="<b>%{x}</b><br>Score: %{y}<br>%{customdata[0]}<extra></extra>"
        )
        threshold = st.slider("Umbral de selección", 0, 100, 70, 1)
        fig.add_hline(y=threshold, line_dash="dot", opacity=0.6)
        st.plotly_chart(fig, use_container_width=True)

        selected_df = df[df["Score"] >= threshold]
        excel_bytes = build_excel(selected_df, df)
        st.download_button("⬇️ Descargar Excel (Selected + All)", data=excel_bytes,
                           file_name="SelektIA_Selection.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    with right:
        st.subheader("Visor de CV (PDF)")
        choice = st.selectbox("Elige un candidato", options=df["Name"].tolist())
        file_name = df.loc[df["Name"] == choice, "FileName"].iloc[0]
        meta = file_store.get(file_name)
        if meta and meta["type"] == "application/pdf":
            show_pdf(meta["bytes"])
        elif meta:
            st.info("Este archivo no es PDF; muestro texto:")
            st.text(meta["bytes"][:2000].decode("utf-8","ignore"))
