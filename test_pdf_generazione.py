#!/usr/bin/env python3
"""
Script di test per la generazione PDF delle versioni documenti.
"""

import os
import sys
from datetime import datetime

# Aggiungi il path del progetto
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import DocumentVersion, User, Document, DocumentReadLog
from weasyprint import HTML, CSS
from weasyprint.text.fonts import FontConfiguration

def test_generazione_pdf():
    """
    Test della generazione PDF per una versione documento.
    """
    with app.app_context():
        print("📄 Test Generazione PDF Versione Documento")
        print("=" * 60)
        
        # Ottieni versione di test
        versione = DocumentVersion.query.first()
        
        if not versione:
            print("❌ Nessuna versione trovata")
            return
        
        doc = versione.document
        print(f"📄 Documento: {doc.title or doc.original_filename}")
        print(f"📋 Versione: {versione.numero_versione}")
        print(f"📅 Data: {versione.data_caricamento.strftime('%d/%m/%Y')}")
        print(f"👥 Firme: {len(versione.read_logs)}")
        print()
        
        try:
            # Genera il contenuto HTML per il PDF
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <title>Test PDF - {doc.title or doc.original_filename}</title>
                <style>
                    body {{
                        font-family: Arial, sans-serif;
                        margin: 20px;
                        color: #333;
                    }}
                    .header {{
                        border-bottom: 2px solid #007bff;
                        padding-bottom: 10px;
                        margin-bottom: 20px;
                    }}
                    .title {{
                        font-size: 24px;
                        font-weight: bold;
                        color: #007bff;
                        margin-bottom: 5px;
                    }}
                    .subtitle {{
                        font-size: 18px;
                        color: #666;
                        margin-bottom: 10px;
                    }}
                    .info-section {{
                        margin-bottom: 20px;
                    }}
                    .info-row {{
                        margin-bottom: 8px;
                    }}
                    .label {{
                        font-weight: bold;
                        display: inline-block;
                        width: 120px;
                    }}
                    .value {{
                        display: inline-block;
                    }}
                    .firme-table {{
                        width: 100%;
                        border-collapse: collapse;
                        margin-top: 20px;
                    }}
                    .firme-table th, .firme-table td {{
                        border: 1px solid #ddd;
                        padding: 8px;
                        text-align: left;
                    }}
                    .firme-table th {{
                        background-color: #f8f9fa;
                        font-weight: bold;
                    }}
                    .status-confermata {{
                        color: #28a745;
                        font-weight: bold;
                    }}
                    .status-in-attesa {{
                        color: #ffc107;
                        font-weight: bold;
                    }}
                    .note-section {{
                        margin-top: 20px;
                        padding: 15px;
                        background-color: #f8f9fa;
                        border-left: 4px solid #007bff;
                    }}
                </style>
            </head>
            <body>
                <div class="header">
                    <div class="title">{doc.title or doc.original_filename}</div>
                    <div class="subtitle">Versione {versione.numero_versione}</div>
                </div>
                
                <div class="info-section">
                    <div class="info-row">
                        <span class="label">Azienda:</span>
                        <span class="value">{doc.company.name}</span>
                    </div>
                    <div class="info-row">
                        <span class="label">Reparto:</span>
                        <span class="value">{doc.department.name}</span>
                    </div>
                    <div class="info-row">
                        <span class="label">Uploader:</span>
                        <span class="value">{doc.uploader_email}</span>
                    </div>
                    <div class="info-row">
                        <span class="label">Data Caricamento:</span>
                        <span class="value">{versione.data_caricamento.strftime('%d/%m/%Y %H:%M')}</span>
                    </div>
                    <div class="info-row">
                        <span class="label">File:</span>
                        <span class="value">{versione.filename}</span>
                    </div>
                </div>
                
                <div class="note-section">
                    <strong>Note sulla Versione:</strong><br>
                    {versione.note or 'Nessuna nota disponibile'}
                </div>
                
                <h2>Firme Associate alla Versione {versione.numero_versione}</h2>
                
                <table class="firme-table">
                    <thead>
                        <tr>
                            <th>Nome Utente</th>
                            <th>Email</th>
                            <th>Ruolo</th>
                            <th>Data Firma</th>
                            <th>Stato</th>
                            <th>Data Conferma</th>
                        </tr>
                    </thead>
                    <tbody>
            """
            
            # Aggiungi le firme alla tabella
            if versione.read_logs:
                for firma in versione.read_logs:
                    stato_class = "status-confermata" if firma.confermata else "status-in-attesa"
                    stato_text = "✅ Confermata" if firma.confermata else "⏳ In Attesa"
                    data_conferma = firma.data_conferma.strftime('%d/%m/%Y %H:%M') if firma.data_conferma else '-'
                    
                    html_content += f"""
                        <tr>
                            <td>{firma.user.username}</td>
                            <td>{firma.user.email}</td>
                            <td>{firma.user.role}</td>
                            <td>{firma.timestamp.strftime('%d/%m/%Y %H:%M')}</td>
                            <td class="{stato_class}">{stato_text}</td>
                            <td>{data_conferma}</td>
                        </tr>
                    """
            else:
                html_content += """
                        <tr>
                            <td colspan="6" style="text-align: center; color: #666;">Nessuna firma registrata per questa versione</td>
                        </tr>
                    """
            
            html_content += """
                    </tbody>
                </table>
                
                <div style="margin-top: 30px; text-align: center; color: #666; font-size: 12px;">
                    <p>Documento generato automaticamente il """ + datetime.utcnow().strftime('%d/%m/%Y alle %H:%M') + """</p>
                    <p>Sistema di Gestione Documenti - Test Generazione PDF</p>
                </div>
            </body>
            </html>
            """
            
            # Configura WeasyPrint
            font_config = FontConfiguration()
            css = CSS(string='''
                @page {
                    size: A4;
                    margin: 2cm;
                    @bottom-center {
                        content: "Pagina " counter(page) " di " counter(pages);
                    }
                }
            ''', font_config=font_config)
            
            # Genera il PDF
            print("🔄 Generazione PDF in corso...")
            html_doc = HTML(string=html_content)
            pdf_bytes = html_doc.write_pdf(stylesheets=[css], font_config=font_config)
            
            # Salva il PDF di test
            test_filename = f"test_pdf_versione_{versione.numero_versione}.pdf"
            with open(test_filename, 'wb') as f:
                f.write(pdf_bytes)
            
            print(f"✅ PDF generato con successo!")
            print(f"📁 File salvato: {test_filename}")
            print(f"📊 Dimensione: {len(pdf_bytes)} bytes")
            
            # Verifica che il file sia stato creato
            if os.path.exists(test_filename):
                file_size = os.path.getsize(test_filename)
                print(f"✅ File verificato: {file_size} bytes")
                
                # Rimuovi il file di test
                os.remove(test_filename)
                print(f"🗑️ File di test rimosso")
            else:
                print("❌ Errore: file non trovato")
            
        except Exception as e:
            print(f"❌ Errore durante la generazione PDF: {e}")
            import traceback
            traceback.print_exc()
        
        print(f"\n✅ Test completato!")

if __name__ == "__main__":
    test_generazione_pdf() 