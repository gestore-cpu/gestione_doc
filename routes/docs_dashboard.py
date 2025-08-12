# 📁 Prompt 101 – Jack Dashboard AI Documentale
# File: routes/docs_dashboard.py

from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import JSONResponse
from datetime import datetime, date, timedelta
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, case
from extensions import db
from models import Document, User, Company, Department

router = APIRouter()

@router.get("/api/jack/docs/dashboard/{user_id}")
async def get_dashboard_data(
    user_id: int,
    period: str = Query("current_month", description="Periodo di analisi"),
    company: Optional[str] = Query(None, description="Filtro azienda"),
    db: Session = Depends(db)
):
    """
    Restituisce dati aggregati per la dashboard AI documentale di Jack
    
    Args:
        user_id: ID utente
        period: Periodo di analisi (current_month, last_month, current_quarter, last_quarter)
        company: Filtro azienda opzionale
        db: Sessione database
    
    Returns:
        JSONResponse: Dati dashboard aggregati
    """
    try:
        # Calcola date per il periodo
        start_date, end_date = calculate_period_dates(period)
        
        # Query dati aggregati
        dashboard_data = query_dashboard_data(db, start_date, end_date, company)
        
        # Genera suggerimento AI
        ai_suggestion = generate_ai_suggestion(dashboard_data)
        
        # Costruisci risposta
        response_data = {
            "scadenze_settimana": dashboard_data["scadenze_settimana"],
            "firme_mancanti": dashboard_data["firme_mancanti"],
            "upload_non_approvati": dashboard_data["upload_non_approvati"],
            "documenti_obsoleti": dashboard_data["documenti_obsoleti"],
            "criticita_per_reparto": dashboard_data["criticita_per_reparto"],
            "suggerimento_ai": ai_suggestion,
            "periodo_analisi": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
                "period_name": period
            },
            "timestamp_aggiornamento": datetime.now().isoformat()
        }
        
        return JSONResponse(content=response_data)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Errore dashboard: {str(e)}")

def calculate_period_dates(period: str) -> tuple[date, date]:
    """
    Calcola le date di inizio e fine per il periodo specificato
    
    Args:
        period: Periodo di analisi
    
    Returns:
        tuple: (start_date, end_date)
    """
    today = date.today()
    
    if period == "current_month":
        start_date = today.replace(day=1)
        if today.month == 12:
            end_date = today.replace(year=today.year + 1, month=1, day=1)
        else:
            end_date = today.replace(month=today.month + 1, day=1)
    
    elif period == "last_month":
        if today.month == 1:
            start_date = today.replace(year=today.year - 1, month=12, day=1)
            end_date = today.replace(day=1)
        else:
            start_date = today.replace(month=today.month - 1, day=1)
            end_date = today.replace(day=1)
    
    elif period == "current_quarter":
        quarter_start_month = ((today.month - 1) // 3) * 3 + 1
        start_date = today.replace(month=quarter_start_month, day=1)
        if quarter_start_month == 10:
            end_date = today.replace(year=today.year + 1, month=1, day=1)
        else:
            end_date = today.replace(month=quarter_start_month + 3, day=1)
    
    elif period == "last_quarter":
        quarter_start_month = ((today.month - 1) // 3) * 3 + 1
        if quarter_start_month == 1:
            start_date = today.replace(year=today.year - 1, month=10, day=1)
            end_date = today.replace(month=1, day=1)
        else:
            start_date = today.replace(month=quarter_start_month - 3, day=1)
            end_date = today.replace(month=quarter_start_month, day=1)
    
    else:
        # Default: mese corrente
        start_date = today.replace(day=1)
        if today.month == 12:
            end_date = today.replace(year=today.year + 1, month=1, day=1)
        else:
            end_date = today.replace(month=today.month + 1, day=1)
    
    return start_date, end_date

def query_dashboard_data(db: Session, start_date: date, end_date: date, company_filter: Optional[str] = None) -> Dict[str, Any]:
    """
    Query dati aggregati per la dashboard
    
    Args:
        db: Sessione database
        start_date: Data inizio periodo
        end_date: Data fine periodo
        company_filter: Filtro azienda opzionale
    
    Returns:
        dict: Dati aggregati dashboard
    """
    # Base query con filtro azienda se specificato
    base_query = db.query(Document)
    if company_filter:
        base_query = base_query.join(Company).filter(Company.name == company_filter)
    
    # Documenti in scadenza (prossimi 7 giorni)
    scadenza_settimana = base_query.filter(
        and_(
            Document.scadenza >= date.today(),
            Document.scadenza <= date.today() + timedelta(days=7),
            Document.stato_approvazione != 'approvato'
        )
    ).count()
    
    # Firme mancanti
    firme_mancanti = base_query.filter(
        and_(
            Document.stato_approvazione == 'approvato',
            Document.is_signed == False
        )
    ).count()
    
    # Upload non approvati nel periodo
    upload_non_approvati = base_query.filter(
        and_(
            Document.created_at >= start_date,
            Document.created_at < end_date,
            Document.stato_approvazione == 'in_attesa'
        )
    ).count()
    
    # Documenti obsoleti (>6 mesi senza aggiornamento)
    sei_mesi_fa = date.today() - timedelta(days=180)
    documenti_obsoleti = base_query.filter(
        and_(
            Document.updated_at < sei_mesi_fa,
            Document.stato_approvazione == 'approvato'
        )
    ).count()
    
    # Criticità per reparto
    criticita_per_reparto = query_criticita_per_reparto(db, start_date, end_date, company_filter)
    
    return {
        "scadenze_settimana": scadenza_settimana,
        "firme_mancanti": firme_mancanti,
        "upload_non_approvati": upload_non_approvati,
        "documenti_obsoleti": documenti_obsoleti,
        "criticita_per_reparto": criticita_per_reparto
    }

def query_criticita_per_reparto(db: Session, start_date: date, end_date: date, company_filter: Optional[str] = None) -> Dict[str, int]:
    """
    Query criticità aggregate per reparto
    
    Args:
        db: Sessione database
        start_date: Data inizio periodo
        end_date: Data fine periodo
        company_filter: Filtro azienda opzionale
    
    Returns:
        dict: Criticità per reparto
    """
    # Query base con join
    query = db.query(
        Department.name,
        func.count(Document.id).label('totale_documenti'),
        func.sum(case((Document.stato_approvazione == 'approvato', 1), else_=0)).label('approvati'),
        func.sum(case((Document.is_signed == True, 1), else_=0)).label('firmati'),
        func.sum(case((
            and_(
                Document.scadenza >= date.today(),
                Document.scadenza <= date.today() + timedelta(days=30)
            ), 1), else_=0)).label('in_scadenza'),
        func.sum(case((
            and_(
                Document.updated_at < date.today() - timedelta(days=180),
                Document.stato_approvazione == 'approvato'
            ), 1), else_=0)).label('obsoleti')
    ).join(Document)
    
    # Applica filtri
    if company_filter:
        query = query.join(Company).filter(Company.name == company_filter)
    
    # Raggruppa per reparto
    results = query.group_by(Department.name).all()
    
    # Calcola criticità per reparto
    criticita = {}
    for result in results:
        criticità_score = 0
        
        # Peso criticità
        if result.in_scadenza > 0:
            criticità_score += result.in_scadenza * 3  # Scadenza = alta criticità
        
        if result.obsoleti > 0:
            criticità_score += result.obsoleti * 2  # Obsoleti = media criticità
        
        # Documenti non firmati
        non_firmati = result.approvati - result.firmati
        if non_firmati > 0:
            criticità_score += non_firmati * 2
        
        # Documenti non approvati
        non_approvati = result.totale_documenti - result.approvati
        if non_approvati > 0:
            criticità_score += non_approvati
        
        if criticità_score > 0:
            criticita[result.name] = criticità_score
    
    return criticita

def generate_ai_suggestion(dashboard_data: Dict[str, Any]) -> str:
    """
    Genera suggerimento AI basato sui dati della dashboard
    
    Args:
        dashboard_data: Dati aggregati dashboard
    
    Returns:
        str: Suggerimento AI
    """
    suggestions = []
    
    # Analisi scadenze
    if dashboard_data["scadenze_settimana"] > 5:
        suggestions.append(f"⚠️ Attenzione: {dashboard_data['scadenze_settimana']} documenti scadono questa settimana")
    elif dashboard_data["scadenze_settimana"] > 0:
        suggestions.append(f"📅 {dashboard_data['scadenze_settimana']} documenti in scadenza questa settimana")
    
    # Analisi firme
    if dashboard_data["firme_mancanti"] > 10:
        suggestions.append(f"🖋️ Urgente: {dashboard_data['firme_mancanti']} documenti approvati attendono firma")
    elif dashboard_data["firme_mancanti"] > 0:
        suggestions.append(f"✍️ {dashboard_data['firme_mancanti']} documenti richiedono firma")
    
    # Analisi upload
    if dashboard_data["upload_non_approvati"] > 5:
        suggestions.append(f"📤 {dashboard_data['upload_non_approvati']} nuovi documenti in attesa di approvazione")
    
    # Analisi obsoleti
    if dashboard_data["documenti_obsoleti"] > 10:
        suggestions.append(f"🕒 Critico: {dashboard_data['documenti_obsoleti']} documenti obsoleti richiedono aggiornamento")
    elif dashboard_data["documenti_obsoleti"] > 0:
        suggestions.append(f"📋 {dashboard_data['documenti_obsoleti']} documenti obsoleti da aggiornare")
    
    # Analisi criticità per reparto
    criticita_reparti = dashboard_data["criticita_per_reparto"]
    if criticita_reparti:
        max_criticita = max(criticita_reparti.values())
        max_reparto = max(criticita_reparti, key=criticita_reparti.get)
        
        if max_criticita > 15:
            suggestions.append(f"🚨 Reparto {max_reparto}: criticità elevata ({max_criticita} punti)")
        elif max_criticita > 8:
            suggestions.append(f"⚠️ Reparto {max_reparto}: attenzione richiesta ({max_criticita} punti)")
    
    # Messaggio di default se nessun suggerimento
    if not suggestions:
        return "✅ Tutto sotto controllo! Nessuna criticità rilevata al momento."
    
    # Combina suggerimenti
    return " | ".join(suggestions[:3])  # Massimo 3 suggerimenti

# Endpoint aggiuntivo per dati dettagliati reparto
@router.get("/api/jack/docs/dashboard/{user_id}/reparto/{reparto}")
async def get_reparto_details(
    user_id: int,
    reparto: str,
    period: str = Query("current_month"),
    db: Session = Depends(db)
):
    """
    Restituisce dettagli criticità per reparto specifico
    
    Args:
        user_id: ID utente
        reparto: Nome reparto
        period: Periodo di analisi
        db: Sessione database
    
    Returns:
        JSONResponse: Dettagli reparto
    """
    try:
        start_date, end_date = calculate_period_dates(period)
        
        # Query documenti del reparto
        documents = db.query(Document).join(Department).filter(
            Department.name == reparto
        ).all()
        
        # Analizza documenti
        documenti_critici = []
        for doc in documents:
            criticità = 0
            problemi = []
            
            # Controlla scadenza
            if doc.scadenza and doc.scadenza <= date.today() + timedelta(days=30):
                criticità += 3
                problemi.append("Scadenza prossima")
            
            # Controlla obsoleto
            if doc.updated_at and doc.updated_at.date() < date.today() - timedelta(days=180):
                criticità += 2
                problemi.append("Obsoleto")
            
            # Controlla firma
            if doc.stato_approvazione == 'approvato' and not doc.is_signed:
                criticità += 2
                problemi.append("Firma mancante")
            
            if criticità > 0:
                documenti_critici.append({
                    "id": doc.id,
                    "titolo": doc.title,
                    "criticità": criticità,
                    "problemi": problemi,
                    "stato": doc.stato_approvazione,
                    "firmato": doc.is_signed,
                    "scadenza": doc.scadenza.isoformat() if doc.scadenza else None,
                    "ultimo_aggiornamento": doc.updated_at.isoformat() if doc.updated_at else None
                })
        
        # Ordina per criticità
        documenti_critici.sort(key=lambda x: x["criticità"], reverse=True)
        
        return JSONResponse(content={
            "reparto": reparto,
            "documenti_critici": documenti_critici,
            "totale_critici": len(documenti_critici),
            "periodo_analisi": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            }
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Errore dettagli reparto: {str(e)}")

# Endpoint per statistiche trend
@router.get("/api/jack/docs/dashboard/{user_id}/trend")
async def get_trend_data(
    user_id: int,
    months: int = Query(6, description="Numero mesi per trend"),
    db: Session = Depends(db)
):
    """
    Restituisce dati trend per grafici
    
    Args:
        user_id: ID utente
        months: Numero mesi per trend
        db: Sessione database
    
    Returns:
        JSONResponse: Dati trend
    """
    try:
        trend_data = []
        today = date.today()
        
        for i in range(months):
            month_date = today.replace(day=1) - timedelta(days=30*i)
            start_date = month_date.replace(day=1)
            
            if month_date.month == 1:
                end_date = month_date.replace(year=month_date.year + 1, month=2, day=1)
            else:
                end_date = month_date.replace(month=month_date.month + 1, day=1)
            
            # Query dati mese
            scaduti = db.query(Document).filter(
                and_(
                    Document.scadenza >= start_date,
                    Document.scadenza < end_date,
                    Document.stato_approvazione != 'approvato'
                )
            ).count()
            
            obsoleti = db.query(Document).filter(
                and_(
                    Document.updated_at < start_date - timedelta(days=180),
                    Document.stato_approvazione == 'approvato'
                )
            ).count()
            
            trend_data.append({
                "mese": start_date.strftime("%Y-%m"),
                "scaduti": scaduti,
                "obsoleti": obsoleti,
                "criticità_totale": scaduti * 3 + obsoleti * 2
            })
        
        # Inverti ordine (più recente prima)
        trend_data.reverse()
        
        return JSONResponse(content={
            "trend": trend_data,
            "labels": [item["mese"] for item in trend_data],
            "criticità": [item["criticità_totale"] for item in trend_data],
            "scaduti": [item["scaduti"] for item in trend_data],
            "obsoleti": [item["obsoleti"] for item in trend_data]
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Errore trend: {str(e)}") 