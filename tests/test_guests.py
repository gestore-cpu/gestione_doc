"""
Test CRUD guest per DOCS Mercury.
"""

import pytest
import json
from datetime import datetime, timedelta
from flask import url_for

class TestGuestsCRUD:
    """Test per operazioni CRUD guest."""
    
    def test_mercury_admin_can_access_guests_page(self, mercury_admin_session):
        """Test che admin Mercury può accedere alla pagina guest."""
        response = mercury_admin_session.get('/admin/guests')
        assert response.status_code == 200
        assert b'Gestione Guest Mercury' in response.data
    
    def test_ceo_can_access_guests_page(self, ceo_session):
        """Test che CEO può accedere alla pagina guest."""
        response = ceo_session.get('/admin/guests')
        assert response.status_code == 200
        assert b'Gestione Guest Mercury' in response.data
    
    def test_mercury_user_cannot_access_guests_page(self, mercury_user_session):
        """Test che user Mercury NON può accedere alla pagina guest."""
        response = mercury_user_session.get('/admin/guests')
        assert response.status_code == 403
    
    def test_mercury_admin_sees_only_mercury_guests(self, mercury_admin_session, database):
        """Test che admin Mercury vede solo guest del modulo Mercury."""
        response = mercury_admin_session.get('/admin/guests')
        
        # Dovrebbe vedere solo guest Mercury
        assert b'guest@mercury.com' in response.data
        assert b'expired@mercury.com' in response.data
    
    def test_ceo_sees_all_guests(self, ceo_session, database):
        """Test che CEO vede tutti i guest."""
        response = ceo_session.get('/admin/guests')
        
        # Dovrebbe vedere tutti i guest
        assert b'guest@mercury.com' in response.data
        assert b'expired@mercury.com' in response.data
    
    def test_create_guest_as_mercury_admin(self, mercury_admin_session, database):
        """Test creazione guest come admin Mercury."""
        guest_data = {
            'first_name': 'New',
            'last_name': 'Guest',
            'email': 'newguest@mercury.com',
            'company_id': '1',
            'access_expiration': (datetime.utcnow() + timedelta(days=30)).strftime('%Y-%m-%d'),
            'assigned_documents': ['1', '2']  # Documenti assegnati
        }
        
        response = mercury_admin_session.post('/admin/guests/create', data=guest_data)
        assert response.status_code == 302  # Redirect dopo creazione
        
        # Verifica che il guest sia stato creato
        from models import User
        new_guest = User.query.filter_by(email='newguest@mercury.com').first()
        assert new_guest is not None
        assert new_guest.modulo == 'Mercury'
        assert new_guest.role == 'guest'
        assert new_guest.access_expiration is not None
    
    def test_create_guest_validation_errors(self, mercury_admin_session, database):
        """Test validazione errori nella creazione guest."""
        # Test email mancante
        guest_data = {
            'first_name': 'Test',
            'last_name': 'Guest',
            'access_expiration': (datetime.utcnow() + timedelta(days=30)).strftime('%Y-%m-%d')
        }
        
        response = mercury_admin_session.post('/admin/guests/create', data=guest_data)
        assert response.status_code == 302  # Redirect con flash message
    
    def test_proroga_guest(self, mercury_admin_session, database):
        """Test proroga scadenza guest."""
        # Dati proroga
        proroga_data = {
            'new_expiration': (datetime.utcnow() + timedelta(days=60)).strftime('%Y-%m-%d'),
            'proroga_reason': 'Estensione necessaria per progetto'
        }
        
        response = mercury_admin_session.post('/admin/guests/proroga/5', data=proroga_data)
        assert response.status_code == 302
        
        # Verifica proroga
        from models import User
        updated_guest = User.query.get(5)  # mercury_guest
        assert updated_guest.access_expiration > datetime.utcnow()
    
    def test_revoke_guest(self, mercury_admin_session, database):
        """Test revoca accesso guest."""
        response = mercury_admin_session.post('/admin/guests/revoke/5')
        assert response.status_code == 302
        
        # Verifica revoca
        from models import User
        revoked_guest = User.query.get(5)
        assert revoked_guest.status == 'revoked' or revoked_guest.access_expiration < datetime.utcnow()
    
    def test_delete_guest(self, mercury_admin_session, database):
        """Test eliminazione guest."""
        # Verifica che il guest esiste prima
        from models import User
        guest_to_delete = User.query.filter_by(email='guest@mercury.com').first()
        assert guest_to_delete is not None
        
        response = mercury_admin_session.post('/admin/guests/delete/5')
        assert response.status_code == 302
        
        # Verifica che il guest sia stato eliminato
        deleted_guest = User.query.get(5)
        assert deleted_guest is None
    
    def test_guest_expiry_badges(self, mercury_admin_session, database):
        """Test badge scadenza guest."""
        response = mercury_admin_session.get('/admin/guests')
        assert response.status_code == 200
        
        # Verifica presenza badge scadenza
        assert b'badge bg-success' in response.data  # Attivo
        assert b'badge bg-danger' in response.data   # Scaduto
        assert b'badge bg-warning' in response.data  # In scadenza
    
    def test_guest_actions_buttons(self, mercury_admin_session, database):
        """Test pulsanti azioni guest."""
        response = mercury_admin_session.get('/admin/guests')
        assert response.status_code == 200
        
        # Verifica presenza pulsanti azioni
        assert b'fas fa-calendar-plus' in response.data  # Proroga
        assert b'fas fa-ban' in response.data            # Revoca
        assert b'fas fa-trash' in response.data          # Elimina
    
    def test_filter_guests_by_company(self, mercury_admin_session, database):
        """Test filtro guest per azienda."""
        response = mercury_admin_session.get('/admin/guests?company=Mercury%20Tech')
        assert response.status_code == 200
        
        # Verifica che solo guest Mercury siano visibili
        assert b'guest@mercury.com' in response.data
        assert b'expired@mercury.com' in response.data
    
    def test_filter_guests_by_status(self, mercury_admin_session, database):
        """Test filtro guest per stato."""
        response = mercury_admin_session.get('/admin/guests?status=active')
        assert response.status_code == 200
        
        # Verifica che solo guest attivi siano visibili
        assert b'guest@mercury.com' in response.data
        assert b'expired@mercury.com' not in response.data
    
    def test_filter_guests_by_expiry(self, mercury_admin_session, database):
        """Test filtro guest per scadenza."""
        response = mercury_admin_session.get('/admin/guests?expiry=week')
        assert response.status_code == 200
    
    def test_search_guests(self, mercury_admin_session, database):
        """Test ricerca guest."""
        response = mercury_admin_session.get('/admin/guests?search=guest')
        assert response.status_code == 200
        
        # Verifica che solo guest con "guest" siano visibili
        assert b'guest@mercury.com' in response.data
        assert b'expired@mercury.com' not in response.data
    
    def test_guest_documents_assignment(self, mercury_admin_session, database):
        """Test assegnazione documenti ai guest."""
        # Verifica che il guest ha documenti assegnati
        from models import AuthorizedAccess
        auth_access = AuthorizedAccess.query.filter_by(user_id=5).first()
        assert auth_access is not None
        assert auth_access.document_id == 1
    
    def test_guest_expiry_calculation(self, database):
        """Test calcolo scadenza guest."""
        from models import User
        from datetime import datetime
        
        # Guest attivo
        active_guest = User.query.get(5)  # mercury_guest
        days_to_expiry = (active_guest.access_expiration - datetime.utcnow()).days
        assert days_to_expiry > 0
        
        # Guest scaduto
        expired_guest = User.query.get(6)  # expired_guest
        days_to_expiry = (expired_guest.access_expiration - datetime.utcnow()).days
        assert days_to_expiry < 0
    
    def test_create_guest_duplicate_email(self, mercury_admin_session, database):
        """Test creazione guest con email duplicata."""
        guest_data = {
            'first_name': 'Duplicate',
            'last_name': 'Guest',
            'email': 'guest@mercury.com',  # Email già esistente
            'company_id': '1',
            'access_expiration': (datetime.utcnow() + timedelta(days=30)).strftime('%Y-%m-%d')
        }
        
        response = mercury_admin_session.post('/admin/guests/create', data=guest_data)
        assert response.status_code == 302  # Redirect con flash message di errore
    
    def test_proroga_nonexistent_guest(self, mercury_admin_session, database):
        """Test proroga guest inesistente."""
        proroga_data = {
            'new_expiration': (datetime.utcnow() + timedelta(days=60)).strftime('%Y-%m-%d'),
            'proroga_reason': 'Test'
        }
        
        response = mercury_admin_session.post('/admin/guests/proroga/999', data=proroga_data)
        assert response.status_code == 404
    
    def test_delete_nonexistent_guest(self, mercury_admin_session, database):
        """Test eliminazione guest inesistente."""
        response = mercury_admin_session.post('/admin/guests/delete/999')
        assert response.status_code == 404
    
    def test_guest_permissions_by_role(self, database):
        """Test permessi guest per ruolo."""
        from models import User
        
        # Test guest Mercury
        guest = User.query.filter_by(email='guest@mercury.com').first()
        assert guest.role == 'guest'
        assert guest.modulo == 'Mercury'
        assert guest.access_expiration is not None
        
        # Test guest scaduto
        expired_guest = User.query.filter_by(email='expired@mercury.com').first()
        assert expired_guest.role == 'guest'
        assert expired_guest.modulo == 'Mercury'
        assert expired_guest.access_expiration < datetime.utcnow()
    
    def test_guest_activity_tracking(self, database):
        """Test tracking attività guest."""
        from models import DocumentActivityLog
        
        # Verifica attività guest
        guest_activity = DocumentActivityLog.query.filter_by(user_id=5).first()
        assert guest_activity is not None
        assert guest_activity.document_id == 1
        assert guest_activity.action == 'download'
    
    def test_guest_welcome_email_simulation(self, mercury_admin_session, database):
        """Test simulazione email di benvenuto guest."""
        # Simula creazione guest con email
        guest_data = {
            'first_name': 'Email',
            'last_name': 'Test',
            'email': 'emailtest@mercury.com',
            'company_id': '1',
            'access_expiration': (datetime.utcnow() + timedelta(days=30)).strftime('%Y-%m-%d')
        }
        
        response = mercury_admin_session.post('/admin/guests/create', data=guest_data)
        assert response.status_code == 302
        
        # Verifica che il guest sia stato creato
        from models import User
        new_guest = User.query.filter_by(email='emailtest@mercury.com').first()
        assert new_guest is not None 