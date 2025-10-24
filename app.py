rows, file_store = [], {}

if files:
    for f in files:
        data = f.read()  # guardo bytes para luego mostrar el PDF
        file_store[f.name] = {"bytes": data, "type": f.type}

        # texto para scoring
        if f.type == "text/plain":
            raw = data.decode("utf-8", errors="ignore")
        else:
            raw = pdf_to_text(BytesIO(data))

        score, reason = score_candidate(raw, jd_keywords)
        rows.append({
            "Name": f.name.replace(".pdf","").replace("_"," ").title(),
            "FileName": f.name,
            "Score": score,
            "Reasons": reason
        })

    df = pd.DataFrame(rows).sort_values("Score", ascending=False)
