from app.models.log import LogAttivitaDocumento
import openai

def analizza_log_ai(db):
    # Estrai ultimi 500 log
    logs = db.query(LogAttivitaDocumento).order_by(LogAttivitaDocumento.timestamp.desc()).limit(500).all()

    testo_log = "\n".join(
        f"{log.timestamp} - {log.azione} - utente {log.user_id} - documento {log.document_id}" for log in logs
    )

    prompt = (
        "Analizza questi log aziendali e identifica:\n"
        "- attività sospette o rischiose\n"
        "- comportamenti da migliorare (es. scarichi notturni, ripetuti)\n"
        "- suggerimenti di sicurezza e organizzazione\n\n"
        f"{testo_log[:3000]}"
    )

    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "Sei un analista di sicurezza e ottimizzazione aziendale."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.2,
        max_tokens=500
    )
    
    return response.choices[0].message["content"].strip() 