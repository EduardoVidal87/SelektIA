def _auto_pos_id():
  return f"P-{random.randint(10_000_000, 99_999_999)}"

def _calc_dias_abierto(fecha_iso: str, estado: str) -> int:
  try:
    fi = datetime.fromisoformat(fecha_iso).date()
  except:
    return 0
  days = (date.today() - fi).days
  return max(0, days)

def page_puestos():
  st.header("Puestos")

  # ====== Filtros ======
  with st.container():
    colf1, colf2, colf3 = st.columns([0.5, 0.3, 0.2])
    with colf1:
      q = st.text_input("Buscar (puesto, manager, ubicación)", value="")
    with colf2:
      est = st.selectbox("Estado", ["Todos","Abierto","Cerrado"], index=0)
    with colf3:
      if st.button("🔄 Refrescar"):
        st.rerun()

  df = ss.positions.copy()

  # Normaliza columnas mínimas
  for c in ["Leads","Nuevos","Recruiter Screen","HM Screen","Entrevista Telefónica","Entrevista Presencial"]:
    if c not in df.columns:
      df[c] = 0

  # Filtros
  if q.strip():
    ql = q.lower()
    mask = (
      df["Puesto"].str.lower().str.contains(ql, na=False) |
      df["Ubicación"].str.lower().str.contains(ql, na=False) |
      df["Hiring Manager"].str.lower().str.contains(ql, na=False) |
      df["ID"].str.lower().str.contains(ql, na=False)
    )
    df = df[mask]
  if est != "Todos":
    df = df[df["Estado"] == est]

  # Campos derivados
  df["Días Abierto"] = df.apply(lambda r: _calc_dias_abierto(r.get("Fecha Inicio",""), r.get("Estado","Abierto")) if r.get("Estado")=="Abierto" else 0, axis=1)
  df["Time to Hire (promedio)"] = df["Días Abierto"].apply(lambda d: f"{max(d,1)+18} días")

  # ====== Crear nuevo puesto ======
  with st.expander("➕ Crear nuevo puesto", expanded=False):
    with st.form("new_pos_form"):
      c1,c2,c3 = st.columns(3)
      with c1:
        new_id = st.text_input("ID", value=_auto_pos_id())
        new_title = st.text_input("Puesto*")
      with c2:
        new_loc = st.text_input("Ubicación*", value="Lima, Perú")
        new_hm  = st.text_input("Hiring Manager*", value="Nombre y Apellido")
      with c3:
        new_state = st.selectbox("Estado*", ["Abierto","Cerrado"], index=0)
        new_start = st.date_input("Fecha Inicio*", value=date.today())
      # Métricas opcionales
      c4,c5,c6,c7,c8 = st.columns(5)
      with c4: leads = st.number_input("Leads", 0, 1_000_000, 0, step=10)
      with c5: nuevos = st.number_input("Nuevos", 0, 1_000_000, 0, step=1)
      with c6: rs = st.number_input("Recruiter Screen", 0, 1_000_000, 0, step=1)
      with c7: hms = st.number_input("HM Screen", 0, 1_000_000, 0, step=1)
      with c8: et = st.number_input("Entrevista Telefónica", 0, 1_000_000, 0, step=1)
      ep = st.number_input("Entrevista Presencial", 0, 1_000_000, 0, step=1, key="new_ep")

      ok_create = st.form_submit_button("Guardar puesto")
      if ok_create:
        if not new_title.strip():
          st.error("Debes completar el campo **Puesto**.")
        else:
          row = {
            "ID": new_id.strip() or _auto_pos_id(),
            "Puesto": new_title.strip(),
            "Ubicación": new_loc.strip(),
            "Hiring Manager": new_hm.strip(),
            "Estado": new_state,
            "Fecha Inicio": new_start.isoformat(),
            "Leads": int(leads), "Nuevos": int(nuevos),
            "Recruiter Screen": int(rs), "HM Screen": int(hms),
            "Entrevista Telefónica": int(et), "Entrevista Presencial": int(ep)
          }
          ss.positions = pd.concat([ss.positions, pd.DataFrame([row])], ignore_index=True)
          save_positions(ss.positions)
          st.success("Puesto creado.")
          st.rerun()

  st.markdown("---")
  st.subheader("Listado de puestos")

  # Orden por estado / días abierto / leads
  df_display = df[
    ["Puesto","Días Abierto","Time to Hire (promedio)","Leads","Nuevos",
     "Recruiter Screen","HM Screen","Entrevista Telefónica","Entrevista Presencial",
     "Ubicación","Hiring Manager","Estado","ID","Fecha Inicio"]
  ].sort_values(["Estado","Días Abierto","Leads"], ascending=[True,True,False])

  # Cabecera de tabla (visual)
  st.markdown("""
  <table style="width:100%; border-spacing:0 8px;">
    <thead>
      <tr style="text-align:left; color:#1B2A3C;">
        <th style="width:26%;">Puesto</th>
        <th style="width:10%;">Días</th>
        <th style="width:12%;">Time to Hire</th>
        <th style="width:10%;">Leads</th>
        <th style="width:10%;">Ubicación</th>
        <th style="width:12%;">Hiring Manager</th>
        <th style="width:8%;">Estado</th>
        <th style="width:12%;">Acciones</th>
      </tr>
    </thead>
  </table>
  """, unsafe_allow_html=True)

  # ====== Filas con acciones ======
  for idx, row in df_display.iterrows():
    rid = row["ID"]
    st.markdown('<div class="k-card">', unsafe_allow_html=True)

    c1,c2,c3,c4,c5,c6,c7,c8 = st.columns([0.26,0.10,0.12,0.10,0.10,0.12,0.08,0.12])
    with c1: st.markdown(f"**{row['Puesto']}**  \n<span style='opacity:.7;font-size:12px'>ID: {rid}</span>", unsafe_allow_html=True)
    with c2: st.write(row["Días Abierto"])
    with c3: st.write(row["Time to Hire (promedio)"])
    with c4: st.write(int(row["Leads"]))
    with c5: st.write(row["Ubicación"])
    with c6: st.write(row["Hiring Manager"])
    with c7: st.write(row["Estado"])

    with c8:
      act = st.selectbox(
        "Acción",
        ["Selecciona…","Editar","Duplicar","Abrir/Cerrar","Eliminar"],
        key=f"pos_act_{rid}", label_visibility="collapsed"
      )

      if act == "Duplicar":
        new_row = dict(row)
        new_row["ID"] = _auto_pos_id()
        ss.positions = pd.concat([ss.positions, pd.DataFrame([new_row])], ignore_index=True)
        save_positions(ss.positions)
        st.success("Puesto duplicado.")
        st.rerun()

      elif act == "Abrir/Cerrar":
        # Toggle estado
        i_real = ss.positions.index[ss.positions["ID"]==rid][0]
        ss.positions.at[i_real, "Estado"] = "Cerrado" if ss.positions.at[i_real, "Estado"]=="Abierto" else "Abierto"
        save_positions(ss.positions); st.success("Estado actualizado."); st.rerun()

      elif act == "Eliminar":
        ss.positions = ss.positions[ss.positions["ID"] != rid].reset_index(drop=True)
        save_positions(ss.positions); st.warning("Puesto eliminado."); st.rerun()

      elif act == "Editar":
        with st.expander(f"Editar: {row['Puesto']}"):
          with st.form(f"edit_pos_{rid}"):
            e1,e2,e3 = st.columns(3)
            with e1:
              eid = st.text_input("ID", value=row["ID"])
              etitle = st.text_input("Puesto*", value=row["Puesto"])
            with e2:
              eloc = st.text_input("Ubicación*", value=row["Ubicación"])
              ehm  = st.text_input("Hiring Manager*", value=row["Hiring Manager"])
            with e3:
              estate = st.selectbox("Estado*", ["Abierto","Cerrado"], index=0 if row["Estado"]=="Abierto" else 1)
              estart = st.date_input("Fecha Inicio*", value=datetime.fromisoformat(row["Fecha Inicio"]).date() if row["Fecha Inicio"] else date.today())
            m1,m2,m3,m4,m5,m6 = st.columns(6)
            with m1: eleads = st.number_input("Leads", 0, 1_000_000, int(row["Leads"]), step=10, key=f"eleads_{rid}")
            with m2: enuevos = st.number_input("Nuevos", 0, 1_000_000, int(row["Nuevos"]), step=1, key=f"enew_{rid}")
            with m3: ers = st.number_input("Recruiter Screen", 0, 1_000_000, int(row["Recruiter Screen"]), step=1, key=f"ers_{rid}")
            with m4: ehms = st.number_input("HM Screen", 0, 1_000_000, int(row["HM Screen"]), step=1, key=f"ehms_{rid}")
            with m5: eet = st.number_input("Entrevista Telefónica", 0, 1_000_000, int(row["Entrevista Telefónica"]), step=1, key=f"eet_{rid}")
            with m6: eep = st.number_input("Entrevista Presencial", 0, 1_000_000, int(row["Entrevista Presencial"]), step=1, key=f"eep_{rid}")

            ok_upd = st.form_submit_button("Guardar cambios")
            if ok_upd:
              i_real = ss.positions.index[ss.positions["ID"]==rid][0]
              ss.positions.at[i_real, "ID"] = eid.strip() or row["ID"]
              ss.positions.at[i_real, "Puesto"] = etitle.strip()
              ss.positions.at[i_real, "Ubicación"] = eloc.strip()
              ss.positions.at[i_real, "Hiring Manager"] = ehm.strip()
              ss.positions.at[i_real, "Estado"] = estate
              ss.positions.at[i_real, "Fecha Inicio"] = estart.isoformat()
              ss.positions.at[i_real, "Leads"] = int(eleads)
              ss.positions.at[i_real, "Nuevos"] = int(enuevos)
              ss.positions.at[i_real, "Recruiter Screen"] = int(ers)
              ss.positions.at[i_real, "HM Screen"] = int(ehms)
              ss.positions.at[i_real, "Entrevista Telefónica"] = int(eet)
              ss.positions.at[i_real, "Entrevista Presencial"] = int(eep)
              save_positions(ss.positions)
              st.success("Puesto actualizado.")
              st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)

  st.markdown("---")
  # ====== Candidatos por puesto (como antes, pero coherente con CRUD) ======
  st.subheader("Candidatos por Puesto")
  pos_list = ss.positions["Puesto"].tolist()
  selected_pos = st.selectbox("Selecciona un puesto para ver candidatos del Pipeline", pos_list) if pos_list else None
  if selected_pos:
    candidates_for_pos = [c for c in ss.candidates if c.get("Role") == selected_pos]
    if candidates_for_pos:
        df_cand = pd.DataFrame(candidates_for_pos)
        st.dataframe(df_cand[["Name", "Score", "stage", "load_date"]].rename(columns={"Name":"Candidato", "Score":"Fit", "stage":"Fase"}), 
                     use_container_width=True, hide_index=True)
    else:
        st.info(f"No hay candidatos activos para **{selected_pos}**.")
