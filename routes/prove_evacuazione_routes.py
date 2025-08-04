"""
Routes per la gestione delle prove di evacuazione.
Dashboard per visualizzare e gestire prove evacuazione.
"""

import os
import json
import logging
from datetime import datetime
from flask import Blueprint, render_template, request, flash, redirect, url_for, send_file, jsonify
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from models import ProvaEvacuazione, db, Reminder
from decorators import roles_required

logger = logging.getLogger(__name__)

# Configurazione upload
UPLOAD_FOLDER_PLANIMETRIE = 'static/uploads/evacuazione/planimetrie'
UPLOAD_FOLDER_VERBALI = 'static/uploads/evacuazione/verbali'
UPLOAD_FOLDER_FOTO = 'static/uploads/evacuazione/foto'
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg'}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB

prove_evacuazione_bp = Blueprint('prove_evacuazione', __name__)

def allowed_file(filename):
    """Verifica se l'estensione del file è consentita."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def validate_file_size(file):
    """Verifica la dimensione del file."""
    if file:
        file.seek(0, os.SEEK_END)
        size = file.tell()
        file.seek(0)
        return size <= MAX_FILE_SIZE
    return True

def registra_audit(prova, campo, vecchio, nuovo, utente):
    """Registra una modifica nell'audit trail."""
    from models import AuditTrailEvacuazione
    
    log = AuditTrailEvacuazione(
        prova_id=prova.id,
        campo_modificato=campo,
        valore_precedente=str(vecchio) if vecchio is not None else "None",
        valore_nuovo=str(nuovo) if nuovo is not None else "None",
        modificato_da=utente
    )
    db.session.add(log)

@prove_evacuazione_bp.route('/prove-evacuazione/nuova', methods=['GET', 'POST'])
@login_required
@roles_required(['admin', 'quality'])
def nuova_prova_evacuazione():
    """
    Crea una nuova prova di evacuazione.
    Accessibile solo ad Admin e Quality.
    """
    if request.method == 'POST':
        try:
            # Validazione campi obbligatori
            data = request.form.get('data')
            luogo = request.form.get('luogo')
            responsabile = request.form.get('responsabile')
            
            if not all([data, luogo, responsabile]):
                flash("❌ Tutti i campi obbligatori devono essere compilati", "danger")
                return render_template('prove_evacuazione/nuova_prova_evacuazione.html')
            
            # Gestione file planimetria
            planimetria_filename = None
            file_planimetria = request.files.get('planimetria')
            
            if file_planimetria and file_planimetria.filename:
                if not allowed_file(file_planimetria.filename):
                    flash("❌ Tipo di file non consentito. Usa PDF, PNG, JPG", "danger")
                    return render_template('prove_evacuazione/nuova_prova_evacuazione.html')
                
                if not validate_file_size(file_planimetria):
                    flash("❌ File troppo grande. Massimo 5MB", "danger")
                    return render_template('prove_evacuazione/nuova_prova_evacuazione.html')
                
                timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
                planimetria_filename = f"planimetria_{timestamp}_{secure_filename(file_planimetria.filename)}"
                file_path = os.path.join(UPLOAD_FOLDER_PLANIMETRIE, planimetria_filename)
                file_planimetria.save(file_path)
            
            # Gestione file verbale
            verbale_filename = None
            file_verbale = request.files.get('verbale')
            
            if file_verbale and file_verbale.filename:
                if not allowed_file(file_verbale.filename):
                    flash("❌ Tipo di file non consentito per il verbale. Usa PDF, PNG, JPG", "danger")
                    return render_template('prove_evacuazione/nuova_prova_evacuazione.html')
                
                if not validate_file_size(file_verbale):
                    flash("❌ File verbale troppo grande. Massimo 5MB", "danger")
                    return render_template('prove_evacuazione/nuova_prova_evacuazione.html')
                
                timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
                verbale_filename = f"verbale_{timestamp}_{secure_filename(file_verbale.filename)}"
                file_path = os.path.join(UPLOAD_FOLDER_VERBALI, verbale_filename)
                file_verbale.save(file_path)
            
            # Gestione file foto
            foto_filename = None
            file_foto = request.files.get('foto')
            
            if file_foto and file_foto.filename:
                if not allowed_file(file_foto.filename):
                    flash("❌ Tipo di file non consentito per le foto. Usa PNG, JPG", "danger")
                    return render_template('prove_evacuazione/nuova_prova_evacuazione.html')
                
                if not validate_file_size(file_foto):
                    flash("❌ File foto troppo grande. Massimo 5MB", "danger")
                    return render_template('prove_evacuazione/nuova_prova_evacuazione.html')
                
                timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
                foto_filename = f"foto_{timestamp}_{secure_filename(file_foto.filename)}"
                file_path = os.path.join(UPLOAD_FOLDER_FOTO, foto_filename)
                file_foto.save(file_path)
            
            # Gestione punti mappa JSON
            punti_mappa = None
            punti_json = request.form.get('punti_mappa')
            if punti_json and punti_json.strip():
                try:
                    punti_mappa = json.loads(punti_json)
                    punti_mappa = json.dumps(punti_mappa)  # Salva come stringa JSON
                except json.JSONDecodeError:
                    flash("❌ Formato JSON non valido per i punti mappa", "danger")
                    return render_template('prove_evacuazione/nuova_prova_evacuazione.html')
            
            # Gestione link FleetFix
            link_fleetfix = request.form.get('link_fleetfix', '').strip()
            
            # Creazione record
            nuova_prova = ProvaEvacuazione(
                data=datetime.strptime(data, '%Y-%m-%d').date(),
                luogo=luogo.strip(),
                responsabile=responsabile.strip(),
                note=request.form.get('note', '').strip(),
                verbale_filename=verbale_filename,
                planimetria_filename=planimetria_filename,
                foto_filename=foto_filename,
                punti_mappa=punti_mappa,
                link_fleetfix=link_fleetfix,
                created_by=current_user.id
            )
            
            db.session.add(nuova_prova)
            db.session.commit()
            
            # Creazione reminder automatico per prossima prova (annuale)
            try:
                from datetime import timedelta
                prossima_data = nuova_prova.data + timedelta(days=365)
                
                reminder = Reminder(
                    tipo='prova_evacuazione',
                    entita_id=nuova_prova.id,
                    entita_tipo='ProvaEvacuazione',
                    destinatario_email='hr@mercurysurgelati.org',
                    destinatario_ruolo='hr',
                    scadenza=prossima_data,
                    giorni_anticipo=30,
                    messaggio=f"Prova di evacuazione da programmare per {nuova_prova.luogo}",
                    canale='email',
                    created_by=current_user.id
                )
                db.session.add(reminder)
                db.session.commit()
                
                logger.info(f"Reminder automatico creato per prova evacuazione {nuova_prova.id}")
                
            except Exception as e:
                logger.error(f"Errore creazione reminder automatico: {str(e)}")
            
            flash("✅ Prova di evacuazione registrata con successo", "success")
            return redirect(url_for('prove_evacuazione.lista_prove_evacuazione'))
            
        except Exception as e:
            logger.error(f"Errore creazione prova evacuazione: {str(e)}")
            flash(f"❌ Errore durante la registrazione: {str(e)}", "danger")
            db.session.rollback()
    
    return render_template('prove_evacuazione/nuova_prova_evacuazione.html', today=datetime.now().strftime('%Y-%m-%d'))

@prove_evacuazione_bp.route('/prove-evacuazione/lista', methods=['GET'])
@login_required
@roles_required(['admin', 'quality', 'hr', 'ceo'])
def lista_prove_evacuazione():
    """
    Visualizza la lista delle prove di evacuazione.
    Accessibile ad Admin, Quality, HR e CEO.
    """
    try:
        prove = ProvaEvacuazione.query.order_by(ProvaEvacuazione.data.desc()).all()
        
        # Statistiche
        totali = len(prove)
        recenti = len([p for p in prove if p.is_recente])
        con_planimetria = len([p for p in prove if p.has_planimetria])
        con_verbale = len([p for p in prove if p.has_verbale])
        
        return render_template(
            'prove_evacuazione/lista_prove_evacuazione.html',
            prove=prove,
            totali=totali,
            recenti=recenti,
            con_planimetria=con_planimetria,
            con_verbale=con_verbale
        )
        
    except Exception as e:
        logger.error(f"Errore lista prove evacuazione: {str(e)}")
        flash("❌ Errore nel caricamento delle prove di evacuazione", "danger")
        return redirect(url_for('admin.dashboard'))

@prove_evacuazione_bp.route('/prove-evacuazione/<int:prova_id>', methods=['GET'])
@login_required
@roles_required(['admin', 'quality', 'hr', 'ceo'])
def dettaglio_prova_evacuazione(prova_id):
    """
    Visualizza i dettagli di una prova di evacuazione.
    """
    try:
        prova = ProvaEvacuazione.query.get_or_404(prova_id)
        return render_template('prove_evacuazione/dettaglio_prova_evacuazione.html', prova=prova)
        
    except Exception as e:
        logger.error(f"Errore dettaglio prova evacuazione: {str(e)}")
        flash("❌ Errore nel caricamento dei dettagli", "danger")
        return redirect(url_for('prove_evacuazione.lista_prove_evacuazione'))

@prove_evacuazione_bp.route('/prove-evacuazione/<int:id>/modifica', methods=['GET', 'POST'])
@login_required
@roles_required(['admin', 'quality'])
def modifica_prova_evacuazione(id):
    """Modifica una prova di evacuazione esistente."""
    prova = ProvaEvacuazione.query.get_or_404(id)
    
    if request.method == 'POST':
        # Registra modifiche per audit trail
        if prova.data != datetime.strptime(request.form['data'], '%Y-%m-%d').date():
            registra_audit(prova, "data", str(prova.data), request.form['data'], current_user.email)
        
        if prova.luogo != request.form['luogo']:
            registra_audit(prova, "luogo", prova.luogo, request.form['luogo'], current_user.email)
        
        if prova.responsabile != request.form['responsabile']:
            registra_audit(prova, "responsabile", prova.responsabile, request.form['responsabile'], current_user.email)
        
        if prova.note != request.form.get('note'):
            registra_audit(prova, "note", prova.note, request.form.get('note'), current_user.email)
        
        if prova.link_fleetfix != request.form.get('link_fleetfix'):
            registra_audit(prova, "link_fleetfix", prova.link_fleetfix, request.form.get('link_fleetfix'), current_user.email)
        
        # Aggiorna campi base
        prova.data = datetime.strptime(request.form['data'], '%Y-%m-%d').date()
        prova.luogo = request.form['luogo']
        prova.responsabile = request.form['responsabile']
        prova.note = request.form.get('note')
        prova.link_fleetfix = request.form.get('link_fleetfix')
        prova.punti_mappa_dict = request.form.get('punti_mappa')

        # Nuovo upload planimetria
        file = request.files.get('planimetria')
        if file and file.filename:
            filename = secure_filename(file.filename)
            timestamped_name = f"{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{filename}"
            file_path = os.path.join('uploads/evacuazione/planimetrie', timestamped_name)
            file.save(file_path)
            
            # Registra audit per nuova planimetria
            registra_audit(prova, "planimetria", prova.planimetria_filename, timestamped_name, current_user.email)
            
            # Crea nuova versione
            versione = VersionePlanimetriaEvacuazione(
                prova_id=id,
                filename=timestamped_name,
                uploaded_by=current_user.email,
                note=request.form.get('note_versione', '')
            )
            db.session.add(versione)
            prova.planimetria_filename = timestamped_name

        db.session.commit()
        flash("✅ Prova di evacuazione aggiornata con successo", "success")
        return redirect(url_for('prove_evacuazione.lista_prove_evacuazione'))
    
    return render_template('prove_evacuazione/modifica_prova_evacuazione.html', prova=prova)

@prove_evacuazione_bp.route('/prove-evacuazione/<int:id>/elimina', methods=['POST'])
@login_required
@roles_required(['admin'])
def elimina_prova_evacuazione(id):
    """Elimina una prova di evacuazione (solo Admin)."""
    prova = ProvaEvacuazione.query.get_or_404(id)
    
    # Elimina file associati
    if prova.verbale_filename:
        try:
            os.remove(os.path.join('uploads/evacuazione/verbali', prova.verbale_filename))
        except:
            pass
    
    if prova.planimetria_filename:
        try:
            os.remove(os.path.join('uploads/evacuazione/planimetrie', prova.planimetria_filename))
        except:
            pass
    
    if prova.foto_filename:
        try:
            os.remove(os.path.join('uploads/evacuazione/foto', prova.foto_filename))
        except:
            pass
    
    # Elimina versioni planimetrie
    for versione in prova.versioni_planimetrie:
        try:
            os.remove(os.path.join('uploads/evacuazione/planimetrie', versione.filename))
        except:
            pass
    
    db.session.delete(prova)
    db.session.commit()
    
    flash("🗑️ Prova di evacuazione eliminata", "info")
    return redirect(url_for('prove_evacuazione.lista_prove_evacuazione'))

@prove_evacuazione_bp.route('/prove-evacuazione/<int:id>/versioni', methods=['GET'])
@login_required
@roles_required(['admin', 'quality'])
def versioni_planimetria(id):
    """Mostra le versioni della planimetria per una prova."""
    prova = ProvaEvacuazione.query.get_or_404(id)
    return render_template('prove_evacuazione/versioni_planimetria.html', prova=prova)

@prove_evacuazione_bp.route('/prove-evacuazione/<int:prova_id>/download/<tipo>', methods=['GET'])
@login_required
@roles_required(['admin', 'quality', 'hr', 'ceo'])
def download_file_prova(prova_id, tipo):
    """
    Download di file associati alla prova di evacuazione.
    """
    try:
        prova = ProvaEvacuazione.query.get_or_404(prova_id)
        
        if tipo == 'planimetria' and prova.planimetria_filename:
            file_path = os.path.join(UPLOAD_FOLDER_PLANIMETRIE, prova.planimetria_filename)
            return send_file(file_path, as_attachment=True)
        
        elif tipo == 'verbale' and prova.verbale_filename:
            file_path = os.path.join(UPLOAD_FOLDER_VERBALI, prova.verbale_filename)
            return send_file(file_path, as_attachment=True)
        
        elif tipo == 'foto' and prova.foto_filename:
            file_path = os.path.join(UPLOAD_FOLDER_FOTO, prova.foto_filename)
            return send_file(file_path, as_attachment=True)
        
        else:
            flash("❌ File non trovato", "danger")
            
    except Exception as e:
        logger.error(f"Errore download file prova evacuazione: {str(e)}")
        flash("❌ Errore durante il download", "danger")
    
    return redirect(url_for('prove_evacuazione.dettaglio_prova_evacuazione', prova_id=prova_id))

def genera_pdf_prova_evacuazione(prova):
    """Genera PDF per una prova di evacuazione con QR code e firma digitale."""
    from io import BytesIO
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    from reportlab.lib.units import mm
    from reportlab.lib.utils import ImageReader
    import qrcode
    
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    
    # Logo aziendale
    logo_path = "static/img/logo_mercury.png"
    try:
        c.drawImage(ImageReader(logo_path), 50, height - 60, width=100, preserveAspectRatio=True, mask='auto')
    except:
        pass
    
    # Titolo
    c.setFont("Helvetica-Bold", 16)
    c.drawString(160, height - 50, f"Prova di Evacuazione - {prova.luogo}")
    
    y = height - 100
    c.setFont("Helvetica", 11)
    
    # Dati prova
    c.drawString(50, y, f"📅 Data: {prova.data.strftime('%d/%m/%Y')}")
    y -= 20
    c.drawString(50, y, f"🏢 Luogo: {prova.luogo}")
    y -= 20
    c.drawString(50, y, f"👤 Responsabile: {prova.responsabile}")
    y -= 20
    
    if prova.note:
        c.drawString(50, y, f"📝 Note: {prova.note}")
        y -= 30
    
    # Allegati
    if prova.verbale_filename:
        c.drawString(50, y, f"📄 Verbale: {prova.verbale_filename}")
        y -= 20
    
    if prova.planimetria_filename:
        c.drawString(50, y, f"🗺️ Planimetria: {prova.planimetria_filename}")
        y -= 20
    
    if prova.foto_filename:
        c.drawString(50, y, f"📷 Foto: {prova.foto_filename}")
        y -= 20
    
    if prova.link_fleetfix:
        c.drawString(50, y, f"🔗 FleetFix: {prova.link_fleetfix}")
        y -= 20
    
    # Versioni planimetrie
    if prova.versioni_planimetrie:
        y -= 20
        c.setFont("Helvetica-Bold", 12)
        c.drawString(50, y, "📋 Versioni Planimetrie:")
        y -= 15
        c.setFont("Helvetica", 10)
        for versione in prova.versioni_planimetrie:
            c.drawString(60, y, f"• {versione.filename} - {versione.uploaded_at.strftime('%d/%m/%Y %H:%M')}")
            y -= 15
            if versione.note:
                c.drawString(70, y, f"  Note: {versione.note}")
                y -= 15
    
    # === FIRME DIGITALI ===
    y -= 30
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, "✍️ Firme Digitali:")
    y -= 20
    c.setFont("Helvetica", 10)
    
    # Firma responsabile
    if prova.has_firma_responsabile:
        try:
            # Converti firma in immagine
            firma_image = ImageReader(BytesIO(prova.firma_responsabile))
            c.drawImage(firma_image, 60, y - 40, width=200, height=50, preserveAspectRatio=True)
            c.drawString(60, y - 50, "✅ Firma Responsabile Presente")
        except Exception as e:
            c.drawString(60, y - 20, "✅ Firma Responsabile Presente (formato non visualizzabile)")
    else:
        c.drawString(60, y - 20, "❌ Firma Responsabile Assente")
    
    y -= 60
    
    # Firma AI simulata
    if prova.has_firma_ai:
        c.setFont("Helvetica-Oblique", 10)
        c.drawString(60, y, "🤖 Firma AI Simulata Attiva")
        c.setFont("Helvetica", 10)
    else:
        c.drawString(60, y, "⏸️ Firma AI Non Attiva")
    
    # Firma digitale
    y -= 30
    c.setFont("Helvetica", 10)
    c.drawString(50, y, f"Documento generato da SYNTHIA DOCS - {datetime.utcnow().strftime('%d/%m/%Y %H:%M')}")
    y -= 20
    c.drawString(50, y, f"Firma digitale: SYNTHIA-EVAC-{prova.id}-{datetime.utcnow().timestamp():.0f}")
    
    # QR Code per verifica
    qr_url = f"https://docs.mercurysurgelati.org/verifica/prova-evacuazione/{prova.id}"
    qr_img = qrcode.make(qr_url)
    qr_buffer = BytesIO()
    qr_img.save(qr_buffer)
    qr_buffer.seek(0)
    c.drawImage(ImageReader(qr_buffer), width - 100, 40, 60, 60)
    
    c.save()
    buffer.seek(0)
    return buffer

@prove_evacuazione_bp.route('/prove-evacuazione/<int:id>/export/pdf', methods=['GET'])
@login_required
@roles_required(['admin', 'quality'])
def export_prova_pdf(id):
    """Esporta una prova di evacuazione in PDF."""
    prova = ProvaEvacuazione.query.get_or_404(id)
    
    try:
        buffer = genera_pdf_prova_evacuazione(prova)
        return send_file(
            buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'Prova_Evacuazione_{prova.luogo}_{prova.data.strftime("%Y%m%d")}.pdf'
        )
    except Exception as e:
        flash(f"❌ Errore generazione PDF: {str(e)}", "danger")
        return redirect(url_for('prove_evacuazione.dettaglio_prova_evacuazione', id=id)) 

@prove_evacuazione_bp.route('/prove-evacuazione/<int:prova_id>/firma', methods=['POST'])
@login_required
@roles_required(['admin', 'quality'])
def firma_responsabile(prova_id):
    """Carica la firma digitale del responsabile."""
    prova = ProvaEvacuazione.query.get_or_404(prova_id)
    
    file = request.files.get("firma")
    if not file:
        return jsonify({"error": "Nessun file caricato"}), 400
    
    # Leggi il file
    firma_data = file.read()
    
    # Registra audit
    vecchio_stato = "Presente" if prova.has_firma_responsabile else "Assente"
    registra_audit(prova, "firma_responsabile", vecchio_stato, "Caricata", current_user.email)
    
    # Salva firma
    prova.firma_responsabile = firma_data
    db.session.commit()
    
    flash("✅ Firma responsabile caricata con successo", "success")
    return jsonify({"ok": True})

@prove_evacuazione_bp.route('/prove-evacuazione/<int:prova_id>/firma_ai', methods=['POST'])
@login_required
@roles_required(['admin'])
def attiva_firma_ai(prova_id):
    """Attiva la firma AI simulata (solo Admin)."""
    prova = ProvaEvacuazione.query.get_or_404(prova_id)
    
    # Registra audit
    registra_audit(prova, "firma_ai_simulata", str(prova.firma_ai_simulata), "True", current_user.email)
    
    # Attiva firma AI
    prova.firma_ai_simulata = True
    db.session.commit()
    
    flash("🤖 Firma AI simulata attivata", "success")
    return jsonify({"ok": True})

@prove_evacuazione_bp.route('/prove-evacuazione/<int:prova_id>/audit', methods=['GET'])
@login_required
@roles_required(['admin', 'quality', 'auditor'])
def audit_trail_prova(prova_id):
    """Visualizza l'audit trail di una prova."""
    prova = ProvaEvacuazione.query.get_or_404(prova_id)
    return render_template('prove_evacuazione/audit_trail.html', prova=prova)

@prove_evacuazione_bp.route('/prove-evacuazione/<int:prova_id>/download_firma', methods=['GET'])
@login_required
@roles_required(['admin', 'quality'])
def download_firma_responsabile(prova_id):
    """Scarica la firma del responsabile."""
    prova = ProvaEvacuazione.query.get_or_404(prova_id)
    
    if not prova.has_firma_responsabile:
        flash("❌ Nessuna firma disponibile", "warning")
        return redirect(url_for('prove_evacuazione.dettaglio_prova_evacuazione', id=prova_id))
    
    return send_file(
        BytesIO(prova.firma_responsabile),
        mimetype='application/octet-stream',
        as_attachment=True,
        download_name=f'firma_responsabile_prova_{prova_id}.sig'
    ) 

@prove_evacuazione_bp.route('/prove-evacuazione/archivio_pdf', methods=['POST'])
@login_required
@roles_required(['admin', 'quality'])
def esporta_archivio_pdf():
    """Esporta un archivio ZIP con tutti i PDF delle prove selezionate."""
    import zipfile
    from io import BytesIO
    
    try:
        # Ottieni IDs dalle prove selezionate
        ids = request.json.get("prove_ids", [])
        if not ids:
            return jsonify({"error": "Nessuna prova selezionata"}), 400
        
        # Crea buffer ZIP
        zip_buffer = BytesIO()
        
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
            for prova_id in ids:
                prova = ProvaEvacuazione.query.get(prova_id)
                if not prova:
                    continue
                
                try:
                    # Genera PDF per questa prova
                    pdf_buffer = genera_pdf_prova_evacuazione(prova)
                    
                    # Nome file sicuro
                    safe_luogo = "".join(c for c in prova.luogo if c.isalnum() or c in (' ', '-', '_')).rstrip()
                    filename = f"ProvaEvacuazione_{prova.id}_{safe_luogo}_{prova.data.strftime('%Y%m%d')}.pdf"
                    
                    # Aggiungi al ZIP
                    zipf.writestr(filename, pdf_buffer.getvalue())
                    
                except Exception as e:
                    # Log errore ma continua con le altre prove
                    print(f"Errore generazione PDF per prova {prova_id}: {str(e)}")
                    continue
        
        zip_buffer.seek(0)
        
        # Registra audit
        registra_audit(
            None,  # Non abbiamo una prova specifica
            "archivio_pdf_export",
            "N/A",
            f"Esportate {len(ids)} prove",
            current_user.email
        )
        
        return send_file(
            zip_buffer,
            mimetype="application/zip",
            as_attachment=True,
            download_name=f"Archivio_Prove_Evacuazione_{datetime.utcnow().strftime('%Y%m%d_%H%M')}.zip"
        )
        
    except Exception as e:
        print(f"Errore esportazione archivio: {str(e)}")
        return jsonify({"error": f"Errore durante l'esportazione: {str(e)}"}), 500 