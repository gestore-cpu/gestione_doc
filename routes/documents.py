from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, send_file, Response, jsonify
from flask_login import login_required, current_user
from models import db, Document
from decorators import admin_required
from io import BytesIO, StringIO
import csv
from datetime import datetime

docs_bp = Blueprint('docs', __name__)


@docs_bp.route("/api/jack/docs/chat", methods=["POST"])
@login_required
def jack_ai_chat():
    """
    Endpoint per la chat AI di Jack nel modulo DOCS.
    
    Returns:
        JSON: Risposta di Jack AI
    """
    try:
        data = request.get_json()
        domanda = data.get('domanda', '').strip()
        
        if not domanda:
            return jsonify({"error": "Domanda vuota"}), 400
        
        # Logica AI di Jack per il modulo DOCS
        risposta = genera_risposta_jack_docs(domanda)
        
        return jsonify({
            "success": True,
            "risposta": risposta,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        current_app.logger.error(f"Errore nella chat Jack AI: {str(e)}")
        return jsonify({
            "error": "Errore interno del server",
            "risposta": "Mi dispiace, c'è stato un errore. Riprova più tardi."
        }), 500


def genera_risposta_jack_docs(domanda):
    """
    Genera una risposta AI per Jack nel modulo DOCS.
    
    Args:
        domanda (str): Domanda dell'utente
        
    Returns:
        str: Risposta di Jack
    """
    domanda_lower = domanda.lower()
    
    # Risposte predefinite per domande comuni
    if any(word in domanda_lower for word in ['carica', 'upload', 'aggiungi']):
        return "📄 Per caricare un documento, clicca sul pulsante 'Carica Documento' in alto a destra. Puoi selezionare file PDF, DOC, DOCX e altri formati supportati. Una volta caricato, il documento sarà automaticamente analizzato con AI! 🤖"
    
    elif any(word in domanda_lower for word in ['firma', 'firmare', 'sign']):
        return "🖋️ Per firmare un documento, clicca sull'icona della firma (✍️) nella riga del documento. Verrà richiesto un token di sicurezza via email/WhatsApp per la 2FA. La firma è tracciabile e sicura! 🔐"
    
    elif any(word in domanda_lower for word in ['scadenza', 'scaduto', 'expiry']):
        return "⏰ I documenti in scadenza sono evidenziati in rosso nella tabella. Puoi anche andare alla sezione 'Scadenziario' per vedere tutti i documenti che scadono nei prossimi 30 giorni. Ti invierò promemoria automatici! 📅"
    
    elif any(word in domanda_lower for word in ['ai', 'analisi', 'analizza']):
        return "🤖 L'analisi AI è automatica per tutti i documenti caricati. Controlla la colonna 'AI Status' per vedere lo stato dell'analisi. I documenti vengono classificati come 'completo', 'incompleto', 'scaduto' o 'manca_firma'. 📊"
    
    elif any(word in domanda_lower for word in ['filtri', 'cerca', 'trova']):
        return "🔍 Usa i filtri in alto per cercare documenti per nome, categoria, stato o azienda. Puoi combinare più filtri per trovare esattamente quello che cerchi! La ricerca è in tempo reale. ✨"
    
    elif any(word in domanda_lower for word in ['esporta', 'download', 'scarica']):
        return "📥 Per scaricare un documento, clicca sull'icona del download (⬇️) nella riga del documento. Puoi anche esportare l'intera lista in CSV o PDF usando i pulsanti in alto a destra della tabella! 📋"
    
    elif any(word in domanda_lower for word in ['statistiche', 'stats', 'numeri']):
        return "📊 Le statistiche sono mostrate nelle card colorate in alto: Documenti Totali (verde), In Revisione (giallo), Documenti Firmati (blu), In Scadenza (rosso). I numeri si aggiornano automaticamente! 📈"
    
    elif any(word in domanda_lower for word in ['aiuto', 'help', 'supporto']):
        return "💡 Sono qui per aiutarti! Puoi chiedermi di: caricare documenti, firmare, cercare, esportare, controllare scadenze, analisi AI e molto altro. Basta scrivere la tua domanda! 🚀"
    
    elif any(word in domanda_lower for word in ['ciao', 'hello', 'salve']):
        return "👋 Ciao! Sono Jack Synthia, il tuo assistente AI per la gestione documenti. Come posso aiutarti oggi? 🤖"
    
    elif any(word in domanda_lower for word in ['grazie', 'thanks', 'thank']):
        return "😊 Prego! Sono sempre qui per aiutarti. Se hai altre domande, non esitare a chiedere! 🚀"
    
    else:
        # Risposta generica per domande non riconosciute
        return "🤔 Interessante domanda! Per il modulo DOCS posso aiutarti con: caricamento documenti, firme digitali, analisi AI, gestione scadenze, filtri e ricerche, esportazioni. Prova a chiedere qualcosa di più specifico! 💡"


@docs_bp.route("/dashboard")
@login_required
def dashboard_docs():
    """
    Dashboard principale per la gestione dei documenti.
    
    Returns:
        template: Template della dashboard con statistiche e lista documenti
    """
    try:
        from datetime import datetime, timedelta
        
        # Ottieni tutti i documenti per l'utente corrente
        if current_user.is_admin or current_user.is_ceo:
            documents = Document.query.all()
        else:
            # Per utenti normali, mostra solo i documenti della loro azienda
            documents = Document.query.filter_by(company_id=current_user.company_id).all()
        
        # Calcola statistiche
        today = datetime.now().date()
        stats = {
            'total_documents': len(documents),
            'pending_review': len([d for d in documents if d.in_revision]),
            'signed_documents': len([d for d in documents if d.signed]),
            'expiring_soon': len([d for d in documents if d.expiry_date and d.expiry_date <= today + timedelta(days=30)])
        }
        
        # Ottieni aziende per il filtro
        from models import Company
        companies = Company.query.all()
        
        # Applica filtri se presenti
        search = request.args.get('search', '')
        category = request.args.get('category', '')
        status = request.args.get('status', '')
        company_id = request.args.get('company', '')
        
        if search:
            documents = [d for d in documents if search.lower() in (d.title or '').lower() or search.lower() in (d.original_filename or '').lower()]
        
        if category:
            documents = [d for d in documents if d.categoria == category]
        
        if status:
            if status == 'attivo':
                documents = [d for d in documents if not d.archiviato]
            elif status == 'in_revisione':
                documents = [d for d in documents if d.in_revision]
            elif status == 'firmato':
                documents = [d for d in documents if d.signed]
            elif status == 'scaduto':
                documents = [d for d in documents if d.expiry_date and d.expiry_date < today]
        
        if company_id:
            documents = [d for d in documents if d.company_id == int(company_id)]
        
        return render_template(
            'docs/dashboard_docs.html',
            documents=documents,
            stats=stats,
            companies=companies,
            today=today
        )
        
    except Exception as e:
        current_app.logger.error(f"Errore nella dashboard documenti: {str(e)}")
        flash("❌ Errore nel caricamento della dashboard", "danger")
        return redirect(url_for('admin.admin_dashboard'))


@docs_bp.route("/documenti/<int:id>/download")
@login_required
def download_document(id):
    """
    Download di un documento.
    
    Args:
        id (int): ID del documento
        
    Returns:
        file: File del documento
    """
    try:
        document = Document.query.get_or_404(id)
        
        # Verifica permessi
        if not current_user.is_admin and not current_user.is_ceo:
            if document.company_id != current_user.company_id:
                flash("❌ Permessi insufficienti per scaricare questo documento", "danger")
                return redirect(url_for("docs.dashboard_docs"))
        
        # Log del download
        from utils.read_tracker import log_download
        log_download(document, current_user)
        
        # Trigger evento Jack (verrà gestito dal frontend)
        # document.dispatchEvent(new CustomEvent('jack-event', {
        #     detail: { type: 'download_document', data: { docId: id } }
        # }))
        
        # Restituisci il file
        return send_file(
            document.file_path,
            as_attachment=True,
            download_name=document.original_filename
        )
        
    except Exception as e:
        current_app.logger.error(f"Errore nel download documento {id}: {str(e)}")
        flash("❌ Errore durante il download del documento", "danger")
        return redirect(url_for("docs.dashboard_docs"))


@docs_bp.route("/documenti/<int:id>/view")
@login_required
def view_document(id):
    """
    Visualizza un documento.
    
    Args:
        id (int): ID del documento
        
    Returns:
        template: Template di visualizzazione documento
    """
    try:
        document = Document.query.get_or_404(id)
        
        # Verifica permessi
        if not current_user.is_admin and not current_user.is_ceo:
            if document.company_id != current_user.company_id:
                flash("❌ Permessi insufficienti per visualizzare questo documento", "danger")
                return redirect(url_for("docs.dashboard_docs"))
        
        return render_template("docs/view_document.html", document=document)
        
    except Exception as e:
        current_app.logger.error(f"Errore nella visualizzazione documento {id}: {str(e)}")
        flash("❌ Errore durante la visualizzazione del documento", "danger")
        return redirect(url_for("docs.dashboard_docs"))


@docs_bp.route("/documenti/<int:id>/archivia", methods=["POST"])
@login_required
@admin_required
def archivia_documento(id):
    """
    Archivia un documento (solo admin/CEO).
    
    Args:
        id (int): ID del documento da archiviare
        
    Returns:
        str: Redirect alla dashboard di revisione
    """
    try:
        doc = Document.query.get_or_404(id)
        
        # Verifica permessi
        if not current_user.is_admin and not current_user.is_ceo:
            flash("❌ Permessi insufficienti per archiviare documenti", "danger")
            return redirect(url_for("docs.dashboard_docs"))
        
        # Archivia il documento
        doc.archiviato = True
        db.session.commit()
        
        flash("📦 Documento archiviato con successo", "success")
        
        # Redirect alla dashboard di revisione se disponibile
        if current_user.is_ceo:
            return redirect(url_for("ceo.dashboard_revisione_ai"))
        else:
            return redirect(url_for("docs.dashboard_docs"))
            
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Errore nell'archiviazione documento {id}: {str(e)}")
        flash("❌ Errore durante l'archiviazione del documento", "danger")
        return redirect(url_for("docs.dashboard_docs"))


@docs_bp.route("/documenti/<int:id>/ripristina", methods=["POST"])
@login_required
@admin_required
def ripristina_documento(id):
    """
    Ripristina un documento archiviato (solo admin/CEO).
    
    Args:
        id (int): ID del documento da ripristinare
        
    Returns:
        str: Redirect alla dashboard appropriata
    """
    try:
        doc = Document.query.get_or_404(id)
        
        # Verifica permessi
        if not current_user.is_admin and not current_user.is_ceo:
            flash("❌ Permessi insufficienti per ripristinare documenti", "danger")
            return redirect(url_for("docs.dashboard_docs"))
        
        # Ripristina il documento
        doc.archiviato = False
        db.session.commit()
        
        flash("✅ Documento ripristinato con successo", "success")
        
        # Redirect alla dashboard appropriata
        if current_user.is_ceo:
            return redirect(url_for("ceo.dashboard_revisione_ai"))
        else:
            return redirect(url_for("docs.dashboard_docs"))
            
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Errore nel ripristino documento {id}: {str(e)}")
        flash("❌ Errore durante il ripristino del documento", "danger")
        return redirect(url_for("docs.dashboard_docs")) 


@docs_bp.route("/documenti/<int:id>/audit/export-pdf")
@login_required
@admin_required
def export_audit_pdf(id):
    """
    Esporta il log di audit di un documento in formato PDF.
    
    Args:
        id (int): ID del documento
        
    Returns:
        file: File PDF con il log di audit
    """
    try:
        doc = Document.query.get_or_404(id)
        logs = doc.audit_logs.order_by(DocumentAuditLog.timestamp.desc()).all()
        
        # Verifica permessi
        if not current_user.is_admin and not current_user.is_ceo:
            flash("❌ Permessi insufficienti per esportare i log di audit", "danger")
            return redirect(url_for("docs.dashboard_docs"))
        
        # Crea PDF semplice (senza dipendenze esterne)
        pdf_content = []
        pdf_content.append(f"Audit Log - {doc.name}")
        pdf_content.append("=" * 50)
        pdf_content.append(f"Documento: {doc.name}")
        pdf_content.append(f"Azienda: {doc.company.name if doc.company else 'N/A'}")
        pdf_content.append(f"Reparto: {doc.department.name if doc.department else 'N/A'}")
        pdf_content.append(f"Data creazione: {doc.created_at.strftime('%d/%m/%Y %H:%M')}")
        pdf_content.append("")
        pdf_content.append("EVENTI DI AUDIT:")
        pdf_content.append("-" * 30)
        
        for log in logs:
            utente = log.user.email if log.user else "Sistema"
            data = log.timestamp.strftime('%d/%m/%Y %H:%M')
            pdf_content.append(f"{data} - {utente}")
            pdf_content.append(f"  Evento: {log.evento}")
            if log.note_ai:
                pdf_content.append(f"  Note AI: {log.note_ai}")
            pdf_content.append("")
        
        # Crea file di testo (simulazione PDF)
        buffer = BytesIO()
        buffer.write('\n'.join(pdf_content).encode('utf-8'))
        buffer.seek(0)
        
        return send_file(
            buffer, 
            as_attachment=True, 
            download_name=f"audit_log_{doc.id}.txt",
            mimetype='text/plain'
        )
        
    except Exception as e:
        current_app.logger.error(f"Errore nell'esportazione PDF audit: {str(e)}")
        flash("❌ Errore durante l'esportazione del log di audit", "danger")
        return redirect(url_for("docs.dashboard_docs"))


@docs_bp.route("/documenti/<int:id>/audit/export-csv")
@login_required
@admin_required
def export_audit_csv(id):
    """
    Esporta il log di audit di un documento in formato CSV.
    
    Args:
        id (int): ID del documento
        
    Returns:
        file: File CSV con il log di audit
    """
    try:
        doc = Document.query.get_or_404(id)
        logs = doc.audit_logs.order_by(DocumentAuditLog.timestamp.desc()).all()
        
        # Verifica permessi
        if not current_user.is_admin and not current_user.is_ceo:
            flash("❌ Permessi insufficienti per esportare i log di audit", "danger")
            return redirect(url_for("docs.dashboard_docs"))
        
        # Crea CSV
        si = StringIO()
        writer = csv.writer(si)
        writer.writerow(["Data", "Utente", "Evento", "Note AI"])
        
        for log in logs:
            utente = log.user.email if log.user else "Sistema"
            data = log.timestamp.strftime('%Y-%m-%d %H:%M')
            writer.writerow([
                data,
                utente,
                log.evento,
                log.note_ai or ''
            ])
        
        # Crea buffer per il download
        output = BytesIO()
        output.write(si.getvalue().encode('utf-8'))
        output.seek(0)
        
        return send_file(
            output, 
            as_attachment=True, 
            download_name=f"audit_log_{doc.id}.csv",
            mimetype='text/csv'
        )
        
    except Exception as e:
        current_app.logger.error(f"Errore nell'esportazione CSV audit: {str(e)}")
        flash("❌ Errore durante l'esportazione del log di audit", "danger")
        return redirect(url_for("docs.dashboard_docs"))


@docs_bp.route("/documenti/<int:id>/audit/summary")
@login_required
@admin_required
def audit_summary(id):
    """
    Mostra un riepilogo del log di audit di un documento.
    
    Args:
        id (int): ID del documento
        
    Returns:
        str: Template con il riepilogo
    """
    try:
        doc = Document.query.get_or_404(id)
        
        # Verifica permessi
        if not current_user.is_admin and not current_user.is_ceo:
            flash("❌ Permessi insufficienti per visualizzare i log di audit", "danger")
            return redirect(url_for("docs.dashboard_docs"))
        
        from utils.audit_logger import get_document_audit_summary
        summary = get_document_audit_summary(doc)
        
        return render_template(
            "audit_summary.html",
            document=doc,
            summary=summary
        )
        
    except Exception as e:
        current_app.logger.error(f"Errore nel riepilogo audit: {str(e)}")
        flash("❌ Errore durante la visualizzazione del riepilogo audit", "danger")
        return redirect(url_for("docs.dashboard_docs")) 


@docs_bp.route("/documenti/<int:id>/track-read", methods=["POST"])
@login_required
def track_document_read_route(id):
    """
    Traccia la lettura di un documento.
    
    Args:
        id (int): ID del documento
        
    Returns:
        JSON: Risultato del tracciamento
    """
    try:
        from utils.read_tracker import track_document_read
        
        document = Document.query.get_or_404(id)
        duration = request.json.get('duration') if request.is_json else None
        
        read_log = track_document_read(document, current_user, duration)
        
        if read_log:
            return {
                'success': True,
                'message': 'Lettura tracciata con successo',
                'is_first_read': read_log.is_first_read
            }
        else:
            return {
                'success': False,
                'message': 'Errore nel tracciamento della lettura'
            }
            
    except Exception as e:
        current_app.logger.error(f"Errore nel tracciamento lettura: {str(e)}")
        return {
            'success': False,
            'message': 'Errore interno del server'
        }


@docs_bp.route("/dashboard/read-tracking")
@login_required
@admin_required
def dashboard_read_tracking():
    """
    Dashboard per il tracciamento delle letture.
    
    Returns:
        str: Template della dashboard
    """
    try:
        from utils.read_tracker import get_user_read_stats, get_document_read_stats
        
        # Statistiche generali
        total_documents = Document.query.count()
        total_reads = DocumentReadLog.query.count()
        total_users = db.session.query(db.func.count(db.distinct(DocumentReadLog.user_id))).scalar()
        
        # Documenti più letti
        most_read_docs = db.session.query(
            Document, 
            db.func.count(DocumentReadLog.id).label('read_count')
        ).join(DocumentReadLog).group_by(Document.id).order_by(
            db.func.count(DocumentReadLog.id).desc()
        ).limit(10).all()
        
        # Utenti con più letture
        most_active_users = db.session.query(
            DocumentReadLog.user_id,
            db.func.count(DocumentReadLog.id).label('read_count')
        ).group_by(DocumentReadLog.user_id).order_by(
            db.func.count(DocumentReadLog.id).desc()
        ).limit(10).all()
        
        # Documenti critici non letti
        critical_docs = Document.query.filter(Document.is_critical == True).all()
        unread_critical = []
        for doc in critical_docs:
            stats = get_document_read_stats(doc)
            if stats.get('read_percentage', 0) < 100:
                unread_critical.append({
                    'document': doc,
                    'stats': stats
                })
        
        return render_template(
            "dashboard_read_tracking.html",
            total_documents=total_documents,
            total_reads=total_reads,
            total_users=total_users,
            most_read_docs=most_read_docs,
            most_active_users=most_active_users,
            unread_critical=unread_critical
        )
        
    except Exception as e:
        current_app.logger.error(f"Errore dashboard read tracking: {str(e)}")
        flash("❌ Errore nel caricamento della dashboard", "danger")
        return redirect(url_for("docs.dashboard_docs"))


@docs_bp.route("/documenti/<int:id>/read-stats")
@login_required
@admin_required
def document_read_stats(id):
    """
    Statistiche di lettura di un documento specifico.
    
    Args:
        id (int): ID del documento
        
    Returns:
        str: Template con le statistiche
    """
    try:
        document = Document.query.get_or_404(id)
        from utils.read_tracker import get_document_read_stats, get_read_duration_stats
        
        read_stats = get_document_read_stats(document)
        duration_stats = get_read_duration_stats(document)
        
        # Lista utenti che hanno letto
        read_logs = DocumentReadLog.query.filter_by(document_id=id).order_by(
            DocumentReadLog.timestamp.desc()
        ).all()
        
        return render_template(
            "document_read_stats.html",
            document=document,
            read_stats=read_stats,
            duration_stats=duration_stats,
            read_logs=read_logs
        )
        
    except Exception as e:
        current_app.logger.error(f"Errore statistiche lettura: {str(e)}")
        flash("❌ Errore nel caricamento delle statistiche", "danger")
        return redirect(url_for("docs.dashboard_docs"))


@docs_bp.route("/export/read-tracking/csv")
@login_required
@admin_required
def export_read_tracking_csv():
    """
    Esporta i dati di tracciamento letture in CSV.
    
    Returns:
        file: File CSV con i dati
    """
    try:
        # Ottieni tutti i log di lettura
        read_logs = DocumentReadLog.query.order_by(DocumentReadLog.timestamp.desc()).all()
        
        # Crea CSV
        si = StringIO()
        writer = csv.writer(si)
        writer.writerow(["Data", "Utente", "Documento", "Prima Lettura", "Durata (sec)", "IP"])
        
        for log in read_logs:
            writer.writerow([
                log.timestamp.strftime('%Y-%m-%d %H:%M'),
                log.user.email if log.user else "N/A",
                log.document.name if log.document else "N/A",
                "Sì" if log.is_first_read else "No",
                log.read_duration or "",
                log.ip_address or ""
            ])
        
        # Crea buffer per il download
        output = BytesIO()
        output.write(si.getvalue().encode('utf-8'))
        output.seek(0)
        
        return send_file(
            output, 
            as_attachment=True, 
            download_name="read_tracking.csv",
            mimetype='text/csv'
        )
        
    except Exception as e:
        current_app.logger.error(f"Errore nell'esportazione CSV: {str(e)}")
        flash("❌ Errore durante l'esportazione", "danger")
        return redirect(url_for("docs.dashboard_docs")) 


@docs_bp.route("/documenti/<int:id>/letture/export")
@login_required
@admin_required
def export_letture_csv(id):
    """
    Export CSV delle letture di un documento.
    
    Args:
        id (int): ID del documento
        
    Returns:
        CSV: File CSV con le letture
    """
    try:
        import csv
        from io import StringIO
        
        document = Document.query.get_or_404(id)
        
        # Crea il CSV in memoria
        si = StringIO()
        writer = csv.writer(si)
        
        # Header
        writer.writerow([
            "Nome utente", 
            "Email", 
            "Data lettura", 
            "Prima lettura", 
            "Durata (sec)", 
            "IP Address"
        ])
        
        # Dati
        for log in document.read_logs:
            writer.writerow([
                f"{log.user.first_name} {log.user.last_name}" if log.user.first_name and log.user.last_name else log.user.username,
                log.user.email,
                log.timestamp.strftime("%d/%m/%Y %H:%M:%S"),
                "Sì" if log.is_first_read else "No",
                log.read_duration or "N/A",
                log.ip_address or "N/A"
            ])
        
        # Prepara la risposta
        output = si.getvalue()
        si.close()
        
        return Response(
            output,
            mimetype="text/csv",
            headers={"Content-Disposition": f"attachment;filename=letture_{document.title}_{datetime.now().strftime('%Y%m%d')}.csv"}
        )
        
    except Exception as e:
        flash(f"❌ Errore durante l'export: {str(e)}", "danger")
        return redirect(url_for("docs.dashboard_docs"))


def has_user_read_document(user, document):
    """
    Helper function per template per verificare se un utente ha letto un documento.
    """
    from utils.read_tracker import has_user_read_document as check_read
    return check_read(user, document)

# La registrazione della funzione helper verrà fatta durante l'inizializzazione dell'app 

@docs_bp.route("/documenti/<int:id>/visualizza")
@login_required
def visualizza_documento(id):
    """
    Visualizza un documento e traccia la lettura.
    
    Args:
        id (int): ID del documento
        
    Returns:
        template: Template del documento
    """
    try:
        from utils.read_tracker import track_document_read
        
        document = Document.query.get_or_404(id)
        
        # Tracciamento lettura automatico
        if current_user.is_authenticated:
            track_document_read(document, current_user)
        
        return render_template("documenti/view_document.html", document=document)
        
    except Exception as e:
        flash(f"❌ Errore durante la visualizzazione: {str(e)}", "danger")
        return redirect(url_for("docs.dashboard_docs")) 