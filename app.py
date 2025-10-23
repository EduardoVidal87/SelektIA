# --- util para mostrar PDF inline ---
import base64
def show_pdf(file_bytes: bytes, height: int = 800):
    b64 = base64.b64encode(file_bytes).decode()
    st.markdown(
        f'<iframe src="data:application/pdf;base64,{b64}" width="100%" height="{height}" type="application/pdf"></iframe>',
        unsafe_allow_html=True
    )

# ---------- procesamiento ----------
rows = []
file_store = {}  # name -> dict con bytes y metadatos

if files:
    for f in files:
        # Guarda bytes para poder mostrar luego
        data = f.read()
        file_store[f.name] = {"bytes": data, "type": f.type}

        # Texto para scoring
        if f.type == "text/plain":
            raw = data.decode("utf-8", errors="ignore")
        else:
            # si es pdf
            raw = pdf_to_text(BytesIO(data))

        score, reason = score_candidate(raw, jd_keywords)

        rows.append({
            "Name": f.name.replace(".pdf","").replace("_"," ").title(),
            "FileName": f.name,
            "Score": score,
            "Reasons": reason
        })

    df = pd.DataFrame(rows).sort_values("Score", ascending=False)

    # --- layout con 2 columnas: izquierda ranking / derecha visor PDF ---
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
        fig.update_layout(yaxis_title="Score", xaxis_title=None, margin=dict(t=70, r=20, b=80, l=40))
        st.plotly_chart(fig, use_container_width=True)

        # Excel
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
        # Selector de candidato
        choice = st.selectbox("Elige un candidato para revisar su CV",
                              options=df["Name"].tolist(),
                              index=0 if not df.empty else None)
        if choice:
            # Recupera el file original por nombre de archivo
            file_name = df.loc[df["Name"] == choice, "FileName"].iloc[0]
            meta = file_store.get(file_name)
            if meta and meta["type"] == "application/pdf":
                show_pdf(meta["bytes"], height=820)
            elif meta:
                st.info("Este archivo no es PDF; muestro el texto inicial.")
                st.text((meta["bytes"][:2000]).decode("utf-8","ignore"))
            else:
                st.warning("No pude encontrar el archivo. Vuelve a cargarlo.")
else:
    st.info("Sube algunos CVs (PDF o TXT) para evaluar.")
