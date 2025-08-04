#!/usr/bin/env python3
"""
Sistema di firma automatica AI per documenti
"""

from datetime import datetime
from models import Document, AdminLog
from extensions import db

def firma_automatica_ai():
    """
    Funzione per la firma automatica AI dei documenti.
    
    Regole per firma automatica:
    - Documento approvato (stato_approvazione == 'approvato')
    - Non già firmato (is_signed == False)
    - Titolo contiene parole chiave specifiche
    - Documenti a bassa criticità
    """
    
    # Query documenti idonei per firma automatica
    documenti = Document.query.filter_by(
        stato_approvazione='approvato', 
        is_signed=False
    ).all()
    
    firme_automatiche = 0
    
    for doc in documenti:
        # Regole per firma automatica
        if _is_eligible_for_auto_sign(doc):
            # Esegui firma automatica
            doc.is_signed = True
            doc.signed_at = datetime.utcnow()
            doc.signed_by = 'AI_AUTOSIGN'
            doc.firma_commento = '✅ Firma automatica AI - Documento idoneo per approvazione automatica'
            doc.signed_by_ai = True
            
            # Log dell'azione
            log = AdminLog(
                action="Firma automatica AI",
                performed_by="AI_SYSTEM",
                document_id=doc.id,
                extra_info=f"Documento '{doc.title}' firmato automaticamente da AI"
            )
            db.session.add(log)
            
            firme_automatiche += 1
    
    if firme_automatiche > 0:
        db.session.commit()
        print(f"🤖 AI ha firmato automaticamente {firme_automatiche} documenti")
    
    return firme_automatiche

def _is_eligible_for_auto_sign(doc):
    """
    Determina se un documento è idoneo per la firma automatica AI.
    
    Args:
        doc: Document object
        
    Returns:
        bool: True se il documento è idoneo per firma automatica
    """
    
    # Parole chiave per documenti a bassa criticità
    low_criticality_keywords = [
        'procedura', 'procedura operativa', 'istruzione', 'istruzioni',
        'checklist', 'lista controllo', 'template', 'modello',
        'form', 'formulario', 'report', 'rapporto', 'verbale',
        'note', 'appunti', 'comunicazione', 'avviso'
    ]
    
    # Controlla se il titolo contiene parole chiave a bassa criticità
    title_lower = doc.title.lower()
    for keyword in low_criticality_keywords:
        if keyword in title_lower:
            return True
    
    # Controlla lunghezza titolo (documenti semplici)
    if len(doc.title) < 50:
        return True
    
    # Controlla se è un documento di routine
    if doc.company and doc.company.name:
        company_lower = doc.company.name.lower()
        if any(word in company_lower for word in ['routine', 'standard', 'template']):
            return True
    
    return False

def suggerisci_firma_ai(doc):
    """
    Genera suggerimenti AI per la firma automatica.
    
    Args:
        doc: Document object
        
    Returns:
        str: Suggerimento AI o stringa vuota
    """
    
    if not doc or doc.is_signed:
        return ""
    
    suggestions = []
    
    # Controlla stato approvazione
    if doc.stato_approvazione == 'approvato':
        suggestions.append("✅ Documento approvato e pronto per firma")
    
    # Controlla tipo documento
    title_lower = doc.title.lower()
    if "verbale" in title_lower:
        suggestions.append("📋 Verbale idoneo per firma automatica")
    elif "procedura" in title_lower:
        suggestions.append("📝 Procedura operativa - firma automatica consigliata")
    elif "checklist" in title_lower:
        suggestions.append("✅ Checklist - approvazione automatica sicura")
    elif "template" in title_lower:
        suggestions.append("📄 Template - firma automatica appropriata")
    
    # Controlla criticità
    if len(doc.title) < 50:
        suggestions.append("📏 Documento semplice - bassa criticità")
    
    # Controlla azienda
    if doc.company and doc.company.name:
        company_lower = doc.company.name.lower()
        if any(word in company_lower for word in ['routine', 'standard']):
            suggestions.append("🏢 Documento di routine aziendale")
    
    if suggestions:
        return "🧠 " + " | ".join(suggestions)
    
    return ""

def get_auto_sign_stats():
    """
    Restituisce statistiche sulle firme automatiche AI.
    
    Returns:
        dict: Statistiche firme automatiche
    """
    
    total_ai_signed = Document.query.filter_by(signed_by_ai=True).count()
    today_ai_signed = Document.query.filter(
        Document.signed_by_ai == True,
        Document.signed_at >= datetime.utcnow().date()
    ).count()
    
    return {
        'total_ai_signed': total_ai_signed,
        'today_ai_signed': today_ai_signed,
        'ai_sign_percentage': (total_ai_signed / Document.query.filter_by(is_signed=True).count() * 100) if Document.query.filter_by(is_signed=True).count() > 0 else 0
    }