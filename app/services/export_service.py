"""
Servizio per l'esportazione intelligente di documenti in PDF e CSV.

Fornisce funzionalità per esportare:
- Metadati del documento
- Versione AI attiva (titolo, descrizione, aforisma)
- Cronologia eventi (notifiche AI, sync, download)
- Versioni precedenti (opzionale)
- Firma digitale o QR code (opzionale)
"""

import io
import csv
import qrcode
from datetime import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from fastapi.responses import StreamingResponse
from weasyprint import HTML, CSS
from jinja2 import Template
import base64
from PIL import Image

from models import Document, User, Company, Department
from app.models.analisi_ai_version import VersioneAnalisiAI
from app.models.notifiche import NotificaAI
from app.services.documenti_eventi import get_timeline_eventi_documento


class ExportService:
    """Servizio per l'esportazione intelligente di documenti."""
    
    def __init__(self, db: Session):
        """
        Inizializza il servizio di esportazione.
        
        Args:
            db (Session): Sessione database.
        """
        self.db = db
    
    def get_document_data(self, document_id: int) -> Dict[str, Any]:
        """
        Recupera tutti i dati del documento per l'esportazione.
        
        Args:
            document_id (int): ID del documento.
            
        Returns:
            Dict[str, Any]: Dati completi del documento.
        """
        # Recupera documento con relazioni
        document = self.db.query(Document).filter_by(id=document_id).first()
        if not document:
            raise ValueError(f"Documento {document_id} non trovato")
        
        # Recupera versione AI attiva
        versione_ai_attiva = self.db.query(VersioneAnalisiAI).filter_by(
            documento_id=document_id, 
            attiva=True
        ).first()
        
        # Recupera tutte le versioni AI
        versioni_ai = self.db.query(VersioneAnalisiAI).filter_by(
            documento_id=document_id
        ).order_by(VersioneAnalisiAI.data_creazione.desc()).all()
        
        # Recupera notifiche AI
        notifiche_ai = self.db.query(NotificaAI).filter_by(
            documento_id=document_id
        ).order_by(NotificaAI.data_invio.desc()).all()
        
        # Recupera timeline eventi
        timeline_eventi = get_timeline_eventi_documento(self.db, document_id)
        
        # Recupera uploader
        uploader = self.db.query(User).filter_by(id=document.user_id).first()
        
        return {
            "document": document,
            "versione_ai_attiva": versione_ai_attiva,
            "versioni_ai": versioni_ai,
            "notifiche_ai": notifiche_ai,
            "timeline_eventi": timeline_eventi,
            "uploader": uploader,
            "company": document.company,
            "department": document.department
        }
    
    def generate_qr_code(self, data: str) -> str:
        """
        Genera un QR code con i dati forniti.
        
        Args:
            data (str): Dati da codificare nel QR code.
            
        Returns:
            str: QR code in formato base64.
        """
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(data)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Converti in base64
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        img_base64 = base64.b64encode(buffer.getvalue()).decode()
        
        return f"data:image/png;base64,{img_base64}"
    
    def generate_pdf(self, document_id: int, include_versions: bool = False) -> bytes:
        """
        Genera un PDF con tutti i dati del documento.
        
        Args:
            document_id (int): ID del documento.
            include_versions (bool): Se includere tutte le versioni AI.
            
        Returns:
            bytes: Contenuto del PDF.
        """
        data = self.get_document_data(document_id)
        
        # Genera QR code per il documento
        qr_data = f"DOC:{document_id}|{data['document'].title}|{datetime.utcnow().isoformat()}"
        qr_code = self.generate_qr_code(qr_data)
        
        # Template HTML per il PDF
        html_template = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Analisi Documento - {{ document.title }}</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; }
                .header { text-align: center; border-bottom: 2px solid #333; padding-bottom: 10px; margin-bottom: 30px; }
                .section { margin: 20px 0; }
                .section h2 { color: #2c3e50; border-left: 4px solid #3498db; padding-left: 10px; }
                .metadata { background: #f8f9fa; padding: 15px; border-radius: 5px; }
                .metadata table { width: 100%; border-collapse: collapse; }
                .metadata td { padding: 8px; border-bottom: 1px solid #ddd; }
                .metadata td:first-child { font-weight: bold; width: 30%; }
                .ai-box { background: #e8f4fd; border: 2px solid #3498db; padding: 15px; border-radius: 5px; margin: 15px 0; }
                .ai-box h3 { color: #2980b9; margin-top: 0; }
                .timeline { margin: 15px 0; }
                .timeline-item { border-left: 3px solid #3498db; padding-left: 15px; margin: 10px 0; }
                .timeline-date { color: #7f8c8d; font-size: 0.9em; }
                .qr-code { text-align: center; margin: 20px 0; }
                .qr-code img { max-width: 200px; }
                .footer { text-align: center; margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd; color: #7f8c8d; }
                .version-item { background: #f1f2f6; padding: 10px; margin: 10px 0; border-radius: 3px; }
                .active-version { background: #d4edda; border: 1px solid #c3e6cb; }
            </style>
        </head>
        <body>
            <div class="header">
                <h1>📄 Analisi Documento</h1>
                <h2>{{ document.title }}</h2>
                <p>Generato il: {{ generation_date }}</p>
            </div>
            
            <div class="section">
                <h2>📋 Metadati Documento</h2>
                <div class="metadata">
                    <table>
                        <tr><td>Titolo:</td><td>{{ document.title }}</td></tr>
                        <tr><td>Descrizione:</td><td>{{ document.description or 'N/A' }}</td></tr>
                        <tr><td>File originale:</td><td>{{ document.original_filename }}</td></tr>
                        <tr><td>Uploader:</td><td>{{ uploader.first_name }} {{ uploader.last_name }} ({{ uploader.email }})</td></tr>
                        <tr><td>Azienda:</td><td>{{ company.name }}</td></tr>
                        <tr><td>Reparto:</td><td>{{ department.name }}</td></tr>
                        <tr><td>Visibilità:</td><td>{{ document.visibility }}</td></tr>
                        <tr><td>Data creazione:</td><td>{{ document.created_at.strftime('%d/%m/%Y %H:%M') }}</td></tr>
                        <tr><td>Downloadable:</td><td>{{ 'Sì' if document.downloadable else 'No' }}</td></tr>
                        {% if document.expiry_date %}
                        <tr><td>Data scadenza:</td><td>{{ document.expiry_date.strftime('%d/%m/%Y') }}</td></tr>
                        {% endif %}
                    </table>
                </div>
            </div>
            
            {% if versione_ai_attiva %}
            <div class="section">
                <h2>🤖 Versione AI Attiva</h2>
                <div class="ai-box">
                    <h3>{{ versione_ai_attiva.titolo }}</h3>
                    <p><strong>Descrizione:</strong> {{ versione_ai_attiva.descrizione }}</p>
                    {% if versione_ai_attiva.aforisma %}
                    <p><strong>Aforisma:</strong> "{{ versione_ai_attiva.aforisma }}"</p>
                    {% endif %}
                    {% if versione_ai_attiva.autore %}
                    <p><strong>Autore:</strong> {{ versione_ai_attiva.autore }}</p>
                    {% endif %}
                    <p><strong>Data creazione:</strong> {{ versione_ai_attiva.data_creazione.strftime('%d/%m/%Y %H:%M') }}</p>
                    <p><strong>Generata da AI:</strong> {{ 'Sì' if versione_ai_attiva.generata_da_ai else 'No' }}</p>
                </div>
            </div>
            {% endif %}
            
            {% if include_versions and versioni_ai %}
            <div class="section">
                <h2>📚 Cronologia Versioni AI</h2>
                {% for versione in versioni_ai %}
                <div class="version-item {% if versione.attiva %}active-version{% endif %}">
                    <h4>{{ versione.titolo }}</h4>
                    <p>{{ versione.descrizione }}</p>
                    {% if versione.aforisma %}
                    <p><em>"{{ versione.aforisma }}"</em></p>
                    {% endif %}
                    <p><strong>Data:</strong> {{ versione.data_creazione.strftime('%d/%m/%Y %H:%M') }}</p>
                    <p><strong>Stato:</strong> {{ 'Attiva' if versione.attiva else 'Inattiva' }}</p>
                </div>
                {% endfor %}
            </div>
            {% endif %}
            
            <div class="section">
                <h2>📊 Timeline Eventi</h2>
                <div class="timeline">
                    {% for evento in timeline_eventi %}
                    <div class="timeline-item">
                        <div class="timeline-date">{{ evento.timestamp.strftime('%d/%m/%Y %H:%M') }}</div>
                        <div><strong>{{ evento.tipo }}</strong>: {{ evento.descrizione }}</div>
                        {% if evento.dettagli %}
                        <div style="color: #666; font-size: 0.9em;">{{ evento.dettagli }}</div>
                        {% endif %}
                    </div>
                    {% endfor %}
                </div>
            </div>
            
            {% if notifiche_ai %}
            <div class="section">
                <h2>🔔 Notifiche AI</h2>
                <div class="timeline">
                    {% for notifica in notifiche_ai %}
                    <div class="timeline-item">
                        <div class="timeline-date">{{ notifica.data_invio.strftime('%d/%m/%Y %H:%M') }}</div>
                        <div><strong>{{ notifica.tipo_evento }}</strong>: {{ notifica.messaggio }}</div>
                        <div style="color: #666; font-size: 0.9em;">
                            Canale: {{ notifica.canale }} | Esito: {{ notifica.esito }}
                        </div>
                    </div>
                    {% endfor %}
                </div>
            </div>
            {% endif %}
            
            <div class="qr-code">
                <h3>🔍 QR Code Documento</h3>
                <img src="{{ qr_code }}" alt="QR Code">
                <p>Scansiona per verificare l'autenticità</p>
            </div>
            
            <div class="footer">
                <p>Documento ID: {{ document.id }</p>
                <p>Generato automaticamente dal sistema di gestione documenti</p>
            </div>
        </body>
        </html>
        """
        
        # Renderizza il template
        template = Template(html_template)
        html_content = template.render(
            document=data['document'],
            versione_ai_attiva=data['versione_ai_attiva'],
            versioni_ai=data['versioni_ai'],
            notifiche_ai=data['notifiche_ai'],
            timeline_eventi=data['timeline_eventi'],
            uploader=data['uploader'],
            company=data['company'],
            department=data['department'],
            generation_date=datetime.utcnow().strftime('%d/%m/%Y %H:%M'),
            qr_code=qr_code,
            include_versions=include_versions
        )
        
        # Genera PDF
        html = HTML(string=html_content)
        pdf_bytes = html.write_pdf()
        
        return pdf_bytes
    
    def generate_csv(self, document_id: int) -> StreamingResponse:
        """
        Genera un CSV con i dati del documento per audit.
        
        Args:
            document_id (int): ID del documento.
            
        Returns:
            StreamingResponse: CSV stream.
        """
        data = self.get_document_data(document_id)
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Header
        writer.writerow([
            "Timestamp", "Tipo Evento", "Descrizione", 
            "Versione AI Attiva", "Titolo AI", "Descrizione AI", "Aforisma AI"
        ])
        
        # Dati documento
        versione_ai = data['versione_ai_attiva']
        ai_titolo = versione_ai.titolo if versione_ai else "N/A"
        ai_desc = versione_ai.descrizione if versione_ai else "N/A"
        ai_aforisma = versione_ai.aforisma if versione_ai else "N/A"
        
        # Eventi timeline
        for evento in data['timeline_eventi']:
            writer.writerow([
                evento.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                evento.tipo,
                evento.descrizione,
                "Sì" if versione_ai else "No",
                ai_titolo,
                ai_desc,
                ai_aforisma
            ])
        
        # Notifiche AI
        for notifica in data['notifiche_ai']:
            writer.writerow([
                notifica.data_invio.strftime('%Y-%m-%d %H:%M:%S'),
                f"Notifica AI - {notifica.tipo_evento}",
                notifica.messaggio,
                "Sì" if versione_ai else "No",
                ai_titolo,
                ai_desc,
                ai_aforisma
            ])
        
        output.seek(0)
        
        return StreamingResponse(
            io.StringIO(output.getvalue()),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=documento_{document_id}_audit.csv"
            }
        ) 