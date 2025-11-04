def _seed_example_if_empty():
    """
    Carga un candidato/tarea de ejemplo SOLO si la tienda está vacía.
    No requiere reportlab. Si no hay PDF demo, el visor simplemente mostrará el mensaje.
    """
    if store["candidates"]:
        return

    demo_jd = """Resumen del puesto:
- Brindar soporte administrativo integral (documentación, coordinación con proveedores, control de caja chica).
- Excel intermedio/avanzado, Word, PowerPoint.
- Atención al cliente, logística ligera, reportes y trabajo en equipo.
Requisitos:
- Puntualidad y excelente presentación personal.
- Deseable experiencia en estaciones de servicio o retail.
"""

    # Intentamos crear un PDF de demo solo si existe reportlab; si no, dejamos vacío.
    pdf_bytes = b""
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import A4
        buf = io.BytesIO()
        c = canvas.Canvas(buf, pagesize=A4)
        c.setFont("Helvetica", 12)
        c.drawString(72, 800, "CV Demo - SelektIA")
        c.drawString(72, 780, "Experiencia: Cajero y atención al cliente (3 años).")
        c.drawString(72, 760, "Habilidades: Excel, Word, puntualidad, presentación personal, orden y limpieza.")
        c.save()
        pdf_bytes = buf.getvalue()
    except Exception:
        # Sin reportlab: seguimos sin PDF (el visor lo manejará).
        pdf_bytes = b""

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
        "cv_bytes_b64": base64.b64encode(pdf_bytes).decode("utf-8") if pdf_bytes else "",
        "cv_name": "cv_demo.pdf" if pdf_bytes else "cv_pendiente.pdf",
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
