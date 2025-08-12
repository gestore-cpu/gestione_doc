"""
Utility per il calcolo del punteggio di rischio AI per le richieste di accesso.
"""

import json
import openai
from datetime import datetime
from flask import current_app
from models import AccessRequest, User, Document


def calculate_risk_score(request_obj):
    """
    Calcola il punteggio di rischio AI per una richiesta di accesso.
    """
    try:
        # Raccogli fattori di rischio
        factors = {
            "user_role": request_obj.user.role,
            "user_email": request_obj.user.email,
            "document_title": request_obj.document.title,
            "document_expiry": request_obj.document.expiry_date.isoformat() if request_obj.document.expiry_date else None,
            "document_is_critical": request_obj.document.is_critical,
            "request_note": request_obj.note or "",
            "user_history_denied": len([r for r in request_obj.user.access_requests if r.status == 'denied']),
            "user_history_total": len(request_obj.user.access_requests)
        }
        
        # Chiamata AI
        prompt = f"""
Analizza questi fattori di richiesta di accesso e assegna un punteggio di rischio (0-100):

FATTORI UTENTE:
- Ruolo: {factors['user_role']}
- Email: {factors['user_email']}
- Richieste negate precedenti: {factors['user_history_denied']}
- Totale richieste: {factors['user_history_total']}

FATTORI DOCUMENTO:
- Titolo: {factors['document_title']}
- Scadenza: {factors['document_expiry']}
- Critico: {factors['document_is_critical']}

FATTORI RICHIESTA:
- Motivazione: "{factors['request_note']}"

Considera:
- Ruoli guest/esterni = rischio alto
- Documenti critici/scaduti = rischio alto
- Storia richieste negate = rischio alto
- Motivazioni vaghe = rischio medio

Rispondi solo con JSON:
{{
    "score": <numero 0-100>,
    "explanation": "<spiegazione in italiano>",
    "risk_factors": ["<fattore1>", "<fattore2>", ...]
}}
"""

        ai_response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "Sei un analista di sicurezza informatica per documenti aziendali."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            max_tokens=500
        )

        ai_data = json.loads(ai_response["choices"][0]["message"]["content"])
        score = ai_data.get("score", 0)
        explanation = ai_data.get("explanation", "")
        risk_factors = ai_data.get("risk_factors", [])
        
        factors_detail = {
            "score": score,
            "explanation": explanation,
            "risk_factors": risk_factors,
            "analysis_timestamp": datetime.utcnow().isoformat(),
            "factors_analyzed": factors
        }
        
        return score, factors_detail
        
    except Exception as e:
        current_app.logger.error(f"Errore nel calcolo risk score: {str(e)}")
        return 0, {"error": str(e)}


def apply_risk_score_to_request(request_id):
    """
    Applica il calcolo del risk score a una richiesta specifica.
    """
    try:
        from extensions import db
        
        request_obj = AccessRequest.query.get(request_id)
        if not request_obj:
            return False
            
        score, factors = calculate_risk_score(request_obj)
        
        request_obj.risk_score = score
        request_obj.risk_factors = factors
        request_obj.risk_analysis_at = datetime.utcnow()
        
        db.session.commit()
        
        current_app.logger.info(f"Risk score applicato alla richiesta {request_id}: {score}/100")
        return True
        
    except Exception as e:
        current_app.logger.error(f"Errore nell'applicazione risk score: {str(e)}")
        return False


def get_high_risk_requests(limit=10):
    """
    Recupera le richieste con rischio alto.
    """
    return AccessRequest.query.filter(
        AccessRequest.risk_score >= 70,
        AccessRequest.status == 'pending'
    ).order_by(AccessRequest.risk_score.desc()).limit(limit).all()


def get_risk_statistics():
    """
    Calcola statistiche sui punteggi di rischio.
    """
    from sqlalchemy import func
    from extensions import db
    
    stats = db.session.query(
        func.avg(AccessRequest.risk_score).label('avg_score'),
        func.count(AccessRequest.id).label('total_requests'),
        func.count(AccessRequest.id).filter(AccessRequest.risk_score >= 70).label('high_risk'),
        func.count(AccessRequest.id).filter(AccessRequest.risk_score.between(40, 69)).label('medium_risk'),
        func.count(AccessRequest.id).filter(AccessRequest.risk_score < 40).label('low_risk')
    ).filter(AccessRequest.risk_score.isnot(None)).first()
    
    return {
        'average_score': round(stats.avg_score or 0, 1),
        'total_requests': stats.total_requests or 0,
        'high_risk_count': stats.high_risk or 0,
        'medium_risk_count': stats.medium_risk or 0,
        'low_risk_count': stats.low_risk or 0
    }
