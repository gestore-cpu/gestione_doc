from datetime import datetime, timedelta
from models import InsightQMSAI, db, AdminLog
from flask_login import current_user

def analizza_documenti_qms(session):
    """
    Analizza i documenti QMS per identificare problemi e generare insight AI
    """
    insights = []
    docs = session.query(DocumentiQMS).all()
    oggi = datetime.utcnow()
    
    for doc in docs:
        # 1. Scadenza superata
        if doc.data_scadenza and doc.data_scadenza < oggi:
            insights.append(InsightQMSAI(
                insight_text=f"❌ Documento '{doc.titolo}' è scaduto il {doc.data_scadenza.strftime('%d/%m/%Y')}",
                insight_type="scadenza",
                severity="critico",
                documento_id=doc.id,
                modulo_qms=doc.modulo
            ))
        
        # 2. Manca revisione da oltre 1 anno
        if doc.data_ultima_revisione and (oggi - doc.data_ultima_revisione).days > 365:
            insights.append(InsightQMSAI(
                insight_text=f"📄 Documento '{doc.titolo}' non è stato revisionato da oltre un anno",
                insight_type="revisione",
                severity="attenzione",
                documento_id=doc.id,
                modulo_qms=doc.modulo
            ))
        
        # 3. Documento senza firma obbligatoria
        if doc.richiesta_firma and not doc.firmato:
            insights.append(InsightQMSAI(
                insight_text=f"✍️ Documento '{doc.titolo}' richiede firma ma risulta non firmato",
                insight_type="firma_mancante",
                severity="critico",
                documento_id=doc.id,
                modulo_qms=doc.modulo
            ))
        
        # 4. Documento in scadenza (entro 30 giorni)
        if doc.data_scadenza and (doc.data_scadenza - oggi).days <= 30 and (doc.data_scadenza - oggi).days > 0:
            insights.append(InsightQMSAI(
                insight_text=f"⚠️ Documento '{doc.titolo}' scade il {doc.data_scadenza.strftime('%d/%m/%Y')}",
                insight_type="scadenza",
                severity="attenzione",
                documento_id=doc.id,
                modulo_qms=doc.modulo
            ))
    
    return insights

def trasforma_qms_insight_in_task(insight_id):
    """
    Trasforma un insight QMS in un task operativo
    """
    try:
        insight = InsightQMSAI.query.get(insight_id)
        if not insight or insight.task_id:
            return None
            
        priorita_map = {"critico": "Alta", "attenzione": "Media", "informativo": "Bassa"}
        priorita = priorita_map.get(insight.severity, "Media")
        
        titolo = f"[QMS AI] {insight.insight_type.capitalize()} - {insight.severity.capitalize()}"
        descrizione = f"🔍 Insight QMS AI: {insight.insight_text}\n\n"
        descrizione += f"📊 Tipo: {insight.insight_type}\n"
        descrizione += f"⚠️ Severità: {insight.severity}\n"
        descrizione += f"📅 Creato il: {insight.data_creazione.strftime('%d/%m/%Y %H:%M')}\n"
        if insight.modulo_qms:
            descrizione += f"📁 Modulo QMS: {insight.modulo_qms}\n"
        
        nuovo_task = Task(
            titolo=titolo,
            descrizione=descrizione,
            priorita=priorita,
            assegnato_a="admin@example.com",
            stato="Da fare",
            scadenza=datetime.utcnow() + timedelta(days=7),
            created_by=current_user.email if current_user.is_authenticated else "sistema",
            qms_insight_id=insight.id
        )
        
        db.session.add(nuovo_task)
        db.session.flush()
        
        insight.task_id = nuovo_task.id
        insight.stato = "trasformato"
        
        # Log dell'azione
        admin_log = AdminLog(
            action="trasformazione_insight_qms_in_task",
            performed_by=current_user.email if current_user.is_authenticated else "sistema",
            extra_info=f"Insight QMS ID: {insight_id} -> Task ID: {nuovo_task.id}"
        )
        db.session.add(admin_log)
        db.session.commit()
        
        return nuovo_task.id
        
    except Exception as e:
        db.session.rollback()
        print(f"Errore trasformazione insight QMS in task: {e}")
        return None 