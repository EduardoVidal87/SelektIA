# app.py
# -*- coding: utf-8 -*-

import io
import re
import base64
from pathlib import Path
from datetime import datetime, date, timedelta
from typing import List, Dict, Any

import streamlit as st
import pandas as pd
import plotly.express as px
from PyPDF2 import PdfReader


# =============================================================================
# THEME / COLORS
# =============================================================================
PRIMARY = "#00CD78"                 # acentos
SIDEBAR_BG = "#0E192B"              # fondo barra izquierda
SIDEBAR_TX = "#FFFFFF"              # texto barra izquierda
BODY_BG = "#F6FAFF"                 # fondo principal
CARD_BG = "#0E192B"                 # mismo color que barra para cajas/botones lateral

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
  padding-top: 1.0rem !important;
}}

/* Sidebar */
[data-testid="stSidebar"] {{
  background: var(--sb-bg) !important;
  color: var(--sb-tx) !important;
  border-right: 0;
}}

/* Contenedor del logo centrado */
.sb-logo-wrap {{
  display:flex; flex-direction:column; align-items:center; justify-content:center;
  width:100%; text-align:center; margin:6px 0 10px 0;
}}
.sidebar-logo {{
  font-family: Inter, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, "Apple Color Emoji","Segoe UI Emoji";
  font-weight: 900;
  font-size: 46px;
  letter-spacing: .5px;
  color: var(--green);
  line-height: 1.05;
}}
.sidebar-powered {{
  color: #9deccf;
  font-size: 12px;
  margin-top: -4px;
}}

/* Títulos de sección del sidebar */
.sb-section-title {{
  color: var(--green) !important;
  text-transform: uppercase;
  font-weight: 800 !important;
  font-size: 12px !important;
  letter-spacing: .6px;
  margin: 10px 10px 6px 10px !important;
}}

/* Botones del sidebar (texto a la izquierda SIEMPRE) */
[data-testid="stSidebar"] .stButton > button {{
  width: 100% !important;
  text-align: left !important;            /* a la izquierda */
  padding: 10px 14px !important;
  margin: 6px 10px !important;            /* menos separación vertical */
  border-radius: 12px !important;
  background: var(--sb-card) !important;  /* mismo color del panel */
  border: 1px solid var(--sb-bg) !important; /* contorno mismo color del panel */
  color: #fff !important;
  font-weight: 600 !important;
}}
[data-testid="stSidebar"] .stButton > button:hover {{
  border-color: #152845 !important;
  filter: brightness(1.05);
}}

/* Botones de acción del cuerpo */
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
.sla-badge {{
  display:inline-block; padding:2px 8px; border-radius:999px; color:#fff; font-weight:700; font-size:11px;
}}
.sla-green {{ background:#16a34a; }}
.sla-amber {{ background:#f59e0b; }}
.sla-red {{ background:#dc2626; }}
"""

st.markdown(f"<style>{CSS}</style>", unsafe_allow_html=True)


# =============================================================================
# STATE HELPERS
# =============================================================================
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
    ss.setdefault("hh_tasks", {})         # por candidato
    ss.setdefault("oferta_queue", [])
    ss.setdefault("offers", {})           # ofertas por candidato
    ss.setdefault("onboarding", {})       # onboarding por candidato
    ss.setdefault("agentes", [])
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
    st.session_state.page = page_key

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
    roles = []
    for line in text.splitlines():
        mm = ROLE_LINE_RX.search(line)
        if mm:
            roles.append(line.strip()[:120])
        if len(roles) >= 3:
            break
    details["roles"] = roles

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
    # Logo centrado
    st.sidebar.markdown(
        """
        <div class="sb-logo-wrap">
          <div class="sidebar-logo">SelektIA</div>
          <div class="sidebar-powered">Powered by Wayki Consulting</div>
        </div>
        """, unsafe_allow_html=True
    )

    # DASHBOARD
    st.sidebar.markdown("<div class='sb-section-title'>Dashboard</div>", unsafe_allow_html=True)
    if st.sidebar.button("Analytics", key="SB_analytics"):
        go("analytics")

    # ASISTENTE IA
    st.sidebar.markdown("<div class='sb-section-title'>Asistente IA</div>", unsafe_allow_html=True)
    if st.sidebar.button("Flujos", key="SB_flujos"):
        go("flujos")
    if st.sidebar.button("Agentes", key="SB_agentes"):
        go("agentes")
    if st.sidebar.button("Tareas de Agente", key="SB_tareas_ag"):
        go("tareas_agente")

    # PROCESO DE SELECCIÓN
    st.sidebar.markdown("<div class='sb-section-title'>Proceso de selección</div>", unsafe_allow_html=True)
    for key, label in [
        ("definicion","Definición & Carga"),
        ("puestos","Puestos"),
        ("evaluacion","Evaluación de CVs"),
        ("pipeline","Pipeline de Candidatos"),
        ("entrevista","Entrevista (Gerencia)"),
        ("tareas_hh","Tareas del Headhunter"),
        ("oferta","Oferta"),
        ("onboarding","Onboarding"),
    ]:
        if st.sidebar.button(label, key=f"SB_{key}_2"):
            go(key)

    # ACCIONES
    st.sidebar.markdown("<div class='sb-section-title'>Acciones</div>", unsafe_allow_html=True)
    if st.sidebar.button("Crear tarea", key="SB_crear_tarea"):
        go("crear_tarea")


# =============================================================================
# PAGES IMPLEMENTATION
# =============================================================================
def page_definicion():
    st.markdown("# Definición & Carga")
    ss = st.session_state

    st.selectbox(
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

    st.text_area("Descripción / JD", value=ss.jd_text, height=160, key="jd_text")
    st.text_input("Palabras clave (coma separada)", value=ss.kw_text, key="kw_text")

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
            score, reasons, hits_kw = simple_score(text, ss.jd_text, ss.kw_text)
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
                st.success("Movido a **Entrevista (Gerencia)**.")
        with c2:
            if cand["_is_pdf"]:
                st.download_button("Descargar PDF", data=cand["_bytes"], file_name=cand["Name"], mime="application/pdf")

# ----------- TAREAS HEADHUNTER -----------
def page_tareas_hh():
    st.markdown("# Tareas del Headhunter")
    ss = st.session_state
    if not ss.candidates:
        st.info("No hay candidatos cargados.")
        return
    names = [c["Name"] for c in ss.candidates]
    selected = st.selectbox("Candidata/o", names, key="hh_sel")

    hh = ss.hh_tasks.get(selected, {
        "contacto": False, "agendada": False, "feedback": False,
        "fortalezas": ["","",""], "riesgos": ["",""],
        "pretension": "", "disponibilidad": "",
        "files": [], "locked": False
    })

    st.markdown("### Checklist")
    c1, c2, c3 = st.columns(3)
    with c1: hh["contacto"] = st.checkbox("✅ Contacto hecho", value=hh["contacto"], disabled=hh["locked"])
    with c2: hh["agendada"] = st.checkbox("✅ Entrevista agendada", value=hh["agendada"], disabled=hh["locked"])
    with c3: hh["feedback"] = st.checkbox("✅ Feedback recibido", value=hh["feedback"], disabled=hh["locked"])

    st.markdown("### Notas (obligatorias)")
    f1, f2, f3 = st.columns(3)
    with f1: hh["fortalezas"][0] = st.text_input("Fortaleza 1", value=hh["fortalezas"][0], disabled=hh["locked"])
    with f2: hh["fortalezas"][1] = st.text_input("Fortaleza 2", value=hh["fortalezas"][1], disabled=hh["locked"])
    with f3: hh["fortalezas"][2] = st.text_input("Fortaleza 3", value=hh["fortalezas"][2], disabled=hh["locked"])
    r1, r2 = st.columns(2)
    with r1: hh["riesgos"][0] = st.text_input("Riesgo 1", value=hh["riesgos"][0], disabled=hh["locked"])
    with r2: hh["riesgos"][1] = st.text_input("Riesgo 2", value=hh["riesgos"][1], disabled=hh["locked"])

    c4, c5 = st.columns(2)
    with c4: hh["pretension"] = st.text_input("Pretensión salarial", value=hh["pretension"], disabled=hh["locked"])
    with c5: hh["disponibilidad"] = st.text_input("Disponibilidad", value=hh["disponibilidad"], disabled=hh["locked"])

    st.markdown("### Adjuntos (BLS/ACLS, colegiatura)")
    up = st.file_uploader("Sube PDF/IMG", type=["pdf","png","jpg","jpeg"], accept_multiple_files=True, disabled=hh["locked"])
    if up:
        hh["files"] = [f.name for f in up]
    if hh["files"]:
        st.caption("Archivos cargados: " + ", ".join(hh["files"]))

    colA, colB = st.columns(2)
    with colA:
        if st.button("Guardar (HH)"):
            ss.hh_tasks[selected] = hh
            st.success("Guardado.")
    with colB:
        disabled = hh["locked"] or not (hh["contacto"] and hh["agendada"] and hh["feedback"] and all(hh["fortalezas"]) and all(hh["riesgos"]))
        if st.button("Enviar a Comité", disabled=disabled):
            hh["locked"] = True
            ss.hh_tasks[selected] = hh
            if selected not in ss.entrevista_queue:
                ss.entrevista_queue.append(selected)
            st.success("Enviado a Comité y bloqueadas ediciones del HH.")

# ----------- ENTREVISTA -----------
def page_entrevista():
    st.markdown("# Entrevista (Gerencia)")
    ss = st.session_state
    if not ss.entrevista_queue:
        st.info("Aún no hay candidatos en cola. Desde **Pipeline** o **Tareas HH** puedes moverlos aquí.")
        return

    name = st.selectbox("Selecciona candidato", ss.entrevista_queue, key="ent_sel")
    st.markdown("### Rúbrica de gerencia (70%)")
    col1, col2, col3, col4 = st.columns(4)
    with col1: t1 = st.slider("Técnico", 0, 10, 7)
    with col2: t2 = st.slider("Cultura", 0, 10, 7)
    with col3: t3 = st.slider("Comunicación", 0, 10, 7)
    with col4: t4 = st.slider("Compensación/Ajuste", 0, 10, 7)
    gerencia_pct = (t1 + t2 + t3 + t4) / 40 * 70

    st.markdown("### Checklist HH (30%)")
    hh = ss.hh_tasks.get(name, {})
    hh_pct = 0
    if hh:
        hh_compl = sum([1 if hh.get("contacto") else 0, 1 if hh.get("agendada") else 0, 1 if hh.get("feedback") else 0]) / 3
        notas = 1.0 if (all(hh.get("fortalezas",["","",""])) and all(hh.get("riesgos",["",""]))) else 0.0
        hh_pct = ((hh_compl*0.7) + (notas*0.3)) * 30

    total = round(gerencia_pct + hh_pct, 1)
    st.write(f"**Score consolidado:** {total}/100")
    sem = "Verde (≥70)" if total >= 70 else ("Ámbar (60–69)" if total >= 60 else "Rojo (<60)")
    st.write("**Semáforo:**", sem)

    x1, x2, x3 = st.columns(3)
    with x1:
        if st.button("Go (avanzar)"):
            st.success("Marca Go. Puedes mover a Oferta.")
    with x2:
        if st.button("Stand-by"):
            st.info("Marcado Stand-by.")
    with x3:
        if st.button("No continúa"):
            st.warning("Marcado No continúa.")

    st.write("---")
    if st.button("Mover a Oferta"):
        if name not in ss.oferta_queue:
            ss.oferta_queue.append(name)
        st.success("Candidato movido a **Oferta**.")

# ----------- OFERTA (con FIX a KeyError) -----------
def page_oferta():
    st.markdown("# Oferta")
    ss = st.session_state
    if not ss.oferta_queue:
        st.info("No hay candidatos para oferta. Muévelos desde **Entrevista (Gerencia)**.")
        return

    cand = st.selectbox("Candidato", ss.oferta_queue, key="offer_sel")

    # Aseguramos que exista una entrada en offers ANTES de presionar cualquier botón
    default_offer = {
        "puesto":"", "ubicacion":"", "modalidad":"Presencial", "contrato":"Indeterminado",
        "salario":"", "beneficios":"", "inicio":str(date.today()+timedelta(days=14)), "caduca":str(date.today()+timedelta(days=7)),
        "aprobadores":"Gerencia; Legal; Finanzas", "estado":"Borrador", "timeline":[("Creado", datetime.utcnow().isoformat())]
    }
    offer = ss.offers.setdefault(cand, default_offer)

    with st.form("form_oferta"):
        c1, c2, c3 = st.columns(3)
        with c1: offer["puesto"] = st.text_input("Puesto", offer["puesto"])
        with c2: offer["ubicacion"] = st.text_input("Ubicación", offer["ubicacion"])
        with c3: offer["modalidad"] = st.selectbox("Modalidad", ["Presencial","Híbrido","Remoto"], index=["Presencial","Híbrido","Remoto"].index(offer["modalidad"]))
        c4, c5 = st.columns(2)
        with c4: offer["contrato"] = st.selectbox("Tipo contrato", ["Indeterminado","Plazo fijo","Servicios"], index=["Indeterminado","Plazo fijo","Servicios"].index(offer["contrato"]))
        with c5: offer["salario"] = st.text_input("Salario (rango/neto)", offer["salario"])
        offer["beneficios"] = st.text_area("Bonos/beneficios", offer["beneficios"])
        d1, d2 = st.columns(2)
        with d1: offer["inicio"] = str(st.date_input("Fecha de inicio", value=pd.to_datetime(offer["inicio"]).date()))
        with d2: offer["caduca"] = str(st.date_input("Caducidad de oferta", value=pd.to_datetime(offer["caduca"]).date()))
        offer["aprobadores"] = st.text_input("Aprobadores", offer["aprobadores"])
        save = st.form_submit_button("Guardar oferta")
    if save:
        ss.offers[cand] = offer
        ss.offers[cand]["timeline"].append(("Guardada", datetime.utcnow().isoformat()))
        st.success("Oferta guardada.")

    colx, coly, colz = st.columns(3)
    with colx:
        if st.button("Enviar"):
            ss.offers[cand]["estado"] = "Enviada"
            ss.offers[cand]["timeline"].append(("Enviada", datetime.utcnow().isoformat()))
            st.success("Oferta enviada.")
    with coly:
        if st.button("Registrar contraoferta"):
            ss.offers[cand]["estado"] = "Contraoferta"
            ss.offers[cand]["timeline"].append(("Contraoferta", datetime.utcnow().isoformat()))
            st.info("Contraoferta registrada.")
    with colz:
        if st.button("Marcar aceptada"):
            ss.offers[cand]["estado"] = "Aceptada"
            ss.offers[cand]["timeline"].append(("Aceptada", datetime.utcnow().isoformat()))
            if cand not in ss.onboarding:
                ss.onboarding[cand] = default_onboarding()
            st.success("Oferta aceptada. Se generaron tareas de Onboarding.")

    st.write("**Estado actual:**", ss.offers[cand]["estado"])
    st.write("**Línea de tiempo:**")
    for ev, ts in ss.offers[cand]["timeline"]:
        st.markdown(f"- {ev} · {ts}")

def default_onboarding():
    today = date.today()
    return {
        "Contrato firmado": {"due": today + timedelta(hours=48), "done": False},
        "Documentos completos": {"due": today + timedelta(hours=72), "done": False},
        "Usuario/email creado": {"due": today + timedelta(hours=24), "done": False},
        "Acceso SAP IS-H": {"due": today + timedelta(hours=48), "done": False},
        "Examen médico": {"due": today + timedelta(days=5), "done": False},
        "Inducción día 1": {"due": today + timedelta(days=1), "done": False},
        "EPP/Uniforme entregado": {"due": today + timedelta(days=1), "done": False},
        "Plan 30-60-90 cargado": {"due": today + timedelta(days=7), "done": False},
    }

# ----------- ONBOARDING -----------
def page_onboarding():
    st.markdown("# Onboarding")
    ss = st.session_state
    if not ss.onboarding:
        st.info("Aún no hay candidatos en Onboarding.")
        return

    cand = st.selectbox("Candidato", list(ss.onboarding.keys()), key="onb_sel")
    tasks = ss.onboarding[cand]

    for k, v in tasks.items():
        due = v["due"]
        now = datetime.now().date()
        days_left = (due - now).days if isinstance(due, date) else 0
        badge_class = "sla-green"
        if days_left < 0:
            badge_class = "sla-red"
        elif days_left <= 1:
            badge_class = "sla-amber"
        b = f"<span class='sla-badge {badge_class}'>SLA: {days_left}d</span>"

        col1, col2, col3 = st.columns([0.6,0.25,0.15])
        with col1: st.markdown(f"**{k}**  {b}", unsafe_allow_html=True)
        with col2: tasks[k]["due"] = st.date_input("Vence", value=due, key=f"due_{k}")
        with col3: tasks[k]["done"] = st.checkbox("Hecho", value=v["done"], key=f"done_{k}")
        st.markdown("---")

    if st.button("Guardar checklist"):
        ss.onboarding[cand] = tasks
        st.success("Onboarding actualizado.")

def page_analytics():
    st.markdown("# Analytics")
    st.info("Aquí podrás integrar tus reportes/dashboards.")

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

# ======== AGENTES ========
def page_agentes():
    st.markdown("# Agentes")
    st.caption("Crea asistentes especializados. Se guardan en esta sesión.")

    with st.form("form_agente"):
        colA, colB = st.columns([1.1, 1])
        with colA:
            rol = st.selectbox("Rol*", ["Headhunter", "Coordinador RR.HH.", "Admin RR.HH.", "Hiring Manager", "Gerencia/Comité"], index=0)
            objetivo = st.text_input("Objetivo*", "Identificar a los mejores profesionales para el cargo definido en el JD")
            backstory = st.text_area("Backstory*", "Eres un analista de RR.HH. con experiencia en análisis de documentos, CV y currículums.", height=100)
            guardrails = st.text_area("Guardrails", "No compartas datos sensibles. Cita la fuente (CV o JD) al argumentar.", height=80)
            herramientas = st.multiselect("Herramientas", ["Parser de PDF", "Recomendador de candidatos", "Clasificador de skills"], default=["Parser de PDF","Recomendador de candidatos"])
        with colB:
            st.markdown("### Permisos y alcance")
            st.markdown("- **RLS** por puesto.")
            st.markdown("- **Acciones según rol**.")
            st.markdown("- **Auditoría**: toda acción queda registrada.")
        submit = st.form_submit_button("Crear/Actualizar Asistente")
    if submit:
        existing = next((a for a in st.session_state.agentes if a["rol"] == rol), None)
        data = {"rol": rol, "objetivo": objetivo, "backstory": backstory, "guardrails": guardrails, "herramientas": herramientas}
        if existing:
            existing.update(data)
        else:
            st.session_state.agentes.append(data)
        st.success("Asistente guardado.")

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
    if page == "definicion":
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
    sidebar()
    router()

if __name__ == "__main__":
    main()
