import httpx
import os

# ✅ URL dell’API FocusMe AI (modifica se necessario)
FOCUSME_API_URL = "https://focusme-ai.mercurysurgelati.org/api/tasks"
FOCUSME_API_TOKEN = os.getenv("FOCUSME_API_TOKEN", "demo-token")  # usa variabile ambiente

async def generate_task_from_doc(result: dict, user):
    # 🎯 Payload del task
    payload = {
        "title": f"Revisione documento: {result['filename']}",
        "description": (
            f"📄 Documento: {result['filename']}\n"
            f"🧠 Classificazione: {result['classification']}\n"
            f"📆 Date: {result.get('dates', {})}\n"
            f"✍️ Firme: {result.get('signatures', [])}\n"
            f"👤 Caricato da: {user.email}"
        ),
        "category": result['classification'].lower(),
        "linked_document": result['filename'],
        "source": "docs.mercurysurgelati.org"
    }

    headers = {
        "Authorization": f"Bearer {FOCUSME_API_TOKEN}",
        "Content-Type": "application/json"
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(FOCUSME_API_URL, json=payload, headers=headers)
            response.raise_for_status()
    except Exception as e:
        print(f"[AI Task] Errore invio task a FocusMe AI: {e}") 

FOCUSME_CEO_API = os.getenv("FOCUSME_CEO_API", "https://focus.mercurysurgelati.org/api/ceo-alerts")
FOCUSME_API_TOKEN = os.getenv("FOCUSME_API_TOKEN", "demo-token")

async def send_ceo_suggestion(result: dict):
    lean = result.get("lean_check", {})
    filename = result.get("filename", "Documento sconosciuto")

    # Se tutto è ✅, non mandare nulla
    if all(value.startswith("✅") for value in lean.values()):
        return

    # Prepara la descrizione con le criticità Lean
    criticita = "\n".join([
        f"{principio}: {valore}" for principio, valore in lean.items() if not valore.startswith("✅")
    ])

    payload = {
        "title": f"💡 Suggerimento AI: Revisione documento \"{filename}\"",
        "message": f"⚠️ L’analisi Lean del documento ha rilevato criticità:\n\n{criticita}",
        "linked_document": filename,
        "source": "docs.mercurysurgelati.org"
    }

    headers = {
        "Authorization": f"Bearer {FOCUSME_API_TOKEN}",
        "Content-Type": "application/json"
    }

    try:
        async with httpx.AsyncClient() as client:
            res = await client.post(FOCUSME_CEO_API, json=payload, headers=headers)
            res.raise_for_status()
    except Exception as e:
        print(f"[CEO Suggestion] Errore invio a FocusMe AI: {e}") 

def genera_task_sblocco_su_focusme(richiesta, utente_richiedente):
    descrizione = (
        f"\U0001F9FE Richiesta accesso al documento {richiesta.document_id} da parte di {utente_richiedente.email}.\n"
        f"Motivo: {richiesta.motivo or 'Non specificato'}\n"
        f"Data richiesta: {richiesta.timestamp.strftime('%Y-%m-%d %H:%M')}"
    )
    payload = {
        "titolo": f"\U0001F4C2 Richiesta sblocco documento {richiesta.document_id}",
        "descrizione": descrizione,
        "categoria": "Richieste Documenti",
        "utente_origine": utente_richiedente.email,
        "origine": "docs.mercurysurgelati.org",
        "priorita": "media",
        "tag": ["task-sblocco"]
    }
    headers = {
        "Authorization": f"Bearer {os.getenv('FOCUSME_API_TOKEN')}"
    }
    try:
        response = httpx.post("https://focus.mercurysurgelati.org/api/task", json=payload, headers=headers, timeout=10)
        response.raise_for_status()
    except Exception as e:
        print(f"Errore invio task FocusMe: {e}") 

def crea_task_da_suggerimento(sugg, user):
    """Crea un task AI su FocusMe a partire da un suggerimento Lean.

    Args:
        sugg (AnalisiLean): Istanza suggerimento Lean.
        user (User): Utente che approva il suggerimento.
    """
    titolo = f"Miglioramento Lean – {sugg.principio}"
    descrizione = sugg.suggerimento
    categoria = "Lean"
    documento_id = sugg.documento_id

    # Funzione esistente per generare il task (da integrare con FocusMe)
    generate_task_from_doc({
        "title": titolo,
        "description": descrizione,
        "category": categoria,
        "document_id": documento_id,
        "source": "lean_checker"
    }, user) 