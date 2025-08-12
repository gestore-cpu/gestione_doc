# === QUALITY ROUTES - MODULO QUALITÀ ===
# Gestione certificazioni, documenti qualità, audit, azioni correttive, formazione

from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
import os
import json
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from extensions import db
from models import (
    User, Document, Company, Department, AuditLog, 
    EventoFormazione, PartecipazioneFormazione,
    Certificazione, DocumentoQualita, Audit, AuditChecklist, 
    AzioneCorrettiva, AttestatoFormazione, db
)

# Creazione Blueprint Quality
quality_bp = Blueprint('quality', __name__)

# === MODELLI QUALITY ===
# I modelli sono definiti in models.py e importati sopra

# === ROUTE CERTIFICAZIONI ===

@quality_bp.route('/quality/certificazioni', methods=['GET'])
@login_required
def get_certificazioni():
    """
    Restituisce tutte le certificazioni.
    
    Returns:
        JSON: Lista certificazioni
    """
    try:
        db = db()
        certificazioni = db.query(Certificazione).order_by(Certificazione.created_at.desc()).all()
        
        certificazioni_data = []
        for cert in certificazioni:
            certificazioni_data.append({
                'id': cert.id,
                'nome': cert.nome,
                'tipo': cert.tipo,
                'ente_certificatore': cert.ente_certificatore,
                'data_rilascio': cert.data_rilascio.isoformat(),
                'data_scadenza': cert.data_scadenza.isoformat(),
                'stato': cert.stato,
                'stato_display': cert.stato_display,
                'is_scaduta': cert.is_scaduta,
                'giorni_alla_scadenza': cert.giorni_alla_scadenza,
                'note': cert.note,
                'created_at': cert.created_at.isoformat(),
                'created_by': cert.created_by
            })
        
        return jsonify({
            'success': True,
            'certificazioni': certificazioni_data,
            'count': len(certificazioni_data)
        })
        
    except Exception as e:
        return jsonify({'error': f'Errore recupero certificazioni: {str(e)}'}), 500

@quality_bp.route('/quality/certificazioni', methods=['POST'])
@login_required
def create_certificazione():
    """
    Crea una nuova certificazione.
    
    Returns:
        JSON: Certificazione creata
    """
    try:
        data = request.get_json()
        
        # Validazione dati
        required_fields = ['nome', 'tipo', 'ente_certificatore', 'data_rilascio', 'data_scadenza']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Campo obbligatorio mancante: {field}'}), 400
        
        db = db()
        
        # Creazione certificazione
        certificazione = Certificazione(
            nome=data['nome'],
            tipo=data['tipo'],
            ente_certificatore=data['ente_certificatore'],
            data_rilascio=datetime.strptime(data['data_rilascio'], '%Y-%m-%d').date(),
            data_scadenza=datetime.strptime(data['data_scadenza'], '%Y-%m-%d').date(),
            note=data.get('note'),
            created_by=current_user.id
        )
        
        db.add(certificazione)
        db.commit()
        
        return jsonify({
            'success': True,
            'message': 'Certificazione creata con successo',
            'certificazione': {
                'id': certificazione.id,
                'nome': certificazione.nome,
                'tipo': certificazione.tipo,
                'stato': certificazione.stato
            }
        })
        
    except Exception as e:
        return jsonify({'error': f'Errore creazione certificazione: {str(e)}'}), 500

@quality_bp.route('/quality/certificazioni/<int:id>', methods=['PUT'])
@login_required
def update_certificazione(id):
    """
    Aggiorna una certificazione.
    
    Args:
        id: ID della certificazione
        
    Returns:
        JSON: Certificazione aggiornata
    """
    try:
        data = request.get_json()
        db = db()
        
        certificazione = db.query(Certificazione).filter(Certificazione.id == id).first()
        if not certificazione:
            return jsonify({'error': 'Certificazione non trovata'}), 404
        
        # Aggiornamento campi
        if 'nome' in data:
            certificazione.nome = data['nome']
        if 'tipo' in data:
            certificazione.tipo = data['tipo']
        if 'ente_certificatore' in data:
            certificazione.ente_certificatore = data['ente_certificatore']
        if 'data_rilascio' in data:
            certificazione.data_rilascio = datetime.strptime(data['data_rilascio'], '%Y-%m-%d').date()
        if 'data_scadenza' in data:
            certificazione.data_scadenza = datetime.strptime(data['data_scadenza'], '%Y-%m-%d').date()
        if 'stato' in data:
            certificazione.stato = data['stato']
        if 'note' in data:
            certificazione.note = data['note']
        
        db.commit()
        
        return jsonify({
            'success': True,
            'message': 'Certificazione aggiornata con successo',
            'certificazione': {
                'id': certificazione.id,
                'nome': certificazione.nome,
                'tipo': certificazione.tipo,
                'stato': certificazione.stato
            }
        })
        
    except Exception as e:
        return jsonify({'error': f'Errore aggiornamento certificazione: {str(e)}'}), 500

@quality_bp.route('/quality/certificazioni/<int:id>', methods=['DELETE'])
@login_required
def delete_certificazione(id):
    """
    Disattiva o elimina una certificazione.
    
    Args:
        id: ID della certificazione
        
    Returns:
        JSON: Conferma eliminazione
    """
    try:
        db = db()
        
        certificazione = db.query(Certificazione).filter(Certificazione.id == id).first()
        if not certificazione:
            return jsonify({'error': 'Certificazione non trovata'}), 404
        
        # Disattiva invece di eliminare
        certificazione.stato = 'disattivata'
        db.commit()
        
        return jsonify({
            'success': True,
            'message': 'Certificazione disattivata con successo'
        })
        
    except Exception as e:
        return jsonify({'error': f'Errore eliminazione certificazione: {str(e)}'}), 500

# === ROUTE DOCUMENTI QUALITÀ ===

@quality_bp.route('/quality/documenti', methods=['GET'])
@login_required
def get_documenti_qualita():
    """
    Restituisce i documenti di qualità con filtri.
    
    Args:
        certificazione_id: ID certificazione (opzionale)
        approvato: Stato approvazione (opzionale)
        data_inizio: Data inizio (opzionale)
        data_fine: Data fine (opzionale)
        
    Returns:
        JSON: Lista documenti qualità
    """
    try:
        certificazione_id = request.args.get('certificazione_id', type=int)
        approvato = request.args.get('approvato', type=str)
        data_inizio = request.args.get('data_inizio')
        data_fine = request.args.get('data_fine')
        
        db = db()
        query = db.query(DocumentoQualita)
        
        # Applica filtri
        if certificazione_id:
            query = query.filter(DocumentoQualita.certificazione_id == certificazione_id)
        
        if approvato:
            if approvato.lower() == 'true':
                query = query.filter(DocumentoQualita.approvato == True)
            elif approvato.lower() == 'false':
                query = query.filter(DocumentoQualita.approvato == False)
        
        if data_inizio:
            data_inizio = datetime.strptime(data_inizio, '%Y-%m-%d').date()
            query = query.filter(DocumentoQualita.created_at >= data_inizio)
        
        if data_fine:
            data_fine = datetime.strptime(data_fine, '%Y-%m-%d').date()
            query = query.filter(DocumentoQualita.created_at <= data_fine)
        
        documenti = query.order_by(DocumentoQualita.created_at.desc()).all()
        
        documenti_data = []
        for doc in documenti:
            documenti_data.append({
                'id': doc.id,
                'titolo': doc.titolo,
                'versione': doc.versione,
                'certificazione_id': doc.certificazione_id,
                'certificazione_nome': doc.certificazione.nome if doc.certificazione else None,
                'filename': doc.filename,
                'original_filename': doc.original_filename,
                'approvato': doc.approvato,
                'approvato_da': doc.approvato_da,
                'data_approvazione': doc.data_approvazione.isoformat() if doc.data_approvazione else None,
                'created_at': doc.created_at.isoformat(),
                'created_by': doc.created_by
            })
        
        return jsonify({
            'success': True,
            'documenti': documenti_data,
            'count': len(documenti_data)
        })
        
    except Exception as e:
        return jsonify({'error': f'Errore recupero documenti qualità: {str(e)}'}), 500

@quality_bp.route('/quality/documenti', methods=['POST'])
@login_required
def upload_documento_qualita():
    """
    Carica un nuovo documento di qualità.
    
    Returns:
        JSON: Documento caricato
    """
    try:
        # Verifica se è presente un file
        if 'file' not in request.files:
            return jsonify({'error': 'Nessun file caricato'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'Nessun file selezionato'}), 400
        
        # Validazione dati
        titolo = request.form.get('titolo')
        versione = request.form.get('versione')
        certificazione_id = request.form.get('certificazione_id', type=int)
        
        if not titolo or not versione or not certificazione_id:
            return jsonify({'error': 'Campi obbligatori mancanti'}), 400
        
        db = db()
        
        # Verifica certificazione esistente
        certificazione = db.query(Certificazione).filter(Certificazione.id == certificazione_id).first()
        if not certificazione:
            return jsonify({'error': 'Certificazione non trovata'}), 404
        
        # Salvataggio file
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"qualita_{timestamp}_{filename}"
        
        upload_folder = os.path.join(current_app.config['UPLOAD_FOLDER'], 'quality')
        os.makedirs(upload_folder, exist_ok=True)
        
        file_path = os.path.join(upload_folder, filename)
        file.save(file_path)
        
        # Creazione documento qualità
        documento = DocumentoQualita(
            titolo=titolo,
            versione=versione,
            certificazione_id=certificazione_id,
            filename=filename,
            original_filename=file.filename,
            created_by=current_user.id
        )
        
        db.add(documento)
        db.commit()
        
        return jsonify({
            'success': True,
            'message': 'Documento qualità caricato con successo',
            'documento': {
                'id': documento.id,
                'titolo': documento.titolo,
                'versione': documento.versione,
                'filename': documento.filename
            }
        })
        
    except Exception as e:
        return jsonify({'error': f'Errore caricamento documento: {str(e)}'}), 500

# === ROUTE AUDIT ===

@quality_bp.route('/quality/audit', methods=['GET'])
@login_required
def get_audit():
    """
    Restituisce la lista degli audit con stato.
    
    Returns:
        JSON: Lista audit
    """
    try:
        db = db()
        audit_list = db.query(Audit).order_by(Audit.created_at.desc()).all()
        
        audit_data = []
        for audit in audit_list:
            audit_data.append({
                'id': audit.id,
                'titolo': audit.titolo,
                'tipo': audit.tipo,
                'data_inizio': audit.data_inizio.isoformat(),
                'data_fine': audit.data_fine.isoformat() if audit.data_fine else None,
                'auditor': audit.auditor,
                'stato': audit.stato,
                'note': audit.note,
                'created_at': audit.created_at.isoformat(),
                'created_by': audit.created_by
            })
        
        return jsonify({
            'success': True,
            'audit': audit_data,
            'count': len(audit_data)
        })
        
    except Exception as e:
        return jsonify({'error': f'Errore recupero audit: {str(e)}'}), 500

@quality_bp.route('/quality/audit', methods=['POST'])
@login_required
def create_audit():
    """
    Crea un nuovo audit.
    
    Returns:
        JSON: Audit creato
    """
    try:
        data = request.get_json()
        
        # Validazione dati
        required_fields = ['titolo', 'tipo', 'data_inizio', 'auditor']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Campo obbligatorio mancante: {field}'}), 400
        
        db = db()
        
        # Creazione audit
        audit = Audit(
            titolo=data['titolo'],
            tipo=data['tipo'],
            data_inizio=datetime.strptime(data['data_inizio'], '%Y-%m-%d').date(),
            data_fine=datetime.strptime(data['data_fine'], '%Y-%m-%d').date() if data.get('data_fine') else None,
            auditor=data['auditor'],
            note=data.get('note'),
            created_by=current_user.id
        )
        
        db.add(audit)
        db.commit()
        
        return jsonify({
            'success': True,
            'message': 'Audit creato con successo',
            'audit': {
                'id': audit.id,
                'titolo': audit.titolo,
                'tipo': audit.tipo,
                'stato': audit.stato
            }
        })
        
    except Exception as e:
        return jsonify({'error': f'Errore creazione audit: {str(e)}'}), 500

@quality_bp.route('/quality/audit/<int:id>/checklist', methods=['POST'])
@login_required
def add_audit_checklist(id):
    """
    Inserisce checklist per un audit.
    
    Args:
        id: ID dell'audit
        
    Returns:
        JSON: Checklist aggiunta
    """
    try:
        data = request.get_json()
        
        if 'domande' not in data or not isinstance(data['domande'], list):
            return jsonify({'error': 'Campo domande obbligatorio e deve essere una lista'}), 400
        
        db = db()
        
        # Verifica audit esistente
        audit = db.query(Audit).filter(Audit.id == id).first()
        if not audit:
            return jsonify({'error': 'Audit non trovato'}), 404
        
        # Aggiunta elementi checklist
        checklist_items = []
        for domanda in data['domande']:
            item = AuditChecklist(
                audit_id=id,
                domanda=domanda
            )
            db.add(item)
            checklist_items.append(item)
        
        db.commit()
        
        return jsonify({
            'success': True,
            'message': f'Checklist aggiunta con successo ({len(checklist_items)} elementi)',
            'checklist_items': [
                {
                    'id': item.id,
                    'domanda': item.domanda,
                    'risposta': item.risposta
                } for item in checklist_items
            ]
        })
        
    except Exception as e:
        return jsonify({'error': f'Errore aggiunta checklist: {str(e)}'}), 500

# === ROUTE AZIONI CORRETTIVE ===

@quality_bp.route('/quality/azioni-correttive', methods=['GET'])
@login_required
def get_azioni_correttive():
    """
    Restituisce le azioni correttive con filtri.
    
    Args:
        stato: Stato azione (opzionale)
        assegnato_a: ID utente assegnato (opzionale)
        priorita: Priorità (opzionale)
        
    Returns:
        JSON: Lista azioni correttive
    """
    try:
        stato = request.args.get('stato')
        assegnato_a = request.args.get('assegnato_a', type=int)
        priorita = request.args.get('priorita')
        
        db = db()
        query = db.query(AzioneCorrettiva)
        
        # Applica filtri
        if stato:
            query = query.filter(AzioneCorrettiva.stato == stato)
        
        if assegnato_a:
            query = query.filter(AzioneCorrettiva.assegnato_a == assegnato_a)
        
        if priorita:
            query = query.filter(AzioneCorrettiva.priorita == priorita)
        
        azioni = query.order_by(AzioneCorrettiva.data_scadenza.asc()).all()
        
        azioni_data = []
        for azione in azioni:
            azioni_data.append({
                'id': azione.id,
                'titolo': azione.titolo,
                'descrizione': azione.descrizione,
                'audit_id': azione.audit_id,
                'documento_id': azione.documento_id,
                'formazione_id': azione.formazione_id,
                'assegnato_a': azione.assegnato_a,
                'assegnato_nome': azione.assegnato_user.username if azione.assegnato_user else None,
                'priorita': azione.priorita,
                'stato': azione.stato,
                'data_scadenza': azione.data_scadenza.isoformat(),
                'data_completamento': azione.data_completamento.isoformat() if azione.data_completamento else None,
                'is_scaduta': azione.is_scaduta,
                'giorni_alla_scadenza': azione.giorni_alla_scadenza,
                'note': azione.note,
                'created_at': azione.created_at.isoformat(),
                'created_by': azione.created_by
            })
        
        return jsonify({
            'success': True,
            'azioni': azioni_data,
            'count': len(azioni_data)
        })
        
    except Exception as e:
        return jsonify({'error': f'Errore recupero azioni correttive: {str(e)}'}), 500

@quality_bp.route('/quality/azioni-correttive', methods=['POST'])
@login_required
def create_azione_correttiva():
    """
    Crea una nuova azione correttiva.
    
    Returns:
        JSON: Azione correttiva creata
    """
    try:
        data = request.get_json()
        
        # Validazione dati
        required_fields = ['titolo', 'descrizione', 'assegnato_a', 'data_scadenza']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Campo obbligatorio mancante: {field}'}), 400
        
        db = db()
        
        # Verifica utente assegnato
        assegnato_user = db.query(User).filter(User.id == data['assegnato_a']).first()
        if not assegnato_user:
            return jsonify({'error': 'Utente assegnato non trovato'}), 404
        
        # Creazione azione correttiva
        azione = AzioneCorrettiva(
            titolo=data['titolo'],
            descrizione=data['descrizione'],
            audit_id=data.get('audit_id'),
            documento_id=data.get('documento_id'),
            formazione_id=data.get('formazione_id'),
            assegnato_a=data['assegnato_a'],
            priorita=data.get('priorita', 'media'),
            data_scadenza=datetime.strptime(data['data_scadenza'], '%Y-%m-%d').date(),
            note=data.get('note'),
            created_by=current_user.id
        )
        
        db.add(azione)
        db.commit()
        
        return jsonify({
            'success': True,
            'message': 'Azione correttiva creata con successo',
            'azione': {
                'id': azione.id,
                'titolo': azione.titolo,
                'stato': azione.stato,
                'assegnato_a': azione.assegnato_a
            }
        })
        
    except Exception as e:
        return jsonify({'error': f'Errore creazione azione correttiva: {str(e)}'}), 500

# === ROUTE FORMAZIONE ===

@quality_bp.route('/quality/formazione/eventi', methods=['GET'])
@login_required
def get_eventi_formazione():
    """
    Restituisce la lista degli eventi formativi.
    
    Returns:
        JSON: Lista eventi formazione
    """
    try:
        db = db()
        eventi = db.query(EventoFormazione).order_by(EventoFormazione.data_evento.desc()).all()
        
        eventi_data = []
        for evento in eventi:
            eventi_data.append({
                'id': evento.id,
                'titolo': evento.titolo,
                'descrizione': evento.descrizione,
                'data_evento': evento.data_evento.isoformat() if evento.data_evento else None,
                'durata_ore': evento.durata_ore,
                'luogo': evento.luogo,
                'trainer': evento.trainer,
                'max_partecipanti': evento.max_partecipanti,
                'stato': evento.stato,
                'partecipanti_totali': evento.partecipanti_totali,
                'partecipanti_firmati': evento.partecipanti_firmati,
                'attestati_completati': evento.attestati_completati,
                'percentuale_copertura': evento.percentuale_copertura,
                'stato_copertura': evento.stato_copertura,
                'created_at': evento.created_at.isoformat()
            })
        
        return jsonify({
            'success': True,
            'eventi': eventi_data,
            'count': len(eventi_data)
        })
        
    except Exception as e:
        return jsonify({'error': f'Errore recupero eventi formazione: {str(e)}'}), 500

@quality_bp.route('/quality/formazione/eventi', methods=['POST'])
@login_required
def create_evento_formazione():
    """
    Crea un nuovo evento formativo.
    
    Returns:
        JSON: Evento creato
    """
    try:
        data = request.get_json()
        
        # Validazione dati
        required_fields = ['titolo', 'data_evento']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Campo obbligatorio mancante: {field}'}), 400
        
        db = db()
        
        # Creazione evento
        evento = EventoFormazione(
            titolo=data['titolo'],
            descrizione=data.get('descrizione'),
            data_evento=datetime.strptime(data['data_evento'], '%Y-%m-%d %H:%M:%S') if 'T' not in data['data_evento'] else datetime.fromisoformat(data['data_evento'].replace('Z', '+00:00')),
            durata_ore=data.get('durata_ore', 1),
            luogo=data.get('luogo'),
            trainer=data.get('trainer'),
            max_partecipanti=data.get('max_partecipanti'),
            stato=data.get('stato', 'programmato')
        )
        
        db.add(evento)
        db.commit()
        
        return jsonify({
            'success': True,
            'message': 'Evento formativo creato con successo',
            'evento': {
                'id': evento.id,
                'titolo': evento.titolo,
                'data_evento': evento.data_evento.isoformat() if evento.data_evento else None,
                'stato': evento.stato
            }
        })
        
    except Exception as e:
        return jsonify({'error': f'Errore creazione evento formazione: {str(e)}'}), 500

@quality_bp.route('/quality/formazione/attestati', methods=['POST'])
@login_required
def save_attestato_formazione():
    """
    Salva un attestato PDF per un utente su un evento.
    
    Returns:
        JSON: Attestato salvato
    """
    try:
        # Verifica se è presente un file
        if 'file' not in request.files:
            return jsonify({'error': 'Nessun file caricato'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'Nessun file selezionato'}), 400
        
        # Validazione dati
        evento_id = request.form.get('evento_id', type=int)
        user_id = request.form.get('user_id', type=int)
        data_rilascio = request.form.get('data_rilascio')
        
        if not evento_id or not user_id or not data_rilascio:
            return jsonify({'error': 'Campi obbligatori mancanti'}), 400
        
        db = db()
        
        # Verifica evento e utente
        evento = db.query(EventoFormazione).filter(EventoFormazione.id == evento_id).first()
        if not evento:
            return jsonify({'error': 'Evento formazione non trovato'}), 404
        
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return jsonify({'error': 'Utente non trovato'}), 404
        
        # Salvataggio file
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"attestato_{evento_id}_{user_id}_{timestamp}_{filename}"
        
        upload_folder = os.path.join(current_app.config['UPLOAD_FOLDER'], 'attestati')
        os.makedirs(upload_folder, exist_ok=True)
        
        file_path = os.path.join(upload_folder, filename)
        file.save(file_path)
        
        # Creazione attestato
        attestato = AttestatoFormazione(
            evento_id=evento_id,
            user_id=user_id,
            filename=filename,
            data_rilascio=datetime.strptime(data_rilascio, '%Y-%m-%d').date(),
            firmato_da=current_user.username,
            note=request.form.get('note')
        )
        
        db.add(attestato)
        db.commit()
        
        return jsonify({
            'success': True,
            'message': 'Attestato salvato con successo',
            'attestato': {
                'id': attestato.id,
                'evento_id': attestato.evento_id,
                'user_id': attestato.user_id,
                'filename': attestato.filename,
                'data_rilascio': attestato.data_rilascio.isoformat()
            }
        })
        
    except Exception as e:
        return jsonify({'error': f'Errore salvataggio attestato: {str(e)}'}), 500

# === ROUTE UTILITY ===

@quality_bp.route('/quality/stats', methods=['GET'])
@login_required
def get_quality_stats():
    """
    Restituisce statistiche del modulo qualità.
    
    Returns:
        JSON: Statistiche qualità
    """
    try:
        db = db()
        
        # Statistiche certificazioni
        certificazioni_totali = db.query(Certificazione).count()
        certificazioni_attive = db.query(Certificazione).filter(Certificazione.stato == 'attiva').count()
        certificazioni_scadute = db.query(Certificazione).filter(Certificazione.stato == 'scaduta').count()
        
        # Statistiche audit
        audit_totali = db.query(Audit).count()
        audit_programmati = db.query(Audit).filter(Audit.stato == 'programmato').count()
        audit_in_corso = db.query(Audit).filter(Audit.stato == 'in_corso').count()
        audit_completati = db.query(Audit).filter(Audit.stato == 'completato').count()
        
        # Statistiche azioni correttive
        azioni_totali = db.query(AzioneCorrettiva).count()
        azioni_aperte = db.query(AzioneCorrettiva).filter(AzioneCorrettiva.stato == 'aperta').count()
        azioni_in_corso = db.query(AzioneCorrettiva).filter(AzioneCorrettiva.stato == 'in_corso').count()
        azioni_completate = db.query(AzioneCorrettiva).filter(AzioneCorrettiva.stato == 'completata').count()
        
        # Statistiche formazione
        eventi_totali = db.query(EventoFormazione).count()
        eventi_programmati = db.query(EventoFormazione).filter(EventoFormazione.stato == 'programmato').count()
        eventi_completati = db.query(EventoFormazione).filter(EventoFormazione.stato == 'completato').count()
        
        return jsonify({
            'success': True,
            'stats': {
                'certificazioni': {
                    'totali': certificazioni_totali,
                    'attive': certificazioni_attive,
                    'scadute': certificazioni_scadute
                },
                'audit': {
                    'totali': audit_totali,
                    'programmati': audit_programmati,
                    'in_corso': audit_in_corso,
                    'completati': audit_completati
                },
                'azioni_correttive': {
                    'totali': azioni_totali,
                    'aperte': azioni_aperte,
                    'in_corso': azioni_in_corso,
                    'completate': azioni_completate
                },
                'formazione': {
                    'eventi_totali': eventi_totali,
                    'eventi_programmati': eventi_programmati,
                    'eventi_completati': eventi_completati
                }
            }
        })
        
    except Exception as e:
        return jsonify({'error': f'Errore recupero statistiche: {str(e)}'}), 500 