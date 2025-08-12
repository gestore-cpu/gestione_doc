#!/usr/bin/env python3
"""
Test semplificato per la tabella alert_report_ceo.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
from extensions import db
from datetime import datetime

def test_alert_table_direct():
    """
    Test diretto della tabella alert_report_ceo.
    """
    try:
        with app.app_context():
            print("🧪 Test diretto tabella alert_report_ceo...")
            
            # Test inserimento diretto
            with db.engine.connect() as conn:
                # Inserisci alert di test
                result = conn.execute(db.text("""
                    INSERT INTO alert_report_ceo 
                    (mese, anno, numero_invii_critici, trigger_attivo, data_trigger, id_report_ceo, letto, note)
                    VALUES (7, 2024, 5, 1, :data_trigger, 'test_report.pdf', 0, 'Test alert')
                """), {"data_trigger": datetime.utcnow()})
                
                conn.commit()
                alert_id = result.lastrowid
                print(f"✅ Alert di test inserito con ID: {alert_id}")
                
                # Verifica inserimento
                result = conn.execute(db.text("""
                    SELECT * FROM alert_report_ceo WHERE id = :alert_id
                """), {"alert_id": alert_id}).fetchone()
                
                if result:
                    print("✅ Alert recuperato dal database:")
                    print(f"  - ID: {result[0]}")
                    print(f"  - Mese: {result[1]}")
                    print(f"  - Anno: {result[2]}")
                    print(f"  - Invii critici: {result[3]}")
                    print(f"  - Trigger attivo: {result[4]}")
                    print(f"  - Report: {result[6]}")
                    print(f"  - Letto: {result[7]}")
                    
                    # Test aggiornamento
                    conn.execute(db.text("""
                        UPDATE alert_report_ceo 
                        SET letto = 1, data_lettura = :data_lettura
                        WHERE id = :alert_id
                    """), {
                        "data_lettura": datetime.utcnow(),
                        "alert_id": alert_id
                    })
                    conn.commit()
                    print("✅ Alert aggiornato (marcato come letto)")
                    
                    # Test query
                    count = conn.execute(db.text("SELECT COUNT(*) FROM alert_report_ceo")).fetchone()[0]
                    print(f"✅ Alert totali nel database: {count}")
                    
                    # Pulisci test
                    conn.execute(db.text("DELETE FROM alert_report_ceo WHERE id = :alert_id"), {"alert_id": alert_id})
                    conn.commit()
                    print("✅ Alert di test rimosso")
                    
                    return True
                else:
                    print("❌ Alert non trovato dopo inserimento")
                    return False
                    
    except Exception as e:
        print(f"❌ Errore test diretto: {e}")
        return False

def main():
    """
    Funzione principale.
    """
    print("🚀 Test semplificato tabella alert_report_ceo")
    print("=" * 50)
    
    success = test_alert_table_direct()
    
    if success:
        print("\n🎉 SUCCESSO: Tabella alert_report_ceo funzionante!")
        print("\n📋 Prossimi passi:")
        print("  1. Riavvia il server Flask")
        print("  2. Verifica le route /ceo/report-alert/")
        print("  3. Testa la generazione di un report con 3+ invii critici")
    else:
        print("\n❌ Test fallito")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
