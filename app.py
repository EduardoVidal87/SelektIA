# app.py
# -*- coding: utf-8 -*-

import io
import re
import base64
from pathlib import Path
from datetime import date, datetime

import streamlit as st
import pandas as pd
import plotly.express as px
from PyPDF2 import PdfReader

# ======================================================================================
# TEMA / COLORES
# ======================================================================================
PRIMARY_GREEN = "#00CD78"
SIDEBAR_BG   = "#10172A"
BOX_DARK     = "#132840"
BOX_DARK_HOV = "#193355"
TEXT_LIGHT   = "#FFFFFF"
MAIN_BG      = "#F7FBFF"
BOX_LIGHT    = "#F1F7FD"
BOX_LIGHT_B  = "#E3EDF6"
TITLE_DARK   = "#142433"
BAR_DEFAULT  = "#E9F3FF"
BAR_GOOD     = "#33FFAC"

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

/* Fondo general */
html, body, [data-testid="stAppViewContainer"] {{
  background: var(--main-bg) !important;
}}
.block-container {{
  background: transparent !important;
  padding-top: 1.2rem !important;
}}

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
[data-testid="stSidebar"] h6,
[data-testid="stSidebar"] .stMarkdown p strong {{
  color: var(--green) !important;
}}
[data-testid="stSidebar"] label, 
[data-testid="stSidebar"] p, 
[data-testid="stSidebar"] span {{
  color: var(--text) !important;
}}

/* 4 boxes del panel izquierdo */
[data-testid="stSidebar"] [data-testid="stSelectbox"] > div > div,
[data-testid="stSidebar"] [data-baseweb="select"],
[data-testid="stSidebar"] [data-testid="stTextArea"] textarea,
[data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] {{
  background: var(--box) !important;
  color: var(--text) !important;
  border: 1.5px solid var(--box) !important;
  border-radius: 14px !important;
  box-shadow: none !important;
}}
[data-testid="stSidebar"] [data-testid="stTextArea"] textarea:hover,
[data-testid="stSidebar"] [data-testid="stTextArea"] textarea:focus,
[data-testid="stSidebar"] [data-testid="stSelectbox"] > div > div:hover,
[data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"]:hover {{
  border-color: var(--box-hover) !important;
}}
[data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] * {{
  color: var(--text) !important;
}}
[data-testid="stSidebar"] [data-testid="stFileUploaderFile"] {{
  background: var(--box) !important;
  border: 1px solid var(--box) !important;
  color: var(--text) !important;
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

/* Títulos unificados (como la captura) */
h1, h2, h3 {{
  color: var(--title-dark) !important;
  margin-bottom: .35rem !important;
}}
h1 strong, h2 strong, h3 strong {{
  color: var(--green) !important;
}}
/* línea suave debajo del bloque de título (solo al primer título siguiente) */
h1 + div, h2 + div, h3 + div {{
  border-top: 1px solid var(--box-light-border);
}}
/* también permite separadores suaves debajo del título directo */
h1 + p, h2 + p, h3 + p {{
  border-top: 1px solid transparent;
}}

/* Tabs visibles: píldoras, activa con subrayado verde */
.stTabs [role="tablist"] {{
  gap: .5rem;
  border-bottom: 1px solid var(--box-light-border);
  margin-top: .2rem;
  padding-bottom: .25rem;
}}
/* botón de tab */
.stTabs [role="tab"] {{
  background: #fff;
  color: #374151;
  border: 1px solid var(--box-light-border);
  border-bottom: 2px solid transparent;
  padding: .45rem .9rem;
  border-radius: 10px 10px 0 0;
  font-weight: 500;
}}
/* activa */
.stTabs [role="tab"][aria-selected="true"] {{
  color: var(--title-dark);
  font-weight: 700;
  border-color: var(--box-light-border);
  border-bottom: 3px solid var(--green);
}}
/* hover */
.stTabs [role="tab"]:hover {{
  border-color: var(--green);
}}

/* Inputs claros del cuerpo */
.block-container [data-testid="stSelectbox"] > div > div,
.block-container [data-baseweb="select"],
.block-container [data-testid="stTextInput"] input,
.block-container [data-testid="stTextArea"] textarea {{
  background: var(--box-light) !important;
  color: var(--title-dark) !important;
  border: 1.5px solid var(--box-light-border) !important;
  border-radius: 10px !important;
}}

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

/* Visor PDF */
#pdf_candidate {{
  background: var(--box-light) !important;
  border: 1.5px solid var(--box-light-border) !important;
  color: var(--title-dark) !important;
  border-radius: 10px !important;
}}
.pdf-frame {{
  border: 1px solid var(--box-light-border);
  border-radius: 12px;
  overflow: hidden;
  background: #fff;
}}

/* Badges */
.badge {{
  display:inline-block;
  padding:.25rem .55rem;
  margin:.2rem .25rem .3rem 0;
  border-radius:999px;
  border:1px solid var(--box-light-border);
  background:#fff;
  font-size:.78rem;
  color:#374151;
}}
.badge.green {{
  background:#ecfdf5;
  border-color:#a7f3d0;
  color:#065f46;
}}
.badge.gray {{
  background:#f3f4f6;
  border-color:#e5e7eb;
  color:#374151;
}}
"""

st.set_page_config(page_title="SelektIA", page_icon="🧠", layout="wide")
st.markdown(f"<style>{CSS}</style>", unsafe_allow_html=True)

# ======================================================================================
# UTILIDADES
# ======================================================================================

def extract_text_from_file(uploaded_file) -> str:
    """Extrae texto de PDF o TXT."""
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
    """Score simple por keywords (70%) + aproximación JD (30%)."""
    base = 0
    reasons = []
    text_low = cv_text.lower()
    jd_low = jd.lower()

    # keywords
    hits = 0
    kws = [k.strip().lower() for k in keywords.split(",") if k.strip()]
    found = []
    for k in kws:
        if k and k in text_low:
            hits += 1
            found.append(k)
    if kws:
        pct_k = hits / len(kws)
        base += int(pct_k * 70)
        reasons.append(f"{hits}/{len(kws)} keywords encontradas — Coincidencias: {', '.join(found)[:120]}")

    # JD aproximado
    jd_terms = [t for t in set(jd_low.split()) if len(t) > 3]
    match_terms = sum(1 for t in jd_terms if t in text_low)
    if jd_terms:
        pct_jd = match_terms / len(jd_terms)
        base += int(pct_jd * 30)
        reasons.append("Coincidencias con el JD (aprox.)")

    return max(0, min(100, base)), " — ".join(reasons)

def pdf_viewer_pdfjs(file_bytes: bytes, height=520, scale=1.1):
    """Visor pdf.js (fiable en Streamlit Cloud)."""
    b64 = base64.b64encode(file_bytes).decode("utf-8")
    pdfjs = "https://mozilla.github.io/pdf.js/web/viewer.html?file="
    src = f"{pdfjs}data:application/pdf;base64,{b64}#zoom={int(scale*100)}"
    st.markdown(
        f"""
        <div class="pdf-frame">
          <iframe src="{src}" style="width:100%; height:{height}px; border:0;" title="PDF Viewer"></iframe>
        </div>
        """,
        unsafe_allow_html=True,
    )

def detect_years(text: str) -> int | None:
    """Heurística simple para detectar años de experiencia."""
    text_low = text.lower()
    m = re.search(r"(\d+)\s*(\+|mas|más)?\s*(años|years)", text_low)
    if m:
        try:
            return int(m.group(1))
        except:
            return None
    return None

def analyze_skills(text: str, kw_csv: str, jd: str):
    """Clasifica skills en validated/likely/to_validate de forma simple."""
    text_low = text.lower()
    kws = [k.strip().lower() for k in kw_csv.split(",") if k.strip()]
    validated, likely, to_validate = [], [], []

    syns = {
        "his": ["his", "hospital information system"],
        "sap is-h": ["sap is-h", "sap ish"],
        "bls": ["bls", "basic life support"],
        "acls": ["acls", "advanced cardiac life support"],
        "iaas": ["iaas", "infecciones asociadas a la atención", "infecciones asociadas a la atencion"],
        "educación al paciente": ["educacion al paciente", "patient education", "educación al paciente"],
        "seguridad del paciente": ["seguridad del paciente", "patient safety"],
        "protocolos": ["protocolo", "protocols", "protocolos"],
    }

    for k in kws:
        k_norm = k.lower()
        syn_list = syns.get(k_norm, [k_norm])
        if any(s in text_low for s in syn_list):
            validated.append(k_norm)
        else:
            if any(t in text_low for t in set(jd.lower().split())):
                likely.append(k_norm)
            else:
                to_validate.append(k_norm)

    def uniq(seq):
        seen = set(); out=[]
        for x in seq:
            if x not in seen:
                out.append(x); seen.add(x)
        return out

    return uniq(validated), uniq(likely), uniq(to_validate)

def score_dots(score: int) -> str:
    """Pintitas de match (5 puntos)."""
    filled = round(score / 20)  # 0..5
    dots = []
    for i in range(5):
        if i < filled:
            dots.append(f"<span style='display:inline-block;width:10px;height:10px;border-radius:999px;background:#10b981;margin-right:6px;'></span>")
        else:
            dots.append(f"<span style='display:inline-block;width:10px;height:10px;border-radius:999px;background:#e5e7eb;margin-right:6px;'></span>")
    return "".join(dots)

# ======================================================================================
# ESTADO INICIAL
# ======================================================================================

if "candidates" not in st.session_state:
    st.session_state.candidates = []

if "uploader_key" not in st.session_state:
    st.session_state.uploader_key = "u1"

# Lista "Entrevista (Gerencia)"
if "gerencia_queue" not in st.session_state:
    st.session_state.gerencia_queue = []  # [{name, score, assigned, moved_at}]

# Datos demo de "Puestos"
if "positions" not in st.session_state:
    st.session_state.positions = pd.DataFrame([
        {
            "ID": 10645194,
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
            "Creado": date.today(),
        },
        {
            "ID": 10376415,
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
            "Creado": date.today(),
        },
        {
            "ID": 10376646,
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
            "Creado": date.today(),
        },
    ])

# ======================================================================================
# SIDEBAR
# ======================================================================================

with st.sidebar:
    st.image("assets/logo-wayki.png", use_column_width=True)
    st.markdown("### Definición del puesto")

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
        key="puesto",
    )

    st.markdown("### Descripción del puesto (texto libre)")
    jd_text = st.text_area(
        "Resume el objetivo del puesto, responsabilidades, protocolos y habilidades deseadas.",
        height=120,
        key="jd",
        label_visibility="collapsed",
    )

    st.markdown("### Palabras clave del perfil\n*(ajústalas si es necesario)*")
    kw_text = st.text_area(
        "HIS, SAP IS-H, BLS, ACLS, IAAS, educación al paciente, seguridad…",
        value="HIS, SAP IS-H, BLS, ACLS, IAAS, educación al paciente, seguridad del paciente, protocolos",
        height=110,
        key="kw",
        label_visibility="collapsed",
    )

    st.markdown("### Subir CVs (PDF o TXT)")
    files = st.file_uploader(
        "Drag and drop files here",
        key=st.session_state.uploader_key,
        type=["pdf", "txt"],
        accept_multiple_files=True,
        label_visibility="collapsed",
    )

    # Proceso automático
    if files:
        st.session_state.candidates = []
        for f in files:
            raw = f.read()
            f.seek(0)
            text = extract_text_from_file(f)
            score, reasons = simple_score(text, jd_text, kw_text)
            st.session_state.candidates.append({
                "Name": f.name,
                "Score": score,
                "Reasons": reasons,
                "_bytes": raw,
                "_is_pdf": Path(f.name).suffix.lower() == ".pdf",
                "_text": text,
            })

    st.divider()
    if st.button("Limpiar Lista", use_container_width=True):
        st.session_state.candidates.clear()
        st.session_state.gerencia_queue.clear()
        st.session_state.uploader_key = f"u{pd.Timestamp.utcnow().value}"
        st.rerun()

# ======================================================================================
# CUERPO (Tabs)
# ======================================================================================

tab_puestos, tab_eval, tab_pipeline, tab_gerencia = st.tabs(
    ["📋 Puestos", "🧪 Evaluación de CVs", "👥 Pipeline de Candidatos", "👔 Entrevista (Gerencia)"]
)

# --------------------------------------------------------------------------------------
# TAB 1: PUESTOS
# --------------------------------------------------------------------------------------
with tab_puestos:
    st.markdown("## SelektIA – **Puestos**")

    col_top_l, col_top_c, col_top_r = st.columns([1.8, 1, 1])
    with col_top_l:
        q = st.text_input(
            "Buscar (puesto, ubicación, ID, hiring manager…) ",
            placeholder="Ej: Lima, 10645194, Angela Cruz",
        )
    with col_top_c:
        st.text("")
        show_filters = st.checkbox("Mostrar filtros", value=False)
    with col_top_r:
        st.metric("Puestos totales", len(st.session_state.positions))

    if show_filters:
        with st.expander("Filtros", expanded=True):
            colf1, colf2, colf3, colf4 = st.columns(4)
            with colf1:
                ubic = st.multiselect("Ubicación", sorted(st.session_state.positions["Ubicación"].unique().tolist()))
            with colf2:
                hm = st.multiselect("Hiring Manager", sorted(st.session_state.positions["Hiring Manager"].unique().tolist()))
            with colf3:
                estado = st.multiselect("Estado", sorted(st.session_state.positions["Estado"].unique().tolist()))
            with colf4:
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
        if 'ubic' in locals() and ubic:
            df_pos = df_pos[df_pos["Ubicación"].isin(ubic)]
        if 'hm' in locals() and hm:
            df_pos = df_pos[df_pos["Hiring Manager"].isin(hm)]
        if 'estado' in locals() and estado:
            df_pos = df_pos[df_pos["Estado"].isin(estado)]
        if 'dias_abierto' in locals():
            df_pos = df_pos[df_pos["Días Abierto"] <= dias_abierto]

    st.caption(f"Mostrando **{len(df_pos)}** posiciones")
    st.dataframe(
        df_pos[
            [
                "Puesto", "Días Abierto", "Leads", "Nuevos", "Recruiter Screen",
                "HM Screen", "Entrevista Telefónica", "Entrevista Presencial",
                "Ubicación", "Hiring Manager", "Estado", "ID"
            ]
        ].sort_values(["Estado","Días Abierto","Leads"], ascending=[True, True, False]),
        use_container_width=True,
        height=420,
    )

# --------------------------------------------------------------------------------------
# TAB 2: EVALUACIÓN DE CVs
# --------------------------------------------------------------------------------------
with tab_eval:
    st.markdown("## SelektIA – **Resultados de evaluación**")
    if not st.session_state.candidates:
        st.info("Carga CVs en la barra lateral. El análisis se ejecuta automáticamente.")
    else:
        df = pd.DataFrame(st.session_state.candidates)
        df_sorted = df.sort_values("Score", ascending=False)

        st.markdown("### Ranking de Candidatos")
        st.dataframe(
            df_sorted[["Name", "Score", "Reasons"]],
            use_container_width=True,
            height=240
        )

        st.markdown("### Comparación de puntajes")
        bar_colors = [BAR_GOOD if s >= 60 else BAR_DEFAULT for s in df_sorted["Score"]]
        fig = px.bar(
            df_sorted,
            x="Name",
            y="Score",
            title="Comparación de puntajes (todos los candidatos)",
        )
        fig.update_traces(marker_color=bar_colors, hovertemplate="%{x}<br>Score: %{y}")
        fig.update_layout(
            plot_bgcolor="#FFFFFF",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color=TITLE_DARK),
            xaxis_title=None,
            yaxis_title="Score",
        )
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("### Visor de CV (PDF/TXT)  ↪️")
        all_names = df_sorted["Name"].tolist()
        selected_name = st.selectbox("Elige un candidato", all_names, index=0, key="pdf_candidate", label_visibility="collapsed")
        cand = df.loc[df["Name"] == selected_name].iloc[0]

        if cand["_is_pdf"] and cand["_bytes"]:
            pdf_viewer_pdfjs(cand["_bytes"], height=480, scale=1.10)
            st.download_button(
                f"Descargar {selected_name}",
                data=cand["_bytes"],
                file_name=selected_name,
                mime="application/pdf",
            )
        else:
            st.info(f"'{selected_name}' es un TXT. Mostrando contenido abajo:")
            with st.expander("Ver contenido TXT", expanded=True):
                try:
                    txt = cand["_bytes"].decode("utf-8", errors="ignore")
                except Exception:
                    txt = "(No se pudo decodificar)"
                st.text_area("Contenido", value=txt, height=400, label_visibility="collapsed")

# --------------------------------------------------------------------------------------
# TAB 3: PIPELINE
# --------------------------------------------------------------------------------------
with tab_pipeline:
    st.markdown("## 👥 Pipeline de Candidatos")
    if not st.session_state.candidates:
        st.info("Primero sube CVs en la barra izquierda.")
    else:
        df_all = pd.DataFrame(st.session_state.candidates)
        df_sorted = df_all.sort_values("Score", ascending=False).reset_index(drop=True)

        df_pipeline = pd.DataFrame({
            "Candidato": df_sorted["Name"],
            "Match (%)": df_sorted["Score"].astype(int),
            "Etapa": ["Leads"] * len(df_sorted),
            "Último contacto": ["—"] * len(df_sorted),
            "Fuente": ["CV"] * len(df_sorted),
            "Notas": [""] * len(df_sorted),
        })

        colL, colR = st.columns([1.15, 1])
        with colL:
            st.markdown("#### Pipeline de Candidatos")
            st.caption("Vista solo lectura")
            st.dataframe(df_pipeline, use_container_width=True, height=260)

            st.markdown("##### Seleccionar candidato")
            nombres = df_sorted["Name"].tolist()
            default_index = 0
            if st.session_state.get("pipeline_selected") in nombres:
                default_index = nombres.index(st.session_state.pipeline_selected)
            sel_name = st.selectbox("Candidato", nombres, index=default_index,
                                    key="pipeline_dropdown", label_visibility="collapsed")
            st.session_state.pipeline_selected = sel_name

        with colR:
            sel_name = st.session_state.get("pipeline_selected")
            if not sel_name:
                st.info("Selecciona un candidato a la izquierda.")
            else:
                row = df_all.loc[df_all["Name"] == sel_name].iloc[0]
                sel_score = int(row["Score"])
                sel_text  = row.get("_text", "") or ""

                years = detect_years(sel_text)
                validated, likely, to_validate = analyze_skills(sel_text, st.session_state.get("kw", ""), st.session_state.get("jd", ""))

                st.markdown("### Detalle del candidato")
                st.markdown(f"**{sel_name}**")
                st.caption("Perfil detectado a partir del CV")

                st.markdown(
                    f"""
                    <div style="padding:.75rem 1rem;border:1px solid var(--box-light-border);border-radius:12px;background:#fff">
                      <div style="margin-bottom:.35rem;">{score_dots(sel_score)} <span style="color:#374151;">Match estimado</span></div>
                      <div class="badge green">Match basado en keywords/JD</div>
                      {"<div class='badge green'>10+ años de experiencia</div>" if years and years>=10 else ""}
                    </div>
                    """,
                    unsafe_allow_html=True
                )

                st.markdown("##### Validated Skills")
                if validated:
                    st.markdown("".join([f"<span class='badge'>{k}</span>" for k in validated]), unsafe_allow_html=True)
                else:
                    st.caption("Sin coincidencias fuertes aún.")

                st.markdown("##### Likely Skills")
                if likely:
                    st.markdown("".join([f"<span class='badge gray'>{k}</span>" for k in likely]), unsafe_allow_html=True)
                else:
                    st.caption("No se detectaron sinónimos relevantes.")

                st.markdown("##### Skills to Validate")
                if to_validate:
                    st.markdown("".join([f"<span class='badge'>{k}</span>" for k in to_validate]), unsafe_allow_html=True)
                else:
                    st.caption("Todo parece validado respecto a tus keywords.")

                st.markdown("---")
                st.markdown("##### Acciones rápidas")

                headhunters = ["Headhunter A", "Headhunter B", "Headhunter C"]
                hh = st.selectbox("¿Quién lo tomará?", headhunters, key="hh_assign")

                if st.button("Mover a ‘Entrevista (Gerencia)’", key="move_to_mgr"):
                    if not any(x["name"] == sel_name for x in st.session_state.gerencia_queue):
                        st.session_state.gerencia_queue.append({
                            "name": sel_name,
                            "score": sel_score,
                            "assigned": hh,
                            "moved_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
                        })
                        st.success(f"Movido a ‘Entrevista (Gerencia)’ → asignado a **{hh}**.")
                    else:
                        st.info("Este candidato ya está en ‘Entrevista (Gerencia)’.")
                    st.rerun()

# --------------------------------------------------------------------------------------
# TAB 4: ENTREVISTA (GERENCIA)
# --------------------------------------------------------------------------------------
with tab_gerencia:
    st.markdown("## 👔 Entrevista (Gerencia)")
    if not st.session_state.gerencia_queue:
        st.info("Aún no hay candidatos movidos a esta etapa.")
    else:
        df_mgr = pd.DataFrame(st.session_state.gerencia_queue)
        df_mgr = df_mgr[["name", "score", "assigned", "moved_at"]].rename(columns={
            "name": "Candidato",
            "score": "Match (%)",
            "assigned": "Headhunter",
            "moved_at": "Movido el",
        }).sort_values(["Headhunter","Match (%)"], ascending=[True, False])
        st.dataframe(df_mgr, use_container_width=True, height=360)

        st.caption("Consejo: usa esta lista para que el equipo de headhunters gestione entrevistas de gerencia.")
