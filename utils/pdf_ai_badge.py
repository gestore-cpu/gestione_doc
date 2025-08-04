#!/usr/bin/env python3
"""
Modulo per l'incorporazione di badge AI nei PDF.
Rende i documenti self-explaining e audit-ready.
"""

import os
import json
import tempfile
from datetime import datetime
from weasyprint import HTML, CSS
from weasyprint.text.fonts import FontConfiguration
import fitz  # PyMuPDF per metadati
from flask import render_template_string

def badge_color(status):
    """
    Restituisce il colore del badge basato sullo stato AI.
    
    Args:
        status (str): Stato AI del documento
        
    Returns:
        str: Codice colore hex
    """
    return {
        "completo": "#28a745",      # Verde
        "incompleto": "#ffc107",    # Giallo
        "scaduto": "#dc3545",       # Rosso
        "manca_firma": "#dc3545",   # Rosso
        "non_analizzato": "#6c757d" # Grigio
    }.get(status.lower(), "#6c757d")

def badge_icon(status):
    """
    Restituisce l'icona del badge basata sullo stato AI.
    
    Args:
        status (str): Stato AI del documento
        
    Returns:
        str: Emoji icona
    """
    return {
        "completo": "✅",
        "incompleto": "⚠️",
        "scaduto": "❌",
        "manca_firma": "❌",
        "non_analizzato": "📄"
    }.get(status.lower(), "📄")

def generate_ai_badge_html(ai_status, ai_explain, document_title=None):
    """
    Genera HTML per il badge AI da incorporare nel PDF.
    
    Args:
        ai_status (str): Stato AI del documento
        ai_explain (str): Spiegazione AI
        document_title (str, optional): Titolo del documento
        
    Returns:
        str: HTML del badge AI
    """
    status = ai_status or "non_analizzato"
    explain = ai_explain or "Documento non ancora analizzato"
    icon = badge_icon(status)
    color = badge_color(status)
    
    badge_html = f"""
    <div style="
        background: {color};
        color: white;
        padding: 15px;
        margin: 0 0 20px 0;
        border-radius: 8px;
        font-family: Arial, sans-serif;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    ">
        <div style="
            display: flex;
            align-items: center;
            font-size: 16px;
            font-weight: bold;
            margin-bottom: 8px;
        ">
            <span style="font-size: 20px; margin-right: 10px;">{icon}</span>
            STATO AI: {status.upper()}
        </div>
        <div style="
            font-size: 14px;
            line-height: 1.4;
            opacity: 0.9;
        ">
            {explain}
        </div>
        <div style="
            font-size: 11px;
            margin-top: 8px;
            opacity: 0.7;
            border-top: 1px solid rgba(255,255,255,0.3);
            padding-top: 8px;
        ">
            📄 Generato automaticamente da Mercury Document Intelligence
            <br>
            🕒 {datetime.now().strftime('%d/%m/%Y %H:%M')}
        </div>
    </div>
    """
    
    return badge_html

def embed_json_metadata(pdf_path, analysis_data):
    """
    Incorpora metadati JSON AI nel PDF usando PyMuPDF.
    
    Args:
        pdf_path (str): Percorso del file PDF
        analysis_data (dict): Dati di analisi AI da incorporare
        
    Returns:
        bool: True se successo, False altrimenti
    """
    try:
        # Apri il PDF
        doc = fitz.open(pdf_path)
        
        # Prepara i metadati AI
        ai_metadata = {
            "ai_analysis": analysis_data,
            "generated_at": datetime.now().isoformat(),
            "version": "1.0",
            "source": "Mercury Document Intelligence"
        }
        
        # Incorpora nei metadati del PDF
        doc.set_metadata({
            "Title": doc.metadata.get("Title", "Documento Mercury"),
            "Author": "Mercury Document Intelligence",
            "Subject": "Documento con analisi AI incorporata",
            "Creator": "Mercury Surgelati",
            "Producer": "WeasyPrint + PyMuPDF",
            "ai_analysis": json.dumps(ai_metadata, indent=2, ensure_ascii=False)
        })
        
        # Salva il PDF modificato
        doc.save(pdf_path, incremental=True)
        doc.close()
        
        return True
        
    except Exception as e:
        print(f"❌ Errore nell'incorporazione metadati AI: {e}")
        return False

def genera_pdf_from_html(html_content, output_path, ai_badge=None, ai_explain=None, ai_analysis=None, document_title=None):
    """
    Genera PDF da HTML con badge AI incorporato.
    
    Args:
        html_content (str): Contenuto HTML del documento
        output_path (str): Percorso di output del PDF
        ai_badge (str, optional): Stato AI del documento
        ai_explain (str, optional): Spiegazione AI
        ai_analysis (dict, optional): Dati analisi AI completi
        document_title (str, optional): Titolo del documento
        
    Returns:
        bool: True se successo, False altrimenti
    """
    try:
        # Inietta badge AI se fornito
        if ai_badge and ai_explain:
            badge_html = generate_ai_badge_html(ai_badge, ai_explain, document_title)
            html_content = badge_html + html_content
        
        # Configurazione font
        font_config = FontConfiguration()
        
        # CSS per il PDF
        css_content = """
        @page {
            size: A4;
            margin: 2cm;
            @top-center {
                content: "Mercury Document Intelligence";
                font-size: 10pt;
                color: #666;
            }
            @bottom-center {
                content: "Pagina " counter(page) " di " counter(pages);
                font-size: 10pt;
                color: #666;
            }
        }
        
        body {
            font-family: Arial, sans-serif;
            font-size: 12pt;
            line-height: 1.4;
            color: #333;
        }
        
        h1, h2, h3 {
            color: #007bff;
            margin-top: 20px;
            margin-bottom: 10px;
        }
        
        table {
            border-collapse: collapse;
            width: 100%;
            margin: 15px 0;
        }
        
        th, td {
            border: 1px solid #ddd;
            padding: 8px;
            text-align: left;
        }
        
        th {
            background-color: #f8f9fa;
            font-weight: bold;
        }
        
        .ai-badge {
            page-break-inside: avoid;
            margin-bottom: 20px;
        }
        """
        
        # Genera PDF con WeasyPrint
        HTML(string=html_content).write_pdf(
            output_path,
            stylesheets=[CSS(string=css_content)],
            font_config=font_config
        )
        
        # Incorpora metadati AI se forniti
        if ai_analysis and os.path.exists(output_path):
            embed_json_metadata(output_path, ai_analysis)
        
        return True
        
    except Exception as e:
        print(f"❌ Errore nella generazione PDF con badge AI: {e}")
        return False

def create_ai_analysis_data(document, ai_status=None, ai_explain=None):
    """
    Crea oggetto dati analisi AI per incorporazione.
    
    Args:
        document: Oggetto Document
        ai_status (str, optional): Stato AI
        ai_explain (str, optional): Spiegazione AI
        
    Returns:
        dict: Dati analisi AI strutturati
    """
    return {
        "document_id": document.id,
        "document_title": document.title or document.original_filename,
        "ai_status": ai_status or document.ai_status or "non_analizzato",
        "ai_explain": ai_explain or document.ai_explain or "Nessuna analisi AI",
        "ai_task_id": document.ai_task_id,
        "last_updated": document.last_updated.isoformat() if document.last_updated else None,
        "company": document.company.name if document.company else None,
        "department": document.department.name if document.department else None,
        "uploaded_by": document.user.username if document.user else None,
        "upload_date": document.upload_date.isoformat() if document.upload_date else None,
        "analysis_timestamp": datetime.now().isoformat(),
        "version": "1.0"
    }

def generate_document_pdf_with_ai(document, output_path=None):
    """
    Genera PDF del documento con badge AI incorporato.
    
    Args:
        document: Oggetto Document
        output_path (str, optional): Percorso output personalizzato
        
    Returns:
        str: Percorso del PDF generato
    """
    try:
        # Percorso output
        if not output_path:
            output_path = f"/tmp/doc_{document.id}_ai_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        
        # Genera HTML del documento
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>{document.title or document.original_filename}</title>
        </head>
        <body>
            <div class="document-content">
                <h1>{document.title or document.original_filename}</h1>
                
                <div class="document-info">
                    <h2>📋 Informazioni Documento</h2>
                    <table>
                        <tr><td><strong>Azienda:</strong></td><td>{document.company.name if document.company else 'N/A'}</td></tr>
                        <tr><td><strong>Reparto:</strong></td><td>{document.department.name if document.department else 'N/A'}</td></tr>
                        <tr><td><strong>Caricato da:</strong></td><td>{document.user.username if document.user else 'N/A'}</td></tr>
                        <tr><td><strong>Data caricamento:</strong></td><td>{document.upload_date.strftime('%d/%m/%Y %H:%M') if document.upload_date else 'N/A'}</td></tr>
                        <tr><td><strong>Ultimo aggiornamento:</strong></td><td>{document.last_updated.strftime('%d/%m/%Y %H:%M') if document.last_updated else 'N/A'}</td></tr>
                    </table>
                </div>
                
                <div class="ai-analysis">
                    <h2>🤖 Analisi AI</h2>
                    <p><strong>Stato:</strong> {document.ai_status or 'Non analizzato'}</p>
                    <p><strong>Spiegazione:</strong> {document.ai_explain or 'Nessuna analisi disponibile'}</p>
                    {f'<p><strong>Task ID:</strong> {document.ai_task_id}</p>' if document.ai_task_id else ''}
                </div>
                
                <div class="document-content">
                    <h2>📄 Contenuto Documento</h2>
                    <p>Questo è il documento originale: <strong>{document.original_filename}</strong></p>
                    <p>Il documento è stato caricato nel sistema Mercury Document Intelligence e analizzato automaticamente.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Dati analisi AI
        ai_analysis = create_ai_analysis_data(document)
        
        # Genera PDF con badge AI
        success = genera_pdf_from_html(
            html_content=html_content,
            output_path=output_path,
            ai_badge=document.ai_status,
            ai_explain=document.ai_explain,
            ai_analysis=ai_analysis,
            document_title=document.title or document.original_filename
        )
        
        if success:
            print(f"✅ PDF generato con successo: {output_path}")
            return output_path
        else:
            print(f"❌ Errore nella generazione PDF")
            return None
            
    except Exception as e:
        print(f"❌ Errore nella generazione PDF documento: {e}")
        return None 