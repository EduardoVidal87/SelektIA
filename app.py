# Al inicio de app.py (o donde tengas set_page_config)
st.set_page_config(page_title="SelektIA", page_icon="assets/logo-wayki.png", layout="wide")

# Logo en el sidebar
st.sidebar.image("assets/logo-wayki.png", use_column_width=True)

# app.py — SelektIA (PyMuPDF extractor + ranking + gráfico + Excel + visor PDF + keywords sugeridas)
import streamlit as st
import pandas as pd
import plotly.express as px
from io import BytesIO
from pdfminer.high_level import extract_text
import base64, unicodedata, re

# ------------------- utilidades -------------------
def _norm(s: str) -> str:
    s = s.lower()
    s = ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')
    return s

SYNONYMS = {
    "his": ["sistema hospitalario", "registro clinico", "erp salud"],
    "sap is-h": ["sap ish", "sap is h", "sap hospital"],
    "bombas de infusion": ["infusion pumps"],
    "bls": ["soporte vital basico"],
    "acls": ["soporte vital avanzado"],
    "uci intermedia": ["uci", "cuidados intermedios"],
    "educacion al paciente": ["educacion a pacientes", "educacion al usuario"],
}

DOMAIN_DICTIONARY = [
    # clínico hospital
    "HIS","SAP IS-H","bombas de infusión","5 correctos","IAAS","bundles VAP","BRC","CAUTI",
    "curación avanzada","educación al paciente","BLS","ACLS","hospitalización","UCI intermedia",
    "LIS","laboratorio clínico","control de calidad","Westgard","TAT","validación","verificación",
    "bioseguridad","calibración","preanalítica","postanalítica","auditoría","trazabilidad",
    "admisión","recepción","caja","facturación","conciliación","verificación de seguros",
    "telemedicina","triage","rutas clínicas","HTA","DM2","dispensación segura","farmacovigilancia",
    "FEFO","cadena de frío","interacciones","stock crítico"
]

def expand_keywords(kws):
    out = []
    for k in kws:
        k2 = _norm(k)
        if not k2:
            continue
        out.append(k2)
        for syn in SYNONYMS.get(k2, []):
            out.append(_norm(syn))
    # únicos, mantiene orden
    return list(dict.fromkeys(out))

def pdf_to_text_from_bytes(data: bytes) -> str:
    """
    Extrae texto de PDFs. Intenta primero PyMuPDF (fitz), luego pdfminer.
    Devuelve "" si no encuentra texto (posible escaneo).
    """
    # 1) PyMuPDF
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(stream=data, filetype="pdf")
        text_pages = []
        for page in doc:
            text_pages.append(page.get_text("text"))
        text = "\n".join(text_pages).strip()
        if len(text) > 20:
            return text
    except Exception:
        pass

    # 2) Fallback: pdfminer
    try:
        return (extract_text(BytesIO(data)) or "").strip()
    except Exception:
        return ""

def smart_keywords_parse(jd_text: str) -> list[str]:
    """Acepta coma, punto y coma, salto de línea, '/', y ' y '. Limpia frases de relleno."""
    parts = [x.strip() for x in re.split(r'[,\n;]+', jd_text) if x.strip()]
    out = []
    for p in parts:
        sub = [s.strip() for s in re.split(r'/|\by\b', p, flags=re.IGNORECASE) if s.strip()]
        out.extend(sub if sub else [p])
    STOP_PHRASES = ["manejo de", "manejo", "uso de", "uso", "vigente", "vigentes", "conocimiento de"]
    cleaned = []
    for k in out:
        kk = k
        for sp in STOP_PHRASES:
            kk = re.sub(rf'\b{sp}\b', '', kk, flags=re.I)
        kk = kk.strip(" .-/")
        if kk:
            cleaned.append(kk)
    return cleaned

def suggest_keywords_from_text(role_title: str, jd_free_text: str) -> list[str]:
    """Sugeridor simple: acrónimos, términos del diccionario y algunos n-gramas."""
    text = jd_free_text + " " + role_title
    text_norm = _norm(text)
    # acrónimos (BLS/ACLS/LIS/HIS…)
    acronyms = re.findall(r'\b[A-ZÁÉÍÓÚÑ]{2,}(?:-[A-Z]{1,})?\b', jd_free_text)
    acronyms = [a.strip() for a in acronyms]
    # diccionario
    dict_hits = [t for t in DOMAIN_DICTIONARY if _norm(t) in text_norm]
    # n-gramas 2–3 palabras (heurístico)
    words = [w for w in re.findall(r'[a-záéíóúñ]{3,}', text_norm) if w not in {
        "para","con","por","del","los","las","una","uno","unos","unas","que","de","al","la","el","y","en","se","su"
    }]
    ngrams = []
    for n in (2,3):
        for i in range(len(words)-n+1):
            ngram = " ".join(words[i:i+n])
            ngrams.append(ngram)
    candidates = acronyms + dict_hits + ngrams
    uniq, seen = [], set()
    for c in candidates:
        key = _norm(c)
        if key not in seen and len(c) >= 3:
            uniq.append(c)
            seen.add(key)
    return uniq[:25]

def score_candidate(raw_text: str, jd_keywords: list) -> tuple[int, str, list]:
    text = _norm(" ".join(raw_text.split()))
    base_kws = [k.strip() for k in jd_keywords if k.strip()]
    # usamos solo las "base" para el conteo de aciertos, pero ampliamos para búsqueda robusta
    expanded = expand_keywords(base_kws)
    # keywords que realmente aparecieron (de las base)
    matched = [k for k in base_kws if re.search(rf"\b{re.escape(_norm(k))}\b", text)]
    hits = len(matched)
    ratio = min(hits / max(1, len(base_kws)), 1.0)
    score = round(100 * ratio)
    reasons = f"{hits}/{len(base_kws)} keywords encontradas"
    return score, reasons, matched

def build_excel(shortlist_df: pd.DataFrame, all_df: pd.DataFrame) -> bytes:
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as xw:
        shortlist_df.to_excel(xw, index=False, sheet_name="Selected")
        all_df.to_excel(xw, index=False, sheet_name="All_Scores")
    buf.seek(0); return buf.read()

def show_pdf(file_bytes: bytes, height: int = 820):
    """
    Visor PDF robusto:
    - Intenta renderizar con pdf.js (streamlit-pdf-viewer) pasando los bytes directamente.
    - Si la librería no está disponible o el navegador bloquea la carga, hace fallback a <object>
      con un enlace de descarga.
    """
    try:
        # Import local para no romper si aún no está instalada la lib
        from streamlit_pdf_viewer import pdf_viewer
        # Render con pdf.js (acepta bytes)
        pdf_viewer(file_bytes, height=height)
    except Exception:
        # Fallback HTML con enlace de descarga
        import base64
        b64 = base64.b64encode(file_bytes).decode()
        html_code = f"""
        <object data="data:application/pdf;base64,{b64}" type="application/pdf" width="100%" height="{height}">
            <p>No se pudo previsualizar el PDF en el navegador.
            <a download="cv.pdf" href="data:application/pdf;base64,{b64}">Descargar CV</a></p>
        </object>
        """
        st.components.v1.html(html_code, height=height, scrolling=True)


# ------------------- UI -------------------
st.set_page_config(page_title="SelektIA", layout="wide")

st.sidebar.header("Definición del puesto")
role_title = st.sidebar.text_input("Puesto", "Enfermera/o Asistencial – Hospitalización / UCI intermedia")
jd_free_text = st.sidebar.text_area(
    "Job Description (texto libre)",
    "Brindar atención segura. Administración de medicamentos (5 correctos), curación avanzada, manejo de bombas de infusión, "
    "educación al paciente/familia, registro en HIS (SAP IS-H), cumplimiento de bundles VAP/BRC/CAUTI. BLS/ACLS vigentes.",
    height=120
)

# Sugerir keywords desde el JD
if "kw_text" not in st.session_state:
    st.session_state.kw_text = ("HIS, SAP IS-H, bombas de infusión, 5 correctos, IAAS, bundles VAP, BRC, CAUTI, "
                                "curación avanzada, educación al paciente, BLS, ACLS, hospitalización, UCI intermedia")

def _fill_keywords():
    sugg = suggest_keywords_from_text(role_title, jd_free_text)
    st.session_state.kw_text = ", ".join(sugg)

st.sidebar.button("Sugerir keywords", on_click=_fill_keywords)
kw_text = st.sidebar.text_area("Keywords (edítalas si quieres)", key="kw_text", height=120)
jd_keywords = smart_keywords_parse(kw_text)

st.sidebar.header("Upload CVs (PDF o TXT)")
files = st.sidebar.file_uploader("Arrastra aquí", type=["pdf","txt"], accept_multiple_files=True)

st.title("SelektIA – Evaluation Results")

# ------------------- lógica principal -------------------
rows, file_store = [], {}

if files:
    for f in files:
        data = f.read()  # guardo bytes para visor
        file_store[f.name] = {"bytes": data, "type": f.type}

        # texto para scoring
        if f.type == "text/plain":
            raw = data.decode("utf-8", errors="ignore")
        else:
            raw = pdf_to_text_from_bytes(data)

        raw_len = len(raw)
        no_text_flag = "PDF sin texto (posible escaneo)" if raw_len < 20 else f"{raw_len} chars"

        score, reasons, matched = score_candidate(raw, jd_keywords)

        rows.append({
            "Name": f.name.replace(".pdf","").replace("_"," ").title(),
            "FileName": f.name,
            "Score": score,
            "Reasons": reasons + (f" — Coincidencias: {', '.join(matched)}" if matched else ""),
            "PDF_text": no_text_flag
        })

    df = pd.DataFrame(rows).sort_values("Score", ascending=False)

    left, right = st.columns([0.58, 0.42])
    with left:
        st.dataframe(df[["Name","Score","Reasons","PDF_text"]], use_container_width=True)

        st.subheader("Score Comparison")
        threshold = st.slider("Umbral de selección", 0, 100, 50, 1)

        fig = px.bar(
            df, x="Name", y="Score", text="Score",
            color=(df["Score"] >= threshold).map({True: "Seleccionado", False: "Revisión"}),
            color_discrete_map={"Seleccionado": "#00A36C", "Revisión": "#1f77b4"}
        )
        fig.update_traces(
            textposition="outside",
            customdata=df[["Reasons"]].values,
            hovertemplate="<b>%{x}</b><br>Score: %{y}<br>%{customdata[0]}<extra></extra>"
        )
        fig.add_hline(y=threshold, line_dash="dot", opacity=0.6)
        fig.update_layout(yaxis_title="Score", xaxis_title=None, margin=dict(t=70, r=20, b=80, l=40))
        st.plotly_chart(fig, use_container_width=True)

        selected_df = df[df["Score"] >= threshold]
        excel_bytes = build_excel(selected_df, df)
        st.download_button(
            "⬇️ Descargar Excel (Selected + All)",
            data=excel_bytes,
            file_name=f"SelektIA_{_norm(role_title).replace(' ','_')}_Selection.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        st.caption(f"Puesto: {role_title} — Seleccionados: {len(selected_df)} / {len(df)}")

    with right:
        st.subheader("Visor de CV (PDF)")
        choice = st.selectbox("Elige un candidato", options=df["Name"].tolist())
        file_name = df.loc[df["Name"] == choice, "FileName"].iloc[0]
        meta = file_store.get(file_name)
        if meta and meta["type"] == "application/pdf":
            show_pdf(meta["bytes"])
        elif meta:
            st.info("Este archivo no es PDF; muestro el texto:")
            try:
                st.text(meta["bytes"][:2000].decode("utf-8","ignore"))
            except Exception:
                st.write("No se pudo mostrar el contenido.")
else:
    st.info("Define el puesto/JD, sugiere (o edita) keywords y sube algunos CVs (PDF o TXT) para evaluar.")
