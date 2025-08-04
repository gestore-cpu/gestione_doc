import httpx
import os
from app.models import DocumentoAnalizzato
from app.services.notifiche_ai import invia_notifica_ai

FOCUSME_OBEYA_URL = os.getenv("FOCUSME_OBEYA_URL", "https://focus.mercurysurgelati.org/api/obeya/sync")
FOCUSME_API_TOKEN = os.getenv("FOCUSME_API_TOKEN")

async def sync_with_focusme_ai(documento: DocumentoAnalizzato):
    if not FOCUSME_API_TOKEN:
        print("⚠️ Token FocusMe AI mancante.")
        return

    payload = {
        "titolo": f"Documento strategico: {documento.nome_file}",
        "descrizione": f"{documento.ai_summary}\n\nNote: documento analizzato automaticamente con classificazione AI.",
        "collegamento": {
            "id_doc": documento.id,
            "qr_code": documento.qr_code_url
        },
        "area": documento.classificazione_ai,
        "tag": ["obeya", "auto-sync", documento.classificazione_ai.lower()] if documento.classificazione_ai else ["obeya", "auto-sync"]
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                FOCUSME_OBEYA_URL,
                json=payload,
                headers={"Authorization": f"Bearer {FOCUSME_API_TOKEN}"}
            )
            if response.status_code == 200:
                print(f"✅ Documento {documento.id} sincronizzato su Obeya.")
                documento.synced = True  # se usi un campo booleano
            else:
                print(f"❌ Sync fallita ({response.status_code}): {response.text}")
                await invia_notifica_ai(ceo_utente, f"❌ Sync con FocusMe Obeya fallito per documento {documento.id}", "Sync Obeya Fallito")
    except Exception as e:
        print(f"❌ Errore nella sincronizzazione Obeya: {e}") 