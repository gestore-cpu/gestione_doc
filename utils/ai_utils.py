from datetime import datetime, timedelta
import logging

# Configurazione logging
logger = logging.getLogger(__name__)

def genera_suggerimenti_guest_ai(accessi):
    """
    Genera suggerimenti AI automatici per la gestione degli ospiti.
    
    Args:
        accessi (list): Lista degli accessi guest da analizzare
        
    Returns:
        list: Lista di suggerimenti AI
    """
    oggi = datetime.utcnow()
    suggerimenti = []
    
    try:
        # Contatori per statistiche
        scaduti = 0
        in_scadenza = 0
        non_registrati = 0
        totali = len(accessi)
        
        for access in accessi:
            # Calcola giorni rimanenti
            giorni_restanti = (access.expires_at - oggi).days
            
            # Accessi scaduti
            if giorni_restanti < 0:
                scaduti += 1
                suggerimenti.append({
                    'tipo': 'scaduto',
                    'severita': 'critico',
                    'messaggio': f"❌ Accesso scaduto per {access.guest.email} – valuta revoca o proroga.",
                    'access_id': access.id,
                    'email': access.guest.email,
                    'giorni': giorni_restanti
                })
            
            # Accessi in scadenza (entro 3 giorni)
            elif giorni_restanti <= 3:
                in_scadenza += 1
                suggerimenti.append({
                    'tipo': 'in_scadenza',
                    'severita': 'attenzione',
                    'messaggio': f"⏳ Accesso in scadenza ({giorni_restanti}gg) per {access.guest.email}",
                    'access_id': access.id,
                    'email': access.guest.email,
                    'giorni': giorni_restanti
                })
            
            # Guest non registrati
            if not access.guest.password:
                non_registrati += 1
                suggerimenti.append({
                    'tipo': 'non_registrato',
                    'severita': 'info',
                    'messaggio': f"⚠️ {access.guest.email} non si è ancora registrato – reinvia invito?",
                    'access_id': access.id,
                    'email': access.guest.email
                })
        
        # Suggerimenti generali basati su statistiche
        if scaduti > 0:
            suggerimenti.append({
                'tipo': 'statistica',
                'severita': 'critico',
                'messaggio': f"📊 Hai {scaduti} accessi scaduti su {totali} totali. Considera una pulizia.",
                'access_id': None
            })
        
        if in_scadenza > 0:
            suggerimenti.append({
                'tipo': 'statistica',
                'severita': 'attenzione',
                'messaggio': f"📊 {in_scadenza} accessi scadono entro 3 giorni. Valuta proroghe.",
                'access_id': None
            })
        
        if non_registrati > 0:
            suggerimenti.append({
                'tipo': 'statistica',
                'severita': 'info',
                'messaggio': f"📊 {non_registrati} guest non si sono ancora registrati.",
                'access_id': None
            })
        
        # Se non ci sono problemi, suggerimento positivo
        if not suggerimenti:
            suggerimenti.append({
                'tipo': 'positivo',
                'severita': 'success',
                'messaggio': "✅ Tutti gli accessi guest sono in regola!",
                'access_id': None
            })
        
        logger.info(f"Generati {len(suggerimenti)} suggerimenti AI per {totali} accessi guest")
        
    except Exception as e:
        logger.error(f"Errore nella generazione suggerimenti AI: {str(e)}")
        suggerimenti.append({
            'tipo': 'errore',
            'severita': 'danger',
            'messaggio': "❌ Errore nell'analisi AI degli accessi guest",
            'access_id': None
        })
    
    return suggerimenti

def analizza_pattern_accessi_guest(accessi):
    """
    Analizza pattern negli accessi guest per identificare anomalie.
    
    Args:
        accessi (list): Lista degli accessi guest
        
    Returns:
        dict: Risultati dell'analisi
    """
    try:
        oggi = datetime.utcnow()
        analisi = {
            'totali': len(accessi),
            'scaduti': 0,
            'in_scadenza': 0,
            'attivi': 0,
            'non_registrati': 0,
            'con_download': 0,
            'solo_vista': 0,
            'creati_ultimi_7gg': 0,
            'creati_ultimi_30gg': 0
        }
        
        for access in accessi:
            giorni_restanti = (access.expires_at - oggi).days
            
            # Conta per stato
            if giorni_restanti < 0:
                analisi['scaduti'] += 1
            elif giorni_restanti <= 3:
                analisi['in_scadenza'] += 1
            else:
                analisi['attivi'] += 1
            
            # Conta per permessi
            if access.can_download:
                analisi['con_download'] += 1
            else:
                analisi['solo_vista'] += 1
            
            # Conta per registrazione
            if not access.guest.password:
                analisi['non_registrati'] += 1
            
            # Conta per data creazione
            giorni_creazione = (oggi - access.created_at).days
            if giorni_creazione <= 7:
                analisi['creati_ultimi_7gg'] += 1
            if giorni_creazione <= 30:
                analisi['creati_ultimi_30gg'] += 1
        
        return analisi
        
    except Exception as e:
        logger.error(f"Errore nell'analisi pattern accessi guest: {str(e)}")
        return {}

def genera_raccomandazioni_ai(analisi):
    """
    Genera raccomandazioni AI basate sull'analisi dei pattern.
    
    Args:
        analisi (dict): Risultati dell'analisi pattern
        
    Returns:
        list: Lista di raccomandazioni
    """
    raccomandazioni = []
    
    try:
        totali = analisi.get('totali', 0)
        if totali == 0:
            return raccomandazioni
        
        # Calcola percentuali
        pct_scaduti = (analisi.get('scaduti', 0) / totali) * 100
        pct_non_registrati = (analisi.get('non_registrati', 0) / totali) * 100
        pct_download = (analisi.get('con_download', 0) / totali) * 100
        
        # Raccomandazioni basate su percentuali
        if pct_scaduti > 20:
            raccomandazioni.append({
                'tipo': 'pulizia',
                'severita': 'critico',
                'messaggio': f"🧹 {pct_scaduti:.1f}% degli accessi sono scaduti. Considera una pulizia automatica.",
                'azione': 'cleanup_expired'
            })
        
        if pct_non_registrati > 30:
            raccomandazioni.append({
                'tipo': 'inviti',
                'severita': 'attenzione',
                'messaggio': f"📧 {pct_non_registrati:.1f}% dei guest non si sono registrati. Valuta reinvio inviti.",
                'azione': 'resend_invites'
            })
        
        if pct_download > 80:
            raccomandazioni.append({
                'tipo': 'sicurezza',
                'severita': 'info',
                'messaggio': f"🔒 {pct_download:.1f}% degli accessi hanno permesso download. Verifica necessità.",
                'azione': 'review_permissions'
            })
        
        # Raccomandazioni per attività recente
        if analisi.get('creati_ultimi_7gg', 0) > 10:
            raccomandazioni.append({
                'tipo': 'attivita',
                'severita': 'info',
                'messaggio': f"📈 Alta attività: {analisi['creati_ultimi_7gg']} nuovi accessi questa settimana.",
                'azione': 'monitor_activity'
            })
        
        return raccomandazioni
        
    except Exception as e:
        logger.error(f"Errore nella generazione raccomandazioni AI: {str(e)}")
        return []


def suggerisci_documenti_da_caricare():
    """
    Suggerisce documenti approvati ma non ancora caricati su Google Drive.
    
    Returns:
        list: Lista di dizionari con documento e motivo
    """
    from models import Document
    
    # Documenti firmati dal CEO ma non caricati su Drive
    da_caricare = Document.query.filter(
        Document.firmato_ceo == True,
        Document.drive_uploaded_at == None
    ).all()
    
    suggeriti = []
    for doc in da_caricare:
        motivo = "✅ Approvato ma non caricato su Drive"
        
        # Controlla approvazioni intermedie
        if not doc.approvato_da_responsabile:
            motivo = "⚠️ Mancano approvazioni intermedie"
        elif not doc.approvato_da_admin:
            motivo = "⚠️ Mancano approvazioni amministrative"
        
        # Controlla se il file esiste fisicamente
        import os
        from flask import current_app
        file_path = os.path.join(current_app.config["UPLOAD_FOLDER"], doc.path)
        if not os.path.exists(file_path):
            motivo = "❌ File fisico non trovato"
        
        suggeriti.append({
            "doc": doc,
            "motivo": motivo,
            "priorita": "alta" if "❌" in motivo else "media"
        })
    
    return suggeriti


def analizza_stato_drive_ai():
    """
    Analizza lo stato generale dei documenti su Google Drive.
    
    Returns:
        dict: Statistiche e raccomandazioni per Drive
    """
    from models import Document
    
    # Statistiche generali
    totali = Document.query.count()
    su_drive = Document.query.filter(Document.drive_uploaded_at.isnot(None)).count()
    da_caricare = Document.query.filter(
        Document.firmato_ceo == True,
        Document.drive_uploaded_at == None
    ).count()
    
    # Documenti con errori
    con_errori = Document.query.filter(
        Document.drive_status_note.like('%❌%')
    ).count()
    
    return {
        'totali': totali,
        'su_drive': su_drive,
        'da_caricare': da_caricare,
        'con_errori': con_errori,
        'percentuale_completamento': round((su_drive / totali * 100) if totali > 0 else 0, 1)
    }


def analizza_documenti_obsoleti():
    """
    Analizza documenti per identificare quelli obsoleti, da revisionare o duplicati.
    
    Returns:
        list: Lista di suggerimenti AI per revisione documenti
    """
    from datetime import datetime, timedelta
    from models import Document
    
    oggi = datetime.utcnow()
    suggerimenti = []
    
    try:
        # Ottieni tutti i documenti
        documenti = Document.query.all()
        
        for doc in documenti:
            # Calcola ultimo accesso/download
            last_download = doc.uploaded_at  # Default alla data di upload
            
            # Se ci sono download logs, usa il più recente
            if hasattr(doc, 'download_logs') and doc.download_logs:
                download_timestamps = [d.timestamp for d in doc.download_logs if hasattr(d, 'timestamp')]
                if download_timestamps:
                    last_download = max(download_timestamps)
            
            # Calcola giorni di inattività
            giorni_inattivo = (oggi - last_download).days
            
            # === DOCUMENTI OBSOLETI (> 1 anno) ===
            if giorni_inattivo > 365:
                suggerimenti.append({
                    "tipo": "🛑 Obsoleto",
                    "severita": "critico",
                    "documento": doc,
                    "motivo": f"Non è stato visualizzato o scaricato da {giorni_inattivo} giorni",
                    "giorni_inattivo": giorni_inattivo,
                    "azione_suggerita": "archivia"
                })
            
            # === DOCUMENTI DA REVISIONARE (> 6 mesi per procedure/policy) ===
            elif giorni_inattivo > 180:
                tipo_doc = doc.tipo.lower() if hasattr(doc, 'tipo') and doc.tipo else ""
                if tipo_doc in ["procedura", "policy", "modulo", "procedura", "politica"]:
                    suggerimenti.append({
                        "tipo": "🔁 Da revisionare",
                        "severita": "media",
                        "documento": doc,
                        "motivo": f"È una {tipo_doc} non aggiornata da {giorni_inattivo} giorni",
                        "giorni_inattivo": giorni_inattivo,
                        "azione_suggerita": "revisiona"
                    })
            
            # === DOCUMENTI INATTIVI (> 3 mesi) ===
            elif giorni_inattivo > 90:
                suggerimenti.append({
                    "tipo": "⚠️ Inattivo",
                    "severita": "bassa",
                    "documento": doc,
                    "motivo": f"Non accesso da {giorni_inattivo} giorni",
                    "giorni_inattivo": giorni_inattivo,
                    "azione_suggerita": "monitora"
                })
            
            # === RICERCA DUPLICATI ===
            if hasattr(doc, 'name') and doc.name:
                # Cerca documenti con nomi simili nella stessa azienda
                duplicati = Document.query.filter(
                    Document.id != doc.id,
                    Document.name.ilike(f"%{doc.name}%"),
                    Document.company_id == doc.company_id if hasattr(doc, 'company_id') else True
                ).all()
                
                if duplicati:
                    suggerimenti.append({
                        "tipo": "⚠️ Possibile duplicato",
                        "severita": "media",
                        "documento": doc,
                        "motivo": f"Trovati {len(duplicati)} documenti con nomi simili",
                        "duplicati": duplicati,
                        "azione_suggerita": "verifica"
                    })
            
            # === DOCUMENTI MAI APPROVATI ===
            if hasattr(doc, 'validazione_ceo') and not doc.validazione_ceo:
                if (oggi - doc.created_at).days > 30:
                    suggerimenti.append({
                        "tipo": "❌ Mai approvato",
                        "severita": "media",
                        "documento": doc,
                        "motivo": "Documento creato da più di 30 giorni ma mai approvato",
                        "giorni_inattivo": (oggi - doc.created_at).days,
                        "azione_suggerita": "approva_o_archivia"
                    })
        
        # Ordina per severità e giorni di inattività
        suggerimenti.sort(key=lambda x: (
            {"critico": 3, "media": 2, "bassa": 1}.get(x["severita"], 0),
            x.get("giorni_inattivo", 0)
        ), reverse=True)
        
        logger.info(f"Analisi documenti obsoleti completata: {len(suggerimenti)} suggerimenti trovati")
        return suggerimenti
        
    except Exception as e:
        logger.error(f"Errore nell'analisi documenti obsoleti: {str(e)}")
        return []


def analizza_statistiche_revisione():
    """
    Analizza statistiche generali per la revisione documenti.
    
    Returns:
        dict: Statistiche per la dashboard di revisione
    """
    from models import Document
    from datetime import datetime, timedelta
    
    oggi = datetime.utcnow()
    
    try:
        totali = Document.query.count()
        obsoleti = 0
        da_revisionare = 0
        inattivi = 0
        mai_approvati = 0
        
        documenti = Document.query.all()
        
        for doc in documenti:
            # Calcola ultimo accesso
            last_download = doc.uploaded_at
            if hasattr(doc, 'download_logs') and doc.download_logs:
                download_timestamps = [d.timestamp for d in doc.download_logs if hasattr(d, 'timestamp')]
                if download_timestamps:
                    last_download = max(download_timestamps)
            
            giorni_inattivo = (oggi - last_download).days
            
            # Conta per categoria
            if giorni_inattivo > 365:
                obsoleti += 1
            elif giorni_inattivo > 180:
                da_revisionare += 1
            elif giorni_inattivo > 90:
                inattivi += 1
            
            # Conta mai approvati
            if hasattr(doc, 'validazione_ceo') and not doc.validazione_ceo:
                if (oggi - doc.created_at).days > 30:
                    mai_approvati += 1
        
        return {
            'totali': totali,
            'obsoleti': obsoleti,
            'da_revisionare': da_revisionare,
            'inattivi': inattivi,
            'mai_approvati': mai_approvati,
            'percentuale_obsoleti': round((obsoleti / totali * 100) if totali > 0 else 0, 1)
        }
        
    except Exception as e:
        logger.error(f"Errore nell'analisi statistiche revisione: {str(e)}")
        return {} 