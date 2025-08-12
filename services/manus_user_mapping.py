"""
Service per il mapping utenti tra Manus e SYNTHIA.
Gestisce la risoluzione automatica e manuale degli utenti.
"""

from models import db, User, ManusUserMapping, TrainingCompletionManus, TrainingCoverageReport
import logging

logger = logging.getLogger(__name__)

def resolve_user_id(manus_user_id: str, email: str = None) -> int:
    """
    Risolve un utente Manus nel corrispondente utente SYNTHIA.
    
    Args:
        manus_user_id (str): ID utente in Manus
        email (str): Email utente in Manus
        
    Returns:
        int: ID utente SYNTHIA o None
    """
    # TODO: implementa lookup utente interno per email/SSO
    u = None
    if email:
        u = User.query.filter(User.email.ilike(email)).first()
    if not u:
        m = ManusUserMapping.query.filter_by(manus_user_id=manus_user_id, active=True).first()
        if m and m.syn_user_id:
            return m.syn_user_id
    return u.id if u else None

def upsert_mapping(manus_user_id: str, syn_user_id: int, email: str = None):
    """
    Crea o aggiorna un mapping utente Manus.
    
    Args:
        manus_user_id (str): ID utente in Manus
        syn_user_id (int): ID utente in SYNTHIA
        email (str): Email utente (opzionale)
        
    Returns:
        ManusUserMapping: Mapping creato/aggiornato
    """
    m = ManusUserMapping.query.filter_by(manus_user_id=manus_user_id).first()
    if not m:
        m = ManusUserMapping(
            manus_user_id=manus_user_id, 
            syn_user_id=syn_user_id, 
            email=email, 
            active=True
        )
        db.session.add(m)
    else:
        m.syn_user_id = syn_user_id
        if email:
            m.email = email
        m.active = True
    db.session.commit()
    return m

def rebuild_coverage_for_user(user_id: int):
    """
    Ricostruisce i report di copertura formazione per un utente.
    
    Args:
        user_id (int): ID utente SYNTHIA
        
    Returns:
        int: Numero di record aggiornati
    """
    # Marca completo se esiste un TrainingCompletionManus su quel requisito
    rows = db.session.execute("""
        INSERT INTO training_coverage_report (azienda_id, user_id, requisito_id, status, source)
        SELECT rf.azienda_id, :uid, rf.id, 
               CASE WHEN EXISTS (
                   SELECT 1 FROM training_completion_manus tcm 
                   WHERE tcm.user_id=:uid AND tcm.requisito_id=rf.id
               ) THEN 'completo' ELSE 'mancante' END,
               'manus'
        FROM documents rf
        WHERE rf.tag = 'Manus Course'
        ON CONFLICT(user_id, requisito_id) DO UPDATE SET
            status=excluded.status, updated_at=CURRENT_TIMESTAMP
    """, {"uid": user_id})
    db.session.commit()
    return rows.rowcount
