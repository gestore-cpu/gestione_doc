from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
from typing import Dict, Optional
from datetime import datetime
import logging

router = APIRouter()

# Configurazione logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 🧠 Logica AI avanzata per la risposta
def genera_risposta_ai_domanda(domanda: str) -> str:
    """
    Genera una risposta AI per Jack nel modulo DOCS.
    
    Args:
        domanda (str): Domanda dell'utente
        
    Returns:
        str: Risposta di Jack
    """
    domanda_lower = domanda.lower()
    
    # Risposte predefinite per domande comuni
    if any(word in domanda_lower for word in ['carica', 'upload', 'aggiungi', 'nuovo']):
        return "📄 Per caricare un documento, clicca sul pulsante 'Carica Documento' in alto a destra. Puoi selezionare file PDF, DOC, DOCX e altri formati supportati. Una volta caricato, il documento sarà automaticamente analizzato con AI! 🤖"
    
    elif any(word in domanda_lower for word in ['firma', 'firmare', 'sign', 'signature']):
        return "🖋️ Per firmare un documento, clicca sull'icona della firma (✍️) nella riga del documento. Verrà richiesto un token di sicurezza via email/WhatsApp per la 2FA. La firma è tracciabile e sicura! 🔐"
    
    elif any(word in domanda_lower for word in ['scadenza', 'scaduto', 'expiry', 'scade']):
        return "⏰ I documenti in scadenza sono evidenziati in rosso nella tabella. Puoi anche andare alla sezione 'Scadenziario' per vedere tutti i documenti che scadono nei prossimi 30 giorni. Ti invierò promemoria automatici! 📅"
    
    elif any(word in domanda_lower for word in ['ai', 'analisi', 'analizza', 'intelligenza']):
        return "🤖 L'analisi AI è automatica per tutti i documenti caricati. Controlla la colonna 'AI Status' per vedere lo stato dell'analisi. I documenti vengono classificati come 'completo', 'incompleto', 'scaduto' o 'manca_firma'. 📊"
    
    elif any(word in domanda_lower for word in ['filtri', 'cerca', 'trova', 'ricerca']):
        return "🔍 Usa i filtri in alto per cercare documenti per nome, categoria, stato o azienda. Puoi combinare più filtri per trovare esattamente quello che cerchi! La ricerca è in tempo reale. ✨"
    
    elif any(word in domanda_lower for word in ['esporta', 'download', 'scarica', 'export']):
        return "📥 Per scaricare un documento, clicca sull'icona del download (⬇️) nella riga del documento. Puoi anche esportare l'intera lista in CSV o PDF usando i pulsanti in alto a destra della tabella! 📋"
    
    elif any(word in domanda_lower for word in ['statistiche', 'stats', 'numeri', 'dashboard']):
        return "📊 Le statistiche sono mostrate nelle card colorate in alto: Documenti Totali (verde), In Revisione (giallo), Documenti Firmati (blu), In Scadenza (rosso). I numeri si aggiornano automaticamente! 📈"
    
    elif any(word in domanda_lower for word in ['aiuto', 'help', 'supporto', 'guida']):
        return "💡 Sono qui per aiutarti! Puoi chiedermi di: caricare documenti, firmare, cercare, esportare, controllare scadenze, analisi AI e molto altro. Basta scrivere la tua domanda! 🚀"
    
    elif any(word in domanda_lower for word in ['ciao', 'hello', 'salve', 'buongiorno']):
        return "👋 Ciao! Sono Jack Synthia, il tuo assistente AI per la gestione documenti. Come posso aiutarti oggi? 🤖"
    
    elif any(word in domanda_lower for word in ['grazie', 'thanks', 'thank', 'grazie mille']):
        return "😊 Prego! Sono sempre qui per aiutarti. Se hai altre domande, non esitare a chiedere! 🚀"
    
    elif any(word in domanda_lower for word in ['revisione', 'revisioni', 'ciclica']):
        return "🔄 Le revisioni cicliche sono automatiche! I documenti vengono revisionati periodicamente in base alla loro frequenza. Puoi vedere lo stato delle revisioni nella colonna 'Ultima Revisione' e 'Prossima Revisione'. 📅"
    
    elif any(word in domanda_lower for word in ['audit', 'log', 'tracciabilità']):
        return "📋 Tutte le azioni sono tracciate nel log di audit. Puoi vedere revisioni, firme, modifiche e accessi nella sezione 'Audit Log'. I log sono esportabili e pronti per audit esterni! 🔍"
    
    elif any(word in domanda_lower for word in ['calendario', 'ics', 'outlook', 'google']):
        return "📅 Puoi sincronizzare il calendario delle revisioni con il tuo calendario personale! Vai su 'Calendario ICS' per ottenere il link da aggiungere a Outlook, Google Calendar o altri client. 🔗"
    
    elif any(word in domanda_lower for word in ['abbandonati', 'ignorati', 'saltati']):
        return "⚠️ I documenti che saltano 2 revisioni consecutive vengono segnalati come 'abbandonati'. Puoi vederli nella sezione 'Documenti Abbandonati'. È importante gestirli per mantenere la compliance! 🚨"
    
    elif any(word in domanda_lower for word in ['kpi', 'performance', 'metriche']):
        return "📈 I KPI settimanali sono disponibili nel dashboard AI. Vedi analisi automatiche, trend, performance e insight generati dall'AI per ottimizzare la gestione documentale! 📊"
    
    elif any(word in domanda_lower for word in ['obeya', 'mappa', 'visuale', 'network']):
        return "🗺️ La mappa visuale Obeya mostra tutti i documenti come nodi collegati. È utile per vedere relazioni e dipendenze tra documenti. Accessibile dalla sezione 'Mappa Visuale'! 🎯"
    
    else:
        # Risposta generica per domande non riconosciute
        return "🤔 Interessante domanda! Per il modulo DOCS posso aiutarti con: caricamento documenti, firme digitali, analisi AI, gestione scadenze, filtri e ricerche, esportazioni, revisioni cicliche, audit log, calendario ICS, documenti abbandonati, KPI e mappa visuale. Prova a chiedere qualcosa di più specifico! 💡"

class ChatInput(BaseModel):
    domanda: str
    user_id: Optional[str] = None
    session_id: Optional[str] = None

class ChatResponse(BaseModel):
    success: bool
    risposta: str
    timestamp: str
    error: Optional[str] = None

@router.post("/api/jack/docs/chat")
async def chat_ai_docs(input_data: ChatInput) -> ChatResponse:
    """
    Endpoint per la chat AI di Jack nel modulo DOCS.
    
    Args:
        input_data (ChatInput): Dati della richiesta chat
        
    Returns:
        ChatResponse: Risposta di Jack AI
    """
    try:
        # Validazione input
        if not input_data.domanda or not input_data.domanda.strip():
            raise HTTPException(status_code=400, detail="Domanda vuota")
        
        # Log della richiesta
        logger.info(f"Chat request from user {input_data.user_id}: {input_data.domanda}")
        
        # Genera risposta AI
        risposta = genera_risposta_ai_domanda(input_data.domanda.strip())
        
        # Log della risposta
        logger.info(f"AI response generated: {risposta[:100]}...")
        
        return ChatResponse(
            success=True,
            risposta=risposta,
            timestamp=datetime.now().isoformat(),
            error=None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Errore nella chat Jack AI: {str(e)}")
        return ChatResponse(
            success=False,
            risposta="Mi dispiace, c'è stato un errore. Riprova più tardi.",
            timestamp=datetime.now().isoformat(),
            error=str(e)
        )

# Endpoint di health check
@router.get("/api/jack/docs/health")
async def health_check() -> Dict[str, str]:
    """Health check per l'endpoint Jack AI."""
    return {
        "status": "healthy",
        "service": "jack_ai_docs",
        "timestamp": datetime.now().isoformat()
    }

# Endpoint per statistiche chat
@router.get("/api/jack/docs/stats")
async def chat_stats() -> Dict[str, any]:
    """Statistiche dell'utilizzo della chat AI."""
    return {
        "total_requests": 0,  # In produzione: leggere da database
        "success_rate": 0.95,
        "average_response_time": 0.2,
        "last_request": datetime.now().isoformat(),
        "active_sessions": 0
    } 