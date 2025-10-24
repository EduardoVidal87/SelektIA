# app.py
# -*- coding: utf-8 -*-

import io
import base64
import html
from pathlib import Path
from datetime import date

import streamlit as st
import pandas as pd
import plotly.express as px
from PyPDF2 import PdfReader

# ======================================================================================
# PALETA / THEME (mantenemos tu look&feel)
# ======================================================================================
PRIMARY_GREEN = "#00CD78"
SIDEBAR_BG = "#10172A"        # fondo columna izquierda
BOX_DARK = "#132840"          # fondo y borde de boxes del sidebar
BOX_DARK_HOV = "#193355"      # borde hover/focus
TEXT_LIGHT = "#FFFFFF"
MAIN_BG = "#F7FBFF"           # cuerpo claro
BOX_LIGHT = "#F1F7FD"         # inputs cuerpo
BOX_LIGHT_B = "#E3EDF6"       # borde inputs
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

/* Fondo app */
html, body, [data-testid="stAppViewContainer"] {{
  background: var(--main-bg) !important;
}}
.block-container {{ background: transparent !important; }}

/* Sidebar */
[data-testid="stSidebar"] {{
  background: var(--sidebar-bg) !important;
  color: var(--text) !important;
}}
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3,
[data-testid="stSidebar"] h4,
[data-testid="stSidebar"] h5,
[data-testid="stSidebar"] h6 {{
  color: var(--green) !important;
}}
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span {{ color: var(--text) !important; }}

/* Cards/inputs Sidebar */
[data-testid="stSidebar"] [data-testid="stTextInput"] input,
[data-testid="stSidebar"] [data-testid="stTextArea"] textarea,
[data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"],
[data-testid="stSidebar"] [data-testid="stSelectbox"] > div > div {{
  background: var(--box) !important;
  color: var(--text) !important;
  border: 1.5px solid var(--box) !important;
  border-radius: 14px !important;
}}
[data-testid="stSidebar"] [data-testid="stTextInput"] input:hover,
[data-testid="stSidebar"] [data-testid="stTextArea"] textarea:hover,
[data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"]:hover,
[data-testid="stSidebar"] [data-testid="stSelectbox"] > div > div:hover {{
  border-color: var(--box-hover) !important;
}}

/* Botón verde */
.stButton > button {{
  background: var(--green) !important;
  color: #082017 !important;
  border-radius: 10px !important;
  border: none !important;
  padding: .45rem .9rem !important;
  font-weight: 600 !important;
}}
.stButton > button:hover {{ filter: brightness(0.95); }}

/* Títulos */
h1, h2, h3 {{ color: var(--title-dark); }}
h1 strong, h2 strong, h3 strong {{ color: var(--green); }}

/* Inputs claros cuerpo */
.block-container [data-testid="stSelectbox"] > div > div,
.block-container [data-testid="stTextInput"] input,
.block-container [data-testid="stTextArea"] textarea {{
  background: var(--box-light) !important;
  color: var(--title-dark) !important;
  border: 1.5px solid var(--box-light-border) !important;
  border-radius: 10px !important;
}}

/* TABS VISIBLES (subrayado verde y texto marcado) */
[data-baseweb="tab-list"] [role="tab"] {{
  color: #1f2937 !important;
  font-weight: 700 !important;
  padding: 8px 12px !important;
  margin-right: 14px !important;
  border-bottom: 3px solid transparent !important;
}}
[data-baseweb="tab-list"] [role="tab"][aria-selected="true"] {{
  color: var(--green) !important;
  border-bottom-color: var(--green) !important;
}}
[data-baseweb="tab-list"] [role="tab"] span {{ color: inherit !important; }}

/* Tabla clara */
.block-container table {{
  background: #fff !important;
  border: 1px solid var(--box-light-border) !important;
  border-radius: 8px !important;
}}
.block-container thead th {{
  background: var(--box-light) !important;
  color: var(--title-dark) !important;
}}

/* Marco visor PDF */
.pdf-frame {{
  border: 1px solid var(--box-light-border);
  border-radius: 12px;
  overflow: hidden;
  background: #fff;
}}
"""

st.set_page_config(page_title="SelektIA", page_icon="🧠", layout="wide")
st.markdown(f"<style>{CSS}</style>", unsafe_allow_html=True)

# ======================================================================================
# UTILIDADES
# ======================================================================================

def chips(items, color="badge"):
    safe = [html.escape(str(i)) for i in items]
    return st.markdown(" ".join([f"<span class='{color}'>{i}</span>" for i in safe]), unsafe_allow_html=True)

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

def simple_score(cv_text: str, jd: str, keywords: str) -> tuple[int, str, list, list, list]:
    base = 0
    reasons = []
    text_low = cv_text.lower()
    jd_low = jd.lower()
    validated, likely, to_validate = [], [], []

    # Palabras clave
    hits = 0
    kws = [k.strip().lower() for k in keywords.split(",") if k.strip()]
    for k in kws:
        if k and k in text_low:
            hits += 1
            validated.append(k.upper())
        else:
            to_validate.append(k)
    if kws:
        pct_k = hits / len(kws)
        base += int(pct_k * 70)
        found = [k for k in kws if k in text_low]
        reasons.append(f"{hits}/{len(kws)} keywords encontradas — Coincidencias: {', '.join(found)[:120]}")

    # JD match
    jd_terms = [t for t in set(jd_low.split()) if len(t) > 3]
    match_terms = sum(1 for t in jd_terms if t in text_low)
    if jd_terms:
        pct_jd = match_terms / len(jd_terms)
        base += int(pct_jd * 30)
        reasons.append("Coincidencias con el JD (aprox.)")

    base = max(0, min(100, base))
    if " iaas" in text_low and "iaas" not in validated:
        likely.append("IAAS")
    return base, " — ".join(reasons), validated, likely, to_validate

def pdf_viewer_pdfjs(file_bytes: bytes, height=520, scale=1.1):
    b64 = base64.b64encode(file_bytes).decode("utf-8")
    src = f"https://mozilla.github.io/pdf.js/web/viewer.html?file=data:application/pdf;base64,{b64}#zoom={int(scale*100)}"
    st.markdown(
        f"""
        <div class="pdf-frame">
          <iframe src="{src}" style="width:100%; height:{height}px; border:0;" title="PDF Viewer"></iframe>
        </div>
        """,
        unsafe_allow_html=True,
    )

# ======================================================================================
# ESTADO INICIAL
# ======================================================================================
if "jd_text" not in st.session_state: st.session_state.jd_text = ""
if "kw_text" not in st.session_state:
    st.session_state.kw_text = "HIS, SAP IS-H, BLS, ACLS, IAAS, educación al paciente, seguridad del paciente, protocolos"
if "candidates" not in st.session_state: st.session_state.candidates = []
if "uploader_key" not in st.session_state: st.session_state.uploader_key = "u1"
if "positions" not in st.session_state:
    st.session_state.positions = pd.DataFrame([
        {"ID": "10,645,194","Puesto":"Desarrollador/a Backend (Python)","Ubicación":"Lima, Perú","Leads":1800,"Nuevos":115,"Recruiter Screen":35,"HM Screen":7,"Entrevista Telefónica":14,"Entrevista Presencial":15,"Días Abierto":3,"Hiring Manager":"Rivers Brykson","Estado":"Abierto"},
        {"ID": "10,376,415","Puesto":"VP de Marketing","Ubicación":"Santiago, Chile","Leads":8100,"Nuevos":1,"Recruiter Screen":15,"HM Screen":35,"Entrevista Telefónica":5,"Entrevista Presencial":7,"Días Abierto":28,"Hiring Manager":"Angela Cruz","Estado":"Abierto"},
        {"ID": "10,376,646","Puesto":"Planner de Demanda","Ubicación":"Ciudad de México, MX","Leads":2300,"Nuevos":26,"Recruiter Screen":3,"HM Screen":8,"Entrevista Telefónica":6,"Entrevista Presencial":3,"Días Abierto":28,"Hiring Manager":"Rivers Brykson","Estado":"Abierto"},
    ])
if "gerencia_pool" not in st.session_state: st.session_state.gerencia_pool = []
if "ofertas" not in st.session_state: st.session_state.ofertas = []
if "onboarding" not in st.session_state: st.session_state.onboarding = []

# ======================================================================================
# SIDEBAR: Logo + acceso rápido (índice)
# ======================================================================================
with st.sidebar:
    st.image("assets/logo-wayki.png", use_column_width=True)
    st.markdown("### Navegación rápida")
    st.markdown("- **Dashboard** (Puestos + KPIs)")
    st.markdown("- **Pestañas** (arriba, visibles con subrayado verde)")
    st.markdown("- **Analytics** (al final)")

    st.divider()
    st.markdown("#### Ayuda")
    st.caption("1) Define JD y sube CVs en **Definición & Carga**.\n2) Revisa **Evaluación de CVs**.\n3) Gestiona **Pipeline** y **Entrevista**.\n4) Avanza a **Oferta** y **Onboarding**.")

# ======================================================================================
# TABS (orden actualizado)
# ======================================================================================
tabs = st.tabs([
    "🤖 Asistente IA",
    "🗂️ Definición & Carga",
    "📋 Puestos",
    "🧪 Evaluación de CVs",
    "👥 Pipeline de Candidatos",
    "🗣️ Entrevista (Gerencia)",
    "🧭 Tareas del Headhunter",
    "🧾 Oferta",
    "🚀 Onboarding",
    "📈 Analytics"
])

# --------------------------------------------------------------------------------------
# 0) ASISTENTE IA
# --------------------------------------------------------------------------------------
with tabs[0]:
    st.markdown("## SelektIA – **Asistente IA**")
    colL, colR = st.columns([1.2, 1])
    with colL:
        st.markdown("#### Configuración del agente")
        rol = st.selectbox("Role*", ["Headhunter","Coordinador RR.HH.","Hiring Manager","Gerencia/Comité","Legal","Finanzas","TI / Onboarding"], index=0)
        goal = st.text_input("Goal*", "Identificar a los mejores profesionales para el cargo que se define en el JD")
        backstory = st.text_area("Backstory*", "Eres un analista de recursos humanos con amplia experiencia en análisis de documentos, CV y currículums...")
        guardrails = st.text_area("Guardrails", "No compartas datos sensibles. Cita siempre la fuente (CV o JD) al argumentar.")
        tools = st.multiselect("Herramientas habilitadas", ["Parser de PDF","Vector Search (JD/CVs)","Recomendador de keywords","Generador de correo"], default=["Parser de PDF","Recomendador de keywords"])
        st.button("Crear/Actualizar Agente", use_container_width=True)
    with colR:
        st.markdown("#### Permisos y alcance")
        st.write("• **RLS** por puesto: el agente solo ve candidatos del puesto/rol asignado.")
        st.write("• Acciones permitidas según rol (ej. HH no aprueba ofertas).")
        st.write("• Auditoría: toda acción queda registrada (usuario/rol, objeto, timestamp).")
        st.info("Tip: usa esta configuración para guiar evaluaciones en la pestaña *Evaluación de CVs*.")

# --------------------------------------------------------------------------------------
# 1) DEFINICIÓN & CARGA (JD + CVs)
# --------------------------------------------------------------------------------------
with tabs[1]:
    st.markdown("## SelektIA – **Definición & Carga**")
    c1, c2 = st.columns([1.2, 1])
    with c1:
        puesto = st.selectbox(
            "Puesto objetivo",
            ["Enfermera/o Asistencial","Tecnólogo/a Médico","Recepcionista de Admisión","Médico/a General","Químico/a Farmacéutico/a"],
            index=0
        )
        st.markdown("##### Descripción del puesto (JD)")
        st.session_state.jd_text = st.text_area(
            "JD",
            value=st.session_state.jd_text,
            height=140,
            label_visibility="collapsed"
        )
        st.markdown("##### Palabras clave del perfil (coma separada)")
        st.session_state.kw_text = st.text_area(
            "Keywords",
            value=st.session_state.kw_text,
            height=90,
            label_visibility="collapsed"
        )
    with c2:
        st.markdown("##### Subir CVs (PDF o TXT)")
        files = st.file_uploader(
            "Arrastra y suelta o haz click",
            key=st.session_state.uploader_key,
            type=["pdf","txt"],
            accept_multiple_files=True,
            label_visibility="collapsed"
        )
        if files:
            st.session_state.candidates = []
            for f in files:
                raw = f.read()
                f.seek(0)
                text = extract_text_from_file(f)
                score, reasons, v, lk, tv = simple_score(text, st.session_state.jd_text, st.session_state.kw_text)
                st.session_state.candidates.append({
                    "Name": f.name,
                    "Score": score,
                    "Reasons": reasons,
                    "Validated": v,
                    "Likely": lk,
                    "ToValidate": tv,
                    "_bytes": raw,
                    "_is_pdf": Path(f.name).suffix.lower() == ".pdf",
                })
            st.success(f"Se procesaron {len(st.session_state.candidates)} archivos.")
        st.divider()
        if st.button("Limpiar lista de CVs", use_container_width=True):
            st.session_state.candidates = []
            st.session_state.uploader_key = f"u{pd.Timestamp.utcnow().value}"
            st.experimental_rerun()

    st.markdown("---")
    st.markdown("#### Resumen de carga")
    colA, colB, colC, colD = st.columns(4)
    colA.metric("CVs cargados", len(st.session_state.candidates))
    colB.metric("JD (caracteres)", len(st.session_state.jd_text))
    colC.metric("Keywords", len([k for k in st.session_state.kw_text.split(",") if k.strip()]))
    colD.metric("Listos para evaluar", sum(1 for c in st.session_state.candidates if c["_bytes"]))

# --------------------------------------------------------------------------------------
# 2) PUESTOS
# --------------------------------------------------------------------------------------
with tabs[2]:
    st.markdown("## SelektIA – **Puestos**")
    q = st.text_input("Buscar (puesto, ubicación, ID, hiring manager…)", placeholder="Ej: Lima, 10645194, Angela Cruz")
    show_filters = st.checkbox("Mostrar filtros", value=False)

    if show_filters:
        with st.expander("Filtros", expanded=True):
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                ubic = st.multiselect("Ubicación", sorted(st.session_state.positions["Ubicación"].unique().tolist()))
            with c2:
                hm = st.multiselect("Hiring Manager", sorted(st.session_state.positions["Hiring Manager"].unique().tolist()))
            with c3:
                estado = st.multiselect("Estado", sorted(st.session_state.positions["Estado"].unique().tolist()))
            with c4:
                dias_abierto = st.slider("Días abierto (máx)", min_value=0, max_value=60, value=60)

    df_pos = st.session_state.positions.copy()
    if q:
        ql = q.lower()
        df_pos = df_pos[
            df_pos["Puesto"].str.lower().str.contains(ql) |
            df_pos["Ubicación"].str.lower().str.contains(ql) |
            df_pos["Hiring Manager"].str.lower().str.contains(ql) |
            df_pos["ID"].astype(str).str.contains(ql)
        ]
    if show_filters:
        if 'ubic' in locals() and ubic: df_pos = df_pos[df_pos["Ubicación"].isin(ubic)]
        if 'hm' in locals() and hm: df_pos = df_pos[df_pos["Hiring Manager"].isin(hm)]
        if 'estado' in locals() and estado: df_pos = df_pos[df_pos["Estado"].isin(estado)]
        df_pos = df_pos[df_pos["Días Abierto"] <= dias_abierto]

    st.caption(f"Mostrando **{len(df_pos)}** posiciones")
    st.dataframe(
        df_pos[["Puesto","Días Abierto","Leads","Nuevos","Recruiter Screen","HM Screen","Entrevista Telefónica","Entrevista Presencial","Ubicación","Hiring Manager","Estado","ID"]]
        .sort_values(["Estado","Días Abierto","Leads"], ascending=[True, True, False]),
        use_container_width=True, height=420
    )

# --------------------------------------------------------------------------------------
# 3) EVALUACIÓN DE CVS
# --------------------------------------------------------------------------------------
with tabs[3]:
    st.markdown("## SelektIA – **Resultados de evaluación**  ↪️")
    if not st.session_state.candidates:
        st.info("Carga CVs en **Definición & Carga**. El análisis se ejecuta automáticamente.")
    else:
        df = pd.DataFrame(st.session_state.candidates)
        df_sorted = df.sort_values("Score", ascending=False)

        st.markdown("### Ranking de Candidatos")
        st.dataframe(df_sorted[["Name","Score","Reasons"]], use_container_width=True, height=240)

        st.markdown("### Comparación de puntajes")
        bar_colors = [BAR_GOOD if s >= 60 else BAR_DEFAULT for s in df_sorted["Score"]]
        fig = px.bar(df_sorted, x="Name", y="Score", title="Comparación de puntajes (todos los candidatos)")
        fig.update_traces(marker_color=bar_colors, hovertemplate="%{x}<br>Score: %{y}")
        fig.update_layout(plot_bgcolor="#FFFFFF", paper_bgcolor="rgba(0,0,0,0)", font=dict(color=TITLE_DARK), xaxis_title=None, yaxis_title="Score")
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("### Visor de CV (PDF/TXT)")
        all_names = df_sorted["Name"].tolist()
        selected_name = st.selectbox("Elige un candidato", all_names, index=0, key="pdf_candidate", label_visibility="collapsed")
        cand = df.loc[df["Name"] == selected_name].iloc[0]
        if cand["_is_pdf"] and cand["_bytes"]:
            pdf_viewer_pdfjs(cand["_bytes"], height=480, scale=1.10)
            st.download_button(f"Descargar {selected_name}", data=cand["_bytes"], file_name=selected_name, mime="application/pdf")
        else:
            st.info(f"'{selected_name}' es un TXT. Mostrando contenido abajo:")
            with st.expander("Ver contenido TXT", expanded=True):
                try:
                    txt = cand["_bytes"].decode("utf-8", errors="ignore")
                except Exception:
                    txt = "(No se pudo decodificar)"
                st.text_area("Contenido", value=txt, height=400, label_visibility="collapsed")

# --------------------------------------------------------------------------------------
# 4) PIPELINE – lista izquierda + detalle derecha (solo lectura)
# --------------------------------------------------------------------------------------
with tabs[4]:
    st.markdown("## SelektIA – **Pipeline de Candidatos**")
    if not st.session_state.candidates:
        st.info("No hay candidatos cargados. Usa **Definición & Carga**.")
    else:
        df = pd.DataFrame(st.session_state.candidates).sort_values("Score", ascending=False)
        colL, colR = st.columns([1.2, 1])
        with colL:
            st.markdown("#### Candidatos detectados (clic para ver detalle)")
            sel = st.radio("Candidatos", df["Name"].tolist(), index=0, label_visibility="collapsed")
        with colR:
            cand = df[df["Name"] == sel].iloc[0]
            st.markdown("### Detalle del candidato")
            st.write(sel)
            match_txt = "Alto" if cand["Score"] >= 60 else "Medio" if cand["Score"] >= 40 else "Bajo"
            st.write("Match estimado:", match_txt)
            st.markdown("**Validated Skills**")
            chips(cand.get("Validated", []) or ["—"])
            st.markdown("**Likely Skills**")
            chips(cand.get("Likely", []) or ["—"])
            st.markdown("**Skills to Validate**")
            chips(cand.get("ToValidate", []) or ["—"])

# --------------------------------------------------------------------------------------
# 5) ENTREVISTA (GERENCIA)
# --------------------------------------------------------------------------------------
with tabs[5]:
    st.markdown("## SelektIA – **Entrevista (Gerencia)**")
    if not st.session_state.gerencia_pool:
        st.info("Aún no hay candidatos enviados desde **Tareas del Headhunter**.")
    else:
        for name in st.session_state.gerencia_pool:
            st.markdown(f"- {name}")
        hh_score = st.slider("Rúbrica de Gerencia (0-70)", 0, 70, 40)
        chk_score = st.slider("Checklist HH (0-30)", 0, 30, 20)
        total = hh_score + chk_score
        st.metric("Score consolidado", f"{total}/100")
        if total >= 70:
            st.success("Semáforo: **Verde** (≥70)")
        elif total >= 60:
            st.warning("Semáforo: **Ámbar** (60–69)")
        else:
            st.error("Semáforo: **Rojo** (<60)")
        colA, colB = st.columns(2)
        with colA:
            if st.button("Mover a Oferta"):
                st.success("Candidata movida a **Oferta** (ver pestaña).")
        with colB:
            if st.button("Descartar con feedback"):
                st.info("Se registró descarte con feedback.")

# --------------------------------------------------------------------------------------
# 6) TAREAS DEL HEADHUNTER – checklist + Enviar a Comité
# --------------------------------------------------------------------------------------
with tabs[6]:
    st.markdown("## SelektIA – **Tareas del Headhunter**")
    if not st.session_state.candidates:
        st.info("Carga CVs en **Definición & Carga** primero.")
    else:
        names = [c["Name"] for c in st.session_state.candidates]
        sel_hh = st.selectbox("Candidata", names)
        c1, c2, c3 = st.columns(3)
        with c1: ch1 = st.checkbox("Contacto hecho")
        with c2: ch2 = st.checkbox("Entrevista agendada")
        with c3: ch3 = st.checkbox("Feedback recibido")
        st.markdown("**Notas (obligatorio)**")
        notas = st.text_area("3 fortalezas, 2 riesgos, pretensión salarial, disponibilidad", height=120, label_visibility="collapsed")
        st.markdown("**Adjuntos (BLS/ACLS, colegiatura… PDF/IMG)**")
        st.file_uploader("Adjuntar", type=["pdf","png","jpg","jpeg"], accept_multiple_files=True)
        st.divider()
        if st.button("Enviar a Comité"):
            if not (ch1 and ch2 and ch3) or len(notas.strip()) < 10:
                st.error("Completa el checklist y agrega notas antes de enviar.")
            else:
                if sel_hh not in st.session_state.gerencia_pool:
                    st.session_state.gerencia_pool.append(sel_hh)
                st.success("Enviado a **Entrevista (Gerencia)** y bloqueado para edición.")

# --------------------------------------------------------------------------------------
# 7) OFERTA
# --------------------------------------------------------------------------------------
with tabs[7]:
    st.markdown("## SelektIA – **Oferta**")
    with st.form("form_oferta", clear_on_submit=False):
        c1, c2, c3 = st.columns(3)
        puesto_o = c1.text_input("Puesto", value="Enfermera/o Asistencial")
        ubi_o    = c2.selectbox("Ubicación", ["Lima, Perú","Santiago, Chile","Ciudad de México, MX","Remoto LATAM"], index=0)
        mod_o    = c3.selectbox("Modalidad", ["Presencial","Híbrido","Remoto"], index=0)
        c4, c5, c6 = st.columns(3)
        contrato  = c4.selectbox("Contrato", ["Indeterminado","Plazo fijo","Servicios (honorarios)"], index=0)
        salario   = c5.text_input("Salario (rango y neto)", "USD 1,200 – 1,500 neto")
        beneficios= c6.text_input("Bonos/beneficios", "Alimentación, movilidad")
        c7, c8 = st.columns(2)
        f_ini    = c7.date_input("Fecha de inicio")
        f_cad    = c8.date_input("Caducidad de oferta")
        aprobadores = st.multiselect("Aprobadores", ["Gerencia","Legal","Finanzas"])
        enviado = st.form_submit_button("Generar oferta (PDF) y Enviar")
        if enviado:
            st.success("Oferta generada/enviada (simulado). SLA recordatorios: 48h y 72h.")
    st.divider()
    if st.button("Marcar **Propuesta aceptada**"):
        st.success("Estado: **Aceptada**. Se crean tareas de **Onboarding** automáticamente.")
        st.session_state.onboarding.append({
            "tareas": [
                {"nombre":"Contrato firmado","due_h":48,"estado":"pendiente"},
                {"nombre":"Documentos completos","due_h":72,"estado":"pendiente"},
                {"nombre":"Usuario/email creado","due_h":24,"estado":"pendiente"},
                {"nombre":"Acceso SAP IS-H","due_h":48,"estado":"pendiente"},
                {"nombre":"Examen médico","due_h":72,"estado":"pendiente"},
                {"nombre":"Inducción día 1","due_h":24*3,"estado":"pendiente"},
                {"nombre":"EPP/Uniforme entregado","due_h":24,"estado":"pendiente"},
                {"nombre":"Plan 30-60-90 cargado","due_h":24*7,"estado":"pendiente"},
            ],
            "responsables": {"RRHH":"Coordinador/a","TI":"Equipo TI","Jefe directo":"Por definir","Tutor":"Asignar"},
        })

# --------------------------------------------------------------------------------------
# 8) ONBOARDING – checklist con SLA y asignaciones
# --------------------------------------------------------------------------------------
with tabs[8]:
    st.markdown("## SelektIA – **Onboarding**")
    if not st.session_state.onboarding:
        st.info("Cuando marques **Propuesta aceptada** en Oferta, se generarán aquí las tareas.")
    else:
        data = st.session_state.onboarding[-1]
        st.markdown("#### Checklist y due dates")
        for i, t in enumerate(data["tareas"]):
            c1, c2, c3 = st.columns([2,1,1])
            done = c1.checkbox(t["nombre"], value=(t.get("estado")=="hecho"), key=f"onb_{i}")
            sla = c2.number_input("SLA (h)", min_value=1, max_value=240, value=int(t["due_h"]), key=f"sla_{i}")
            st.caption("Rojo si vencido, naranja si <24h")
            estado = "hecho" if done else "pendiente"
            t["estado"] = estado
            t["due_h"] = sla
        st.markdown("#### Asignaciones")
        rrhh = st.text_input("RR.HH. responsable", value=data["responsables"].get("RRHH",""))
        ti   = st.text_input("TI responsable", value=data["responsables"].get("TI",""))
        jefe = st.text_input("Jefe directo", value=data["responsables"].get("Jefe directo",""))
        tutor= st.text_input("Tutor/buddy", value=data["responsables"].get("Tutor",""))
        data["responsables"] = {"RRHH": rrhh, "TI": ti, "Jefe directo": jefe, "Tutor": tutor}
        st.markdown("#### Documentos")
        st.file_uploader("Contrato / BLS-ACLS / Colegiatura / Referencias", type=["pdf","png","jpg","jpeg"], accept_multiple_files=True)
        st.success("Al completar, exporta a Payroll/HRIS (futuro).")

# --------------------------------------------------------------------------------------
# 9) ANALYTICS – placeholder simple
# --------------------------------------------------------------------------------------
with tabs[9]:
    st.markdown("## SelektIA – **Analytics**")
    st.caption("KPIs de conversión por etapa, time-to-fill, SLA, razones de descarte, etc. (en construcción)")
