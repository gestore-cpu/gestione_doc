#!/usr/bin/env python3
"""
Script per aggiungere la tabella alert_report_ceo al database.
Bypassa Flask-Migrate per evitare problemi di configurazione.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
from extensions import db
from models import AlertReportCEO

def create_alert_report_ceo_table():
    """
    Crea la tabella alert_report_ceo nel database.
    """
    try:
        with app.app_context():
            print("🔧 Creazione tabella alert_report_ceo...")
            
            # Crea la tabella
            AlertReportCEO.__table__.create(db.engine, checkfirst=True)
            
            print("✅ Tabella alert_report_ceo creata con successo!")
            
            # Verifica che la tabella esista
            with db.engine.connect() as conn:
                result = conn.execute(db.text("""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name='alert_report_ceo'
                """)).fetchone()
                
                if result:
                    print("✅ Verifica: tabella alert_report_ceo presente nel database")
                    
                    # Mostra struttura tabella
                    columns = conn.execute(db.text("PRAGMA table_info(alert_report_ceo)")).fetchall()
                    print("\n📋 Struttura tabella alert_report_ceo:")
                    for col in columns:
                        print(f"  - {col[1]} ({col[2]})")
                else:
                    print("❌ Errore: tabella non trovata dopo la creazione")
                    return False
                
            return True
            
    except Exception as e:
        print(f"❌ Errore creazione tabella: {e}")
        return False

def test_alert_model():
    """
    Testa il modello AlertReportCEO.
    """
    try:
        with app.app_context():
            print("\n🧪 Test modello AlertReportCEO...")
            
            # Test creazione alert
            test_alert = AlertReportCEO(
                mese=7,
                anno=2024,
                numero_invii_critici=5,
                trigger_attivo=True,
                id_report_ceo='test_report.pdf',
                note='Test alert'
            )
            
            db.session.add(test_alert)
            db.session.commit()
            
            print("✅ Alert di test creato con successo")
            print(f"  - ID: {test_alert.id}")
            print(f"  - Periodo: {test_alert.periodo_display}")
            print(f"  - Livello: {test_alert.livello_display}")
            print(f"  - Attivo: {test_alert.is_attivo}")
            
            # Test query
            alerts = AlertReportCEO.query.all()
            print(f"  - Alert totali nel DB: {len(alerts)}")
            
            # Pulisci test
            db.session.delete(test_alert)
            db.session.commit()
            print("✅ Alert di test rimosso")
            
            return True
            
    except Exception as e:
        print(f"❌ Errore test modello: {e}")
        return False

def main():
    """
    Funzione principale.
    """
    print("🚀 Avvio script creazione tabella alert_report_ceo")
    print("=" * 50)
    
    # Crea tabella
    success = create_alert_report_ceo_table()
    
    if success:
        # Test modello
        test_success = test_alert_model()
        
        if test_success:
            print("\n🎉 SUCCESSO: Tabella alert_report_ceo creata e testata!")
            print("\n📋 Prossimi passi:")
            print("  1. Riavvia il server Flask")
            print("  2. Verifica le route /ceo/report-alert/")
            print("  3. Testa la generazione di un report con 3+ invii critici")
        else:
            print("\n⚠️ Tabella creata ma test fallito")
            return False
    else:
        print("\n❌ Errore nella creazione della tabella")
        return False
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
