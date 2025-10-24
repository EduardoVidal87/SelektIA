# app.py
# -*- coding: utf-8 -*-

import io
import re
import base64
from pathlib import Path
from datetime import datetime, date
from typing import List, Dict, Any

import streamlit as st
import pandas as pd
import plotly.express as px
from PyPDF2 import PdfReader


# =============================================================================
# THEME / COLORS
# =============================================================================
PRIMARY = "#00CD78"                 # encabezados laterales, acentos
SIDEBAR_BG = "#0E192B"              # fondo barra izquierda
SIDEBAR_TX = "#FFFFFF"              # texto barra izquierda
BODY_BG = "#F6FAFF"                 # fondo principal
CARD_BG = "#0E192B"                 # mismo color que barra para cajas laterales
ACCENT_BADGE = "#0DD091"

st.set_page_config(page_title="SelektIA", page_icon="🧠", layout="wide")

CSS = f"""
:root {{
  --green: {PRIMARY};
  --sb-bg: {SIDEBAR_BG};
  --sb-tx: {SIDEBAR_TX};
  --body: {BODY_BG};
  --sb-card: {CARD_BG};
}}

/* Fondo general */
html, body, [data-testid="stAppViewContainer"] {{
  background: var(--body) !important;
}}
.block-container {{
  background: transparent !important;
  padding-top: 1.25rem !important;
}}

/* Sidebar */
[data-testid="stSidebar"] {{
  background: var(--sb-bg) !important;
  color: var(--sb-tx) !important;
  border-right: 0;
}}
/* Logo texto en sidebar */
.sidebar-logo {{
  font-family: Inter, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, "Apple Color Emoji","Segoe UI Emoji";
  font-weight: 800;
  font-size: 42px;
  letter-spacing: .5px;
  color: var(--green);
  margin: 8px 6px 0 6px;
  line-height: 1.1;
}}
.sidebar-powered {{
  color: #9deccf;
  margin: -6px 8px 6px 8px;
  font-size: 12px;
}}

/* Títulos de sección del sidebar */
.sb-section-title {{
  color: var(--green) !important;
  text-transform: uppercase;
  font-weight: 800 !important;
  font-size: 12px !important;
  letter-spacing: .6px;
  margin: 18px 10px 6px 10px !important;
}}

/* Botón lateral (link) */
.sb-link {{
  display: block;
  width: 100%;
  padding: 10px 14px;
  margin: 8px 10px;
  border-radius: 12px;
  background: var(--sb-card);
  border: 1px solid var(--sb-bg);  /* borde igual al fondo */
  color: #fff;
  text-decoration: none !important;
  font-weight: 600;
  text-align: left;   /* SIEMPRE A LA IZQUIERDA */
}}
.sb-link:hover {{
  border-color: #14263e;
  filter: brightness(1.05);
}}
.sb-link.active {{
  outline: 0;
  box-shadow: 0 0 0 2px var(--green) inset;
}}

/* Botones de acción principales */
.stButton > button {{
  background: var(--green) !important;
  color: #082017 !important;
  border: 0 !important;
  border-radius: 10px !important;
  font-weight: 700 !important;
}}

/* Inputs del cuerpo */
.block-container [data-testid="stTextArea"] textarea,
.block-container [data-testid="stTextInput"] input,
.block-container [data-testid="stSelectbox"] > div > div {{
  background: #F3F8FF !important;
  border: 1px solid #D8E6F6 !important;
  color: #142433 !important;
  border-radius: 10px !important;
}}

/* Títulos principales */
h1, h2, h3 {{
  color: #142433;
}}
h1 strong, h2 strong, h3 strong {{
  color: var(--green);
}}
.badge {{
  display:inline-block; background:#E6FFF4; color:#07694e; 
  border-radius:999px; padding:2px 10px; font-weight:700; font-size:12px
}}
"""

st.markdown(f"<style>{CSS}</style>", unsafe_allow_html=True)


# =============================================================================
# STATE HELPERS
# =============================================================================
PAGES = [
    ("dashboard", "Bienvenido a Selektia", "🏠"),
    # ASISTENTE / AGENTES
    ("flujos", "Flujos", "🔁"),
    ("agentes", "Agentes", "🤖"),
    ("tareas_agente", "Tareas de Agente", "🗒️"),
    # PROCESO DE SELECCIÓN
    ("definicion", "Definición & Carga", "🧱"),
    ("puestos", "Puestos", "🗂️"),
    ("evaluacion", "Evaluación de CVs", "🧪"),
    ("pipeline", "Pipeline de Candidatos", "👥"),
    ("entrevista", "Entrevista (Gerencia)", "🗣️"),
    ("tareas_hh", "Tareas del Headhunter", "✅"),
    ("oferta", "Oferta", "📄"),
    ("onboarding", "Onboarding", "🎒"),
    # ANALYTICS
    ("analytics", "Abrir Analytics", "📊"),
    # ACCIONES
    ("crear_tarea", "Crear tarea", "➕"),
]

def init_state():
    ss = st.session_state
    ss.setdefault("page", "definicion")
    ss.setdefault("positions", default_positions())
    ss.setdefault("jd_text", "")
    ss.setdefault("kw_text", "HIS, SAP IS-H, BLS, ACLS, IAAS, educación al paciente, seguridad del paciente, protocolos")
    ss.setdefault("puesto_selected", "Enfermera/o Asistencial")
    ss.setdefault("candidates", [])
    ss.setdefault("uploader_key", "u1")
    ss.setdefault("entrevista_queue", [])
    ss.setdefault("agentes", [])         # elementos {"rol","objetivo","backstory","guardrails","herramientas":[...]}
    ss.setdefault("tareas", [])

def default_positions() -> pd.DataFrame:
    return pd.DataFrame([
        {
            "ID": "10,645,194",
            "Puesto": "Desarrollador/a Backend (Python)",
            "Ubicación": "Lima, Perú",
            "Leads": 1800,
            "Nuevos": 115,
            "Recruiter Screen": 35,
            "HM Screen": 7,
            "Entrevista Telefónica": 14,
            "Entrevista Presencial": 15,
            "Días Abierto": 3,
            "Hiring Manager": "Rivers Brykson",
            "Estado": "Abierto",
        },
        {
            "ID": "10,376,415",
            "Puesto": "VP de Marketing",
            "Ubicación": "Santiago, Chile",
            "Leads": 8100,
            "Nuevos": 1,
            "Recruiter Screen": 15,
            "HM Screen": 35,
            "Entrevista Telefónica": 5,
            "Entrevista Presencial": 7,
            "Días Abierto": 28,
            "Hiring Manager": "Angela Cruz",
            "Estado": "Abierto",
        },
        {
            "ID": "10,376,646",
            "Puesto": "Planner de Demanda",
            "Ubicación": "Ciudad de México, MX",
            "Leads": 2300,
            "Nuevos": 26,
            "Recruiter Screen": 3,
            "HM Screen": 8,
            "Entrevista Telefónica": 6,
            "Entrevista Presencial": 3,
            "Días Abierto": 28,
            "Hiring Manager": "Rivers Brykson",
            "Estado": "Abierto",
        },
    ])


# =============================================================================
# UTILITIES
# =============================================================================
def go(page_key: str):
    """ Navega a otra 'página' (pestaña) """
    st.session_state.page = page_key

def sb_link(title: str, key: str, icon: str = ""):
    active = "active" if st.session_state.page == key else ""
    if st.button(f"{icon} {title}", key=f"SB_{key}", use_container_width=True):
        go(key)
    # for the CSS look as anchor
    st.markdown(f"<a class='sb-link {active}'>{icon} {title}</a>", unsafe_allow_html=True)

def extract_text_from_upload(uploaded_file) -> str:
    """Extrae texto de PDF o TXT."""
    suffix = Path(uploaded_file.name).suffix.lower()
    if suffix == ".pdf":
        rdr = PdfReader(io.BytesIO(uploaded_file.read()))
        txt = ""
        for p in rdr.pages:
            try:
                txt += p.extract_text() or ""
            except Exception:
                pass
        return txt
    return uploaded_file.read().decode("utf-8", errors="ignore")

def pdf_viewer_pdfjs(file_bytes: bytes, height=520, scale=1.05):
    b64 = base64.b64encode(file_bytes).decode("utf-8")
    src = f"https://mozilla.github.io/pdf.js/web/viewer.html?file=data:application/pdf;base64,{b64}#zoom={int(scale*100)}"
    st.markdown(
        f"""<iframe src="{src}" style="width:100%; height:{height}px; border:0;" title="PDF"></iframe>""",
        unsafe_allow_html=True
    )

# Heurística sencilla para años de experiencia
YEAR_RX = re.compile(r"(\d{1,2})\+?\s*(?:years|años)\s+of\s+total\s+experience", re.I)
BACHELOR_RX = re.compile(r"(?:Universidad|University)\s+.*?\b(\d{{4}})\b", re.I)
ROLE_LINE_RX = re.compile(r"(?:(Senior|Lead|Principal)\s+)?([A-Za-zÁÉÍÓÚÑáéíóúñ/ ,.-]+?Engineer|Developer|Recepcionista|Tecnólogo|Médico|Químico|Farmacéutico|Asistente|Nurse)", re.I)

def parse_cv_details(text: str) -> Dict[str, Any]:
    details = {"años_experiencia": None, "roles": [], "universidad_ultimo": None, "anio_grado": None}
    m = YEAR_RX.search(text)
    if m:
        try:
            details["años_experiencia"] = int(m.group(1))
        except Exception:
            pass
    # roles (top 3 lines que machean)
    roles = []
    for line in text.splitlines():
        mm = ROLE_LINE_RX.search(line)
        if mm:
            roles.append(line.strip()[:120])
        if len(roles) >= 3:
            break
    details["roles"] = roles

    # universidad + año (último que aparezca)
    uni_years = list(BACHELOR_RX.finditer(text))
    if uni_years:
        last = uni_years[-1]
        details["universidad_ultimo"] = "Universidad detectada"
        details["anio_grado"] = last.group(1)

    return details

def simple_score(cv_text: str, jd: str, keywords: str) -> tuple[int, str, List[str]]:
    base = 0
    reasons = []
    hits_kw = []
    t = cv_text.lower()
    jd_low = jd.lower()
    kws = [k.strip().lower() for k in keywords.split(",") if k.strip()]
    hits = 0
    for k in kws:
        if k in t:
            hits += 1
            hits_kw.append(k)
    if kws:
        base += int((hits/len(kws))*70)
        reasons.append(f"{hits}/{len(kws)} keywords encontradas")
    jd_terms = [w for w in set(jd_low.split()) if len(w) > 3]
    m2 = sum(1 for w in jd_terms if w in t)
    if jd_terms:
        base += int((m2/len(jd_terms))*30)
        reasons.append("Coincidencias con JD (aprox.)")
    base = max(0, min(100, base))
    return base, " — ".join(reasons), hits_kw


# =============================================================================
# SIDEBAR
# =============================================================================
def sidebar():
    st.sidebar.markdown("<div class='sidebar-logo'>SelektIA</div>", unsafe_allow_html=True)
    st.sidebar.markdown("<div class='sidebar-powered'>Powered by Wayki Consulting</div>", unsafe_allow_html=True)

    # DASHBOARD
    st.sidebar.markdown("<div class='sb-section-title'>Dashboard</div>", unsafe_allow_html=True)
    if st.sidebar.button("Bienvenido a Selektia", use_container_width=True, key="SB_home"):
        go("dashboard")
    st.sidebar.markdown("<a class='sb-link'></a>", unsafe_allow_html=True)

    # ASISTENTE IA
    st.sidebar.markdown("<div class='sb-section-title'>Asistente IA</div>", unsafe_allow_html=True)
    if st.sidebar.button("Flujos", use_container_width=True, key="SB_flujos"):
        go("flujos")
    if st.sidebar.button("Agentes", use_container_width=True, key="SB_agentes"):
        go("agentes")
    if st.sidebar.button("Tareas de Agente", use_container_width=True, key="SB_tareas_ag"):
        go("tareas_agente")
    st.sidebar.markdown("<a class='sb-link'></a>", unsafe_allow_html=True)

    # PROCESO DE SELECCIÓN
    st.sidebar.markdown("<div class='sb-section-title'>Proceso de selección</div>", unsafe_allow_html=True)
    for key, label, _ in [
        ("definicion","Definición & Carga",""),
        ("puestos","Puestos",""),
        ("evaluacion","Evaluación de CVs",""),
        ("pipeline","Pipeline de Candidatos",""),
        ("entrevista","Entrevista (Gerencia)",""),
        ("tareas_hh","Tareas del Headhunter",""),
        ("oferta","Oferta",""),
        ("onboarding","Onboarding",""),
    ]:
        if st.sidebar.button(label, use_container_width=True, key=f"SB_{key}_2"):
            go(key)
    st.sidebar.markdown("<a class='sb-link'></a>", unsafe_allow_html=True)

    # ANALYTICS
    st.sidebar.markdown("<div class='sb-section-title'>Analytics</div>", unsafe_allow_html=True)
    if st.sidebar.button("Abrir Analytics", use_container_width=True, key="SB_analytics"):
        go("analytics")
    st.sidebar.markdown("<a class='sb-link'></a>", unsafe_allow_html=True)

    # ACCIONES
    st.sidebar.markdown("<div class='sb-section-title'>Acciones</div>", unsafe_allow_html=True)
    if st.sidebar.button("Crear tarea", use_container_width=True, key="SB_crear_tarea"):
        go("crear_tarea")


# =============================================================================
# PAGES IMPLEMENTATION
# =============================================================================
def page_dashboard():
    st.markdown("# Bienvenido a Selektia")
    st.write("Panel básico de bienvenida. Usa el menú izquierdo para navegar.")

def page_definicion():
    st.markdown("# Definición & Carga")
    ss = st.session_state

    puesto = st.selectbox(
        "Puesto",
        [
            "Enfermera/o Asistencial",
            "Tecnólogo/a Médico",
            "Recepcionista de Admisión",
            "Médico/a General",
            "Químico/a Farmacéutico/a",
        ],
        index=0,
        key="puesto_selected",
    )

    jd = st.text_area("Descripción / JD", value=ss.jd_text, height=160, key="jd_text")
    kw = st.text_input("Palabras clave (coma separada)", value=ss.kw_text, key="kw_text")

    st.markdown("### Subir CVs (PDF o TXT)")
    files = st.file_uploader(
        "Arrastra aquí o haz clic para subir",
        key=ss.uploader_key,
        type=["pdf", "txt"],
        accept_multiple_files=True,
        label_visibility="collapsed",
    )

    if files:
        ss.candidates.clear()
        for f in files:
            raw = f.read()
            f.seek(0)
            text = extract_text_from_upload(f)
            score, reasons, hits_kw = simple_score(text, jd, kw)
            details = parse_cv_details(text)
            ss.candidates.append({
                "Name": f.name,
                "Score": score,
                "Reasons": reasons,
                "Hits": hits_kw,
                "_bytes": raw,
                "_is_pdf": Path(f.name).suffix.lower() == ".pdf",
                "_text": text,
                "_meta": {
                    "uploaded_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
                    **details
                },
            })
        st.success(f"Se cargaron {len(ss.candidates)} CV(s). Ve a **Evaluación de CVs** o **Pipeline** para continuar.")

    st.caption("Tip: el análisis se recalcula en base al JD y keywords actuales.")

def page_puestos():
    st.markdown("# Puestos")
    df = st.session_state.positions.copy()
    st.dataframe(
        df[
            [
                "Puesto", "Días Abierto", "Leads", "Nuevos", "Recruiter Screen",
                "HM Screen", "Entrevista Telefónica", "Entrevista Presencial",
                "Ubicación", "Hiring Manager", "Estado", "ID"
            ]
        ],
        use_container_width=True,
        height=420
    )

def page_evaluacion():
    st.markdown("# Resultados de evaluación")
    ss = st.session_state
    if not ss.candidates:
        st.info("Sube CVs en **Definición & Carga**.")
        return
    df = pd.DataFrame(ss.candidates).sort_values("Score", ascending=False)
    st.markdown("### Ranking de Candidatos")
    st.dataframe(df[["Name","Score","Reasons"]], use_container_width=True, height=240)

    st.markdown("### Comparación de puntajes")
    fig = px.bar(df, x="Name", y="Score", title="Comparación de puntajes (todos los candidatos)")
    colors = [PRIMARY if s >= 60 else "#E9F3FF" for s in df["Score"]]
    fig.update_traces(marker_color=colors)
    fig.update_layout(plot_bgcolor="#fff", paper_bgcolor="rgba(0,0,0,0)", xaxis_title=None, yaxis_title="Score")
    st.plotly_chart(fig, use_container_width=True)

    # Visor
    st.markdown("### Visor de CV (PDF/TXT)")
    selected = st.selectbox("Elige un candidato", df["Name"].tolist(), label_visibility="collapsed")
    row = df[df["Name"] == selected].iloc[0]
    if row["_is_pdf"]:
        pdf_viewer_pdfjs(row["_bytes"], height=520, scale=1.1)
        st.download_button(f"Descargar {row['Name']}", data=row["_bytes"], file_name=row["Name"], mime="application/pdf")
    else:
        st.info("Archivo TXT. Contenido abajo:")
        st.text_area("Contenido", row["_text"], height=360, label_visibility="collapsed")

def page_pipeline():
    st.markdown("# Pipeline de Candidatos")
    ss = st.session_state
    if not ss.candidates:
        st.info("Sube CVs en **Definición & Carga**.")
        return

    # Tabla izquierda
    colL, colR = st.columns([1.15, 1])
    with colL:
        df = pd.DataFrame(ss.candidates)[["Name","Score","Reasons"]]
        df = df.sort_values("Score", ascending=False).reset_index(drop=True)
        st.markdown("#### Candidatos")
        st.dataframe(df, use_container_width=True, height=360)
        selected = st.selectbox("Seleccionar", df["Name"].tolist(), key="pipeline_sel", label_visibility="collapsed")

    # Detalle derecha
    with colR:
        cand = next(c for c in ss.candidates if c["Name"] == selected)
        meta = cand["_meta"]
        st.markdown("#### Detalle del candidato")
        st.write(f"**Archivo:** {cand['Name']}")
        st.write(f"**Match estimado:** {cand['Score']} / 100")
        st.write(f"**Keywords halladas:** {', '.join(cand['Hits']) if cand['Hits'] else '—'}")
        st.write("---")
        st.write("**Años de experiencia (estimado):**", meta.get("años_experiencia") or "—")
        st.write("**Cargos (últimos detectados):**")
        if meta.get("roles"):
            for r in meta["roles"]:
                st.markdown(f"- {r}")
        else:
            st.markdown("—")
        st.write("**Universidad (último registro) y año:**", f"{meta.get('universidad_ultimo') or '—'} {meta.get('anio_grado') or ''}")
        st.write("**Fecha de carga:**", meta.get("uploaded_at","—"))

        st.write("---")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Mover a Entrevista (Gerencia)"):
                if cand["Name"] not in ss.entrevista_queue:
                    ss.entrevista_queue.append(cand["Name"])
                st.success("Movido a **Entrevista (Gerencia)**. Revisa esa pestaña.")
        with c2:
            if cand["_is_pdf"]:
                st.download_button("Descargar PDF", data=cand["_bytes"], file_name=cand["Name"], mime="application/pdf")

def page_entrevista():
    st.markdown("# Entrevista (Gerencia)")
    queue = st.session_state.entrevista_queue
    if not queue:
        st.info("Aún no hay candidatos en cola. En **Pipeline** mueve candidatos a esta etapa.")
        return
    st.write("**En cola para entrevista:**")
    for name in queue:
        st.markdown(f"- {name}")

def page_tareas_hh():
    st.markdown("# Tareas del Headhunter")
    st.caption("Checklist y notas se gestionan aquí (siguiente iteración).")

def page_oferta():
    st.markdown("# Oferta")
    st.caption("Genera y gestiona ofertas. (Formulario detallado en iteración siguiente).")

def page_onboarding():
    st.markdown("# Onboarding")
    st.caption("Checklist de ingreso y tareas automáticas.")

def page_analytics():
    st.markdown("# Analytics")
    st.info("Placeholder. Integraremos tus dashboards favoritos aquí.")

def page_crear_tarea():
    st.markdown("# Crear tarea")
    with st.form("form_tarea", clear_on_submit=True):
        titulo = st.text_input("Título")
        desc = st.text_area("Descripción", height=160)
        due = st.date_input("Fecha límite", value=date.today())
        ok = st.form_submit_button("Guardar")
    if ok:
        st.session_state.tareas.append({"titulo": titulo, "desc": desc, "due": str(due)})
        st.success("Tarea creada.")

def page_flujos():
    st.markdown("# Flujos")
    st.info("Configura flujos y automatizaciones (pendiente).")

# ======== AGENTES (incluye la lógica que antes estaba en “Asistente IA”) ========
def page_agentes():
    st.markdown("# Agentes")
    st.caption("Crea asistentes especializados (p.ej., Headhunter). Se guardan en esta sesión.")

    with st.form("form_agente"):
        colA, colB = st.columns([1.1, 1])
        with colA:
            rol = st.selectbox("Rol*", ["Headhunter", "Coordinador RR.HH.", "Admin RR.HH.", "Hiring Manager", "Gerencia/Comité"], index=0)
            objetivo = st.text_input("Objetivo*", "Identificar a los mejores profesionales para el cargo definido en el JD")
            backstory = st.text_area("Backstory*", "Eres un analista de RR.HH. con experiencia en análisis de documentos, CV y currículums.", height=100)
            guardrails = st.text_area("Guardrails", "No compartas datos sensibles. Cita la fuente (CV o JD) al argumentar.", height=80)
            herramientas = st.multiselect("Herramientas habilitadas", ["Parser de PDF", "Recomendador de candidatos", "Clasificador de skills"], default=["Parser de PDF","Recomendador de candidatos"])
        with colB:
            st.markdown("### Permisos y alcance")
            st.markdown("- **RLS** por puesto: el asistente ve candidatos del puesto/rol asignado.")
            st.markdown("- **Acciones según rol** (p.ej., HH no aprueba ofertas).")
            st.markdown("- **Auditoría**: toda acción queda registrada.")

        submit = st.form_submit_button("Crear/Actualizar Asistente")
    if submit:
        # si existe rol, actualiza; si no, crea
        existing = next((a for a in st.session_state.agentes if a["rol"] == rol), None)
        data = {"rol": rol, "objetivo": objetivo, "backstory": backstory, "guardrails": guardrails, "herramientas": herramientas}
        if existing:
            existing.update(data)
        else:
            st.session_state.agentes.append(data)
        st.success("Asistente guardado. Esta configuración guiará la evaluación de CVs.")

    if st.session_state.agentes:
        st.markdown("### Mis asistentes")
        gcols = st.columns(3)
        for i, ag in enumerate(st.session_state.agentes):
            with gcols[i % 3]:
                st.markdown(
                    f"""
                    <div style="background:#fff;border:1px solid #E3EDF6;border-radius:14px;padding:14px;margin-bottom:10px">
                      <div style="font-weight:800">{ag['rol']}</div>
                      <div style="font-size:12px;color:#455; margin:6px 0">{ag['objetivo']}</div>
                      <span class="badge">{', '.join(ag['herramientas'])}</span>
                    </div>
                    """, unsafe_allow_html=True
                )

def page_tareas_agente():
    st.markdown("# Tareas de Agente")
    st.caption("Aquí verás las tareas de tus asistentes IA (pendiente).")


# =============================================================================
# ROUTER
# =============================================================================
def router():
    page = st.session_state.page
    if page == "dashboard":
        page_dashboard()
    elif page == "definicion":
        page_definicion()
    elif page == "puestos":
        page_puestos()
    elif page == "evaluacion":
        page_evaluacion()
    elif page == "pipeline":
        page_pipeline()
    elif page == "entrevista":
        page_entrevista()
    elif page == "tareas_hh":
        page_tareas_hh()
    elif page == "oferta":
        page_oferta()
    elif page == "onboarding":
        page_onboarding()
    elif page == "analytics":
        page_analytics()
    elif page == "crear_tarea":
        page_crear_tarea()
    elif page == "flujos":
        page_flujos()
    elif page == "agentes":
        page_agentes()
    elif page == "tareas_agente":
        page_tareas_agente()
    else:
        page_definicion()


# =============================================================================
# MAIN
# =============================================================================
def main():
    init_state()
    sidebar()       # izquierda
    router()        # contenido central

if __name__ == "__main__":
    main()
