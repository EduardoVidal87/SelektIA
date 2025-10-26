# app.py
# -*- coding: utf-8 -*-

import io, base64, re, json, random, zipfile
from pathlib import Path
from datetime import datetime, date, timedelta

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from PyPDF2 import PdfReader

# =========================================================
# PALETA / CONST (no tocar look & feel)
# =========================================================
PRIMARY    = "#00CD78"         # <- color marca (usado en los charts)
SIDEBAR_BG = "#0E192B"
SIDEBAR_TX = "#B9C7DF"
BODY_BG    = "#F7FBFF"
CARD_BG    = "#0E192B"
TITLE_DARK = "#142433"

BAR_DEFAULT = "#E9F3FF"
BAR_GOOD    = "#33FFAC"

JOB_BOARDS  = ["laborum.pe","Computrabajo","Bumeran","Indeed","LinkedIn Jobs"]

# =========================================================
# ESTILOS GLOBALES
# =========================================================
st.set_page_config(page_title="SelektIA", layout="wide")
GLOBAL_CSS = f"""
<style>
/* Body + sidebar */
.stApp {{ background:{BODY_BG}; }}
section[data-testid="stSidebar"] {{ background:{SIDEBAR_BG}; color:{SIDEBAR_TX}; }}
.sidebar-brand .brand-title {{ color:#fff; font-weight:700; font-size:20px; }}
.sidebar-brand .brand-sub {{ color:{SIDEBAR_TX}; font-size:12px; margin-top:-4px; }}

h1, h2, h3, h4, h5 {{ color:{TITLE_DARK}; }}

.card {{
  background:#FFFFFF; border-radius:12px; padding:16px;
  border:1px solid rgba(20,36,51,.06); box-shadow:0 1px 3px rgba(0,0,0,.06),0 1px 2px rgba(0,0,0,.04);
}}
.kpi .value {{ font-size:28px; font-weight:800; color:{TITLE_DARK}; }}
.kpi .sub   {{ font-size:12px; color:#57708A; }}

.badge {{
  display:inline-flex; align-items:center; gap:8px;
  background:#fff; border:1px solid #e8eef7; color:#4d5b6a; border-radius:999px; padding:6px 10px; font-size:12px;
}}
.badge .dot {{ width:8px; height:8px; border-radius:50%; background:{PRIMARY}; display:inline-block; }}
</style>
"""
st.markdown(GLOBAL_CSS, unsafe_allow_html=True)

# =========================================================
# DATOS DE EJEMPLO Y UTILIDADES
# =========================================================
DATA_DIR = Path("data"); DATA_DIR.mkdir(exist_ok=True)

def b64_of_bytes(b: bytes) -> str:
    return base64.b64encode(b).decode("utf-8")

def pdf_viewer_from_bytes(b: bytes, height=520):
    b64 = b64_of_bytes(b)
    st.components.v1.html(
        f'<embed src="data:application/pdf;base64,{b64}" type="application/pdf" width="100%" height="{height}px"/>',
        height=height
    )

def _extract_docx_bytes(b: bytes) -> str:
    try:
        with zipfile.ZipFile(io.BytesIO(b)) as z:
            xml = z.read("word/document.xml").decode("utf-8", "ignore")
            text = re.sub(r"<.*?>", " ", xml)
            return re.sub(r"\s+", " ", text).strip()
    except Exception:
        return ""

def extract_text_from_file(uploaded_file) -> str:
    try:
        suffix = Path(uploaded_file.name).suffix.lower()
        if suffix == ".pdf":
            pdf_reader = PdfReader(io.BytesIO(uploaded_file.read()))
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() or ""
            return text
        elif suffix == ".docx":
            return _extract_docx_bytes(uploaded_file.read())
        else:
            return uploaded_file.read().decode("utf-8", errors="ignore")
    except Exception as e:
        st.error(f"Error al leer '{uploaded_file.name}': {e}")
        return ""

def _max_years(t:str) -> int:
    t = t.lower()
    years = 0
    for m in re.finditer(r'(\d{1,2})\s*(años|year|years)', t):
        years = max(years, int(m.group(1)))
    if years == 0 and any(w in t for w in ["años","experiencia","years"]):
        years = 5
    return years

def extract_meta(text:str) -> dict:
    t = (text or "").lower()
    years = _max_years(t)
    return {
        "universidad":"—",
        "anios_exp": years,
        "titulo":"—",
        "ubicacion":"—",
        "ultima_actualizacion": date.today().isoformat()
    }

def simple_score(cv_text: str, jd: str, keywords: str) -> tuple[int, str]:
    base = 0; reasons = []
    text_low = (cv_text or "").lower()
    kws = [k.strip().lower() for k in (keywords or "").split(",") if k.strip()]
    hits = sum(1 for k in kws if k in text_low)
    if kws:
        base += int((hits/len(kws))*70)
        reasons.append(f"{hits}/{len(kws)} keywords encontradas")
    base = max(0, min(100, base))
    return base, " — ".join(reasons)

# =========================================================
# PRESETS (roles, posiciones demo)
# =========================================================
ROLE_PRESETS = {
    "Data Engineer": {
        "jd": "Construir y mantener pipelines de datos en la nube. Experiencia en Python, SQL, ETL.",
        "keywords": "python, sql, etl, aws, airflow",
        "must": ["Python","SQL","ETL","Cloud"],
        "nice": ["Airflow","Spark","Docker"]
    },
    "Enfermera(o) UCI": {
        "jd": "Atención en UCI. Certificados BLS/ACLS. Manejo de historias clínicas.",
        "keywords": "bls, acls, uci, enfermería, historias clínicas",
        "must": ["BLS","ACLS","UCI"],
        "nice": ["Excel","HIS"]
    }
}

DEFAULT_POSITIONS = pd.DataFrame([
    {"Puesto":"Data Engineer","Días Abierto":12,"Leads":36,"Nuevos":10,"Recruiter Screen":7,"HM Screen":4,
     "Entrevista Telefónica":3,"Entrevista Presencial":2,"Ubicación":"Remoto","Hiring Manager":"Laura G.","Estado":"Abierto","ID":"DE-001"},
    {"Puesto":"Enfermera UCI","Días Abierto":5,"Leads":18,"Nuevos":6,"Recruiter Screen":4,"HM Screen":2,
     "Entrevista Telefónica":2,"Entrevista Presencial":1,"Ubicación":"Lima","Hiring Manager":"Dr. Vega","Estado":"Abierto","ID":"NU-010"},
])

# =========================================================
# LOGIN
# =========================================================
USERS = {
    "colab": {"password":"colab123","role":"Colaborador","name":"Colab"},
    "super": {"password":"super123","role":"Supervisor","name":"Sup"},
    "admin": {"password":"admin123","role":"Administrador","name":"Admin"},
}

def login_screen():
    st.markdown(
        """
        <div style="display:flex;justify-content:center;margin-top:40px">
          <div style="width:380px;background:#fff;border-radius:16px;padding:24px;border:1px solid #e8eef7">
            <h3 style="margin:0 0 12px 0;color:#142433">Acceso a SelektIA</h3>
        """,
        unsafe_allow_html=True,
    )
    with st.form("login_form", clear_on_submit=False):
        u = st.text_input("Usuario")
        p = st.text_input("Contraseña", type="password")
        ok = st.form_submit_button("Ingresar")
        if ok:
            if u in USERS and USERS[u]["password"] == p:
                st.session_state.auth = {"username":u, "role": USERS[u]["role"], "name": USERS[u]["name"]}
                st.success("Bienvenido.")
                st.rerun()
            else:
                st.error("Usuario o contraseña incorrectos.")
    st.markdown("</div></div>", unsafe_allow_html=True)

def require_auth():
    if st.session_state.get("auth") is None:
        login_screen()
        return False
    return True

# =========================================================
# ESTADO INICIAL
# =========================================================
ss = st.session_state
if "auth" not in ss: ss.auth = None
if "section" not in ss: ss.section = "def_sourcing"
if "tasks" not in ss: ss.tasks = []
if "candidates" not in ss: ss.candidates = []
if "positions" not in ss: ss.positions = DEFAULT_POSITIONS.copy()
if "offers" not in ss: ss.offers = {}
if "agents" not in ss: ss.agents = []

# =========================================================
# SIDEBAR
# =========================================================
def render_sidebar():
    with st.sidebar:
        st.markdown(
            """
            <div class="sidebar-brand">
              <div class="brand-title">SelektIA</div>
              <div class="brand-sub">Powered by Wayki Consulting</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("#### DASHBOARD")
        if st.button("Analytics", key="sb_analytics"): ss.section = "analytics"

        st.markdown("#### ASISTENTE IA")
        for txt, sec in [("Flujos","flows"), ("Agentes","agents"), ("Tareas de Agente","agent_tasks")]:
            if st.button(txt, key=f"sb_{sec}"): ss.section = sec

        # ----- NUEVO BLOQUE: TAREAS -----
        st.markdown("#### TAREAS")
        _tasks = ss.get("tasks", [])
        _user  = (ss.get("auth") or {}).get("username", "")
        _count_all  = sum(1 for t in _tasks if not t.get("archived"))
        _count_me   = sum(1 for t in _tasks if t.get("assignee")==_user and not t.get("archived"))
        _count_team = sum(1 for t in _tasks if t.get("team") is not None and not t.get("archived"))
        _count_arch = sum(1 for t in _tasks if t.get("archived"))
        if st.button(f"Todas las tareas ({_count_all})", key="sb_tasks_all"): ss.section = "tasks_all"
        if st.button(f"Asignadas a mí ({_count_me})", key="sb_tasks_me"): ss.section = "tasks_me"
        if st.button(f"Asignadas a mi equipo ({_count_team})", key="sb_tasks_team"): ss.section = "tasks_team"
        if st.button(f"Archivadas ({_count_arch})", key="sb_tasks_arch"): ss.section = "tasks_arch"

        st.markdown("#### PROCESO DE SELECCIÓN")
        for txt, sec in [
            ("Publicación & Sourcing","def_sourcing"),
            ("Puestos","puestos"),
            ("Evaluación de CVs","eval"),
            ("Pipeline de Candidatos","pipeline"),
            ("Entrevista (Gerencia)","interview"),
            ("Tareas del Headhunter","hh_tasks"),
            ("Oferta","offer"),
            ("Onboarding","onboarding"),
        ]:
            if st.button(txt, key=f"sb_{sec}"): ss.section = sec

        st.markdown("#### ACCIONES")
        if st.button("Crear tarea", key="sb_task"): ss.section = "create_task"

        if st.button("Cerrar sesión", key="sb_logout"):
            ss.clear()
            st.rerun()

# =========================================================
# PÁGINAS
# =========================================================
def page_def_sourcing():
    st.header("Publicación & Sourcing")
    role_names = list(ROLE_PRESETS.keys())
    puesto = st.selectbox("Puesto", role_names, index=0)
    preset = ROLE_PRESETS[puesto]

    jd_text = st.text_area("Descripción / JD", height=160, value=preset["jd"])
    kw_text = st.text_area("Palabras clave (coma separada)", height=100, value=preset["keywords"])
    ss["last_role"] = puesto
    ss["last_jd_text"] = jd_text
    ss["last_kw_text"] = kw_text

    files = st.file_uploader("Subir CVs (PDF / DOCX / TXT)", type=["pdf","docx","txt"], accept_multiple_files=True)
    if files and st.button("Procesar CVs cargados"):
        ss.candidates = []
        for f in files:
            b = f.read(); f.seek(0)
            text = extract_text_from_file(f)
            score, reasons = simple_score(text, jd_text, kw_text)
            ss.candidates.append({
                "Name": f.name, "Score": score, "Reasons": reasons, "_bytes": b,
                "_is_pdf": Path(f.name).suffix.lower()==".pdf", "_text": text,
                "meta": extract_meta(text)
            })
        st.success("CVs cargados y analizados.")
        st.rerun()

    with st.expander("🔌 Importar desde portales (demo)"):
        srcs = st.multiselect("Portales", JOB_BOARDS, default=["laborum.pe"])
        qty  = st.number_input("Cantidad por portal", 1, 30, 6)
        search_q = st.text_input("Búsqueda", value=puesto)
        location = st.text_input("Ubicación", value="Lima, Perú")
        if st.button("Traer CVs (demo)"):
            for board in srcs:
                for i in range(1, int(qty)+1):
                    txt = f"{puesto} — {search_q} en {location}. Experiencia 5 años. Excel, SQL, gestión documental."
                    ss.candidates.append({
                        "Name": f"{board}_Candidato_{i:02d}.txt","Score":60,"Reasons":"demo",
                        "_bytes": txt.encode(),"._is_pdf": False,"_text": txt,"meta": extract_meta(txt)
                    })
            st.success("CVs importados.")
            st.rerun()

def page_puestos():
    st.header("Puestos")
    st.dataframe(
        ss.positions[
            ["Puesto","Días Abierto","Leads","Nuevos","Recruiter Screen","HM Screen",
             "Entrevista Telefónica","Entrevista Presencial","Ubicación","Hiring Manager","Estado","ID"]
        ].sort_values(["Estado","Días Abierto","Leads"], ascending=[True,True,False]),
        use_container_width=True, height=380
    )

def page_eval():
    st.header("Resultados de evaluación")
    if not ss.candidates:
        st.info("Carga CVs en **Publicación & Sourcing**.")
        return

    df = pd.DataFrame([{"Nombre":c["Name"], "Score":c["Score"], "Motivos":c["Reasons"]} for c in ss.candidates])
    st.dataframe(df.sort_values("Score", ascending=False), use_container_width=True, height=360)

    with st.expander("Ver CV seleccionado"):
        cand = st.selectbox("Candidato", [c["Name"] for c in ss.candidates])
        c = next(ci for ci in ss.candidates if ci["Name"]==cand)
        if c.get("_is_pdf"):
            pdf_viewer_from_bytes(c["_bytes"])
        else:
            st.code((c.get("_text") or "").strip()[:8000], language="text")

def page_pipeline():
    st.header("Pipeline de Candidatos")
    if not ss.candidates:
        st.info("Aún no hay candidatos en pipeline.")
        return
    # Demo simple
    grid = pd.DataFrame([
        {"Candidato": c["Name"], "Estado":"Nuevo", "Score":c["Score"], "Fecha": date.today().isoformat()}
        for c in ss.candidates
    ])
    st.dataframe(grid, use_container_width=True, height=360)

def page_interview():
    st.header("Entrevista (Gerencia)")
    cands = [c["Name"] for c in ss.candidates] or ["—"]
    cand = st.selectbox("Candidata/o", cands)
    with st.form("form_intv"):
        st.date_input("Fecha")
        st.time_input("Hora")
        st.text_area("Preguntas clave", height=120)
        st.text_area("Comentarios", height=120)
        ok = st.form_submit_button("Guardar")
        if ok: st.success("Entrevista registrada.")

def page_hh_tasks():
    st.header("Tareas del Headhunter")
    cand = st.text_input("Candidata/o", ss.get("selected_cand",""))
    col1, col2, col3 = st.columns(3)
    with col1: st.checkbox("✅ Contacto hecho")
    with col2: st.checkbox("✅ Entrevista agendada")
    with col3: st.checkbox("✅ Feedback recibido")
    st.text_area("Notas (3 fortalezas, 2 riesgos, pretensión, disponibilidad)", height=120)
    st.file_uploader("Adjuntos (BLS/ACLS, colegiatura, etc.)", accept_multiple_files=True)
    c1, c2 = st.columns(2)
    if c1.button("Guardar"): st.success("Checklist y notas guardadas.")
    if c2.button("Enviar a Comité"): st.info("Acta breve generada.")

def page_offer():
    st.header("Oferta")
    cands = [c["Name"] for c in ss.candidates] or ["—"]
    cand = st.selectbox("Candidata/o", cands)
    offer = ss.offers.get(cand, {
        "monto":"", "moneda":"USD", "beneficios":"EPS + Bono anual",
        "fecha_inicio": date.today(), "caducidad": date.today()+timedelta(days=7), "aprobadores":"HRBP; CFO",
        "estado":"Borrador"
    })

    with st.form("form_offer"):
        offer["monto"] = st.text_input("Monto", value=offer["monto"])
        offer["moneda"] = st.selectbox("Moneda", ["USD","PEN","EUR"], index=["USD","PEN","EUR"].index(offer["moneda"]))
        offer["beneficios"] = st.text_area("Beneficios", value=offer["beneficios"], height=100)
        offer["fecha_inicio"] = st.date_input("Fecha de inicio", value=offer["fecha_inicio"])
        offer["caducidad"] = st.date_input("Caducidad de oferta", value=offer["caducidad"])
        offer["aprobadores"] = st.text_input("Aprobadores", value=offer["aprobadores"])
        saved = st.form_submit_button("Guardar oferta")
        if saved:
            ss.offers[cand] = offer
            st.success("Oferta guardada.")

    c1, c2, c3 = st.columns(3)
    if c1.button("Enviar"):
        offer["estado"] = "Enviada"; ss.offers[cand] = offer; st.success("Oferta enviada.")
    if c2.button("Registrar contraoferta"):
        offer["estado"] = "Contraoferta"; ss.offers[cand] = offer; st.info("Contraoferta registrada.")
    if c3.button("Marcar aceptada"):
        offer["estado"] = "Aceptada"; ss.offers[cand] = offer; st.success("Oferta aceptada.")

def page_onboarding():
    st.header("Onboarding")
    data = {
        "Item":["Contrato","Alta de cuenta","Entrega de equipo","Accesos","Examen ocupacional","Inducción 1","Inducción 2","Mentor asignado"],
        "Estado":["Pendiente","Pendiente","Pendiente","Pendiente","Pendiente","Pendiente","Pendiente","Pendiente"],
        "Cuándo":["día 1","día 1","día 1","día 1","primer semana","primer semana","primer semana","primer semana"],
        "Responsable":["RR.HH.","RR.HH.","TI","TI","Salud Ocup.","RR.HH.","RR.HH.","Jefe/Tutor"]
    }
    st.dataframe(pd.DataFrame(data), use_container_width=True, height=260)

def page_agents():
    st.header("Agentes")
    with st.form("new_agent"):
        col1, col2 = st.columns([2,1])
        name = col1.text_input("Nombre del agente")
        role = col2.selectbox("Rol", ["Headhunter","Coordinador RR.HH.","Admin RR.HH."])
        about = st.text_area("Descripción", height=100)
        ok = st.form_submit_button("Crear")
        if ok:
            ss.agents.append({"name":name, "role":role, "about":about})
            st.success("Agente creado.")

    if ss.agents:
        st.markdown("#### Mis agentes")
        st.dataframe(pd.DataFrame(ss.agents), use_container_width=True, height=260)
    else:
        st.info("Aún no hay agentes.")

def page_flows():
    st.header("Flujos")
    st.write("Define y visualiza flujos de proceso para recruiting (borrador).")

def page_agent_tasks():
    st.header("Tareas de Agente")
    st.info("Aquí verás la cola de tareas ejecutables por agente (borrador).")

def page_create_task():
    st.header("Nueva tarea")
    with st.form("task_form"):
        titulo = st.text_input("Título")
        desc   = st.text_area("Descripción", height=150)
        due    = st.date_input("Fecha límite", value=date.today())
        assignee = st.text_input("Asignar a (usuario)", value=(ss.get("auth") or {}).get("username",""))
        team     = st.text_input("Equipo (opcional)")
        ok = st.form_submit_button("Guardar")
        if ok:
            ss.tasks.append({"titulo":titulo,"desc":desc,"due":str(due), "assignee":assignee, "team":team or None, "archived":False})
            st.success("Tarea creada.")

def page_tasks_all():
    st.header("Tareas — Todas")
    _tasks = [t for t in ss.get("tasks",[]) if not t.get("archived")]
    if not _tasks: st.info("No hay tareas."); return
    st.dataframe(pd.DataFrame(_tasks), use_container_width=True, height=360)

def page_tasks_me():
    st.header("Tareas — Asignadas a mí")
    _u = (ss.get("auth") or {}).get("username","")
    _tasks = [t for t in ss.get("tasks",[]) if t.get("assignee")==_u and not t.get("archived")]
    if not _tasks: st.info("Sin tareas asignadas."); return
    st.dataframe(pd.DataFrame(_tasks), use_container_width=True, height=360)

def page_tasks_team():
    st.header("Tareas — Asignadas a mi equipo")
    _tasks = [t for t in ss.get("tasks",[]) if t.get("team") is not None and not t.get("archived")]
    if not _tasks: st.info("No hay tareas de equipo."); return
    st.dataframe(pd.DataFrame(_tasks), use_container_width=True, height=360)

def page_tasks_arch():
    st.header("Tareas — Archivadas")
    _tasks = [t for t in ss.get("tasks",[]) if t.get("archived")]
    if not _tasks: st.info("No hay tareas archivadas."); return
    st.dataframe(pd.DataFrame(_tasks), use_container_width=True, height=360)

# =========================================================
# ANALYTICS (Right Start ES + Sourcing Performance)
# =========================================================
def _sparkline(series):
    series = series or [0,0,0,0]
    fig = go.Figure()
    fig.add_trace(go.Scatter(y=series, mode="lines", line=dict(width=2), hoverinfo="skip"))
    fig.update_layout(height=60, margin=dict(l=0,r=0,t=0,b=0),
                      xaxis=dict(visible=False), yaxis=dict(visible=False))
    return fig

def page_analytics():
    st.header("Analytics")

    # ---------- Right Start (ES) ----------
    st.markdown("### Right Start — Resumen")
    rng = st.radio("Rango", ["Hoy","Ayer","7D","30D","3M","6M","12M","Personalizado"], horizontal=True, index=6)
    if rng == "Personalizado":
        c1, c2 = st.columns(2)
        c1.date_input("Desde", value=date.today())
        c2.date_input("Hasta", value=date.today())

    engaged_pct = float(ss.get("kpi_engaged_pct", 41.7))
    tffc_days   = float(ss.get("kpi_tffc_days", 14.5))
    engaged_n   = int(ss.get("kpi_engaged_users", 43))
    less_eng_n  = int(ss.get("kpi_less_engaged_users", 60))

    k1,k2,k3,k4 = st.columns(4)
    with k1: st.metric("Usuarios con engagement (%)", f"{engaged_pct:.1f}%")
    with k2: st.metric("Tiempo hasta 1er contacto (días)", f"{tffc_days:.1f}")
    with k3: st.metric("Usuarios con engagement", f"{engaged_n}")
    with k4: st.metric("Usuarios con menor engagement", f"{less_eng_n}")

    st.markdown("**Engagement por usuario**")
    df_eng = ss.get("analytics_engagement_by_user",
                    pd.DataFrame([
                        {"user":"Jackie Morales","engagement":8800},
                        {"user":"Brenda Russels","engagement":6500},
                        {"user":"Tilly Quinn","engagement":4800},
                        {"user":"Marc Melendez","engagement":3100},
                        {"user":"Marley Moon","engagement":820},
                        {"user":"Alison Gonzales","engagement":240},
                    ]))
    if isinstance(df_eng, pd.DataFrame) and set(["user","engagement"]).issubset(df_eng.columns):
        fig = px.bar(df_eng, x="engagement", y="user", orientation="h",
                     color_discrete_sequence=[PRIMARY])
        fig.update_layout(height=320, plot_bgcolor="#FFF", paper_bgcolor="#FFF", showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    # ---------- Sourcing Performance ----------
    st.subheader("Sourcing Performance")

    total_apps = int(ss.get("kpi_total_apps", 281))
    contact_to_interest = float(ss.get("kpi_cti", 14.3))
    time_to_reply_days  = float(ss.get("kpi_ttr_days", 4.2))

    s_apps = ss.get("spark_apps", [120, 180, 160, total_apps])
    s_cti  = ss.get("spark_cti",  [12.8, 13.2, contact_to_interest])
    s_ttr  = ss.get("spark_ttr",  [time_to_reply_days*1.1, time_to_reply_days, max(time_to_reply_days*0.9,0)])

    c1,c2,c3 = st.columns(3)
    with c1:
        st.markdown('<div class="card kpi"><div class="sub">Applications</div><div class="value">'
                    f'{total_apps:,}</div></div>', unsafe_allow_html=True)
        st.plotly_chart(_sparkline(s_apps), use_container_width=True, config={"displayModeBar": False})
    with c2:
        st.markdown('<div class="card kpi"><div class="sub">Contact-to-Interest Rate</div><div class="value">'
                    f'{contact_to_interest:.1f}%</div></div>', unsafe_allow_html=True)
        st.plotly_chart(_sparkline(s_cti), use_container_width=True, config={"displayModeBar": False})
    with c3:
        st.markdown('<div class="card kpi"><div class="sub">Time to Reply (días)</div><div class="value">'
                    f'{time_to_reply_days:.1f}</div></div>', unsafe_allow_html=True)
        st.plotly_chart(_sparkline(s_ttr), use_container_width=True, config={"displayModeBar": False})

    # Data esperada para gráficos
    apps_by_channel = ss.get("analytics_apps_by_channel",
                             pd.DataFrame([
                                 {"date":"2025-06-01","channel":"Inbound","applications":15},
                                 {"date":"2025-06-01","channel":"External","applications":7},
                                 {"date":"2025-06-01","channel":"ATS Candidates","applications":5},
                                 {"date":"2025-06-08","channel":"Inbound","applications":12},
                                 {"date":"2025-06-08","channel":"External","applications":6},
                                 {"date":"2025-06-08","channel":"ATS Candidates","applications":10},
                             ]))
    outreach_funnel = ss.get("analytics_outreach_funnel",
                             pd.DataFrame([
                                 {"stage":"Contacted","count":774},
                                 {"stage":"Replied","count":180},
                                 {"stage":"Interested","count":111},
                             ]))
    reply_rate = ss.get("analytics_reply_rate",
                        pd.DataFrame([
                            {"channel":"ATS Candidates","rate":25},
                            {"channel":"External Sourcing","rate":18},
                            {"channel":"Employee Connections","rate":9},
                        ]))
    cti_rate = ss.get("analytics_cti_rate",
                      pd.DataFrame([
                          {"channel":"ATS Candidates","rate":15},
                          {"channel":"Employee Connections","rate":6},
                          {"channel":"External Sourcing","rate":12},
                      ]))

    cA, cB = st.columns([2,1], gap="small")
    with cA:
        st.markdown("**Applications by Hiring Channel (%)**")
        if not apps_by_channel.empty and set(["date","channel","applications"]).issubset(apps_by_channel.columns):
            fig = px.bar(apps_by_channel, x="date", y="applications", color="channel", barnorm="percent")
            fig.update_layout(height=280, margin=dict(l=12,r=12,t=8,b=8), legend_title=None,
                              plot_bgcolor="#fff", paper_bgcolor="#fff")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Carga `analytics_apps_by_channel` con columnas: date, channel, applications.")
    with cB:
        st.markdown("**Outreach Funnel Conversion**")
        if not outreach_funnel.empty and set(["stage","count"]).issubset(outreach_funnel.columns):
            fig = px.funnel(outreach_funnel, x="count", y="stage")
            fig.update_layout(height=280, margin=dict(l=12,r=12,t=8,b=8), plot_bgcolor="#fff", paper_bgcolor="#fff")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Carga `analytics_outreach_funnel` con columnas: stage, count.")

    d1, d2, d3 = st.columns(3, gap="small")
    with d1:
        st.markdown("**Reply Rate by Hiring Channel**")
        if not reply_rate.empty and set(["channel","rate"]).issubset(reply_rate.columns):
            fig = px.bar(reply_rate, x="rate", y="channel", orientation="h")
            fig.update_layout(height=260, margin=dict(l=12,r=12,t=8,b=8),
                              plot_bgcolor="#fff", paper_bgcolor="#fff", showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Carga `analytics_reply_rate` con columnas: channel, rate.")
    with d2:
        st.markdown("**Contact-to-Interest by Channel**")
        if not cti_rate.empty and set(["channel","rate"]).issubset(cti_rate.columns):
            fig = px.bar(cti_rate, x="rate", y="channel", orientation="h")
            fig.update_layout(height=260, margin=dict(l=12,r=12,t=8,b=8),
                              plot_bgcolor="#fff", paper_bgcolor="#fff", showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Carga `analytics_cti_rate` con columnas: channel, rate.")
    with d3:
        st.markdown("**Notas**")
        st.caption("Este panel se alimenta de tus otras pestañas (puestos, candidatos, outreach, etc.).")

# =========================================================
# ROUTER
# =========================================================
ROUTES = {
    "def_sourcing": page_def_sourcing,
    "puestos": page_puestos,
    "eval": page_eval,
    "pipeline": page_pipeline,
    "interview": page_interview,
    "hh_tasks": page_hh_tasks,
    "offer": page_offer,
    "onboarding": page_onboarding,
    "agents": page_agents,
    "flows": page_flows,
    "agent_tasks": page_agent_tasks,
    "analytics": page_analytics,
    "create_task": page_create_task,
    "tasks_all": page_tasks_all,
    "tasks_me": page_tasks_me,
    "tasks_team": page_tasks_team,
    "tasks_arch": page_tasks_arch,
}

# =========================================================
# APP
# =========================================================
if require_auth():
    render_sidebar()
    ROUTES.get(ss.section, page_def_sourcing)()
