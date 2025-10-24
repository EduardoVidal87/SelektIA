# app.py
# -*- coding: utf-8 -*-

import io
import base64
from pathlib import Path
from datetime import date

import streamlit as st
import pandas as pd
import plotly.express as px
from PyPDF2 import PdfReader

# ======================================================================================
# COLORES / TEMA
# ======================================================================================
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
/* Boxes del sidebar */
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
  font-weight: 700 !important;
}}
.stButton > button:hover {{ filter: brightness(0.95); }}

/* Títulos del cuerpo */
h1, h2, h3 {{
  color: var(--title-dark) !important;
  margin-bottom: .6rem !important;
}}
h1 strong, h2 strong, h3 strong {{
  color: var(--green) !important;
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

/* Tablas */
.block-container table {{
  background: #fff !important;
  border: 1px solid var(--box-light-border) !important;
  border-radius: 8px !important;
}}
.block-container thead th {{
  background: var(--box-light) !important;
  color: var(--title-dark) !important;
}}

/* Selector visor */
#pdf_candidate {{
  background: var(--box-light) !important;
  border: 1.5px solid var(--box-light-border) !important;
  color: var(--title-dark) !important;
  border-radius: 10px !important;
}}

/* Contenedor visor PDF */
.pdf-frame {{
  border: 1px solid var(--box-light-border);
  border-radius: 12px;
  overflow: hidden;
  background: #fff;
}}

/* ====== TABS VISIBLES ====== */
/* >>> TABS-VISIBLES: START >>> */
[data-testid="stTabs"] [role="tablist"],
[data-baseweb="tab-list"] {{
  display: flex;
  gap: 12px;
  align-items: flex-end;
  padding: 0 .25rem;
  margin: .4rem 0 1.1rem 0;           /* más aire para que se vean */
  border-bottom: 3px solid #d0e4f7;
}}
[data-testid="stTabs"] button[role="tab"],
[data-baseweb="tab"] {{
  background: transparent !important;
  color: #2b3a55 !important;           /* texto más oscuro */
  padding: .55rem 1rem !important;
  border-radius: 12px 12px 0 0 !important;
  font-weight: 900 !important;
  letter-spacing: .2px;
  border: none !important;
  position: relative;
}}
[data-testid="stTabs"] button[role="tab"]:hover,
[data-baseweb="tab"]:hover {{
  color: #1a2538 !important;
  background: rgba(0,0,0,.03) !important;
}}
[data-testid="stTabs"] button[role="tab"][aria-selected="true"],
[data-baseweb="tab"][aria-selected="true"] {{
  color: var(--green) !important;
  background: #f2fbf7 !important;
}}
[data-testid="stTabs"] button[role="tab"][aria-selected="true"]::after,
[data-baseweb="tab"][aria-selected="true"]::after {{
  content: "";
  position: absolute;
  left: 10px; right: 10px; bottom: -3px;
  height: 4px; border-radius: 4px; background: var(--green);
}}
/* >>> TABS-VISIBLES: END >>> */
"""

st.set_page_config(page_title="SelektIA", page_icon="🧠", layout="wide")
st.markdown(f"<style>{CSS}</style>", unsafe_allow_html=True)

# ======================================================================================
# UTILIDADES
# ======================================================================================

def extract_text_from_file(uploaded_file) -> str:
    """Extrae texto de PDF (PyPDF2) o TXT."""
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
    """Score simple por coincidencia de palabras clave y términos del JD."""
    base = 0
    reasons = []
    text_low = cv_text.lower()
    jd_low = jd.lower()

    # keywords
    hits = 0
    kws = [k.strip().lower() for k in keywords.split(",") if k.strip()]
    for k in kws:
        if k and k in text_low:
            hits += 1
    if kws:
        pct_k = hits / len(kws)
        base += int(pct_k * 70)
        top_hits = [k for k in kws if k in text_low]
        reasons.append(f"{hits}/{len(kws)} keywords encontradas — Coincidencias: {', '.join(top_hits)[:120]}")

    # JD match
    jd_terms = [t for t in set(jd_low.split()) if len(t) > 3]
    match_terms = sum(1 for t in jd_terms if t in text_low)
    if jd_terms:
        pct_jd = match_terms / len(jd_terms)
        base += int(pct_jd * 30)
        reasons.append("Coincidencias con el JD (aprox.)")

    base = max(0, min(100, base))
    return base, " — ".join(reasons)

def pdf_viewer_pdfjs(file_bytes: bytes, height=520, scale=1.1):
    """Visor estable con pdf.js."""
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

# ======================================================================================
# ESTADO INICIAL
# ======================================================================================
if "candidates" not in st.session_state:
    st.session_state.candidates = []
if "uploader_key" not in st.session_state:
    st.session_state.uploader_key = "u1"
if "interview_list" not in st.session_state:
    st.session_state.interview_list = []
if "selected_pipeline" not in st.session_state:
    st.session_state.selected_pipeline = None

# Puestos demo
if "positions" not in st.session_state:
    st.session_state.positions = pd.DataFrame([
        {"ID": 10645194, "Puesto": "Desarrollador/a Backend (Python)", "Ubicación": "Lima, Perú",
         "Leads": 1800, "Nuevos": 115, "Recruiter Screen": 35, "HM Screen": 7,
         "Entrevista Telefónica": 14, "Entrevista Presencial": 15, "Días Abierto": 3,
         "Hiring Manager": "Rivers Brykson", "Estado": "Abierto", "Creado": date.today()},
        {"ID": 10376646, "Puesto": "Planner de Demanda", "Ubicación": "Ciudad de México, MX",
         "Leads": 2300, "Nuevos": 26, "Recruiter Screen": 3, "HM Screen": 8,
         "Entrevista Telefónica": 6, "Entrevista Presencial": 3, "Días Abierto": 28,
         "Hiring Manager": "Rivers Brykson", "Estado": "Abierto", "Creado": date.today()},
        {"ID": 10376415, "Puesto": "VP de Marketing", "Ubicación": "Santiago, Chile",
         "Leads": 8100, "Nuevos": 1, "Recruiter Screen": 15, "HM Screen": 35,
         "Entrevista Telefónica": 5, "Entrevista Presencial": 7, "Días Abierto": 28,
         "Hiring Manager": "Angela Cruz", "Estado": "Abierto", "Creado": date.today()},
    ])

# ======================================================================================
# SIDEBAR (análisis automático)
# ======================================================================================
with st.sidebar:
    st.image("assets/logo-wayki.png", use_column_width=True)
    st.markdown("### Definición del puesto")
    puesto = st.selectbox(
        "Puesto",
        ["Enfermera/o Asistencial","Tecnólogo/a Médico","Recepcionista de Admisión","Médico/a General","Químico/a Farmacéutico/a"],
        index=0, key="puesto",
    )

    st.markdown("### Descripción del puesto (texto libre)")
    jd_text = st.text_area(
        "Resumen / responsabilidades / protocolos / habilidades…",
        height=120, key="jd", label_visibility="collapsed",
    )

    st.markdown("### Palabras clave del perfil\n*(ajústalas si es necesario)*")
    kw_text = st.text_area(
        "HIS, SAP IS-H, BLS, ACLS, IAAS, educación al paciente, seguridad…",
        value="HIS, SAP IS-H, BLS, ACLS, IAAS, educación al paciente, seguridad del paciente, protocolos",
        height=110, key="kw", label_visibility="collapsed",
    )

    st.markdown("### Subir CVs (PDF o TXT)")
    files = st.file_uploader(
        "Drag and drop files here",
        key=st.session_state.uploader_key,
        type=["pdf", "txt"],
        accept_multiple_files=True,
        label_visibility="collapsed",
    )

    if files:
        st.session_state.candidates = []
        for f in files:
            b = f.read()
            f.seek(0)                           # ← IMPORTANTE
            text = extract_text_from_file(f)
            score, reasons = simple_score(text, jd_text, kw_text)
            st.session_state.candidates.append({
                "Name": f.name,
                "Score": score,
                "Reasons": reasons,
                "_bytes": b,
                "_is_pdf": Path(f.name).suffix.lower() == ".pdf",
            })

    st.divider()
    if st.button("Limpiar Lista", use_container_width=True):
        st.session_state.candidates = []
        st.session_state.uploader_key = f"u{pd.Timestamp.utcnow().value}"
        st.rerun()

# ======================================================================================
# PESTAÑAS
# ======================================================================================
tabs = st.tabs(
    ["🗂️ Puestos", "🧪 Evaluación de CVs", "👥 Pipeline de Candidatos", "📁 Entrevista (Gerencia)"]
)

# --------------------------------------------------------------------------------------
# TAB 1: PUESTOS
# --------------------------------------------------------------------------------------
with tabs[0]:
    st.markdown("## SelektIA – **Puestos**")
    col_top_l, col_top_c, col_top_r = st.columns([1.8, 1, 1])
    with col_top_l:
        q = st.text_input("Buscar (puesto, ubicación, ID, hiring manager…)", placeholder="Ej: Lima, 10645194, Angela Cruz")
    with col_top_c:
        st.text("")
        show_filters = st.checkbox("Mostrar filtros", value=False)
    with col_top_r:
        st.metric("Puestos totales", len(st.session_state.positions))

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
            if 'ubic' in locals() and ubic: df_pos = df_pos[df_pos["Ubicación"].isin(ubic)]
            if 'hm' in locals() and hm: df_pos = df_pos[df_pos["Hiring Manager"].isin(hm)]
            if 'estado' in locals() and estado: df_pos = df_pos[df_pos["Estado"].isin(estado)]
            if 'dias_abierto' in locals(): df_pos = df_pos[df_pos["Días Abierto"] <= dias_abierto]

    st.caption(f"Mostrando **{len(df_pos)}** posiciones")
    st.dataframe(
        df_pos[
            ["Puesto","Días Abierto","Leads","Nuevos","Recruiter Screen","HM Screen",
             "Entrevista Telefónica","Entrevista Presencial","Ubicación","Hiring Manager","Estado","ID"]
        ].sort_values(["Estado","Días Abierto","Leads"], ascending=[True, True, False]),
        use_container_width=True,
        height=360,
    )

# --------------------------------------------------------------------------------------
# TAB 2: EVALUACIÓN DE CVS
# --------------------------------------------------------------------------------------
with tabs[1]:
    st.markdown("## SelektIA – **Resultados de evaluación**")

    if not st.session_state.candidates:
        st.info("Carga CVs en la barra lateral. El análisis se ejecuta automáticamente.")
    else:
        df = pd.DataFrame(st.session_state.candidates)
        df_sorted = df.sort_values("Score", ascending=False)

        st.markdown("### Ranking de Candidatos")
        st.dataframe(df_sorted[["Name","Score","Reasons"]], use_container_width=True, height=240)

        st.markdown("### Comparación de puntajes")
        bar_colors = [BAR_GOOD if s >= 60 else BAR_DEFAULT for s in df_sorted["Score"]]
        fig = px.bar(df_sorted, x="Name", y="Score", title="Comparación de puntajes (todos los candidatos)")
        fig.update_traces(marker_color=bar_colors, hovertemplate="%{x}<br>Score: %{y}")
        fig.update_layout(plot_bgcolor="#FFFFFF", paper_bgcolor="rgba(0,0,0,0)",
                          font=dict(color=TITLE_DARK), xaxis_title=None, yaxis_title="Score")
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("### Visor de CV (PDF/TXT)  ↪️")
        all_names = df_sorted["Name"].tolist()
        selected_name = st.selectbox("Elige un candidato", all_names, index=0, key="pdf_candidate", label_visibility="collapsed")

        cand = df.loc[df["Name"] == selected_name].iloc[0]
        if cand["_is_pdf"] and cand["_bytes"]:
            pdf_viewer_pdfjs(cand["_bytes"], height=520, scale=1.10)
            st.download_button(f"Descargar {selected_name}", data=cand["_bytes"],
                               file_name=selected_name, mime="application/pdf")
        else:
            st.info(f"'{selected_name}' es un TXT. Mostrando contenido abajo:")
            with st.expander("Ver contenido TXT", expanded=True):
                try:
                    txt = cand["_bytes"].decode("utf-8", errors="ignore")
                except Exception:
                    txt = "(No se pudo decodificar)"
                st.text_area("Contenido", value=txt, height=400, label_visibility="collapsed")

# --------------------------------------------------------------------------------------
# TAB 3: PIPELINE DE CANDIDATOS (CUADRO ORIGINAL + DROPDOWN)
# --------------------------------------------------------------------------------------
with tabs[2]:
    st.markdown("## SelektIA – **Pipeline de Candidatos**")

    if not st.session_state.candidates:
        st.info("Primero sube algunos CVs para poblar el pipeline.")
    else:
        df = pd.DataFrame(st.session_state.candidates).sort_values("Score", ascending=False).reset_index(drop=True)

        # --------- CUADRO (tabla no editable) ---------
        left, right = st.columns([1.3, 1])
        with left:
            st.markdown("#### Candidatos (vista rápida)")
            cuadro = pd.DataFrame({
                "Candidato": df["Name"],
                "Match (%)": df["Score"].astype(int),
                "Etapa": ["Leads"] * len(df),
                "Último contacto": ["None"] * len(df),
                "Fuente": ["CV"] * len(df),
                "Notas": ["" for _ in range(len(df))]
            })
            st.dataframe(cuadro, use_container_width=True, height=280)

            # Además, un selector (lista desplegable) para mostrar detalle
            st.markdown("**Elegir candidato (lista desplegable):**")
            pick = st.selectbox("Selecciona para ver detalles", df["Name"].tolist(),
                                key="pipeline_select", label_visibility="collapsed")
            st.session_state.selected_pipeline = pick

        with right:
            st.markdown("#### Detalle del candidato")

            if not st.session_state.selected_pipeline:
                st.info("Selecciona un candidato de la lista para ver sus detalles.")
            else:
                cand = df.loc[df["Name"] == st.session_state.selected_pipeline].iloc[0]
                st.write(f"**{cand['Name']}**")
                st.caption("Perfil detectado a partir del CV")

                st.write("**Match estimado**")
                st.progress(min(100, int(cand["Score"])))

                st.write("**Validated Skills**")
                v_items = []
                if "his" in kw_text.lower(): v_items.append("his")
                if v_items: st.write(", ".join(v_items))
                else: st.caption("No se detectaron sinónimos relevantes.")

                st.write("**Likely Skills**")
                st.caption("No se detectaron sinónimos relevantes.")

                st.write("**Skills to Validate**")
                chips = [x.strip() for x in kw_text.split(",") if x.strip()]
                st.write(" ".join([f"`{c}`" for c in chips]) if chips else "Sin elementos.")

                st.markdown("#### Acciones rápidas")
                c1, c2 = st.columns(2)
                with c1:
                    st.button("Añadir nota 'Buen encaje'", use_container_width=True)
                with c2:
                    if st.button("Mover a ‘Entrevista (Gerencia)’", use_container_width=True):
                        if cand["Name"] not in st.session_state.interview_list:
                            st.session_state.interview_list.append(cand["Name"])
                        st.success("Candidato movido a Entrevista (Gerencia). Revisa la pestaña correspondiente.")

# --------------------------------------------------------------------------------------
# TAB 4: ENTREVISTA (GERENCIA)
# --------------------------------------------------------------------------------------
with tabs[3]:
    st.markdown("## SelektIA – **Entrevista (Gerencia)**")
    if not st.session_state.interview_list:
        st.info("Aún no has movido candidatos a esta etapa desde el Pipeline.")
    else:
        st.write("**Candidatos en entrevista (gerencia):**")
        for name in st.session_state.interview_list:
            st.write(f"• {name}")
        st.markdown("---")
        hh = st.selectbox("Headhunter asignado", ["Sin asignar", "Carla P.", "Diego R.", "Lucía T."])
        st.button("Asignar / Reasignar", key="asignar_hh")
