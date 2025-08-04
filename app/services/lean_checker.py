import openai
from app.services.notifiche_ai import invia_notifica_ai

def check_lean_principles(content: str) -> dict:
    if len(content) > 4000:
        content = content[:4000]

    prompt = (
        "Leggi questo contenuto aziendale e valuta se rispetta i seguenti 7 principi Lean "
        "ispirati al Toyota Production System. Per ciascuno, rispondi con uno di questi tag:\n"
        "✅ Se è rispettato\n⚠️ Se è parzialmente rispettato\n❌ Se è assente\n"
        "Includi una breve nota esplicativa per ogni principio.\n\n"
        "Principi Lean:\n"
        "1. Valore per il cliente\n"
        "2. Eliminazione degli sprechi (Muda)\n"
        "3. Flusso continuo\n"
        "4. Sistema pull\n"
        "5. Miglioramento continuo (Kaizen)\n"
        "6. Standardizzazione\n"
        "7. Coinvolgimento delle persone\n\n"
        f"Contenuto:\n{content}\n\n"
        "Rispondi nel seguente formato JSON:\n"
        "{\n"
        "  \"Valore per il cliente\": \"✅ Documento utile per…\",\n"
        "  \"Eliminazione sprechi\": \"⚠️ Contiene passaggi ripetitivi…\",\n"
        "  …\n"
        "}"
    )

    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "Sei un esperto di Lean Management. Analizza i documenti aziendali secondo i 7 principi TPS."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.2,
        max_tokens=600
    )

    import json
    try:
        return json.loads(response.choices[0].message["content"])
    except Exception as e:
        return {"error": f"Errore nel parsing JSON AI: {e}"} 