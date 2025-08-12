"""
API per File Manager - Gestione file e cartelle con preview e azioni batch.
"""

import os
import json
import mimetypes
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path

from flask import Blueprint, request, jsonify, current_app, send_file, abort
from flask_login import login_required, current_user
from sqlalchemy import and_, or_, func, desc
from sqlalchemy.orm import joinedload

from extensions import db
from models import Document, Company, Department, User, SecurityAuditLog, Tag
from decorators import admin_required
from utils.audit_utils import log_audit_event

files_api = Blueprint('files_api', __name__, url_prefix='/api/files')


def get_user_permissions(user: User) -> Dict[str, Any]:
    """
    Ottiene i permessi dell'utente per filtrare i file.
    
    Args:
        user: Utente corrente
        
    Returns:
        Dict con permessi: companies, departments, is_admin
    """
    if user.role in ['admin', 'superadmin']:
        return {
            'companies': None,  # Tutte le aziende
            'departments': None,  # Tutti i reparti
            'is_admin': True
        }
    
    return {
        'companies': [c.id for c in user.companies] if user.companies else [],
        'departments': [d.id for d in user.departments] if user.departments else [],
        'is_admin': False
    }


def apply_rbac_filters(query, user_permissions: Dict[str, Any]):
    """
    Applica filtri RBAC alla query.
    
    Args:
        query: Query SQLAlchemy
        user_permissions: Permessi utente
        
    Returns:
        Query filtrata
    """
    if user_permissions['is_admin']:
        return query
    
    # Filtra per aziende e reparti dell'utente
    filters = []
    
    if user_permissions['companies']:
        filters.append(Document.company_id.in_(user_permissions['companies']))
    
    if user_permissions['departments']:
        filters.append(Document.department_id.in_(user_permissions['departments']))
    
    if filters:
        return query.filter(or_(*filters))
    
    return query


@files_api.route('/tree', methods=['GET'])
@login_required
def get_file_tree():
    """
    Ottiene l'alberatura dei file organizzata per azienda/reparto/cartelle.
    
    Query params:
        azienda_id: ID azienda (opzionale)
        reparto_id: ID reparto (opzionale)
        path: Percorso cartella (opzionale)
        
    Returns:
        JSON con struttura tree
    """
    try:
        user_permissions = get_user_permissions(current_user)
        
        # Parametri query
        azienda_id = request.args.get('azienda_id', type=int)
        reparto_id = request.args.get('reparto_id', type=int)
        path = request.args.get('path', '').strip()
        
        # Query base
        query = db.session.query(
            Document.company_id,
            Document.department_id,
            func.count(Document.id).label('file_count')
        ).group_by(Document.company_id, Document.department_id)
        
        # Applica filtri
        if azienda_id:
            query = query.filter(Document.company_id == azienda_id)
        
        if reparto_id:
            query = query.filter(Document.department_id == reparto_id)
        
        # Applica RBAC
        query = apply_rbac_filters(query, user_permissions)
        
        # Esegui query
        results = query.all()
        
        # Costruisci struttura tree
        tree = {
            'companies': {},
            'total_files': 0
        }
        
        for company_id, department_id, file_count in results:
            if company_id not in tree['companies']:
                company = Company.query.get(company_id)
                if company:
                    tree['companies'][company_id] = {
                        'id': company_id,
                        'name': company.name,
                        'departments': {},
                        'file_count': 0
                    }
            
            if company_id in tree['companies']:
                if department_id not in tree['companies'][company_id]['departments']:
                    department = Department.query.get(department_id)
                    if department:
                        tree['companies'][company_id]['departments'][department_id] = {
                            'id': department_id,
                            'name': department.name,
                            'file_count': file_count
                        }
                        tree['companies'][company_id]['file_count'] += file_count
                        tree['total_files'] += file_count
        
        # Converti in lista per JSON
        tree['companies'] = list(tree['companies'].values())
        for company in tree['companies']:
            company['departments'] = list(company['departments'].values())
        
        return jsonify({
            'success': True,
            'data': tree
        })
        
    except Exception as e:
        current_app.logger.error(f"Errore API tree: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@files_api.route('/list', methods=['GET'])
@login_required
def get_file_list():
    """
    Ottiene lista paginata dei file con filtri.
    
    Query params:
        azienda_id: ID azienda (opzionale)
        reparto_id: ID reparto (opzionale)
        path: Percorso cartella (opzionale)
        q: Ricerca testuale (opzionale)
        tag: Tag specifico (opzionale)
        type: Tipo file (pdf, doc, xls, img) (opzionale)
        status: Status (attivo, scaduto) (opzionale)
        page: Numero pagina (default: 1)
        page_size: Dimensione pagina (default: 25)
        
    Returns:
        JSON con lista paginata e metadati
    """
    try:
        user_permissions = get_user_permissions(current_user)
        
        # Parametri query
        azienda_id = request.args.get('azienda_id', type=int)
        reparto_id = request.args.get('reparto_id', type=int)
        path = request.args.get('path', '').strip()
        q = request.args.get('q', '').strip()
        tag = request.args.get('tag', '').strip()
        file_type = request.args.get('type', '').strip()
        status = request.args.get('status', '').strip()
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('page_size', 25, type=int)
        
        # Query base con join
        query = Document.query.options(
            joinedload(Document.user),
            joinedload(Document.company),
            joinedload(Document.department)
        )
        
        # Applica filtri
        if azienda_id:
            query = query.filter(Document.company_id == azienda_id)
        
        if reparto_id:
            query = query.filter(Document.department_id == reparto_id)
        
        if q:
            # Ricerca su titolo, descrizione, nome file
            search_filter = or_(
                Document.title.ilike(f'%{q}%'),
                Document.description.ilike(f'%{q}%'),
                Document.original_filename.ilike(f'%{q}%')
            )
            query = query.filter(search_filter)
        
        if file_type:
            # Filtra per tipo file
            if file_type == 'pdf':
                query = query.filter(Document.original_filename.ilike('%.pdf'))
            elif file_type == 'doc':
                query = query.filter(Document.original_filename.ilike('%.doc%'))
            elif file_type == 'xls':
                query = query.filter(Document.original_filename.ilike('%.xls%'))
            elif file_type == 'img':
                query = query.filter(Document.original_filename.ilike('%.jpg%').or_(
                    Document.original_filename.ilike('%.png%').or_(
                        Document.original_filename.ilike('%.gif%')
                    )
                ))
        
        if status == 'scaduto':
            query = query.filter(Document.expiry_date < datetime.utcnow())
        elif status == 'attivo':
            query = query.filter(
                or_(
                    Document.expiry_date.is_(None),
                    Document.expiry_date >= datetime.utcnow()
                )
            )
        
        # Applica RBAC
        query = apply_rbac_filters(query, user_permissions)
        
        # Ordina per data creazione (più recenti prima)
        query = query.order_by(desc(Document.created_at))
        
        # Paginazione
        pagination = query.paginate(
            page=page,
            per_page=page_size,
            error_out=False
        )
        
        # Serializza risultati
        files = []
        for doc in pagination.items:
            # Calcola hash se presente
            file_hash = None
            if hasattr(doc, 'hashes') and doc.hashes:
                file_hash = doc.hashes[0].value if doc.hashes else None
            
            # Determina tipo file
            file_ext = Path(doc.original_filename).suffix.lower() if doc.original_filename else ''
            mime_type, _ = mimetypes.guess_type(doc.original_filename or '')
            
            file_data = {
                'id': doc.id,
                'name': doc.title or doc.original_filename,
                'original_name': doc.original_filename,
                'size': getattr(doc, 'file_size', 0),  # Se la colonna esiste
                'mimetype': mime_type or 'application/octet-stream',
                'owner': {
                    'id': doc.user.id,
                    'username': doc.user.username,
                    'email': doc.user.email
                } if doc.user else None,
                'company': {
                    'id': doc.company.id,
                    'name': doc.company.name
                } if doc.company else None,
                'department': {
                    'id': doc.department.id,
                    'name': doc.department.name
                } if doc.department else None,
                'tags': [{'id': tag.id, 'name': tag.name, 'color': tag.color} for tag in doc.tags],
                'classification': getattr(doc, 'classification', 'public'),
                'scadenza': doc.expiry_date.isoformat() if doc.expiry_date else None,
                'version': getattr(doc, 'version', 1),
                'created_at': doc.created_at.isoformat(),
                'updated_at': doc.updated_at.isoformat() if hasattr(doc, 'updated_at') else doc.created_at.isoformat(),
                'hash': file_hash,
                'file_ext': file_ext,
                'visibility': doc.visibility,
                'downloadable': doc.downloadable
            }
            files.append(file_data)
        
        return jsonify({
            'success': True,
            'data': {
                'files': files,
                'pagination': {
                    'page': page,
                    'pages': pagination.pages,
                    'per_page': page_size,
                    'total': pagination.total,
                    'has_next': pagination.has_next,
                    'has_prev': pagination.has_prev
                }
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Errore API list: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@files_api.route('/batch', methods=['POST'])
@login_required
def batch_action():
    """
    Esegue azioni batch sui file.
    
    Body:
        action: delete/move/tag_add/tag_remove
        file_ids: Lista ID file
        target_folder: ID cartella destinazione (per move)
        tags: Lista tag (per tag_add/tag_remove)
        
    Returns:
        JSON con risultato operazione
    """
    try:
        data = request.get_json()
        action = data.get('action')
        file_ids = data.get('file_ids', [])
        target_folder = data.get('target_folder')
        tags = data.get('tags', [])
        
        if not file_ids:
            return jsonify({
                'success': False,
                'error': 'Nessun file selezionato'
            }), 400
        
        # Verifica permessi
        user_permissions = get_user_permissions(current_user)
        
        # Ottieni file con permessi
        files_query = Document.query
        files_query = apply_rbac_filters(files_query, user_permissions)
        files = files_query.filter(Document.id.in_(file_ids)).all()
        
        if not files:
            return jsonify({
                'success': False,
                'error': 'Nessun file accessibile trovato'
            }), 403
        
        processed_count = 0
        errors = []
        
        for file in files:
            try:
                if action == 'delete':
                    # Log prima della cancellazione
                    log_audit_event(
                        current_user.id,
                        'file_deleted',
                        'document',
                        file.id,
                        {'filename': file.original_filename, 'title': file.title}
                    )
                    
                    # TODO: Implementare cancellazione fisica del file
                    db.session.delete(file)
                    processed_count += 1
                    
                elif action == 'move':
                    if not target_folder:
                        errors.append(f"Cartella destinazione richiesta per file {file.id}")
                        continue
                    
                    # TODO: Implementare spostamento cartella
                    log_audit_event(
                        current_user.id,
                        'file_moved',
                        'document',
                        file.id,
                        {'target_folder': target_folder}
                    )
                    processed_count += 1
                    
                elif action in ['tag_add', 'tag_remove']:
                    # Gestione tag
                    if action == 'tag_add':
                        for tag_name in tags:
                            tag = Tag.query.filter_by(name=tag_name).first()
                            if not tag:
                                tag = Tag(name=tag_name)
                                db.session.add(tag)
                            
                            if tag not in file.tags:
                                file.tags.append(tag)
                    
                    elif action == 'tag_remove':
                        for tag_name in tags:
                            tag = Tag.query.filter_by(name=tag_name).first()
                            if tag and tag in file.tags:
                                file.tags.remove(tag)
                    
                    log_audit_event(
                        current_user.id,
                        f'file_{action}',
                        'document',
                        file.id,
                        {'tags': tags}
                    )
                    processed_count += 1
                    
            except Exception as e:
                errors.append(f"Errore processando file {file.id}: {str(e)}")
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'data': {
                'processed': processed_count,
                'errors': errors
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Errore API batch: {e}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@files_api.route('/<int:file_id>/meta', methods=['GET'])
@login_required
def get_file_meta(file_id):
    """
    Ottiene metadati completi di un file.
    
    Args:
        file_id: ID del file
        
    Returns:
        JSON con metadati completi e versioni
    """
    try:
        user_permissions = get_user_permissions(current_user)
        
        # Query file con permessi
        query = Document.query.options(
            joinedload(Document.user),
            joinedload(Document.company),
            joinedload(Document.department)
        ).filter(Document.id == file_id)
        
        query = apply_rbac_filters(query, user_permissions)
        file = query.first()
        
        if not file:
            return jsonify({
                'success': False,
                'error': 'File non trovato o accesso negato'
            }), 404
        
        # Ottieni versioni se disponibili
        versions = []
        if hasattr(file, 'versions'):
            for version in file.versions:
                versions.append({
                    'id': version.id,
                    'version_number': version.version_number,
                    'created_at': version.created_at.isoformat(),
                    'created_by': version.created_by.username if version.created_by else None
                })
        
        # Ottieni hash se presente
        file_hash = None
        if hasattr(file, 'hashes') and file.hashes:
            file_hash = file.hashes[0].value if file.hashes else None
        
        # Ottieni scansioni antivirus se presenti
        antivirus_scans = []
        if hasattr(file, 'antivirus_scans'):
            for scan in file.antivirus_scans:
                antivirus_scans.append({
                    'id': scan.id,
                    'engine': scan.engine,
                    'signature': scan.signature,
                    'verdict': scan.verdict.value,
                    'timestamp': scan.ts.isoformat()
                })
        
        meta = {
            'id': file.id,
            'title': file.title,
            'original_filename': file.original_filename,
            'description': file.description,
            'visibility': file.visibility,
            'downloadable': file.downloadable,
            'expiry_date': file.expiry_date.isoformat() if file.expiry_date else None,
            'created_at': file.created_at.isoformat(),
            'updated_at': file.updated_at.isoformat() if hasattr(file, 'updated_at') else file.created_at.isoformat(),
            'classification': getattr(file, 'classification', 'public'),
            'owner': {
                'id': file.user.id,
                'username': file.user.username,
                'email': file.user.email
            } if file.user else None,
            'company': {
                'id': file.company.id,
                'name': file.company.name
            } if file.company else None,
            'department': {
                'id': file.department.id,
                'name': file.department.name
            } if file.department else None,
            'tags': [{'id': tag.id, 'name': tag.name, 'color': tag.color} for tag in file.tags],
            'versions': versions,
            'hash': file_hash,
            'antivirus_scans': antivirus_scans,
            'file_size': getattr(file, 'file_size', 0),
            'mime_type': mimetypes.guess_type(file.original_filename or '')[0] or 'application/octet-stream'
        }
        
        return jsonify({
            'success': True,
            'data': meta
        })
        
    except Exception as e:
        current_app.logger.error(f"Errore API meta file {file_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@files_api.route('/<int:file_id>/preview', methods=['GET'])
@login_required
def get_file_preview(file_id):
    """
    Ottiene preview di un file (PDF, immagine, Office).
    
    Args:
        file_id: ID del file
        
    Returns:
        File preview o JSON con errore
    """
    try:
        user_permissions = get_user_permissions(current_user)
        
        # Query file con permessi
        query = Document.query.filter(Document.id == file_id)
        query = apply_rbac_filters(query, user_permissions)
        file = query.first()
        
        if not file:
            return jsonify({
                'success': False,
                'error': 'File non trovato o accesso negato'
            }), 404
        
        # Determina tipo file
        filename = file.original_filename or file.filename
        if not filename:
            return jsonify({
                'success': False,
                'error': 'Nome file non disponibile'
            }), 400
        
        file_ext = Path(filename).suffix.lower()
        mime_type, _ = mimetypes.guess_type(filename)
        
        # Percorso file fisico
        file_path = os.path.join(current_app.config.get('UPLOAD_FOLDER', 'uploads'), file.filename)
        
        if not os.path.exists(file_path):
            return jsonify({
                'success': False,
                'error': 'File fisico non trovato'
            }), 404
        
        # Log accesso preview
        log_audit_event(
            current_user.id,
            'file_preview',
            'document',
            file.id,
            {'filename': filename, 'mime_type': mime_type}
        )
        
        # Gestione preview per tipo
        if file_ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp']:
            # Immagini: serve direttamente con resize
            return send_file(
                file_path,
                mimetype=mime_type,
                as_attachment=False,
                cache_timeout=300  # 5 minuti cache
            )
        
        elif file_ext == '.pdf':
            # PDF: prima pagina come PNG
            try:
                from services.preview_service import generate_pdf_preview
                preview_path = generate_pdf_preview(file_path, file.id)
                
                if preview_path and os.path.exists(preview_path):
                    return send_file(
                        preview_path,
                        mimetype='image/png',
                        as_attachment=False,
                        cache_timeout=3600  # 1 ora cache
                    )
                else:
                    # Fallback: serve PDF originale
                    return send_file(
                        file_path,
                        mimetype='application/pdf',
                        as_attachment=False,
                        cache_timeout=300
                    )
            except Exception as e:
                current_app.logger.error(f"Errore preview PDF {file_id}: {e}")
                return send_file(
                    file_path,
                    mimetype='application/pdf',
                    as_attachment=False,
                    cache_timeout=300
                )
        
        elif file_ext in ['.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx']:
            # Office: prova conversione PDF
            try:
                from services.preview_service import convert_office_to_pdf, generate_pdf_preview
                pdf_path = convert_office_to_pdf(file_path, file.id)
                
                if pdf_path and os.path.exists(pdf_path):
                    # Genera preview dal PDF convertito
                    preview_path = generate_pdf_preview(pdf_path, f"{file.id}_converted")
                    
                    if preview_path and os.path.exists(preview_path):
                        return send_file(
                            preview_path,
                            mimetype='image/png',
                            as_attachment=False,
                            cache_timeout=3600
                        )
                
                return jsonify({
                    'success': False,
                    'error': 'Nessuna preview disponibile per questo tipo di file'
                }), 404
                
            except Exception as e:
                current_app.logger.error(f"Errore preview Office {file_id}: {e}")
                return jsonify({
                    'success': False,
                    'error': 'Nessuna preview disponibile per questo tipo di file'
                }), 404
        
        else:
            # Altri tipi: nessuna preview
            return jsonify({
                'success': False,
                'error': 'Nessuna preview disponibile per questo tipo di file'
            }), 404
        
    except Exception as e:
        current_app.logger.error(f"Errore API preview file {file_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@files_api.route('/<int:file_id>/meta', methods=['PATCH'])
@login_required
def update_file_meta(file_id):
    """
    Aggiorna metadati di un file.
    
    Args:
        file_id: ID del file
        
    Body:
        title: Nuovo titolo (opzionale)
        description: Nuova descrizione (opzionale)
        classification: Nuova classificazione (opzionale)
        tags: Lista tag (opzionale)
        
    Returns:
        JSON con risultato aggiornamento
    """
    try:
        data = request.get_json()
        
        user_permissions = get_user_permissions(current_user)
        
        # Query file con permessi
        query = Document.query.filter(Document.id == file_id)
        query = apply_rbac_filters(query, user_permissions)
        file = query.first()
        
        if not file:
            return jsonify({
                'success': False,
                'error': 'File non trovato o accesso negato'
            }), 404
        
        # Aggiorna campi se forniti
        updated_fields = []
        
        if 'title' in data and data['title'] != file.title:
            file.title = data['title']
            updated_fields.append('title')
        
        if 'description' in data and data['description'] != file.description:
            file.description = data['description']
            updated_fields.append('description')
        
        if 'classification' in data and hasattr(file, 'classification'):
            file.classification = data['classification']
            updated_fields.append('classification')
        
        if 'tags' in data:
            # Gestione tag
            current_tags = {tag.name for tag in file.tags}
            new_tags = set(data['tags'])
            
            # Rimuovi tag non più presenti
            for tag in list(file.tags):
                if tag.name not in new_tags:
                    file.tags.remove(tag)
            
            # Aggiungi nuovi tag
            for tag_name in new_tags:
                if tag_name not in current_tags:
                    tag = Tag.query.filter_by(name=tag_name).first()
                    if not tag:
                        tag = Tag(name=tag_name)
                        db.session.add(tag)
                    file.tags.append(tag)
            
            updated_fields.append('tags')
        
        if updated_fields:
            # Log aggiornamento
            log_audit_event(
                current_user.id,
                'file_updated',
                'document',
                file.id,
                {'updated_fields': updated_fields, 'data': data}
            )
            
            db.session.commit()
        
        return jsonify({
            'success': True,
            'data': {
                'updated_fields': updated_fields
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Errore API update meta file {file_id}: {e}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@files_api.route('/folders', methods=['POST'])
@login_required
def create_folder():
    """
    Crea una nuova cartella.
    
    Body:
        name: Nome cartella
        parent_id: ID cartella padre (opzionale)
        company_id: ID azienda
        department_id: ID reparto
        
    Returns:
        JSON con cartella creata
    """
    try:
        data = request.get_json()
        name = data.get('name', '').strip()
        parent_id = data.get('parent_id')
        company_id = data.get('company_id')
        department_id = data.get('department_id')
        
        if not name:
            return jsonify({
                'success': False,
                'error': 'Nome cartella richiesto'
            }), 400
        
        # TODO: Implementare sistema cartelle
        # Per ora restituisce errore
        return jsonify({
            'success': False,
            'error': 'Sistema cartelle non ancora implementato'
        }), 501
        
    except Exception as e:
        current_app.logger.error(f"Errore API create folder: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@files_api.route('/move', methods=['POST'])
@login_required
def move_file():
    """
    Sposta un file in una nuova cartella.
    
    Body:
        file_id: ID file
        target_folder_id: ID cartella destinazione
        
    Returns:
        JSON con risultato spostamento
    """
    try:
        data = request.get_json()
        file_id = data.get('file_id')
        target_folder_id = data.get('target_folder_id')
        
        if not file_id or not target_folder_id:
            return jsonify({
                'success': False,
                'error': 'File ID e cartella destinazione richiesti'
            }), 400
        
        user_permissions = get_user_permissions(current_user)
        
        # Query file con permessi
        query = Document.query.filter(Document.id == file_id)
        query = apply_rbac_filters(query, user_permissions)
        file = query.first()
        
        if not file:
            return jsonify({
                'success': False,
                'error': 'File non trovato o accesso negato'
            }), 404
        
        # TODO: Implementare spostamento cartella
        # Per ora logga l'azione
        log_audit_event(
            current_user.id,
            'file_move_requested',
            'document',
            file.id,
            {'target_folder_id': target_folder_id}
        )
        
        return jsonify({
            'success': False,
            'error': 'Sistema cartelle non ancora implementato'
        }), 501
        
    except Exception as e:
        current_app.logger.error(f"Errore API move file: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
