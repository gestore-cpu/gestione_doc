"""
Script periodico per l'analisi AI automatica dei documenti.

Questo modulo fornisce:
- Analisi periodica di tutti i documenti
- Generazione automatica di insight AI
- Creazione di task suggeriti
- Integrazione con il sistema di notifiche
"""

import os
import sys
import json
from datetime import datetime, timedelta
from typing import List, Dict

# Aggiungi il percorso del progetto al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import Document, DocumentoAIInsight, Task, InsightAI
from extensions import db
from ai.document_ai_utils import analizza_documento, genera_insight_ai, suggerisci_task_automatico
from ai.task_generator import genera_task_intelligente, determina_modulo_destinazione


def esegui_analisi_ai():
    """
    Esegue l'analisi AI su tutti i documenti del sistema.
    
    Returns:
        Dict: Statistiche dell'analisi eseguita.
    """
    print(f"[AI] Inizio analisi documenti - {datetime.utcnow()}")
    
    # Recupera tutti i documenti
    tutti_documenti = Document.query.all()
    print(f"[AI] Trovati {len(tutti_documenti)} documenti da analizzare")
    
    statistiche = {
        'documenti_analizzati': 0,
        'insight_generati': 0,
        'task_creati': 0,
        'errori': 0
    }
    
    for documento in tutti_documenti:
        try:
            # Verifica se il file esiste
            if not hasattr(documento, 'file_path') or not documento.file_path:
                # Usa il filename come fallback
                documento.file_path = os.path.join('uploads', documento.filename)
            
            if not os.path.exists(documento.file_path):
                print(f"[AI] File non trovato per documento {documento.id}: {documento.file_path}")
                statistiche['errori'] += 1
                continue
            
            # Analizza il documento
            risultato = analizza_documento(documento, tutti_documenti)
            
            if risultato and not 'errore' in risultato:
                # Genera insight AI
                insight = genera_insight_ai(risultato, documento)
                
                if insight['insight_type']:  # Solo se c'è un insight significativo
                    # Salva l'insight nel database
                    salva_insight_ai(insight, documento)
                    statistiche['insight_generati'] += 1
                    
                    # Suggerisci task automatico
                    task_suggerito = suggerisci_task_automatico(insight)
                    if task_suggerito['titolo']:
                        crea_task_automatico(task_suggerito, insight)
                        statistiche['task_creati'] += 1
                
                print(f"[AI] Documento {documento.id} ({documento.title}): {insight['insight_text']}")
            
            statistiche['documenti_analizzati'] += 1
            
        except Exception as e:
            print(f"[AI] Errore nell'analisi del documento {documento.id}: {e}")
            statistiche['errori'] += 1
    
    print(f"[AI] Analisi completata - {datetime.utcnow()}")
    print(f"[AI] Statistiche: {statistiche}")
    
    return statistiche


def salva_insight_ai(insight: Dict, documento) -> DocumentoAIInsight:
    """
    Salva un insight AI nel database.
    
    Args:
        insight (Dict): Insight AI generato.
        documento: Oggetto Document.
        
    Returns:
        DocumentoAIInsight: Insight salvato.
    """
    # Verifica se esiste già un insight simile per questo documento
    insight_esistente = DocumentoAIInsight.query.filter_by(
        document_id=documento.id,
        tipo=insight['insight_type'],
        status='attivo'
    ).first()
    
    if insight_esistente:
        # Aggiorna l'insight esistente
        insight_esistente.valore = insight.get('insight_text', '')
        insight_esistente.severity = insight['severity']
        insight_esistente.timestamp = datetime.utcnow()
        db.session.commit()
        return insight_esistente
    else:
        # Crea nuovo insight
        nuovo_insight = DocumentoAIInsight(
            document_id=documento.id,
            tipo=insight['insight_type'],
            valore=insight.get('insight_text', ''),
            severity=insight['severity'],
            status='attivo'
        )
        db.session.add(nuovo_insight)
        db.session.commit()
        return nuovo_insight


def crea_task_automatico(task_suggerito: Dict, insight: Dict) -> Task:
    """
    Crea un task automatico basato su un insight AI con routing intelligente.
    
    Args:
        task_suggerito (Dict): Task suggerito dall'AI.
        insight (Dict): Insight AI che ha generato il task.
        
    Returns:
        Task: Task creato.
    """
    try:
        # Recupera il documento
        documento = Document.query.get(insight['documento_id'])
        if not documento:
            print(f"[AI] Documento {insight['documento_id']} non trovato")
            return None
        
        # Crea l'insight AI principale se non esiste
        insight_ai = InsightAI(
            insight_text=insight['insight_text'],
            insight_type='documento_management',
            severity=insight['severity'],
            status='attivo',
            affected_documents=json.dumps([insight['documento_id']])
        )
        db.session.add(insight_ai)
        db.session.flush()  # Per ottenere l'ID
        
        # Determina il tipo di insight per il routing
        tipo_insight = insight.get('tipo', 'revisione')
        
        # Genera task con routing intelligente
        task = genera_task_intelligente(documento, tipo_insight, insight_ai.id)
        
        # Aggiorna il task con informazioni aggiuntive
        task.insight_id = insight_ai.id
        
        # Determina il modulo di destinazione
        modulo = determina_modulo_destinazione(documento, tipo_insight)
        print(f"[AI] Task assegnato al modulo: {modulo}")
        
        db.session.commit()
        print(f"[AI] Creato task automatico: {task.titolo} -> {modulo}")
        return task
        
    except Exception as e:
        print(f"[AI] Errore creazione task automatico: {e}")
        db.session.rollback()
        return None


def pulisci_insight_obsoleti():
    """
    Pulisce gli insight AI obsoleti o risolti.
    """
    # Rimuovi insight risolti più vecchi di 30 giorni
    data_limite = datetime.utcnow() - timedelta(days=30)
    insight_obsoleti = DocumentoAIInsight.query.filter(
        DocumentoAIInsight.status.in_(['risolto', 'ignorato']),
        DocumentoAIInsight.timestamp < data_limite
    ).all()
    
    for insight in insight_obsoleti:
        db.session.delete(insight)
    
    db.session.commit()
    print(f"[AI] Rimossi {len(insight_obsoleti)} insight obsoleti")


def aggiorna_insight_esistenti():
    """
    Aggiorna gli insight esistenti basandosi sui cambiamenti recenti.
    """
    # Trova insight attivi per documenti che potrebbero essere stati aggiornati
    insight_attivi = DocumentoAIInsight.query.filter_by(status='attivo').all()
    
    for insight in insight_attivi:
        documento = insight.document
        
        # Verifica se il documento è ancora valido per questo insight
        if insight.tipo == 'obsoleto':
            # Se il documento è stato aggiornato recentemente, risolvi l'insight
            if documento.created_at and documento.created_at > insight.timestamp:
                insight.status = 'risolto'
                insight.valore = 'Documento aggiornato'
        
        elif insight.tipo == 'inutilizzato':
            # Se il documento è stato accesso recentemente, risolvi l'insight
            if documento.download_logs:
                ultimo_accesso = max(log.timestamp for log in documento.download_logs)
                if ultimo_accesso > insight.timestamp:
                    insight.status = 'risolto'
                    insight.valore = 'Documento nuovamente utilizzato'
    
    db.session.commit()
    print(f"[AI] Aggiornati {len(insight_attivi)} insight esistenti")


def esegui_analisi_completa():
    """
    Esegue un'analisi completa del sistema documentale.
    """
    print("=== ANALISI AI DOCUMENTALE ===")
    
    # 1. Pulisci insight obsoleti
    pulisci_insight_obsoleti()
    
    # 2. Aggiorna insight esistenti
    aggiorna_insight_esistenti()
    
    # 3. Esegui analisi su tutti i documenti
    statistiche = esegui_analisi_ai()
    
    # 4. Genera report
    genera_report_analisi(statistiche)
    
    print("=== ANALISI COMPLETATA ===")


def genera_report_analisi(statistiche: Dict):
    """
    Genera un report dell'analisi eseguita.
    
    Args:
        statistiche (Dict): Statistiche dell'analisi.
    """
    report = {
        'data_analisi': datetime.utcnow().isoformat(),
        'statistiche': statistiche,
        'insight_attivi': DocumentoAIInsight.query.filter_by(status='attivo').count(),
        'task_pendenti': Task.query.filter_by(stato='Da fare').count()
    }
    
    # Salva il report (opzionale)
    with open('logs/ai_analysis_report.json', 'w') as f:
        json.dump(report, f, indent=2, default=str)
    
    print(f"[AI] Report salvato: {report}")


if __name__ == "__main__":
    # Esegui l'analisi se chiamato direttamente
    esegui_analisi_completa() 