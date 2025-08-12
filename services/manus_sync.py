"""
Service per la sincronizzazione con Manus Core.
Gestisce manuali, corsi e completamenti.
"""

from datetime import datetime, timezone
from models import db, Document, Company, ManusManualLink, ManusCourseLink, TrainingCompletionManus
from services.manus_client import ManusClient
import logging

logger = logging.getLogger(__name__)

def _utcnow():
    """Restituisce datetime UTC senza timezone info."""
    return datetime.now(timezone.utc).replace(tzinfo=None)

def sync_manuals(azienda_id: int, azienda_ref: str):
    """
    Sincronizza i manuali da Manus per un'azienda.
    
    Args:
        azienda_id (int): ID dell'azienda nel sistema locale
        azienda_ref (str): Riferimento azienda in Manus
    """
    try:
        mc = ManusClient()
        manuals = mc.list_manuals(azienda_ref)
        
        logger.info(f"🔄 Sync manuali per azienda {azienda_id} ({azienda_ref}): {len(manuals)} manuali trovati")
        
        for m in manuals:
            try:
                title = m.get("title") or f"Manual {m['id']}"
                version = str(m.get("version") or "1")
                
                # Cerca documento esistente per titolo
                doc = (Document.query
                       .filter_by(company_id=azienda_id, title=title)
                       .first())
                
                if not doc:
                    # Crea nuovo documento
                    doc = Document(
                        company_id=azienda_id,
                        title=title,
                        filename=f"manus_manual_{m['id']}.pdf",  # Placeholder
                        original_filename=f"{title}.pdf",
                        description=f"Manuale sincronizzato da Manus - {m.get('description', '')}",
                        user_id=1,  # Admin user
                        uploader_email="admin@example.com",
                        department_id=1,  # Default department
                        visibility='privato',
                        downloadable=True,
                        tag="Manus Manual",
                        categoria_ai="Manuale QMS"
                    )
                    db.session.add(doc)
                    db.session.flush()  # Per ottenere l'ID
                    logger.info(f"✅ Creato nuovo documento: {title}")

                # Gestisci link Manus
                link = (ManusManualLink.query
                        .filter_by(azienda_id=azienda_id, manus_manual_id=m["id"])
                        .first())
                
                if not link:
                    link = ManusManualLink(
                        azienda_id=azienda_id,
                        documento_id=doc.id,
                        manus_manual_id=m["id"],
                        manus_version=version
                    )
                    db.session.add(link)
                    logger.info(f"✅ Creato link Manus per: {title}")
                else:
                    # Aggiorna versione se cambiata
                    if link.manus_version != version:
                        link.manus_version = version
                        logger.info(f"🔄 Aggiornata versione per: {title} -> {version}")
                
                link.last_sync_at = _utcnow()
                
            except Exception as e:
                logger.error(f"❌ Errore sync manuale {m.get('id', 'unknown')}: {e}")
                continue
        
        db.session.commit()
        logger.info(f"✅ Sync manuali completato per azienda {azienda_id}")
        
    except Exception as e:
        logger.error(f"❌ Errore sync manuali per azienda {azienda_id}: {e}")
        db.session.rollback()
        raise

def sync_courses(azienda_id: int, azienda_ref: str):
    """
    Sincronizza i corsi da Manus per un'azienda.
    
    Args:
        azienda_id (int): ID dell'azienda nel sistema locale
        azienda_ref (str): Riferimento azienda in Manus
    """
    try:
        mc = ManusClient()
        courses = mc.list_courses(azienda_ref)
        
        logger.info(f"🔄 Sync corsi per azienda {azienda_id} ({azienda_ref}): {len(courses)} corsi trovati")
        
        for c in courses:
            try:
                code = c.get("code")
                if not code:
                    continue
                
                # Cerca documento esistente per codice corso
                req = (Document.query
                       .filter_by(company_id=azienda_id, tag="Manus Course")
                       .filter(Document.title.contains(code))
                       .first())
                
                if not req:
                    # Crea nuovo documento requisito
                    req = Document(
                        company_id=azienda_id,
                        title=f"Corso {code} - {c.get('title', 'Formazione')}",
                        filename=f"manus_course_{c['id']}.pdf",  # Placeholder
                        original_filename=f"corso_{code}.pdf",
                        description=f"Corso sincronizzato da Manus - {c.get('description', '')}",
                        user_id=1,  # Admin user
                        uploader_email="admin@example.com",
                        department_id=1,  # Default department
                        visibility='privato',
                        downloadable=True,
                        tag="Manus Course",
                        categoria_ai="Corso Formazione"
                    )
                    db.session.add(req)
                    db.session.flush()
                    logger.info(f"✅ Creato nuovo requisito corso: {code}")
                
                # Gestisci link corso
                link = (ManusCourseLink.query
                        .filter_by(azienda_id=azienda_id, requisito_id=req.id)
                        .first())
                
                if not link:
                    link = ManusCourseLink(
                        azienda_id=azienda_id,
                        requisito_id=req.id,
                        manus_course_id=c["id"]
                    )
                    db.session.add(link)
                    logger.info(f"✅ Creato link corso per: {code}")
                
                link.last_sync_at = _utcnow()
                
            except Exception as e:
                logger.error(f"❌ Errore sync corso {c.get('id', 'unknown')}: {e}")
                continue
        
        db.session.commit()
        logger.info(f"✅ Sync corsi completato per azienda {azienda_id}")
        
    except Exception as e:
        logger.error(f"❌ Errore sync corsi per azienda {azienda_id}: {e}")
        db.session.rollback()
        raise

def sync_completions_for_course(link: ManusCourseLink, since_iso: str = None):
    """
    Sincronizza i completamenti per un corso specifico.
    
    Args:
        link (ManusCourseLink): Link del corso
        since_iso (str): Data ISO da cui filtrare (opzionale)
    """
    try:
        mc = ManusClient()
        payload = mc.list_course_completions(link.manus_course_id, since_iso)
        
        completions = payload.get("items", [])
        logger.info(f"🔄 Sync completamenti per corso {link.manus_course_id}: {len(completions)} trovati")
        
        for row in completions:
            try:
                # ATTENZIONE: serve mappare l'utente Manus → user_id interno
                user_id = row.get("user_id_internal")
                email = row.get("user_email")
                
                if not user_id:
                    # Prova a risolvere per email
                    from services.manus_user_mapping import resolve_user_id
                    user_id = resolve_user_id(None, email)
                    
                    if not user_id:
                        # Crea mapping inattivo per revisione manuale
                        from models import ManusUserMapping
                        existing = ManusUserMapping.query.filter_by(
                            manus_user_id=row.get("user_id", f"unknown_{row.get('id', 'unknown')}")
                        ).first()
                        
                        if not existing:
                            mapping = ManusUserMapping(
                                manus_user_id=row.get("user_id", f"unknown_{row.get('id', 'unknown')}"),
                                email=email,
                                syn_user_id=None,
                                active=False
                            )
                            db.session.add(mapping)
                            db.session.commit()
                            logger.warning(f"⚠️ Utente non mappato, creato mapping inattivo: {email}")
                        
                        continue
                
                completed_at_str = row.get("completed_at")
                if not completed_at_str:
                    continue
                
                # Converti stringa ISO in datetime
                completed_at = datetime.fromisoformat(completed_at_str.replace("Z", "+00:00")).replace(tzinfo=None)
                
                # Cerca completamento esistente
                rec = (TrainingCompletionManus.query
                       .filter_by(user_id=user_id, requisito_id=link.requisito_id)
                       .first())
                
                if not rec:
                    rec = TrainingCompletionManus(
                        user_id=user_id,
                        requisito_id=link.requisito_id,
                        manus_course_id=link.manus_course_id,
                        completed_at=completed_at
                    )
                    db.session.add(rec)
                    logger.info(f"✅ Creato completamento per utente {user_id}")
                elif rec.completed_at < completed_at:
                    # Aggiorna se più recente
                    rec.completed_at = completed_at
                    logger.info(f"🔄 Aggiornato completamento per utente {user_id}")
                
            except Exception as e:
                logger.error(f"❌ Errore sync completamento: {e}")
                continue
        
        db.session.commit()
        logger.info(f"✅ Sync completamenti completato per corso {link.manus_course_id}")
        
    except Exception as e:
        logger.error(f"❌ Errore sync completamenti per corso {link.manus_course_id}: {e}")
        db.session.rollback()
        raise

def sync_all_for_company(azienda_id: int, azienda_ref: str):
    """
    Sincronizza tutto per un'azienda: manuali, corsi e completamenti.
    
    Args:
        azienda_id (int): ID dell'azienda nel sistema locale
        azienda_ref (str): Riferimento azienda in Manus
    """
    logger.info(f"🚀 Avvio sync completo per azienda {azienda_id} ({azienda_ref})")
    
    try:
        # Sync manuali
        sync_manuals(azienda_id, azienda_ref)
        
        # Sync corsi
        sync_courses(azienda_id, azienda_ref)
        
        # Sync completamenti per tutti i corsi
        course_links = ManusCourseLink.query.filter_by(azienda_id=azienda_id).all()
        for link in course_links:
            sync_completions_for_course(link)
        
        logger.info(f"✅ Sync completo completato per azienda {azienda_id}")
        
    except Exception as e:
        logger.error(f"❌ Errore sync completo per azienda {azienda_id}: {e}")
        raise
