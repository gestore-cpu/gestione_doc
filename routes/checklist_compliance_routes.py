from flask import Blueprint, request, jsonify, render_template, flash, redirect, url_for, current_app, send_file
from flask_login import login_required, current_user
from functools import wraps
from datetime import datetime
from models import db, ChecklistCompliance, Document
from utils.audit_logger import log_event
import json
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
import qrcode

# Blueprint per checklist compliance
checklist_compliance_bp = Blueprint('checklist_compliance', __name__, url_prefix='/checklist_compliance')

def roles_required(roles):
    """Decorator per verificare i ruoli dell'utente."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return jsonify({'error': 'Non autorizzato'}), 401
            
            if current_user.role not in roles:
                return jsonify({'error': 'Accesso negato'}), 403
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def log_checklist_action(azione, checklist_id=None, dettagli=None):
    """Log automatico per audit compliance."""
    try:
        log_entry = {
            'azione': azione,
            'checklist_id': checklist_id,
            'user_id': current_user.id,
            'user_name': f"{current_user.first_name} {current_user.last_name}" if current_user.first_name and current_user.last_name else current_user.username,
            'dettagli': dettagli,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # Log nell'audit logger esistente
        log_event(
            user_id=current_user.id,
            document_id=dettagli.get('documento_id') if dettagli else None,
            azione=f"checklist_compliance_{azione}",
            note=json.dumps(log_entry)
        )
        
        current_app.logger.info(f"Checklist compliance {azione}: {log_entry}")
    except Exception as e:
        current_app.logger.error(f"Errore nel logging checklist compliance: {str(e)}")

@checklist_compliance_bp.route('/documento/<int:documento_id>', methods=['GET'])
@login_required
@roles_required(['admin', 'ceo', 'hr', 'auditor', 'quality_manager'])
def lista_checklist(documento_id):
    """
    Elenco checklist compliance per un documento specifico.
    
    Args:
        documento_id (int): ID del documento
        
    Returns:
        JSON: Lista delle checklist compliance
    """
    try:
        # Verifica esistenza documento
        documento = Document.query.get_or_404(documento_id)
        
        # Recupera checklist per il documento
        checklist = ChecklistCompliance.query.filter_by(documento_id=documento_id).all()
        
        # Prepara dati per JSON
        checklist_data = []
        for voce in checklist:
            checklist_data.append({
                'id': voce.id,
                'tipo_standard': voce.tipo_standard,
                'tipo_standard_display': voce.tipo_standard_display,
                'voce': voce.voce,
                'is_completa': voce.is_completa,
                'completata_da': voce.completata_da,
                'completata_il': voce.completata_il_formatted,
                'note': voce.note,
                'stato_display': voce.stato_display,
                'badge_class': voce.badge_class
            })
        
        return jsonify({
            'success': True,
            'documento': {
                'id': documento.id,
                'title': documento.title
            },
            'checklist': checklist_data
        })
        
    except Exception as e:
        current_app.logger.error(f"Errore nel recupero checklist documento {documento_id}: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Errore nel recupero delle checklist'
        }), 500

@checklist_compliance_bp.route('/add', methods=['POST'])
@login_required
@roles_required(['admin', 'ceo', 'hr', 'auditor', 'quality_manager'])
def aggiungi_voce():
    """
    Aggiunge una nuova voce alla checklist compliance.
    
    Returns:
        JSON: Risultato dell'operazione
    """
    try:
        data = request.get_json() or {}
        
        # Validazione dati
        documento_id = data.get('documento_id')
        tipo_standard = data.get('tipo_standard')
        voce = data.get('voce')
        note = data.get('note')
        
        if not all([documento_id, tipo_standard, voce]):
            return jsonify({
                'success': False,
                'message': 'Dati mancanti: documento_id, tipo_standard, voce sono obbligatori'
            }), 400
        
        # Verifica esistenza documento
        documento = Document.query.get_or_404(documento_id)
        
        # Crea nuova voce checklist
        nuova_voce = ChecklistCompliance(
            documento_id=documento_id,
            tipo_standard=tipo_standard,
            voce=voce,
            note=note
        )
        
        db.session.add(nuova_voce)
        db.session.commit()
        
        # Log dell'azione
        log_checklist_action('aggiunta_voce', nuova_voce.id, {
            'documento_id': documento_id,
            'tipo_standard': tipo_standard,
            'voce': voce,
            'note': note
        })
        
        return jsonify({
            'success': True,
            'message': 'Voce checklist aggiunta con successo',
            'voce': {
                'id': nuova_voce.id,
                'tipo_standard': nuova_voce.tipo_standard,
                'tipo_standard_display': nuova_voce.tipo_standard_display,
                'voce': nuova_voce.voce,
                'is_completa': nuova_voce.is_completa,
                'note': nuova_voce.note,
                'stato_display': nuova_voce.stato_display,
                'badge_class': nuova_voce.badge_class
            }
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Errore nell'aggiunta voce checklist: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Errore nell\'aggiunta della voce checklist'
        }), 500

@checklist_compliance_bp.route('/<int:id>/completa', methods=['PATCH'])
@login_required
@roles_required(['admin', 'ceo', 'hr', 'auditor', 'quality_manager'])
def completa_voce(id):
    """
    Completa una voce della checklist compliance.
    
    Args:
        id (int): ID della voce checklist
        
    Returns:
        JSON: Risultato dell'operazione
    """
    try:
        data = request.get_json() or {}
        note = data.get('note')
        
        # Recupera voce checklist
        voce = ChecklistCompliance.query.get_or_404(id)
        
        # Verifica se può essere completata dall'utente
        if not voce.can_be_completed_by(current_user):
            return jsonify({
                'success': False,
                'message': 'Non autorizzato a completare questa checklist'
            }), 403
        
        # Completa la checklist
        voce.completa_checklist(current_user, note)
        db.session.commit()
        
        # Log dell'azione
        log_checklist_action('completamento_voce', id, {
            'documento_id': voce.documento_id,
            'tipo_standard': voce.tipo_standard,
            'voce': voce.voce,
            'note': note,
            'completata_da': voce.completata_da,
            'completata_il': voce.completata_il.isoformat() if voce.completata_il else None
        })
        
        return jsonify({
            'success': True,
            'message': 'Voce checklist completata con successo',
            'voce': {
                'id': voce.id,
                'is_completa': voce.is_completa,
                'completata_da': voce.completata_da,
                'completata_il': voce.completata_il_formatted,
                'note': voce.note,
                'stato_display': voce.stato_display,
                'badge_class': voce.badge_class
            }
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Errore nel completamento voce checklist {id}: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Errore nel completamento della voce checklist'
        }), 500

@checklist_compliance_bp.route('/<int:id>/reset', methods=['PATCH'])
@login_required
@roles_required(['admin', 'ceo', 'auditor'])
def reset_voce(id):
    """
    Resetta una voce della checklist compliance (solo admin/auditor).
    
    Args:
        id (int): ID della voce checklist
        
    Returns:
        JSON: Risultato dell'operazione
    """
    try:
        # Recupera voce checklist
        voce = ChecklistCompliance.query.get_or_404(id)
        
        # Resetta la checklist
        voce.reset_checklist(current_user)
        db.session.commit()
        
        # Log dell'azione
        log_checklist_action('reset_voce', id, {
            'documento_id': voce.documento_id,
            'tipo_standard': voce.tipo_standard,
            'voce': voce.voce
        })
        
        return jsonify({
            'success': True,
            'message': 'Voce checklist resettata con successo',
            'voce': {
                'id': voce.id,
                'is_completa': voce.is_completa,
                'completata_da': voce.completata_da,
                'completata_il': voce.completata_il_formatted,
                'note': voce.note,
                'stato_display': voce.stato_display,
                'badge_class': voce.badge_class
            }
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Errore nel reset voce checklist {id}: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Errore nel reset della voce checklist'
        }), 500

@checklist_compliance_bp.route('/<int:id>', methods=['DELETE'])
@login_required
@roles_required(['admin', 'ceo', 'auditor'])
def elimina_voce(id):
    """
    Elimina una voce della checklist compliance.
    
    Args:
        id (int): ID della voce checklist
        
    Returns:
        JSON: Risultato dell'operazione
    """
    try:
        # Recupera voce checklist
        voce = ChecklistCompliance.query.get_or_404(id)
        
        # Salva dati per log
        dati_eliminazione = {
            'documento_id': voce.documento_id,
            'tipo_standard': voce.tipo_standard,
            'voce': voce.voce,
            'is_completa': voce.is_completa,
            'completata_da': voce.completata_da
        }
        
        # Elimina la voce
        db.session.delete(voce)
        db.session.commit()
        
        # Log dell'azione
        log_checklist_action('eliminazione_voce', id, dati_eliminazione)
        
        return jsonify({
            'success': True,
            'message': 'Voce checklist eliminata con successo'
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Errore nell'eliminazione voce checklist {id}: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Errore nell\'eliminazione della voce checklist'
        }), 500

@checklist_compliance_bp.route('/statistiche/<int:documento_id>', methods=['GET'])
@login_required
@roles_required(['admin', 'ceo', 'hr', 'auditor', 'quality_manager'])
def statistiche_checklist(documento_id):
    """
    Statistiche delle checklist compliance per un documento.
    
    Args:
        documento_id (int): ID del documento
        
    Returns:
        JSON: Statistiche delle checklist
    """
    try:
        # Verifica esistenza documento
        documento = Document.query.get_or_404(documento_id)
        
        # Recupera tutte le checklist del documento
        checklist = ChecklistCompliance.query.filter_by(documento_id=documento_id).all()
        
        # Calcola statistiche
        totale = len(checklist)
        completate = len([c for c in checklist if c.is_completa])
        incompletate = totale - completate
        percentuale_completamento = (completate / totale * 100) if totale > 0 else 0
        
        # Raggruppa per standard
        per_standard = {}
        for voce in checklist:
            standard = voce.tipo_standard
            if standard not in per_standard:
                per_standard[standard] = {'totale': 0, 'completate': 0}
            per_standard[standard]['totale'] += 1
            if voce.is_completa:
                per_standard[standard]['completate'] += 1
        
        return jsonify({
            'success': True,
            'statistiche': {
                'totale': totale,
                'completate': completate,
                'incompletate': incompletate,
                'percentuale_completamento': round(percentuale_completamento, 2),
                'per_standard': per_standard
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Errore nel calcolo statistiche checklist documento {documento_id}: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Errore nel calcolo delle statistiche'
        }), 500

@checklist_compliance_bp.route('/documento/<int:documento_id>/export/pdf', methods=['GET'])
@login_required
@roles_required(['admin', 'ceo', 'hr', 'auditor', 'quality_manager'])
def export_checklist_pdf(documento_id):
    """
    Esporta checklist compliance in PDF audit-ready.
    
    Args:
        documento_id (int): ID del documento
        
    Returns:
        PDF: File PDF con checklist e firma digitale
    """
    try:
        # Recupera documento e checklist
        documento = Document.query.get_or_404(documento_id)
        checklist = ChecklistCompliance.query.filter_by(documento_id=documento_id).all()
        
        # Prepara buffer PDF
        buffer = BytesIO()
        c = canvas.Canvas(buffer, pagesize=A4)
        width, height = A4
        
        # ✅ BONUS 1: LOGO AZIENDA
        logo_path = "static/logonew.png"
        try:
            c.drawImage(ImageReader(logo_path), 50, height - 60, width=100, preserveAspectRatio=True, mask='auto')
        except Exception as e:
            current_app.logger.warning(f"Logo non trovato: {str(e)}")
        
        # Header documento
        c.setFont("Helvetica-Bold", 18)
        c.drawString(160, height - 50, "CHECKLIST COMPLIANCE AUDIT")
        
        c.setFont("Helvetica-Bold", 14)
        c.drawString(160, height - 70, f"Documento: {documento.title}")
        
        # Informazioni documento
        c.setFont("Helvetica", 10)
        c.drawString(160, height - 85, f"ID Documento: {documento.id}")
        c.drawString(160, height - 100, f"Data Generazione: {datetime.utcnow().strftime('%d/%m/%Y %H:%M')}")
        c.drawString(160, height - 115, f"Generato da: {current_user.username}")
        
        # Statistiche checklist
        totale = len(checklist)
        completate = len([c for c in checklist if c.is_completa])
        percentuale = (completate / totale * 100) if totale > 0 else 0
        
        c.setFont("Helvetica-Bold", 12)
        c.drawString(50, height - 140, f"STATISTICHE CHECKLIST:")
        c.setFont("Helvetica", 10)
        c.drawString(50, height - 155, f"• Totale voci: {totale}")
        c.drawString(50, height - 170, f"• Completate: {completate}")
        c.drawString(50, height - 185, f"• Incompletate: {totale - completate}")
        c.drawString(50, height - 200, f"• Percentuale completamento: {percentuale:.1f}%")
        
        # Lista checklist
        y = height - 230
        c.setFont("Helvetica-Bold", 12)
        c.drawString(50, y, "DETTAGLIO CHECKLIST:")
        y -= 20
        
        c.setFont("Helvetica", 10)
        for i, voce in enumerate(checklist, 1):
            if y < 100:  # Nuova pagina se necessario
                c.showPage()
                y = height - 50
                c.setFont("Helvetica-Bold", 12)
                c.drawString(50, y, "DETTAGLIO CHECKLIST (continua):")
                y -= 20
                c.setFont("Helvetica", 10)
            
            # Stato voce
            stato = "✅ COMPLETATA" if voce.is_completa else "❌ IN ATTESA"
            c.setFont("Helvetica-Bold", 10)
            c.drawString(50, y, f"{i}. [{stato}] {voce.tipo_standard_display}")
            y -= 15
            
            # Dettagli voce
            c.setFont("Helvetica", 9)
            c.drawString(60, y, f"Voce: {voce.voce}")
            y -= 12
            
            if voce.is_completa:
                c.drawString(60, y, f"Completata da: {voce.completata_da}")
                y -= 12
                c.drawString(60, y, f"Data completamento: {voce.completata_il}")
                y -= 12
            
            if voce.note:
                c.setFont("Helvetica-Oblique", 8)
                c.drawString(60, y, f"Note: {voce.note}")
                y -= 12
                c.setFont("Helvetica", 9)
            
            y -= 8  # Spazio tra voci
        
        # ✅ BONUS 2: FIRMA AUTOMATICA SYNTHIA
        y -= 30
        c.setFont("Helvetica-Bold", 10)
        c.drawString(50, y, "FIRMA DIGITALE SYNTHIA DOCS:")
        y -= 15
        c.setFont("Helvetica", 9)
        c.drawString(50, y, f"Documento generato da SYNTHIA DOCS – {datetime.utcnow().strftime('%d/%m/%Y %H:%M')}")
        y -= 12
        c.drawString(50, y, f"Firma digitale sistema: SYNTHIA-AUDIT-{documento_id}-{datetime.utcnow().timestamp():.0f}")
        y -= 12
        c.drawString(50, y, f"Utente generatore: {current_user.username}")
        y -= 12
        c.drawString(50, y, f"Ruolo utente: {current_user.role}")
        
        # ✅ BONUS 3: QR CODE per verifica
        qr_url = f"https://docs.mercurysurgelati.org/verifica/checklist/{documento_id}"
        qr_img = qrcode.make(qr_url)
        qr_buffer = BytesIO()
        qr_img.save(qr_buffer, format='PNG')
        qr_buffer.seek(0)
        
        # Posiziona QR code in basso a destra
        qr_size = 60
        qr_x = width - qr_size - 50
        qr_y = 50
        c.drawImage(ImageReader(qr_buffer), qr_x, qr_y, qr_size, qr_size)
        
        # Testo QR code
        c.setFont("Helvetica", 8)
        c.drawString(qr_x, qr_y - 15, "Scansiona per verificare")
        c.drawString(qr_x, qr_y - 30, "online la checklist")
        
        # Footer
        c.setFont("Helvetica", 8)
        c.drawString(50, 30, "Questo documento è generato automaticamente da SYNTHIA DOCS per audit compliance.")
        c.drawString(50, 20, "Il QR code permette la verifica online della validità della checklist.")
        
        c.save()
        buffer.seek(0)
        
        # Log dell'export
        log_checklist_action('export_pdf', None, {
            'documento_id': documento_id,
            'totale_voci': totale,
            'completate': completate,
            'percentuale': percentuale,
            'generato_da': current_user.username
        })
        
        return send_file(
            buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'Checklist_Audit_{documento.title}_{datetime.utcnow().strftime("%Y%m%d_%H%M")}.pdf'
        )
        
    except Exception as e:
        current_app.logger.error(f"Errore nell'export PDF checklist documento {documento_id}: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Errore nella generazione del PDF'
        }), 500 