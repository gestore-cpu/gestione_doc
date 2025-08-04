def ai_suggerisci_documenti(user, all_documents):
    """
    Suggerisce documenti potenzialmente utili all’utente.
    Simula l’analisi AI sullo storico dell’utente.
    """
    recent_keywords = []

    for req in user.access_requests:
        if req.status == "approved":
            recent_keywords.append(req.document.original_filename.lower())
            if req.document.company:
                recent_keywords.append(req.document.company.name.lower())
            if req.document.department:
                recent_keywords.append(req.document.department.name.lower())

    suggested = []
    for doc in all_documents:
        if doc.id in [r.document_id for r in user.access_requests if r.status == "approved"]:
            continue  # già suggerito / visto
        score = sum(1 for word in recent_keywords if word in doc.original_filename.lower())
        if score > 0:
            suggested.append((doc, score))

    suggested.sort(key=lambda tup: tup[1], reverse=True)
    return [doc for doc, _ in suggested[:5]]

def ai_suggerisci_documenti_nascosti(user, all_documents):
    """
    Suggerisce documenti a cui l’utente NON ha accesso diretto,
    ma che potrebbero essergli utili.
    """
    recent_keywords = []
    for req in user.access_requests:
        if req.status == "approved":
            recent_keywords.append(req.document.original_filename.lower())
            if req.document.company:
                recent_keywords.append(req.document.company.name.lower())
            if req.document.department:
                recent_keywords.append(req.document.department.name.lower())

    # ID dei documenti già accessibili
    allowed_ids = set()
    if user.role == "admin":
        allowed_ids = {doc.id for doc in all_documents}
    else:
        allowed_ids |= {doc.id for doc in all_documents if (
            doc.company in user.companies and doc.department in user.departments
        )}
        from models import AccessRequest, db
        approved = db.session.query(AccessRequest.document_id).filter_by(user_id=user.id, status="approved").all()
        allowed_ids |= {doc_id for doc_id, in approved}

    suggestions = []
    for doc in all_documents:
        if doc.id in allowed_ids:
            continue
        text = f"{doc.original_filename} {doc.company.name if doc.company else ''} {doc.department.name if doc.department else ''}".lower()
        score = sum(1 for kw in recent_keywords if kw in text)
        if score > 0:
            suggestions.append((doc, score))

    suggestions.sort(key=lambda tup: tup[1], reverse=True)
    return [doc for doc, _ in suggestions[:5]] 