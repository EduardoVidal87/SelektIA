# app.py
# -*- coding: utf-8 -*-

import io
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
  padding-top: 1.25rem !important;
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

/* 4 boxes del panel izquierdo con el mismo diseño */
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

/* Botón verde (sidebar y cuerpo) */
.stButton > button {{
  background: var(--green) !important;
  color: #082017 !important;
  border-radius: 10px !important;
  border: none !important;
  padding: .45rem .9rem !important;
  font-weight: 600 !important;
}}
.stButton > button:hover {{ filter: brightness(0.95); }}

/* Títulos cuerpo */
h1, h2, h3 {{ color: var(--title-dark); }}
h1 strong, h2 strong, h3 strong {{ color: var(--green); }}

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

/* Tabs visibles (color + subrayado en activo) */
[data-baseweb="tab-list"] > div[role="tab"] {{
  color: #6B7280 !important;
  font-weight: 600 !important;
}}
[data-baseweb="tab-list"] > div[aria-selected="true"] {{
  color: var(--green) !important;
  border-bottom: 3px solid var(--green) !important;
}}
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
        uploaded_file.seek(0)
        data = uploaded_file.read()
        if suffix == ".pdf":
            pdf_reader = PdfReader(io.BytesIO(data))
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() or ""
            return text
        else:
            return data.decode("utf-8", errors="ignore")
    except Exception as e:
        st.error(f"Error al leer '{uploaded_file.name}': {e}")
        return ""

def simple_score(cv_text: str, jd: str, keywords: str) -> tuple[int, str]:
    """Score simple por coincidencia de keywords + términos del JD."""
    base = 0
    reasons = []
    text_low = (cv_text or "").lower()
    jd_low = (jd or "").lower()

    # palabras clave (70%)
    hits = 0
    kws = [k.strip().lower() for k in (keywords or "").split(",") if k.strip()]
    for k in kws:
        if k and (k in text_low):
            hits += 1
    if kws:
        pct_k = hits / len(kws)
        base += int(pct_k * 70)
        reasons.append(
            f"{hits}/{len(kws)} keywords encontradas — Coincidencias: "
            f"{', '.join([k for k in kws if k in text_low])[:120]}"
        )

    # JD (30%)
    jd_terms = [t for t in set(jd_low.split()) if len(t) > 3]
    match_terms = sum(1 for t in jd_terms if t in text_low)
    if jd_terms:
        pct_jd = match_terms / len(jd_terms)
        base += int(pct_jd * 30)
        reasons.append("Coincidencias con el JD (aprox.)")

    base = max(0, min(100, base))
    return base, " — ".join(reasons)

def pdf_viewer_pdfjs(file_bytes: bytes, height=520, scale=1.1):
    """Visor usando pdf.js (robusto en Streamlit Cloud)."""
    try:
        b64 = base64.b64encode(file_bytes).decode("utf-8")
        pdfjs = "https://mozilla.github.io/pdf.js/web/viewer.html?file="
        src = f"{pdfjs}data:application/pdf;base64,{b64}#zoom={int(scale*100)}"
        st.markdown(
            f"""
            <div style="border:1px solid {BOX_LIGHT_B};border-radius:12px;overflow:hidden;background:#fff;">
              <iframe src="{src}" style="width:100%; height:{height}px; border:0;" title="PDF Viewer"></iframe>
            </div>
            """,
            unsafe_allow_html=True,
        )
    except Exception as e:
        st.warning(f"No se pudo embeber el PDF. Descarga directa: {e}")

# ======================================================================================
# ESTADO INICIAL
# ======================================================================================
if "candidates" not in st.session_state:
    st.session_state.candidates = []
if "uploader_key" not in st.session_state:
    st.session_state.uploader_key = "u1"
if "positions" not in st.session_state:
    st.session_state.positions = pd.DataFrame([
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
if "pipeline" not in st.session_state:
    st.session_state.pipeline = []
if "committee" not in st.session_state:
    st.session_state.committee = []  # para “Entrevista (Gerencia)”
if "hh_tasks" not in st.session_state:
    st.session_state.hh_tasks = {}  # tareas por candidata
if "offers" not in st.session_state:
    st.session_state.offers = {}  # ofertas por candidata

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
        value=st.session_state.get(
            "kw",
            "HIS, SAP IS-H, BLS, ACLS, IAAS, educación al paciente, seguridad del paciente, protocolos",
        ),
        height=110,
        key="kw",
        label_visibility="collapsed",
    )

    st.markdown("### Subir CVs (PDF o TXT)")
    files = st.file_uploader(
        "Arrastra y suelta o busca archivos",
        key=st.session_state.uploader_key,
        type=["pdf", "txt"],
        accept_multiple_files=True,
        label_visibility="collapsed",
    )

    # Proceso automático: cada vez que subes archivos, analizamos
    if files:
        st.session_state.candidates = []
        for f in files:
            # guardamos bytes para visor
            f.seek(0)
            b = f.read()
            f.seek(0)
            text = extract_text_from_file(f)
            score, reasons = simple_score(text, jd_text, kw_text)
            st.session_state.candidates.append({
                "Name": f.name,
                "Score": score,
                "Reasons": reasons,
                "_bytes": b,
                "_is_pdf": Path(f.name).suffix.lower() == ".pdf",
            })
        # Sincroniza pipeline a partir de candidates si pipeline está vacío
        if not st.session_state.pipeline:
            for c in st.session_state.candidates:
                st.session_state.pipeline.append({
                    "name": c["Name"],
                    "score": int(c["Score"]),
                    "stage": "Leads",
                    "last_contact": None,
                    "source": "CV",
                    "notes": ""
                })

    st.divider()

    if st.button("Limpiar Lista", use_container_width=True):
        st.session_state.candidates = []
        st.session_state.pipeline = []
        st.session_state.committee = []
        st.session_state.uploader_key = f"u{pd.Timestamp.utcnow().value}"
        st.rerun()

# ======================================================================================
# PESTAÑAS
# ======================================================================================
tab_puestos, tab_eval, tab_pipe, tab_gerencia, tab_hh, tab_oferta = st.tabs(
    ["📋 Puestos", "🧪 Evaluación de CVs", "👥 Pipeline de Candidatos", "🗂️ Entrevista (Gerencia)", "🧾 Tareas del Headhunter", "📄 Oferta"]
)

# --------------------------------------------------------------------------------------
# TAB 1: PUESTOS
# --------------------------------------------------------------------------------------
with tab_puestos:
    st.markdown("## SelektIA – **Puestos**")

    col_top_l, col_top_c, col_top_r = st.columns([1.8, 1, 1])
    with col_top_l:
        q = st.text_input("Buscar (puesto, ubicación, ID, hiring manager…)",
                          placeholder="Ej: Lima, 10645194, Angela Cruz")
    with col_top_c:
        st.text("")
        show_filters = st.checkbox("Mostrar filtros", value=False)
    with col_top_r:
        st.metric("Puestos totales", len(st.session_state.positions))

    df_pos = st.session_state.positions.copy()

    if show_filters:
        with st.expander("Filtros", expanded=True):
            colf1, colf2, colf3, colf4 = st.columns(4)
            with colf1:
                ubic = st.multiselect("Ubicación",
                                      sorted(df_pos["Ubicación"].unique().tolist()))
            with colf2:
                hm = st.multiselect("Hiring Manager",
                                    sorted(df_pos["Hiring Manager"].unique().tolist()))
            with colf3:
                estado = st.multiselect("Estado",
                                        sorted(df_pos["Estado"].unique().tolist()))
            with colf4:
                dias_abierto = st.slider("Días abierto (máx)",
                                         min_value=0, max_value=60, value=60)

    if q:
        ql = q.lower()
        df_pos = df_pos[
            df_pos["Puesto"].str.lower().str.contains(ql) |
            df_pos["Ubicación"].str.lower().str.contains(ql) |
            df_pos["Hiring Manager"].str.lower().str.contains(ql) |
            df_pos["ID"].astype(str).str.contains(ql)
        ]

    if show_filters:
        if ubic:
            df_pos = df_pos[df_pos["Ubicación"].isin(ubic)]
        if hm:
            df_pos = df_pos[df_pos["Hiring Manager"].isin(hm)]
        if estado:
            df_pos = df_pos[df_pos["Estado"].isin(estado)]
        df_pos = df_pos[df_pos["Días Abierto"] <= dias_abierto]

    st.caption(f"Mostrando **{len(df_pos)}** posiciones")
    st.dataframe(
        df_pos[
            [
                "Puesto", "Días Abierto", "Leads", "Nuevos", "Recruiter Screen",
                "HM Screen", "Entrevista Telefónica", "Entrevista Presencial",
                "Ubicación", "Hiring Manager", "Estado", "ID"
            ]
        ].sort_values(["Estado", "Días Abierto", "Leads"], ascending=[True, True, False]),
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

        st.markdown("### Visor de CV (PDF/TXT) ↪️")
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
# TAB 3: PIPELINE DE CANDIDATOS — Tabla (no editable) + Panel (derecha)
# --------------------------------------------------------------------------------------
with tab_pipe:
    st.markdown("## SelektIA – **Pipeline de Candidatos**")

    # --- CSS mínimo para chips (badges) del panel derecho
    st.markdown("""
    <style>
    .badge {display:inline-block; padding:3px 8px; margin:2px 6px 2px 0;
            border-radius:999px; font-size:12px; line-height:1; white-space:nowrap;}
    .badge-green {background:#E8FFF5; color:#0F5132; border:1px solid #B7F0D0;}
    .badge-amber {background:#FFF6E6; color:#7A4D00; border:1px solid #FFD8A8;}
    .badge-gray {background:#F1F3F5; color:#495057; border:1px solid #E9ECEF;}
    </style>
    """, unsafe_allow_html=True)

    if not st.session_state.pipeline:
        if st.session_state.candidates:
            for c in st.session_state.candidates:
                st.session_state.pipeline.append({
                    "name": c["Name"],
                    "score": int(c["Score"]),
                    "stage": "Leads",
                    "last_contact": None,
                    "source": "CV",
                    "notes": ""
                })
        else:
            st.info("Aún no hay candidatos en pipeline. Sube CVs para iniciar.")
            st.stop()

    # normaliza filas
    pipe_rows = []
    for p in st.session_state.pipeline:
        pipe_rows.append({
            "name": p.get("name"),
            "match": int(p.get("score", 0)),
            "stage": p.get("stage", "Leads"),
            "last_contact": p.get("last_contact", None),
            "source": p.get("source", "CV"),
            "notes": p.get("notes", ""),
        })
    df_pipe = pd.DataFrame(pipe_rows)
    df_view = df_pipe.rename(columns={
        "name": "Candidato",
        "match": "Match (%)",
        "stage": "Etapa",
        "last_contact": "Último contacto",
        "source": "Fuente",
        "notes": "Notas"
    })

    colL, colR = st.columns([1.25, 1])

    with colL:
        st.caption("Candidatos (clic o selección para ver detalles a la derecha)")
        st.dataframe(
            df_view[["Candidato", "Match (%)", "Etapa", "Último contacto", "Fuente", "Notas"]],
            use_container_width=True,
            height=320
        )

        c1, c2 = st.columns(2)
        with c1:
            if st.button("Mover Leads → Contactado", use_container_width=True):
                for p in st.session_state.pipeline:
                    if p.get("stage", "Leads") == "Leads":
                        p["stage"] = "Contactado"
                st.success("Se movieron los Leads a Contactado.")
                st.rerun()
        with c2:
            if st.button("Marcar contacto (hoy)", use_container_width=True):
                now = datetime.now().strftime("%Y-%m-%d %H:%M")
                for p in st.session_state.pipeline:
                    if p.get("stage") in ("Contactado", "Screen"):
                        p["last_contact"] = now
                st.success("Último contacto marcado en candidatos Contactado/Screen.")
                st.rerun()

        with st.expander("Resumen por etapa", expanded=False):
            resumen = (
                df_view.groupby("Etapa")["Candidato"]
                .count().reset_index().rename(columns={"Candidato": "Candidatos"})
            )
            st.dataframe(resumen, use_container_width=True, height=160)

    with colR:
        st.markdown("### Detalle del candidato")

        cand_names = df_view["Candidato"].tolist()
        sel_name = st.selectbox("Seleccionar", cand_names, index=0, key="pipe_selected_name")

        row = df_pipe[df_pipe["name"] == sel_name].iloc[0]
        st.markdown(f"**{row['name']}**")
        alto = int(row["match"]) >= 60
        st.markdown(f"**Match estimado:** {'✅ Alto' if alto else '⚠️ Medio/Bajo'}")
        st.markdown(f"**Etapa:** {row['stage']}  \n**Último contacto:** {row['last_contact'] or '—'}  \n**Fuente:** {row['source']}")

        # Chips (simple demo) basadas en keywords del sidebar
        try:
            kws = [k.strip() for k in st.session_state.kw.split(",") if k.strip()]
        except Exception:
            kws = [k.strip() for k in (st.session_state.get("kw") or "").split(",") if k.strip()]
        validated = kws[:1] if kws else []
        likely = []
        to_validate = kws[:6] if kws else []

        def chips(items, cls):
            if not items:
                return "<span class='badge badge-gray'>—</span>"
            # st._escape_md es util; si no existe en tu versión, usa html.escape
            return " ".join([f"<span class='badge {cls}'>{st._escape_md(i)}</span>" for i in items])

        st.markdown("**Validated Skills**")
        st.markdown(chips(validated, "badge-green"), unsafe_allow_html=True)

        st.markdown("**Likely Skills**")
        st.markdown(chips(likely, "badge-amber"), unsafe_allow_html=True)

        st.markdown("**Skills to Validate**")
        st.markdown(chips(to_validate, "badge-gray"), unsafe_allow_html=True)

        st.markdown("---")
        st.caption("Acciones rápidas")
        a1, a2 = st.columns(2)
        with a1:
            if st.button("Añadir nota 'Buen encaje'"):
                for p in st.session_state.pipeline:
                    if p.get("name") == sel_name:
                        note = (p.get("notes") or "")
                        p["notes"] = (note + " | Buen encaje").strip(" |")
                st.toast("Nota agregada", icon="✅")
        with a2:
            if st.button("Mover a ‘Entrevista (Gerencia)’"):
                if sel_name not in st.session_state.committee:
                    st.session_state.committee.append(sel_name)
                st.toast("Enviado a Entrevista (Gerencia)", icon="📨")

# --------------------------------------------------------------------------------------
# TAB 4: ENTREVISTA (GERENCIA)
# --------------------------------------------------------------------------------------
with tab_gerencia:
    st.markdown("## SelektIA – **Entrevista (Gerencia)**")

    if not st.session_state.committee:
        st.info("No hay candidatas/os en ‘Entrevista (Gerencia)’. Muévelos desde el Pipeline.")
    else:
        st.markdown("**Candidatos en entrevista (gerencia):**")
        for n in st.session_state.committee:
            st.markdown(f"- {n}")

        st.markdown("### Asignación de Headhunter")
        hh_name = st.selectbox("Headhunter asignado", ["Carla P.", "Daniel R.", "Marcos T.", "Lucía S."], index=0)
        if st.button("Asignar / Reasignar"):
            st.success(f"Headhunter asignado: {hh_name}")

# --------------------------------------------------------------------------------------
# TAB 5: TAREAS DEL HEADHUNTER
# --------------------------------------------------------------------------------------
with tab_hh:
    st.markdown("## SelektIA – **Tareas del Headhunter**")

    # elegir candidata objetivo desde pipeline o comité
    pool = sorted(set([p["name"] for p in st.session_state.pipeline] + st.session_state.committee))
    if not pool:
        st.info("No hay candidatos disponibles.")
        st.stop()

    tgt = st.selectbox("Candidata/o", pool, index=0)

    task = st.session_state.hh_tasks.get(tgt, {
        "contacto": False,
        "agendada": False,
        "feedback": False,
        "notas": "",
        "fortalezas": "",
        "riesgos": "",
        "pretension": "",
        "disponibilidad": "",
        "sent_to_committee": False,
        "due_date": date.today(),
        "attachments": []
    })

    colA, colB = st.columns([1, 1])
    with colA:
        st.markdown("### Checklist hoy (HH)")
        c1 = st.checkbox("✅ Contacto hecho", value=task["contacto"], disabled=task["sent_to_committee"])
        c2 = st.checkbox("✅ Entrevista agendada", value=task["agendada"], disabled=task["sent_to_committee"])
        c3 = st.checkbox("✅ Feedback recibido", value=task["feedback"], disabled=task["sent_to_committee"])

        due = st.date_input("Due date (SLA)", value=task["due_date"], disabled=task["sent_to_committee"])
        # SLA badges
        slap = ""
        if due < date.today():
            slap = ":red[**Vencido**]"
        elif (due - date.today()).days <= 1:
            slap = ":orange[**≤24h**]"
        if slap:
            st.caption(slap)

    with colB:
        st.markdown("### Notas (obligatorio)")
        fortalezas = st.text_area("3 fortalezas", value=task["fortalezas"], placeholder="• ...\n• ...\n• ...", height=100, disabled=task["sent_to_committee"])
        riesgos = st.text_area("2 riesgos", value=task["riesgos"], placeholder="• ...\n• ...", height=70, disabled=task["sent_to_committee"])
        pret = st.text_input("Pretensión salarial", value=task["pretension"], placeholder="Ej: S/ 3,800", disabled=task["sent_to_committee"])
        disp = st.text_input("Disponibilidad", value=task["disponibilidad"], placeholder="Ej: inmediata / 15 días", disabled=task["sent_to_committee"])

    st.markdown("### Adjuntos (BLS/ACLS, Colegiatura)")
    files_hh = st.file_uploader("PDF/IMG (opcional)", type=["pdf","png","jpg","jpeg"], accept_multiple_files=True, disabled=task["sent_to_committee"])
    new_attachments = task["attachments"][:]
    if files_hh and not task["sent_to_committee"]:
        for f in files_hh:
            new_attachments.append({"name": f.name, "bytes": f.read()})

    # Guardar cambios temporales
    if st.button("Guardar cambios"):
        st.session_state.hh_tasks[tgt] = {
            "contacto": c1, "agendada": c2, "feedback": c3,
            "fortalezas": fortalezas, "riesgos": riesgos,
            "pretension": pret, "disponibilidad": disp,
            "notas": (fortalezas + "\n" + riesgos).strip(),
            "due_date": due,
            "attachments": new_attachments,
            "sent_to_committee": task["sent_to_committee"]
        }
        st.success("Cambios guardados.")

    st.divider()

    blocked = task.get("sent_to_committee", False)
    if not blocked:
        if st.button("Enviar a Comité"):
            # validación mínima
            if not fortalezas.strip() or not riesgos.strip():
                st.warning("Completa fortalezas y riesgos.")
            else:
                st.session_state.hh_tasks[tgt] = {
                    "contacto": c1, "agendada": c2, "feedback": c3,
                    "fortalezas": fortalezas, "riesgos": riesgos,
                    "pretension": pret, "disponibilidad": disp,
                    "notas": (fortalezas + "\n" + riesgos).strip(),
                    "due_date": due,
                    "attachments": new_attachments,
                    "sent_to_committee": True
                }
                if tgt not in st.session_state.committee:
                    st.session_state.committee.append(tgt)
                st.success("Enviado a Comité. Checklist congelado.")
                st.rerun()
    else:
        st.info("Checklist bloqueado (enviado a Comité).")

# --------------------------------------------------------------------------------------
# TAB 6: OFERTA
# --------------------------------------------------------------------------------------
with tab_oferta:
    st.markdown("## SelektIA – **Oferta**")

    # selecciona candidata (desde comité suele tener sentido)
    pool = st.session_state.committee or [p["name"] for p in st.session_state.pipeline]
    if not pool:
        st.info("No hay candidatas/os para oferta.")
        st.stop()

    tgt = st.selectbox("Candidata/o", pool, index=0, key="offer_cand")
    of = st.session_state.offers.get(tgt, {
        "puesto": "",
        "ubicacion": "",
        "modalidad": "Presencial",
        "contrato": "Indeterminado",
        "salario": "",
        "beneficios": "",
        "inicio": date.today(),
        "caducidad": date.today(),
        "aprobadores": "",
        "estado": "Borrador",
        "timeline": []
    })

    c1, c2 = st.columns(2)
    with c1:
        puesto_o = st.text_input("Puesto", value=of["puesto"])
        ubic_o = st.text_input("Ubicación", value=of["ubicacion"])
        mod_o = st.selectbox("Modalidad", ["Presencial","Híbrido","Remoto"], index=["Presencial","Híbrido","Remoto"].index(of["modalidad"]))
        cont_o = st.selectbox("Tipo de contrato", ["Indeterminado","Plazo fijo","Servicio (honorarios)"], index=["Indeterminado","Plazo fijo","Servicio (honorarios)"].index(of["contrato"]))
        sal_o = st.text_input("Salario (rango y neto)", value=of["salario"], placeholder="USD 2,000–2,800 neto")
    with c2:
        bene_o = st.text_area("Bonos/beneficios", value=of["beneficios"], height=90)
        ini_o = st.date_input("Fecha de inicio", value=of["inicio"])
        cad_o = st.date_input("Fecha de caducidad de oferta", value=of["caducidad"])
        aprov_o = st.text_input("Aprobadores (Gerencia, Legal, Finanzas)", value=of["aprobadores"])

    colb1, colb2, colb3, colb4 = st.columns(4)
    with colb1:
        if st.button("Generar oferta (PDF)"):
            st.toast("Generación simulada de carta PDF", icon="📄")
            of["timeline"].append((datetime.now().isoformat(), "Carta de oferta generada"))
    with colb2:
        if st.button("Enviar"):
            of["estado"] = "Enviada"
            of["timeline"].append((datetime.now().isoformat(), "Oferta enviada"))
            st.success("Oferta enviada.")
    with colb3:
        if st.button("Registrar contraoferta"):
            of["estado"] = "Contraoferta"
            of["timeline"].append((datetime.now().isoformat(), "Contraoferta registrada"))
            st.info("Se registró una contraoferta.")
    with colb4:
        if st.button("Marcar aceptada"):
            of["estado"] = "Aceptada"
            of["timeline"].append((datetime.now().isoformat(), "Oferta aceptada"))
            st.success("¡Oferta aceptada!")

    # guardar
    st.session_state.offers[tgt] = {
        "puesto": puesto_o, "ubicacion": ubic_o, "modalidad": mod_o, "contrato": cont_o,
        "salario": sal_o, "beneficios": bene_o, "inicio": ini_o, "caducidad": cad_o,
        "aprobadores": aprov_o, "estado": of["estado"], "timeline": of["timeline"]
    }

    st.markdown("---")
    st.subheader("Estado: " + st.session_state.offers[tgt]["estado"])
    st.markdown("**Línea de tiempo**")
    if st.session_state.offers[tgt]["timeline"]:
        tl_df = pd.DataFrame(st.session_state.offers[tgt]["timeline"], columns=["Fecha", "Evento"])
        st.dataframe(tl_df, use_container_width=True, height=180)
    else:
        st.caption("Sin eventos aún.")
