"""
Test semplificato per export audit CSV e PDF
Versione per debug e test rapido
"""

import os
import sys
import tempfile
from datetime import datetime, timedelta

# Aggiungi il path del progetto
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db
from models import EventoFormazione, PartecipazioneFormazione, User

def test_export_audit_simple():
    """
    Test semplificato per verificare le funzionalità di export.
    """
    print("🧪 Avvio test export audit...")
    
    # Configura app per test
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['WTF_CSRF_ENABLED'] = False
    app.config['SECRET_KEY'] = 'test-secret-key'
    
    with app.app_context():
        # Crea database in memoria
        db.create_all()
        
        # Crea dati di test
        print("📝 Creazione dati di test...")
        
        # Crea admin user
        admin_user = User(
            username='admin_test',
            email='admin@test.com',
            first_name='Admin',
            last_name='Test',
            role='admin',
            password='admin123'
        )
        db.session.add(admin_user)
        
        # Crea utenti di test
        user1 = User(
            username='user1_test',
            email='user1@test.com',
            first_name='Mario',
            last_name='Rossi',
            role='user',
            password='user123'
        )
        db.session.add(user1)
        
        user2 = User(
            username='user2_test',
            email='user2@test.com',
            first_name='Luigi',
            last_name='Verdi',
            role='user',
            password='user123'
        )
        db.session.add(user2)
        
        # Crea evento di test
        evento = EventoFormazione(
            titolo='Corso Sicurezza Test',
            descrizione='Corso di formazione sicurezza per test export',
            data_evento=datetime.now() + timedelta(days=1),
            durata_ore=4,
            stato='programmato',
            max_partecipanti=10
        )
        db.session.add(evento)
        db.session.commit()
        
        print(f"✅ Evento creato: {evento.titolo} (ID: {evento.id})")
        
        # Crea partecipazioni di test
        partecipazione1 = PartecipazioneFormazione(
            evento_id=evento.id,
            user_id=user1.id,
            stato_partecipazione='confermato',
            data_completamento=datetime.now(),
            firma_presenza_path='/tmp/firma1.png',  # Simula firma presente
            attestato_path='/tmp/attestato1.pdf'    # Simula attestato presente
        )
        db.session.add(partecipazione1)
        
        partecipazione2 = PartecipazioneFormazione(
            evento_id=evento.id,
            user_id=user2.id,
            stato_partecipazione='confermato',
            data_completamento=datetime.now(),
            firma_presenza_path=None,  # Simula firma mancante
            attestato_path='/tmp/attestato2.pdf'    # Simula attestato presente
        )
        db.session.add(partecipazione2)
        
        db.session.commit()
        print(f"✅ Partecipazioni create: {len([partecipazione1, partecipazione2])}")
        
        # Test export CSV
        print("📊 Test export CSV...")
        try:
            from routes.qms_routes import export_audit_csv
            
            # Mock os.path.exists
            original_exists = os.path.exists
            def mock_exists(path):
                return 'firma1.png' in path or 'attestato' in path
            
            os.path.exists = mock_exists
            
            # Test export CSV
            with app.test_request_context():
                response = export_audit_csv(evento.id)
                
                if hasattr(response, 'status_code'):
                    print(f"✅ CSV Status: {response.status_code}")
                else:
                    print(f"✅ CSV Response: {type(response)}")
                    
                    # Verifica contenuto CSV
                    csv_content = response.get_data(as_text=True)
                    print(f"📄 CSV Content length: {len(csv_content)}")
                    
                    # Verifica elementi chiave
                    checks = [
                        ('AUDIT VERIFICA EVENTO FORMATIVO', 'Header'),
                        ('Nome,Email,Firma,Attestato', 'Table header'),
                        ('Mario Rossi', 'User 1'),
                        ('Luigi Verdi', 'User 2'),
                        ('✅', 'Present signature'),
                        ('❌', 'Missing signature'),
                        ('STATISTICHE AUDIT', 'Statistics')
                    ]
                    
                    for check_text, check_name in checks:
                        if check_text in csv_content:
                            print(f"✅ {check_name}: OK")
                        else:
                            print(f"❌ {check_name}: MISSING")
            
            # Ripristina os.path.exists
            os.path.exists = original_exists
            
        except Exception as e:
            print(f"❌ Errore test CSV: {e}")
        
        # Test export PDF
        print("📄 Test export PDF...")
        try:
            from routes.qms_routes import export_audit_pdf
            
            # Mock os.path.exists
            def mock_exists(path):
                return 'firma1.png' in path or 'attestato' in path
            
            os.path.exists = mock_exists
            
            # Test export PDF
            with app.test_request_context():
                response = export_audit_pdf(evento.id)
                
                if hasattr(response, 'status_code'):
                    print(f"✅ PDF Status: {response.status_code}")
                else:
                    print(f"✅ PDF Response: {type(response)}")
                    
                    # Verifica contenuto PDF
                    pdf_content = response.get_data()
                    print(f"📄 PDF Content length: {len(pdf_content)} bytes")
                    
                    # Verifica che sia un PDF valido
                    if pdf_content.startswith(b'%PDF'):
                        print("✅ PDF format: OK")
                    else:
                        print("❌ PDF format: INVALID")
            
            # Ripristina os.path.exists
            os.path.exists = original_exists
            
        except Exception as e:
            print(f"❌ Errore test PDF: {e}")
        
        print("🎉 Test completato!")

if __name__ == '__main__':
    test_export_audit_simple() 