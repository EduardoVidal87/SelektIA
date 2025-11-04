# -*- coding: utf-8 -*-
# =============================================================================
# SelektIA - app.py  (versión compacta, monolítica)
# Mantiene look & feel existente (#00CD78 primario) y agrega visor PDF + voicebot.
# =============================================================================

import io, base64, re, json, zipfile, uuid, os
from pathlib import Path
from datetime import datetime, timedelta

import streamlit as st
import pandas as pd
from PyPDF2 import PdfReader

# =============================================================================
# Config & estilo
# =============================================================================

APP_TITLE = "SelektIA"
PRIMARY = "#00CD78"
DARK_SIDEBAR = "#0E192B"
STORE_PATH = Path("/mnt/data/selektia_store.json")  # Persistencia ligera

st.set_page_config(page_title=APP_TITLE, page_icon="🧠", layout="wide")

CUSTOM_CSS = f"""
<style>
/* Fuente y colores mínimos respetando look & feel */
:root {{
  --primary: {PRIMARY};
}}
.stApp [data-testid="stHeader"] {{ background: white; }}
.sidebar .sidebar-content, section[data-testid="stSidebar"] {{
  background: {DARK_SIDEBAR} !important;
}}
.sidebar .sidebar-content * {{ color: #E7EEF6 !important; }}
a, .st-emotion-cache-10trblm p a {{ color: var(--primary) !important; }}
.stProgress > div > div > div {{
  background: var(--primary) !important;
}}
/* Badges */
.badge {{
  display: inline-block; padding: 2px 10px; border-radius: 999px;
  font-size: 12px; border: 1px solid #e6e9ef; color: #4e5a6b; background: #f6f8fb;
}}
.badge-primary {{
  color: white; background: var(--primary); border-color: var(--primary);
}}
.card {{
  border: 1px solid #eef1f6; border-radius: 14px; padding: 16px; background: #fff;
}}
.kpi {{
  font-size: 40px; font-weight: 700; margin-bottom: -8px; color: #1d2433;
}}
.kpi-sub {{
  color: #6b778c; font-size: 12px; text-transform: uppercase;
}}
.small-muted {{ color: #7a869a; font-size: 12px; }}
.btn-primary button {{ background: var(--primary) !important; }}
hr {{ border: none; border-top: 1px solid #edf0f5; }}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# =============================================================================
# Persistencia
# =============================================================================

def _empty_store():
    return {
        "jobs": [],
        "candidates": [],
        "tasks": [],
        "interviews": []
    }

def load_store() -> dict:
    if STORE_PATH.exists():
        try:
            return json.loads(STORE_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return _empty_store()

def save_store(store: dict):
    try:
        STORE_PATH.write_text(json.dumps(store, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        st.warning(f"No se pudo guardar la data: {e}")

if "store" not in st.session_state:
    st.session_state.store = load_store()

store = st.session_state.store

# =============================================================================
# Utilidades
# =============================================================================

def safe_id(prefix: str = "id"):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

def extract_docx_text(file_bytes: bytes) -> str:
    try:
        with zipfile.ZipFile(io.BytesIO(file_bytes)) as z:
            xml = z.read("word/document.xml").decode("utf-8", "ignore")
        txt = re.sub(r"<(.|\n)*?>", " ", xml)
        return re.sub(r"\s+", " ", txt).strip()
    except Exception:
        return ""

def extract_pdf_text(file_bytes: bytes) -> str:
    try:
        reader = PdfReader(io.BytesIO(file_bytes))
        out = []
        for page in reader.pages:
            out.append(page.extract_text() or "")
        return " ".join(out)
    except Exception:
        return ""

def extract_text_from_upload(uploaded_file) -> tuple[str, bytes]:
    """Devuelve (texto, bytes). Soporta .pdf y .docx; otros: devuelve bytes y texto vacío."""
    suffix = Path(uploaded_file.name).suffix.lower()
    file_bytes = uploaded_file.read(); uploaded_file.seek(0)
    if suffix == ".pdf":
        return extract_pdf_text(file_bytes), file_bytes
    if suffix == ".docx":
        return extract_docx_text(file_bytes), file_bytes
    # Otros
    return "", file_bytes

def guess_years_experience(text: str) -> int:
    # Heurística simple: busca "X años" o "X year(s)"
    m = re.search(r"(\d+)\s*(?:años|year)", text, re.IGNORECASE)
    if m:
        try:
            return min(30, max(0, int(m.group(1))))
        except Exception:
            pass
    # fallback: heurística por cantidad de roles detectados
    roles = len(re.findall(r"(analista|asistente|ingenier|coordinador|jefe|manager)", text, re.I))
    return min(10, roles // 2)

def guess_english_level(text: str) -> str:
    # Heurística: presencia de secciones/keywords en inglés
    score = 0
    for kw in ["skills", "summary", "projects", "experience", "certifications", "responsibilities"]:
        if re.search(rf"\b{kw}\b", text, re.I):
            score += 1
    if score >= 5: return "Advanced"
    if score >= 3: return "Intermediate"
    return "Beginner"

def compute_fit_score(text: str, jd_text: str) -> tuple[int, list[str]]:
    """Score 0-100 y lista de 'habilidades clave' detectadas respecto al JD."""
    # extrae keywords del JD (muy simple)
    kws = [k.strip().lower() for k in re.split(r"[,\n;/]", jd_text) if 2 <= len(k.strip()) <= 40]
    kws = [k for k in kws if len(k.split()) <= 5][:30]
    found = []
    hits = 0
    for kw in kws:
        if not kw: continue
        if re.search(re.escape(kw), text, re.I):
            hits += 1
            found.append(kw)
    coverage = int((hits / max(1, len(kws))) * 100)
    # refino con señales básicas
    years = guess_years_experience(text)
    weight = min(100, coverage + years*4)
    return weight, list(dict.fromkeys(found))[:12]

def pdf_viewer_embed(file_bytes: bytes, height: int = 520, key: str = "pdf_viewer"):
    """
    Renderiza PDF inline con data URI para evitar bloqueos por CSP/origen cruzado.
    Si el navegador no embebe, no rompe la app (no exceptions).
    """
    try:
        b64 = base64.b64encode(file_bytes).decode("utf-8")
        src = f"data:application/pdf;base64,{b64}"
        html = f'''
        <div style="border:1px solid #eef1f6;border-radius:12px;overflow:hidden">
            <object data="{src}" type="application/pdf" width="100%" height="{height}">
                <embed src="{src}" type="application/pdf" width="100%" height="{height}" />
            </object>
        </div>
        '''
        st.components.v1.html(html, height=height+8, scrolling=False)
    except Exception:
        st.info("El visor embebido no está disponible en este navegador. Usa el botón de descarga.")

# =============================================================================
# Voicebot (entrevista IA) - lógica y UI
# =============================================================================

VOICEBOT_DEFAULT_RUBRIC = {
    "experiencia": {
        "pregunta": "Experiencia previa relevante (estación de servicio / atención al cliente).",
        "peso": 0.35
    },
    "servicio": {
        "pregunta": "Servicio al cliente: manejo de clientes difíciles, amabilidad, comunicación.",
        "peso": 0.25
    },
    "orden_puntualidad": {
        "pregunta": "Presentación personal, orden/limpieza y puntualidad.",
        "peso": 0.20
    },
    "comercial": {
        "pregunta": "Comodidad para ofrecer promociones o productos complementarios.",
        "peso": 0.20
    }
}

def analyse_transcript(transcript: str, rubric: dict = None) -> dict:
    """Analiza texto de entrevista y devuelve un dict con sub-scores y veredicto."""
    rubric = rubric or VOICEBOT_DEFAULT_RUBRIC
    t = transcript.lower()

    def score_for(keywords: list[str]) -> float:
        if not keywords: return 0.0
        s = 0
        for k in keywords:
            if re.search(re.escape(k), t, re.I): s += 1
        return min(1.0, s / len(keywords))

    # señales por criterio (ajusta/expande si quieres)
    s_experiencia   = score_for(["caja", "atención", "estación", "cliente", "gasolina", "turno", "stock"])
    s_servicio      = score_for(["amable", "disculpa", "solución", "espera", "calmar", "trato", "rápido"])
    s_orden         = score_for(["puntual", "presentación", "orden", "limpieza", "prolijo"])
    s_comercial     = score_for(["promoción", "ofrecer", "complementario", "venta", "sugerir"])

    subs = {
        "experiencia": round(s_experiencia * 100),
        "servicio": round(s_servicio * 100),
        "orden_puntualidad": round(s_orden * 100),
        "comercial": round(s_comercial * 100),
    }

    total = 0
    for k, cfg in VOICEBOT_DEFAULT_RUBRIC.items():
        total += subs[k] * cfg["peso"]
    total = int(round(total))

    feedback = []
    if subs["experiencia"] < 60:      feedback.append("Profundizar ejemplos concretos de experiencia y tareas específicas.")
    if subs["servicio"] < 60:         feedback.append("Describir pasos ante clientes molestos y cómo cerrar positivamente.")
    if subs["orden_puntualidad"] < 60:feedback.append("Resaltar hábitos de puntualidad y orden en pista.")
    if subs["comercial"] < 60:        feedback.append("Explicar cómo ofrecerías promociones sin incomodar al cliente.")

    verdict = "Aprobar" if total >= 70 else ("Mantener en reserva" if total >= 55 else "Descartar")
    return {
        "subscores": subs,
        "score": total,
        "verdict": verdict,
        "feedback": feedback
    }

def new_interview_task(store: dict, candidate_id: str, job_id: str, when: datetime):
    interview_id = safe_id("interview")
    store["interviews"].append({
        "id": interview_id,
        "candidate_id": candidate_id,
        "job_id": job_id,
        "scheduled_for": when.isoformat(),
        "transcript": "",
        "result": None,       # dict de analyse_transcript(...)
        "decision": "pendiente",  # pendiente/aprobado/descartado
        "created_at": datetime.utcnow().isoformat()
    })
    save_store(store)
    return interview_id

def ui_voicebot_block(candidate: dict, job: dict, store: dict):
    st.subheader("🎙️ Entrevista IA (Voicebot)")
    c1, c2 = st.columns([1,1])

    with c1:
        st.caption("Programación")
        with st.form(f"schedule_voicebot_{candidate['id']}"):
            date_ = st.date_input("Fecha", value=datetime.utcnow().date())
            time_ = st.time_input("Hora", value=(datetime.utcnow()+timedelta(minutes=15)).time())
            submitted = st.form_submit_button("Programar entrevista IA")
            if submitted:
                when = datetime.combine(date_, time_)
                new_interview_task(store, candidate["id"], job.get("id","-"), when)
                st.success(f"Entrevista programada para {when.strftime('%Y-%m-%d %H:%M')}")

    with c2:
        st.caption("Analizar llamada")
        txt = st.text_area("Pegar transcripción", height=160, key=f"tr_{candidate['id']}")
        up = st.file_uploader("o subir .txt", type=["txt"], key=f"fu_{candidate['id']}")
        if up:
            try:
                txt = up.read().decode("utf-8", "ignore")
            except Exception:
                st.warning("No se pudo leer el archivo. Usa UTF-8.")
        if st.button("Analizar transcripción", type="primary", use_container_width=True):
            if not txt.strip():
                st.warning("Pega la transcripción o sube un .txt.")
            else:
                result = analyse_transcript(txt)
                # crea registro y guarda
                interview_id = new_interview_task(store, candidate["id"], job.get("id","-"), datetime.utcnow())
                # sobreescribe con transcripción y resultado
                for it in store["interviews"]:
                    if it["id"] == interview_id:
                        it["transcript"] = txt
                        it["result"] = result
                        break
                save_store(store)
                st.session_state[f"voicebot_result_{candidate['id']}"] = result
                st.success("Entrevista analizada.")

    # Render de resultado si existe en sesión
    result = st.session_state.get(f"voicebot_result_{candidate['id']}")
    if result:
        st.markdown("### ✅ Resultado Voicebot")
        colA, colB, colC, colD, colE = st.columns(5)
        colA.metric("Score total", f"{result['score']}%")
        colB.metric("Experiencia", f"{result['subscores']['experiencia']}%")
        colC.metric("Servicio", f"{result['subscores']['servicio']}%")
        colD.metric("Orden/Puntualidad", f"{result['subscores']['orden_puntualidad']}%")
        colE.metric("Comercial", f"{result['subscores']['comercial']}%")

        if result["feedback"]:
            with st.expander("Sugerencias de mejora"):
                for fb in result["feedback"]:
                    st.write(f"- {fb}")

        d1, d2, d3 = st.columns([1,1,4])
        if d1.button("Aprobar", key=f"ap_{candidate['id']}"):
            # última entrevista del candidato: marca decisión
            for it in reversed(store["interviews"]):
                if it["candidate_id"] == candidate["id"] and it["result"]:
                    it["decision"] = "aprobado"
                    save_store(store)
                    break
            st.success("Candidato aprobado. Flujo finalizado en entrevista IA.")
        if d2.button("Descartar", key=f"de_{candidate['id']}"):
            for it in reversed(store["interviews"]):
                if it["candidate_id"] == candidate["id"] and it["result"]:
                    it["decision"] = "descartado"
                    save_store(store)
                    break
            st.warning("Candidato descartado. Flujo finalizado en entrevista IA.")
        d3.markdown(f"<span class='badge'>Veredicto: <b>{result['verdict']}</b></span>", unsafe_allow_html=True)

# =============================================================================
# Carga de candidatos + evaluación
# =============================================================================

def add_candidate_ui():
    st.subheader("Cargar candidato")
    with st.form("add_cand"):
        name = st.text_input("Nombre completo")
        recent_role = st.text_input("Puesto reciente")
        jd = st.text_area("Job Description (JD) / texto de referencia", help="Se usa para evaluar match.")
        cv = st.file_uploader("CV del candidato (.pdf o .docx)", type=["pdf","docx"])
        submitted = st.form_submit_button("Evaluar y guardar", use_container_width=True)
        if submitted:
            if not (name and cv and jd):
                st.warning("Completa nombre, JD y sube el CV.")
                return
            text, file_bytes = extract_text_from_upload(cv)
            score, skills_found = compute_fit_score(text, jd)
            cand_id = safe_id("cand")
            # “años exp.” y “inglés” heurísticos
            years = guess_years_experience(text)
            english = guess_english_level(text)
            store["candidates"].append({
                "id": cand_id,
                "name": name,
                "recent_position": recent_role or "",
                "skills": skills_found,
                "notes": "",
                "score": score,
                "years_exp": years,
                "english": english,
                "cv_bytes_b64": base64.b64encode(file_bytes).decode("utf-8"),
                "cv_name": cv.name,
                "jd_text": jd,
                "created_at": datetime.utcnow().isoformat()
            })
            # crea tarea
            task_id = safe_id("task")
            store["tasks"].append({
                "id": task_id,
                "candidate_id": cand_id,
                "job_id": safe_id("job"),
                "status": "pendiente",
                "priority": "media",
                "due_date": (datetime.utcnow()+timedelta(days=7)).date().isoformat(),
                "assigned_to": "Admin",
                "created_at": datetime.utcnow().isoformat()
            })
            save_store(store)
            st.success("Candidato evaluado y guardado.")
            st.experimental_rerun()

def list_tasks_ui():
    st.subheader("Tareas")
    if not store["tasks"]:
        st.info("No hay tareas.")
        return
    df = []
    for t in store["tasks"]:
        c = next((x for x in store["candidates"] if x["id"] == t["candidate_id"]), None)
        df.append({
            "Tarea": t["id"],
            "Candidato": c["name"] if c else "-",
            "Score": c["score"] if c else "-",
            "Estado": t["status"],
            "Prioridad": t["priority"],
            "Vence": t["due_date"]
        })
    st.dataframe(pd.DataFrame(df), use_container_width=True)

def task_detail_ui(task_id: str):
    t = next((x for x in store["tasks"] if x["id"] == task_id), None)
    if not t:
        st.error("Tarea no encontrada.")
        return
    c = next((x for x in store["candidates"] if x["id"] == t["candidate_id"]), None)
    if not c:
        st.error("Candidato no encontrado.")
        return

    # Header (similar al layout de tu captura)
    st.markdown("### Detalle de Tarea")
    st.caption(f"CV {c['name']}")
    k1, k2, k3, k4 = st.columns([1,1,1,1])
    with k1:
        st.markdown("<div class='kpi'>"+f"{c['score']}%"+"</div>", unsafe_allow_html=True)
        st.markdown("<div class='kpi-sub'>Score (Fit)</div>", unsafe_allow_html=True)
    with k2:
        st.markdown("<div class='kpi'>"+f"{c['years_exp']}"+"</div>", unsafe_allow_html=True)
        st.markdown("<div class='kpi-sub'>Años Exp.</div>", unsafe_allow_html=True)
    with k3:
        st.markdown("<div class='kpi'>"+f"{c['english']}"+"</div>", unsafe_allow_html=True)
        st.markdown("<div class='kpi-sub'>Nivel Inglés</div>", unsafe_allow_html=True)
    with k4:
        st.markdown(f"<span class='badge'>Puesto Reciente:&nbsp;<b>{c['recent_position'] or '-'}</b></span>", unsafe_allow_html=True)

    if c["skills"]:
        st.markdown("**Habilidades Clave:** " + ", ".join(c["skills"]))
    if c["notes"]:
        st.markdown("**Notas IA:** " + c["notes"])

    st.markdown("#### Visualizar CV (PDF)")
    # Descargar
    file_bytes = base64.b64decode(c["cv_bytes_b64"])
    st.download_button("⬇️ Descargar CV (PDF)", data=file_bytes, file_name=c["cv_name"], mime="application/pdf", use_container_width=True)
    # Visor embebido
    pdf_viewer_embed(file_bytes, height=520)

    with st.expander("Ver Job Description (JD) usado"):
        st.code(c["jd_text"] or "", language="markdown")

    # Voicebot aquí
    ui_voicebot_block(c, {"id": t.get("job_id","-")}, store)

    st.markdown("### Información Principal")
    col1, col2, col3, col4 = st.columns(4)
    col1.markdown("**Asignado a:**  \nAdmin")
    col2.markdown(f"**Vencimiento:**  \n{t['due_date']}")
    col3.markdown(f"**Estado:**  \n{t['status'].capitalize()}")
    col4.markdown(f"**Prioridad:**  \n{t['priority'].capitalize()}")

# =============================================================================
# Navegación
# =============================================================================

def sidebar_nav():
    st.sidebar.image("https://raw.githubusercontent.com/waykiconsulting/assets/main/selektia_logo_green.png", use_column_width=True)
    st.sidebar.markdown("---")
    choice = st.sidebar.selectbox("Menú", [
        "Dashboard",
        "Proceso de Selección: Evaluación de CVs",
        "Tareas (lista)",
        "Abrir tarea por ID"
    ])
    return choice

# =============================================================================
# Seeds (opcional)
# =============================================================================

def _seed_example_if_empty():
    if store["candidates"]: return
    # JD y PDF demo
    demo_jd = """Resumen del puesto:
- Brindar soporte administrativo integral (documentación, coordinación con proveedores, control de caja chica).
- Excel intermedio/avanzado, Word, PowerPoint.
- Atención al cliente, logística ligera, reportes y trabajo en equipo.
Requisitos:
- Puntualidad y excelente presentación personal.
- Deseable experiencia en estaciones de servicio o retail.
"""
    # PDF 'vacío' (un solo texto) para que el visor funcione sin archivos externos
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    c.setFont("Helvetica", 12)
    c.drawString(72, 800, "CV Demo - SelektIA")
    c.drawString(72, 780, "Experiencia: Cajero y atención al cliente (3 años).")
    c.drawString(72, 760, "Habilidades: Excel, Word, puntualidad, presentacion personal, orden y limpieza.")
    c.save()
    pdf_bytes = buf.getvalue()

    cand_id = safe_id("cand")
    store["candidates"].append({
        "id": cand_id,
        "name": "Luis Alberto",
        "recent_position": "Asistente Administrativo",
        "skills": ["excel", "word", "atención al cliente", "puntualidad"],
        "notes": "Candidato con experiencia directa en caja y trato al cliente.",
        "score": 75,
        "years_exp": 3,
        "english": "Intermediate",
        "cv_bytes_b64": base64.b64encode(pdf_bytes).decode("utf-8"),
        "cv_name": "cv_luis_alberto.pdf",
        "jd_text": demo_jd,
        "created_at": datetime.utcnow().isoformat()
    })
    store["tasks"].append({
        "id": safe_id("task"),
        "candidate_id": cand_id,
        "job_id": safe_id("job"),
        "status": "pendiente",
        "priority": "media",
        "due_date": (datetime.utcnow()+timedelta(days=5)).date().isoformat(),
        "assigned_to": "Admin",
        "created_at": datetime.utcnow().isoformat()
    })
    save_store(store)

# =============================================================================
# App
# =============================================================================

def main():
    _seed_example_if_empty()
    choice = sidebar_nav()

    st.title("SelektIA")
    st.caption("Powered by Wayki Consulting")

    if choice == "Dashboard":
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Candidatos", len(store["candidates"]))
        c2.metric("Tareas", len(store["tasks"]))
        c3.metric("Entrevistas IA", len(store["interviews"]))
        aprob = sum(1 for it in store["interviews"] if it.get("decision")=="aprobado")
        c4.metric("Aprobados por Voicebot", aprob)
        st.markdown("—")
        st.markdown("### Últimas tareas")
        list_tasks_ui()

    elif choice == "Proceso de Selección: Evaluación de CVs":
        add_candidate_ui()
        st.markdown("---")
        st.subheader("Candidatos cargados")
        if store["candidates"]:
            df = pd.DataFrame([{
                "ID": c["id"], "Nombre": c["name"], "Score": c["score"],
                "Años Exp.": c["years_exp"], "Inglés": c["english"]
            } for c in store["candidates"]])
            st.dataframe(df, use_container_width=True)
        else:
            st.info("Aún no hay candidatos cargados.")

    elif choice == "Tareas (lista)":
        list_tasks_ui()

    elif choice == "Abrir tarea por ID":
        task_id = st.text_input("ID de tarea")
        if st.button("Abrir"):
            if not task_id:
                st.warning("Coloca un ID.")
            else:
                task_detail_ui(task_id)

    # Guardar en cada render
    save_store(store)

if __name__ == "__main__":
    main()
