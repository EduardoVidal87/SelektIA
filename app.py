# app.py
import io
import re
import base64
import pandas as pd
import plotly.express as px
import streamlit as st
from pdfminer.high_level import extract_text

# =========================
# Configuración general
# =========================
st.set_page_config(
    page_title="SelektIA – Evaluación de CVs",
    page_icon="🗂️",
    layout="wide"
)

PRIMARY = "#00CD78"
SIDEBAR_BG = "#10172A"      # barra izquierda
BOX_BG = "#132840"          # interiores y bordes de boxes en la izquierda
LIGHT_BG = "#F5F7FA"        # fondo claro principal
TEXT = "#FFFFFF"            # texto blanco
ACCENT = "#9FB3C8"          # gris azulado sutil

# =========================
# Estilos (CSS)
# =========================
CSS = f"""
<style>
/* Fondo app y tipografías */
body, .main, [data-testid="stAppViewContainer"] {{
  background: {LIGHT_BG};
}}
/* Sidebar */
[data-testid="stSidebar"], section[data-testid="stSidebar"] {{
  background: {SIDEBAR_BG} !important;
  color: {TEXT} !important;
}}
/* Títulos globales */
h1, h2, h3, h4, h5, h6 {{
  color: {PRIMARY} !important;
  font-weight: 700;
}}
/* Texto general en sidebar */
[data-testid="stSidebar"] * {{
  color: {TEXT} !important;
}}
/* Etiquetas (subtítulos) del panel izquierdo */
.sidebar-label {{
  color: {PRIMARY} !important;
  font-weight: 700 !important;
  margin-bottom: .25rem;
  display:block;
}}

/* ---------- Componentes de entrada en el panel izquierdo ---------- */
/* Text input */
[data-testid="stTextInput"] input {{
  background:{BOX_BG} !important;
  color:{TEXT} !important;
  border:1px solid {BOX_BG} !important;
  border-radius:10px !important;
}}
/* Text area */
[data-testid="stTextArea"] textarea {{
  background:{BOX_BG} !important;
  color:{TEXT} !important;
  border:1px solid {BOX_BG} !important;
  border-radius:10px !important;
}}
/* Selectbox (contenedor cerrado) */
[data-testid="stSelectbox"] > div > div {{
  background:{BOX_BG} !important;
  color:{TEXT} !important;
  border:1px solid {BOX_BG} !important;
  border-radius:10px !important;
}}
/* Selectbox (valor mostrado) */
[data-testid="stSelectbox"] [data-baseweb="select"] div {{
  color:{TEXT} !important;
}}
/* Botón secundario/primario en panel izquierdo */
[data-testid="stSidebar"] button[kind="secondary"],
[data-testid="stSidebar"] button[kind="primary"] {{
  background:{PRIMARY} !important;
  color:#001017 !important;
  border:1px solid {PRIMARY} !important;
  font-weight:700 !important;
  border-radius:12px !important;
}}
[data-testid="stSidebar"] button[kind="secondary"]:hover,
[data-testid="stSidebar"] button[kind="primary"]:hover {{
  filter:brightness(1.05);
  transform:translateY(-1px);
}}

/* ---------- File uploader ---------- */
/* Zona de arrastre */
[data-testid="stFileUploaderDropzone"] {{
  background:{BOX_BG} !important;
  border:2px dashed {ACCENT} !important;
  color:{TEXT} !important;
  border-radius:14px !important;
}}
/* Botón Browse */
[data-testid="stFileUploaderDropzone"] button {{
  background:{PRIMARY} !important;
  color:#001017 !important;
  border:1px solid {PRIMARY} !important;
  border-radius:10px !important;
}}
/* Caja de cada archivo subido */
[data-testid="stFileUploader"] .uploadedFile {{
  background:{BOX_BG} !important;
  border:1px solid {BOX_BG} !important;
  border-radius:12px !important;
  color:{TEXT} !important;
}}
/* Nombre y tamaño del archivo */
.uploadedFileName, .uploadedFileSize {{
  color:{TEXT} !important;
}}
/* Icono PDF vistoso */
[data-testid="stFileUploader"] .uploadedFile::before {{
  content:"PDF";
  display:inline-flex;
  align-items:center;
  justify-content:center;
  width:28px;
  height:28px;
  margin-right:.5rem;
  background:#FF5252;
  color:white;
  font-weight:900;
  border-radius:6px;
}}

/* ---------- Barra de selección en el visor (dropdown claro) ---------- */
.select-light > div > div {{
  background:#E9EEF5 !important;
  color:#0F172A !important;
  border:1px solid #E9EEF5 !important;
  border-radius:10px !important;
}}

/* ---------- Tabla/ayuda superior ---------- */
.helper-pill {{
  background:#E3EEFF;
  color:#1E293B;
  border-radius:10px;
  padding:10px 12px;
  font-size:.95rem;
}}
/* DataFrame header contraste sutil */
[data-testid="stTable"] th, .dataframe thead th {{
  background:#E9EEF5 !important;
  color:#0F172A !important;
  font-weight:700 !important;
}}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

# =========================
# Encabezado con logotipo
# =========================
def logo_base64(path="assets/logo-wayki.png"):
    try:
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except Exception:
        return None

logo64 = logo_base64()
if logo64:
    st.sidebar.markdown(
        f'<img src="data:image/png;base64,{logo64}" style="width:140px;margin:8px 0 16px 2px;">',
        unsafe_allow_html=True
    )

st.title("SelektIA – Evaluation Results")

# =========================
# Panel izquierdo (definición)
# =========================
st.sidebar.markdown('<span class="sidebar-label">Puesto</span>', unsafe_allow_html=True)
role = st.sidebar.selectbox(
    "", 
    ["Enfermera/o Asistencial – Hospitalización / UCI intermedia", "Otro"],
    index=0, label_visibility="collapsed"
)

st.sidebar.markdown('<span class="sidebar-label">Descripción del puesto (texto libre)</span>', unsafe_allow_html=True)
jd_text = st.sidebar.text_area(
    "",
    value="Resume el objetivo del puesto, responsabilidades, protocolos y competencias clave.",
    height=110,
    label_visibility="collapsed"
)

if st.sidebar.button("Sugerir keywords"):
    if "HIS" not in jd_text.upper():
        jd_text += "\n Palabras sugeridas: HIS, SAP IS-H, BLS/ACLS, IAAS, protocolos, seguridad del paciente, educación al paciente/familia."

st.sidebar.markdown('<span class="sidebar-label">Palabras clave del perfil (ajústalas si es necesario)</span>', unsafe_allow_html=True)
keywords_text = st.sidebar.text_area(
    "",
    value="HIS, SAP IS-H, BLS, ACLS, IAAS, educación al paciente, seguridad del paciente, monitoreo, eventos adversos",
    height=110,
    label_visibility="collapsed"
)

st.sidebar.markdown('<span class="sidebar-label">Subir CVs (PDF o TXT)</span>', unsafe_allow_html=True)
files = st.sidebar.file_uploader(
    "Arrastra aquí",
    type=["pdf","txt"],
    accept_multiple_files=True,
    label_visibility="collapsed"
)

# =========================
# Funciones de parsing y scoring
# =========================
def read_pdf(file_bytes: bytes) -> str:
    try:
        text = extract_text(io.BytesIO(file_bytes))
        return text or ""
    except Exception:
        return ""

def normalize(s: str) -> str:
    s = s.lower()
    s = re.sub(r"[^a-z0-9áéíóúüñ\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def keywords_from_text(txt: str):
    kws = [k.strip() for k in re.split(r"[,\n;]", txt) if k.strip()]
    # sinónimos básicos (ejemplo)
    syn = {
        "bls": ["soporte vital básico", "basic life support"],
        "acls": ["advanced cardiac life support", "soporte vital avanzado"],
        "his": ["sistema his", "hospital information system"],
        "sap is-h": ["sap ish", "sap is-h"]
    }
    expanded = []
    for k in kws:
        expanded.append(k)
        for k0, vs in syn.items():
            if k0 in k.lower():
                expanded.extend(vs)
    # únicos
    seen, final = set(), []
    for k in expanded:
        kl = k.lower()
        if kl not in seen:
            seen.add(kl)
            final.append(k)
    return final

def score_cv(text: str, keywords: list[str]) -> tuple[int, list[str]]:
    nt = normalize(text)
    found = []
    score = 0
    for kw in keywords:
        k = normalize(kw)
        if len(k) < 2: 
            continue
        if re.search(rf"\b{k}\b", nt):
            score += 1
            found.append(kw)
    return score, found

# =========================
# Procesar CVs
# =========================
kw_list = keywords_from_text(keywords_text)
rows = []

if files:
    for f in files:
        raw = f.read()
        if f.type == "text/plain" or f.name.lower().endswith(".txt"):
            text = raw.decode("utf-8", errors="ignore")
        else:
            text = read_pdf(raw)

        s, found = score_cv(text, kw_list)
        rows.append({
            "Name": f.name,
            "Score": s,
            "Reasons": f"{len(found)}/{len(kw_list)} keywords encontradas — Coincidencias: " + (", ".join(found) if found else "—"),
            "PDF_text": f"{len(text)} chars",
            "_text": text
        })

# =========================
# Resultados (tabla + gráfico)
# =========================
if rows:
    df = pd.DataFrame(rows).sort_values("Score", ascending=False).reset_index(drop=True)

    st.markdown('<div class="helper-pill">Define el puesto/JD, sugiere (o edita) keywords y sube algunos CVs (PDF o TXT) para evaluar.</div>', unsafe_allow_html=True)
    st.dataframe(
        df[["Name","Score","Reasons","PDF_text"]],
        use_container_width=True, height=260
    )

    # Gráfico
    threshold = st.slider("Umbral de selección", 0, max(1, df["Score"].max()+1), min(50, max(1, df["Score"].max())), help="Puntaje mínimo para resaltar candidatos")
    fig = px.bar(
        df, x="Name", y="Score",
        color=df["Score"] >= threshold,
        color_discrete_map={True: PRIMARY, False: "#C7D2E3"},
        text="Score",
        height=360
    )
    fig.update_traces(textposition="outside")
    fig.update_layout(
        xaxis_title=None, yaxis_title="Score",
        showlegend=False, bargap=0.25,
        margin=dict(l=10,r=10,t=10,b=10)
    )
    st.plotly_chart(fig, use_container_width=True)

    # =========================
    # Visor de CV (PDF/TXT)
    # =========================
    st.subheader("Visor de CV (PDF)")
    colL, colR = st.columns([1,2])

    with colL:
        st.caption("Elige un candidato")
        # select claro (clase select-light)
        choice = st.selectbox(
            "", df["Name"].tolist(),
            label_visibility="collapsed",
            key="viewer_choice"
        )
        # Aplico CSS “select-light” sólo a este select
        st.markdown(
            """
            <script>
            const boxes = window.parent.document.querySelectorAll('div[data-baseweb="select"]');
            if (boxes && boxes.length){
                boxes[boxes.length-1].parentElement.parentElement.classList.add('select-light');
            }
            </script>
            """, unsafe_allow_html=True
        )

        # Alternativa
        with st.expander("Elegir candidato (opción alternativa)"):
            alt = st.selectbox("Candidato", df["Name"].tolist(), key="alt_choice")
            if st.session_state.alt_choice:
                choice = st.session_state.alt_choice

    with colR:
        st.caption(f"Mostrando: {choice}")

    # Render del texto (por simplicidad mostramos el texto indexado)
    text = df.loc[df["Name"]==choice, "_text"].iloc[0]
    # Extraigo fragmentos donde aparezcan keywords
    def highlight_snippets(t: str, kws: list[str], n=8):
        nt = normalize(t)
        snippets = []
        for kw in kws:
            k = normalize(kw)
            for m in re.finditer(rf"\b{k}\b", nt):
                start = max(0, m.start()-80)
                end   = min(len(nt), m.end()+80)
                snippets.append(nt[start:end])
                if len(snippets) >= n:
                    return snippets
        return snippets
    snips = highlight_snippets(text, kw_list, n=12)
    if snips:
        st.markdown("**Fragmentos con coincidencias:**")
        for sni in snips:
            st.markdown(f"- {sni}")
    else:
        st.info("No hay coincidencias visibles; desplázate por el PDF/Texto completo o ajusta las keywords.")

else:
    st.info("Sube algunos CVs para ver el demo.")


# =========================
# Notas finales
# =========================
st.caption("Puesto: **{}** — Keywords totales: **{}**".format(role, len(kw_list)))
