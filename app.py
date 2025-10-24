# app.py
# -*- coding: utf-8 -*-

import io
import base64
from pathlib import Path
from datetime import date, datetime, timedelta

import streamlit as st
import pandas as pd
import plotly.express as px
from PyPDF2 import PdfReader

# =============================================================================
# THEME & COLORS
# =============================================================================
PRIMARY_GREEN = "#00CD78"
SIDEBAR_BG = "#10172A"
BOX_DARK = "#132840"
BOX_DARK_HOV = "#193355"
TEXT_LIGHT = "#FFFFFF"
MAIN_BG = "#F7FBFF"
BOX_LIGHT = "#F1F7FD"
BOX_LIGHT_B = "#E3EDF6"
TITLE_DARK = "#142433"
BAR_DEFAULT = "#E9F3FF"
BAR_GOOD = "#33FFAC"

CSS = f"""
:root {{
  --green: {PRIMARY_GREEN};
  --sidebar-bg: {SIDEBAR_BG};
  --box: {BOX_DARK};
  --box-hover: {BOX_DARK_HOV};
  --text: {TEXT_LIGHT};
  --main-bg: {MAIN_BG};
  --box-light: {BOX_LIGHT};
  --box-light-border: {BOX_LIGHT_B};
  --title-dark: {TITLE_DARK};
}}
html, body, [data-testid="stAppViewContainer"] {{
  background: var(--main-bg) !important;
}}
.block-container {{ background: transparent !important; }}
/* Sidebar */
[data-testid="stSidebar"] {{
  background: var(--sidebar-bg) !important; color: var(--text) !important;
}}
[data-testid="stSidebar"] h1,[data-testid="stSidebar"] h2,[data-testid="stSidebar"] h3,
[data-testid="stSidebar"] h4,[data-testid="stSidebar"] h5,[data-testid="stSidebar"] h6,
[data-testid="stSidebar"] .stMarkdown p strong {{ color: var(--green) !important; }}
[data-testid="stSidebar"] label,[data-testid="stSidebar"] p,[data-testid="stSidebar"] span {{
  color: var(--text) !important;
}}
/* Boxes sidebar */
[data-testid="stSidebar"] [data-testid="stSelectbox"] > div > div,
[data-testid="stSidebar"] [data-baseweb="select"],
[data-testid="stSidebar"] [data-testid="stTextArea"] textarea,
[data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] {{
  background: var(--box) !important; color: var(--text) !important;
  border: 1.5px solid var(--box) !important; border-radius: 14px !important; box-shadow: none !important;
}}
[data-testid="stSidebar"] [data-testid="stTextArea"] textarea:hover,
[data-testid="stSidebar"] [data-testid="stTextArea"] textarea:focus,
[data-testid="stSidebar"] [data-testid="stSelectbox"] > div > div:hover,
[data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"]:hover {{
  border-color: var(--box-hover) !important;
}}
[data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] * {{ color: var(--text) !important; }}
[data-testid="stSidebar"] [data-testid="stFileUploaderFile"] {{
  background: var(--box) !important; border: 1px solid var(--box) !important; color: var(--text) !important;
}}
/* Buttons */
.stButton > button {{
  background: var(--green) !important; color: #082017 !important;
  border-radius: 10px !important; border: none !important; padding: .45rem .9rem !important; font-weight: 600 !important;
}}
.stButton > button:hover {{ filter: brightness(0.95); }}
/* Headings */
h1, h2, h3 {{ color: var(--title-dark); }}
h1 strong, h2 strong, h3 strong {{ color: var(--green); }}
/* Inputs body */
.block-container [data-testid="stSelectbox"] > div > div,
.block-container [data-baseweb="select"],
.block-container [data-testid="stTextInput"] input,
.block-container [data-testid="stTextArea"] textarea {{
  background: var(--box-light) !important; color: var(--title-dark) !important;
  border: 1.5px solid var(--box-light-border) !important; border-radius: 10px !important;
}}
/* Table */
.block-container table {{
  background: #fff !important; border: 1px solid var(--box-light-border) !important; border-radius: 8px !important;
}}
.block-container thead th {{ background: var(--box-light) !important; color: var(--title-dark) !important; }}
/* Tab pills (visibles) */
.stTabs [role="tablist"] {{
  display: flex; gap: 16px; border-bottom: 1px solid var(--box-light-border); margin-bottom: 10px;
}}
.stTabs [role="tab"] {{
  background: #fff; color: #4b5563; border: 1px solid var(--box-light-border);
  border-bottom: 3px solid transparent; border-radius: 10px 10px 0 0; padding: 8px 14px;
}}
.stTabs [aria-selected="true"] {{
  color: var(--green) !important; border-bottom: 3px solid var(--green) !important; font-weight: 700;
}}
/* PDF viewer */
#pdf_candidate {{ background: var(--box-light) !important; border: 1.5px solid var(--box-light-border) !important;
  color: var(--title-dark) !important; border-radius: 10px !important; }}
.pdf-frame {{ border: 1px solid var(--box-light-border); border-radius: 12px; overflow: hidden; background: #fff; }}
/* Badges */
.badge {{
  display:inline-block; padding:2px 8px; border-radius:12px; font-size:12px; font-weight:600;
}}
.badge-green {{ background:#E7FFF6; color:#067A55; border:1px solid #B9F5E5; }}
.badge-amber {{ background:#FFF7E6; color:#925B00; border:1px solid #FFE1AE; }}
.badge-red {{ background:#FFECEC; color:#9C1C1C; border:1px solid #FFCACA; }}
"""

st.set_page_config(page_title="SelektIA", page_icon="🧠", layout="wide")
st.markdown(f"<style>{CSS}</style>", unsafe_allow_html=True)

# =============================================================================
# UTILITIES
# =============================================================================
def extract_text_from_file(uploaded_file) -> str:
    try:
        suffix = Path(uploaded_file.name).suffix.lower()
        if suffix == ".pdf":
            pdf_reader = PdfReader(io.BytesIO(uploaded_file.read()))
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() or ""
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
        pct_k = hits / len(kws)
        base += int(pct_k * 70)
        reasons.append(f"{hits}/{len(kws)} keywords encontradas — Coincidencias: {', '.join([k for k in kws if k in text_low])[:120]}")
    jd_terms = [t for t in set(jd_low.split()) if len(t) > 3]
    match_terms = sum(1 for t in jd_terms if t in text_low)
    if jd_terms:
        pct_jd = match_terms / len(jd_terms)
        base += int(pct_jd * 30)
        reasons.append("Coincidencias con el JD (aprox.)")
    base = max(0, min(100, base))
    return base, " — ".join(reasons)

def pdf_viewer_pdfjs(file_bytes: bytes, height=520, scale=1.1):
    b64 = base64.b64encode(file_bytes).decode("utf-8")
    pdfjs = "https://mozilla.github.io/pdf.js/web/viewer.html?file="
    src = f"{pdfjs}data:application/pdf;base64,{b64}#zoom={int(scale*100)}"
    st.markdown(
        f"""<div class="pdf-frame">
              <iframe src="{src}" style="width:100%; height:{height}px; border:0;" title="PDF Viewer"></iframe>
            </div>""",
        unsafe_allow_html=True,
    )

def sla_badge(due: datetime) -> str:
    now = datetime.now()
    if due is None:
        return '<span class="badge badge-amber">SLA: sin fecha</span>'
    delta = due - now
    hours = int(delta.total_seconds() // 3600)
    if hours < 0:
        return f'<span class="badge badge-red">SLA vencido {abs(hours)}h</span>'
    if hours <= 24:
        return f'<span class="badge badge-amber">SLA {hours}h</span>'
    return f'<span class="badge badge-green">SLA {hours}h</span>'

def semaforo_badge(score: int) -> str:
    if score >= 70:
        return '<span class="badge badge-green">Verde ≥70</span>'
    if score >= 60:
        return '<span class="badge badge-amber">Ámbar 60–69</span>'
    return '<span class="badge badge-red">Rojo &lt;60</span>'

def redact_acta_breve(candidato: str, score: int, fortalezas: list[str], riesgos: list[str], pretension: str, disponibilidad: str, flags: list[str]) -> str:
    return (
        f"Acta breve — Comité\n"
        f"Candidata/o: {candidato}\n"
        f"Score total: {score}/100\n"
        f"Fortalezas: {', '.join(fortalezas[:3])}\n"
        f"Riesgos: {', '.join(riesgos[:2])}\n"
        f"Pretensión: {pretension} | Disponibilidad: {disponibilidad}\n"
        f"Red flags: {', '.join(flags) if flags else 'Ninguna'}\n"
        f"Fecha: {datetime.now():%Y-%m-%d %H:%M}\n"
    )

def txt_to_bytes(text: str) -> bytes:
    return text.encode("utf-8")

# =============================================================================
# INITIAL STATE
# =============================================================================
if "candidates" not in st.session_state:
    st.session_state.candidates = []
if "uploader_key" not in st.session_state:
    st.session_state.uploader_key = "u1"

# demo positions
if "positions" not in st.session_state:
    st.session_state.positions = pd.DataFrame([
        {"ID":"10,645,194","Puesto":"Desarrollador/a Backend (Python)","Días Abierto":3,"Leads":1800,"Nuevos":115,"Recruiter Screen":35,"HM Screen":7,"Entrevista Telefónica":14,"Entrevista Presencial":15,"Ubicación":"Lima, Perú","Hiring Manager":"Rivers Brykson","Estado":"Abierto"},
        {"ID":"10,376,415","Puesto":"VP de Marketing","Días Abierto":28,"Leads":8100,"Nuevos":1,"Recruiter Screen":15,"HM Screen":35,"Entrevista Telefónica":5,"Entrevista Presencial":7,"Ubicación":"Santiago, Chile","Hiring Manager":"Angela Cruz","Estado":"Abierto"},
        {"ID":"10,376,646","Puesto":"Planner de Demanda","Días Abierto":28,"Leads":2300,"Nuevos":26,"Recruiter Screen":3,"HM Screen":8,"Entrevista Telefónica":6,"Entrevista Presencial":3,"Ubicación":"Ciudad de México, MX","Hiring Manager":"Rivers Brykson","Estado":"Abierto"},
    ])

# Pipeline simple
if "pipeline" not in st.session_state:
    # each: name, score, stage
    st.session_state.pipeline = []

# Comité (gerencia)
if "committee" not in st.session_state:
    st.session_state.committee = []  # list of candidate names

# Headhunter Tasks store
if "hh_tasks" not in st.session_state:
    # per candidate name
    st.session_state.hh_tasks = {}
# Offers store
if "offers" not in st.session_state:
    # per candidate name
    st.session_state.offers = {}

# =============================================================================
# SIDEBAR
# =============================================================================
with st.sidebar:
    st.image("assets/logo-wayki.png", use_column_width=True)
    st.markdown("### Definición del puesto")
    puesto = st.selectbox(
        "Puesto",
        ["Enfermera/o Asistencial","Tecnólogo/a Médico","Recepcionista de Admisión","Médico/a General","Químico/a Farmacéutico/a"],
        index=0, key="puesto"
    )
    st.markdown("### Descripción del puesto (texto libre)")
    jd_text = st.text_area("Resume el objetivo del puesto, responsabilidades, protocolos y habilidades deseadas.",
                           height=120, key="jd", label_visibility="collapsed")
    st.markdown("### Palabras clave del perfil\n*(ajústalas si es necesario)*")
    kw_text = st.text_area(
        "HIS, SAP IS-H, BLS, ACLS, IAAS, educación al paciente, seguridad…",
        value="HIS, SAP IS-H, BLS, ACLS, IAAS, educación al paciente, seguridad del paciente, protocolos",
        height=110, key="kw", label_visibility="collapsed",
    )
    st.markdown("### Subir CVs (PDF o TXT)")
    files = st.file_uploader("Drag and drop files here", key=st.session_state.uploader_key,
                             type=["pdf","txt"], accept_multiple_files=True, label_visibility="collapsed")

    if files:
        st.session_state.candidates = []
        for f in files:
            b = f.read()
            f.seek(0)
            text = extract_text_from_file(f)
            score, reasons = simple_score(text, jd_text, kw_text)
            st.session_state.candidates.append({
                "Name": f.name, "Score": score, "Reasons": reasons,
                "_bytes": b, "_is_pdf": Path(f.name).suffix.lower()==".pdf",
            })
        # refresh pipeline scaffold
        st.session_state.pipeline = [
            {"name": c["Name"], "score": c["Score"], "stage": "Leads"} for c in st.session_state.candidates
        ]

    st.divider()
    if st.button("Limpiar Lista", use_container_width=True):
        st.session_state.candidates = []
        st.session_state.pipeline = []
        st.session_state.committee = []
        st.session_state.hh_tasks = {}
        st.session_state.offers = {}
        st.session_state.uploader_key = f"u{pd.Timestamp.utcnow().value}"
        st.rerun()

# =============================================================================
# TABS
# =============================================================================
tab_puestos, tab_eval, tab_pipe, tab_gerencia, tab_hh, tab_oferta = st.tabs(
    ["📋 Puestos", "🧪 Evaluación de CVs", "👥 Pipeline de Candidatos", "🏛️ Entrevista (Gerencia)", "📝 Tareas del Headhunter", "📄 Oferta"]
)

# -----------------------------------------------------------------------------
# TAB: Puestos
# -----------------------------------------------------------------------------
with tab_puestos:
    st.markdown("## SelektIA – **Puestos**")
    col_top_l, col_top_c, col_top_r = st.columns([1.8, 1, 1])
    with col_top_l:
        q = st.text_input("Buscar (puesto, ubicación, ID, hiring manager…)", placeholder="Ej: Lima, 10645194, Angela Cruz")
    with col_top_c:
        show_filters = st.checkbox("Mostrar filtros", value=False)
    with col_top_r:
        st.metric("Puestos totales", len(st.session_state.positions))

    df_pos = st.session_state.positions.copy()
    if show_filters:
        with st.expander("Filtros", expanded=True):
            colf1, colf2, colf3, colf4 = st.columns(4)
            with colf1:
                ubic = st.multiselect("Ubicación", sorted(df_pos["Ubicación"].unique().tolist()))
            with colf2:
                hm = st.multiselect("Hiring Manager", sorted(df_pos["Hiring Manager"].unique().tolist()))
            with colf3:
                estado = st.multiselect("Estado", sorted(df_pos["Estado"].unique().tolist()))
            with colf4:
                dias_abierto = st.slider("Días abierto (máx)", min_value=0, max_value=60, value=60)
        if ubic: df_pos = df_pos[df_pos["Ubicación"].isin(ubic)]
        if hm: df_pos = df_pos[df_pos["Hiring Manager"].isin(hm)]
        if estado: df_pos = df_pos[df_pos["Estado"].isin(estado)]
        df_pos = df_pos[df_pos["Días Abierto"] <= dias_abierto]

    if q:
        ql = q.lower()
        df_pos = df_pos[
            df_pos["Puesto"].str.lower().str.contains(ql) |
            df_pos["Ubicación"].str.lower().str.contains(ql) |
            df_pos["Hiring Manager"].str.lower().str.contains(ql) |
            df_pos["ID"].astype(str).str.contains(ql)
        ]

    st.caption(f"Mostrando **{len(df_pos)}** posiciones")
    st.dataframe(
        df_pos[["Puesto","Días Abierto","Leads","Nuevos","Recruiter Screen","HM Screen","Entrevista Telefónica","Entrevista Presencial","Ubicación","Hiring Manager","Estado","ID"]]
        .sort_values(["Estado","Días Abierto","Leads"], ascending=[True, True, False]),
        use_container_width=True, height=420,
    )

# -----------------------------------------------------------------------------
# TAB: Evaluación de CVs
# -----------------------------------------------------------------------------
with tab_eval:
    st.markdown("## SelektIA – **Resultados de evaluación**  ↪️")
    if not st.session_state.candidates:
        st.info("Carga CVs en la barra lateral. El análisis se ejecuta automáticamente.")
    else:
        df = pd.DataFrame(st.session_state.candidates)
        df_sorted = df.sort_values("Score", ascending=False)

        st.markdown("### Ranking de Candidatos")
        st.dataframe(df_sorted[["Name","Score","Reasons"]], use_container_width=True, height=260)

        st.markdown("### Comparación de puntajes")
        bar_colors = [BAR_GOOD if s >= 60 else BAR_DEFAULT for s in df_sorted["Score"]]
        fig = px.bar(df_sorted, x="Name", y="Score", title="Comparación de puntajes (todos los candidatos)")
        fig.update_traces(marker_color=bar_colors, hovertemplate="%{x}<br>Score: %{y}")
        fig.update_layout(plot_bgcolor="#FFFFFF", paper_bgcolor="rgba(0,0,0,0)", font=dict(color=TITLE_DARK), xaxis_title=None, yaxis_title="Score")
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("### Visor de CV (PDF/TXT)  ↪️")
        all_names = df_sorted["Name"].tolist()
        selected_name = st.selectbox("Elige un candidato", all_names, index=0, key="pdf_candidate", label_visibility="collapsed")
        cand = df.loc[df["Name"] == selected_name].iloc[0]
        if cand["_is_pdf"] and cand["_bytes"]:
            pdf_viewer_pdfjs(cand["_bytes"], height=480, scale=1.05)
            st.download_button(f"Descargar {selected_name}", data=cand["_bytes"], file_name=selected_name, mime="application/pdf")
        else:
            st.info(f"'{selected_name}' es un TXT. Mostrando contenido abajo:")
            with st.expander("Ver contenido TXT", expanded=True):
                try:
                    txt = cand["_bytes"].decode("utf-8", errors="ignore")
                except Exception:
                    txt = "(No se pudo decodificar)"
                st.text_area("Contenido", value=txt, height=400, label_visibility="collapsed")

# -----------------------------------------------------------------------------
# TAB: Pipeline de Candidatos (lista comprimida no editable + hover en detalles)
# -----------------------------------------------------------------------------
with tab_pipe:
    st.markdown("## SelektIA – **Pipeline de Candidatos**")
    if not st.session_state.pipeline:
        st.info("Aún no hay candidatos en pipeline. Sube CVs para iniciar.")
    else:
        left, right = st.columns([1.2, 1])
        with left:
            st.caption("Candidatos (haz clic para ver detalles a la derecha)")
            for row in st.session_state.pipeline:
                label = f"🟢 {row['name']} — {row['score']}%"
                if st.button(label, key=f"btn_{row['name']}", use_container_width=True):
                    st.session_state["pipe_selected"] = row['name']
        with right:
            sel = st.session_state.get("pipe_selected", None)
            if not sel:
                st.info("Selecciona un candidato de la lista.")
            else:
                dat = next((c for c in st.session_state.candidates if c["Name"] == sel), None)
                st.markdown(f"### Detalle del candidato\n**{sel}**")
                st.markdown("**Match estimado**: " + ("✅ Alto" if dat and dat["Score"]>=60 else "⚠️ Medio/Bajo"))
                skills_validated = [k.strip() for k in (st.session_state.kw if "kw" in st.session_state else kw_text).split(",")][:1]
                st.markdown("**Validated Skills**")
                st.write(skills_validated if skills_validated else ["—"])
                st.markdown("**Likely Skills**")
                st.write(["—"])
                st.markdown("**Skills to Validate**")
                st.write([k.strip() for k in kw_text.split(",")][:6])

# -----------------------------------------------------------------------------
# TAB: Entrevista (Gerencia) — Input simple para simular rúbrica y decisión
# -----------------------------------------------------------------------------
with tab_gerencia:
    st.markdown("## SelektIA – **Entrevista (Gerencia)**")
    st.caption("Candidatos enviados por el Headhunter al Comité (solo lectura de lista).")
    if not st.session_state.committee:
        st.info("Aún no hay candidatos en comité. Usa el botón *Enviar a Comité* desde **Tareas del Headhunter**.")
    else:
        sel = st.selectbox("Selecciona candidato", st.session_state.committee)
        st.markdown("---")
        st.subheader("Rúbrica de Gerencia (70%)")
        colg1, colg2, colg3 = st.columns(3)
        with colg1:
            r_tech = st.slider("Técnico (0–35)", 0, 35, 25, key=f"rg_tech_{sel}")
        with colg2:
            r_culture = st.slider("Cultura (0–20)", 0, 20, 14, key=f"rg_cult_{sel}")
        with colg3:
            r_comp = st.slider("Compensación (0–15)", 0, 15, 10, key=f"rg_comp_{sel}")
        score_rubrica = r_tech + r_culture + r_comp  # /70
        st.write(f"Subtotal rúbrica: **{score_rubrica}/70**")

        st.subheader("Checklist HH (30%) (traído de Tareas HH)")
        hh = st.session_state.hh_tasks.get(sel, {})
        hh_score = hh.get("hh_score", 0)
        st.write(f"Subtotal HH: **{hh_score}/30**")

        total = score_rubrica + hh_score
        st.markdown(f"### Score consolidado: **{total}/100**  {semaforo_badge(total)}", unsafe_allow_html=True)

        st.subheader("Decisión")
        decision = st.selectbox("Resultado", ["Go","Stand-by","No continúa"], index=0, key=f"decision_{sel}")
        reason = st.text_input("Razón estandarizada (breve)", key=f"reason_{sel}")
        colb1, colb2 = st.columns(2)
        with colb1:
            if st.button("Mover a Oferta", disabled=(decision!="Go")):
                # bootstrap offer record
                st.session_state.offers.setdefault(sel, {"status":"En preparación","timeline":[(datetime.now(),"Creación de oferta")]})
                st.success("Candidato movido a Oferta")
        with colb2:
            if st.button("Descartar con feedback", disabled=(decision=="Go")):
                st.success(f"Descartado con feedback: {reason or '—'}")

# -----------------------------------------------------------------------------
# TAB: Tareas del Headhunter — NUEVA
# -----------------------------------------------------------------------------
with tab_hh:
    st.markdown("## SelektIA – **Tareas del Headhunter**")
    if not st.session_state.pipeline:
        st.info("Sube CVs para gestionar tareas del HH.")
    else:
        left, right = st.columns([1,1.2])
        with left:
            sel_hh = st.selectbox("Candidata/o para cerrar etapa HH", [p["name"] for p in st.session_state.pipeline])
            # ensure record
            rec = st.session_state.hh_tasks.setdefault(sel_hh, {
                "contacto": False, "agendada": False, "feedback": False,
                "fortalezas": "", "riesgos": "", "pretension": "", "disponibilidad": "",
                "files": [], "due": (datetime.now()+timedelta(hours=36)).replace(minute=0, second=0, microsecond=0),
                "locked": False, "hh_score": 0, "acta": None
            })
            st.markdown("#### Checklist (HH) — hoy")
            ch1 = st.checkbox("✅ Contacto hecho", value=rec["contacto"], disabled=rec["locked"], key=f"hh_c1_{sel_hh}")
            ch2 = st.checkbox("✅ Entrevista agendada", value=rec["agendada"], disabled=rec["locked"], key=f"hh_c2_{sel_hh}")
            ch3 = st.checkbox("✅ Feedback recibido", value=rec["feedback"], disabled=rec["locked"], key=f"hh_c3_{sel_hh}")
            # notes
            st.markdown("#### Notas (obligatorias)")
            f = st.text_input("3 fortalezas (coma separada)", value=rec["fortalezas"], disabled=rec["locked"], key=f"hh_f_{sel_hh}")
            r = st.text_input("2 riesgos (coma separada)", value=rec["riesgos"], disabled=rec["locked"], key=f"hh_r_{sel_hh}")
            p = st.text_input("Pretensión salarial", value=rec["pretension"], disabled=rec["locked"], key=f"hh_p_{sel_hh}")
            d = st.text_input("Disponibilidad", value=rec["disponibilidad"], disabled=rec["locked"], key=f"hh_d_{sel_hh}")
            st.markdown("#### Adjuntos (BLS/ACLS, colegiatura)")
            up = st.file_uploader("PDF/IMG", type=["pdf","png","jpg","jpeg"], key=f"hh_files_{sel_hh}", disabled=rec["locked"], accept_multiple_files=True)
            if up and not rec["locked"]:
                for fu in up:
                    rec["files"].append({"name": fu.name, "bytes": fu.read()})

            st.markdown("#### SLA")
            due = st.date_input("Fecha límite", value=rec["due"].date() if rec["due"] else date.today(), disabled=rec["locked"], key=f"hh_due_date_{sel_hh}")
            due_hour = st.time_input("Hora límite", value=(rec["due"].time() if rec["due"] else datetime.now().time()), disabled=rec["locked"], key=f"hh_due_time_{sel_hh}")
            rec["due"] = datetime.combine(due, due_hour)
            st.markdown(sla_badge(rec["due"]), unsafe_allow_html=True)

            # Save interim
            rec["contacto"], rec["agendada"], rec["feedback"] = ch1, ch2, ch3
            rec["fortalezas"], rec["riesgos"], rec["pretension"], rec["disponibilidad"] = f, r, p, d

            # compute HH score (0-30)
            check_points = 10*int(ch1) + 10*int(ch2) + 10*int(ch3)
            notes_ok = (len([x for x in f.split(",") if x.strip()]) >= 3) and (len([x for x in r.split(",") if x.strip()]) >= 2) and p and d
            docs_ok = any("bls" in f_.get("name","").lower() or "acls" in f_.get("name","").lower() for f_ in rec["files"]) \
                      and any("colegi" in f_.get("name","").lower() for f_ in rec["files"])
            bonus = 0
            if notes_ok: bonus += 10  # virtual, capped at 30 below
            if docs_ok:  bonus += 10
            rec["hh_score"] = min(30, check_points // 1)  # base from checklist; you can swap to (check_points + bonus)

            st.markdown("---")
            disabled_send = rec["locked"] or not (ch1 and ch2 and ch3 and notes_ok and docs_ok)
            if st.button("Enviar a Comité", disabled=disabled_send, key=f"hh_send_{sel_hh}"):
                # lock record & generate acta
                rec["locked"] = True
                flags = []
                if not docs_ok:
                    flags.append("Documentación incompleta (BLS/ACLS o colegiatura)")
                rec["acta"] = redact_acta_breve(
                    sel_hh, rec["hh_score"], [x.strip() for x in f.split(",") if x.strip()],
                    [x.strip() for x in r.split(",") if x.strip()], p, d, flags
                )
                if sel_hh not in st.session_state.committee:
                    st.session_state.committee.append(sel_hh)
                st.success("Enviado a Comité. Edición bloqueada.")
            if rec.get("acta"):
                st.download_button("Descargar acta breve", data=txt_to_bytes(rec["acta"]),
                                   file_name=f"Acta_{sel_hh}.txt", mime="text/plain")

        with right:
            st.markdown("### Consolidado para Gerencia (hoy)")
            sel2 = st.selectbox("Candidata/o", [p["name"] for p in st.session_state.pipeline], key="hh_sel2")
            rec2 = st.session_state.hh_tasks.get(sel2, {})
            # rubrica simulada (user verá consolidado real en tab gerencia)
            r_70 = st.slider("Rúbrica de Gerencia (estimada) /70", 0, 70, 48, key=f"hh_r70_{sel2}")
            hh_30 = rec2.get("hh_score", 0)
            total = r_70 + hh_30
            st.markdown(f"**Score total:** {total}/100  {semaforo_badge(total)}", unsafe_allow_html=True)

            # Red flags
            flags = []
            if not any("bls" in f_.get("name","").lower() or "acls" in f_.get("name","").lower() for f_ in rec2.get("files",[])):
                flags.append("Faltan BLS/ACLS")
            if not any("colegi" in f_.get("name","").lower() for f_ in rec2.get("files",[])):
                flags.append("Coleg. no vigente")
            # gaps (simples)
            if st.session_state.candidates:
                cdat = next((c for c in st.session_state.candidates if c["Name"]==sel2), None)
                if cdat and cdat["Score"] < 45:
                    flags.append("Brecha HIS/SAP IS-H/IAAS")
            if flags:
                st.error("Red flags: " + ", ".join(flags))
            else:
                st.success("Sin red flags")

            st.markdown("### Reunión de decisión (mañana)")
            dtime = st.time_input("Horario sugerido (20 min)", value=datetime.now().time(), key=f"hh_t_{sel2}")
            decision = st.selectbox("Salida", ["Go","Stand-by","No continúa"], key=f"hh_dec_{sel2}")
            reason = st.text_input("Razones estandarizadas", key=f"hh_reason_{sel2}")
            colx, coly = st.columns(2)
            with colx:
                if st.button("Mover a Oferta", disabled=(decision!="Go")):
                    st.session_state.offers.setdefault(sel2, {"status":"En preparación","timeline":[(datetime.now(),"Creación de oferta")]})
                    st.success("Candidato movido a Oferta")
            with coly:
                if st.button("Descartar con feedback", disabled=(decision=="Go")):
                    st.success(f"Descartado. Motivo: {reason or '—'}")

            st.markdown("### Micro-plantillas")
            st.code(
f"""Asunto: Comité — {{Puesto}} — {sel2}
Resumen: Score total {{score}}/100 · Pretensión {{monto}} · Inicio {{fecha}}.
Fortalezas: {{3 bullets}}
Riesgos: {{2 bullets}}
Docs: BLS/ACLS {{vigente?}}, colegiatura {{habilitada?}}
Propuesta: {{Go / Stand-by / No continúa}}.
Saludos, {{Tu nombre}}""", language="text")
            st.code(
f"""Hola {sel2},
Confirmamos tu entrevista con Gerencia el {{fecha}} a las {{hora}} (duración {{min}} min).
Por favor, lleva BLS/ACLS y colegiatura.
¡Gracias! {{Firma}}""", language="text")

# -----------------------------------------------------------------------------
# TAB: Oferta — NUEVA
# -----------------------------------------------------------------------------
with tab_oferta:
    st.markdown("## SelektIA – **Oferta**")
    candidates_for_offer = sorted(st.session_state.offers.keys())
    if not candidates_for_offer:
        st.info("Aún no hay candidatos en Oferta. Usa el botón *Mover a Oferta* desde Gerencia o HH.")
    else:
        sel_o = st.selectbox("Candidata/o", candidates_for_offer)
        offer = st.session_state.offers.setdefault(sel_o, {"status":"En preparación","timeline":[]})

        st.markdown("### Formulario de Oferta")
        c1, c2, c3 = st.columns(3)
        with c1:
            of_puesto = st.text_input("Puesto", value=st.session_state.get("puesto",""))
            of_ubic = st.selectbox("Ubicación", ["Lima, Perú","Santiago, Chile","Ciudad de México, MX","Remoto LATAM"])
        with c2:
            of_modal = st.selectbox("Modalidad", ["Presencial","Híbrido","Remoto"])
            of_contrato = st.selectbox("Tipo de contrato", ["Indeterminado","Plazo fijo","Servicio (honorarios)"])
        with c3:
            of_salario = st.text_input("Salario (rango y neto)", placeholder="USD 2,000–2,800 neto")
            of_benef = st.text_input("Bonos/beneficios", placeholder="Bono anual, EPS, alimentación")

        c4, c5, c6 = st.columns(3)
        with c4:
            of_inicio = st.date_input("Fecha de inicio", value=date.today()+timedelta(days=14))
        with c5:
            of_caduca = st.date_input("Caducidad de oferta", value=date.today()+timedelta(days=5))
        with c6:
            of_aprob = st.multiselect("Aprobadores", ["Gerencia","Legal","Finanzas"], default=["Gerencia","Legal","Finanzas"])

        st.markdown("---")
        colg, colh, coli, colj = st.columns(4)
        with colg:
            if st.button("Generar oferta (PDF)"):
                content = (
                    f"OFERTA\nCandidato: {sel_o}\nPuesto: {of_puesto}\nUbicación: {of_ubic}\n"
                    f"Modalidad: {of_modal} | Contrato: {of_contrato}\nSalario: {of_salario}\n"
                    f"Beneficios: {of_benef}\nInicio: {of_inicio} | Caduca: {of_caduca}\n"
                    f"Aprobadores: {', '.join(of_aprob)}\n"
                    f"Fecha: {datetime.now():%Y-%m-%d %H:%M}\n"
                )
                offer["last_pdf"] = txt_to_bytes(content)  # placeholder PDF: texto
                offer["timeline"].append((datetime.now(),"Oferta generada"))
                st.success("Oferta generada (texto).")
        with colh:
            if st.button("Enviar"):
                offer["status"] = "Enviada"
                offer["timeline"].append((datetime.now(),"Oferta enviada"))
                st.success("Oferta enviada al candidato (simulado). SLA recordatorios 48h/72h.")
        with coli:
            contra = st.text_input("Contraoferta (monto/notas)", value="", key=f"of_contra_{sel_o}")
            if st.button("Registrar contraoferta"):
                offer["status"] = "Contraoferta"
                offer["timeline"].append((datetime.now(), f"Contraoferta: {contra or '—'}"))
                st.warning("Contraoferta registrada.")
        with colj:
            if st.button("Marcar aceptada"):
                offer["status"] = "Aceptada"
                offer["timeline"].append((datetime.now(),"Aceptada"))
                st.balloons()

        st.markdown("#### Estado actual")
        st.write(offer.get("status","—"))
        if "last_pdf" in offer:
            st.download_button("Descargar oferta (PDF simulado)", data=offer["last_pdf"], file_name=f"Oferta_{sel_o}.pdf", mime="application/pdf")

        st.markdown("#### Línea de tiempo")
        if offer["timeline"]:
            for t, e in offer["timeline"]:
                st.write(f"- {t:%Y-%m-%d %H:%M} · {e}")
        else:
            st.caption("Sin eventos aún.")

        st.markdown("---")
        st.subheader("Pre-oferta (control documental)")
        ok_colegi = st.checkbox("Coleg. habilitada", value=False, key=f"po_col_{sel_o}")
        ok_bls   = st.checkbox("BLS/ACLS vigentes", value=False, key=f"po_bls_{sel_o}")
        ok_refs  = st.checkbox("Referencias (2) ok", value=False, key=f"po_refs_{sel_o}")
        ok_conf  = st.checkbox("Rango salarial/modalidad/fecha ok", value=False, key=f"po_conf_{sel_o}")
        if not all([ok_colegi, ok_bls, ok_refs, ok_conf]):
            st.error("No se puede cerrar oferta: faltan validaciones de pre-oferta.")
        else:
            st.success("Pre-oferta OK. Puedes proceder cuando el candidato acepte.")

# =============================================================================
# END
# =============================================================================
