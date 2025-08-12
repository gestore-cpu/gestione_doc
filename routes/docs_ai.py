"""
Route FastAPI per l'analisi AI dei documenti.
Integrazione con OpenAI/GPT per analisi intelligente dell'utilizzo documentale.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, desc
from typing import List, Dict, Any
from datetime import datetime, timedelta
import logging
import os

# Import dei modelli e servizi esistenti
from models import (
    Document, Department, User, LogInvioPDF, LetturaPDF, 
    FirmaDocumento, DownloadLog, DocumentSignature
)
from extensions import db
from services.document_analytics_service import DocumentAnalyticsService
from services.ai_document_analysis_service import AIDocumentAnalysisService
from decorators import admin_required

logger = logging.getLogger(__name__)

# Router FastAPI
router = APIRouter(prefix="/docs/ai", tags=["AI Documenti"])


def get_db():
    """
    Dependency per ottenere la sessione del database.
    """
    return db.session


@router.get("/analizza_utilizzo")
def analizza_utilizzo_documenti(db: Session = Depends(get_db)):
    """
    Analizza l'utilizzo dei documenti per reparto tramite AI.
    
    Args:
        db: Sessione del database
        
    Returns:
        dict: Report AI dell'analisi documenti
    """
    try:
        logger.info("🤖 Avvio analisi AI utilizzo documenti...")
        
        # 1. Raccogli i dati aggregati per reparto e documento
        risultati = []
        
        # Query per ottenere tutti i reparti
        reparti = db.query(Department).all()
        
        for reparto in reparti:
            # Query per documenti del reparto
            documenti = (
                db.query(Document)
                .filter(Document.department_id == reparto.id)
                .all()
            )
            
            for doc in documenti:
                # Conta firme per questo documento
                firme = (
                    db.query(func.count(FirmaDocumento.id))
                    .filter(FirmaDocumento.document_id == doc.id)
                    .scalar()
                )
                
                # Conta download per questo documento
                download = (
                    db.query(func.count(DownloadLog.id))
                    .filter(DownloadLog.document_id == doc.id)
                    .scalar()
                )
                
                # Conta letture per questo documento
                letture = (
                    db.query(func.count(LetturaPDF.id))
                    .filter(LetturaPDF.document_id == doc.id)
                    .scalar()
                )
                
                # Ottieni ultima firma per versione
                ultima_firma = (
                    db.query(FirmaDocumento)
                    .filter(FirmaDocumento.document_id == doc.id)
                    .order_by(FirmaDocumento.timestamp.desc())
                    .first()
                )
                
                # Ottieni ultima lettura
                ultima_lettura = (
                    db.query(LetturaPDF)
                    .filter(LetturaPDF.document_id == doc.id)
                    .order_by(LetturaPDF.timestamp.desc())
                    .first()
                )
                
                # Calcola anomalie
                anomalie = []
                if download > 0 and letture == 0:
                    anomalie.append("Scaricato ma non letto")
                if letture > 0 and firme == 0:
                    anomalie.append("Letto ma non firmato")
                if download > 0 and letture == 0 and firme == 0:
                    anomalie.append("Documento ignorato")
                
                # Determina stato compliance
                if firme > 0:
                    stato_compliance = "Compliant"
                elif letture > 0:
                    stato_compliance = "In Attesa Firma"
                elif download > 0:
                    stato_compliance = "Scaricato"
                else:
                    stato_compliance = "Non Utilizzato"
                
                risultati.append({
                    "reparto": reparto.name,
                    "documento": doc.title,
                    "uploader": doc.uploader_email,
                    "data_creazione": doc.created_at.strftime('%d/%m/%Y') if doc.created_at else "N/A",
                    "versione_attuale": "1.0",  # Placeholder - da implementare se necessario
                    "versione_usata": "1.0",    # Placeholder - da implementare se necessario
                    "firme": firme,
                    "download": download,
                    "letture": letture,
                    "ultima_firma": ultima_firma.timestamp.strftime('%d/%m/%Y %H:%M') if ultima_firma else None,
                    "ultima_lettura": ultima_lettura.timestamp.strftime('%d/%m/%Y %H:%M') if ultima_lettura else None,
                    "stato_compliance": stato_compliance,
                    "anomalie": anomalie,
                    "anomalie_count": len(anomalie)
                })
        
        # 2. Costruisci il prompt per l'AI
        prompt = _costruisci_prompt_ai(risultati)
        
        # 3. Chiamata al modello AI
        risposta_ai = _call_ai_model(prompt)
        
        # 4. Prepara la risposta
        response_data = {
            "success": True,
            "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "documenti_analizzati": len(risultati),
            "reparti_coinvolti": len(set(r['reparto'] for r in risultati)),
            "report": risposta_ai,
            "dati_bruti": risultati,
            "statistiche": _calcola_statistiche_rapide(risultati)
        }
        
        logger.info(f"✅ Analisi AI completata - {len(risultati)} documenti analizzati")
        return response_data
        
    except Exception as e:
        logger.error(f"❌ Errore nell'analisi AI utilizzo documenti: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Errore nell'analisi AI: {str(e)}"
        )


def _costruisci_prompt_ai(risultati: List[Dict[str, Any]]) -> str:
    """
    Costruisce il prompt per l'AI basato sui dati dei documenti.
    
    Args:
        risultati: Lista dei dati documenti
        
    Returns:
        str: Prompt formattato per l'AI
    """
    prompt = """Sei un esperto analista di gestione qualità e sicurezza aziendale. 
Analizza l'utilizzo dei documenti nei reparti e fornisci un report dettagliato.

DATI DI UTILIZZO DOCUMENTI:

"""
    
    # Raggruppa per reparto per una migliore analisi
    reparti_data = {}
    for r in risultati:
        reparto = r['reparto']
        if reparto not in reparti_data:
            reparti_data[reparto] = []
        reparti_data[reparto].append(r)
    
    # Aggiungi dati per reparto
    for reparto, docs in reparti_data.items():
        prompt += f"\n📊 REPARTO: {reparto}\n"
        prompt += "=" * 50 + "\n"
        
        for doc in docs:
            prompt += f"""
📄 Documento: {doc['documento']}
   • Uploader: {doc['uploader']}
   • Data creazione: {doc['data_creazione']}
   • Download: {doc['download']}
   • Letture: {doc['letture']}
   • Firme: {doc['firme']}
   • Stato compliance: {doc['stato_compliance']}
   • Ultima firma: {doc['ultima_firma'] or 'N/A'}
   • Ultima lettura: {doc['ultima_lettura'] or 'N/A'}
   • Anomalie: {', '.join(doc['anomalie']) if doc['anomalie'] else 'Nessuna'}
"""
    
    prompt += """

ANALISI RICHIESTA:

1. **Osservazioni Generali:**
   - Identifica pattern di utilizzo per reparto
   - Evidenzia differenze tra reparti virtuosi e problematici
   - Analizza la compliance generale

2. **Rischi e Problemi:**
   - Documenti non utilizzati o sottoutilizzati
   - Reparti con bassa compliance
   - Anomalie specifiche rilevate
   - Problemi di formazione o comunicazione

3. **Anomalie Critiche:**
   - Documenti scaricati ma non letti
   - Documenti letti ma non firmati
   - Reparti che ignorano documenti importanti
   - Versioni obsolete o non aggiornate

4. **Suggerimenti di Miglioramento:**
   - Formazione specifica per reparti carenti
   - Procedure di reminder automatici
   - Obbligo di firma per documenti critici
   - Allineamento versioni e invalidazione firme obsolete
   - Follow-up per compliance

5. **Priorità di Intervento:**
   - Situazioni critiche da risolvere entro 24h
   - Problemi di compliance da monitorare
   - Opportunità di miglioramento
   - Raccomandazioni per la direzione

Fornisci un report strutturato, pratico e actionable per l'admin qualità.
"""
    
    return prompt


def _call_ai_model(prompt: str) -> str:
    """
    Chiama il modello AI (OpenAI/GPT) per l'analisi.
    
    Args:
        prompt: Prompt da inviare all'AI
        
    Returns:
        str: Risposta dell'AI
    """
    try:
        # Controlla se OpenAI è configurato
        openai_api_key = os.getenv('OPENAI_API_KEY')
        
        if not openai_api_key:
            logger.warning("⚠️ OpenAI API key non configurata, usando analisi automatica")
            return _analisi_automatica_fallback(prompt)
        
        # Import OpenAI solo se necessario
        import openai
        openai.api_key = openai_api_key
        
        # Chiamata a OpenAI
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {
                    "role": "system", 
                    "content": "Sei un esperto analista di gestione qualità e sicurezza aziendale. Fornisci analisi pratiche e actionable."
                },
                {
                    "role": "user", 
                    "content": prompt
                }
            ],
            temperature=0.3,
            max_tokens=1500,
        )
        
        return response.choices[0].message["content"]
        
    except ImportError:
        logger.warning("⚠️ OpenAI non installato, usando analisi automatica")
        return _analisi_automatica_fallback(prompt)
    except Exception as e:
        logger.error(f"❌ Errore nella chiamata OpenAI: {str(e)}")
        return _analisi_automatica_fallback(prompt)


def _analisi_automatica_fallback(prompt: str) -> str:
    """
    Analisi automatica di fallback quando OpenAI non è disponibile.
    
    Args:
        prompt: Prompt originale (non utilizzato in questo caso)
        
    Returns:
        str: Analisi automatica basata su regole
    """
    try:
        # Usa il servizio AI esistente
        risultato_ai = AIDocumentAnalysisService.analizza_documenti_con_ai()
        
        if not risultato_ai['success']:
            return "❌ Impossibile completare l'analisi AI. Verificare la configurazione."
        
        # Genera report automatico
        report = f"""
🤖 REPORT ANALISI AUTOMATICA DOCUMENTI
Generato il: {risultato_ai['timestamp']}

📊 PANORAMICA GENERALE
- Documenti analizzati: {risultato_ai['documenti_analizzati']}
- Compliance rate generale: {risultato_ai['statistiche_ai']['compliance_rate_generale']}%

🚨 ALERT CRITICI ({len(risultato_ai['analisi_automatica']['alert_critici'])})
"""
        
        for alert in risultato_ai['analisi_automatica']['alert_critici']:
            report += f"""
• {alert['tipo']}
  - Documento: {alert['documento']}
  - Reparto: {alert['reparto']}
  - Azione: {alert['azione']}
"""
        
        report += f"""
🏆 REPARTI VIRTUOSI ({len(risultato_ai['analisi_automatica']['reparti_virtuosi'])})
"""
        
        for reparto in risultato_ai['analisi_automatica']['reparti_virtuosi']:
            report += f"""
• {reparto['reparto']} - Compliance: {reparto['compliance_rate']}%
"""
        
        report += f"""
⚠️ REPARTI PROBLEMATICI ({len(risultato_ai['analisi_automatica']['reparti_problematici'])})
"""
        
        for reparto in risultato_ai['analisi_automatica']['reparti_problematici']:
            report += f"""
• {reparto['reparto']} - Compliance: {reparto['compliance_rate']}%
  - Anomalie: {reparto['anomalie']}
  - Azione: {reparto['azione']}
"""
        
        report += f"""
💡 RACCOMANDAZIONI
"""
        
        for racc in risultato_ai['analisi_automatica']['raccomandazioni']:
            report += f"""
• {racc['tipo']}: {racc['descrizione']}
  - Azione: {racc['azione']}
"""
        
        report += f"""

---
*Report generato automaticamente dal sistema AI di analisi documenti*
"""
        
        return report
        
    except Exception as e:
        logger.error(f"❌ Errore nell'analisi automatica: {str(e)}")
        return f"❌ Errore nell'analisi automatica: {str(e)}"


def _calcola_statistiche_rapide(risultati: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Calcola statistiche rapide per la risposta API.
    
    Args:
        risultati: Lista dei dati documenti
        
    Returns:
        dict: Statistiche rapide
    """
    try:
        total_documenti = len(risultati)
        total_reparti = len(set(r['reparto'] for r in risultati))
        
        # Conta stati compliance
        compliant = len([r for r in risultati if r['stato_compliance'] == "Compliant"])
        in_attesa = len([r for r in risultati if r['stato_compliance'] == "In Attesa Firma"])
        non_utilizzati = len([r for r in risultati if r['stato_compliance'] == "Non Utilizzato"])
        
        # Conta anomalie
        total_anomalie = sum(r['anomalie_count'] for r in risultati)
        
        # Calcola compliance rate
        compliance_rate = round((compliant / total_documenti) * 100, 1) if total_documenti > 0 else 0
        
        return {
            'total_documenti': total_documenti,
            'total_reparti': total_reparti,
            'compliant': compliant,
            'in_attesa': in_attesa,
            'non_utilizzati': non_utilizzati,
            'total_anomalie': total_anomalie,
            'compliance_rate': compliance_rate
        }
        
    except Exception as e:
        logger.error(f"❌ Errore nel calcolo statistiche rapide: {str(e)}")
        return {
            'total_documenti': 0,
            'total_reparti': 0,
            'compliant': 0,
            'in_attesa': 0,
            'non_utilizzati': 0,
            'total_anomalie': 0,
            'compliance_rate': 0
        }


@router.get("/statistiche")
def get_statistiche_ai(db: Session = Depends(get_db)):
    """
    Ottiene statistiche rapide dell'analisi AI.
    
    Args:
        db: Sessione del database
        
    Returns:
        dict: Statistiche AI
    """
    try:
        # Usa il servizio AI esistente
        risultato_ai = AIDocumentAnalysisService.analizza_documenti_con_ai()
        
        if not risultato_ai['success']:
            raise HTTPException(
                status_code=500,
                detail=risultato_ai.get('error', 'Errore sconosciuto')
            )
        
        # Estrai statistiche chiave
        statistiche = risultato_ai['statistiche_ai']
        analisi_auto = risultato_ai['analisi_automatica']
        
        stats_ai = {
            "documenti_analizzati": risultato_ai['documenti_analizzati'],
            "compliance_rate": statistiche['compliance_rate_generale'],
            "alert_critici": len(analisi_auto['alert_critici']),
            "reparti_virtuosi": len(analisi_auto['reparti_virtuosi']),
            "reparti_problematici": len(analisi_auto['reparti_problematici']),
            "documenti_prioritari": len(analisi_auto['documenti_prioritari']),
            "raccomandazioni": len(analisi_auto['raccomandazioni']),
            "timestamp": risultato_ai['timestamp']
        }
        
        return stats_ai
        
    except Exception as e:
        logger.error(f"❌ Errore nel caricamento statistiche AI: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Errore nel caricamento statistiche AI: {str(e)}"
        )


@router.get("/report")
def get_report_ai(db: Session = Depends(get_db)):
    """
    Genera e restituisce il report AI completo.
    
    Args:
        db: Sessione del database
        
    Returns:
        dict: Report AI completo
    """
    try:
        # Genera il report AI
        report_ai = AIDocumentAnalysisService.genera_report_ai()
        
        return {
            "success": True,
            "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "report": report_ai
        }
        
    except Exception as e:
        logger.error(f"❌ Errore nella generazione report AI: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Errore nella generazione report AI: {str(e)}"
        )


@router.get("/download_report")
def download_ai_report(format: str = "txt", db: Session = Depends(get_db)):
    """
    Scarica il report AI in formato .txt o .pdf.
    
    Args:
        format: Formato del file (txt o pdf)
        db: Sessione del database
        
    Returns:
        FileResponse: File del report
    """
    try:
        import uuid
        import os
        from fastapi.responses import FileResponse
        
        # Genera il report AI
        report_ai = AIDocumentAnalysisService.genera_report_ai()
        
        # Crea nome file univoco
        ext = "pdf" if format == "pdf" else "txt"
        filename = f"report_ai_documenti_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{ext}"
        filepath = f"/tmp/{filename}"
        
        if format == "pdf":
            # Genera PDF con reportlab
            try:
                from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
                from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
                from reportlab.lib.pagesizes import letter
                from reportlab.lib.units import inch
                
                doc = SimpleDocTemplate(filepath, pagesize=letter)
                styles = getSampleStyleSheet()
                
                # Stile personalizzato per il report
                report_style = ParagraphStyle(
                    'ReportStyle',
                    parent=styles['Normal'],
                    fontSize=10,
                    spaceAfter=6,
                    spaceBefore=6
                )
                
                # Stile per i titoli
                title_style = ParagraphStyle(
                    'TitleStyle',
                    parent=styles['Heading1'],
                    fontSize=14,
                    spaceAfter=12,
                    spaceBefore=12,
                    textColor='#0d6efd'
                )
                
                elements = []
                
                # Titolo del report
                elements.append(Paragraph("🤖 REPORT ANALISI AI DOCUMENTI", title_style))
                elements.append(Spacer(1, 12))
                elements.append(Paragraph(f"Generato il: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}", report_style))
                elements.append(Spacer(1, 12))
                
                # Dividi il report in sezioni
                sections = report_ai.split('\n\n')
                for section in sections:
                    if section.strip():
                        # Controlla se è un titolo (inizia con #)
                        if section.startswith('#'):
                            # È un titolo
                            title = section.replace('#', '').strip()
                            elements.append(Paragraph(title, title_style))
                        else:
                            # È contenuto normale
                            elements.append(Paragraph(section, report_style))
                        elements.append(Spacer(1, 6))
                
                doc.build(elements)
                
            except ImportError:
                logger.warning("⚠️ ReportLab non installato, generando file di testo")
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(report_ai)
                # Cambia l'estensione a .txt
                new_filepath = filepath.replace('.pdf', '.txt')
                os.rename(filepath, new_filepath)
                filepath = new_filepath
                filename = filename.replace('.pdf', '.txt')
        else:
            # Genera file di testo
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(report_ai)
        
        # Restituisci il file
        return FileResponse(
            path=filepath, 
            filename=filename, 
            media_type="application/octet-stream"
        )
        
    except Exception as e:
        logger.error(f"❌ Errore nel download report AI: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Errore nel download report AI: {str(e)}"
        )


@router.get("/reparto_stats")
def reparto_stats(current_user: User = Depends(admin_required)):
    """
    Statistiche per reparto: firme e download.
    
    Args:
        current_user (User): Utente autenticato (admin)
        
    Returns:
        Dict: Statistiche per reparto nel formato atteso dal frontend
    """
    try:
        stats = (
            db.session.query(
                Department.name,
                func.count(DocumentSignature.id).label("firme"),
                func.count(DownloadLog.id).label("download")
            )
            .join(User, User.department_id == Department.id)
            .outerjoin(DocumentSignature, DocumentSignature.signed_by == User.username)
            .outerjoin(DownloadLog, DownloadLog.user_id == User.id)
            .group_by(Department.id)
            .all()
        )
        
        # Formatta i risultati nel formato atteso dal frontend
        reparto_stats = []
        for r in stats:
            reparto_stats.append({
                "nome": r[0],
                "firme": r[1],
                "download": r[2],
                "letture": 0  # Campo aggiuntivo per compatibilità
            })
        
        return {
            "success": True,
            "reparto_stats": reparto_stats,
            "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
    except Exception as e:
        logger.error(f"Errore statistiche reparto: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Errore statistiche reparto: {str(e)}")

@router.get("/analisi_ai")
def analisi_ai(current_user: User = Depends(admin_required)):
    """
    Analisi AI avanzata per documenti e utenti.
    
    Args:
        current_user (User): Utente autenticato (admin)
        
    Returns:
        Dict: Analisi AI con vari indicatori
    """
    try:
        da_30_giorni = datetime.utcnow() - timedelta(days=30)

        # 1. Reparti inattivi (nessun download negli ultimi 30 giorni)
        reparti_inattivi = (
            db.session.query(Department.name)
            .outerjoin(User, User.department_id == Department.id)
            .outerjoin(DownloadLog, DownloadLog.user_id == User.id)
            .filter(
                (DownloadLog.timestamp == None) | 
                (DownloadLog.timestamp < da_30_giorni)
            )
            .group_by(Department.id)
            .all()
        )

        # 2. Documenti obbligatori mai scaricati
        documenti_obbligatori = (
            db.session.query(Document.title)
            .filter(Document.richiedi_firma == True)
            .outerjoin(DownloadLog, DownloadLog.document_id == Document.id)
            .group_by(Document.id)
            .having(func.count(DownloadLog.id) == 0)
            .all()
        )

        # 3. Utenti che scaricano ma non firmano
        utenti_senza_firma = (
            db.session.query(User.email)
            .join(DownloadLog, DownloadLog.user_id == User.id)
            .outerjoin(DocumentSignature, DocumentSignature.signed_by == User.username)
            .group_by(User.id)
            .having(func.count(DocumentSignature.id) == 0)
            .all()
        )

        # 4. Download fuori orario lavorativo (7-17)
        orari_sospetti = (
            db.session.query(DownloadLog)
            .filter(
                func.extract('hour', DownloadLog.timestamp).notin_([7,8,9,10,11,12,13,14,15,16,17])
            )
            .all()
        )

        # 5. Tipologie di documento poco usate
        tipi_poco_usati = (
            db.session.query(
                Document.tag, 
                func.count(DownloadLog.id).label("cnt")
            )
            .join(DownloadLog, DownloadLog.document_id == Document.id)
            .group_by(Document.tag)
            .order_by("cnt")
            .limit(3)
            .all()
        )

        return {
            "reparti_inattivi": [r[0] for r in reparti_inattivi],
            "documenti_obbligatori_non_scaricati": [d[0] for d in documenti_obbligatori],
            "utenti_scaricano_senza_firma": [u[0] for u in utenti_senza_firma],
            "download_fuori_orario": [
                f"{d.user.email if d.user else 'N/A'} - {d.timestamp}" 
                for d in orari_sospetti
            ],
            "tipi_poco_usati": [
                {"tipo": t[0], "count": t[1]} for t in tipi_poco_usati
            ]
        }
        
    except Exception as e:
        logger.error(f"Errore analisi AI: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Errore analisi AI: {str(e)}")
