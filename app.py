# --- Pegar aquí el resto de las funciones page_* ---

def page_pipeline():
    filter_stage = ss.get("pipeline_filter")
    if filter_stage:
        st.header(f"Pipeline: Candidatos en Fase '{filter_stage}'")
        candidates_to_show = [c for c in ss.candidates if c.get("stage") == filter_stage]
    else:
        st.header("Pipeline de Candidatos (Vista Kanban)")
        candidates_to_show = ss.candidates
    st.caption("Arrastra los candidatos a través de las etapas para avanzar el proceso.")
    if not candidates_to_show and filter_stage:
          st.info(f"No hay candidatos en la fase **{filter_stage}**."); return
    elif not ss.candidates:
          st.info("No hay candidatos activos. Carga CVs en **Publicación & Sourcing**."); return
    candidates_by_stage = {stage: [] for stage in PIPELINE_STAGES}
    for c in candidates_to_show:
        candidates_by_stage[c["stage"]].append(c)
    cols = st.columns(len(PIPELINE_STAGES))
    for i, stage in enumerate(PIPELINE_STAGES):
        with cols[i]:
            st.markdown(f"**{stage} ({len(candidates_by_stage[stage])})**", unsafe_allow_html=True)
            st.markdown("---")
            for c in candidates_by_stage[stage]:
                card_name = c["Name"].split('_')[-1].replace('.pdf', '').replace('.txt', '')
                st.markdown(f"""
                <div class="k-card" style="margin-bottom: 10px; border-left: 4px solid {PRIMARY if c['Score'] >= 70 else ('#FFA500' if c['Score'] >= 40 else '#D60000')}">
                    <div style="font-weight:700; color:{TITLE_DARK};">{card_name}</div>
                    <div style="font-size:12px; opacity:.8;">{c.get("Role", "Puesto Desconocido")}</div>
                    <div style="font-size:14px; font-weight:700; margin-top:8px;">Fit: <span style="color:{PRIMARY};">{c["Score"]}%</span></div>
                    <div style="font-size:10px; opacity:.6; margin-top:4px;">Fuente: {c.get("source", "N/A")}</div>
                </div>
                """, unsafe_allow_html=True)
                with st.form(key=f"form_move_{c['id']}", clear_on_submit=False):
                    current_stage_index = PIPELINE_STAGES.index(stage)
                    available_stages = [s for s in PIPELINE_STAGES if s != stage]
                    try:
                        default_index = available_stages.index(PIPELINE_STAGES[min(current_stage_index + 1, len(PIPELINE_STAGES) - 1)])
                    except ValueError:
                        default_index = 0
                    new_stage = st.selectbox("Mover a:", available_stages, key=f"select_move_{c['id']}", index=default_index, label_visibility="collapsed")
                    if st.form_submit_button("Mover Candidato"):
                        c["stage"] = new_stage
                        if new_stage == "Descartado":
                            st.success(f"📧 **Comunicación:** Email de rechazo automático enviado a {card_name}.")
                        elif new_stage == "Entrevista Telefónica":
                            st.info(f"📅 **Automatización:** Tarea de programación de entrevista generada para {card_name}.")
                            task_context = {"candidate_name": card_name, "candidate_id": c["id"], "role": c.get("Role", "N/A")}
                            create_task_from_flow(f"Programar entrevista - {card_name}", date.today()+timedelta(days=2),
                                                  "Coordinar entrevista telefónica con el candidato.",
                                                  assigned="Headhunter", status="Pendiente", context=task_context)
                        elif new_stage == "Contratado":
                            st.balloons()
                            st.success(f"🎉 **¡Éxito!** Flujo de Onboarding disparado para {card_name}.")
                        if filter_stage and new_stage != filter_stage:
                            ss.pipeline_filter = None
                            st.info("El filtro ha sido removido al mover el candidato de fase.")
                        st.rerun()
                st.markdown("<br>", unsafe_allow_html=True)

def page_interview():
  st.header("Entrevista (Gerencia)")
  st.write("Esta página ahora redirige al **Pipeline** con el filtro **Entrevista Gerencia**.")
  st.info("Por favor, usa el **Pipeline de Candidatos** y el filtro del menú lateral para gestionar esta etapa de forma visual.")
  ss.section = "pipeline"; ss.pipeline_filter = "Entrevista Gerencia"; st.rerun()

def _ensure_offer_record(cand_name: str):
  if cand_name not in ss.offers:
    ss.offers[cand_name] = {
      "puesto": "", "ubicacion": "", "modalidad": "Presencial", "salario": "", "beneficios": "",
      "fecha_inicio": date.today() + timedelta(days=14), "caducidad": date.today() + timedelta(days=7),
      "aprobadores": "Gerencia, Legal, Finanzas", "estado": "Borrador"
    }

def page_offer():
  st.header("Oferta")
  st.write("Esta página ahora redirige al **Pipeline** con el filtro **Oferta**.")
  st.info("Por favor, usa el **Pipeline de Candidatos** y el filtro del menú lateral para gestionar esta etapa de forma visual.")
  ss.section = "pipeline"; ss.pipeline_filter = "Oferta"; st.rerun()

def page_onboarding():
  st.header("Onboarding")
  st.write("Esta página ahora redirige al **Pipeline** con el filtro **Contratado**.")
  st.info("Por favor, usa el **Pipeline de Candidatos** y el filtro del menú lateral para gestionar esta etapa de forma visual.")
  ss.section = "pipeline"; ss.pipeline_filter = "Contratado"; st.rerun()

def page_hh_tasks():
    st.header("Tareas Asignadas a Mí")
    st.write("Esta página lista las tareas asignadas a tu rol (Headhunter/Colaborador).")
    if not isinstance(ss.tasks, list) or not ss.tasks: st.info("No tienes tareas asignadas."); return
    df_tasks = pd.DataFrame(ss.tasks)
    my_name = ss.auth["name"] if ss.get("auth") else "Colab"
    my_tasks = df_tasks[df_tasks["assigned_to"].isin(["Headhunter", "Colaborador", my_name])]
    all_statuses = ["Todos"] + sorted(my_tasks["status"].unique())
    prefer_order = ["Pendiente", "En Proceso", "En Espera"]
    preferred = next((s for s in prefer_order if s in all_statuses), "Todos")
    selected_status = st.selectbox("Filtrar por Estado", all_statuses, index=all_statuses.index(preferred))
    my_tasks_filtered = my_tasks if selected_status=="Todos" else my_tasks[my_tasks["status"] == selected_status]
    if not my_tasks_filtered.empty:
        st.dataframe(
            my_tasks_filtered.rename(
                columns={"titulo":"Título", "desc":"Descripción", "due":"Vencimiento", "assigned_to": "Asignado a", "status": "Estado", "created_at": "Fecha de Creación", "priority": "Prioridad"}
            )[["Título", "Descripción", "Estado", "Prioridad", "Vencimiento", "Fecha de Creación"]],
            use_container_width=True, hide_index=True
        )
    else:
        st.info(f"No hay tareas en el estado '{selected_status}' asignadas directamente.")

def page_agent_tasks():
    st.header("Tareas Asignadas a mi Equipo")
    st.write("Esta página lista las tareas generadas por Flujos y asignadas a roles de equipo.")
    if not isinstance(ss.tasks, list) or not ss.tasks: st.write("No hay tareas pendientes en el equipo."); return
    df_tasks = pd.DataFrame(ss.tasks)
    team_tasks = df_tasks[df_tasks["assigned_to"].isin(HR_ROLES + ["Agente de Análisis"])]
    all_statuses = ["Todos"] + sorted(team_tasks["status"].unique())
    prefer_order = ["Pendiente", "En Proceso", "En Espera"]
    preferred = next((s for s in prefer_order if s in all_statuses), "Todos")
    selected_status = st.selectbox("Filtrar por Estado", all_statuses, index=all_statuses.index(preferred), key="agent_task_filter")
    team_tasks_filtered = team_tasks if selected_status=="Todos" else team_tasks[team_tasks["status"] == selected_status]
    if not team_tasks_filtered.empty:
        st.dataframe(
            team_tasks_filtered.rename(
                columns={"titulo":"Título", "desc":"Descripción", "due":"Vencimiento", "assigned_to": "Asignado a", "status": "Estado", "created_at": "Fecha de Creación", "priority": "Prioridad"}
            )[["Título", "Descripción", "Asignado a", "Estado", "Prioridad", "Vencimiento", "Fecha de Creación"]],
            use_container_width=True, hide_index=True
        )
    else:
        st.info(f"No hay tareas en el estado '{selected_status}' asignadas al equipo.")

def page_agents():
  st.header("Agentes")
  st.subheader("Crear / Editar agente")
  left, _ = st.columns([0.25, 0.75])
  with left:
    if st.button(("➕ Nuevo" if not ss.new_role_mode else "✖ Cancelar"), key="toggle_new_role"):
      ss.new_role_mode = not ss.new_role_mode
      if ss.new_role_mode:
        ss.agent_view_idx = None; ss.agent_edit_idx = None
      st.rerun()

  if ss.new_role_mode:
    st.info("Completa el formulario para crear un nuevo rol/agente.")
    with st.form("agent_new_form"):
      c1, c2 = st.columns(2)
      with c1:
        role_name  = st.text_input("Rol*", value="")
        objetivo   = st.text_input("Objetivo*", value="Identificar a los mejores profesionales para el cargo definido en el JD")
        backstory  = st.text_area("Backstory*", value="Eres un analista de RR.HH. con experiencia en análisis de documentos, CV y currículums.", height=120)
        guardrails = st.text_area("Guardrails", value="No compartas datos sensibles. Cita la fuente (CV o JD) al argumentar.", height=90)
      with c2:
        st.text_input("Modelo LLM (Evaluación)", value=LLM_IN_USE, disabled=True)
        img_src    = st.text_input("URL de imagen", value=AGENT_DEFAULT_IMAGES.get("Headhunter",""))
        perms      = st.multiselect("Permisos (quién puede editar)", ["Colaborador","Supervisor","Administrador"], default=["Supervisor","Administrador"])

      saved = st.form_submit_button("Guardar/Actualizar Agente")
      if saved:
        rn = (role_name or "").strip()
        if not rn: st.error("El campo Rol* es obligatorio.")
        else:
          ss.agents.append({ "rol": rn, "objetivo": objetivo, "backstory": backstory, "guardrails": guardrails, "herramientas": [], "llm_model": LLM_IN_USE, "image": img_src, "perms": perms, "ts": datetime.utcnow().isoformat() })
          save_agents(ss.agents)
          roles_new = sorted(list({*ss.roles, rn})); ss.roles = roles_new; save_roles(roles_new)
          st.success("Agente creado."); ss.new_role_mode = False; st.rerun()

  st.subheader("Tus agentes")
  if not ss.agents: st.info("Aún no hay agentes. Crea el primero."); return

  cols_per_row = 5
  for i in range(0, len(ss.agents), cols_per_row):
    row_agents = ss.agents[i:i+cols_per_row]
    cols = st.columns(cols_per_row)
    for j, ag in enumerate(row_agents):
      idx = i + j
      with cols[j]:
        img = ag.get("image") or AGENT_DEFAULT_IMAGES.get(ag.get("rol","Headhunter"))
        st.markdown(f'<div class="agent-card"><img src="{img}"><div class="agent-title">{ag.get("rol","—")}</div><div class="agent-sub">{ag.get("objetivo","—")}</div></div>', unsafe_allow_html=True)
        st.markdown('<div class="toolbar">', unsafe_allow_html=True)
        c1, c2, c3, c4 = st.columns(4)
        with c1:
          if st.button("👁", key=f"ag_v_{idx}", help="Ver"): ss.agent_view_idx = (None if ss.agent_view_idx == idx else idx); ss.agent_edit_idx = None; st.rerun()
        with c2:
          if st.button("✏", key=f"ag_e_{idx}", help="Editar"): ss.agent_edit_idx = (None if ss.agent_edit_idx == idx else idx); ss.agent_view_idx = None; st.rerun()
        with c3:
          if st.button("🧬", key=f"ag_c_{idx}", help="Clonar"): clone = dict(ag); clone["rol"] = f"{ag.get('rol','Agente')} (copia)"; ss.agents.append(clone); save_agents(ss.agents); st.success("Agente clonado."); st.rerun()
        with c4:
          if st.button("🗑", key=f"ag_d_{idx}", help="Eliminar"): ss.agents.pop(idx); save_agents(ss.agents); st.success("Agente eliminado."); st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

  if ss.agent_view_idx is not None and 0 <= ss.agent_view_idx < len(ss.agents):
    ag = ss.agents[ss.agent_view_idx]
    st.markdown("### Detalle del agente"); st.markdown('<div class="agent-detail">', unsafe_allow_html=True)
    c1, c2 = st.columns([0.42, 0.58])
    with c1:
      raw_img = ag.get("image") or ""; safe_img = (raw_img.strip() if isinstance(raw_img, str) and raw_img.strip() else AGENT_DEFAULT_IMAGES.get(ag.get("rol","Headhunter"), AGENT_DEFAULT_IMAGES["Headhunter"]))
      st.markdown(f'<div style="text-align:center;margin:6px 0 12px"><img src="{safe_img}" style="width:180px;height:180px;border-radius:999px;object-fit:cover;border:4px solid #F1F7FD;"></div>', unsafe_allow_html=True)
      st.caption("Modelo LLM"); st.markdown(f"<div class='badge'>🧠 {ag.get('llm_model',LLM_IN_USE)}</div>", unsafe_allow_html=True)
    with c2:
      st.text_input("Role*", value=ag.get("rol",""), disabled=True); st.text_input("Objetivo*", value=ag.get("objetivo",""), disabled=True)
      st.text_area("Backstory*", value=ag.get("backstory",""), height=120, disabled=True); st.text_area("Guardrails", value=ag.get("guardrails",""), height=90, disabled=True)
      st.caption("Permisos"); st.write(", ".join(ag.get("perms",[])) or "—")
    st.markdown('</div>', unsafe_allow_html=True)

  if ss.agent_edit_idx is not None and 0 <= ss.agent_edit_idx < len(ss.agents):
    ag = ss.agents[ss.agent_edit_idx]
    st.markdown("### Editar agente")
    with st.form(f"agent_edit_{ss.agent_edit_idx}"):
      objetivo   = st.text_input("Objetivo*", value=ag.get("objetivo","")); backstory  = st.text_area("Backstory*", value=ag.get("backstory",""), height=120)
      guardrails = st.text_area("Guardrails", value=ag.get("guardrails",""), height=90); st.text_input("Modelo LLM (Evaluación)", value=ag.get('llm_model', LLM_IN_USE), disabled=True)
      img_src      = st.text_input("URL de imagen", value=ag.get("image","")); perms        = st.multiselect("Permisos (quién puede editar)", ["Colaborador","Supervisor","Administrador"], default=ag.get("perms",["Supervisor","Administrador"]))
      if st.form_submit_button("Guardar cambios"):
        ag.update({"objetivo":objetivo,"backstory":backstory,"guardrails":guardrails, "llm_model":ag.get('llm_model', LLM_IN_USE),"image":img_src,"perms":perms})
        save_agents(ss.agents); st.success("Agente actualizado."); st.rerun()

def page_analytics():
    st.header("Analytics y KPIs Estratégicos")
    st.subheader("Visión General del Proceso")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Costo por Hire (Promedio)", "S/ 4,250", "-8% vs Q2"); c2.metric("Time to Hire (P50)", "28 días", "+2 días")
    c3.metric("Conversión (Oferta > Contratado)", "81%", "+3%"); c4.metric("Exactitud de IA (Fit)", "92%", "Modelo v2.1")
    st.markdown("---")
    col_funnel, col_time = st.columns(2)
    with col_funnel:
        st.subheader("Embudo de Conversión"); df_funnel = pd.DataFrame({"Fase": ["Recibido", "Screening RRHH", "Entrevista Gerencia", "Oferta", "Contratado"], "Candidatos": [1200, 350, 80, 25, 20]})
        df_funnel = df_funnel[df_funnel["Candidatos"] > 0]; fig_funnel = px.funnel(df_funnel, x='Candidatos', y='Fase', title="Conversión Total por Fase")
        fig_funnel.update_traces(marker=dict(color=PRIMARY)); fig_funnel.update_layout(plot_bgcolor="#FFFFFF", paper_bgcolor="rgba(0,0,0,0)", font=dict(color=TITLE_DARK), yaxis_title=None)
        st.plotly_chart(fig_funnel, use_container_width=True)
    with col_time:
        st.subheader("Tiempos del Proceso (P50 / P90)"); df_times = pd.DataFrame({"Métrica": ["Time to Interview", "Time to Offer", "Time to Hire"], "P50 (Días)": [12, 22, 28], "P90 (Días)": [20, 31, 42]})
        df_times_melted = df_times.melt(id_vars="Métrica", var_name="Percentil", value_name="Días")
        fig_time = px.bar(df_times_melted, x="Métrica", y="Días", color="Percentil", barmode="group", title="Tiempos Clave del Ciclo (P50 vs P90)", color_discrete_sequence=PLOTLY_GREEN_SEQUENCE)
        fig_time.update_layout(plot_bgcolor="#FFFFFF", paper_bgcolor="rgba(0,0,0,0)", font=dict(color=TITLE_DARK), yaxis_title="Días")
        st.plotly_chart(fig_time, use_container_width=True)
    st.markdown("---")
    col_prod, col_cost_ia = st.columns(2)
    with col_prod:
        st.subheader("Productividad del Reclutador"); df_prod = pd.DataFrame({"Reclutador": ["Admin", "Sup", "Colab", "Headhunter"], "Contratados (Últ. 90d)": [8, 5, 12, 9], "CVs Gestionados": [450, 300, 700, 620]})
        fig_prod = px.bar(df_prod, x="Reclutador", y="Contratados (Últ. 90d)", title="Contrataciones por Reclutador", color_discrete_sequence=PLOTLY_GREEN_SEQUENCE)
        fig_prod.update_layout(plot_bgcolor="#FFFFFF", paper_bgcolor="rgba(0,0,0,0)", font=dict(color=TITLE_DARK)); st.plotly_chart(fig_prod, use_container_width=True)
    with col_cost_ia:
        st.subheader("Exactitud de IA"); df_ia = pd.DataFrame({"Puesto": ["Business Analytics", "Diseñador/a UX", "Ingeniero/a", "Enfermera/o"], "Candidatos": [120, 85, 200, 310], "Fit Promedio IA": [82, 75, 88, 79]})
        fig_ia = px.scatter(df_ia, x="Candidatos", y="Fit Promedio IA", size="Candidatos", color="Puesto", title="Fit Promedio (IA) por Volumen de Puesto", color_discrete_sequence=PLOTLY_GREEN_SEQUENCE)
        fig_ia.update_layout(plot_bgcolor="#FFFFFF", paper_bgcolor="rgba(0,0,0,0)", font=dict(color=TITLE_DARK)); st.plotly_chart(fig_ia, use_container_width=True)

def page_create_task():
    st.header("Todas las Tareas")
    with st.expander("➕ Crear Tarea Manual"):
        with st.form("manual_task_form", clear_on_submit=True):
            st.markdown("**Nueva Tarea**"); new_title = st.text_input("Título de la Tarea*"); new_desc = st.text_area("Descripción")
            c1, c2, c3 = st.columns(3)
            with c1: new_due = st.date_input("Vencimiento", date.today() + timedelta(days=7))
            with c2: all_assignees = list(USERS.keys()) + DEFAULT_ROLES; new_assignee = st.selectbox("Asignar a", sorted(list(set(all_assignees))), index=0)
            with c3: new_prio = st.selectbox("Prioridad", TASK_PRIORITIES, index=1)
            if st.form_submit_button("Guardar Tarea"):
                if new_title.strip(): create_manual_task(new_title, new_desc, new_due, new_assignee, new_prio); st.success(f"Tarea '{new_title}' creada."); st.rerun()
                else: st.error("El Título es obligatorio.")

    st.info("Muestra todas las tareas registradas."); tasks_list = ss.tasks
    if not isinstance(tasks_list, list): st.error("Error: Lista de tareas no válida."); tasks_list = []
    if not tasks_list: st.write("No hay tareas registradas."); return

    st.markdown("---"); fc1, fc2 = st.columns([1, 1.5])
    with fc1: filter_category = st.selectbox("Filtrar por", ["Todas las tareas", "Toda la cola (Pendientes)", "Asignadas a HR"], key="task_category_filter", label_visibility="collapsed")
    with fc2: filter_search = st.text_input("Buscar tareas...", key="task_search_filter", placeholder="Buscar tareas...", label_visibility="collapsed")

    tasks_to_show = tasks_list
    if filter_category == "Toda la cola (Pendientes)": tasks_to_show = [t for t in tasks_to_show if t.get("status") in ["Pendiente", "En Proceso"]]
    elif filter_category == "Asignadas a HR": tasks_to_show = [t for t in tasks_to_show if t.get("assigned_to") in HR_ROLES]
    if filter_search: search_low = filter_search.lower(); tasks_to_show = [t for t in tasks_to_show if search_low in (t.get("titulo") or "").lower()]
    if not tasks_to_show: st.info(f"No hay tareas que coincidan."); return

    col_w = [0.9, 2.2, 2.4, 1.6, 1.4, 1.6, 1.0, 1.2, 1.6]; headers = ["Id", "Nombre", "Descripción", "Asignado a", "Creado el", "Vencimiento", "Prioridad", "Estado", "Acciones"]
    h_cols = st.columns(col_w); [h_cols[i].markdown(f"**{h}**") for i, h in enumerate(headers)]; st.markdown("<hr style='border:1px solid #E3EDF6; opacity:.6;'/>", unsafe_allow_html=True)

    for task in tasks_to_show:
        t_id = task.get("id") or str(uuid.uuid4()); task["id"] = t_id
        c_cols = st.columns(col_w)
        with c_cols[0]: short = (t_id[:5] + "…") if len(t_id) > 6 else t_id; st.caption(short)
        with c_cols[1]: st.markdown(f"**{task.get('titulo','—')}**")
        with c_cols[2]: st.caption(task.get("desc","—"))
        with c_cols[3]: st.markdown(f"`{task.get('assigned_to','—')}`")
        with c_cols[4]: st.markdown(task.get("created_at","—"))
        with c_cols[5]: st.markdown(task.get("due","—"))
        with c_cols[6]: st.markdown(_priority_pill(task.get("priority","Media")), unsafe_allow_html=True)
        with c_cols[7]: st.markdown(_status_pill(task.get("status","Pendiente")), unsafe_allow_html=True)

        def _handle_action_change(task_id):
            action = ss[f"accion_{task_id}"]; task_to_update = next((t for t in ss.tasks if t.get("id") == task_id), None)
            if not task_to_update: return
            ss.confirm_delete_id = None; ss.show_assign_for = None; ss.expanded_task_id = None
            if action == "Ver detalle": ss.expanded_task_id = task_id
            elif action == "Asignar tarea": ss.show_assign_for = task_id
            elif action == "Tomar tarea": current_user = (ss.auth["name"] if ss.get("auth") else "Admin"); task_to_update["assigned_to"] = current_user; task_to_update["status"] = "En Proceso"; save_tasks(ss.tasks); st.toast("Tarea tomada."); st.rerun()
            elif action == "Eliminar": ss.confirm_delete_id = task_id

        with c_cols[8]: st.selectbox("Acciones", ["Selecciona…", "Ver detalle", "Asignar tarea", "Tomar tarea", "Eliminar"], key=f"accion_{t_id}", label_visibility="collapsed", on_change=_handle_action_change, args=(t_id,))

        if ss.get("confirm_delete_id") == t_id:
            b1, b2, _ = st.columns([1.0, 1.0, 7.8])
            with b1:
                if st.button("Eliminar permanentemente", key=f"del_confirm_{t_id}", type="primary", use_container_width=True):
                    ss.tasks = [t for t in ss.tasks if t.get("id") != t_id]; save_tasks(ss.tasks); ss.confirm_delete_id = None; st.warning("Tarea eliminada."); st.rerun()
            with b2:
                if st.button("Cancelar", key=f"del_cancel_{t_id}", use_container_width=True): ss.confirm_delete_id = None; st.rerun()

        if ss.show_assign_for == t_id:
            a1, a2, a3, a4, _ = st.columns([1.6, 1.6, 1.2, 1.0, 3.0])
            with a1: assign_type = st.selectbox("Tipo", ["En Espera", "Equipo", "Usuario"], key=f"type_{t_id}", index=2)
            with a2:
                if assign_type == "En Espera": nuevo_assignee = "En Espera"; st.text_input("Asignado a", "En Espera", key=f"val_esp_{t_id}", disabled=True)
                elif assign_type == "Equipo": nuevo_assignee = st.selectbox("Equipo", HR_ROLES + ["Agente de Análisis"], key=f"val_eq_{t_id}")
                else: nuevo_assignee = st.selectbox("Usuario", ["Headhunter", "Colab", "Sup", "Admin"], key=f"val_us_{t_id}")
            with a3: cur_p = task.get("priority", "Media"); idx_p = TASK_PRIORITIES.index(cur_p) if cur_p in TASK_PRIORITIES else 1; nueva_prio = st.selectbox("Prioridad", TASK_PRIORITIES, key=f"prio_{t_id}", index=idx_p)
            with a4:
                if st.button("Guardar", key=f"btn_assign_{t_id}", use_container_width=True):
                    task_to_update = next((t for t in ss.tasks if t.get("id") == t_id), None)
                    if task_to_update:
                        task_to_update["assigned_to"] = nuevo_assignee; task_to_update["priority"] = nueva_prio
                        if assign_type == "En Espera": task_to_update["status"] = "En Espera"
                        elif task_to_update["status"] == "En Espera": task_to_update["status"] = "Pendiente"
                        save_tasks(ss.tasks); ss.show_assign_for = None; st.success("Cambios guardados."); st.rerun()
        st.markdown("<hr style='border:1px solid #E3EDF6; opacity:.35;'/>", unsafe_allow_html=True)

    task_id_for_dialog = ss.get("expanded_task_id")
    if task_id_for_dialog:
        task_data = next((t for t in ss.tasks if t.get("id") == task_id_for_dialog), None)
        if task_data:
            try:
                with st.dialog("Detalle de Tarea", width="large"):
                    st.markdown(f"### {task_data.get('titulo', 'Sin Título')}")
                    c1, c2 = st.columns(2)
                    with c1: st.markdown("**Información Principal**"); st.markdown(f"**Asignado a:** `{task_data.get('assigned_to', 'N/A')}`"); st.markdown(f"**Vencimiento:** `{task_data.get('due', 'N/A')}`"); st.markdown(f"**Creado el:** `{task_data.get('created_at', 'N/A')}`")
                    with c2: st.markdown("**Estado y Prioridad**"); st.markdown(f"**Estado:**"); st.markdown(_status_pill(task_data.get('status', 'Pendiente')), unsafe_allow_html=True); st.markdown(f"**Prioridad:**"); st.markdown(_priority_pill(task_data.get('priority', 'Media')), unsafe_allow_html=True)
                    context = task_data.get("context");
                    if context and ("candidate_name" in context or "role" in context):
                        st.markdown("---"); st.markdown("**Contexto del Flujo**")
                        if "candidate_name" in context: st.markdown(f"**Postulante:** {context['candidate_name']}")
                        if "role" in context: st.markdown(f"**Puesto:** {context['role']}")
                    st.markdown("---"); st.markdown("**Descripción:**"); st.markdown(task_data.get('desc', 'Sin descripción.'))
                    st.markdown("---"); st.markdown("**Actividad Reciente:**"); st.markdown("- *No hay actividad registrada.*")
                    with st.form("comment_form"): st.text_area("Comentarios", placeholder="Añadir un comentario...", key="task_comment"); submitted = st.form_submit_button("Enviar Comentario"); #if submitted: st.toast("Comentario (aún no) guardado.")
                    if st.button("Cerrar", key="close_dialog"): ss.expanded_task_id = None; st.rerun()
            except Exception as e: st.error(f"Error al mostrar detalles: {e}"); ss.expanded_task_id = None
        else: ss.expanded_task_id = None

# =========================================================
# ROUTER
# =========================================================
ROUTES = {
  "publicacion_sourcing": page_def_carga, "puestos": page_puestos, "eval": page_eval,
  "pipeline": page_pipeline, "interview": page_interview, "offer": page_offer,
  "onboarding": page_onboarding, "hh_tasks": page_hh_tasks, "agents": page_agents,
  "flows": page_flows, "agent_tasks": page_agent_tasks, "analytics": page_analytics,
  "create_task": page_create_task,
}

# =========================================================
# APP
# =========================================================
if __name__ == "__main__":
    if require_auth():
        render_sidebar()
        ROUTES.get(ss.section, page_def_carga)()
