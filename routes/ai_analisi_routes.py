"""
Route per l'analisi AI delle firme documentali.
Gestisce l'analisi intelligente e i grafici dinamici.
"""

from flask import Blueprint, jsonify, current_app, request, make_response
from flask_login import login_required
from sqlalchemy import func, desc
from datetime import datetime, timedelta
import logging
from typing import Dict, Any
import pdfkit

from models import DocumentSignature, User, Department, DownloadLog
from extensions import db
from decorators import admin_required

# Configurazione logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Blueprint per analisi AI
ai_analisi_bp = Blueprint('ai_analisi', __name__, url_prefix='/admin/ai')

@ai_analisi_bp.route("/analisi-firme")
@login_required
@admin_required
def analisi_ai_firme():
    """
    Analisi AI delle firme documentali con grafici dinamici.
    Fornisce insights intelligenti sui pattern di firma.
    
    Returns:
        JSON: Report, suggerimenti e dati per grafici
    """
    try:
        oggi = datetime.utcnow()
        trenta_giorni_fa = oggi - timedelta(days=30)
        
        # Statistiche generali
        totale_firme = DocumentSignature.query.count()
        firme_ai = DocumentSignature.query.filter(DocumentSignature.signed_by_ai == True).count()
        firme_manuali = totale_firme - firme_ai
        
        # Firme ultimi 30 giorni
        firme_recenti = DocumentSignature.query.filter(
            DocumentSignature.signed_at >= trenta_giorni_fa
        ).count()
        
        # Top firmatari
        top_firmatari = db.session.query(
            DocumentSignature.signed_by,
            func.count(DocumentSignature.id).label('count')
        ).group_by(DocumentSignature.signed_by)\
         .order_by(desc('count'))\
         .limit(5)\
         .all()
        
        # Pattern temporali
        firme_per_giorno = db.session.query(
            func.date(DocumentSignature.signed_at).label('data'),
            func.count(DocumentSignature.id).label('count')
        ).filter(DocumentSignature.signed_at >= trenta_giorni_fa)\
         .group_by(func.date(DocumentSignature.signed_at))\
         .order_by(func.date(DocumentSignature.signed_at))\
         .all()
        
        # Dati per grafici
        chart_donut = {
            "labels": ["Firme AI", "Firme Manuali"],
            "data": [firme_ai, firme_manuali]
        }
        
        # Se ci sono reparti, usa quelli invece
        if Department.query.count() > 0:
            firme_per_reparto = db.session.query(
                Department.name,
                func.count(DocumentSignature.id).label('count')
            ).join(User, User.department_id == Department.id)\
             .join(DocumentSignature, DocumentSignature.signed_by == User.username)\
             .group_by(Department.name)\
             .order_by(desc('count'))\
             .limit(8)\
             .all()
            
            if firme_per_reparto:
                chart_donut = {
                    "labels": [r[0] for r in firme_per_reparto],
                    "data": [r[1] for r in firme_per_reparto]
                }
        
        # Dati per bar chart (firme vs download)
        chart_bar = {
            "labels": [f[0] for f in top_firmatari[:5]],
            "firme": [f[1] for f in top_firmatari[:5]],
            "download": []
        }
        
        # Aggiungi dati download se disponibili
        for firmatario in chart_bar["labels"]:
            download_count = DownloadLog.query.join(User, User.username == firmatario)\
                .filter(DownloadLog.timestamp >= trenta_giorni_fa)\
                .count()
            chart_bar["download"].append(download_count)
        
        # Dati per heatmap (trend temporale)
        chart_heatmap = {
            "labels": [f[0].strftime('%d/%m') for f in firme_per_giorno[-14:]],  # Ultimi 14 giorni
            "data": [f[1] for f in firme_per_giorno[-14:]]
        }
        
        # Genera report
        report = f"""
ANALISI AI FIRME DOCUMENTALI
============================

📊 STATISTICHE GENERALI
- Totale firme: {totale_firme}
- Firme AI: {firme_ai} ({round(firme_ai/totale_firme*100, 1) if totale_firme > 0 else 0}%)
- Firme manuali: {firme_manuali} ({round(firme_manuali/totale_firme*100, 1) if totale_firme > 0 else 0}%)
- Firme ultimi 30 giorni: {firme_recenti}

🏆 TOP FIRMATARI
"""
        for firmatario, count in top_firmatari:
            report += f"- {firmatario}: {count} firme\n"
        
        report += f"""
📈 TREND TEMPORALE (ultimi 30 giorni)
"""
        for data, count in firme_per_giorno[-7:]:  # Ultimi 7 giorni
            report += f"- {data.strftime('%d/%m/%Y')}: {count} firme\n"
        
        # Genera suggerimenti AI
        suggerimenti = []
        
        if firme_ai == 0 and totale_firme > 0:
            suggerimenti.append("🤖 Considera l'abilitazione della firma automatica AI per documenti standard")
        
        if firme_recenti < totale_firme * 0.1:  # Meno del 10% delle firme sono recenti
            suggerimenti.append("⚠️ Bassa attività di firma recente. Verifica se ci sono documenti in attesa")
        
        if len(top_firmatari) > 0 and top_firmatari[0][1] > totale_firme * 0.5:
            suggerimenti.append("👤 Un utente ha firmato più del 50% dei documenti. Considera la distribuzione del carico")
        
        if firme_manuali > firme_ai * 2:
            suggerimenti.append("📝 Molte firme manuali. Valuta l'estensione della firma automatica AI")
        
        # Statistiche aggiuntive
        statistiche = {
            "Firme totali": totale_firme,
            "Firme AI": firme_ai,
            "Firme manuali": firme_manuali,
            "Firme recenti (30g)": firme_recenti,
            "Top firmatario": top_firmatari[0][0] if top_firmatari else "N/A",
            "Firme top firmatario": top_firmatari[0][1] if top_firmatari else 0
        }
        
        return jsonify({
            "success": True,
            "report": report,
            "suggerimenti": suggerimenti,
            "statistiche": statistiche,
            "chart_donut": chart_donut,
            "chart_bar": chart_bar,
            "chart_heatmap": chart_heatmap
        })
        
    except Exception as e:
        current_app.logger.error(f"Errore analisi AI firme: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"Errore durante l'analisi AI: {str(e)}"
        }), 500


@ai_analisi_bp.route("/report/attivita")
@login_required
@admin_required
def report_attivita_ai():
    """
    Report completo di attività AI con tutte le analisi aggiuntive.
    Include analisi su reparti, utenti, documenti e pattern di utilizzo.
    
    Returns:
        JSON: Report completo con tutte le analisi AI
    """
    try:
        from utils.ai_utils import analizza_attivita_ai
        
        # Esegui tutte le analisi AI
        risultati = analizza_attivita_ai()
        
        if "error" in risultati:
            return jsonify({
                "success": False,
                "error": risultati["error"]
            }), 500
        
        # Prepara dati per grafici
        chart_data = prepara_dati_grafici(risultati["analisi"])
        
        # Aggiungi dati per grafici ai risultati
        risultati["chart_data"] = chart_data
        
        return jsonify({
            "success": True,
            "report": risultati,
            "timestamp": risultati["timestamp"]
        })
        
    except Exception as e:
        current_app.logger.error(f"Errore report attività AI: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"Errore durante la generazione del report: {str(e)}"
        }), 500


def prepara_dati_grafici(analisi: Dict[str, Any]) -> Dict[str, Any]:
    """
    Prepara i dati per i grafici basati sui risultati delle analisi.
    
    Args:
        analisi: Risultati delle analisi AI
        
    Returns:
        Dict: Dati formattati per i grafici
    """
    chart_data = {}
    
    try:
        # Grafico donut per reparti inattivi
        if "reparti_inattivi" in analisi and "error" not in analisi["reparti_inattivi"]:
            reparti_data = analisi["reparti_inattivi"]
            chart_data["reparti_donut"] = {
                "labels": ["Reparti Attivi", "Reparti Inattivi"],
                "data": [
                    reparti_data.get("reparti_attivi", 0),
                    reparti_data.get("reparti_inattivi", [])
                ]
            }
        
        # Grafico bar per utenti problematici
        if "utenti_scaricano_non_firmano" in analisi and "error" not in analisi["utenti_scaricano_non_firmano"]:
            utenti_data = analisi["utenti_scaricano_non_firmano"]
            utenti_problematici = utenti_data.get("utenti_problematici", [])
            
            if utenti_problematici:
                chart_data["utenti_bar"] = {
                    "labels": [u["username"] for u in utenti_problematici[:10]],  # Top 10
                    "download": [u["download_count"] for u in utenti_problematici[:10]],
                    "firme": [u["firme_count"] for u in utenti_problematici[:10]]
                }
        
        # Grafico line per tipologie poco utilizzate
        if "tipologie_poco_utilizzate" in analisi and "error" not in analisi["tipologie_poco_utilizzate"]:
            tipologie_data = analisi["tipologie_poco_utilizzate"]
            tipologie = tipologie_data.get("tipologie_poco_utilizzate", [])
            
            if tipologie:
                chart_data["tipologie_line"] = {
                    "labels": [t["categoria"] for t in tipologie],
                    "data": [t["percentuale_utilizzo"] for t in tipologie]
                }
        
        # Grafico bar per download fuori orario
        if "download_fuori_orario" in analisi and "error" not in analisi["download_fuori_orario"]:
            download_data = analisi["download_fuori_orario"]
            utenti_sospetti = download_data.get("download_fuori_orario", [])
            
            if utenti_sospetti:
                chart_data["download_sospetti_bar"] = {
                    "labels": [u["username"] for u in utenti_sospetti[:10]],  # Top 10
                    "data": [u["count"] for u in utenti_sospetti[:10]]
                }
        
        return chart_data
        
    except Exception as e:
        logger.error(f"Errore preparazione dati grafici: {str(e)}")
        return {}


@ai_analisi_bp.route("/report/attivita/export/<format>")
@login_required
@admin_required
def export_report_attivita(format):
    """
    Export del report di attività AI in vari formati.
    
    Args:
        format: Formato di export (pdf, csv, json)
    
    Returns:
        File: Report in formato richiesto
    """
    try:
        from utils.ai_utils import analizza_attivita_ai
        from flask import Response
        import csv
        import io
        
        # Esegui analisi
        risultati = analizza_attivita_ai()
        
        if "error" in risultati:
            return jsonify({
                "success": False,
                "error": risultati["error"]
            }), 500
        
        if format == "json":
            return jsonify(risultati)
        
        elif format == "csv":
            # Crea CSV
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Header
            writer.writerow(["ANALISI AI - REPORT ATTIVITA"])
            writer.writerow([f"Generato il: {risultati['timestamp']}"])
            writer.writerow([])
            
            # Sezioni
            for sezione, dati in risultati["analisi"].items():
                if isinstance(dati, dict) and "error" not in dati:
                    writer.writerow([f"=== {sezione.upper().replace('_', ' ')} ==="])
                    
                    if sezione == "statistiche_generali":
                        for key, value in dati.items():
                            writer.writerow([key, value])
                    
                    elif sezione == "reparti_inattivi":
                        writer.writerow(["Reparti inattivi:", ", ".join(dati.get("reparti_inattivi", []))])
                        writer.writerow(["Percentuale inattivi:", f"{dati.get('percentuale_inattivi', 0)}%"])
                    
                    elif sezione == "file_obbligatori_non_scaricati":
                        for file in dati.get("file_non_scaricati", []):
                            writer.writerow([file["nome"], file["categoria"]])
                    
                    writer.writerow([])
            
            output.seek(0)
            return Response(
                output.getvalue(),
                mimetype="text/csv",
                headers={"Content-Disposition": f"attachment;filename=report_attivita_ai_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"}
            )
        
        elif format == "pdf":
            # Implementazione export PDF
            html = request.form.get("html")
            if not html:
                return jsonify({
                    "success": False,
                    "error": "Contenuto HTML mancante"
                }), 400

            try:
                # Configurazione pdfkit
                options = {
                    'page-size': 'A4',
                    'encoding': "UTF-8",
                    'no-outline': None,
                    'quiet': '',
                    'margin-top': '0.75in',
                    'margin-right': '0.75in',
                    'margin-bottom': '0.75in',
                    'margin-left': '0.75in'
                }

                # Genera PDF
                pdf = pdfkit.from_string(html, False, options=options)

                # Crea response
                response = make_response(pdf)
                response.headers["Content-Type"] = "application/pdf"
                response.headers["Content-Disposition"] = f"attachment; filename=report_ai_attivita_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
                return response

            except Exception as e:
                current_app.logger.error(f"Errore generazione PDF: {str(e)}")
                return jsonify({
                    "success": False,
                    "error": f"Errore durante la generazione del PDF: {str(e)}"
                }), 500
        
        else:
            return jsonify({
                "success": False,
                "error": f"Formato {format} non supportato"
            }), 400
        
    except Exception as e:
        current_app.logger.error(f"Errore export report attività: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"Errore durante l'export: {str(e)}"
        }), 500


@ai_analisi_bp.route("/report/attivita/page")
@login_required
@admin_required
def ai_report_attivita_page():
    """
    Pagina HTML per visualizzare il report AI attività.
    
    Returns:
        HTML: Pagina del report AI attività
    """
    try:
        from flask import render_template
        return render_template("admin/ai_analisi.html")
    except Exception as e:
        current_app.logger.error(f"Errore caricamento pagina report AI: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"Errore durante il caricamento della pagina: {str(e)}"
        }), 500
