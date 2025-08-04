from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from datetime import datetime, time
import random

router = APIRouter()

def genera_messaggio_jack(pagina: str, user_role: str, kpi_data: dict = None) -> dict:
    """
    Genera messaggi automatici di Jack Synthia basati su:
    - Pagina corrente
    - Ruolo utente
    - Orario della giornata
    - Dati KPI (se disponibili)
    """
    
    # Orario corrente per personalizzazione
    ora_corrente = datetime.now().hour
    
    # Messaggi base per ruolo
    messaggi_ceo = {
        "dashboard_ceo": [
            "🌟 Buongiorno CEO! Pronto per guidare la giornata? Ho analizzato i KPI e ho alcuni suggerimenti strategici.",
            "🎯 Benvenuto nella tua dashboard! Ho identificato 3 priorità critiche che richiedono la tua attenzione.",
            "🧠 Buongiorno! I dati mostrano un trend positivo. Vuoi che analizzi le opportunità di crescita?"
        ],
        "focus_planner": [
            "⏰ È il momento perfetto per pianificare il Deep Work! Hai già identificato i blocchi di tempo?",
            "🎯 Pianificazione strategica in corso! Ti suggerisco di dedicare 2 ore al mattino per le priorità critiche.",
            "🧠 Ottimo momento per la pianificazione! Ho notato che i tuoi picchi di produttività sono tra le 9-11."
        ],
        "task_manager": [
            "📋 Hai 5 task in corso e 2 in ritardo. Vuoi che ti aiuti a riorganizzare le priorità?",
            "✅ Task management time! Ho identificato 3 task che possono essere completati oggi.",
            "🎯 Gestione task ottimale! Ti suggerisco di concentrarti sui task ad alto impatto."
        ],
        "docs_overview": [
            "📄 Gestione documentale! Ho rilevato 3 documenti critici che richiedono la tua attenzione.",
            "🔍 Panoramica documenti completa! Ci sono 2 documenti scaduti che necessitano aggiornamento.",
            "📊 Stato documenti: 85% completi. Vuoi che analizzi le lacune da colmare?"
        ],
        "qms_overview": [
            "🏆 Sistema Qualità! Tutti i processi sono conformi. Vuoi un'analisi dettagliata?",
            "📈 KPI Qualità in crescita! Ho identificato 2 aree di miglioramento.",
            "🎯 Sistema Qualità ottimale! Pronto per l'audit esterno."
        ]
    }
    
    messaggi_admin = {
        "dashboard_admin": [
            "👨‍💼 Buongiorno Admin! Sistema operativo al 100%. Tutto sotto controllo.",
            "🔧 Dashboard amministrativa attiva! Ho rilevato 2 notifiche che richiedono attenzione.",
            "📊 Gestione sistema ottimale! Tutti i moduli funzionano correttamente."
        ],
        "docs_overview": [
            "📄 Gestione documenti! 3 documenti in attesa di approvazione.",
            "🔍 Controllo documentale! Tutti i documenti sono aggiornati.",
            "📋 Sistema documentale efficiente! Nessuna criticità rilevata."
        ]
    }
    
    messaggi_user = {
        "dashboard_user": [
            "👋 Buongiorno! Pronto per una giornata produttiva?",
            "🎯 Benvenuto! Hai 3 task da completare oggi.",
            "🌟 Buongiorno! Il sistema è ottimizzato per la tua produttività."
        ],
        "focus_planner": [
            "⏰ Pianificazione personale! Ti suggerisco di iniziare con i task più importanti.",
            "🎯 Tempo di pianificare! Organizza la tua giornata per massimizzare l'efficienza.",
            "🧠 Pianificazione intelligente! Considera i tuoi picchi di energia."
        ]
    }
    
    # Selezione messaggi in base al ruolo
    if user_role.upper() == "CEO":
        messaggi_disponibili = messaggi_ceo.get(pagina, messaggi_ceo["dashboard_ceo"])
    elif user_role.upper() in ["ADMIN", "AMMINISTRATORE"]:
        messaggi_disponibili = messaggi_admin.get(pagina, messaggi_admin["dashboard_admin"])
    else:
        messaggi_disponibili = messaggi_user.get(pagina, messaggi_user["dashboard_user"])
    
    # Personalizzazione in base all'orario
    if 6 <= ora_corrente < 12:
        saluto = "🌅 Buongiorno"
    elif 12 <= ora_corrente < 18:
        saluto = "☀️ Buon pomeriggio"
    elif 18 <= ora_corrente < 22:
        saluto = "🌆 Buonasera"
    else:
        saluto = "🌙 Buonanotte"
    
    # Selezione messaggio casuale
    messaggio_base = random.choice(messaggi_disponibili)
    
    # Aggiunta di informazioni contestuali se disponibili
    if kpi_data:
        if kpi_data.get("task_in_ritardo", 0) > 0:
            messaggio_base += f" ⚠️ Hai {kpi_data['task_in_ritardo']} task in ritardo."
        if kpi_data.get("documenti_critici", 0) > 0:
            messaggio_base += f" 📄 Ci sono {kpi_data['documenti_critici']} documenti critici."
    
    # Generazione azione contestuale
    azione_url = None
    azione_testo = None
    
    if pagina == "focus_planner":
        azione_url = "/focus/planner"
        azione_testo = "🎯 Pianifica Ora"
    elif pagina == "task_manager":
        azione_url = "/focus/tasks"
        azione_testo = "📋 Gestisci Task"
    elif pagina == "docs_overview":
        azione_url = "/admin/docs"
        azione_testo = "📄 Verifica Documenti"
    elif pagina == "qms_overview":
        azione_url = "/qms/dashboard"
        azione_testo = "🏆 Controllo Qualità"
    
    return {
        "messaggio": messaggio_base,
        "azione_url": azione_url,
        "azione_testo": azione_testo,
        "timestamp": datetime.now().isoformat(),
        "pagina": pagina,
        "user_role": user_role
    }

@router.get("/synthia/ai/evento/{evento}")
async def messaggio_automatico(evento: str, user_role: str = "CEO"):
    """
    Genera messaggi automatici di Jack Synthia basati sull'evento
    """
    
    # Mappa eventi -> pagine
    pagina_map = {
        "login": "dashboard_ceo",
        "apertura_planner": "focus_planner", 
        "apertura_task": "task_manager",
        "apertura_docs": "docs_overview",
        "apertura_qms": "qms_overview",
        "apertura_review": "review_ai",
        "apertura_ceo": "dashboard_ceo",
        "apertura_admin": "dashboard_admin",
        "apertura_user": "dashboard_user"
    }
    
    pagina = pagina_map.get(evento, "dashboard_ceo")
    
    # Dati KPI simulati (in futuro verranno dal database)
    fake_kpi_data = {
        "task_in_ritardo": random.randint(0, 3),
        "documenti_critici": random.randint(0, 5),
        "performance_score": random.randint(70, 95)
    }
    
    try:
        messaggio = genera_messaggio_jack(pagina, user_role, fake_kpi_data)
        return JSONResponse(content=messaggio)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Errore nella generazione messaggio: {str(e)}")

@router.get("/synthia/ai/evento/contesto/{pagina}")
async def messaggio_contesto(pagina: str, user_role: str = "CEO"):
    """
    Genera messaggi basati sul contesto della pagina corrente
    """
    return await messaggio_automatico(f"apertura_{pagina}", user_role)

@router.get("/synthia/ai/evento/orario")
async def messaggio_orario(user_role: str = "CEO"):
    """
    Genera messaggi basati sull'orario della giornata
    """
    ora_corrente = datetime.now().hour
    
    if 6 <= ora_corrente < 9:
        evento = "mattina_precoce"
    elif 9 <= ora_corrente < 12:
        evento = "mattina"
    elif 12 <= ora_corrente < 15:
        evento = "pomeriggio_precoce"
    elif 15 <= ora_corrente < 18:
        evento = "pomeriggio"
    elif 18 <= ora_corrente < 22:
        evento = "sera"
    else:
        evento = "notte"
    
    return await messaggio_automatico(evento, user_role) 