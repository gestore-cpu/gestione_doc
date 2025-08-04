#!/usr/bin/env python3
"""
Script di test per la generazione HTML delle versioni documenti.
"""

import os
import sys
from datetime import datetime

# Aggiungi il path del progetto
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import DocumentVersion, User, Document, DocumentReadLog

def test_generazione_html():
    """
    Test della generazione HTML per una versione documento.
    """
    with app.app_context():
        print("📄 Test Generazione HTML Versione Documento")
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
            # Genera il contenuto HTML ottimizzato per stampa/PDF
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <title>Test HTML - {doc.title or doc.original_filename}</title>
                <style>
                    @media print {{
                        body {{ margin: 0; padding: 20px; }}
                        .no-print {{ display: none; }}
                        .page-break {{ page-break-before: always; }}
                    }}
                    
                    body {{
                        font-family: Arial, sans-serif;
                        margin: 20px;
                        color: #333;
                        line-height: 1.6;
                    }}
                    
                    .header {{
                        border-bottom: 2px solid #007bff;
                        padding-bottom: 15px;
                        margin-bottom: 25px;
                    }}
                    
                    .title {{
                        font-size: 28px;
                        font-weight: bold;
                        color: #007bff;
                        margin-bottom: 8px;
                    }}
                    
                    .subtitle {{
                        font-size: 20px;
                        color: #666;
                        margin-bottom: 15px;
                    }}
                    
                    .info-section {{
                        margin-bottom: 25px;
                        background-color: #f8f9fa;
                        padding: 15px;
                        border-radius: 5px;
                    }}
                    
                    .info-row {{
                        margin-bottom: 10px;
                        display: flex;
                    }}
                    
                    .label {{
                        font-weight: bold;
                        min-width: 150px;
                        color: #495057;
                    }}
                    
                    .value {{
                        flex: 1;
                    }}
                    
                    .note-section {{
                        margin: 25px 0;
                        padding: 20px;
                        background-color: #e3f2fd;
                        border-left: 5px solid #007bff;
                        border-radius: 5px;
                    }}
                    
                    .firme-section {{
                        margin-top: 30px;
                    }}
                    
                    .firme-table {{
                        width: 100%;
                        border-collapse: collapse;
                        margin-top: 20px;
                        font-size: 14px;
                    }}
                    
                    .firme-table th, .firme-table td {{
                        border: 1px solid #dee2e6;
                        padding: 12px 8px;
                        text-align: left;
                    }}
                    
                    .firme-table th {{
                        background-color: #007bff;
                        color: white;
                        font-weight: bold;
                    }}
                    
                    .firme-table tr:nth-child(even) {{
                        background-color: #f8f9fa;
                    }}
                    
                    .status-confermata {{
                        color: #28a745;
                        font-weight: bold;
                    }}
                    
                    .status-in-attesa {{
                        color: #ffc107;
                        font-weight: bold;
                    }}
                    
                    .footer {{
                        margin-top: 40px;
                        text-align: center;
                        color: #666;
                        font-size: 12px;
                        border-top: 1px solid #dee2e6;
                        padding-top: 20px;
                    }}
                    
                    .print-button {{
                        position: fixed;
                        top: 20px;
                        right: 20px;
                        background-color: #007bff;
                        color: white;
                        border: none;
                        padding: 10px 20px;
                        border-radius: 5px;
                        cursor: pointer;
                        font-size: 14px;
                    }}
                    
                    .print-button:hover {{
                        background-color: #0056b3;
                    }}
                    
                    @media print {{
                        .print-button {{ display: none; }}
                    }}
                </style>
            </head>
            <body>
                <button class="print-button no-print" onclick="window.print()">🖨️ Stampa PDF</button>
                
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
                    <strong>📝 Note sulla Versione:</strong><br>
                    {versione.note or 'Nessuna nota disponibile'}
                </div>
                
                <div class="firme-section">
                    <h2>👥 Firme Associate alla Versione {versione.numero_versione}</h2>
                    
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
                            <td><strong>{firma.user.username}</strong></td>
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
                            <td colspan="6" style="text-align: center; color: #666; font-style: italic;">
                                Nessuna firma registrata per questa versione
                            </td>
                        </tr>
                    """
            
            html_content += f"""
                        </tbody>
                    </table>
                    
                    <div class="footer">
                        <p>📄 Documento generato automaticamente il {datetime.utcnow().strftime('%d/%m/%Y alle %H:%M')}</p>
                        <p>🏢 Sistema di Gestione Documenti - Test Generazione HTML</p>
                        <p>📋 Per convertire in PDF: usa la funzione di stampa del browser (Ctrl+P)</p>
                    </div>
                </body>
                </html>
                """
            
            # Salva l'HTML di test
            test_filename = f"test_html_versione_{versione.numero_versione}.html"
            with open(test_filename, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            print(f"✅ HTML generato con successo!")
            print(f"📁 File salvato: {test_filename}")
            print(f"📊 Dimensione: {len(html_content)} caratteri")
            
            # Verifica che il file sia stato creato
            if os.path.exists(test_filename):
                file_size = os.path.getsize(test_filename)
                print(f"✅ File verificato: {file_size} bytes")
                
                # Mostra un preview del contenuto
                print(f"\n📋 Preview del contenuto:")
                print(f"   - Titolo: {doc.title or doc.original_filename}")
                print(f"   - Versione: {versione.numero_versione}")
                print(f"   - Firme incluse: {len(versione.read_logs)}")
                print(f"   - Note: {versione.note or 'Nessuna'}")
                
                # Rimuovi il file di test
                os.remove(test_filename)
                print(f"🗑️ File di test rimosso")
            else:
                print("❌ Errore: file non trovato")
            
        except Exception as e:
            print(f"❌ Errore durante la generazione HTML: {e}")
            import traceback
            traceback.print_exc()
        
        print(f"\n✅ Test completato!")

if __name__ == "__main__":
    test_generazione_html() 