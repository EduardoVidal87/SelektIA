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
# PALETA / CONST (se mantienen)
# =========================================================
PRIMARY    = "#00CD78"         # color marca
SIDEBAR_BG = "#0E192B"
SIDEBAR_TX = "#B9C7DF"
BODY_BG    = "#F7FBFF"
CARD_BG    = "#0E192B"
TITLE_DARK = "#142433"

BAR_DEFAULT = "#E9F3FF"
BAR_GOOD    = "#33FFAC"

JOB_BOARDS  = ["laborum.pe","Computrabajo","Bumeran","Indeed","LinkedIn Jobs"]

# =========================================================
# ESTILOS (respetando look & feel)
# =========================================================
def inject_base_css():
    st.markdown(f"""
    <style>
      /* Fondo general */
      .stApp {{
        background: {BODY_BG};
      }}
      /* Sidebar */
      section[data-testid="stSidebar"] {{
        background: {SIDEBAR_BG};
        color: {SIDEBAR_TX};
      }}
      section[data-testid="stSidebar"] * {{
        color: {SIDEBAR_TX};
      }}
      /* Títulos verdes */
      h1, h2, h3, h4 {{
        color: "{PRIMARY}";
      }}
      /* Tarjetas y contenedores */
      .card {{
        background: white;
        border: 1px solid #E6EEF7;
        border-radius: 14px;
        padding: 14px 16px;
        margin-bottom: 10px;
      }}
      .card-header {{
        display: flex;
        align-items: center;
        justify-content: space-between;
      }}
      .pill {{
        padding: 2px 10px;
        border-radius: 999px;
        font-size: 12px;
        border: 1px solid #E6EEF7;
        background: #F7FAFC;
      }}
      .pill-green {{
        border-color: {PRIMARY}33;
        background: {PRIMARY}14;
        color: #0E6B47;
      }}
      .muted {{
        color: #6B7A90;
        font-size: 12px;
      }}
      .title-dark {{
        color: {TITLE_DARK};
        margin: 0;
      }}
      /* Fijar títulos de secciones si haces scroll (solo los h2 principales) */
      .sticky-title {{
        position: sticky;
        top: 0;
        background: {BODY_BG};
        z-index: 2;
        padding-top: 8px;
        padding-bottom: 8px;
      }}
      /* Selects y botones con acento marca */
      div[data-baseweb="select"] span {{
        color: #0A1F2E;
      }}
      .stButton>button {{
        border-radius: 10px;
        border: 1px solid #DDE7F1;
      }}
      .stButton>button:hover {{
        border-color: {PRIMARY};
      }}
      .accent {{
        color: "{PRIMARY}";
      }}
    </style>
    """, unsafe_allow_html=True)

# =========================================================
# ESTADO
# =========================================================
def init_state():
    if "current_user" not in st.session_state:
        st.session_state.current_user = "Admin"  # puedes cambiar según tu login
    if "tasks" not in st.session_state:
        st.session_state.tasks = []
    if "show_assign_for" not in st.session_state:
        st.session_state.show_assign_for = None  # task_id que está en modo asignar
    if "expanded_task_id" not in st.session_state:
        st.session_state.expanded_task_id = None
    if "flows" not in st.session_state:
        st.session_state.flows = []
    if "filters" not in st.session_state:
        st.session_state.filters = {"estado":"Todos", "busqueda":""}

def seed_example_data():
    """Crea algunos ejemplos solo si no hay datos."""
    if not st.session_state.tasks:
        now = datetime.now()
        demo = [
            {
                "id": str(uuid.uuid4()),
                "titulo": "Revisión JD - Data Engineer",
                "detalle": "Validar JD con hiring manager, stack AWS y pipelines.",
                "creado": now - timedelta(hours=6),
                "vence": (now + timedelta(days=3)).date().isoformat(),
                "estado": "Pendiente",
                "asignado": "",
                "flujo": "DE-001",
                "prioridad":"Alta",
            },
            {
                "id": str(uuid.uuid4()),
                "titulo": "Screening CVs - Backend Sr",
                "detalle": "Filtrar por Python/Go y 5+ años.",
                "creado": now - timedelta(days=1, hours=2),
                "vence": (now + timedelta(days=1)).date().isoformat(),
                "estado": "Asignada",
                "asignado": "Sup",
                "flujo": "BE-009",
                "prioridad":"Media",
            },
        ]
        st.session_state.tasks.extend(demo)

# =========================================================
# UTILIDADES
# =========================================================
def estado_pill(estado: str) -> str:
    color = {
        "Pendiente": "#9AA6B2",
        "Asignada": PRIMARY,
        "En progreso": "#0072E3",
        "Completada": "#10B981",
        "Bloqueada": "#EF4444",
    }.get(estado, "#9AA6B2")
    return f'<span class="pill" style="border-color:{color}33;background:{color}14;color:#0A2230">{estado}</span>'

def prioridad_pill(p: str) -> str:
    color = {
        "Alta": "#E11D48",
        "Media": "#F59E0B",
        "Baja": "#6B7280",
    }.get(p, "#6B7280")
    return f'<span class="pill" style="border-color:{color}33;background:{color}14;color:#0A2230">{p}</span>'

def add_task_from_flow(flujo_dict: dict):
    """Crea una tarea automáticamente al guardar un flujo."""
    t = {
        "id": str(uuid.uuid4()),
        "titulo": flujo_dict.get("nombre","Nueva tarea"),
        "detalle": flujo_dict.get("descripcion",""),
        "creado": datetime.now(),
        "vence": flujo_dict.get("fecha_compromiso") or (date.today() + timedelta(days=3)).isoformat(),
        "estado": "Pendiente",
        "asignado": "",
        "flujo": flujo_dict.get("codigo",""),
        "prioridad": flujo_dict.get("prioridad","Media"),
    }
    st.session_state.tasks.insert(0, t)  # al inicio para que se vea arriba

# =========================================================
# SIDEBAR (sin cambiar estética)
# =========================================================
def render_sidebar():
    with st.sidebar:
        st.markdown("### Tareas")
        # Filtros rápidos (texto, estado)
        st.session_state.filters["busqueda"] = st.text_input("Buscar", placeholder="Título, detalle, flujo...")
        st.session_state.filters["estado"] = st.selectbox(
            "Estado",
            ["Todos","Pendiente","Asignada","En progreso","Completada","Bloqueada"],
            index=0
        )

        st.markdown("---")
        st.markdown("**Usuario**")
        st.text_input("Nombre de usuario", value=st.session_state.current_user, key="current_user_input")
        # Sin romper nada: sincroniza si cambia
        st.session_state.current_user = st.session_state.current_user_input

        st.markdown("---")
        st.caption("Job boards")
        st.multiselect("Origen", JOB_BOARDS, default=[], key="job_boards_sel")

# =========================================================
# PESTAÑA: Publicación & Sourcing (renombrada)
# =========================================================
def tab_publicacion_sourcing():
    st.markdown('<h2 class="sticky-title">Publicación & Sourcing</h2>', unsafe_allow_html=True)
    with st.container():
        col1, col2 = st.columns([2,1])
        with col1:
            st.text_input("Título del puesto", key="pub_title", placeholder="Ej: Lead Data Engineer")
            st.text_area("Descripción breve", key="pub_desc", height=120, placeholder="Resumen del rol...")
            st.multiselect("Canales de publicación", JOB_BOARDS, key="pub_channels")
        with col2:
            st.date_input("Fecha límite de publicación", key="pub_deadline", value=date.today()+timedelta(days=7))
            st.selectbox("Tipo de empleo", ["Tiempo completo","Medio tiempo","Prácticas","Temporal","Consultoría"], key="pub_type")
            st.selectbox("Seniority", ["Junior","Semi Senior","Senior","Lead"], key="pub_sen")

        st.markdown("")
        st.button("Publicar aviso", use_container_width=True)

# =========================================================
# PESTAÑA: Flujos (al guardar -> crea tarea y la manda a “Todas las tareas”)
# =========================================================
def tab_flujos():
    st.markdown('<h2 class="sticky-title">Flujos</h2>', unsafe_allow_html=True)
    with st.form("form_flujo", clear_on_submit=True):
        col1, col2 = st.columns([2,1])
        with col1:
            nombre = st.text_input("Nombre del flujo", placeholder="Ej: Screening CVs - Data Engineer")
            descripcion = st.text_area("Descripción del flujo", height=120, placeholder="Pasos, criterios, responsables...")
            codigo = st.text_input("Código interno (opcional)", placeholder="Ej: DE-2025-001")
        with col2:
            prioridad = st.selectbox("Prioridad", ["Alta","Media","Baja"], index=1)
            fecha_compromiso = st.date_input("Fecha compromiso", value=date.today()+timedelta(days=3))
            responsable_inicial = st.selectbox("Responsable inicial (opcional)", ["","Admin","Sup","Colab"], index=0)

        submitted = st.form_submit_button("Guardar flujo", use_container_width=True)
        if submitted:
            flujo = {
                "id": str(uuid.uuid4()),
                "nombre": nombre.strip() or "Flujo sin título",
                "descripcion": descripcion.strip(),
                "codigo": codigo.strip(),
                "prioridad": prioridad,
                "fecha_compromiso": fecha_compromiso.isoformat(),
                "responsable_inicial": responsable_inicial
            }
            st.session_state.flows.insert(0, flujo)
            add_task_from_flow(flujo)
            # Si hay responsable inicial, marca la tarea como Asignada
            if responsable_inicial:
                st.session_state.tasks[0]["asignado"] = responsable_inicial
                st.session_state.tasks[0]["estado"] = "Asignada"

            st.success("✅ Flujo guardado y tarea creada en ‘Todas las tareas’. Desplázate a esa pestaña para verla.")

    # Listado simple de flujos
    if st.session_state.flows:
        st.markdown("#### Flujos recientes")
        for f in st.session_state.flows[:10]:
            st.markdown(
                f"""
                <div class="card">
                  <div class="card-header">
                    <h4 class="title-dark">{f.get('nombre')}</h4>
                    <div>
                      {prioridad_pill(f.get('prioridad','Media'))}
                    </div>
                  </div>
                  <div class="muted">Código: {f.get('codigo','-')} · Compromiso: {f.get('fecha_compromiso','-')}</div>
                  <div style="margin-top:8px;">{f.get('descripcion','')}</div>
                </div>
                """,
                unsafe_allow_html=True
            )
    else:
        st.info("Aún no has creado flujos.")

# =========================================================
# ACCIONES EN TABLA DE TAREAS
# =========================================================
def render_task_row(task, idx):
    """Render de una fila (tarjeta) de tarea con acciones."""
    t_id = task["id"]
    col1, col2, col3, col4, col5 = st.columns([3,1.2,1.2,1.6,1.6])
    with col1:
        st.markdown(f"**{task['titulo']}**")
        st.caption(f"Flujo: {task.get('flujo','-')}")
    with col2:
        st.markdown(estado_pill(task["estado"]), unsafe_allow_html=True)
    with col3:
        st.markdown(prioridad_pill(task.get("prioridad","Media")), unsafe_allow_html=True)
    with col4:
        st.markdown(f"<span class='muted'>Vence:</span> {task['vence']}", unsafe_allow_html=True)
    with col5:
        accion = st.selectbox(
            "Acciones",
            ["Selecciona…","Ver detalle","Asignar tarea","Tomar tarea","Eliminar"],
            key=f"accion_{t_id}",
            label_visibility="collapsed",
        )
        if accion == "Ver detalle":
            st.session_state.expanded_task_id = t_id
            st.session_state.show_assign_for = None
        elif accion == "Asignar tarea":
            st.session_state.show_assign_for = t_id
            st.session_state.expanded_task_id = None
        elif accion == "Tomar tarea":
            task["asignado"] = st.session_state.current_user
            task["estado"] = "En progreso"
            st.session_state.show_assign_for = None
            st.session_state.expanded_task_id = None
            st.toast("Tarea tomada.")
            st.rerun()
        elif accion == "Eliminar":
            # eliminar por id
            st.session_state.tasks = [t for t in st.session_state.tasks if t["id"] != t_id]
            st.session_state.show_assign_for = None
            st.session_state.expanded_task_id = None
            st.warning("Tarea eliminada.")
            st.rerun()

    # Bloque de asignación inline
    if st.session_state.show_assign_for == t_id:
        with st.container():
            st.markdown(
                """
                <div class="card" style="margin-top:8px;">
                  <div class="title-dark" style="font-weight:600;margin-bottom:6px;">Asignar tarea</div>
                </div>
                """,
                unsafe_allow_html=True
            )
            c1, c2, c3 = st.columns([2,2,1])
            with c1:
                nuevo_resp = st.selectbox("Responsable", ["Admin","Sup","Colab"], key=f"assign_user_{t_id}")
            with c2:
                nuevo_estado = st.selectbox("Estado", ["Asignada","En progreso","Completada","Bloqueada","Pendiente"], index=0, key=f"assign_state_{t_id}")
            with c3:
                if st.button("Guardar", key=f"btn_assign_{t_id}", use_container_width=True):
                    task["asignado"] = nuevo_resp
                    task["estado"] = nuevo_estado
                    st.session_state.show_assign_for = None
                    st.success("Cambios guardados.")
                    st.rerun()

    # Bloque de detalle expandido
    if st.session_state.expanded_task_id == t_id:
        with st.container():
            st.markdown(
                f"""
                <div class="card" style="margin-top:8px;">
                    <div class="title-dark" style="font-weight:600;">Detalle de la tarea</div>
                    <div class="muted">Creado: {task['creado'].strftime('%Y-%m-%d %H:%M')}</div>
                    <div style="margin-top:8px;">{task.get('detalle','Sin detalle')}</div>
                    <div class="muted" style="margin-top:8px;">Asignado a: {task.get('asignado') or '—'}</div>
                </div>
                """,
                unsafe_allow_html=True
            )

def filtered_tasks(tasks):
    q = (st.session_state.filters.get("busqueda") or "").strip().lower()
    estado = st.session_state.filters.get("estado","Todos")
    out = []
    for t in tasks:
        if estado != "Todos" and t["estado"] != estado:
            continue
        if q:
            blob = f"{t['titulo']} {t.get('detalle','')} {t.get('flujo','')}".lower()
            if q not in blob:
                continue
        out.append(t)
    return out

# =========================================================
# PESTAÑA: Todas las tareas (con Acciones)
# =========================================================
def tab_todas_las_tareas():
    st.markdown('<h2 class="sticky-title">Todas las tareas</h2>', unsafe_allow_html=True)

    tasks = filtered_tasks(st.session_state.tasks)

    if not tasks:
        st.info("No hay tareas con el filtro actual.")
        return

    for idx, task in enumerate(tasks):
        with st.container():
            st.markdown('<div class="card">', unsafe_allow_html=True)
            render_task_row(task, idx)
            st.markdown('</div>', unsafe_allow_html=True)

# =========================================================
# PESTAÑA: Analytics (placeholder estable, sin romper estilos)
# =========================================================
def tab_analytics():
    st.markdown('<h2 class="sticky-title">Analytics</h2>', unsafe_allow_html=True)

    # Datos básicos desde las tareas para no romper
    df = pd.DataFrame([{
        "estado": t["estado"],
        "prioridad": t.get("prioridad","Media"),
        "asignado": t.get("asignado") or "Sin asignar"
    } for t in st.session_state.tasks]) if st.session_state.tasks else pd.DataFrame(columns=["estado","prioridad","asignado"])

    if df.empty:
        st.info("Aún no hay datos para analizar.")
        return

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Tareas por estado")
        g1 = df["estado"].value_counts().reset_index()
        g1.columns = ["Estado","Cantidad"]
        fig1 = px.bar(g1, x="Estado", y="Cantidad", text="Cantidad")
        fig1.update_traces(marker_color=PRIMARY)
        st.plotly_chart(fig1, use_container_width=True, theme=None)
    with c2:
        st.subheader("Tareas por prioridad")
        g2 = df["prioridad"].value_counts().reset_index()
        g2.columns = ["Prioridad","Cantidad"]
        fig2 = px.bar(g2, x="Prioridad", y="Cantidad", text="Cantidad")
        fig2.update_traces(marker_color=PRIMARY)
        st.plotly_chart(fig2, use_container_width=True, theme=None)

    st.subheader("Asignación")
    g3 = df["asignado"].value_counts().reset_index()
    g3.columns = ["Responsable","Cantidad"]
    fig3 = px.pie(g3, names="Responsable", values="Cantidad", hole=0.5)
    fig3.update_traces(textinfo="value+label", marker=dict(line=dict(width=0)))
    st.plotly_chart(fig3, use_container_width=True, theme=None)

# =========================================================
# MAIN
# =========================================================
def main():
    st.set_page_config(page_title="SelektIA", layout="wide")
    inject_base_css()
    init_state()
    seed_example_data()

    render_sidebar()

    st.markdown(f"<h1 style='margin-top:0;'>SelektIA</h1>", unsafe_allow_html=True)

    tabs = st.tabs([
        "Publicación & Sourcing",
        "Flujos",
        "Todas las tareas",
        "Analytics",
    ])

    with tabs[0]:
        tab_publicacion_sourcing()
    with tabs[1]:
        tab_flujos()
    with tabs[2]:
        tab_todas_las_tareas()
    with tabs[3]:
        tab_analytics()

if __name__ == "__main__":
    main()
