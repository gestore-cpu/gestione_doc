"""
Test CRUD utenti per DOCS Mercury.
"""

import pytest
import json
from datetime import datetime, timedelta
from flask import url_for

class TestUsersCRUD:
    """Test per operazioni CRUD utenti."""
    
    def test_mercury_admin_can_access_users_page(self, mercury_admin_session):
        """Test che admin Mercury può accedere alla pagina utenti."""
        response = mercury_admin_session.get('/admin/users')
        assert response.status_code == 200
        assert b'Gestione Utenti Mercury' in response.data
    
    def test_ceo_can_access_users_page(self, ceo_session):
        """Test che CEO può accedere alla pagina utenti."""
        response = ceo_session.get('/admin/users')
        assert response.status_code == 200
        assert b'Gestione Utenti Mercury' in response.data
    
    def test_mercury_user_cannot_access_users_page(self, mercury_user_session):
        """Test che user Mercury NON può accedere alla pagina utenti."""
        response = mercury_user_session.get('/admin/users')
        assert response.status_code == 403
    
    def test_other_admin_cannot_access_users_page(self, other_admin_session):
        """Test che admin altro modulo NON può accedere alla pagina utenti."""
        response = other_admin_session.get('/admin/users')
        assert response.status_code == 403
    
    def test_mercury_admin_sees_only_mercury_users(self, mercury_admin_session, database):
        """Test che admin Mercury vede solo utenti del modulo Mercury."""
        response = mercury_admin_session.get('/admin/users')
        
        # Dovrebbe vedere solo utenti Mercury
        assert b'admin@mercury.com' in response.data
        assert b'user@mercury.com' in response.data
        
        # NON dovrebbe vedere utenti altri moduli
        assert b'admin@other.com' not in response.data
    
    def test_ceo_sees_all_users(self, ceo_session, database):
        """Test che CEO vede tutti gli utenti."""
        response = ceo_session.get('/admin/users')
        
        # Dovrebbe vedere tutti gli utenti
        assert b'admin@mercury.com' in response.data
        assert b'user@mercury.com' in response.data
        assert b'admin@other.com' in response.data
        assert b'ceo@company.com' in response.data
    
    def test_create_user_as_mercury_admin(self, mercury_admin_session, database):
        """Test creazione utente come admin Mercury."""
        user_data = {
            'first_name': 'Test',
            'last_name': 'User',
            'email': 'test@mercury.com',
            'role': 'user',
            'company_id': '1',
            'department_id': '1'
        }
        
        response = mercury_admin_session.post('/admin/users/create', data=user_data)
        assert response.status_code == 302  # Redirect dopo creazione
        
        # Verifica che l'utente sia stato creato
        from models import User
        new_user = User.query.filter_by(email='test@mercury.com').first()
        assert new_user is not None
        assert new_user.modulo == 'Mercury'
        assert new_user.role == 'user'
    
    def test_create_user_as_ceo(self, ceo_session, database):
        """Test creazione utente come CEO."""
        user_data = {
            'first_name': 'CEO',
            'last_name': 'Created',
            'email': 'ceo.created@company.com',
            'role': 'admin',
            'company_id': '1',
            'department_id': '1'
        }
        
        response = ceo_session.post('/admin/users/create', data=user_data)
        assert response.status_code == 302
        
        # Verifica che l'utente sia stato creato
        from models import User
        new_user = User.query.filter_by(email='ceo.created@company.com').first()
        assert new_user is not None
        assert new_user.role == 'admin'
    
    def test_create_user_validation_errors(self, mercury_admin_session, database):
        """Test validazione errori nella creazione utente."""
        # Test email mancante
        user_data = {
            'first_name': 'Test',
            'last_name': 'User',
            'role': 'user'
        }
        
        response = mercury_admin_session.post('/admin/users/create', data=user_data)
        assert response.status_code == 302  # Redirect con flash message
    
    def test_update_user(self, mercury_admin_session, database):
        """Test aggiornamento utente."""
        # Dati aggiornamento
        update_data = {
            'first_name': 'Updated',
            'last_name': 'User',
            'email': 'user@mercury.com',
            'role': 'admin',
            'company_id': '1',
            'department_id': '1'
        }
        
        response = mercury_admin_session.post('/admin/users/update/2', data=update_data)
        assert response.status_code == 302
        
        # Verifica aggiornamento
        from models import User
        updated_user = User.query.get(2)
        assert updated_user.first_name == 'Updated'
        assert updated_user.role == 'admin'
    
    def test_delete_user(self, mercury_admin_session, database):
        """Test eliminazione utente."""
        # Verifica che l'utente esiste prima
        from models import User
        user_to_delete = User.query.filter_by(email='user@mercury.com').first()
        assert user_to_delete is not None
        
        response = mercury_admin_session.post('/admin/users/delete/2')
        assert response.status_code == 302
        
        # Verifica che l'utente sia stato eliminato
        deleted_user = User.query.get(2)
        assert deleted_user is None
    
    def test_reset_password(self, mercury_admin_session, database):
        """Test reset password utente."""
        response = mercury_admin_session.post('/admin/users/2/reset_password')
        assert response.status_code == 302  # Redirect dopo reset
    
    def test_filter_users_by_company(self, mercury_admin_session, database):
        """Test filtro utenti per azienda."""
        response = mercury_admin_session.get('/admin/users?company=Mercury%20Tech')
        assert response.status_code == 200
        
        # Verifica che solo utenti Mercury siano visibili
        assert b'admin@mercury.com' in response.data
        assert b'user@mercury.com' in response.data
        assert b'admin@other.com' not in response.data
    
    def test_filter_users_by_role(self, mercury_admin_session, database):
        """Test filtro utenti per ruolo."""
        response = mercury_admin_session.get('/admin/users?role=admin')
        assert response.status_code == 200
        
        # Verifica che solo admin siano visibili
        assert b'admin@mercury.com' in response.data
        assert b'user@mercury.com' not in response.data
    
    def test_search_users(self, mercury_admin_session, database):
        """Test ricerca utenti."""
        response = mercury_admin_session.get('/admin/users?search=admin')
        assert response.status_code == 200
        
        # Verifica che solo utenti con "admin" siano visibili
        assert b'admin@mercury.com' in response.data
        assert b'user@mercury.com' not in response.data
    
    def test_user_status_badges(self, mercury_admin_session, database):
        """Test badge di stato utenti."""
        response = mercury_admin_session.get('/admin/users')
        assert response.status_code == 200
        
        # Verifica presenza badge
        assert b'badge bg-success' in response.data  # Attivo
        assert b'badge bg-danger' in response.data   # CEO
        assert b'badge bg-warning' in response.data  # Admin
    
    def test_user_actions_buttons(self, mercury_admin_session, database):
        """Test pulsanti azioni utenti."""
        response = mercury_admin_session.get('/admin/users')
        assert response.status_code == 200
        
        # Verifica presenza pulsanti azioni
        assert b'fas fa-edit' in response.data      # Modifica
        assert b'fas fa-key' in response.data       # Reset password
        assert b'fas fa-trash' in response.data     # Elimina
    
    def test_create_user_duplicate_email(self, mercury_admin_session, database):
        """Test creazione utente con email duplicata."""
        user_data = {
            'first_name': 'Duplicate',
            'last_name': 'User',
            'email': 'admin@mercury.com',  # Email già esistente
            'role': 'user',
            'company_id': '1',
            'department_id': '1'
        }
        
        response = mercury_admin_session.post('/admin/users/create', data=user_data)
        assert response.status_code == 302  # Redirect con flash message di errore
    
    def test_update_nonexistent_user(self, mercury_admin_session, database):
        """Test aggiornamento utente inesistente."""
        update_data = {
            'first_name': 'Nonexistent',
            'last_name': 'User',
            'email': 'nonexistent@mercury.com',
            'role': 'user',
            'company_id': '1',
            'department_id': '1'
        }
        
        response = mercury_admin_session.post('/admin/users/update/999', data=update_data)
        assert response.status_code == 404
    
    def test_delete_nonexistent_user(self, mercury_admin_session, database):
        """Test eliminazione utente inesistente."""
        response = mercury_admin_session.post('/admin/users/delete/999')
        assert response.status_code == 404
    
    def test_user_permissions_by_role(self, database):
        """Test permessi utenti per ruolo."""
        from models import User
        
        # Test admin Mercury
        admin_user = User.query.filter_by(email='admin@mercury.com').first()
        assert admin_user.role == 'admin'
        assert admin_user.modulo == 'Mercury'
        
        # Test user Mercury
        user = User.query.filter_by(email='user@mercury.com').first()
        assert user.role == 'user'
        assert user.modulo == 'Mercury'
        
        # Test CEO
        ceo = User.query.filter_by(email='ceo@company.com').first()
        assert ceo.role == 'ceo'
        assert ceo.modulo == 'All'
    
    def test_user_last_login_tracking(self, database):
        """Test tracking ultimo accesso utenti."""
        from models import User
        from datetime import datetime
        
        user = User.query.filter_by(email='user@mercury.com').first()
        assert user.last_login is not None
        
        # Simula nuovo accesso
        user.last_login = datetime.utcnow()
        from extensions import db
        db.session.commit()
        
        # Verifica aggiornamento
        updated_user = User.query.filter_by(email='user@mercury.com').first()
        assert updated_user.last_login is not None 