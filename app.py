# app.py
import io
import base64
from pathlib import Path

import streamlit as st
import pandas as pd
import plotly.express as px
from PyPDF2 import PdfReader  # Usamos PyPDF2
import google.generativeai as genai
import json

# =========================
# Variables de tema/colores
# =========================
PRIMARY_GREEN = "#00CD78"
SIDEBAR_BG = "#10172A"  # fondo columna izquierda
BOX_DARK = "#132840"  # fondo y borde de boxes del sidebar
BOX_DARK_HOV = "#193355"  # borde en hover/focus del sidebar
TEXT_LIGHT = "#FFFFFF"  # texto blanco
MAIN_BG = "#F7FBFF"  # fondo del cuerpo (claro)
BOX_LIGHT = "#F1F7FD"  # fondo claro de inputs principales
BOX_LIGHT_B = "#E3EDF6"  # borde claro de inputs principales
TITLE_DARK = "#142433"  # texto títulos principales

# ==========
#   ESTILO
# ==========
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
/* Fondo de la app (quita el blanco del contenedor) */
.block-container {{
  background: transparent !important;
}}

/* Sidebar fondo */
[data-testid="stSidebar"] {{
  background: var(--sidebar-bg) !important;
  color: var(--text) !important;
}}
/* --- TÍTULOS DEL SIDEBAR EN VERDE --- */
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3,
[data-testid="stSidebar"] h4,
[data-testid="stSidebar"] h5,
[data-testid="stSidebar"] h6,
[data-testid="stSidebar"] .stMarkdown p strong {{
  color: var(--green) !important;
}}

/* Etiquetas del sidebar y texto */
[data-testid="stSidebar"] label, 
[data-testid="stSidebar"] p, 
[data-testid="stSidebar"] span {{
  color: var(--text) !important;
}}

/* Inputs del SIDEBAR (select, input, textarea, dropzone) */
[data-testid="stSidebar"] [data-testid="stSelectbox"] > div > div,
[data-testid="stSidebar"] [data-baseweb="select"] {{
  background: var(--box) !important;
  color: var(--text) !important;
  border: 1.5px solid var(--box) !important;
  border-radius: 12px !important;
  box-shadow: none !important;
}}
[data-testid="stSidebar"] [data-testid="stTextInput"] input,
[data-testid="stSidebar"] [data-testid="stTextArea"] textarea {{
  background: var(--box) !important;
  color: var(--text) !important;
  border: 1.5px solid var(--box) !important;
  border-radius: 12px !important;
  box-shadow: none !important;
}}
[data-testid="stSidebar"] [data-testid="stTextInput"] input:hover,
[data-testid="stSidebar"] [data-testid="stTextInput"] input:focus,
[data-testid="stSidebar"] [data-testid="stTextArea"] textarea:hover,
[data-testid="stSidebar"] [data-testid="stTextArea"] textarea:focus,
[data-testid="stSidebar"] [data-testid="stSelectbox"] > div > div:hover {{
  border-color: var(--box-hover) !important;
}}
/* Dropzone */
[data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] {{
  background: var(--box) !important;
  border: 1.5px dashed var(--box) !important;
  border-radius: 14px !important;
}}
[data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] * {{
  color: var(--text) !important;
}}
/* Pills de archivos subidos */
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

# Inyectar CSS
st.markdown(f"<style>{CSS}</style>", unsafe_allow_html=True)

st.set_page_config(
    page_title="SelektIA",
    page_icon="🧠",
    layout="wide",
)

# =================================
#  CONFIGURACIÓN DE API (SECRETS)
# =================================
API_KEY = None
try:
    # Cargar la API key desde los Secrets de Streamlit
    API_KEY = st.secrets["api_key_gemini"]
    genai.configure(api_key=API_KEY)
    st.session_state.api_key_configured = True
except (FileNotFoundError, KeyError):
    st.session_state.api_key_configured = False

# =================================
#  FUNCIONES DE PROCESAMIENTO
# =================================

def extract_text_from_file(uploaded_file) -> str:
    """Extrae texto de PDF (usando PyPDF2) o TXT."""
    try:
        if Path(uploaded_file.name).suffix.lower() == ".pdf":
            # Usar PyPDF2 para leer PDF
            pdf_reader = PdfReader(io.BytesIO(uploaded_file.read()))
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() or ""
            return text
        else:
            # Leer TXT
            return uploaded_file.read().decode("utf-8", errors="ignore")
    except Exception as e:
        st.error(f"Error al leer '{uploaded_file.name}': {e}")
        return ""

def safe_gemini_call(prompt_text):
    """Llama a la API de Gemini de forma segura y maneja errores."""
    if not st.session_state.api_key_configured:
        st.error("Error: La API Key de Gemini no está configurada en los Secrets de Streamlit.")
        return None
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt_text)
        return response.text
    except Exception as e:
        st.error(f"Error al contactar la IA: {e}")
        return None

def analyze_cvs(jd, keywords, cv_files):
    """Función principal para analizar CVs y guardar en session_state."""
    st.session_state.candidates = []
    
    # Preparamos el prompt base
    prompt_base = f"""
    Eres un asistente de reclutamiento experto.
    
    **Descripción del Puesto (JD):**
    {jd}

    **Palabras Clave Esenciales:**
    {keywords}

    **Instrucción:**
    Para el siguiente CV, analiza su adecuación para el puesto. Devuelve tu análisis estrictamente en formato JSON, sin texto antes ni después.
    El JSON debe tener 3 claves:
    1. "score": Un número entero (de 0 a 100) basado en la coincidencia con el JD y las palabras clave.
    2. "pros": Un resumen en 2 o 3 puntos (bullets) de por qué el candidato es un buen fit.
    3. "cons": Un resumen en 2 o 3 puntos (bullets) de por qué el candidato podría no ser ideal (ej. falta de experiencia clave).
    
    **CV del Candidato:**
    ---
    """
    
    progress_bar = st.progress(0, "Analizando CVs...")
    
    for i, file in enumerate(cv_files):
        # Leer el contenido (texto y bytes)
        file_bytes = file.read()
        file.seek(0)  # Resetear el puntero para la extracción de texto
        cv_text = extract_text_from_file(file)
        
        if not cv_text:
            st.warning(f"No se pudo extraer texto de '{file.name}'. Omitiendo.")
            continue
            
        # Construir el prompt final
        final_prompt = prompt_base + cv_text
        
        # Llamar a la IA
        response_text = safe_gemini_call(final_prompt)
        
        if response_text:
            try:
                # Limpiar el response por si Gemini añade "```json"
                clean_response = response_text.strip().replace("```json", "").replace("```", "")
                result = json.loads(clean_response)
                
                # Guardar el resultado
                st.session_state.candidates.append({
                    "Name": file.name,
                    "Score": int(result.get("score", 0)),
                    "Pros": result.get("pros", "N/A"),
                    "Cons": result.get("cons", "N/A"),
                    "file_bytes": file_bytes,  # Guardamos los bytes para el visor
                    "is_pdf": Path(file.name).suffix.lower() == ".pdf"
                })
                
            except json.JSONDecodeError:
                st.error(f"La IA devolvió un formato incorrecto para '{file.name}'. Omitiendo.")
            except Exception as e:
                st.error(f"Error procesando '{file.name}': {e}")
                
        # Actualizar la barra de progreso
        progress_bar.progress((i + 1) / len(cv_files), f"Analizando: {file.name}")

    progress_bar.empty()
    st.success(f"¡Análisis completo! {len(st.session_state.candidates)} CVs procesados.")
    # Forzar un 'rerun' para actualizar la UI principal con los nuevos datos
    st.rerun()


# ================
#  SIDEBAR (oscuro)
# ================
with st.sidebar:
    st.image("assets/logo-wayki.png", use_column_width=True) # Logo activado
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

    st.markdown("### Palabras clave del perfil\n*(ajústalas si es necesario)*")
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

    # Botón de análisis
    if st.button("Analizar CVs", type="primary", use_container_width=True):
        if not files:
            st.error("¡Por favor, sube al menos un CV!")
        elif not st.session_state.api_key_configured:
            st.error("API Key no configurada. Añádela en los 'Secrets' de Streamlit.")
        else:
            analyze_cvs(jd_text, kw_text, files)
            
    st.divider()

    # Botón de limpiar (Esta es la línea 63, indentación corregida)
    if 'candidates' in st.session_state and st.session_state.candidates:
        if st.button("Limpiar Lista", use_container_width=True):
            st.session_state.candidates = []
            st.success("Resultados limpiados.")
            st.rerun()


# ===================
#  UI PRINCIPAL (claro)
# ===================
st.markdown(f"## <span style='color:{PRIMARY_GREEN}'>SelektIA – Evaluation Results</span>", unsafe_allow_html=True)

if not st.session_state.api_key_configured:
    st.error("🔴 **Acción Requerida:** Falta la API Key de Gemini. Por favor, añádela en los 'Secrets' de tu app en Streamlit Cloud.")
    st.markdown("1. Ve a 'Manage app' > '...' (menú) > 'Secrets'.\n2. Añade un nuevo secreto: `api_key_gemini = \"TU_API_KEY_AQUI\"`")
elif not 'candidates' in st.session_state or not st.session_state.candidates:
    st.info("Define el puesto, ajusta keywords y sube CVs. Luego presiona 'Analizar CVs' en la barra lateral.", icon="ℹ️")


# Si hay candidatos, los mostramos
if 'candidates' in st.session_state and st.session_state.candidates:
    
    # Convertir a DataFrame para mostrar y graficar
    df = pd.DataFrame(st.session_state.candidates)
    df_sorted = df.sort_values("Score", ascending=False)

    st.markdown(f"### <span style='color:{PRIMARY_GREEN}'>Ranking de Candidatos</span>", unsafe_allow_html=True)
    
    # Usar st.tabs para el ranking y el visor
    tab_ranking, tab_visor = st.tabs(["🏆 Ranking Top 5", "📄 Visor de CV"])

    with tab_ranking:
        st.write("Estos son los 5 candidatos con mayor puntuación según la IA.")
        
        # Tomar los 5 mejores
        top_5 = df_sorted.head(5).to_dict('records')
        
        for i, candidate in enumerate(top_5):
            rank = i + 1
            emoji = "🥇" if rank == 1 else "🥈" if rank == 2 else "🥉" if rank == 3 else f"**#{rank}**"
            
            with st.expander(f"{emoji} {candidate['Name']}  (Score: {candidate['Score']}/100)", expanded=(rank==1)):
                st.markdown("**✅ A favor (Pros):**")
                st.markdown(candidate['Pros'])
                st.markdown("**⚠️ A mejorar (Cons):**")
                st.markdown(candidate['Cons'])

        # Gráfico simple de todos los candidatos
        st.markdown("---")
        st.markdown("#### Comparativa General de Puntuaciones")
        fig = px.bar(
            df_sorted,
            x="Name",
            y="Score",
            title="Score Comparison (Todos los candidatos)",
            color="Score",
            color_continuous_scale=px.colors.sequential.Greens_r
        )
        fig.update_layout(
            plot_bgcolor="#FFFFFF",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color=TITLE_DARK),
            xaxis_title=None,
            yaxis_title="Score",
        )
        st.plotly_chart(fig, use_container_width=True)

    with tab_visor:
        st.markdown(f"#### <span style='color:{PRIMARY_GREEN}'>Visor de CV</span>", unsafe_allow_html=True)
        st.caption("Elige un candidato de la lista para ver su CV original.")
        
        # Selector con todos los candidatos, ordenados por nombre
        all_names = df.sort_values("Name")["Name"].tolist()
        
        selected_name = st.selectbox(
            "Selecciona un candidato:",
            all_names,
            key="pdf_candidate",
            label_visibility="collapsed",
        )

        # Visor PDF claro (embed)
        if selected_name:
            # Encontrar los datos del candidato seleccionado
            candidate_data = next(c for c in st.session_state.candidates if c['Name'] == selected_name)
            
            if candidate_data['is_pdf'] and candidate_data['file_bytes']:
                data_b64 = base64.b64encode(candidate_data['file_bytes']).decode("utf-8")
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
                st.download_button(
                    f"Descargar {selected_name}", 
                    data=candidate_data['file_bytes'], 
                    file_name=selected_name, 
                    mime="application/pdf"
                )
            else:
                # Mostrar TXT
                st.info(f"'{selected_name}' es un archivo de texto. Mostrando contenido:")
                txt_content = candidate_data['file_bytes'].decode("utf-8", errors="ignore")
                st.text_area("Contenido del TXT:", value=txt_content, height=600, disabled=True)

else:
    # Esto se muestra si st.session_state.candidates está vacío después de un análisis
    if 'candidates' in st.session_state and not st.session_state.candidates:
        st.warning("El análisis finalizó, pero no se procesó ningún candidato con éxito. Revisa los logs de la app si el error persiste.", icon="⚠️")

