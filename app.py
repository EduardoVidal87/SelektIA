import streamlit as st
import base64
import pandas as pd

st.set_page_config(page_title="SelektIA – Evaluation Results", layout="wide")

# =========================
# 🎨 Paleta (ajústala aquí)
# =========================
BORDER = "#132840"          # Color de contornos/bordes (NO blanco)
DARK_BG = "#132840"         # Fondo de boxes oscuros
LIGHT_BG = "#F5FAF8"        # Fondo de boxes claros (derecha)
TEXT_ON_DARK = "#FFFFFF"    # Texto sobre fondo oscuro
ACCENT = "#00CD78"          # Titulares y acentos

# =========================
# 🧼 CSS global (bordes y estilos unificados)
# =========================
st.markdown(f"""
<style>
:root {{
  --border: {BORDER};
  --dark-bg: {DARK_BG};
  --light-bg: {LIGHT_BG};
  --text-on-dark: {TEXT_ON_DARK};
  --accent: {ACCENT};
}}

/* Titulares en color de acento */
h1, h2, h3, h4, h5, h6 {{
  color: var(--accent) !important;
}}

/* Contenedores "card" DIY con bordes uniformes */
.card {{
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 16px;
  margin-bottom: 16px;
}}

.card-dark {{
  background: var(--dark-bg);
  color: var(--text-on-dark);
}}

.card-light {{
  background: var(--light-bg);
  color: #0F172A;
}}

/* Widgets: inputs, selects, textareas, file-uploader con el mismo borde */
div[data-testid="stTextInput"] input,
div[data-testid="stTextArea"] textarea,
div[data-testid="stSelectbox"] div[role="combobox"],
div[data-testid="stMultiSelect"] div[role="combobox"] {{
  border: 1px solid var(--border) !important;
  border-radius: 10px !important;
  background: #FFFFFF;
}}

div[data-testid="stFileUploader"] section {{
  border: 1px solid var(--border) !important;
  border-radius: 12px !important;
}}

/* Dataframe / AgGrid wrapper */
div[data-testid="stDataFrame"] {{
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 6px;
}}

/* Botones */
button[kind="primary"] {{
  border: 1px solid var(--border) !important;
  background: var(--accent) !important;
}}

/* Quitar el "doble borde" visual entre cards (anti-borde blanco) */
.block-container > div > div > div:has(.card) {{
  background: transparent !important;
}}
</style>
""", unsafe_allow_html=True)

# ===============
# 📚 Sidebar
# ===============
with st.sidebar:
    st.image("https://raw.githubusercontent.com/streamlit/brand/main/logos/mark/streamlit-mark.svg",
             caption="Wayki Consulting", use_container_width=True)

    st.markdown('<div class="card card-dark">', unsafe_allow_html=True)
    st.subheader("Definición del puesto")
    puesto = st.text_input("Puesto", value="Enfermero/a Asistencial")
    st.subheader("Descripción (texto libre)")
    descripcion = st.text_area("Descripción", height=120)
    st.subheader("Palabras clave (opcional)")
    keywords = st.text_area("Palabras clave (coma separadas)", value="HIS, SAP, BL, BLS, ACLS")
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="card card-dark">', unsafe_allow_html=True)
    st.subheader("Subir CVs (PDF o TXT)")
    uploads = st.file_uploader("Arrastra y suelta o examina…", type=["pdf", "txt"], accept_multiple_files=True)
    st.caption("Límite sugerido: 20MB por archivo")
    st.markdown("</div>", unsafe_allow_html=True)

# =================
# 🧱 Layout general
# =================
left, right = st.columns([2, 1])

with left:
    st.markdown('<div class="card card-dark">', unsafe_allow_html=True)
    st.title("SelektIA – Evaluation Results")

    # Tabla simple de CVs (demo)
    rows = []
    if uploads:
        for f in uploads:
            rows.append({"Name": f.name, "Score": 0, "Reasons": "0/8 keywords — Coincidencias—", "PDF_text": f.size})
    df = pd.DataFrame(rows) if rows else pd.DataFrame(
        [{"Name": "01_CV_Daniela_Rojas_Enfermera_Asistencial.pdf", "Score": 0, "Reasons": "0/8 keywords —", "PDF_text": "3147 bytes"},
         {"Name": "02_CV_Luis_Cardenas_Tecnologo_Medico_Laboratorio.pdf", "Score": 0, "Reasons": "0/8 keywords —", "PDF_text": "3070 bytes"}]
    )
    st.dataframe(df, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="card card-dark">', unsafe_allow_html=True)
    st.subheader("Visor de CV (PDF)")
    # Selector de archivo
    opciones = [r["Name"] for _, r in df.iterrows()]
    elegido = st.selectbox("Elige un candidato", opciones) if len(opciones) else None

    # ==========================
    # 👁️ Visor PDF que SÍ carga
    # ==========================
    def show_pdf(pdf_bytes: bytes, height: int = 700):
        """Muestra un PDF en un iframe (compatible con Streamlit Cloud)."""
        b64 = base64.b64encode(pdf_bytes).decode("utf-8")
        html = f'''
        <iframe
            src="data:application/pdf;base64,{b64}#view=FitH"
            width="100%" height="{height}" style="border:1px solid var(--border); border-radius:12px;"
            type="application/pdf">
        </iframe>'''
        st.components.v1.html(html, height=height, scrolling=True)

    # Localiza el archivo elegido entre los subidos
    if uploads and elegido:
        match = next((f for f in uploads if f.name == elegido), None)
        if match and match.type == "application/pdf":
            show_pdf(match.getvalue(), height=700)
        elif match and match.type == "text/plain":
            st.text(match.getvalue().decode("utf-8"))
        else:
            st.info("Sube un PDF para visualizarlo aquí.")
    else:
        st.info("Sube CVs y selecciona uno para previsualizar el PDF.")
    st.markdown("</div>", unsafe_allow_html=True)

with right:
    st.markdown('<div class="card card-light">', unsafe_allow_html=True)
    st.subheader("Acciones rápidas")
    st.write("- Ajusta **BORDER** al color que prefieras.")
    st.write("- Los titulares usan el color **ACCENT**.")
    st.write("- El box de la **derecha es claro** (card-light).")
    st.markdown("</div>", unsafe_allow_html=True)

# =========================
# 🔧 Nota de deprecaciones
# =========================
st.caption("Si ves advertencias de `use_column_width`, cámbialo por `use_container_width=True` en `st.image()`/`st.dataframe()`.")
