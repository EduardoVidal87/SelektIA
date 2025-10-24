import io
import base64
from pathlib import Path
import re # ### NUEVO ###

import streamlit as st
import pandas as pd
import plotly.express as px
import fitz  # PyMuPDF ### NUEVO ###
import google.generativeai as genai ### NUEVO ###

# =========================
# Variables de tema/colores
# =========================
PRIMARY_GREEN = "#00CD78"
SIDEBAR_BG    = "#10172A"    # fondo columna izquierda
BOX_DARK      = "#132840"    # fondo y borde de boxes del sidebar
BOX_DARK_HOV  = "#193355"    # borde en hover/focus del sidebar
TEXT_LIGHT    = "#FFFFFF"    # texto blanco
MAIN_BG       = "#F7FBFF"    # fondo del cuerpo (claro)
BOX_LIGHT     = "#F1F7FD"    # fondo claro de inputs principales
BOX_LIGHT_B   = "#E3EDF6"    # borde claro de inputs principales
TITLE_DARK    = "#142433"    # texto títulos principales

# ==========
#    ESTILO
# ==========
# (Tu CSS original va aquí - está perfecto, no lo he cambiado)
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
/* ... (Todo tu CSS va aquí - lo he omitido por brevedad pero está en el archivo) ... */
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
.stButton > button:hover {{
  filter: brightness(0.95);
}}

/* Títulos del cuerpo */
h1, h2, h3 {{
  color: var(--title-dark);
}}
h1 strong, h2 strong, h3 strong {{
  color: var(--green);
}}

/* Controles del área principal (claros) */
.block-container [data-testid="stSelectbox"] > div > div,
.block-container [data-baseweb="select"],
.block-container [data-testid="stTextInput"] input,
.block-container [data-testid="stTextArea"] textarea {{
  background: var(--box-light) !important;
  color: var(--title-dark) !important;
  border: 1.5px solid var(--box-light-border) !important;
  border-radius: 10px !important;
}}

/* Tabla clara (dataframe/simple table) */
.block-container table {{
  background: #fff !important;
  border: 1px solid var(--box-light-border) !important;
  border-radius: 8px !important;
}}
.block-container thead th {{
  background: var(--box-light) !important;
  color: var(--title-dark) !important;
}}

/* Expander claro */
[data-testid="stExpander"] {{
  background: #fff !important;
  border: 1px solid var(--box-light-border) !important;
  border-radius: 12px !important;
}}
[data-testid="stExpander"] [data-testid="stExpanderHeader"] p {{
  color: var(--title-dark) !important;
}}

/* Selector del visor de PDF en claro */
#pdf_candidate, #pdf_candidate_alt {{
  background: var(--box-light) !important;
  border: 1.5px solid var(--box-light-border) !important;
  color: var(--title-dark) !important;
  border-radius: 10px !important;
}}
"""
st.markdown(f"<style>{CSS}</style>", unsafe_allow_html=True)

st.set_page_config(
    page_title="SelektIA",
    page_icon="🧠",
    layout="wide",
)

# ### NUEVO ###
# Inicializar el estado de la sesión para guardar candidatos
if "applicants" not in st.session_state:
    st.session_state.applicants = []

# ================
#  SIDEBAR (oscuro)
# ================
with st.sidebar:
    # st.image("logo-wayki.png", use_column_width=True) # Descomenta si tienes el logo
    st.markdown("# SelektIA")
    
    # ### NUEVO ### - Input para la API Key
    st.markdown("### Configuración de IA")
    api_key = st.text_input(
        "Ingresa tu API Key de Gemini", 
        type="password",
        key="api_key_gemini"
    )

    st.markdown("### Definición del puesto")
    puesto = st.selectbox(
        "Puesto",
        [
            "Enfermera/o Asistencial",
            "Tecnólogo Médico",
            "Recepcionista de Admisión",
            "Médico General",
            "Químico Farmacéutico",
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

    st.markdown("### Palabras clave del perfil\n*(IA las usará como guía)*")
    kw_text = st.text_area(
        "HIS, SAP IS-H, BLS, ACLS, IAAS, educación al paciente, seguridad, protocolos…",
        value="HIS, SAP IS-H, BLS, ACLS, IAAS, educación al paciente, seguridad del paciente, protocolos",
        height=110,
        key="kw",
        label_visibility="collapsed",
    )

    st.markdown("### Subir CVs (PDF o TXT)")
    files = st.file_uploader(
        "Drag and drop files here",
        type=["pdf", "txt"],
        accept_multiple_files=True,
        label_visibility="collapsed",
    )

    # ### NUEVO ### - Botón de análisis y limpieza
    col_btn_1, col_btn_2 = st.columns(2)
    with col_btn_1:
        analyze_button = st.button("Analizar CVs", type="primary", use_container_width=True)
    with col_btn_2:
        if st.button("Limpiar Lista", use_container_width=True):
            st.session_state.applicants = []
            st.rerun()


# ===================
#  FUNCIONES DE PROCESAMIENTO (### NUEVAS ###)
# ===================

def call_gemini_api(api_key, system_prompt, user_prompt):
    """Llama a la API de Gemini usando la biblioteca oficial de Python."""
    try:
        genai.configure(api_key=api_key)
        generation_config = {"temperature": 0.2, "top_p": 1, "top_k": 1, "max_output_tokens": 4096}
        safety_settings = [
          {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
          {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
          {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
          {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        ]
        model = genai.GenerativeModel(model_name="gemini-1.5-flash-latest",
                                      generation_config=generation_config,
                                      system_instruction=system_prompt,
                                      safety_settings=safety_settings)
        response = model.generate_content(user_prompt)
        return response.text
    except Exception as e:
        st.error(f"Error al llamar a la API de Gemini: {e}")
        if "API_KEY_INVALID" in str(e):
             return "Error: La API Key de Gemini no es válida. Por favor, revísala."
        return f"Error al contactar la API de Gemini. Detalles: {e}"

def extract_text_from_pdf(pdf_bytes):
    """Extracts text from PDF bytes using PyMuPDF (fitz)."""
    try:
        pdf_doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        text = ""
        for page in pdf_doc:
            text += page.get_text()
        pdf_doc.close()
        return text
    except Exception as e:
        st.error(f"Error al leer el PDF: {e}")
        return ""

def extract_text_from_txt(txt_bytes):
    """Extracts text from TXT bytes."""
    try:
        return txt_bytes.decode("utf-8", errors="ignore")
    except Exception as e:
        st.error(f"Error al leer el archivo TXT: {e}")
        return ""

def parse_analysis(response_text):
    """
    Extrae la puntuación y el texto del análisis de la respuesta de la IA.
    Espera una línea como 'Puntuación: 85/100' al inicio.
    """
    score = 0
    analysis_text = response_text
    match = re.search(r"Puntuación:\s*(\d+)/100", response_text)
    
    if match:
        try:
            score = int(match.group(1))
            analysis_text = re.sub(r"Puntuación:\s*(\d+)/100\n*", "", response_text).strip()
        except Exception:
            score = 0
            analysis_text = response_text
    
    return score, analysis_text

# ===================
#  LÓGICA DE PROCESAMIENTO (### MODIFICADA ###)
# ===================

if analyze_button:
    if not api_key:
        st.error("Por favor, ingresa tu API Key de Gemini en la barra lateral.")
    elif not jd_text:
        st.error("Por favor, ingresa una descripción del puesto.")
    elif not files:
        st.error("Por favor, sube al menos un CV.")
    else:
        with st.spinner(f"Analizando {len(files)} CVs con IA..."):
            new_applicants_found = False
            
            # Prepara el prompt del sistema UNA SOLA VEZ
            system_prompt = f"""
            Eres un asistente de reclutamiento de IA. Tu tarea es analizar un currículum contra una descripción de trabajo.
            El puesto es: {puesto}.
            La descripción del puesto es: {jd_text}.
            Las palabras clave importantes son: {kw_text}.

            Tu respuesta DEBE estar en dos partes:
            1.  **Puntuación:** En la PRIMERA LÍNEA, da una puntuación numérica de 0 a 100. La línea debe ser EXACTAMENTE: `Puntuación: [score]/100`.
            2.  **Análisis:** Después de la puntuación, proporciona un análisis en Markdown que incluya:
                * **Coincidencia con el Puesto:** Qué tan bien coinciden sus habilidades con el puesto.
                * **Fortalezas Clave:** 2-3 puntos destacando lo más relevante.
                * **Posibles Debilidades:** 2-3 puntos sobre áreas donde no cumple con los requisitos.
                * **Veredicto:** Una recomendación breve (Fuerte coincidencia, Coincidencia moderada, etc.).
            """

            for f in files:
                # Evitar re-analizar
                if f.name not in [app["Name"] for app in st.session_state.applicants]:
                    new_applicants_found = True
                    raw = f.read()
                    f.seek(0)
                    ext = Path(f.name).suffix.lower()
                    
                    resume_text = ""
                    if ext == ".txt":
                        resume_text = extract_text_from_txt(raw)
                    elif ext == ".pdf":
                        resume_text = extract_text_from_pdf(raw)

                    if resume_text:
                        # Prepara el prompt del usuario
                        user_prompt = f"""
                        Por favor, analiza el siguiente currículum:

                        --- CURRÍCULUM ({f.name}) ---
                        {resume_text}
                        """
                        
                        # Llama a la IA
                        response_text = call_gemini_api(api_key, system_prompt, user_prompt)
                        
                        # Parsea la respuesta
                        score, analysis_text = parse_analysis(response_text)
                        
                        # Guarda en el estado de la sesión
                        st.session_state.applicants.append({
                            "Name": f.name,
                            "Score": score,
                            "Reasons": analysis_text, # Ahora 'Reasons' es el análisis completo
                            "CV_Text": resume_text,
                            "is_pdf": (ext == ".pdf"),
                            "raw_bytes": raw # Guardamos los bytes para el visor
                        })
                    else:
                        st.error(f"No se pudo leer el texto de {f.name}.")
            
            if new_applicants_found:
                st.rerun()
            else:
                st.toast("No se encontraron CVs nuevos para analizar.")


# ===================
#  UI PRINCIPAL (claro) (### MODIFICADO ###)
# ===================
st.markdown(f"## <span style='color:{PRIMARY_GREEN}'>SelektIA – Evaluation Results</span>", unsafe_allow_html=True)

# Construimos el DataFrame desde el estado de la sesión
df = pd.DataFrame(st.session_state.applicants) if st.session_state.applicants else pd.DataFrame(columns=["Name", "Score", "Reasons", "is_pdf", "raw_bytes"])

# Ordenar por Score
if not df.empty:
    df = df.sort_values("Score", ascending=False)

# Mostrar Info o Warning
if df.empty:
    st.warning("Sube algunos CVs (PDF o TXT) y haz clic en 'Analizar CVs' para ver resultados.", icon="📄")
else:
    st.info(f"Mostrando {len(df)} candidatos analizados. Elige uno del ranking para ver su CV y el análisis de la IA.", icon="ℹ️")

# Dividimos la UI principal
col_rank, col_visor = st.columns([1, 1], gap="large")

with col_rank:
    st.markdown(f"### <span style='color:{PRIMARY_GREEN}'>Ranking de Candidatos</span>", unsafe_allow_html=True)
    
    if not df.empty:
        # Usamos st.radio para crear un ranking seleccionable
        # Formateamos las opciones para mostrar Puntuación y Nombre
        df["display_name"] = df.apply(lambda row: f"**{row['Score']}/100** – {row['Name']}", axis=1)
        
        selected_name = st.radio(
            "Ranking (Top 5)",
            df.head(5)["display_name"].tolist(),
            key="ranking_selector",
            label_visibility="collapsed"
        )
        
        if selected_name:
            # Encontrar el nombre de archivo real
            selected_file_name = selected_name.split(" – ")[-1]
            # Obtener la fila completa de datos de ese candidato
            selected_row = df[df["Name"] == selected_file_name].iloc[0]
            
            # Gráfico (lo movemos aquí para que esté junto al ranking)
            fig = px.bar(
                df.head(10).sort_values("Score", ascending=True), # Top 10, ascendente para gráfico
                y="Name",
                x="Score",
                orientation='h', # Gráfico horizontal
                text="Score" # Mostrar puntuación en la barra
            )
            fig.update_layout(
                plot_bgcolor="#FFFFFF",
                paper_bgcolor="rgba(0,0,0,0)",
                font=dict(color=TITLE_DARK),
                xaxis_title="Puntuación (Score)",
                yaxis_title=None,
                height=300,
                margin=dict(l=0, r=0, t=0, b=0)
            )
            st.plotly_chart(fig, use_container_width=True)

            # Mostrar el análisis de la IA
            st.markdown("---")
            st.markdown(f"#### Análisis de IA para: **{selected_file_name}**")
            st.markdown(selected_row["Reasons"], unsafe_allow_html=True) # El análisis de la IA

    else:
        st.info("El ranking aparecerá aquí.")

with col_visor:
    st.markdown(f"### <span style='color:{PRIMARY_GREEN}'>Visor de CV</span>", unsafe_allow_html=True)
    
    if 'selected_row' in locals():
        # Lógica del visor (tu código original, ¡funcionaba perfecto!)
        if bool(selected_row["is_pdf"]):
            data_b64 = base64.b64encode(selected_row["raw_bytes"]).decode("utf-8")
            st.markdown(
                f"""
                <div style="border:1px solid {BOX_LIGHT_B}; border-radius:12px; overflow:hidden; background:#fff;">
                  <iframe src="data:application/pdf;base64,{data_b64}"  
                          style="width:100%; height:750px; border:0;"
                          title="PDF Viewer"></iframe>
                </div>
                """,
                unsafe_allow_html=True,
            )
            st.download_button("Descargar PDF", data=selected_row["raw_bytes"], file_name=selected_row["Name"], mime="application/pdf")
        else:
            # Mostrar el CV en texto si es .txt
            st.text_area(
                "Contenido del CV (archivo .txt)", 
                selected_row["CV_Text"], 
                height=750,
                disabled=True
            )
    else:
        st.info("Selecciona un candidato del ranking para ver su CV.")

# Ocultamos la tabla de datos crudos (puedes descomentarla si la quieres)
# if not df.empty:
#     st.markdown("---")
#     st.markdown("### Datos Crudos (para depuración)")
#     st.dataframe(
#         df[["Name", "Score"]],
#         use_container_width=True,
#         hide_index=True,
#     )
