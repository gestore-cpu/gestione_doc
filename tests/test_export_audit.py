"""
Test automatico per le funzionalità di export audit CSV e PDF
Modulo: QMS.023.3 - STEP 2

Questo test verifica:
- Export CSV audit con statistiche
- Export PDF con logo e firma
- Formato corretto dei file
- Gestione errori
- Integrazione con modelli QMS
"""

import os
import tempfile
import pytest
import csv
import io
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

# Import Flask e modelli
from app import app, db
from models import EventoFormazione, PartecipazioneFormazione, User, AuditVerificaLog
from flask import url_for
from flask_login import login_user

# Configurazione test
@pytest.fixture
def client():
    """
    Fixture per creare un client di test con database temporaneo.
    
    Returns:
        Flask test client con database di test
    """
    # Crea database temporaneo
    db_fd, db_path = tempfile.mkstemp()
    
    # Configura app per test
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + db_path
    app.config['WTF_CSRF_ENABLED'] = False  # Disabilita CSRF per test
    app.config['SECRET_KEY'] = 'test-secret-key'
    
    client = app.test_client()
    
    with app.app_context():
        # Crea tabelle
        db.create_all()
        
        # Crea dati di test
        setup_test_data()
        
        yield client
        
        # Cleanup
        db.session.remove()
        db.drop_all()
    
    # Rimuovi file temporaneo
    os.close(db_fd)
    os.unlink(db_path)

def setup_test_data():
    """
    Crea dati di test per i test di export audit.
    """
    # Crea utenti di test
    admin_user = User(
        username='admin_test',
        email='admin@test.com',
        first_name='Admin',
        last_name='Test',
        role='admin',
        is_active=True
    )
    db.session.add(admin_user)
    
    user1 = User(
        username='user1_test',
        email='user1@test.com',
        first_name='Mario',
        last_name='Rossi',
        role='user',
        is_active=True
    )
    db.session.add(user1)
    
    user2 = User(
        username='user2_test',
        email='user2@test.com',
        first_name='Luigi',
        last_name='Verdi',
        role='user',
        is_active=True
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

@pytest.fixture
def auth_client(client):
    """
    Fixture per client autenticato come admin.
    
    Args:
        client: Flask test client
        
    Returns:
        Flask test client autenticato
    """
    with app.app_context():
        # Login come admin
        admin_user = User.query.filter_by(username='admin_test').first()
        with client.session_transaction() as sess:
            sess['user_id'] = admin_user.id
            sess['_fresh'] = True
    
    return client

# Test per export CSV
def test_export_csv_success(auth_client):
    """
    Test export CSV con successo.
    
    Args:
        auth_client: Client autenticato
    """
    with app.app_context():
        evento = EventoFormazione.query.first()
        
        # Mock os.path.exists per simulare file esistenti
        with patch('os.path.exists') as mock_exists:
            mock_exists.side_effect = lambda path: 'firma1.png' in path or 'attestato' in path
            
            response = auth_client.get(f'/qms/eventi/{evento.id}/verifica_audit/export_csv')
            
            # Verifica response
            assert response.status_code == 200
            assert response.headers['Content-Type'] == 'text/csv'
            assert 'attachment' in response.headers['Content-Disposition']
            
            # Verifica contenuto CSV
            csv_content = response.get_data(as_text=True)
            assert 'Nome,Email,Firma,Attestato' in csv_content
            assert 'Mario Rossi' in csv_content
            assert 'Luigi Verdi' in csv_content
            assert '✅' in csv_content  # Firma presente
            assert '❌' in csv_content  # Firma mancante
            assert 'STATISTICHE AUDIT' in csv_content

def test_export_csv_no_auth(client):
    """
    Test export CSV senza autenticazione.
    
    Args:
        client: Client non autenticato
    """
    with app.app_context():
        evento = EventoFormazione.query.first()
        response = client.get(f'/qms/eventi/{evento.id}/verifica_audit/export_csv')
        
        # Dovrebbe reindirizzare al login
        assert response.status_code in [302, 401]

def test_export_csv_invalid_evento(auth_client):
    """
    Test export CSV con evento inesistente.
    
    Args:
        auth_client: Client autenticato
    """
    response = auth_client.get('/qms/eventi/99999/verifica_audit/export_csv')
    
    # Dovrebbe restituire 404
    assert response.status_code == 404

# Test per export PDF
def test_export_pdf_success(auth_client):
    """
    Test export PDF con successo.
    
    Args:
        auth_client: Client autenticato
    """
    with app.app_context():
        evento = EventoFormazione.query.first()
        
        # Mock os.path.exists per simulare file esistenti
        with patch('os.path.exists') as mock_exists:
            mock_exists.side_effect = lambda path: 'firma1.png' in path or 'attestato' in path
            
            response = auth_client.get(f'/qms/eventi/{evento.id}/verifica_audit/export_pdf')
            
            # Verifica response
            assert response.status_code == 200
            assert response.headers['Content-Type'] == 'application/pdf'
            assert 'attachment' in response.headers['Content-Disposition']
            
            # Verifica dimensione PDF (almeno 1KB)
            pdf_content = response.data
            assert len(pdf_content) > 1000

def test_export_pdf_no_auth(client):
    """
    Test export PDF senza autenticazione.
    
    Args:
        client: Client non autenticato
    """
    with app.app_context():
        evento = EventoFormazione.query.first()
        response = client.get(f'/qms/eventi/{evento.id}/verifica_audit/export_pdf')
        
        # Dovrebbe reindirizzare al login
        assert response.status_code in [302, 401]

def test_export_pdf_invalid_evento(auth_client):
    """
    Test export PDF con evento inesistente.
    
    Args:
        auth_client: Client autenticato
    """
    response = auth_client.get('/qms/eventi/99999/verifica_audit/export_pdf')
    
    # Dovrebbe restituire 404
    assert response.status_code == 404

# Test per formato CSV
def test_csv_format_correct(auth_client):
    """
    Test formato CSV corretto con dati specifici.
    
    Args:
        auth_client: Client autenticato
    """
    with app.app_context():
        evento = EventoFormazione.query.first()
        
        with patch('os.path.exists') as mock_exists:
            mock_exists.side_effect = lambda path: 'firma1.png' in path or 'attestato' in path
            
            response = auth_client.get(f'/qms/eventi/{evento.id}/verifica_audit/export_csv')
            
            # Parsing CSV
            csv_content = response.get_data(as_text=True)
            csv_reader = csv.reader(io.StringIO(csv_content))
            rows = list(csv_reader)
            
            # Verifica header
            assert rows[0] == ['AUDIT VERIFICA EVENTO FORMATIVO']
            assert rows[2] == ['Evento:', 'Corso Sicurezza Test']
            
            # Trova riga con dati partecipante
            data_row = None
            for row in rows:
                if 'Mario Rossi' in row:
                    data_row = row
                    break
            
            assert data_row is not None
            assert 'mario@test.com' in data_row
            assert '✅' in data_row  # Firma presente
            assert '✅' in data_row  # Attestato presente

# Test per statistiche
def test_csv_statistics_correct(auth_client):
    """
    Test statistiche CSV corrette.
    
    Args:
        auth_client: Client autenticato
    """
    with app.app_context():
        evento = EventoFormazione.query.first()
        
        with patch('os.path.exists') as mock_exists:
            mock_exists.side_effect = lambda path: 'firma1.png' in path or 'attestato' in path
            
            response = auth_client.get(f'/qms/eventi/{evento.id}/verifica_audit/export_csv')
            csv_content = response.get_data(as_text=True)
            
            # Verifica statistiche
            assert 'STATISTICHE AUDIT' in csv_content
            assert 'Totale Partecipanti: 2' in csv_content
            assert 'Problemi Rilevati: 1' in csv_content  # Luigi Verdi senza firma
            assert 'Firme Mancanti: 1' in csv_content
            assert 'Attestati Mancanti: 0' in csv_content

# Test per gestione errori
def test_export_with_database_error(auth_client):
    """
    Test gestione errori database.
    
    Args:
        auth_client: Client autenticato
    """
    with app.app_context():
        # Simula errore database
        with patch('models.EventoFormazione.query') as mock_query:
            mock_query.get_or_404.side_effect = Exception("Database error")
            
            response = auth_client.get('/qms/eventi/1/verifica_audit/export_csv')
            
            # Dovrebbe restituire errore 500
            assert response.status_code == 500

# Test per integrazione modelli
def test_integration_with_models():
    """
    Test integrazione con modelli QMS.
    """
    with app.app_context():
        # Verifica modelli esistono
        evento = EventoFormazione.query.first()
        assert evento is not None
        assert evento.titolo == 'Corso Sicurezza Test'
        
        # Verifica partecipazioni
        partecipazioni = PartecipazioneFormazione.query.filter_by(evento_id=evento.id).all()
        assert len(partecipazioni) == 2
        
        # Verifica utenti
        users = User.query.all()
        assert len(users) >= 2

# Test per performance
def test_export_performance(auth_client):
    """
    Test performance export (tempo di risposta).
    
    Args:
        auth_client: Client autenticato
    """
    import time
    
    with app.app_context():
        evento = EventoFormazione.query.first()
        
        with patch('os.path.exists') as mock_exists:
            mock_exists.side_effect = lambda path: 'firma1.png' in path or 'attestato' in path
            
            # Test CSV
            start_time = time.time()
            response_csv = auth_client.get(f'/qms/eventi/{evento.id}/verifica_audit/export_csv')
            csv_time = time.time() - start_time
            
            # Test PDF
            start_time = time.time()
            response_pdf = auth_client.get(f'/qms/eventi/{evento.id}/verifica_audit/export_pdf')
            pdf_time = time.time() - start_time
            
            # Verifica tempi ragionevoli (< 5 secondi)
            assert csv_time < 5.0
            assert pdf_time < 5.0
            assert response_csv.status_code == 200
            assert response_pdf.status_code == 200

# Test per filename
def test_filename_format(auth_client):
    """
    Test formato filename corretto.
    
    Args:
        auth_client: Client autenticato
    """
    with app.app_context():
        evento = EventoFormazione.query.first()
        
        with patch('os.path.exists') as mock_exists:
            mock_exists.side_effect = lambda path: 'firma1.png' in path or 'attestato' in path
            
            # Test CSV filename
            response_csv = auth_client.get(f'/qms/eventi/{evento.id}/verifica_audit/export_csv')
            content_disposition_csv = response_csv.headers['Content-Disposition']
            assert f'audit_evento_{evento.id}' in content_disposition_csv
            assert '.csv' in content_disposition_csv
            
            # Test PDF filename
            response_pdf = auth_client.get(f'/qms/eventi/{evento.id}/verifica_audit/export_pdf')
            content_disposition_pdf = response_pdf.headers['Content-Disposition']
            assert f'audit_evento_{evento.id}' in content_disposition_pdf
            assert '.pdf' in content_disposition_pdf

if __name__ == '__main__':
    # Esegui test se chiamato direttamente
    pytest.main([__file__, '-v']) 