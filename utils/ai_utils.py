"""
Utility per analisi AI avanzate del sistema documentale.
Gestisce analisi intelligenti su reparti, utenti, documenti e pattern di utilizzo.
"""

from datetime import datetime, timedelta
from sqlalchemy import func, and_, desc, or_
from typing import Dict, List, Any, Optional
import logging

from models import (
    Department, User, Document, DownloadLog, DocumentSignature,
    LogInvioPDF, LetturaPDF
)
from extensions import db

# Configurazione logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def analizza_attivita_ai() -> Dict[str, Any]:
    """
    Esegue tutte le analisi AI aggiuntive sul sistema documentale.
    
    Returns:
        Dict: Risultati di tutte le analisi AI
    """
    try:
        oggi = datetime.utcnow()
        trenta_giorni_fa = oggi - timedelta(days=30)
        
        risultati = {
            "timestamp": oggi.isoformat(),
            "periodo_analisi": "ultimi 30 giorni",
            "analisi": {}
        }
        
        # 1. 📌 Reparti inattivi negli ultimi 30gg
        risultati["analisi"]["reparti_inattivi"] = analizza_reparti_inattivi(trenta_giorni_fa)
        
        # 2. 🚨 File mai scaricati ma obbligatori
        risultati["analisi"]["file_obbligatori_non_scaricati"] = analizza_file_obbligatori_non_scaricati()
        
        # 3. 📤 Utenti che scaricano ma non firmano
        risultati["analisi"]["utenti_scaricano_non_firmano"] = analizza_utenti_scaricano_non_firmano(trenta_giorni_fa)
        
        # 4. 🕒 Picchi di download fuori orario
        risultati["analisi"]["download_fuori_orario"] = analizza_download_fuori_orario(trenta_giorni_fa)
        
        # 5. 🏷️ Tipologie documenti poco utilizzate
        risultati["analisi"]["tipologie_poco_utilizzate"] = analizza_tipologie_poco_utilizzate(trenta_giorni_fa)
        
        # 6. 📊 Statistiche generali
        risultati["analisi"]["statistiche_generali"] = genera_statistiche_generali(trenta_giorni_fa)
        
        # 7. 🎯 Suggerimenti AI
        risultati["analisi"]["suggerimenti_ai"] = genera_suggerimenti_ai(risultati["analisi"])
        
        return risultati
        
    except Exception as e:
        logger.error(f"Errore nell'analisi AI attività: {str(e)}")
        return {
            "error": f"Errore nell'analisi AI: {str(e)}",
            "timestamp": datetime.utcnow().isoformat()
        }


def analizza_reparti_inattivi(data_inizio: datetime) -> Dict[str, Any]:
    """
    Analizza reparti inattivi negli ultimi 30 giorni.
    
    Args:
        data_inizio: Data di inizio per l'analisi
        
    Returns:
        Dict: Risultati analisi reparti inattivi
    """
    try:
        # Trova reparti con attività recente
        reparti_attivi = db.session.query(Department.name).distinct()\
            .join(User, User.department_id == Department.id)\
            .outerjoin(DownloadLog, DownloadLog.user_id == User.id)\
            .outerjoin(DocumentSignature, DocumentSignature.signed_by == User.username)\
            .filter(
                or_(
                    DownloadLog.timestamp >= data_inizio,
                    DocumentSignature.signed_at >= data_inizio
                )
            ).all()
        
        reparti_attivi_nomi = [r[0] for r in reparti_attivi]
        
        # Tutti i reparti
        tutti_reparti = db.session.query(Department.name).all()
        tutti_reparti_nomi = [r[0] for r in tutti_reparti]
        
        # Reparti inattivi
        reparti_inattivi = [r for r in tutti_reparti_nomi if r not in reparti_attivi_nomi]
        
        return {
            "reparti_inattivi": reparti_inattivi,
            "totale_reparti": len(tutti_reparti_nomi),
            "reparti_attivi": len(reparti_attivi_nomi),
            "percentuale_inattivi": round(len(reparti_inattivi) / len(tutti_reparti_nomi) * 100, 1) if tutti_reparti_nomi else 0
        }
        
    except Exception as e:
        logger.error(f"Errore analisi reparti inattivi: {str(e)}")
        return {"error": str(e)}


def analizza_file_obbligatori_non_scaricati() -> Dict[str, Any]:
    """
    Trova documenti obbligatori mai scaricati.
    
    Returns:
        Dict: Risultati analisi file obbligatori
    """
    try:
        # Documenti obbligatori
        documenti_obbligatori = Document.query.filter(Document.obbligatorio == True).all()
        
        file_non_scaricati = []
        for doc in documenti_obbligatori:
            # Verifica se è mai stato scaricato
            download_count = DownloadLog.query.filter(DownloadLog.file_id == doc.id).count()
            if download_count == 0:
                file_non_scaricati.append({
                    "id": doc.id,
                    "nome": doc.nome,
                    "categoria": doc.categoria,
                    "data_creazione": doc.created_at.isoformat() if doc.created_at else None
                })
        
        return {
            "file_non_scaricati": file_non_scaricati,
            "totale_obbligatori": len(documenti_obbligatori),
            "non_scaricati": len(file_non_scaricati),
            "percentuale_non_scaricati": round(len(file_non_scaricati) / len(documenti_obbligatori) * 100, 1) if documenti_obbligatori else 0
        }
        
    except Exception as e:
        logger.error(f"Errore analisi file obbligatori: {str(e)}")
        return {"error": str(e)}


def analizza_utenti_scaricano_non_firmano(data_inizio: datetime) -> Dict[str, Any]:
    """
    Trova utenti che scaricano ma non firmano.
    
    Args:
        data_inizio: Data di inizio per l'analisi
        
    Returns:
        Dict: Risultati analisi utenti
    """
    try:
        # Utenti che hanno scaricato documenti
        utenti_con_download = db.session.query(User.id, User.username, User.email)\
            .join(DownloadLog, DownloadLog.user_id == User.id)\
            .filter(DownloadLog.timestamp >= data_inizio)\
            .distinct().all()
        
        utenti_problematici = []
        for utente in utenti_con_download:
            # Conta download dell'utente
            download_count = DownloadLog.query.filter(
                DownloadLog.user_id == utente.id,
                DownloadLog.timestamp >= data_inizio
            ).count()
            
            # Conta firme dell'utente
            firme_count = DocumentSignature.query.filter(
                DocumentSignature.signed_by == utente.username,
                DocumentSignature.signed_at >= data_inizio
            ).count()
            
            # Se ha scaricato ma non ha firmato
            if download_count > 0 and firme_count == 0:
                utenti_problematici.append({
                    "id": utente.id,
                    "username": utente.username,
                    "email": utente.email,
                    "download_count": download_count,
                    "firme_count": firme_count
                })
        
        return {
            "utenti_problematici": utenti_problematici,
            "totale_utenti_con_download": len(utenti_con_download),
            "utenti_senza_firme": len(utenti_problematici),
            "percentuale_problematici": round(len(utenti_problematici) / len(utenti_con_download) * 100, 1) if utenti_con_download else 0
        }
        
    except Exception as e:
        logger.error(f"Errore analisi utenti: {str(e)}")
        return {"error": str(e)}


def analizza_download_fuori_orario(data_inizio: datetime) -> Dict[str, Any]:
    """
    Analizza download fuori orario lavorativo (6:00-20:00).
    
    Args:
        data_inizio: Data di inizio per l'analisi
        
    Returns:
        Dict: Risultati analisi download fuori orario
    """
    try:
        # Download fuori orario (prima delle 6 o dopo le 20)
        download_fuori_orario = db.session.query(
            DownloadLog.id,
            DownloadLog.user_id,
            DownloadLog.file_id,
            DownloadLog.timestamp,
            User.username,
            Document.nome.label('documento_nome')
        ).join(User, DownloadLog.user_id == User.id)\
         .join(Document, DownloadLog.file_id == Document.id)\
         .filter(
            DownloadLog.timestamp >= data_inizio,
            or_(
                func.extract('hour', DownloadLog.timestamp) < 6,
                func.extract('hour', DownloadLog.timestamp) >= 20
            )
        ).all()
        
        # Raggruppa per utente
        utenti_sospetti = {}
        for download in download_fuori_orario:
            username = download.username
            if username not in utenti_sospetti:
                utenti_sospetti[username] = {
                    "username": username,
                    "download_fuori_orario": [],
                    "count": 0
                }
            
            utenti_sospetti[username]["download_fuori_orario"].append({
                "id": download.id,
                "documento": download.documento_nome,
                "timestamp": download.timestamp.isoformat(),
                "ora": download.timestamp.strftime('%H:%M')
            })
            utenti_sospetti[username]["count"] += 1
        
        return {
            "download_fuori_orario": list(utenti_sospetti.values()),
            "totale_download_sospetti": len(download_fuori_orario),
            "utenti_sospetti": len(utenti_sospetti),
            "orario_min": "06:00",
            "orario_max": "20:00"
        }
        
    except Exception as e:
        logger.error(f"Errore analisi download fuori orario: {str(e)}")
        return {"error": str(e)}


def analizza_tipologie_poco_utilizzate(data_inizio: datetime) -> Dict[str, Any]:
    """
    Analizza tipologie di documenti poco utilizzate.
    
    Args:
        data_inizio: Data di inizio per l'analisi
        
    Returns:
        Dict: Risultati analisi tipologie
    """
    try:
        # Statistiche per categoria/tipologia
        stats_categoria = db.session.query(
            Document.categoria,
            func.count(Document.id).label('totale_documenti'),
            func.count(DownloadLog.id).label('download_totali')
        ).outerjoin(DownloadLog, Document.id == DownloadLog.file_id)\
         .filter(DownloadLog.timestamp >= data_inizio)\
         .group_by(Document.categoria)\
         .all()
        
        tipologie_poco_utilizzate = []
        for categoria, totale_doc, download in stats_categoria:
            if totale_doc > 0:
                percentuale_utilizzo = (download / totale_doc) * 100
                if percentuale_utilizzo < 50:  # Meno del 50% di utilizzo
                    tipologie_poco_utilizzate.append({
                        "categoria": categoria,
                        "totale_documenti": totale_doc,
                        "download_totali": download,
                        "percentuale_utilizzo": round(percentuale_utilizzo, 1)
                    })
        
        # Ordina per percentuale di utilizzo (meno utilizzate prima)
        tipologie_poco_utilizzate.sort(key=lambda x: x["percentuale_utilizzo"])
        
        return {
            "tipologie_poco_utilizzate": tipologie_poco_utilizzate,
            "totale_categorie": len(stats_categoria),
            "categorie_problematiche": len(tipologie_poco_utilizzate),
            "soglia_utilizzo": 50  # percentuale
        }
        
    except Exception as e:
        logger.error(f"Errore analisi tipologie: {str(e)}")
        return {"error": str(e)}


def genera_statistiche_generali(data_inizio: datetime) -> Dict[str, Any]:
    """
    Genera statistiche generali del sistema.
    
    Args:
        data_inizio: Data di inizio per l'analisi
        
    Returns:
        Dict: Statistiche generali
    """
    try:
        # Statistiche base
        totale_utenti = User.query.count()
        totale_documenti = Document.query.count()
        totale_download = DownloadLog.query.filter(DownloadLog.timestamp >= data_inizio).count()
        totale_firme = DocumentSignature.query.filter(DocumentSignature.signed_at >= data_inizio).count()
        
        # Documenti obbligatori
        documenti_obbligatori = Document.query.filter(Document.obbligatorio == True).count()
        
        # Reparti
        totale_reparti = Department.query.count()
        
        return {
            "totale_utenti": totale_utenti,
            "totale_documenti": totale_documenti,
            "documenti_obbligatori": documenti_obbligatori,
            "totale_reparti": totale_reparti,
            "download_ultimi_30gg": totale_download,
            "firme_ultimi_30gg": totale_firme,
            "periodo_analisi": "ultimi 30 giorni"
        }
        
    except Exception as e:
        logger.error(f"Errore generazione statistiche: {str(e)}")
        return {"error": str(e)}


def genera_suggerimenti_ai(analisi: Dict[str, Any]) -> List[str]:
    """
    Genera suggerimenti AI basati sui risultati delle analisi.
    
    Args:
        analisi: Risultati delle analisi AI
        
    Returns:
        List: Lista di suggerimenti AI
    """
    suggerimenti = []
    
    try:
        # Suggerimenti basati su reparti inattivi
        if "reparti_inattivi" in analisi:
            reparti_data = analisi["reparti_inattivi"]
            if not isinstance(reparti_data, dict) or "error" in reparti_data:
                return ["⚠️ Errore nell'analisi dei reparti inattivi"]
            
            if reparti_data.get("percentuale_inattivi", 0) > 30:
                suggerimenti.append("🚨 Alta percentuale di reparti inattivi. Considera campagne di sensibilizzazione.")
            elif reparti_data.get("reparti_inattivi"):
                suggerimenti.append("📊 Alcuni reparti sono inattivi. Verifica la necessità di formazione.")
        
        # Suggerimenti basati su file obbligatori
        if "file_obbligatori_non_scaricati" in analisi:
            file_data = analisi["file_obbligatori_non_scaricati"]
            if not isinstance(file_data, dict) or "error" in file_data:
                return ["⚠️ Errore nell'analisi dei file obbligatori"]
            
            if file_data.get("non_scaricati", 0) > 0:
                suggerimenti.append("📋 Documenti obbligatori non scaricati. Implementa notifiche automatiche.")
        
        # Suggerimenti basati su utenti problematici
        if "utenti_scaricano_non_firmano" in analisi:
            utenti_data = analisi["utenti_scaricano_non_firmano"]
            if not isinstance(utenti_data, dict) or "error" in utenti_data:
                return ["⚠️ Errore nell'analisi degli utenti"]
            
            if utenti_data.get("utenti_senza_firme", 0) > 0:
                suggerimenti.append("👤 Utenti scaricano ma non firmano. Verifica il processo di firma.")
        
        # Suggerimenti basati su download fuori orario
        if "download_fuori_orario" in analisi:
            download_data = analisi["download_fuori_orario"]
            if not isinstance(download_data, dict) or "error" in download_data:
                return ["⚠️ Errore nell'analisi dei download fuori orario"]
            
            if download_data.get("totale_download_sospetti", 0) > 10:
                suggerimenti.append("🕒 Molti download fuori orario. Verifica attività sospette.")
        
        # Suggerimenti basati su tipologie poco utilizzate
        if "tipologie_poco_utilizzate" in analisi:
            tipologie_data = analisi["tipologie_poco_utilizzate"]
            if not isinstance(tipologie_data, dict) or "error" in tipologie_data:
                return ["⚠️ Errore nell'analisi delle tipologie"]
            
            if tipologie_data.get("categorie_problematiche", 0) > 0:
                suggerimenti.append("🏷️ Alcune categorie documenti poco utilizzate. Considera formazione specifica.")
        
        # Se non ci sono suggerimenti specifici
        if not suggerimenti:
            suggerimenti.append("✅ Sistema ben gestito. Continua così!")
        
        return suggerimenti
        
    except Exception as e:
        logger.error(f"Errore generazione suggerimenti AI: {str(e)}")
        return ["⚠️ Errore nella generazione dei suggerimenti AI"] 