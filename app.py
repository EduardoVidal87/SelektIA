# app.py
# -*- coding: utf-8 -*-
from __future__ import annotations
import io, re, base64
from pathlib import Path
from datetime import date, datetime, timedelta

import streamlit as st
import pandas as pd
import plotly.express as px
from PyPDF2 import PdfReader

# -----------------------------------------------------------------------------
# Configuración base
# -----------------------------------------------------------------------------
st.set_page_config(page_title="SelektIA", page_icon="🧠", layout="wide")

# -----------------------------------------------------------------------------
# Estilos (sidebar + títulos)
# -----------------------------------------------------------------------------
PRIMARY = "#00CD78"              # Verde
SIDEBAR_BG = "#0E1828"           # Fondo sidebar
TEXT_LIGHT = "#FFFFFF"

CSS_SIDEBAR = f"""
:root {{
  --primary: {PRIMARY};
  --sidebar-bg: {SIDEBAR_BG};
  --text: {TEXT_LIGHT};
}}

[data-testid="stSidebar"] {{
  background: var(--sidebar-bg) !important;
  color: var(--text) !important;
}}

[data-testid="stSidebar"] .wayki-logo {{
  display:flex; align-items:center; gap:.5rem; margin:14px 10px 4px 10px;
}}
[data-testid="stSidebar"] .wayki-brand {{
  font-weight:800; font-size:36px; color:var(--primary); line-height:1;
}}
[data-testid="stSidebar"] .wayki-powered {{
  margin:-4px 10px 10px 10px; font-size:12px; opacity:.85; color:#A6F3D3;
}}

.sidebar-section-title {{
  margin:14px 10px 6px; 
  font-size:12px; 
  letter-spacing:.3px;
  font-weight:800; 
  color: var(--primary);
}}

.sidebar-link, .stButton>button.sidebar-link {{
  width:100%;
  text-align:left;
  background: var(--sidebar-bg) !important;    /* mismo color que fondo */
  color: var(--text) !important;
  border:1px solid var(--sidebar-bg) !important; /* borde igual al fondo */
  border-radius:10px !important;
  padding:.6rem .8rem !important;
  margin:6px 10px !important;
}}
.sidebar-link:hover {{
  border-color:#172741 !important;
}}
.page-title h2, .page-title h1 {{
  color:#142433; font-weight:800;
}}
/* Botón verde global */
.stButton>button:not(.sidebar-link) {{
  background: {PRIMARY} !important; color:#062018 !important; border:0; 
  border-radius:10px !important; font-weight:700 !important; padding:.5rem 1rem;
}}
"""
st.markdown(f"<style>{CSS_SIDEBAR}</style>", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# Estado inicial demo
# -----------------------------------------------------------------------------
if "route" not in st.session_state:
    st.session_state.route = "define"

if "positions" not in st.session_state:
    st.session_state.positions = pd.DataFrame([
        {"ID":"10,645,194","Puesto":"Desarrollador/a Backend (Python)","Días Abierto":3,"Leads":1800,"Nuevos":115,"Recruiter Screen":35,"HM Screen":7,"Entrevista Telefónica":14,"Entrevista Presencial":15,"Ubicación":"Lima, Perú","Hiring Manager":"Rivers Brykson","Estado":"Abierto"},
        {"ID":"10,376,415","Puesto":"VP de Marketing","Días Abierto":28,"Leads":8100,"Nuevos":1,"Recruiter Screen":15,"HM Screen":35,"Entrevista Telefónica":5,"Entrevista Presencial":7,"Ubicación":"Santiago, Chile","Hiring Manager":"Angela Cruz","Estado":"Abierto"},
        {"ID":"10,376,646","Puesto":"Planner de Demanda","Días Abierto":28,"Leads":2300,"Nuevos":26,"Recruiter Screen":3,"HM Screen":8,"Entrevista Telefónica":6,"Entrevista Presencial":3,"Ubicación":"Ciudad de México, MX","Hiring Manager":"Rivers Brykson","Estado":"Abierto"},
    ])

if "candidates" not in st.session_state:
    st.session_state.candidates = []  # se llena desde Definición & Carga

if "assistants" not in st.session_state:
    st.session_state.assistants = []

# -----------------------------------------------------------------------------
# Utilidades
# -----------------------------------------------------------------------------
def goto(route: str):
    st.session_state.route = route
    st.rerun()

def extract_text_from_file(uploaded_file) -> str:
    try:
        suffix = Path(uploaded_file.name).suffix.lower()
        if suffix == ".pdf":
            pdf_reader = PdfReader(io.BytesIO(uploaded_file.read()))
            text = ""
            for p in pdf_reader.pages:
                text += p.extract_text() or ""
            return text
        else:
            return uploaded_file.read().decode("utf-8", errors="ignore")
    except Exception as e:
        st.error(f"Error al leer '{uploaded_file.name}': {e}")
        return ""

def simple_score(cv_text: str, jd: str, keywords: str) -> tuple[int, str]:
    base = 0
    reasons = []
    text_low = cv_text.lower()
    jd_low = jd.lower()

    hits = 0
    kws = [k.strip().lower() for k in keywords.split(",") if k.strip()]
    for k in kws:
        if k and k in text_low:
            hits += 1
    if kws:
        pct_k = hits/len(kws)
        base += int(pct_k*70)
        coincid = ", ".join([k for k in kws if k in text_low])[:120]
        reasons.append(f"{hits}/{len(kws)} keywords encontradas — Coincidencias: {coincid}")

    jd_terms = [t for t in set(jd_low.split()) if len(t) > 3]
    match_terms = sum(1 for t in jd_terms if t in text_low)
    if jd_terms:
        pct_jd = match_terms/len(jd_terms)
        base += int(pct_jd*30)
        reasons.append("Coincidencias con el JD (aprox.)")

    base = max(0, min(100, base))
    return base, " — ".join(reasons)

def parse_meta_from_text(txt: str) -> dict:
    """Parseo simple: intenta obtener años de experiencia, roles, universidad/año y skills."""
    meta = {}
    # años de experiencia (heurística)
    m = re.search(r"(\d+)\+?\s*(?:años|years)\s+de\s+experiencia", txt.lower())
    if m:
        meta["years_exp"] = m.group(1)
    else:
        # si aparecen varios años, tomar el mayor (crudo)
        nums = [int(n) for n in re.findall(r"\b(\d{1,2})\s*(?:años|years)\b", txt.lower())]
        meta["years_exp"] = str(max(nums)) if nums else "—"

    # roles (tomar palabras capitalizadas seguidas de Engineer/Developer/Manager/etc.)
    roles = re.findall(r"(?i)(Senior|Lead|Principal|Software|Cloud|Data|Nurse|Enfermer[oa]|Médic[oa]|Tecnólog[oa]|Recepcionista|Químic[oa])(?:[^\\n\\r]{{0,40}})", txt)
    meta["roles"] = list(dict.fromkeys([r.strip() for r in roles]))[:5] if roles else []

    # universidad y año
    uni = re.search(r"(?i)(Universidad|University)[^\\n\\r]{{0,60}}", txt)
    year = re.search(r"\b(19|20)\d{{2}}\b", txt)
    meta["university"] = uni.group(0).strip() if uni else "—"
    meta["grad_year"] = year.group(0) if year else "—"

    # skills (lista simple: palabras comunes)
    skill_list = []
    for k in ["HIS","SAP IS-H","BLS","ACLS","IAAS","educación al paciente","seguridad del paciente","protocolos",
              "python","sql","gestión","excel","linux","cloud"]:
        if re.search(rf"(?i)\b{re.escape(k)}\b", txt):
            skill_list.append(k)
    meta["skills"] = skill_list

    # última actualización (placeholder: hoy)
    meta["last_update"] = date.today().isoformat()
    return meta

def pdf_viewer_pdfjs(file_bytes: bytes, height=520, scale=1.1):
    b64 = base64.b64encode(file_bytes).decode("utf-8")
    pdfjs = "https://mozilla.github.io/pdf.js/web/viewer.html?file="
    src = f"{pdfjs}data:application/pdf;base64,{b64}#zoom={int(scale*100)}"
    st.markdown(
        f'<iframe src="{src}" style="width:100%;height:{height}px;border:0" title="PDF Viewer"></iframe>',
        unsafe_allow_html=True
    )

# -----------------------------------------------------------------------------
# Sidebar (navegación)
# -----------------------------------------------------------------------------
def sidebar_nav():
    with st.sidebar:
        st.markdown(
            '<div class="wayki-logo"><span class="wayki-brand">SelektIA</span></div>'
            '<div class="wayki-powered">Powered by Wayki Consulting</div>',
            unsafe_allow_html=True
        )

        st.markdown('<div class="sidebar-section-title">DASHBOARD</div>', unsafe_allow_html=True)
        st.button("Bienvenido a Selektia", key="btn_dash", on_click=goto, args=("dashboard",), use_container_width=True, type="secondary")

        st.markdown('<div class="sidebar-section-title">ASISTENTE IA</div>', unsafe_allow_html=True)
        st.button("Flujos", key="btn_flows", on_click=goto, args=("flows",), use_container_width=True, type="secondary")
        st.button("Agentes", key="btn_agents", on_click=goto, args=("agents",), use_container_width=True, type="secondary")
        st.button("Tareas de Agente", key="btn_agent_tasks", on_click=goto, args=("agent_tasks",), use_container_width=True, type="secondary")
        st.button("Asistente IA", key="btn_ai", on_click=goto, args=("assistant",), use_container_width=True, type="secondary")

        st.markdown('<div class="sidebar-section-title">PROCESO DE SELECCIÓN</div>', unsafe_allow_html=True)
        st.button("Definición & Carga", key="btn_define", on_click=goto, args=("define",), use_container_width=True, type="secondary")
        st.button("Puestos", key="btn_positions", on_click=goto, args=("positions",), use_container_width=True, type="secondary")
        st.button("Evaluación de CVs", key="btn_eval", on_click=goto, args=("eval",), use_container_width=True, type="secondary")
        st.button("Pipeline de Candidatos", key="btn_pipe", on_click=goto, args=("pipeline",), use_container_width=True, type="secondary")
        st.button("Entrevista (Gerencia)", key="btn_mgr", on_click=goto, args=("interview",), use_container_width=True, type="secondary")
        st.button("Tareas del Headhunter", key="btn_hh", on_click=goto, args=("hh_tasks",), use_container_width=True, type="secondary")
        st.button("Oferta", key="btn_offer", on_click=goto, args=("offer",), use_container_width=True, type="secondary")
        st.button("Onboarding", key="btn_onboard", on_click=goto, args=("onboarding",), use_container_width=True, type="secondary")

        st.markdown('<div class="sidebar-section-title">ANALYTICS</div>', unsafe_allow_html=True)
        st.button("Abrir Analytics", key="btn_analytics", on_click=goto, args=("analytics",), use_container_width=True, type="secondary")

        st.markdown('<div class="sidebar-section-title">ACCIONES</div>', unsafe_allow_html=True)
        st.button("Crear tarea", key="btn_newtask", on_click=goto, args=("create_task",), use_container_width=True, type="secondary")

sidebar_nav()

# -----------------------------------------------------------------------------
# Páginas
# -----------------------------------------------------------------------------
def page_dashboard():
    st.markdown('<div class="page-title"><h2>Bienvenido a Selektia</h2></div>', unsafe_allow_html=True)
    st.write("Resumen rápido del estado de procesos, KPIs y atajos.")

# ----- Asistente IA -----------------------------------------------------------
def page_assistant():
    st.markdown('<div class="page-title"><h2>Asistente IA</h2></div>', unsafe_allow_html=True)

    colL, colR = st.columns([7,5], vertical_alignment="top")

    with colL:
        role = st.selectbox("Rol*", ["Headhunter","Coordinador/a RR.HH.","Admin RR.HH."], index=0)
        goal = st.text_input("Objetivo*", "Identificar a los mejores profesionales para el cargo definido en el JD")
        backstory = st.text_area("Backstory*", "Eres un analista de RR.HH. con experiencia en análisis de documentos, CV y currículums.", height=120)
        guardrails = st.text_area("Guardrails", "No compartas datos sensibles. Cita la fuente (CV o JD) al argumentar.", height=90)

        st.caption("Herramientas habilitadas")
        tag_cols = st.columns(2)
        with tag_cols[0]:
            pdf_tool = st.checkbox("Parser de PDF", value=True)
        with tag_cols[1]:
            rec_tool = st.checkbox("Recomendador de candidatos", value=True)

        if st.button("Crear/Actualizar Asistente", use_container_width=True, type="primary"):
            st.session_state.assistants.append({
                "rol": role,
                "objetivo": goal,
                "backstory": backstory,
                "guardrails": guardrails,
                "tools": {"pdf": pdf_tool, "reco": rec_tool}
            })
            st.success("Asistente guardado. Esta configuración guiará la evaluación de CVs.")

    with colR:
        st.subheader("Permisos y alcance")
        st.markdown("- **RLS** por puesto: el asistente ve candidatos del puesto/rol asignado.")
        st.markdown("- Acciones según rol (p.ej., **HH no aprueba ofertas**).")
        st.markdown("- **Auditoría**: toda acción queda registrada.")

    if st.session_state.assistants:
        st.markdown("### Asistentes creados")
        cards = st.session_state.assistants[-6:]
        cols = st.columns(3)
        icons = {"Headhunter":"🕵️‍♂️", "Coordinador/a RR.HH.":"🧭", "Admin RR.HH.":"🛡️"}
        for i, a in enumerate(cards):
            with cols[i % 3]:
                st.markdown(
                    f"""
                    <div style="border:1px solid #E5EEF8;border-radius:14px;padding:14px;margin-bottom:12px;background:#fff">
                      <div style="font-size:44px">{icons.get(a['rol'],'🤖')}</div>
                      <div style="font-weight:800;margin-top:4px">{a['rol']}</div>
                      <div style="font-size:12px;opacity:.75">{a['objetivo']}</div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

# ----- Definición & Carga -----------------------------------------------------
def page_definicion_y_carga():
    st.markdown('<div class="page-title"><h2>Definición & Carga</h2></div>', unsafe_allow_html=True)

    puesto = st.selectbox("Puesto", ["Enfermera/o Asistencial","Tecnólogo/a Médico","Recepcionista de Admisión","Médico/a General","Químico/a Farmacéutico/a"], index=0)
    jd_text = st.text_area("Descripción del puesto (texto libre) — JD", height=140)
    kw_text = st.text_area("Palabras clave (coma separada)", "HIS, SAP IS-H, BLS, ACLS, IAAS, educación al paciente, seguridad del paciente, protocolos")

    st.subheader("Subir CVs (PDF o TXT)")
    files = st.file_uploader("Arrastra o haz clic para subir", type=["pdf","txt"], accept_multiple_files=True)

    if st.button("Procesar archivos", disabled=not files):
        st.session_state.candidates = []
        for f in files:
            raw = f.read()
            f.seek(0)
            txt = extract_text_from_file(f)
            score, reasons = simple_score(txt, jd_text, kw_text)
            meta = parse_meta_from_text(txt)
            st.session_state.candidates.append({
                "Name": f.name, "Score": score, "Reasons": reasons, "_bytes": raw,
                "_is_pdf": Path(f.name).suffix.lower()==".pdf", "stage": "Leads", "meta": meta
            })
        st.success(f"{len(st.session_state.candidates)} CV(s) procesados.")
        goto("eval")

# ----- Puestos ----------------------------------------------------------------
def page_puestos():
    st.markdown('<div class="page-title"><h2>Puestos</h2></div>', unsafe_allow_html=True)
    st.dataframe(
        st.session_state.positions[
            ["Puesto","Días Abierto","Leads","Nuevos","Recruiter Screen","HM Screen","Entrevista Telefónica","Entrevista Presencial","Ubicación","Hiring Manager","Estado","ID"]
        ],
        use_container_width=True, height=420
    )

# ----- Evaluación de CVs ------------------------------------------------------
def page_evaluacion():
    st.markdown('<div class="page-title"><h2>Resultados de evaluación</h2></div>', unsafe_allow_html=True)
    if not st.session_state.candidates:
        st.info("Carga CVs en **Definición & Carga**.")
        return
    df = pd.DataFrame(st.session_state.candidates).sort_values("Score", ascending=False)
    st.dataframe(df[["Name","Score","Reasons"]], use_container_width=True, height=240)

    colors = ["#33FFAC" if s>=60 else "#E9F3FF" for s in df["Score"]]
    fig = px.bar(df, x="Name", y="Score", title="Comparación de puntajes")
    fig.update_traces(marker_color=colors)
    fig.update_layout(plot_bgcolor="#fff", paper_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("### Visor de CV (PDF/TXT)")
    names = df["Name"].tolist()
    pick = st.selectbox("Elige un candidato", names, label_visibility="collapsed")
    row = df[df["Name"]==pick].iloc[0]
    if row["_is_pdf"]:
        pdf_viewer_pdfjs(row["_bytes"], height=480, scale=1.1)
        st.download_button(f"Descargar {pick}", data=row["_bytes"], file_name=pick, mime="application/pdf")
    else:
        st.info(f"'{pick}' es TXT. Mostrando contenido abajo:")
        st.text_area("Contenido", value=row.get("_bytes", b"").decode("utf-8", errors="ignore"), height=400, label_visibility="collapsed")

# ----- Pipeline de Candidatos -------------------------------------------------
def move_to_interview(idx: int):
    if "candidates" in st.session_state and 0 <= idx < len(st.session_state.candidates):
        st.session_state.candidates[idx]["stage"] = "Entrevista (Gerencia)"
        st.session_state.candidates[idx]["moved_ts"] = pd.Timestamp.utcnow().isoformat()
    st.session_state.route = "interview"
    st.rerun()

def page_pipeline():
    st.markdown('<div class="page-title"><h2>Pipeline de Candidatos</h2></div>', unsafe_allow_html=True)
    if not st.session_state.candidates:
        st.info("Sube CVs desde **Definición & Carga** para poblar el pipeline.")
        return

    df = pd.DataFrame(st.session_state.candidates)
    df_sorted = df.sort_values("Score", ascending=False).reset_index(drop=True)

    left, right = st.columns([6,6], vertical_alignment="top")

    with left:
        st.markdown("#### Candidatos")
        st.dataframe(df_sorted[["Name","Score","stage"]].rename(columns={"stage":"Etapa"}), use_container_width=True, height=370)

    with right:
        st.markdown("#### Detalle del candidato")
        names = df_sorted["Name"].tolist()
        pick = st.selectbox("Selecciona un candidato", names, label_visibility="collapsed")
        row_sorted = df_sorted[df_sorted["Name"]==pick].iloc[0]
        idx_source = int(df.index[df["Name"]==pick][0])

        meta = st.session_state.candidates[idx_source].get("meta", {})
        exp = meta.get("years_exp","—")
        cargos = ", ".join(meta.get("roles", [])[:3]) or "—"
        uni = meta.get("university","—")
        egreso = meta.get("grad_year","—")
        skills = ", ".join(meta.get("skills", [])[:8]) or "—"
        last_upd = meta.get("last_update","—")

        st.write(f"**Match estimado:** {row_sorted['Score']}%")
        st.write(f"**Años de experiencia:** {exp}")
        st.write(f"**Últimos cargos:** {cargos}")
        st.write(f"**Universidad / Año:** {uni} — {egreso}")
        st.write(f"**Skills:** {skills}")
        st.caption(f"Última actualización del CV: {last_upd}")

        c1, c2 = st.columns(2)
        with c1:
            st.button("Mover a Entrevista (Gerencia)", key=f"mv_{idx_source}", on_click=move_to_interview, args=(idx_source,), use_container_width=True)
        with c2:
            st.button("Añadir nota 'Buen encaje'", key=f"note_{idx_source}", use_container_width=True)

# ----- Entrevista (Gerencia) --------------------------------------------------
def page_entrevista_gerencia():
    st.markdown('<div class="page-title"><h2>Entrevista (Gerencia)</h2></div>', unsafe_allow_html=True)
    df = pd.DataFrame(st.session_state.candidates)
    if df.empty:
        st.info("No hay candidatos.")
        return
    sub = df[df["stage"]=="Entrevista (Gerencia)"]
    if sub.empty:
        st.info("Aún no moviste candidatos a Entrevista (Gerencia).")
        return
    st.markdown("#### Candidatos en entrevista")
    st.dataframe(sub[["Name","Score","stage"]], use_container_width=True, height=260)
    st.selectbox("Headhunter asignado", ["Carla P.","Luis V.","Andrea R."], index=0)
    st.button("Marcar 'Entrevista realizada'", use_container_width=True)

# ----- Tareas del Headhunter --------------------------------------------------
def page_tareas_headhunter():
    st.markdown('<div class="page-title"><h2>Tareas del Headhunter</h2></div>', unsafe_allow_html=True)
    df = pd.DataFrame(st.session_state.candidates)
    if df.empty:
        st.info("No hay candidatos.")
        return
    for i, c in enumerate(st.session_state.candidates):
        with st.expander(f"{c['Name']} — {c.get('stage','-')}"):
            col1,col2,col3 = st.columns(3)
            done_contact = col1.checkbox("Contacto hecho", key=f"ct_{i}")
            done_sched   = col2.checkbox("Entrevista agendada", key=f"sc_{i}")
            done_fb      = col3.checkbox("Feedback recibido", key=f"fb_{i}")
            notes = st.text_area("Notas (3 fortalezas, 2 riesgos, pretensión salarial, disponibilidad):", key=f"nt_{i}")
            adj = st.file_uploader("Adjuntos (BLS/ACLS, colegiatura)", type=["pdf","png","jpg"], key=f"ad_{i}", accept_multiple_files=True)
            st.button("Enviar a Comité", key=f"com_{i}")

# ----- Oferta -----------------------------------------------------------------
def page_oferta():
    st.markdown('<div class="page-title"><h2>Oferta</h2></div>', unsafe_allow_html=True)
    col1,col2 = st.columns(2)
    with col1:
        puesto = st.text_input("Puesto", "Enfermera/o Asistencial")
        ubic = st.text_input("Ubicación", "Lima, Perú")
        modalidad = st.selectbox("Modalidad", ["Presencial","Híbrido","Remoto"], index=0)
        contrato = st.selectbox("Tipo de contrato", ["Indeterminado","Plazo fijo","Servicio (honorarios)"], index=0)
        salario = st.text_input("Salario (rango y neto)", "S/ 3,500 – 4,000 neto")
        beneficios = st.text_input("Bonos/beneficios", "Alimentación, EPS")
    with col2:
        f_inicio = st.date_input("Fecha de inicio", value=date.today()+timedelta(days=14))
        f_caduca = st.date_input("Fecha de caducidad de oferta", value=date.today()+timedelta(days=7))
        aprobadores = st.multiselect("Aprobadores", ["Gerencia","Legal","Finanzas"])
        if st.button("Generar oferta (PDF)"):
            st.success("Oferta generada (simulado).")
        st.button("Enviar")
        st.button("Registrar contraoferta")
        if st.button("Marcar aceptada"):
            st.success("Propuesta aceptada. Se crearán tareas de Onboarding.")
            goto("onboarding")

# ----- Onboarding -------------------------------------------------------------
def page_onboarding():
    st.markdown('<div class="page-title"><h2>Onboarding</h2></div>', unsafe_allow_html=True)
    st.markdown("Checklist y responsables con recordatorios por SLA.")
    df = pd.DataFrame([
        {"Tarea":"Contrato firmado","SLA":"48 h","Responsable":"Legal","Estado":"Pendiente"},
        {"Tarea":"Documentos completos","SLA":"72 h","Responsable":"RR.HH.","Estado":"Pendiente"},
        {"Tarea":"Usuario/email creado","SLA":"24 h","Responsable":"TI","Estado":"Pendiente"},
        {"Tarea":"Acceso SAP IS-H","SLA":"24–48 h","Responsable":"TI","Estado":"Pendiente"},
        {"Tarea":"Examen médico","SLA":"Agenda","Responsable":"Salud Ocup.","Estado":"Pendiente"},
        {"Tarea":"Inducción día 1","SLA":"Día 1","Responsable":"RR.HH.","Estado":"Pendiente"},
        {"Tarea":"EPP/Uniforme","SLA":"Día 1","Responsable":"Almacén","Estado":"Pendiente"},
        {"Tarea":"Plan 30-60-90","SLA":"Semana 1","Responsable":"Jefe Directo","Estado":"Pendiente"},
    ])
    st.dataframe(df, use_container_width=True, height=360)

# ----- Analytics / Flujos / Agentes / Tareas Agente / Crear Tarea -------------
def page_analytics():
    st.markdown('<div class="page-title"><h2>Analytics</h2></div>', unsafe_allow_html=True)
    st.info("Aquí irán paneles y gráficos de KPIs.")

def page_flows():
    st.markdown('<div class="page-title"><h2>Flujos</h2></div>', unsafe_allow_html=True)
    st.info("Gestión de flujos del Asistente IA.")

def page_agents():
    st.markdown('<div class="page-title"><h2>Agentes</h2></div>', unsafe_allow_html=True)
    st.info("Listado de agentes IA configurados.")

def page_agent_tasks():
    st.markdown('<div class="page-title"><h2>Tareas de Agente</h2></div>', unsafe_allow_html=True)
    st.info("Cola de tareas ejecutadas por los agentes.")

def page_create_task():
    st.markdown('<div class="page-title"><h2>Crear tarea</h2></div>', unsafe_allow_html=True)
    st.text_input("Título")
    st.text_area("Descripción")
    st.date_input("Fecha límite", value=date.today()+timedelta(days=2))
    st.button("Guardar")

# -----------------------------------------------------------------------------
# Router
# -----------------------------------------------------------------------------
route = st.session_state.route
if route == "dashboard":
    page_dashboard()
elif route == "assistant":
    page_assistant()
elif route == "define":
    page_definicion_y_carga()
elif route == "positions":
    page_puestos()
elif route == "eval":
    page_evaluacion()
elif route == "pipeline":
    page_pipeline()
elif route == "interview":
    page_entrevista_gerencia()
elif route == "hh_tasks":
    page_tareas_headhunter()
elif route == "offer":
    page_oferta()
elif route == "onboarding":
    page_onboarding()
elif route == "analytics":
    page_analytics()
elif route == "flows":
    page_flows()
elif route == "agents":
    page_agents()
elif route == "agent_tasks":
    page_agent_tasks()
elif route == "create_task":
    page_create_task()
else:
    page_definicion_y_carga()
