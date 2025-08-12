#!/usr/bin/env python3
"""
Test semplice per il sistema di notifiche CEO.
"""
import os
import sys
from datetime import datetime
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app
from extensions import db

def test_notifiche_ceo_simple():
    """Test semplice del sistema di notifiche CEO."""
    with app.app_context():
        try:
            print("🧪 Test semplice sistema notifiche CEO...")
            
            # 1. Verifica che la tabella esista
            inspector = db.inspect(db.engine)
            tables = inspector.get_table_names()
            
            if 'notifiche_ceo' not in tables:
                print("❌ Tabella 'notifiche_ceo' non trovata")
                return False
            
            print("✅ Tabella 'notifiche_ceo' trovata")
            
            # 2. Verifica che la tabella log_invio_pdf esista
            if 'log_invio_pdf' not in tables:
                print("❌ Tabella 'log_invio_pdf' non trovata")
                return False
            
            print("✅ Tabella 'log_invio_pdf' trovata")
            
            # 3. Conta notifiche esistenti
            from models import NotificaCEO
            totale_notifiche = NotificaCEO.query.count()
            print(f"📊 Notifiche esistenti nel database: {totale_notifiche}")
            
            # 4. Conta log invii PDF
            from models import LogInvioPDF
            totale_log = LogInvioPDF.query.count()
            print(f"📊 Log invii PDF esistenti: {totale_log}")
            
            # 5. Test creazione notifica manuale
            print("\n📝 Test creazione notifica manuale...")
            
            notifica_test = NotificaCEO(
                titolo="Test Notifica CEO",
                descrizione="Questa è una notifica di test per verificare il sistema",
                tipo="invio_pdf_sensibile",
                email_mittente="admin@test.com",
                email_destinatario="test@esterno.com",
                nome_utente_guest="Utente Test",
                stato="nuovo"
            )
            
            db.session.add(notifica_test)
            db.session.commit()
            
            print(f"✅ Notifica di test creata con ID: {notifica_test.id}")
            
            # 6. Verifica proprietà
            print(f"   Titolo: {notifica_test.titolo}")
            print(f"   Tipo: {notifica_test.tipo_display}")
            print(f"   Stato: {notifica_test.stato_display}")
            print(f"   È nuova: {notifica_test.is_nuovo}")
            
            # 7. Test marcatura come letta
            print("\n✅ Test marcatura come letta...")
            notifica_test.marca_letta()
            db.session.commit()
            
            print(f"   Stato dopo marcatura: {notifica_test.stato_display}")
            print(f"   È letta: {notifica_test.is_letta}")
            print(f"   Data lettura: {notifica_test.data_lettura_formatted}")
            
            # 8. Statistiche finali
            print("\n📈 Statistiche finali...")
            totale_finale = NotificaCEO.query.count()
            notifiche_lette = NotificaCEO.query.filter_by(stato='letto').count()
            notifiche_nuove = NotificaCEO.query.filter_by(stato='nuovo').count()
            
            print(f"   Totale notifiche: {totale_finale}")
            print(f"   Notifiche lette: {notifiche_lette}")
            print(f"   Notifiche nuove: {notifiche_nuove}")
            
            print("\n🎉 Test semplice completato con successo!")
            return True
            
        except Exception as e:
            print(f"❌ Errore durante il test: {e}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == "__main__":
    test_notifiche_ceo_simple()
