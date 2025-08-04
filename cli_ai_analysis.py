#!/usr/bin/env python3
"""
Comando CLI per l'analisi AI dei documenti.

Uso:
    python cli_ai_analysis.py --analyze-all    # Analizza tutti i documenti
    python cli_ai_analysis.py --clean-insights # Pulisce insight obsoleti
    python cli_ai_analysis.py --export-csv     # Esporta insight in CSV
    python cli_ai_analysis.py --help           # Mostra aiuto
"""

import os
import sys
import argparse
from datetime import datetime

# Aggiungi il percorso del progetto
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def setup_flask_app():
    """Configura l'applicazione Flask per l'uso CLI."""
    from app import app
    from extensions import db
    
    with app.app_context():
        return app, db

def analyze_all_documents():
    """Analizza tutti i documenti nel sistema."""
    print("🤖 Avvio analisi AI di tutti i documenti...")
    
    try:
        app, db = setup_flask_app()
        
        from ai.document_ai_scheduler import esegui_analisi_completa
        
        # Esegui l'analisi
        esegui_analisi_completa()
        
        print("✅ Analisi completata con successo!")
        return True
        
    except Exception as e:
        print(f"❌ Errore durante l'analisi: {e}")
        return False

def clean_old_insights():
    """Pulisce gli insight AI obsoleti."""
    print("🧹 Pulizia insight AI obsoleti...")
    
    try:
        app, db = setup_flask_app()
        
        from models import DocumentoAIInsight
        from datetime import timedelta
        
        # Rimuovi insight risolti più vecchi di 30 giorni
        data_limite = datetime.utcnow() - timedelta(days=30)
        insight_obsoleti = DocumentoAIInsight.query.filter(
            DocumentoAIInsight.status.in_(['risolto', 'ignorato']),
            DocumentoAIInsight.timestamp < data_limite
        ).all()
        
        count = len(insight_obsoleti)
        for insight in insight_obsoleti:
            db.session.delete(insight)
        
        db.session.commit()
        print(f"✅ Rimossi {count} insight obsoleti")
        return True
        
    except Exception as e:
        print(f"❌ Errore durante la pulizia: {e}")
        return False

def export_insights_csv():
    """Esporta gli insight AI in formato CSV."""
    print("📊 Esportazione insight AI in CSV...")
    
    try:
        app, db = setup_flask_app()
        
        from models import DocumentoAIInsight
        import csv
        
        insights = DocumentoAIInsight.query.order_by(DocumentoAIInsight.timestamp.desc()).all()
        
        filename = f"ai_insights_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
        
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(["ID", "Documento", "Tipo", "Dettagli", "Severità", "Stato", "Data Analisi"])
            
            for insight in insights:
                writer.writerow([
                    insight.id,
                    insight.document.title if insight.document else "N/A",
                    insight.tipo,
                    insight.valore or "",
                    insight.severity,
                    insight.status,
                    insight.timestamp.strftime("%Y-%m-%d %H:%M") if insight.timestamp else "N/A"
                ])
        
        print(f"✅ Esportazione completata: {filename}")
        print(f"📈 Esportati {len(insights)} insight")
        return True
        
    except Exception as e:
        print(f"❌ Errore durante l'esportazione: {e}")
        return False

def show_insights_summary():
    """Mostra un riepilogo degli insight AI."""
    print("📋 Riepilogo Insight AI...")
    
    try:
        app, db = setup_flask_app()
        
        from models import DocumentoAIInsight
        
        # Conta per tipo
        totali = db.session.query(
            DocumentoAIInsight.tipo,
            db.func.count(DocumentoAIInsight.id)
        ).group_by(DocumentoAIInsight.tipo).all()
        
        # Conta per stato
        stati = db.session.query(
            DocumentoAIInsight.status,
            db.func.count(DocumentoAIInsight.id)
        ).group_by(DocumentoAIInsight.status).all()
        
        # Conta per severità
        severita = db.session.query(
            DocumentoAIInsight.severity,
            db.func.count(DocumentoAIInsight.id)
        ).group_by(DocumentoAIInsight.severity).all()
        
        print("\n📊 Statistiche Insight AI:")
        print("-" * 40)
        
        print("\n📈 Per Tipo:")
        for tipo, count in totali:
            print(f"  {tipo}: {count}")
        
        print("\n📈 Per Stato:")
        for stato, count in stati:
            print(f"  {stato}: {count}")
        
        print("\n📈 Per Severità:")
        for sev, count in severita:
            print(f"  {sev}: {count}")
        
        return True
        
    except Exception as e:
        print(f"❌ Errore durante il riepilogo: {e}")
        return False

def main():
    """Funzione principale del CLI."""
    parser = argparse.ArgumentParser(
        description="CLI per l'analisi AI dei documenti",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Esempi:
  python cli_ai_analysis.py --analyze-all     # Analizza tutti i documenti
  python cli_ai_analysis.py --clean-insights  # Pulisce insight obsoleti
  python cli_ai_analysis.py --export-csv      # Esporta in CSV
  python cli_ai_analysis.py --summary         # Mostra riepilogo
        """
    )
    
    parser.add_argument(
        '--analyze-all',
        action='store_true',
        help='Analizza tutti i documenti nel sistema'
    )
    
    parser.add_argument(
        '--clean-insights',
        action='store_true',
        help='Pulisce gli insight AI obsoleti'
    )
    
    parser.add_argument(
        '--export-csv',
        action='store_true',
        help='Esporta gli insight AI in formato CSV'
    )
    
    parser.add_argument(
        '--summary',
        action='store_true',
        help='Mostra un riepilogo degli insight AI'
    )
    
    args = parser.parse_args()
    
    if not any([args.analyze_all, args.clean_insights, args.export_csv, args.summary]):
        parser.print_help()
        return
    
    print("🤖 CLI Analisi AI Documenti")
    print("=" * 40)
    
    success = True
    
    if args.analyze_all:
        success &= analyze_all_documents()
    
    if args.clean_insights:
        success &= clean_old_insights()
    
    if args.export_csv:
        success &= export_insights_csv()
    
    if args.summary:
        success &= show_insights_summary()
    
    print("\n" + "=" * 40)
    if success:
        print("✅ Tutte le operazioni completate con successo!")
        sys.exit(0)
    else:
        print("❌ Alcune operazioni sono fallite.")
        sys.exit(1)

if __name__ == "__main__":
    main() 