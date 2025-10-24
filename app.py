# app.py
import io
import re
import base64
import pandas as pd
import plotly.express as px
import streamlit as st
from pdfminer.high_level import extract_text

# =========================
# Configuración
# =========================
st.set_page_config(
    page_title="SelektIA – Evaluación de CVs",
    page_icon="🗂️",
    layout="wide"
)

PRIMARY = "#00CD78"
SIDEBAR_BG = "#10172A"      # columna izquierda
BOX_BG = "#132840"          # fondo + borde de TODOS los boxes izquierda
LIGHT_BG = "#F5F7FA"        # fondo derecha
TEXT = "#FFFFFF"            # texto blanco
ACCENT = "#9FB3C8"          # gris azulado sutil
RADIUS = "14px"

# =========================
# Estilos CSS unificados
# =========================
CSS = f"""
<style>
/* Fondo general */
body, .main, [data-testid="stAppViewContainer"] {{
  background: {LIGHT_BG};
}}

/* Sidebar */
[data-testid="stSidebar"] {{
  background: {SIDEBAR_BG} !important;
}}
/* Texto del sidebar en blanco por defecto */
[data-testid="stSidebar"] * {{
  color: {TEXT} !important;
}}

/* Títulos en verde Wayki */
h1, h2, h3, h4, h5 {{
  color: {PRIMARY} !important;
  font-weight: 800 !important;
}}

/* Etiquetas del panel izquierdo */
.sidebar-label {{
  color: {PRIMARY} !important;
  font-weight: 800 !important;
  display:block;
  margin: 2px 0 6px;
}}

/* === BOXES UNIFICADOS EN LA IZQUIERDA (mismo look) === */
/* Select cerrado (contenedor) */
[data-testid="stSidebar"] [data-testid="stSelectbox"] > div > div {{
  background:{BOX_BG} !important;
  border:1px solid {BOX_BG} !important;
  border-radius:{RADIUS} !important;
}}
/* Texto del valor mostrado en select */
[data-testid="stSidebar"] [data-testid="stSelectbox"] [data-baseweb="select"] div {{
  color:{TEXT} !important;
}}

/* Inputs */
[data-testid="stSidebar"] [data-testid="stTextInput"] input {{
  background:{BOX_BG} !important;
  color:{TEXT} !important;
  border:1px solid {BOX_BG} !important;
  border-radius:{RADIUS} !important;
}}
/* Textareas */
[data-testid="stSidebar"] [data-testid="stTextArea"] textarea {{
  background:{BOX_BG} !important;
  color:{TEXT} !important;
  border:1px solid {BOX_BG} !important;
  border-radius:{RADIUS} !important;
}}
/* Botón (sugerir keywords / browse) */
[data-testid="stSidebar"] button[kind="primary"],
[data-testid="stSidebar"] button[kind="secondary"] {{
  background:{PRIMARY} !important;
  color:#011014 !important;
  border:1px solid {PRIMARY} !important;
  border-radius:{RADIUS} !important;
  font-weight:800 !important;
}}
[data-testid="stSidebar"] button:hover {{
  filter:brightness(1.05);
  transform:translateY(-1px);
}}

/* Dropzone */
[data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] {{
  background:{BOX_BG} !important;
  border:2px dashed {ACCENT} !important;
  color:{TEXT} !important;
  border-radius:{RADIUS} !important;
}}
/* Botón Browse dentro del dropzone */
[data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] button {{
  background:{PRIMARY} !important;
  color:#011014 !important;
  border:1px solid {PRIMARY} !important;
  border-radius:{RADIUS} !important;
  font-weight:800 !important;
}}

/* Tarjetas de archivo subido */
[data-testid="stSidebar"] [data-testid="stFileUploader"] .uploadedFile {{
  background:{BOX_BG} !important;
  border:1px solid {BOX_BG} !important;
  border-radius:{RADIUS} !important;
  color:{TEXT} !important;
}}
.uploadedFileName, .uploadedFileSize {{ color:{TEXT} !important; }}

/* Icono PDF rojo para que resalte */
[data-testid="stSidebar"] [data-testid="stFileUploader"] .uploadedFile::before {{
  content:"PDF";
  display:inline-flex;
  align-items:center;
  justify-content:center;
  width:28px;
  height:28px;
  margin-right:.6rem;
  background:#FF5252;
  color:white;
  font-weight:900;
  border-radius:6px;
}}

/* === CONTROLES EN LA DERECHA EN TONO CLARO === */
.select-light > div > div {{
  background:#E9EEF5 !important;
  color:#0F172A !important;
  border:1px solid #E9EEF5 !important;
  border-radius:{RADIUS} !important;
}}
[data-testid="stExpander"] > details {{
  background:#EEF3FA !important;
  border:1px solid #EEF3FA !important;
  border-radius:{RADIUS} !important;
  color:#0F172A !important;
}}
[data-testid="stExpander"] summary p {{
  color:#0F172A !important;
  font-weight:700 !important;
}}

/* Pastilla de ayuda bajo el título */
.helper-pill {{
  background:#E3EEFF;
  color:#1E293B;
  border-radius:10px;
  padding:10px 12px;
  font-size:.95rem;
}}

/* Cabecera de tablas */
[data-testid="stTable"] th, .dataframe thead th {{
  background:#E9EEF5 !important;
  color:#0F172A !important;
  font-weight:800 !important;
}}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

# Inyección ligera para que los select de la derecha usen la clase select-light automáticamente
st.markdown("""
<script>
const applyLightToMainSelects = () => {
  const app = window.parent.document;
  const all = [...app.querySelectorAll('div[data-baseweb="select"]')];
  all.forEach(el => {
    // ignora los que están dentro del sidebar
    let inSidebar = false;
    let node = el;
    while (node) {
      if (node.getAttribute && node.getAttribute('data-testid') === 'stSidebar') { inSidebar = true; break; }
      node = node.parentElement;
    }
    if (!inSidebar) {
       const wrap = el.closest('div');
       if (wrap) wrap.parentElement?.parentElement?.classList?.add('select-light');
    }
  });
}
setTimeout(applyLightToMainSelects, 300);
</script>
""", unsafe_allow_html=True)

# =========================
# Logo en sidebar
# =========================
def logo_b64(path="assets/logo-wayki.png"):
    try:
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except Exception:
        return None

logo64 = logo_b64()
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
    height=110, label_visibility="collapsed"
)

if st.sidebar.button("Sugerir keywords"):
    if "HIS" not in jd_text.upper():
        jd_text += "\n Palabras sugeridas: HIS, SAP IS-H, BLS/ACLS, IAAS, protocolos, seguridad del paciente, educación al paciente/familia."

st.sidebar.markdown('<span class="sidebar-label">Palabras clave del perfil (ajústalas si es necesario)</span>', unsafe_allow_html=True)
keywords_text = st.sidebar.text_area(
    "",
    value="HIS, SAP IS-H, BLS, ACLS, IAAS, educación al paciente, seguridad del paciente, monitoreo, eventos adversos",
    height=110, label_visibility="collapsed"
)

st.sidebar.markdown('<span class="sidebar-label">Subir CVs (PDF o TXT)</span>', unsafe_allow_html=True)
files = st.sidebar.file_uploader(
    "Arrastra aquí",
    type=["pdf","txt"],
    accept_multiple_files=True,
    label_visibility="collapsed"
)

# =========================
# Helpers de texto/score
# =========================
def read_pdf(b: bytes) -> str:
    try:
        return extract_text(io.BytesIO(b)) or ""
    except Exception:
        return ""

def normalize(s: str) -> str:
    s = s.lower()
    s = re.sub(r"[^a-z0-9áéíóúüñ\s]", " ", s)
    return re.sub(r"\s+", " ", s).strip()

def keywords_from_text(txt: str):
    raw = [k.strip() for k in re.split(r"[,\n;]", txt) if k.strip()]
    syn = {
        "bls": ["soporte vital básico", "basic life support"],
        "acls": ["advanced cardiac life support", "soporte vital avanzado"],
        "his": ["sistema his", "hospital information system"],
        "sap is-h": ["sap ish", "sap is-h"]
    }
    out = []
    for k in raw:
        out.append(k)
        for base, vs in syn.items():
            if base in k.lower():
                out.extend(vs)
    uniq, final = set(), []
    for k in out:
        if k.lower() not in uniq:
            uniq.add(k.lower())
            final.append(k)
    return final

def score_cv(text: str, keywords: list[str]) -> tuple[int, list[str]]:
    nt = normalize(text)
    found, score = [], 0
    for kw in keywords:
        k = normalize(kw)
        if len(k) < 2:
            continue
        if re.search(rf"\b{k}\b", nt):
            found.append(kw)
            score += 1
    return score, found

# =========================
# Procesar CVs
# =========================
kw_list = keywords_from_text(keywords_text)
rows = []
files_map = {}  # name -> {bytes, mime, text}

if files:
    for f in files:
        raw = f.read()
        name = f.name
        mime = f.type or ("application/pdf" if name.lower().endswith(".pdf") else "text/plain")

        if mime == "application/pdf" or name.lower().endswith(".pdf"):
            text = read_pdf(raw)
        else:
            text = raw.decode("utf-8", errors="ignore")

        s, found = score_cv(text, kw_list)
        rows.append({
            "Name": name,
            "Score": s,
            "Reasons": f"{len(found)}/{len(kw_list)} keywords encontradas — Coincidencias: " + (", ".join(found) if found else "—"),
            "PDF_text": f"{len(text)} chars"
        })
        files_map[name] = {"bytes": raw, "mime": mime, "text": text}

# =========================
# UI derecha: tabla + gráfico + visor
# =========================
if rows:
    df = pd.DataFrame(rows).sort_values("Score", ascending=False).reset_index(drop=True)

    st.markdown('<div class="helper-pill">Define el puesto/JD, sugiere (o edita) keywords y sube algunos CVs (PDF o TXT) para evaluar.</div>', unsafe_allow_html=True)
    st.dataframe(df[["Name","Score","Reasons","PDF_text"]], use_container_width=True, height=260)

    threshold = st.slider("Umbral de selección", 0, max(1, df["Score"].max()+1), min(50, max(1, df["Score"].max())))
    fig = px.bar(
        df, x="Name", y="Score",
        color=df["Score"] >= threshold,
        color_discrete_map={True: PRIMARY, False: "#C7D2E3"},
        text="Score", height=360
    )
    fig.update_traces(textposition="outside")
    fig.update_layout(xaxis_title=None, yaxis_title="Score", showlegend=False, bargap=0.25, margin=dict(l=10,r=10,t=10,b=10))
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Visor de CV (PDF)")
    colL, colR = st.columns([1,2])

    with colL:
        st.caption("Elige un candidato")
        choice = st.selectbox("", df["Name"].tolist(), label_visibility="collapsed")
        # fuerza select claro por JS (añade clase select-light)
        st.markdown(
            """
            <script>
            const app = window.parent.document;
            const boxes = app.querySelectorAll('div[data-baseweb="select"]');
            if (boxes && boxes.length){
              const last = boxes[boxes.length-1];
              const wrap = last.closest('div');
              if (wrap) wrap.parentElement?.parentElement?.classList?.add('select-light');
            }
            </script>
            """, unsafe_allow_html=True
        )

        with st.expander("Elegir candidato (opción alternativa)"):
            alt = st.selectbox("Candidato", df["Name"].tolist(), key="alt_choice")
            if alt:
                choice = alt

    with colR:
        st.caption(f"Mostrando: {choice}")

    # === Mostrar PDF o texto según el tipo ===
    blob = files_map.get(choice, {})
    raw = blob.get("bytes", b"")
    mime = blob.get("mime", "application/pdf")
    text = blob.get("text", "")

    if raw:
        if mime == "application/pdf":
            # visor PDF embebido
            b64pdf = base64.b64encode(raw).decode("utf-8")
            st.download_button("Descargar PDF", data=raw, file_name=choice, mime="application/pdf")
            st.markdown(
                f'<iframe src="data:application/pdf;base64,{b64pdf}" width="100%" height="850px" style="border:1px solid #E5E7EB;border-radius:{RADIUS};"></iframe>',
                unsafe_allow_html=True
            )
        else:
            # si no es PDF, muestra el texto plano
            st.download_button("Descargar archivo", data=raw, file_name=choice, mime=mime)
            st.text_area("Contenido del archivo", text, height=450)

    st.caption(f"Puesto: **{role}** — Keywords totales: **{len(kw_list)}**")

else:
    st.info("Sube algunos CVs para ver el demo.")
