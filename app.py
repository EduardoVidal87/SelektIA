def page_analytics():
  st.header("Sourcing Performance")

  # -------------------------------
  # Helper: KPI card con sparkline
  # -------------------------------
  def kpi_card(title, value, series, fmt="{:,.0f}", help_text=None):
    c = st.container()
    with c:
      col1, col2 = st.columns([0.55, 0.45])
      with col1:
        st.markdown(f"**{title}**")
        st.markdown(f"<div style='font-size:34px;font-weight:800;color:{TITLE_DARK}'>{fmt.format(value)}</div>",
                    unsafe_allow_html=True)
        if help_text:
          st.caption(help_text)
      with col2:
        if series is not None and len(series) > 1:
          spark = px.area(
            x=list(range(len(series))), y=series,
            height=70
          )
          spark.update_traces(hovertemplate=None, line_color=PRIMARY, fillcolor="rgba(0,205,120,0.18)")
          spark.update_layout(
            margin=dict(l=0,r=0,t=0,b=0),
            xaxis=dict(visible=False), yaxis=dict(visible=False),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)"
          )
          st.plotly_chart(spark, use_container_width=True, config={"displayModeBar": False})

  # -------------------------------
  # Preparación de datos
  # -------------------------------
  # Candidates DF
  cand = []
  for c in ss.candidates:
    fit = None
    try:
      # si ya transformaste en page_eval, guarda Fit, si no, re-calculamos con defaults
      fit = c.get("Fit", None)
    except:
      fit = None
    if fit is None:
      jd = ss.get("last_jd_text", "")
      preset = ROLE_PRESETS.get(ss.get("last_role",""), {})
      must, nice = preset.get("must", []), preset.get("nice", [])
      txt = c.get("_text") or (c.get("_bytes") or b"").decode("utf-8","ignore")
      fit,_ = score_fit_by_skills(jd, must, nice, txt or "")

    # canal (hiring channel) desde prefijo <portal>_...
    name = c.get("Name","")
    canal = name.split("_")[0] if "_" in name else "Otros"

    # fecha (para sparklines)
    meta = c.get("meta", {})
    fch  = meta.get("ultima_actualizacion", date.today().isoformat())
    try:
      fch = pd.to_datetime(fch).date()
    except Exception:
      fch = date.today()

    cand.append({"Name": name, "fit": int(fit), "canal": canal, "fecha": fch})

  dfc = pd.DataFrame(cand) if cand else pd.DataFrame(columns=["Name","fit","canal","fecha"])

  # Sparklines: counts por día y fit promedio por día
  if not dfc.empty:
    series_count = (dfc.groupby("fecha").size().astype(int)
                        .reindex(pd.date_range(dfc["fecha"].min(), date.today()), fill_value=0))
    series_fit   = (dfc.groupby("fecha")["fit"].mean()
                        .reindex(pd.date_range(dfc["fecha"].min(), date.today()), fill_value=0))
    spark_counts = series_count.rolling(5, min_periods=1).mean().tolist()
    spark_fit    = series_fit.rolling(5, min_periods=1).mean().tolist()
  else:
    spark_counts, spark_fit = [0,1,0,1,0], [0,20,40,30,50]

  # KPIs
  total_puestos = len(ss.positions)
  total_cvs     = len(dfc)
  avg_fit       = round(float(dfc["fit"].mean()),1) if not dfc.empty else 0.0

  # -------------------------------
  # Fila de KPIs (3 tarjetas)
  # -------------------------------
  k1,k2,k3 = st.columns(3)
  with k1: kpi_card("Findem-Influenced Applications", total_cvs, spark_counts)
  with k2: kpi_card("Contact-to-interest Rate", (dfc["fit"]>=70).mean()*100 if not dfc.empty else 0,
                    spark_fit, fmt="{:.1f}%")
  with k3: kpi_card("Puestos activos", total_puestos, spark_counts, fmt="{:,.0f}")

  st.markdown("---")

  # -------------------------------
  # Gráficos principales (fila 1)
  # -------------------------------
  g1,g2,g3 = st.columns([1.05,1.05,0.9])

  # (1) Barras apiladas por canal: % en bandas de fit
  with g1:
    st.markdown("**Findem-influenced Application by Hiring Channel**")
    if not dfc.empty:
      dfc["band"] = pd.cut(dfc["fit"],
                           bins=[-1,39,69,100],
                           labels=["Bajo (<40)","Medio (40-69)","Alto (≥70)"])
      dist = (dfc.groupby(["canal","band"]).size().reset_index(name="qty"))
      total_canal = dist.groupby("canal")["qty"].transform("sum")
      dist["pct"] = dist["qty"]/total_canal

      # order bands para apilado
      band_cat = pd.Categorical(dist["band"],
                                categories=["Bajo (<40)","Medio (40-69)","Alto (≥70)"],
                                ordered=True)
      dist = dist.assign(band=band_cat).sort_values(["canal","band"])

      fig = px.bar(dist, x="canal", y="pct", color="band",
                   color_discrete_sequence=["#e8eefc","#98c8ff","#00CD78"],
                   labels={"pct":"%"},
                   height=340)
      fig.update_layout(legend_title_text="", yaxis_tickformat=".0%")
      st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    else:
      st.info("Sin datos de candidatos para graficar.")

  # (2) Funnel (Contacted → Replied → Interested)
  with g2:
    st.markdown("**Outreach Funnel Conversion**")
    if not dfc.empty:
      contacted  = len(dfc)
      replied    = int((dfc["fit"]>=40).sum())
      interested = int((dfc["fit"]>=70).sum())
      funnel_df  = pd.DataFrame({"Stage":["Contacted","Replied","Interested"],
                                 "Count":[contacted, replied, interested]})
      fig = px.funnel(funnel_df, x="Count", y="Stage", height=340,
                      color_discrete_sequence=[PRIMARY])
      fig.update_layout(margin=dict(l=30,r=30,t=20,b=20),
                        paper_bgcolor="rgba(0,0,0,0)",
                        plot_bgcolor="rgba(0,0,0,0)")
      st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    else:
      st.info("Sin datos de candidatos para graficar.")

  # (3) Días abiertos por puesto (ya lo tenías)
  with g3:
    st.markdown("**Time to Reply by Hiring Channel (proxy)**")
    # Usamos días abiertos como proxy visual
    dfp = ss.positions[["Puesto","Días Abierto"]].copy()
    fig2 = px.bar(dfp, x="Puesto", y="Días Abierto", height=340)
    fig2.update_layout(plot_bgcolor="#FFFFFF", paper_bgcolor="rgba(0,0,0,0)",
                       font=dict(color=TITLE_DARK), xaxis_tickangle=-25)
    st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})

  # -------------------------------
  # Gráficos secundarios (fila 2)
  # -------------------------------
  s1,s2,s3 = st.columns(3)

  # (4) Reply Rate por canal (fit ≥ 40)
  with s1:
    st.markdown("**Reply Rate by Hiring Channel**")
    if not dfc.empty:
      reply = (dfc.assign(reply=(dfc["fit"]>=40))
                    .groupby("canal")["reply"].mean().reset_index())
      fig = px.bar(reply, x="canal", y="reply", height=320, labels={"reply":"Reply Rate"})
      fig.update_layout(yaxis_tickformat=".0%")
      st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    else:
      st.info("Sin datos de candidatos para graficar.")

  # (5) Contact-to-Interest Rate por canal (fit ≥ 70)
  with s2:
    st.markdown("**Contact-to-Interest Rate by Hiring Channel**")
    if not dfc.empty:
      ir = (dfc.assign(interested=(dfc["fit"]>=70))
                .groupby("canal")["interested"].mean().reset_index())
      fig = px.bar(ir, x="canal", y="interested", height=320,
                   labels={"interested":"Interest Rate"},
                   color="canal", color_discrete_sequence=px.colors.qualitative.Set2)
      fig.update_layout(showlegend=False, yaxis_tickformat=".0%")
      st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    else:
      st.info("Sin datos de candidatos para graficar.")

  # (6) Distribución de Fit (histograma)
  with s3:
    st.markdown("**Fit Distribution**")
    if not dfc.empty:
      fig = px.histogram(dfc, x="fit", nbins=15, height=320,
                         color_discrete_sequence=[PRIMARY])
      fig.update_layout(xaxis_title="Fit", yaxis_title="Candidatos")
      st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    else:
      st.info("Sin datos de candidatos para graficar.")
