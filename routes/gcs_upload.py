from flask import Blueprint, request, redirect, url_for, flash, current_app
from google.cloud import storage
from werkzeug.utils import secure_filename

gcs_upload_bp = Blueprint('gcs_upload', __name__, url_prefix='/gcs')

GCS_CREDENTIALS = "/var/www/gestione_doc/gcp_credentials.json"
GCS_BUCKET = "mio-bucket-di-test"

@gcs_upload_bp.route('/upload', methods=['POST'])
def upload_to_gcs():
    if 'file' not in request.files:
        flash("Nessun file selezionato", "danger")
        return redirect(url_for('dashboard'))

    file = request.files['file']
    if file.filename == '':
        flash("Nome file vuoto", "danger")
        return redirect(url_for('dashboard'))

    filename = secure_filename(file.filename)
    blob_path = f"documenti/webapp/{filename}"

    try:
        client = storage.Client.from_service_account_json(GCS_CREDENTIALS)
        bucket = client.bucket(GCS_BUCKET)
        blob = bucket.blob(blob_path)
        blob.upload_from_file(file.stream, content_type=file.content_type)

        current_app.logger.info(f"[GCS UPLOAD] File caricato su GCS: {blob_path}")
        flash(f"✅ File caricato su GCS: {blob_path}", "success")
    except Exception as e:
        current_app.logger.error(f"[GCS ERROR] Errore durante l'upload: {e}")
        flash("❌ Errore durante l'upload del file su GCS", "danger")

    return redirect(url_for('dashboard'))
