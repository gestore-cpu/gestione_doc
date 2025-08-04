from flask import Blueprint, request, jsonify, send_file, flash, redirect, url_for, render_template
from flask_login import login_required, current_user
from models import db, PianoVisitePerMansione, VisitaMedicaEffettuata, DocumentoRelazioneMedico, User
from decorators import roles_required
from datetime import datetime
from io import BytesIO
import os

visite_mediche_avanzate_bp = Blueprint('visite_mediche_avanzate', __name__)

# 📌 1. Rotta – Caricamento piano visite per mansione
@visite_mediche_avanzate_bp.route("/piano_visite", methods=["POST"])
@login_required
@roles_required(['admin', 'quality'])
def crea_piano_visite():
    """Crea un nuovo piano visite per una mansione."""
    try:
        data = request.json
        mansione = data.get("mansione")
        tipo_visita = data.get("tipo_visita")
        frequenza_anni = data.get("frequenza_anni", 1)
        obbligatoria = data.get("obbligatoria", True)
        note = data.get("note", "")

        if not mansione or not tipo_visita:
            return jsonify({"error": "Campi mansione e tipo_visita sono obbligatori"}), 400

        # Verifica se esiste già
        esistente = PianoVisitePerMansione.query.filter_by(
            mansione=mansione, 
            tipo_visita=tipo_visita
        ).first()
        
        if esistente:
            return jsonify({"error": "Piano visite già esistente per questa mansione e tipo"}), 400

        entry = PianoVisitePerMansione(
            mansione=mansione,
            tipo_visita=tipo_visita,
            frequenza_anni=frequenza_anni,
            obbligatoria=obbligatoria,
            note=note,
            created_by=current_user.id
        )
        db.session.add(entry)
        db.session.commit()
        
        return jsonify({
            "ok": True, 
            "id": entry.id,
            "message": f"Piano visite creato: {entry.display_name}"
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Errore durante la creazione: {str(e)}"}), 500

# 📌 2. Rotta – Lista piano visite per mansione
@visite_mediche_avanzate_bp.route("/piano_visite/<mansione>", methods=["GET"])
@login_required
@roles_required(['admin', 'quality'])
def lista_visite_per_mansione(mansione):
    """Ottiene la lista delle visite per una mansione specifica."""
    try:
        voci = PianoVisitePerMansione.query.filter_by(mansione=mansione).all()
        return jsonify([
            {
                "id": v.id, 
                "tipo_visita": v.tipo_visita,
                "frequenza_anni": v.frequenza_anni,
                "frequenza_display": v.frequenza_display,
                "obbligatoria": v.obbligatoria,
                "note": v.note,
                "created_at": v.created_at.strftime('%d/%m/%Y %H:%M') if v.created_at else None
            }
            for v in voci
        ])
    except Exception as e:
        return jsonify({"error": f"Errore durante il recupero: {str(e)}"}), 500

# 📌 3. Rotta – Aggiungi visita effettuata (per utente)
@visite_mediche_avanzate_bp.route("/visite", methods=["POST"])
@login_required
@roles_required(['admin', 'quality'])
def registra_visita():
    """Registra una nuova visita medica effettuata."""
    try:
        data = request.json
        user_id = data.get("user_id")
        tipo_visita = data.get("tipo_visita")
        data_visita = data.get("data_visita")
        esito = data.get("esito")
        scadenza = data.get("scadenza")
        mansione_riferimento = data.get("mansione_riferimento")
        note = data.get("note", "")

        if not all([user_id, tipo_visita, data_visita]):
            return jsonify({"error": "Campi user_id, tipo_visita e data_visita sono obbligatori"}), 400

        # Verifica che l'utente esista
        user = User.query.get(user_id)
        if not user:
            return jsonify({"error": "Utente non trovato"}), 404

        visita = VisitaMedicaEffettuata(
            user_id=user_id,
            tipo_visita=tipo_visita,
            data_visita=datetime.strptime(data_visita, "%Y-%m-%d").date(),
            esito=esito,
            scadenza=datetime.strptime(scadenza, "%Y-%m-%d").date() if scadenza else None,
            mansione_riferimento=mansione_riferimento,
            note=note,
            created_by=current_user.id
        )
        db.session.add(visita)
        db.session.commit()
        
        return jsonify({
            "ok": True, 
            "id": visita.id,
            "message": f"Visita registrata per {user.username}"
        })
        
    except ValueError as e:
        return jsonify({"error": f"Formato data non valido: {str(e)}"}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Errore durante la registrazione: {str(e)}"}), 500

# 📌 4. Rotta – Upload certificato idoneità finale (PDF)
@visite_mediche_avanzate_bp.route("/visite/<int:visita_id>/certificato", methods=["POST"])
@login_required
@roles_required(['admin', 'quality'])
def upload_certificato(visita_id):
    """Carica il certificato di idoneità per una visita."""
    try:
        visita = VisitaMedicaEffettuata.query.get_or_404(visita_id)
        file = request.files.get("certificato")
        
        if not file:
            return jsonify({"error": "Nessun file ricevuto"}), 400

        # Verifica tipo file
        if not file.filename.lower().endswith(('.pdf', '.jpg', '.jpeg', '.png')):
            return jsonify({"error": "Solo file PDF, JPG, PNG sono ammessi"}), 400

        # Verifica dimensione (max 10MB)
        file.seek(0, 2)  # Vai alla fine
        size = file.tell()
        file.seek(0)  # Torna all'inizio
        
        if size > 10 * 1024 * 1024:  # 10MB
            return jsonify({"error": "File troppo grande. Dimensione massima: 10MB"}), 400

        visita.certificato_finale = True
        visita.allegato_certificato = file.read()
        visita.filename_certificato = file.filename
        db.session.commit()
        
        return jsonify({
            "ok": True,
            "message": f"Certificato caricato: {file.filename}"
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Errore durante il caricamento: {str(e)}"}), 500

# 📌 5. Rotta – Download certificato finale
@visite_mediche_avanzate_bp.route("/visite/<int:visita_id>/download", methods=["GET"])
@login_required
@roles_required(['admin', 'quality'])
def download_certificato(visita_id):
    """Scarica il certificato di una visita."""
    try:
        visita = VisitaMedicaEffettuata.query.get_or_404(visita_id)
        
        if not visita.allegato_certificato:
            return jsonify({"error": "Nessun certificato presente"}), 404

        return send_file(
            BytesIO(visita.allegato_certificato),
            mimetype='application/octet-stream',
            download_name=visita.filename_certificato,
            as_attachment=True
        )
        
    except Exception as e:
        return jsonify({"error": f"Errore durante il download: {str(e)}"}), 500

# 📌 6. Rotta – Upload relazione medico del lavoro
@visite_mediche_avanzate_bp.route("/relazione_medico", methods=["POST"])
@login_required
@roles_required(['admin', 'quality'])
def upload_relazione_medico():
    """Carica la relazione medica annuale."""
    try:
        file = request.files.get("file")
        anno = request.form.get("anno")
        note = request.form.get("note", "")
        
        if not file or not anno:
            return jsonify({"error": "File e anno sono obbligatori"}), 400

        # Verifica anno
        try:
            anno_int = int(anno)
            if anno_int < 2020 or anno_int > 2030:
                return jsonify({"error": "Anno non valido"}), 400
        except ValueError:
            return jsonify({"error": "Anno non valido"}), 400

        # Verifica se esiste già una relazione per quell'anno
        esistente = DocumentoRelazioneMedico.query.filter_by(anno=anno_int).first()
        if esistente:
            return jsonify({"error": f"Relazione per l'anno {anno} già presente"}), 400

        # Verifica tipo file
        if not file.filename.lower().endswith('.pdf'):
            return jsonify({"error": "Solo file PDF sono ammessi"}), 400

        # Verifica dimensione (max 20MB)
        file.seek(0, 2)
        size = file.tell()
        file.seek(0)
        
        if size > 20 * 1024 * 1024:  # 20MB
            return jsonify({"error": "File troppo grande. Dimensione massima: 20MB"}), 400

        doc = DocumentoRelazioneMedico(
            anno=anno_int,
            file_data=file.read(),
            filename=file.filename,
            caricato_da=current_user.email,
            note=note,
            created_by=current_user.id
        )
        db.session.add(doc)
        db.session.commit()
        
        return jsonify({
            "ok": True,
            "message": f"Relazione medica {anno} caricata con successo"
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Errore durante il caricamento: {str(e)}"}), 500

# 📌 7. Rotta aggiuntiva – Lista tutte le visite di un utente
@visite_mediche_avanzate_bp.route("/visite/utente/<int:user_id>", methods=["GET"])
@login_required
@roles_required(['admin', 'quality'])
def lista_visite_utente(user_id):
    """Ottiene tutte le visite di un utente specifico."""
    try:
        user = User.query.get_or_404(user_id)
        visite = VisitaMedicaEffettuata.query.filter_by(user_id=user_id).order_by(VisitaMedicaEffettuata.data_visita.desc()).all()
        
        return jsonify([
            {
                "id": v.id,
                "tipo_visita": v.tipo_visita,
                "data_visita": v.data_visita_display,
                "esito": v.esito,
                "scadenza": v.scadenza_display,
                "mansione_riferimento": v.mansione_riferimento,
                "has_certificato": v.has_certificato,
                "is_scaduta": v.is_scaduta,
                "is_in_scadenza": v.is_in_scadenza,
                "esito_badge_class": v.esito_badge_class,
                "note": v.note
            }
            for v in visite
        ])
    except Exception as e:
        return jsonify({"error": f"Errore durante il recupero: {str(e)}"}), 500

# 📌 8. Rotta aggiuntiva – Lista tutte le relazioni mediche
@visite_mediche_avanzate_bp.route("/relazioni_mediche", methods=["GET"])
@login_required
@roles_required(['admin', 'quality'])
def lista_relazioni_mediche():
    """Ottiene tutte le relazioni mediche caricate."""
    try:
        relazioni = DocumentoRelazioneMedico.query.order_by(DocumentoRelazioneMedico.anno.desc()).all()
        
        return jsonify([
            {
                "id": r.id,
                "anno": r.anno,
                "filename": r.filename,
                "data_caricamento": r.data_caricamento_display,
                "caricato_da": r.caricato_da,
                "file_size": r.file_size_display,
                "note": r.note
            }
            for r in relazioni
        ])
    except Exception as e:
        return jsonify({"error": f"Errore durante il recupero: {str(e)}"}), 500 