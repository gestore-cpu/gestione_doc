#!/usr/bin/env python3
"""
Test script per verificare il funzionamento del log invii PDF.
"""
import sys, os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import LogInvioPDF, User
from datetime import datetime, timedelta

def test_pdf_log():
    """Test del modello LogInvioPDF e delle sue proprietà."""
    
    with app.app_context():
        print("🧪 Test Log Invii PDF")
        print("=" * 50)
        
        # Test 1: Creazione log entry
        print("\n1. Test creazione log entry...")
        try:
            log_entry = LogInvioPDF(
                id_utente_o_guest=1,
                tipo='user',
                inviato_da='admin@mercury.com',
                inviato_a='ceo@mercury.com',
                oggetto_email='Report attività utente - Mario Rossi',
                messaggio_email='Report per audit interno',
                timestamp=datetime.utcnow(),
                esito='successo'
            )
            
            db.session.add(log_entry)
            db.session.commit()
            print("✅ Log entry creata con successo")
            
            # Test 2: Verifica proprietà
            print("\n2. Test proprietà del modello...")
            print(f"   - Tipo display: {log_entry.tipo_display}")
            print(f"   - Esito display: {log_entry.esito_display}")
            print(f"   - Badge class: {log_entry.esito_badge_class}")
            print(f"   - Timestamp formattato: {log_entry.timestamp_formatted}")
            print(f"   - Messaggio preview: {log_entry.messaggio_preview}")
            print("✅ Proprietà funzionanti")
            
            # Test 3: Query log entries
            print("\n3. Test query log entries...")
            all_logs = LogInvioPDF.query.all()
            print(f"   - Totale log entries: {len(all_logs)}")
            
            success_logs = LogInvioPDF.query.filter_by(esito='successo').count()
            error_logs = LogInvioPDF.query.filter_by(esito='errore').count()
            print(f"   - Successi: {success_logs}")
            print(f"   - Errori: {error_logs}")
            print("✅ Query funzionanti")
            
            # Test 4: Filtri
            print("\n4. Test filtri...")
            recent_logs = LogInvioPDF.query.filter(
                LogInvioPDF.timestamp >= datetime.utcnow() - timedelta(days=1)
            ).count()
            print(f"   - Log ultimi 24h: {recent_logs}")
            
            user_logs = LogInvioPDF.query.filter_by(tipo='user').count()
            guest_logs = LogInvioPDF.query.filter_by(tipo='guest').count()
            print(f"   - Log utenti: {user_logs}")
            print(f"   - Log guest: {guest_logs}")
            print("✅ Filtri funzionanti")
            
            # Test 5: Paginazione
            print("\n5. Test paginazione...")
            pagination = LogInvioPDF.query.order_by(LogInvioPDF.timestamp.desc()).paginate(
                page=1, per_page=10, error_out=False
            )
            print(f"   - Pagina 1: {len(pagination.items)} elementi")
            print(f"   - Totale pagine: {pagination.pages}")
            print(f"   - Totale elementi: {pagination.total}")
            print("✅ Paginazione funzionante")
            
            print("\n🎉 Tutti i test completati con successo!")
            
        except Exception as e:
            print(f"❌ Errore durante il test: {str(e)}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    test_pdf_log()
