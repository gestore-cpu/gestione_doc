#!/usr/bin/env python3
"""
Script di test per il sistema di notifiche CEO.
"""
import os
import sys
from datetime import datetime
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app
from extensions import db
from models import NotificaCEO, LogInvioPDF, User
from services.ceo_notifications import processa_invio_pdf_per_notifiche, get_notifiche_ceo_non_lette

def test_notifiche_ceo():
    """Test del sistema di notifiche CEO."""
    with app.app_context():
        try:
            print("🧪 Test sistema notifiche CEO...")
            
            # 1. Verifica che la tabella esista
            inspector = db.inspect(db.engine)
            tables = inspector.get_table_names()
            
            if 'notifiche_ceo' not in tables:
                print("❌ Tabella 'notifiche_ceo' non trovata")
                return False
            
            print("✅ Tabella 'notifiche_ceo' trovata")
            
            # 2. Crea un log invio PDF di test
            print("\n📝 Creazione log invio PDF di test...")
            
            # Cerca un admin esistente
            admin = User.query.filter_by(role='admin').first()
            if not admin:
                print("❌ Nessun admin trovato nel database")
                return False
            
            # Crea log invio PDF di test
            log_test = LogInvioPDF(
                id_utente_o_guest=1,
                tipo='user',
                inviato_da=admin.email,
                inviato_a='test@esterno.com',  # Email esterna per trigger notifica
                oggetto_email='Test PDF - Utente',
                messaggio_email='Test messaggio',
                timestamp=datetime.utcnow(),
                esito='successo'
            )
            
            db.session.add(log_test)
            db.session.commit()
            print(f"✅ Log invio PDF creato con ID: {log_test.id}")
            
            # 3. Processa notifica
            print("\n🔔 Processamento notifica...")
            notifica = processa_invio_pdf_per_notifiche(log_test.id)
            
            if notifica:
                print(f"✅ Notifica CEO creata con ID: {notifica.id}")
                print(f"   Titolo: {notifica.titolo}")
                print(f"   Tipo: {notifica.tipo_display}")
                print(f"   Stato: {notifica.stato_display}")
            else:
                print("⚠️ Nessuna notifica generata (criteri non soddisfatti)")
            
            # 4. Verifica notifiche non lette
            print("\n📊 Verifica notifiche non lette...")
            notifiche_non_lette = get_notifiche_ceo_non_lette()
            print(f"✅ Notifiche non lette trovate: {len(notifiche_non_lette)}")
            
            # 5. Statistiche generali
            print("\n📈 Statistiche generali...")
            totale_notifiche = NotificaCEO.query.count()
            notifiche_lette = NotificaCEO.query.filter_by(stato='letto').count()
            notifiche_nuove = NotificaCEO.query.filter_by(stato='nuovo').count()
            
            print(f"   Totale notifiche: {totale_notifiche}")
            print(f"   Notifiche lette: {notifiche_lette}")
            print(f"   Notifiche nuove: {notifiche_nuove}")
            
            # 6. Test marcatura come letta
            if notifiche_non_lette:
                print("\n✅ Test marcatura come letta...")
                notifica_test = notifiche_non_lette[0]
                notifica_test.marca_letta()
                db.session.commit()
                print(f"   Notifica {notifica_test.id} marcata come letta")
            
            print("\n🎉 Test completato con successo!")
            return True
            
        except Exception as e:
            print(f"❌ Errore durante il test: {e}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == "__main__":
    test_notifiche_ceo()
