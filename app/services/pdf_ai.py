import re
import openai
import json
from datetime import datetime

def classify_document(content: str) -> str:
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

def extract_dates(content: str) -> dict:
    import re
    import openai
    import json
    # 1. Estrai tutte le date (italiane o ISO)
    date_pattern = r"\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}-\d{2}-\d{2})\b"
    found_dates = re.findall(date_pattern, content)
    if not found_dates:
        return {}
    # 2. Prompt per AI
    prompt = (
        "Nel seguente testo sono state trovate queste date:\n"
        f"{found_dates}\n\n"
        "Associa ogni data a una delle seguenti categorie se possibile:\n"
        "- Data Emissione\n- Data Scadenza\n- Data Firma\n- Altro\n\n"
        f"Testo:\n{content[:2000]}\n\n"
        "Rispondi come JSON, esempio:\n"
        "{ \"2025-05-01\": \"Data Emissione\", \"2025-06-30\": \"Data Scadenza\" }"
    )
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "Classifica le date estratte da documenti aziendali."},
                {"role": "user", "content": prompt}
            ],
            temperature=0,
            max_tokens=300
        )
        return json.loads(response.choices[0].message["content"])
    except Exception as e:
        return {"error": f"Impossibile interpretare la risposta AI: {str(e)}"} 

def detect_signatures(content: str) -> list:
    signature_keywords = [
        r"firma\s*[:\-]?", 
        r"firmato da", 
        r"sig\.?\s*[A-Z][a-z]+", 
        r"dott\.?\s*[A-Z][a-z]+", 
        r"signed by", 
        r"signature", 
        r"firma digitale", 
        r"certificato.*CN="
    ]

    found_signatures = []

    for pattern in signature_keywords:
        matches = re.findall(pattern, content, flags=re.IGNORECASE)
        if matches:
            found_signatures.extend(matches)

    return list(set(found_signatures)) if found_signatures else [] 

async def analyze_document(file):
    content = await extract_text_from_pdf(file)
    summary = generate_summary(content)
    classification = classify_document(content)
    key_dates = extract_dates(content)
    signatures = detect_signatures(content)
    return {
        "summary": summary,
        "classification": classification,
        "dates": key_dates,
        "signatures": signatures,
        "filename": file.filename,
        "content": content
    } 

def generate_filename_ai(content: str, user) -> str:
    prompt = (
        "Leggi questo contenuto di un documento aziendale e indica un oggetto sintetico, "
        "utile per nominarlo in modo archivistico (es. 'procedura_sicurezza', 'istruzioni_macchine').\n"
        "Usa massimo 3 parole, in snake_case.\n\n"
        f"Contenuto:\n{content[:3000]}\n\n"
        "Rispondi solo con l’oggetto."
    )

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "Genera nomi sintetici e coerenti per documenti aziendali."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            max_tokens=30
        )

        oggetto = response.choices[0].message["content"].strip().replace(" ", "_").lower()

        nome = user.first_name[:3].lower()
        cognome = user.last_name[:3].lower()
        data = datetime.now().strftime("%Y%m%d")

        filename = f"{oggetto}-{nome}-{cognome}-{data}-v1.pdf"
        return filename

    except Exception as e:
        return f"errore-nomefile-{datetime.now().strftime('%Y%m%d')}.pdf" 

def generate_storage_path(content: str, user) -> dict:
    """
    Restituisce un dizionario con area, azienda, reparti → per costruire il path e assegnare permessi.
    """
    prompt = (
        "Analizza questo documento e indica:\n"
        "- L’area aziendale (es. Qualità, R&D, Service, Formazione, Altro)\n"
        "- Il nome dell’azienda (es. Mercury, Margarita, ecc.)\n"
        "- Uno o più reparti coinvolti (Produzione, Logistica, Manutenzione, ecc.)\n"
        "Rispondi in formato JSON:\n"
        '{ "area": "Qualità", "azienda": "Mercury", "reparti": ["Produzione", "Logistica"] }'
    )

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "Sei un assistente aziendale che analizza i documenti per organizzarli."},
                {"role": "user", "content": prompt + "\n\nContenuto:\n" + content[:3000]}
            ],
            temperature=0.2,
            max_tokens=200
        )

        import json
        return json.loads(response.choices[0].message["content"])

    except Exception:
        return {"area": "Altro", "azienda": "Mercury", "reparti": ["NonDefinito"]} 