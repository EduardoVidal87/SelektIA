# app.py
# -*- coding: utf-8 -*-

import io, base64, re, json, random, zipfile, uuid
from pathlib import Path
from datetime import datetime, date, timedelta

import streamlit as st
import pandas as pd
import plotly.express as px
from PyPDF2 import PdfReader

# =========================================================
# PALETA / CONST
# =========================================================
PRIMARY       = "#00CD78"
SIDEBAR_BG = "#0E192B"
SIDEBAR_TX = "#B9C7DF"
BODY_BG     = "#F7FBFF"
CARD_BG     = "#0E192B"
TITLE_DARK = "#142433"

BAR_DEFAULT = "#E9F3FF"
BAR_GOOD    = "#33FFAC"

JOB_BOARDS  = ["laborum.pe","Computrabajo","Bumeran","Indeed","LinkedIn Jobs"]
PIPELINE_STAGES = ["Recibido", "Screening RRHH", "Entrevista Telefónica", "Entrevista Gerencia", "Oferta", "Contratado", "Descartado"]
TASK_PRIORITIES = ["Alta", "Media", "Baja"]
TASK_STATUSES = ["Pendiente", "En Proceso", "Completada", "En Espera"]

EVAL_INSTRUCTION = (
  "Debes analizar los CVs de postulantes y calificarlos de 0% a 100% según el nivel de coincidencia con el JD. "
  "Incluye un análisis breve que explique por qué califica o no el postulante, destacando habilidades must-have, "
  "nice-to-have, brechas y hallazgos relevantes."
)

# ===== Login =====
USERS = {
  "colab": {"password":"colab123","role":"Colaborador","name":"Colab"},
  "super": {"password":"super123","role":"Supervisor","name":"Sup"},
  "admin": {"password":"admin123","role":"Administrador","name":"Admin"},
}

AGENT_DEFAULT_IMAGES = {
  "Headhunter":        "https://images.unsplash.com/photo-1581090464777-f3220bbe1b8b?q=80&w=512&auto-format&fit=crop",
  "Coordinador RR.HH.":"https://images.unsplash.com/photo-1542751371-adc38448a05e?q=80&w=512&auto-format&fit=crop",
  "Admin RR.HH.":      "https://images.unsplash.com/photo-1526378722484-bd91ca387e72?q=80&w=512&auto-format&fit=crop",
}
LLM_MODELS = ["gpt-4o-mini","gpt-4.1","gpt-4o","claude-3.5-sonnet","claude-3-haiku","gemini-1.5-pro","mixtral-8x7b","llama-3.1-70b"]

# ===== Presets de puestos =====
ROLE_PRESETS = {
  "Asistente Administrativo": {"jd": "Brindar soporte...", "keywords": "Excel, Word...", "must": ["Excel","Gestión documental","Redacción"], "nice": ["Facturación","Caja"], "synth_skills": ["Excel","Word..."]},
  "Business Analytics": {"jd": "Recolectar, transformar...", "keywords": "SQL, Power BI...", "must": ["SQL","Power BI"], "nice": ["Tableau","Python","ETL"], "synth_skills": ["SQL","Power BI..."]},
  "Diseñador/a UX": {"jd": "Responsable de research...", "keywords": "Figma, UX research...", "must": ["Figma","UX Research","Prototipado"], "nice":["Heurísticas","Accesibilidad"], "synth_skills":["Figma","UX Research..."]},
  "Ingeniero/a de Proyectos": {"jd":"Planificar, ejecutar...", "keywords":"MS Project, AutoCAD...", "must":["MS Project","AutoCAD","Presupuestos"], "nice":["BIM","PMBOK"], "synth_skills":["MS Project","AutoCAD..."]},
  "Enfermera/o Asistencial": {"jd":"Brindar atención...", "keywords":"HIS, SAP IS-H...", "must":["HIS","BLS","ACLS"], "nice":["SAP IS-H","Educación paciente"], "synth_skills":["HIS","BLS..."]},
  "Recepcionista de Admisión": {"jd": "Recepción de pacientes...", "keywords": "admisión, caja...", "must": ["Atención cliente","Registro","Caja"], "nice": ["Facturación","SAP"], "synth_skills": ["Atención cliente","Registro..."]}
}

# PDF de ejemplo mínimo
DUMMY_PDF_BYTES = base64.b64decode(
    b'JVBERi0xLjAKMSAwIG9iajw8L1R5cGUvQ2F0YWxvZy9QYWdlcyAyIDAgUj4+ZW5kb2JqCjIgMCBvYmo8PC9UeXBlL1BhZ2VzL0NvdW50IDEvS2lkc1szIDAgUl0+PmVuZG9iagozIDAgb2JqPDwvVHlwZS9QYWdlL01lZGlhQm94WzAgMCAzMCAzMF0vUGFyZW50IDIgMCBSPj5lbmRvYmoKeHJlZgowIDQKMDAwMDAwMDAwMCA2NTUzNSBmIAowMDAwMDAwMDA5IDAwMDAwIG4gCjAwMDAwMDAwNTIgMDAwMDAgbiAKMDAwMDAwMDA5OSAwMDAwMCBuIAp0cmFpbGVyPDwvU2l6ZSA0L1Jvb3QgMSAwIFI+PgpzdGFydHhyZWYKMTQ3CiUlRU9G'
)

# =========================================================
# CSS
# =========================================================
CSS = f"""
:root {{
  --green: {PRIMARY}; --sb-bg: {SIDEBAR_BG}; --sb-tx: {SIDEBAR_TX};
  --body: {BODY_BG}; --sb-card: {CARD_BG};
}}
html, body, [data-testid="stAppViewContainer"] {{ background: var(--body) !important; }}
.block-container {{ background: transparent !important; padding-top: 1.25rem !important; }}
#MainMenu {{visibility:hidden;}}
[data-testid="stToolbar"] {{ display:none !important; }}
header[data-testid="stHeader"] {{ height:0 !important; min-height:0 !important; }}
[data-testid="stSidebar"] {{ background: var(--sb-bg) !important; color: var(--sb-tx) !important; }}
[data-testid="stSidebar"] * {{ color: var(--sb-tx) !important; }}
[data-testid="stSidebar"] h4, [data-testid="stSidebar"] .stMarkdown h4 {{ color: var(--green) !important; }}
.sidebar-brand {{ display:flex; flex-direction:column; align-items:center; justify-content:center; padding:0 0 2px; margin-top:0; text-align:center; }}
.sidebar-brand .brand-title {{ color: var(--green) !important; font-weight:800 !important; font-size:55px !important; line-height:1.05 !important; }}
.sidebar-brand .brand-sub {{ margin-top:4px !important; color: var(--green) !important; font-size:12px !important; opacity:.95 !important; }}
[data-testid="stSidebar"] .stButton>button {{ width: 100% !important; display:flex !important; justify-content:flex-start !important; align-items:center !important; text-align:left !important; gap:8px !important; background: var(--sb-card) !important; border:1px solid var(--sb-bg) !important; color:#fff !important; border-radius:12px !important; padding:9px 12px !important; margin:6px 8px !important; font-weight:600 !important; }}
.block-container .stButton>button {{ width:auto !important; display:flex !important; justify-content:center !important; align-items:center !important; text-align:center !important; background: var(--green) !important; color:#082017 !important; border-radius:10px !important; border:none !important; padding:.50rem .90rem !important; font-weight:700 !important; }}
.block-container .stButton>button:hover {{ filter: brightness(.96); }}
.block-container .stButton>button.delete-confirm-btn {{ background: #D60000 !important; color: white !important; }}
.block-container .stButton>button.cancel-btn {{ background: #e0e0e0 !important; color: #333 !important; }}
h1, h2, h3 {{ color: {TITLE_DARK}; }}
h1 strong, h2 strong, h3 strong {{ color: var(--green); }}
.block-container [data-testid="stSelectbox"]>div>div, .block-container [data-baseweb="select"], .block-container [data-testid="stTextInput"] input, .block-container [data-testid="stTextArea"] textarea {{ background:#F1F7FD !important; color:{TITLE_DARK} !important; border:1.5px solid #E3EDF6 !important; border-radius:10px !important; }}
.block-container table {{ background:#fff !important; border:1px solid #E3EDF6 !important; border-radius:8px !important; }}
.block-container thead th {{ background:#F1F7FD !important; color:{TITLE_DARK} !important; }}
.k-card {{ background:#fff;border:1px solid #E3EDF6;border-radius:12px;padding:14px; margin-bottom: 8px; }}
.badge {{ display:inline-flex;align-items:center;gap:6px;background:#F1F7FD;border:1px solid #E3EDF6;border-radius:24px;padding:4px 10px;font-size:12px;color:#1B2A3C; }}
.priority-Alta {{ border-color: #FFA500 !important; background: #FFF5E6 !important; color: #E88E00 !important; font-weight: 600;}}
.priority-Media {{ border-color: #B9C7DF !important; background: #F1F7FD !important; color: #0E192B !important; }}
.priority-Baja {{ border-color: #D1D5DB !important; background: #F3F4F6 !important; color: #6B7280 !important; }}
.agent-card{{background:#fff;border:1px solid #E3EDF6;border-radius:14px;padding:10px;text-align:center;min-height:178px}}
.agent-card img{{width:84px;height:84px;border-radius:999px;object-fit:cover;border:4px solid #F1F7FD}}
.agent-title{{font-weight:800;color:{TITLE_DARK};font-size:15px;margin-top:6px}}
.agent-sub{{font-size:12px;opacity:.8;margin-top:4px;min-height:30px}}
.toolbar{{display:flex;align-items:center;justify-content:center;gap:8px;margin-top:8px}}
.toolbar .stButton>button{{ background:#fff !important; color:#2b3b4d !important; border:1px solid #E3EDF6 !important; border-radius:10px !important; padding:6px 8px !important; min-width:36px !important; }}
.toolbar .stButton>button:hover{{ background:#F7FBFF !important; }}
.agent-detail{{background:#fff;border:2px solid #E3EDF6;border-radius:16px;padding:16px;box-shadow:0 6px 18px rgba(14,25,43,.08)}}
.login-bg{{background:{SIDEBAR_BG};position:fixed;inset:0;display:flex;align-items:center;justify-content:center}}
.login-card{{background:transparent;border:none;box-shadow:none;padding:0;width:min(600px,92vw);}}
.login-logo-wrap{{display:flex;align-items:center;justify-content:center;margin-bottom:14px}}
.login-sub{{color:#9fb2d3;text-align:center;margin:0 0 18px 0;font-size:12.5px}}
.login-card [data-testid="stTextInput"] input {{ background:#10283f !important; color:#E7F0FA !important; border:1.5px solid #1d3a57 !important; border-radius:24px !important; height:48px !important; padding:0 16px !important; }}
.login-card .stButton>button{{ width:160px !important; border-radius:24px !important; }}
.status-Contratado {{ background-color: #E6FFF1 !important; color: {PRIMARY} !important; border-color: #98E8BF !important; }}
.status-Descartado {{ background-color: #FFE6E6 !important; color: #D60000 !important; border-color: #FFB3B3 !important; }}
.status-Oferta {{ background-color: #FFFDE6 !important; color: #E8B900 !important; border-color: #FFE066 !important; }}
"""
st.set_page_config(page_title="SelektIA", page_icon="🧠", layout="wide")
st.markdown(f"<style>{CSS}</style>", unsafe_allow_html=True)
st.markdown("""<style>[data-testid="stSidebar"] .sidebar-brand .brand-sub{font-size: 12px !important; line-height: 1.2 !important; margin-top: 4px !important; opacity: .95 !important;}</style>""", unsafe_allow_html=True)
st.markdown("""<style>[data-testid="stSidebar"] .sidebar-brand{ margin-top:0 !important; padding-bottom:0 !important; margin-bottom:55px !important; } [data-testid="stSidebar"] [data-testid="stVerticalBlock"]{ gap:2px !important; } [data-testid="stSidebar"] [data-testid="stVerticalBlock"]>div{ margin:0 !important; padding:0 !important; } [data-testid="stSidebar"] h4, [data-testid="stSidebar"] .stMarkdown h4{ margin:2px 8px 2px !important; line-height:1 !important; } [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p{ margin:2px 8px !important; } [data-testid="stSidebar"] .stButton{ margin:0 !important; padding:0 !important; } [data-testid="stSidebar"] .stButton>button{ margin:0 8px 6px 0 !important; padding-left:8px !important; line-height:1.05 !important; gap:6px !important; }</style>""", unsafe_allow_html=True)

# =========================================================
# Persistencia
# =========================================================
# ... (Funciones de persistencia sin cambios) ...
DATA_DIR=Path("data"); DATA_DIR.mkdir(exist_ok=True); AGENTS_FILE=DATA_DIR/"agents.json"; WORKFLOWS_FILE=DATA_DIR/"workflows.json"; ROLES_FILE=DATA_DIR/"roles.json"; TASKS_FILE=DATA_DIR/"tasks.json"; DEFAULT_ROLES=["Headhunter", "Coordinador RR.HH.", "Admin RR.HH."]; DEFAULT_TASKS=[{"id":str(uuid.uuid4()), "titulo":"Revisar CVs top 5", "desc":"Analizar...", "due":str(date.today()+timedelta(days=2)), "assigned_to":"Headhunter", "status":"Pendiente", "priority":"Alta", "created_at":(date.today()-timedelta(days=3)).isoformat()}, {"id":str(uuid.uuid4()), "titulo":"Coordinar entrevista...", "desc":"Agendar...", "due":str(date.today()+timedelta(days=5)), "assigned_to":"Coordinador RR.HH.", "status":"En Proceso", "priority":"Media", "created_at":(date.today()-timedelta(days=8)).isoformat()}, {"id":str(uuid.uuid4()), "titulo":"Crear workflow Onboarding", "desc":"Definir pasos...", "due":str(date.today()-timedelta(days=1)), "assigned_to":"Admin RR.HH.", "status":"Completada", "priority":"Baja", "created_at":(date.today()-timedelta(days=15)).isoformat()}, {"id":str(uuid.uuid4()), "titulo":"Análisis Detallado...", "desc":"Utilizar agente...", "due":str(date.today()+timedelta(days=3)), "assigned_to":"Agente de Análisis", "status":"Pendiente", "priority":"Media", "created_at":date.today().isoformat()}];
def load_roles():
    if ROLES_FILE.exists():
        try: roles=json.loads(ROLES_FILE.read_text(encoding="utf-8")); return sorted(list({*DEFAULT_ROLES, *(r.strip() for r in roles if r.strip())}))
        except: pass
    return DEFAULT_ROLES.copy()
def save_roles(roles: list): roles_clean=sorted(list({r.strip() for r in roles if r.strip()})); custom_only=[r for r in roles_clean if r not in DEFAULT_ROLES]; ROLES_FILE.write_text(json.dumps(custom_only, ensure_ascii=False, indent=2), encoding="utf-8")
def load_json(path: Path, default):
    if path.exists():
        try: return json.loads(path.read_text(encoding="utf-8"))
        except Exception as e: print(f"Error reading {path}: {e}"); return default if isinstance(default, (list, dict)) else []
    if default is not None:
        try: save_json(path, default)
        except Exception as e: print(f"Error creating {path}: {e}")
    return default if isinstance(default, (list, dict)) else []
def save_json(path: Path, data):
    try: path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e: print(f"Error saving {path}: {e}")
def load_agents(): return load_json(AGENTS_FILE, []); def save_agents(agents): save_json(AGENTS_FILE, agents)
def load_workflows(): return load_json(WORKFLOWS_FILE, []); def save_workflows(wfs): save_json(WORKFLOWS_FILE, wfs)
def load_tasks(): return load_json(TASKS_FILE, DEFAULT_TASKS); def save_tasks(tasks): save_json(TASKS_FILE, tasks)


# =========================================================
# ESTADO
# =========================================================
ss = st.session_state
if "auth" not in ss: ss.auth = None
if "section" not in ss: ss.section = "publicacion_sourcing"
if "tasks_loaded" not in ss:
    ss.tasks = load_tasks()
    if not isinstance(ss.tasks, list): ss.tasks = DEFAULT_TASKS; save_tasks(ss.tasks)
    ss.tasks_loaded = True
if "candidates" not in ss: ss.candidates = []
if "offers" not in ss: ss.offers = {}
if "agents_loaded" not in ss: ss.agents = load_agents(); ss.agents_loaded = True
if "workflows_loaded" not in ss: ss.workflows = load_workflows(); ss.workflows_loaded = True
if "agent_view_idx" not in ss: ss.agent_view_idx = None
if "agent_edit_idx" not in ss: ss.agent_edit_idx = None
if "new_role_mode" not in ss: ss.new_role_mode = False
if "roles" not in ss: ss.roles = load_roles()
if "positions" not in ss: ss.positions = pd.DataFrame([{"ID":"10,645,194","Puesto":"Dev Backend","Días Abierto":3,"Leads":1800,"Nuevos":115,"RS":35,"HS":7,"ET":14,"EP":15,"Loc":"Lima","HM":"R. Brykson","Estado":"Abierto","Inicio":date.today()-timedelta(days=3)}, {"ID":"10,376,415","Puesto":"VP Marketing","Días Abierto":28,"Leads":8100,"Nuevos":1,"RS":15,"HS":35,"ET":5,"EP":7,"Loc":"Santiago","HM":"A. Cruz","Estado":"Abierto","Inicio":date.today()-timedelta(days=28)}, {"ID":"10,376,646","Puesto":"Planner Demanda","Días Abierto":28,"Leads":2300,"Nuevos":26,"RS":3,"HS":8,"ET":6,"EP":3,"Loc":"CDMX","HM":"R. Brykson","Estado":"Abierto","Inicio":date.today()-timedelta(days=28)}])
if "pipeline_filter" not in ss: ss.pipeline_filter = None
if "expanded_task_id" not in ss: ss.expanded_task_id = None
if "show_assign_for" not in ss: ss.show_assign_for = None
if "confirm_delete_id" not in ss: ss.confirm_delete_id = None

# =========================================================
# UTILS
# =========================================================
# ... (Funciones Utils sin cambios significativos) ...
SKILL_SYNONYMS={"Excel":["excel","xlsx"],"Gestión documental":["gestión documental"],"Redacción":["redacción"],"Facturación":["facturación"],"Caja":["caja"],"SQL":["sql"],"Power BI":["power bi"],"Tableau":["tableau"],"ETL":["etl"],"KPIs":["kpi"],"MS Project":["ms project"],"AutoCAD":["autocad"],"BIM":["bim"],"Presupuestos":["presupuesto"],"Figma":["figma"],"UX Research":["ux research"],"Prototipado":["prototipado"],"Python":["python"],"Agile":["agile","scrum"]}
def _normalize(t): return re.sub(r"\s+"," ",(t or "")).strip().lower()
def infer_skills(t): t=_normalize(t); o=set();[o.add(k) for k,s in SKILL_SYNONYMS.items() if any(sy in t for sy in s)]; return o
def score_fit_by_skills(jd,must_l,nice_l,cv): js=infer_skills(jd); m=set([i.strip() for i in must_l if i.strip()]) or js; n=set([i.strip() for i in nice_l if i.strip()])-m; cvs=infer_skills(cv); mm=sorted(list(m&cvs)); mn=sorted(list(n&cvs)); gm=sorted(list(m-cvs)); gn=sorted(list(n-cvs)); ex=sorted(list((cvs&(js|m|n))-set(mm)-set(mn))); cm=len(mm)/len(m) if m else 0; cn=len(mn)/len(n) if n else 0; sc=int(round(100*(0.65*cm+0.2*cn+0.15*min(len(ex),5)/5))); return sc,{"matched_must":mm,"matched_nice":mn,"gaps_must":gm,"gaps_nice":gn,"extras":ex,"must_total":len(m),"nice_total":len(n)}
def build_analysis_text(n,ex): okm=", ".join(ex["matched_must"]) if ex["matched_must"] else"-"; okn=", ".join(ex["matched_nice"]) if ex["matched_nice"] else"-"; g=", ".join(ex["gaps_must"][:3]) if ex["gaps_must"] else"-"; e=", ".join(ex["extras"][:3]) if ex["extras"] else"-"; return f"{n}: Must:{okm}. Nice:{okn}. Brechas:{g}. Extras:{e}."
def pdf_viewer_embed(fb, h=520): try: b64=base64.b64encode(fb).decode("utf-8"); st.components.v1.html(f'<embed src="data:application/pdf;base64,{b64}" type="application/pdf" width="100%" height="{h}px"/>',height=h) except Exception as e: st.error(f"Err PDF: {e}")
def _extract_docx_bytes(b): try: z=zipfile.ZipFile(io.BytesIO(b)); x=z.read("word/document.xml").decode("utf-8","ignore"); t=re.sub(r"<.*?>"," ",x); return re.sub(r"\s+"," ",t).strip(); except: return ""
def extract_text_from_file(uf): try: s=Path(uf.name).suffix.lower(); fb=uf.read(); uf.seek(0);
if s==".pdf": r=PdfReader(io.BytesIO(fb)); t=""; [t:= (t+(p.extract_text() or "")+"\n") for p in r.pages]; return t
elif s==".docx": return _extract_docx_bytes(fb)
else: return fb.decode("utf-8","ignore")
except Exception as e: print(f"Err extract {uf.name}:{e}"); return ""
def _max_years(t): t=t.lower(); y=0; [y:=max(y, int(m.group(1))) for m in re.finditer(r'(\d{1,2})\s*(años|year)', t)]; return 5 if y==0 and any(w in t for w in ["años","exp"]) else y
def extract_meta(t): y=_max_years(t); return{"uni":"—","anios":y,"titulo":"—","loc":"—","update":date.today().isoformat()}
def calculate_analytics(cands):
    if not cands: return{"avg_fit":0, "time_to_hire":"—","source_counts":{},"funnel_data":pd.DataFrame()}
    jd=ss.get("last_jd_text",""); p=ROLE_PRESETS.get(ss.get("last_role",""),{}); m,n=p.get("must",[]),p.get("nice",[]); fits=[]; sc={}; stc={s:0 for s in PIPELINE_STAGES}; tths=[]
    for c in cands: txt=c.get("_text",""); f,_=score_fit_by_skills(jd,m,n,txt); fits.append(f); s=c.get("source","Manual"); sc[s]=sc.get(s,0)+1; stc[c.get("stage",PIPELINE_STAGES[0])]+=1;
    if c.get("stage")=="Contratado" and (ld:=c.get("load_date")): try: tths.append((datetime.now()-datetime.fromisoformat(ld)).days); except: pass
    avgf=round(sum(fits)/len(fits),1) if fits else 0; tth=f"{round(sum(tths)/len(tths),1)}d" if tths else"—"; fd=pd.DataFrame({"Fase":PIPELINE_STAGES,"Candidatos":[stc.get(s,0) for s in PIPELINE_STAGES]})
    return{"avg_fit":avgf, "time_to_hire":tth,"source_counts":sc,"funnel_data":fd}

# ====== Helpers de TAREAS (Acciones) ======
def _status_pill(s: str)->str: colors={"Pendiente":"#9AA6B2","En Proceso":"#0072E3","Completada":"#10B981","En Espera":"#FFB700"}; c=colors.get(s,"#9AA6B2"); return f'<span class="badge" style="border-color:{c}33;background:{c}14;color:#0A2230">{s}</span>'
def _priority_pill(p: str) -> str: p_safe=p if p in TASK_PRIORITIES else "Media"; return f'<span class="badge priority-{p_safe}">{p_safe}</span>'

# (MODIFICADO) render_task_row para layout de tarjeta, confirmación y prioridad
def render_task_row(task: dict):
    t_id = task.get("id") or str(uuid.uuid4()); task["id"] = t_id

    # --- Layout Principal de la Tarjeta ---
    st.markdown(f"**{task.get('titulo','—')}**")
    st.caption(task.get("desc","—"))

    # --- Fila de Metadatos (Estado, Prio, Vence, Asignado) ---
    meta_cols = st.columns([1, 1, 1.5, 1.5]) # Ajustar pesos si es necesario
    with meta_cols[0]:
        st.markdown(_status_pill(task.get("status","Pendiente")), unsafe_allow_html=True)
    with meta_cols[1]:
         st.markdown(_priority_pill(task.get("priority", "Media")), unsafe_allow_html=True)
    with meta_cols[2]:
        st.markdown(f"<small>Vence: {task.get('due','—')}</small>", unsafe_allow_html=True)
    with meta_cols[3]:
        st.markdown(f"<small>Asignado a: {task.get('assigned_to','—')}</small>", unsafe_allow_html=True)

    st.markdown("---") # Separador antes de acciones

    # --- Fila de Acciones ---
    action_col_placeholder = st.empty()

    # --- Callback ---
    def handle_action_change(task_id_arg):
        selectbox_key = f"accion_{task_id_arg}"
        if selectbox_key not in ss: return
        action = ss[selectbox_key]
        task_to_update = next((t for t in ss.tasks if t.get("id") == task_id_arg), None)
        if not task_to_update: return

        # Limpiar otros estados activos si son de OTRA tarea
        if ss.get("expanded_task_id") and ss.expanded_task_id != task_id_arg: ss.expanded_task_id = None
        if ss.get("show_assign_for") and ss.show_assign_for != task_id_arg: ss.show_assign_for = None
        if ss.get("confirm_delete_id") and ss.confirm_delete_id != task_id_arg: ss.confirm_delete_id = None

        needs_rerun = False
        if action == "Ver detalle":
            ss.expanded_task_id = task_id_arg; ss.show_assign_for = None; ss.confirm_delete_id = None; needs_rerun = True
        elif action == "Asignar tarea":
            ss.show_assign_for = task_id_arg; ss.expanded_task_id = None; ss.confirm_delete_id = None; needs_rerun = True
        elif action == "Tomar tarea":
            current_user = (ss.auth["name"] if ss.get("auth") else "Admin")
            task_to_update["assigned_to"] = current_user; task_to_update["status"] = "En Proceso"; save_tasks(ss.tasks)
            ss.show_assign_for = None; ss.expanded_task_id = None; ss.confirm_delete_id = None
            st.toast("Tarea tomada."); needs_rerun = True
        elif action == "Eliminar":
            ss.confirm_delete_id = task_id_arg; ss.show_assign_for = None; ss.expanded_task_id = None; needs_rerun = True

        if needs_rerun:
             try: st.rerun()
             except Exception as e: print(f"Rerun failed: {e}")

    # --- Mostrar Selectbox o Confirmación ---
    with action_col_placeholder.container():
        selectbox_key = f"accion_{t_id}"
        if ss.get("confirm_delete_id") == t_id:
             st.caption("¿Seguro?")
             btn_cols = st.columns(2)
             with btn_cols[0]:
                 if st.button("Eliminar permanentemente", key=f"del_confirm_{t_id}", type="primary", use_container_width=True):
                     ss.tasks = [t for t in ss.tasks if t.get("id") != t_id]; save_tasks(ss.tasks)
                     ss.confirm_delete_id = None; st.warning("Tarea eliminada."); st.rerun()
             with btn_cols[1]:
                 if st.button("Cancelar", key=f"del_cancel_{t_id}", use_container_width=True):
                     ss.confirm_delete_id = None; ss[selectbox_key] = "Selecciona…"; st.rerun()
        else:
            options = ["Selecciona…", "Ver detalle", "Asignar tarea", "Tomar tarea", "Eliminar"]
            current_selection = "Selecciona…" # Default a no seleccionar nada activo
            # Determinar si hay una acción activa para esta tarea específica
            if ss.get("expanded_task_id") == t_id: current_selection = "Ver detalle"
            elif ss.get("show_assign_for") == t_id: current_selection = "Asignar tarea"
            # No hay estado visual para "Eliminar" (se convierte en botones) o "Tomar tarea" (es instantáneo)

            try: current_action_index = options.index(current_selection)
            except ValueError: current_action_index = 0

            st.selectbox(
                "Acciones", options, key=selectbox_key,
                label_visibility="collapsed", index=current_action_index,
                on_change=handle_action_change, args=(t_id,)
            )

    # --- Asignación inline (fuera de la columna de acciones, debajo del separador) ---
    if ss.show_assign_for == t_id:
        assign_cols = st.columns([1.5, 1.5, 1.2, 0.8])
        with assign_cols[0]: assign_type = st.selectbox("Tipo Asignación", ["En Espera", "Equipo", "Usuario"], key=f"type_{t_id}", index=2)
        with assign_cols[1]:
            nuevo_assignee = ""; current_assignee = task.get("assigned_to", "Headhunter")
            if assign_type == "En Espera": nuevo_assignee = "En Espera"; st.text_input("Asignado a", "En Espera", key=f"val_esp_{t_id}", disabled=True)
            elif assign_type == "Equipo": equipos = ["Coordinador RR.HH.", "Admin RR.HH.", "Agente de Análisis"]; idx = equipos.index(current_assignee) if current_assignee in equipos else 0; nuevo_assignee = st.selectbox("Equipo", equipos, key=f"val_eq_{t_id}", index=idx)
            elif assign_type == "Usuario": usuarios = ["Headhunter", "Colab", "Sup", "Admin"]; idx = usuarios.index(current_assignee) if current_assignee in usuarios else 0; nuevo_assignee = st.selectbox("Usuario", usuarios, key=f"val_us_{t_id}", index=idx)
        with assign_cols[2]: current_prio = task.get("priority", "Media"); prio_index = TASK_PRIORITIES.index(current_prio) if current_prio in TASK_PRIORITIES else 1; nueva_prio = st.selectbox("Prioridad", TASK_PRIORITIES, key=f"prio_{t_id}", index=prio_index)
        with assign_cols[3]:
            if st.button("Guardar", key=f"btn_assign_{t_id}", use_container_width=True):
              task_to_update = next((t for t in ss.tasks if t.get("id") == t_id), None)
              if task_to_update:
                  task_to_update["assigned_to"] = nuevo_assignee; task_to_update["priority"] = nueva_prio
                  if assign_type == "En Espera": task_to_update["status"] = "En Espera"
                  elif task_to_update["status"] == "En Espera": task_to_update["status"] = "Pendiente"
                  save_tasks(ss.tasks); ss.show_assign_for = None; selectbox_key = f"accion_{t_id}"; ss[selectbox_key] = "Selecciona…"
                  if assign_type == "Equipo": st.success("Asignado a Equipo."); ss.section = "agent_tasks"; st.rerun()
                  else: st.success("Cambios guardados."); st.rerun()


# (MODIFICADO) create_task_from_flow ahora marca la tarea como Completada
def create_task_from_flow(name:str, due_date:date, desc:str, assigned:str="Sistema", status:str="Completada", priority:str="Media"):
    t = {"id": str(uuid.uuid4()),"titulo": f"Flujo Ejecutado: {name}","desc": desc or f"Flujo '{name}' ejecutado.","due": due_date.isoformat(),"assigned_to": assigned,"status": "Completada","priority": priority if priority in TASK_PRIORITIES else "Media","created_at": datetime.now().isoformat()}
    if not isinstance(ss.tasks, list): ss.tasks = []
    ss.tasks.insert(0, t)
    save_tasks(ss.tasks)


# =========================================================
# INICIALIZACIÓN DE CANDIDATOS
# =========================================================
# ... (Sin cambios) ...
if "candidate_init" not in ss:
  initial_candidates=[{"Name":"CV_AnaLopez.pdf","Score":85,"Role":"Business Analytics","source":"LinkedIn Jobs"},{"Name":"CV_LuisGomez.pdf","Score":42,"Role":"Business Analytics","source":"Computrabajo"},{"Name":"CV_MartaDiaz.pdf","Score":91,"Role":"Desarrollador/a Backend (Python)","source":"Indeed"},{"Name":"CV_JaviRuiz.pdf","Score":30,"Role":"Diseñador/a UX","source":"laborum.pe"}]; cl=[]
  for i,c in enumerate(initial_candidates): c["id"]=f"C{i+1}-{random.randint(1000,9999)}"; c["stage"]=PIPELINE_STAGES[random.choice([0,1,1,2,6])]; c["load_date"]=(date.today()-timedelta(days=random.randint(5,30))).isoformat(); c["_bytes"]=DUMMY_PDF_BYTES; c["_is_pdf"]=True; c["_text"]=f"CV {c['Name']}. Exp 5a."; c["meta"]=extract_meta(c["_text"]);
  if c["stage"]=="Descartado": c["Score"]=random.randint(20,34);
  if c["stage"]=="Contratado": c["Score"]=95; cl.append(c)
  ss.candidates=cl; ss.candidate_init=True


# =========================================================
# LOGIN + SIDEBAR
# =========================================================
# ... (Sin cambios) ...
def asset_logo_wayki(): local=Path("assets/logo-wayki.png"); return str(local) if local.exists() else "https://raw.githubusercontent.com/wayki-consulting/.dummy/main/logo-wayki.png"
def login_screen(): st.markdown('<div class="login-bg"><div class="login-card">', unsafe_allow_html=True); try: st.markdown('<div class="login-logo-wrap"><img src="'+asset_logo_wayki()+'" width=120></div>', unsafe_allow_html=True); except: pass; st.markdown('<div class="login-sub">Acceso a SelektIA</div>', unsafe_allow_html=True);
with st.form("login_form"): u=st.text_input("Usuario"); p=st.text_input("Contraseña", type="password");
if st.form_submit_button("Ingresar"):
    if u in USERS and USERS[u]["password"]==p: ss.auth={"username":u,"role":USERS[u]["role"],"name":USERS[u]["name"]}; st.success("Bienvenido."); st.rerun()
    else: st.error("Inválido.")
st.markdown("</div></div>", unsafe_allow_html=True)
def require_auth():
    if ss.auth is None: login_screen(); return False
    return True
def render_sidebar():
    with st.sidebar: st.markdown('<div class="sidebar-brand"><div class="brand-title">SelektIA</div><div class="brand-sub">Powered by Wayki</div></div>', unsafe_allow_html=True); st.markdown("#### DASHBOARD"); if st.button("Analytics", key="sb_analytics"): ss.section="analytics"; ss.pipeline_filter=None; st.rerun(); st.markdown("#### ASISTENTE IA"); if st.button("Flujos", key="sb_flows"): ss.section="flows"; ss.pipeline_filter=None; st.rerun(); if st.button("Agentes", key="sb_agents"): ss.section="agents"; ss.pipeline_filter=None; st.rerun(); st.markdown("#### PROCESO");
    for txt, sec, stage in [("Publicación","pub_sourcing",None),("Puestos","puestos",None),("Evaluación","eval",None),("Pipeline","pipeline",None),("Entr. Gerencia","pipeline","Entrevista Gerencia"),("Oferta","pipeline","Oferta"),("Onboarding","pipeline","Contratado")]: is_pipe=stage is not None or txt=="Pipeline"; key=f"sb_{sec}"+ (f"_{txt.replace(' ','_')}" if is_pipe and stage else "");
    if st.button(txt,key=key): ss.section="pipeline" if is_pipe else sec; ss.pipeline_filter=stage if is_pipe else None; st.rerun()
    st.markdown("#### TAREAS"); if st.button("Todas",key="sb_task_manual"): ss.section="create_task"; st.rerun(); if st.button("Asignado a mi",key="sb_task_hh"): ss.section="hh_tasks"; st.rerun(); if st.button("Mi equipo",key="sb_task_agente"): ss.section="agent_tasks"; st.rerun(); st.markdown("#### ACCIONES"); if st.button("Cerrar sesión",key="sb_logout"): ss.auth=None; st.rerun()


# =========================================================
# PÁGINAS (Sin cambios significativos)
# =========================================================
# ... (page_def_carga, page_puestos, page_eval, page_pipeline, page_interview, page_offer, page_onboarding, page_hh_tasks, page_agent_tasks, page_agents, page_flows, page_analytics) ...
def page_def_carga(): st.header("Publicación & Sourcing"); roles=list(ROLE_PRESETS.keys()); st.subheader("1. Vacante"); c1,c2=st.columns(2); with c1: p=st.selectbox("Puesto", roles, index=1); with c2: id_p=st.text_input("ID", value=f"P-{random.randint(1000,9999)}"); preset=ROLE_PRESETS[p]; jd=st.text_area("JD", height=180, value=preset["jd"]); kw=st.text_area("Keywords", height=100, value=preset["keywords"]); ss["last_role"]=p; ss["last_jd_text"]=jd; ss["last_kw_text"]=kw; st.subheader("2. Carga Manual"); files=st.file_uploader("Subir CVs", type=["pdf","docx","txt"], accept_multiple_files=True);
if files and st.button("Procesar (Manual)"): nc=[]; must=[s.strip() for s in preset.get("must",[]) if s.strip()]; nice=[s.strip() for s in preset.get("nice",[]) if s.strip()];
for f in files: b=f.read(); f.seek(0); txt=extract_text_from_file(f); score,exp=score_fit_by_skills(jd,must,nice,txt); c={"id":f"C{len(ss.candidates)+len(nc)+1}-{int(datetime.now().timestamp())}","Name":f.name,"Score":score,"Role":p,"Role_ID":id_p,"_bytes":b,"_is_pdf":Path(f.name).suffix.lower()==".pdf","_text":txt,"meta":extract_meta(txt),"stage":PIPELINE_STAGES[0],"load_date":date.today().isoformat(),"_exp":exp,"source":"Manual"}; nc.append(c)
for c in nc: if c["Score"]<35: c["stage"]="Descartado"; ss.candidates.append(c);
st.success(f"{len(nc)} CVs procesados."); st.rerun()
st.subheader("3. Sourcing Portales"); with st.expander("🔌 Integración"): srcs=st.multiselect("Portales", JOB_BOARDS, default=["laborum.pe"]); qty=st.number_input("Cantidad",1,30,6); sq=st.text_input("Búsqueda", value=p); loc=st.text_input("Ubicación", value="Lima");
if st.button("Traer CVs"): nc=[]; must=[s.strip() for s in preset.get("must",[]) if s.strip()]; nice=[s.strip() for s in preset.get("nice",[]) if s.strip()];
for board in srcs:
    for i in range(1,int(qty)+1): txt=f"CV Sim {board}/{p}. Exp {random.randint(2,10)}a. Skills: {', '.join(random.sample(preset.get('synth_skills',['Excel']),k=3))}"; score,exp=score_fit_by_skills(jd,must,nice,txt); c={"id":f"C{len(ss.candidates)+len(nc)+1}-{int(datetime.now().timestamp())}","Name":f"{board}_Cand_{i:02d}.pdf","Score":score,"Role":p,"Role_ID":id_p,"_bytes":DUMMY_PDF_BYTES,"_is_pdf":True,"_text":txt,"meta":extract_meta(txt),"stage":PIPELINE_STAGES[0],"load_date":date.today().isoformat(),"_exp":exp,"source":board}; nc.append(c)
for c in nc: if c["Score"]<35: c["stage"]="Descartado"; ss.candidates.append(c);
st.success(f"{len(nc)} CVs importados."); st.rerun()

def page_puestos(): st.header("Puestos"); dfp=ss.positions.copy(); dfp["TTH"]=dfp["Días Abierto"].apply(lambda d:f"{d+random.randint(10,40)}d" if d<30 else f"{d}d"); st.dataframe(dfp.rename(columns={"Días Abierto":"Abierto","Time to Hire (promedio)":"TTH"}),use_container_width=True, height=380, hide_index=True, column_order=["Puesto","Abierto","TTH","Leads","Nuevos","Recruiter Screen","HM Screen","Entrevista Telefónica","Entrevista Presencial","Ubicación","Hiring Manager","Estado","ID"]); st.subheader("Candidatos x Puesto"); pl=dfp["Puesto"].tolist(); sp=st.selectbox("Selecciona Puesto", pl);
if sp: cands=[c for c in ss.candidates if c.get("Role")==sp];
if cands: dfc=pd.DataFrame(cands); st.dataframe(dfc[["Name","Score","stage","load_date"]].rename(columns={"Name":"Cand","Score":"Fit","stage":"Fase","load_date":"Fecha"}), use_container_width=True, hide_index=True)
else: st.info(f"No hay candidatos para **{sp}**.")

def page_eval(): st.header("Evaluación");
if not ss.candidates: st.info("Carga CVs."); return; jd=st.text_area("JD",ss.get("last_jd_text",""),height=140); preset=ROLE_PRESETS.get(ss.get("last_role",""),{}); c1,c2=st.columns(2); with c1: md=st.text_area("Must",value=", ".join(preset.get("must",[]))); with c2: nd=st.text_area("Nice",value=", ".join(preset.get("nice",[]))); m=[s.strip() for s in md.split(",") if s.strip()]; n=[s.strip() for s in nd.split(",") if s.strip()]; enriched=[]
for c in ss.candidates: cv=c.get("_text",""); fit,exp=score_fit_by_skills(jd,m,n,cv); c["Score"]=fit; c["_exp"]=exp; enriched.append({"id":c["id"],"Name":c["Name"],"Fit":fit,"Must":f"{len(exp['matched_must'])}/{exp['must_total']}","Nice":f"{len(exp['matched_nice'])}/{exp['nice_total']}","Extras":len(exp['extras'])})
df=pd.DataFrame(enriched).sort_values("Fit",ascending=False).reset_index(drop=True); st.subheader("Ranking"); st.dataframe(df[["Name","Fit","Must","Nice","Extras"]], use_container_width=True, height=250); st.subheader("Detalle")
if not df.empty: sn=st.selectbox("Candidato", df["Name"].tolist()); sid=df[df["Name"]==sn]["id"].iloc[0]; cand=next((c for c in ss.candidates if c["id"]==sid),None)
if cand: fit=cand["Score"]; exp=cand["_exp"]; cvb=cand.get("_bytes",b""); cvt=cand.get("_text",""); ispdf=cand.get("_is_pdf",False); c1,c2=st.columns([1,1])
with c1: fig=px.bar(pd.DataFrame([{"C":sn,"Fit":fit}]), x="C", y="Fit"); fig.update_layout(yaxis_range=[0,100]); st.plotly_chart(fig, use_container_width=True); st.markdown("**Explicación**"); st.markdown(f"- Must: {len(exp['matched_must'])}/{exp['must_total']} ({', '.join(exp['matched_must']) if exp['matched_must'] else '-'})"); if exp["gaps_must"]: st.markdown(f"  - Faltan: {', '.join(exp['gaps_must'])}"); st.markdown(f"- Nice: {len(exp['matched_nice'])}/{exp['nice_total']} ({', '.join(exp['matched_nice']) if exp['matched_nice'] else '-'})"); if exp["gaps_nice"]: st.markdown(f"  - Faltan: {', '.join(exp['gaps_nice'])}"); if exp["extras"]: st.markdown(f"- Extras: {', '.join(exp['extras'])}")
with c2: st.markdown("**CV**");
if ispdf and cvb: pdf_viewer_embed(cvb, height=420)
else: st.text_area("TXT", cvt, height=420)
else: st.error("Detalles no hallados.")
else: st.info("No hay candidatos.")

def page_pipeline(): fs=ss.get("pipeline_filter"); hdr=f"Pipeline: '{fs}'" if fs else "Pipeline Kanban"; st.header(hdr); cands=[c for c in ss.candidates if c.get("stage")==fs] if fs else ss.candidates; st.caption("Mueve candidatos.");
if not cands and fs: st.info(f"No hay en **{fs}**."); return;
if not ss.candidates: st.info("No hay candidatos."); return; cands_by_stage={s:[] for s in PIPELINE_STAGES}; [cands_by_stage[c.get("stage",PIPELINE_STAGES[0])].append(c) for c in cands]; cols=st.columns(len(PIPELINE_STAGES))
for i, stage in enumerate(PIPELINE_STAGES):
    with cols[i]: st.markdown(f"**{stage} ({len(cands_by_stage[stage])})**"); st.markdown("---");
    for c in cands_by_stage[stage]: name=c["Name"].split('_')[-1].replace('.pdf','').replace('.txt',''); bc=PRIMARY if c['Score']>=70 else ('#FFA500' if c['Score']>=40 else '#D60000'); st.markdown(f'<div class="k-card" style="margin-bottom:10px; border-left:4px solid {bc}"><div style="font-weight:700;">{name}</div><div style="font-size:12px;opacity:.8;">{c.get("Role","N/A")}</div><div style="font-size:14px;font-weight:700;margin-top:8px;">Fit: <span style="color:{PRIMARY};">{c["Score"]}%</span></div><div style="font-size:10px;opacity:.6;margin-top:4px;">Fuente: {c.get("source","N/A")}</div></div>', unsafe_allow_html=True);
    with st.form(key=f"fm_{c['id']}"): ci=PIPELINE_STAGES.index(stage); av=[s for s in PIPELINE_STAGES if s!=stage]; try: di=av.index(PIPELINE_STAGES[min(ci+1,len(PIPELINE_STAGES)-1)]); except: di=0; ns=st.selectbox("Mover:", av, key=f"sm_{c['id']}", index=di, label_visibility="collapsed");
    if st.form_submit_button("➡️"): c["stage"]=ns;
    if ns=="Descartado": st.success(f"📧 Rechazo a {name}.")
    elif ns=="Entrevista Telefónica": st.info(f"📅 Tarea para {name}."); create_task_from_flow(f"Programar {name}", date.today()+timedelta(days=2),"Coord. entrevista.", assigned="Headhunter", status="Pendiente")
    elif ns=="Contratado": st.balloons(); st.success(f"🎉 Onboarding {name}.")
    if fs and ns!=fs: ss.pipeline_filter=None; st.info("Filtro removido.");
    st.rerun() # Rerun es necesario después de mover
    st.markdown("<br>", unsafe_allow_html=True) # Espacio

def page_interview(): st.rerun()
def _ensure_offer_record(cn):
    if cn not in ss.offers: ss.offers[cn]={"puesto":"","ubicacion":"","modalidad":"Presencial","salario":"","beneficios":"","fecha_inicio":date.today()+timedelta(days=14),"caducidad":date.today()+timedelta(days=7),"aprobadores":"Gerencia, Legal","estado":"Borrador"}
def page_offer(): st.rerun()
def page_onboarding(): st.rerun()

# ===================== TODAS LAS TAREAS =====================
# (MODIFICADO) page_create_task para usar formato tarjeta
def page_create_task():
    st.header("Todas las Tareas")
    st.info("Muestra todas las tareas registradas en el sistema.")
    if not isinstance(ss.tasks, list): ss.tasks = load_tasks()
    if not isinstance(ss.tasks, list): ss.tasks = []

    if not ss.tasks: st.write("No hay tareas registradas."); return

    tasks_list = ss.tasks # Trabajar directamente con la lista en sesión

    all_statuses_set = set(t.get('status', 'Pendiente') for t in tasks_list)
    if "En Espera" not in all_statuses_set: all_statuses_set.add("En Espera")
    all_statuses = ["Todos"] + sorted(list(all_statuses_set))
    selected_status = st.selectbox("Filtrar por Estado", all_statuses, index=0)
    tasks_to_show = tasks_list if selected_status=="Todos" else [t for t in tasks_list if t.get("status") == selected_status]

    if not tasks_to_show: st.info(f"No hay tareas con el estado '{selected_status}'."); return

    # --- Renderizar cada tarea como una TARJETA ---
    for task in tasks_to_show:
        # Usar k-card para mantener el estilo original
        st.markdown('<div class="k-card">', unsafe_allow_html=True)
        render_task_row(task) # Renderiza el contenido dentro de la tarjeta
        st.markdown('</div>', unsafe_allow_html=True)


# =========================================================
# ROUTER
# =========================================================
ROUTES = {"publicacion_sourcing": page_def_carga,"puestos": page_puestos,"eval": page_eval,"pipeline": page_pipeline,"interview": page_interview,"offer": page_offer,"onboarding": page_onboarding,"hh_tasks": page_hh_tasks,"agents": page_agents,"flows": page_flows,"agent_tasks": page_agent_tasks,"analytics": page_analytics,"create_task": page_create_task}

# =========================================================
# APP
# =========================================================
if require_auth():
    render_sidebar()
    task_id_for_dialog = ss.get("expanded_task_id")

    # Redirecciones si la sección actual no tiene página dedicada
    if ss.section in ["interview", "offer", "onboarding"]:
        target_stage = {"interview": "Entrevista Gerencia", "offer": "Oferta", "onboarding": "Contratado"}.get(ss.section)
        st.info(f"Gestiona '{target_stage}' desde el Pipeline.")
        # Actualizar estado ANTES de llamar a rerun implícito por fin de script
        ss.section = "pipeline"
        ss.pipeline_filter = target_stage
        # No llamar a st.rerun() explícitamente aquí
    else:
        # Renderizar página normal
        page_func = ROUTES.get(ss.section, page_def_carga)
        page_func()


    # --- Lógica del Diálogo (MODIFICADA con try...except y Prioridad) ---
    if task_id_for_dialog:
        task_data = next((t for t in ss.tasks if t.get("id") == task_id_for_dialog), None)
        if task_data:
            try:
                with st.dialog("Detalle de Tarea", width="large"):
                    st.markdown(f"### {task_data.get('titulo', 'Sin Título')}")
                    c1, c2, c3, c4 = st.columns(4)
                    with c1: st.markdown("**Asignado a:**"); st.markdown(f"`{task_data.get('assigned_to', 'N/A')}`")
                    with c2: st.markdown("**Vencimiento:**"); st.markdown(f"`{task_data.get('due', 'N/A')}`")
                    with c3: st.markdown("**Estado:**"); st.markdown(_status_pill(task_data.get('status', 'Pendiente')), unsafe_allow_html=True)
                    with c4: st.markdown("**Prioridad:**"); st.markdown(_priority_pill(task_data.get('priority', 'Media')), unsafe_allow_html=True)
                    st.markdown("---"); st.markdown("**Descripción:**"); st.markdown(task_data.get('desc', 'Sin descripción.'))
                    st.markdown("---"); st.markdown("**Actividad Reciente:**")
                    st.markdown(f"- Creada: {task_data.get('created_at', 'N/A').split('T')[0]}")
                    st.markdown("- *No hay más actividad.*")
                    with st.form("comment_form"): st.text_area("Comentarios", placeholder="Añadir...", key="task_comment");
                    if st.form_submit_button("Enviar Comentario"): st.toast("Comentario no guardado.")
                    if st.button("Cerrar", key="close_dialog"): ss.expanded_task_id = None; st.rerun()
            except Exception as e:
                st.error(f"Error al mostrar detalles: {e}")
                print(f"Error dialog {task_id_for_dialog}: {e}") # Debug
                if ss.get("expanded_task_id") == task_id_for_dialog: ss.expanded_task_id = None; st.rerun()
        else:
             if ss.get("expanded_task_id") == task_id_for_dialog: ss.expanded_task_id = None; # st.rerun() # Opcional
