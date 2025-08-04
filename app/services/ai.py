import openai

def ai_filter_documents(query: str, documents, user):
    """
    Simulazione AI: restituisce gli ID dei documenti rilevanti per la query.
    (In produzione, connettere a OpenAI o altro LLM)
    """
    query_lower = query.lower()
    results = []

    for doc in documents:
        # Simulazione: cerca nella stringa composta
        text = f"{doc.original_filename} {doc.company.name if doc.company else ''} {doc.department.name if doc.department else ''}".lower()
        if query_lower in text:
            if user.role == "admin" or (doc.company in user.companies and doc.department in user.departments):
                results.append(doc.id)
    return results

def classify_document(content: str) -> str:
    """Classifica un documento in base al contenuto in una delle categorie: Qualità, Service, Formazione, R&D, Altro.

    Args:
        content (str): Il testo del documento da classificare.

    Returns:
        str: La categoria assegnata dal modello AI.
    """
    if len(content) > 3000:
        content = content[:3000]

    prompt = (
        "Leggi il seguente documento e restituisci una delle seguenti categorie:\n"
        "Qualità, Service, Formazione, R&D, Altro.\n\n"
        f"Documento:\n{content}\n\n"
        "Categoria:"
    )

    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "Classifica i documenti aziendali in base al contenuto."},
            {"role": "user", "content": prompt}
        ],
        temperature=0,
        max_tokens=10
    )

    return response.choices[0].message["content"].strip()

from app.models.richiesta_sblocco import RichiestaSblocco

def openai_chat(prompt: str) -> str:
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "Sei un assistente AI che analizza pattern anomali nelle richieste di accesso a documenti aziendali."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.2,
        max_tokens=400
    )
    return response.choices[0].message["content"].strip()

def analizza_richieste_ai(db) -> str:
    richieste = db.query(RichiestaSblocco).order_by(RichiestaSblocco.timestamp.desc()).limit(100).all()
    raw_data = "\n".join([
        f"{r.timestamp} | {r.user_email} | doc:{r.document_id} | stato:{r.stato} | motivo:{r.motivo or '-'}"
        for r in richieste
    ])
    prompt = (
        "Sei un assistente AI che analizza pattern anomali nelle richieste di accesso a documenti aziendali.\n"
        "Ecco i dati recenti:\n\n"
        f"{raw_data}\n\n"
        "Fornisci un elenco puntato con:\n"
        "- Attività sospette\n"
        "- Utenti che fanno troppe richieste\n"
        "- Documenti frequentemente bloccati\n"
        "- Suggerimenti per l’amministratore"
    )
    risposta = openai_chat(prompt)
    return risposta 