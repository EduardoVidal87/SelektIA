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
# ... (variables de color sin cambios) ...
TITLE_DARK    = "#142433"    # texto títulos principales

# ==========
#    ESTILO
# ==========
CSS = f"""
:root {{
  --green: {PRIMARY_GREEN};
# ... (CSS sin cambios) ...
#pdf_candidate, #pdf_candidate_alt {{
  background: var(--box-light) !important;
  border: 1.5px solid var(--box-light-border) !important;
  color: var(--title-dark) !important;
  border-radius: 10px !important;
}}
"""
st.markdown(f"<style>{CSS}</style>", unsafe_allow_html=True)

st.set_page_config(
# ... (config sin cambios) ...
)

# ### NUEVO ###
# Inicializar el estado de la sesión para guardar candidatos
if "applicants" not in st.session_state:
    st.session_state.applicants = []

# ================
#  SIDEBAR (oscuro)
# ================
with st.sidebar:
    # ### MODIFICADO ### - Ruta del logo corregida
    st.image("assets/logo-wayki.png", use_column_width=True)
    st.markdown("# SelektIA")
    
    # ### MODIFICADO ### - Carga la API Key desde Streamlit Secrets
    st.markdown("### Configuración de IA")
    if 'api_key_gemini' not in st.secrets:
        st.error("API Key no configurada.")
        st.caption("Ve a 'Settings > Secrets' en Streamlit Cloud y añade tu 'api_key_gemini'.")
        api_key = None
    else:
        api_key = st.secrets["api_key_gemini"]
        st.success("API Key de IA cargada.", icon="✅")


    st.markdown("### Definición del puesto")
# ... (definición del puesto sin cambios) ...
    st.markdown("### Subir CVs (PDF o TXT)")
    files = st.file_uploader(
# ... (uploader sin cambios) ...
    )

    # ### NUEVO ### - Botón de análisis y limpieza
# ... (botones sin cambios) ...
        if st.button("Limpiar Lista", use_container_width=True):
            st.session_state.applicants = []
            st.rerun()


# ===================
#  FUNCIONES DE PROCESAMIENTO (### NUEVAS ###)
# ===================

def call_gemini_api(api_key, system_prompt, user_prompt):
# ... (función sin cambios) ...
    except Exception as e:
        st.error(f"Error al llamar a la API de Gemini: {e}")
        if "API_KEY_INVALID" in str(e):
             return "Error: La API Key de Gemini no es válida. Revísala en tus Secrets."
        return f"Error al contactar la API de Gemini. Detalles: {e}"

def extract_text_from_pdf(pdf_bytes):
# ... (función sin cambios) ...

def extract_text_from_txt(txt_bytes):
# ... (función sin cambios) ...

def parse_analysis(response_text):
# ... (función sin cambios) ...
    
    return score, analysis_text

# ===================
#  LÓGICA DE PROCESAMIENTO (### MODIFICADA ###)
# ===================

if analyze_button:
    # ### MODIFICADO ### - Comprobación de API Key
    if not api_key:
        st.error("Acción detenida. API Key no configurada en Streamlit Cloud Secrets.")
    elif not jd_text:
# ... (resto de la lógica sin cambios) ...
            if new_applicants_found:
                st.rerun()
            else:
                st.toast("No se encontraron CVs nuevos para analizar.")


# ===================
#  UI PRINCIPAL (claro) (### MODIFICADO ###)
# ===================
st.markdown(f"## <span style='color:{PRIMARY_GREEN}'>SelektIA – Evaluation Results</span>", unsafe_allow_html=True)
# ... (resto de la UI sin cambios) ...
    else:
        st.info("Selecciona un candidato del ranking para ver su CV.")

# Ocultamos la tabla de datos crudos (puedes descomentarla si la quieres)
# ... (código sin cambios) ...

