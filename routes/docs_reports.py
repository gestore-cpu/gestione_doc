# 📁 Prompt 100 – Jack genera report mensile AI per il CEO (PDF)
# File: routes/docs_reports.py

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import FileResponse
from datetime import datetime, date, timedelta
import pdfkit
import os
from typing import Optional
from sqlalchemy.orm import Session
from extensions import db
from models import Document, User, Company, Department
from sqlalchemy import func, and_, case

router = APIRouter()

@router.get("/api/jack/docs/report_ceo/{year}/{month}")
def genera_report_ceo_docs(year: int, month: int, db: Session = Depends(db)):
    """
    Genera report mensile AI per il CEO con statistiche documentali
    
    Args:
        year: Anno del report
        month: Mese del report (1-12)
        db: Sessione database
    
    Returns:
        FileResponse: PDF del report
    """
    try:
        # Validazione parametri
        if not (1 <= month <= 12):
            raise HTTPException(status_code=400, detail="Mese deve essere tra 1 e 12")
        
        if year < 2020 or year > 2030:
            raise HTTPException(status_code=400, detail="Anno non valido")
        
        # Calcolo date per il mese
        start_date = date(year, month, 1)
        if month == 12:
            end_date = date(year + 1, 1, 1)
        else:
            end_date = date(year, month + 1, 1)
        
        # 🔍 Query dati reali dal database
        dati = query_dati_mensili(db, start_date, end_date)
        
        # Generazione HTML del report
        mese_nome = datetime(year, month, 1).strftime("%B %Y")
        html = genera_html_report(dati, mese_nome)
        
        # Generazione PDF
        filename = f"report_ceo_docs_{year}_{month:02d}.pdf"
        output_path = f"/tmp/{filename}"
        
        # Configurazione pdfkit
        options = {
            'page-size': 'A4',
            'margin-top': '0.75in',
            'margin-right': '0.75in',
            'margin-bottom': '0.75in',
            'margin-left': '0.75in',
            'encoding': "UTF-8",
            'no-outline': None
        }
        
        pdfkit.from_string(html, output_path, options=options)
        
        return FileResponse(
            output_path, 
            media_type='application/pdf', 
            filename=filename
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Errore generazione report: {str(e)}")

def query_dati_mensili(db: Session, start_date: date, end_date: date) -> dict:
    """
    Query dati mensili dal database
    
    Args:
        db: Sessione database
        start_date: Data inizio mese
        end_date: Data fine mese
    
    Returns:
        dict: Dati aggregati per il report
    """
    # Documenti scaduti nel mese
    documenti_scaduti = db.query(Document).filter(
        and_(
            Document.scadenza >= start_date,
            Document.scadenza < end_date,
            Document.stato_approvazione != 'approvato'
        )
    ).count()
    
    # Revisioni mancate (documenti non aggiornati da >6 mesi)
    sei_mesi_fa = date.today().replace(day=1) - timedelta(days=180)
    revisioni_mancate = db.query(Document).filter(
        and_(
            Document.updated_at < sei_mesi_fa,
            Document.stato_approvazione == 'approvato'
        )
    ).count()
    
    # Upload senza approvazione
    upload_senza_approvazione = db.query(Document).filter(
        and_(
            Document.created_at >= start_date,
            Document.created_at < end_date,
            Document.stato_approvazione == 'in_attesa'
        )
    ).count()
    
    # Firme mancanti
    firme_mancanti = db.query(Document).filter(
        and_(
            Document.stato_approvazione == 'approvato',
            Document.is_signed == False
        )
    ).count()
    
    # Statistiche per azienda
    stats_per_azienda = db.query(
        Company.name,
        func.count(Document.id).label('totale_documenti'),
        func.sum(case((Document.stato_approvazione == 'approvato', 1), else_=0)).label('approvati'),
        func.sum(case((Document.is_signed == True, 1), else_=0)).label('firmati')
    ).join(Document).group_by(Company.name).all()
    
    # Top documenti più scaricati
    top_downloads = db.query(
        Document.title,
        Document.download_count
    ).filter(Document.download_count > 0).order_by(
        Document.download_count.desc()
    ).limit(5).all()
    
    return {
        "documenti_scaduti": documenti_scaduti,
        "revisioni_mancate": revisioni_mancate,
        "upload_senza_approvazione": upload_senza_approvazione,
        "firme_mancanti": firme_mancanti,
        "stats_per_azienda": stats_per_azienda,
        "top_downloads": top_downloads,
        "periodo": {
            "start": start_date,
            "end": end_date
        }
    }

def genera_html_report(dati: dict, mese_nome: str) -> str:
    """
    Genera HTML del report mensile
    
    Args:
        dati: Dati aggregati per il report
        mese_nome: Nome del mese per il titolo
    
    Returns:
        str: HTML del report
    """
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Report Mensile Jack - {mese_nome}</title>
        <style>
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                margin: 0;
                padding: 20px;
                background-color: #f8f9fa;
            }}
            .container {{
                max-width: 800px;
                margin: 0 auto;
                background: white;
                padding: 30px;
                border-radius: 10px;
                box-shadow: 0 0 20px rgba(0,0,0,0.1);
            }}
            .header {{
                text-align: center;
                border-bottom: 3px solid #007bff;
                padding-bottom: 20px;
                margin-bottom: 30px;
            }}
            .header h1 {{
                color: #007bff;
                margin: 0;
                font-size: 28px;
            }}
            .stats-grid {{
                display: grid;
                grid-template-columns: repeat(2, 1fr);
                gap: 20px;
                margin-bottom: 30px;
            }}
            .stat-card {{
                background: #f8f9fa;
                padding: 20px;
                border-radius: 8px;
                border-left: 4px solid #007bff;
            }}
            .stat-number {{
                font-size: 24px;
                font-weight: bold;
                color: #007bff;
            }}
            .stat-label {{
                color: #6c757d;
                font-size: 14px;
                margin-top: 5px;
            }}
            .section {{
                margin-bottom: 30px;
            }}
            .section h2 {{
                color: #495057;
                border-bottom: 2px solid #e9ecef;
                padding-bottom: 10px;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin-top: 15px;
            }}
            th, td {{
                padding: 12px;
                text-align: left;
                border-bottom: 1px solid #dee2e6;
            }}
            th {{
                background-color: #f8f9fa;
                font-weight: bold;
            }}
            .footer {{
                margin-top: 40px;
                padding-top: 20px;
                border-top: 1px solid #dee2e6;
                text-align: center;
                color: #6c757d;
                font-size: 14px;
            }}
            .ai-badge {{
                background: linear-gradient(45deg, #007bff, #6610f2);
                color: white;
                padding: 5px 15px;
                border-radius: 20px;
                font-size: 12px;
                display: inline-block;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>📊 Report Mensile Jack – {mese_nome}</h1>
                <p>Analisi documentale intelligente generata automaticamente</p>
            </div>
            
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-number">{dati['documenti_scaduti']}</div>
                    <div class="stat-label">Documenti Scaduti</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{dati['revisioni_mancate']}</div>
                    <div class="stat-label">Revisioni Mancate</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{dati['upload_senza_approvazione']}</div>
                    <div class="stat-label">Upload in Attesa</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{dati['firme_mancanti']}</div>
                    <div class="stat-label">Firme Mancanti</div>
                </div>
            </div>
            
            <div class="section">
                <h2>📈 Statistiche per Azienda</h2>
                <table>
                    <thead>
                        <tr>
                            <th>Azienda</th>
                            <th>Totale Documenti</th>
                            <th>Approvati</th>
                            <th>Firmati</th>
                        </tr>
                    </thead>
                    <tbody>
    """
    
    for azienda in dati['stats_per_azienda']:
        html += f"""
                        <tr>
                            <td>{azienda.name}</td>
                            <td>{azienda.totale_documenti}</td>
                            <td>{azienda.approvati}</td>
                            <td>{azienda.firmati}</td>
                        </tr>
        """
    
    html += """
                    </tbody>
                </table>
            </div>
            
            <div class="section">
                <h2>🔥 Top Documenti Più Scaricati</h2>
                <table>
                    <thead>
                        <tr>
                            <th>Documento</th>
                            <th>Download</th>
                        </tr>
                    </thead>
                    <tbody>
    """
    
    for doc in dati['top_downloads']:
        html += f"""
                        <tr>
                            <td>{doc.title}</td>
                            <td>{doc.download_count}</td>
                        </tr>
        """
    
    html += f"""
                    </tbody>
                </table>
            </div>
            
            <div class="footer">
                <p>🤖 Questo report è stato generato automaticamente da <span class="ai-badge">Jack Synthia AI</span></p>
                <p>Periodo analizzato: {dati['periodo']['start'].strftime('%d/%m/%Y')} - {dati['periodo']['end'].strftime('%d/%m/%Y')}</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    return html

# Endpoint aggiuntivo per report personalizzati
@router.get("/api/jack/docs/report_custom")
def genera_report_personalizzato(
    start_date: str,
    end_date: str,
    company_id: Optional[int] = None,
    db: Session = Depends(db)
):
    """
    Genera report personalizzato per periodo specifico
    
    Args:
        start_date: Data inizio (YYYY-MM-DD)
        end_date: Data fine (YYYY-MM-DD)
        company_id: ID azienda (opzionale)
        db: Sessione database
    
    Returns:
        FileResponse: PDF del report personalizzato
    """
    try:
        start = datetime.strptime(start_date, "%Y-%m-%d").date()
        end = datetime.strptime(end_date, "%Y-%m-%d").date()
        
        # Query con filtro azienda se specificato
        if company_id:
            dati = query_dati_personalizzati(db, start, end, company_id)
        else:
            dati = query_dati_mensili(db, start, end)
        
        html = genera_html_report(dati, f"Periodo {start_date} - {end_date}")
        
        filename = f"report_custom_{start_date}_{end_date}.pdf"
        output_path = f"/tmp/{filename}"
        
        options = {
            'page-size': 'A4',
            'margin-top': '0.75in',
            'margin-right': '0.75in',
            'margin-bottom': '0.75in',
            'margin-left': '0.75in',
            'encoding': "UTF-8",
            'no-outline': None
        }
        
        pdfkit.from_string(html, output_path, options=options)
        
        return FileResponse(
            output_path, 
            media_type='application/pdf', 
            filename=filename
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Errore generazione report: {str(e)}")

def query_dati_personalizzati(db: Session, start_date: date, end_date: date, company_id: int) -> dict:
    """
    Query dati personalizzati per azienda specifica
    
    Args:
        db: Sessione database
        start_date: Data inizio
        end_date: Data fine
        company_id: ID azienda
    
    Returns:
        dict: Dati aggregati per il report
    """
    # Filtra per azienda
    base_query = db.query(Document).filter(Document.company_id == company_id)
    
    # Documenti scaduti nel periodo
    documenti_scaduti = base_query.filter(
        and_(
            Document.scadenza >= start_date,
            Document.scadenza < end_date,
            Document.stato_approvazione != 'approvato'
        )
    ).count()
    
    # Revisioni mancate (documenti non aggiornati da >6 mesi)
    sei_mesi_fa = date.today().replace(day=1) - timedelta(days=180)
    revisioni_mancate = base_query.filter(
        and_(
            Document.updated_at < sei_mesi_fa,
            Document.stato_approvazione == 'approvato'
        )
    ).count()
    
    # Upload senza approvazione nel periodo
    upload_senza_approvazione = base_query.filter(
        and_(
            Document.created_at >= start_date,
            Document.created_at < end_date,
            Document.stato_approvazione == 'in_attesa'
        )
    ).count()
    
    # Firme mancanti
    firme_mancanti = base_query.filter(
        and_(
            Document.stato_approvazione == 'approvato',
            Document.is_signed == False
        )
    ).count()
    
    # Statistiche per reparto (solo per questa azienda)
    stats_per_reparto = db.query(
        Department.name,
        func.count(Document.id).label('totale_documenti'),
        func.sum(case((Document.stato_approvazione == 'approvato', 1), else_=0)).label('approvati'),
        func.sum(case((Document.is_signed == True, 1), else_=0)).label('firmati')
    ).join(Document).filter(
        Document.company_id == company_id
    ).group_by(Department.name).all()
    
    # Top documenti più scaricati per questa azienda
    top_downloads = base_query.filter(
        Document.download_count > 0
    ).order_by(
        Document.download_count.desc()
    ).limit(5).all()
    
    return {
        "documenti_scaduti": documenti_scaduti,
        "revisioni_mancate": revisioni_mancate,
        "upload_senza_approvazione": upload_senza_approvazione,
        "firme_mancanti": firme_mancanti,
        "stats_per_azienda": stats_per_reparto,  # In questo caso sono per reparto
        "top_downloads": top_downloads,
        "periodo": {
            "start": start_date,
            "end": end_date
        }
    } 