# app.py — SelektIA (puesto + JD libre -> sugerir keywords -> ranking + visor PDF + Excel)
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
    # puedes añadir más…
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

def pdf_to_text(file_like) -> str:
    try:
        return extract_text(file_like)
    except Exception:
        return ""

def smart_keywords_parse(jd_text: str) -> list[str]:
    """
    Acepta coma, punto y coma, salto de línea, '/', y ' y '.
    Limpia frases de relleno típicas.
    """
    # 1) separa por coma, punto y coma o salto de línea
    parts = [x.strip() for x in re.split(r'[,\n;]+', jd_text) if x.strip()]
    # 2) divide por "/" y por ' y '
    out = []
    for p in parts:
        sub = [s.strip() for s in re.split(r'/|\\by\\b', p, flags=re.IGNORECASE) if s.strip()]
        out.extend(sub if sub else [p])
    # 3) elimina palabras de relleno
    STOP_PHRASES = ["manejo de", "manejo", "uso de", "uso", "vigente", "vigentes", "conocimiento de"]
    cleaned = []
    for k in out:
        kk = k
        for sp in STOP_PHRASES:
            kk = re.sub(rf'\\b{sp}\\b', '', kk, flags=re.I)
        kk = kk.strip(" .-/")
        if kk:
            cleaned.append(kk)
    return cleaned

def suggest_keywords_from_text(role_title: str, jd_free_text: str) -> list[str]:
    """
    Sugeridor simple: extrae acrónimos (MAYÚSCULAS), frases del diccionario
    y términos de 2-3 palabras frecuentes en el JD.
    """
    text = jd_free_text + " " + role_title
    text_norm = _norm(text)

    # 1) acrónimos tipo BLS/ACLS/LIS/HIS
    acronyms = re.findall(r'\\b[A-ZÁÉÍÓÚÑ]{2,}(?:-[A-Z]{1,})?\\b', jd_free_text)
    acronyms = [a.strip() for a in acronyms]

    # 2) términos del diccionario presentes
    dict_hits = [t for t in DOMAIN_DICTIONARY if _norm(t) in text_norm]

    # 3) bigramas/triagramas simples (muy heurístico)
    words = [w for w in re.findall(r'[a-záéíóúñ]{3,}', text_norm) if w not in {"para","con","por","del","los","las","una","uno","unos","unas","que","de","al","la","el","y","en"}]
    ngrams = []
    for n in (2,3):
        for i in range(len(words)-n+1):
            ngram = " ".join(words[i:i+n])
            if n == 2 and ngram in {"educacion paciente","bajos costos","alta calidad"}:
                pass
            ngrams.append(ngram)
    # filtrado ligero de repetidos y ruido
    candidates = acronyms + dict_hits + ngrams
    uniq = []
    seen = set()
    for c in candidates:
        key = _norm(c)
        if key not in seen and len(c) >= 3:
            uniq.append(c)
            seen.add(key)
    # limita a 25 para no saturar
    return uniq[:25]

def score_candidate(raw_text: str, jd_keywords: list) -> tuple[int, str, li]()_

