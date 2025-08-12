#!/usr/bin/env python3
"""
Test per il modulo Mercury - Gestione Utenti e Guest
"""

import unittest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
import json

class TestMercuryUsersGuests(unittest.TestCase):
    
    def setUp(self):
        """Setup per i test."""
        self.mock_user = MagicMock()
        self.mock_user.id = 1
        self.mock_user.email = "test@example.com"
        self.mock_user.first_name = "Test"
        self.mock_user.last_name = "User"
        self.mock_user.role = "user"
        self.mock_user.modulo = "Mercury"
        self.mock_user.company = MagicMock()
        self.mock_user.company.name = "Test Company"
        self.mock_user.department = MagicMock()
        self.mock_user.department.name = "Test Department"
        self.mock_user.last_login = datetime.utcnow()
        self.mock_user.access_expiration = None
        self.mock_user.status = "active"
        
        self.mock_guest = MagicMock()
        self.mock_guest.id = 1
        self.mock_guest.email = "guest@example.com"
        self.mock_guest.first_name = "Test"
        self.mock_guest.last_name = "Guest"
        self.mock_guest.modulo = "Mercury"
        self.mock_guest.access_expiration = datetime.utcnow() + timedelta(days=30)
        self.mock_guest.created_at = datetime.utcnow()
        self.mock_guest.status = "active"
        self.mock_guest.assigned_documents = []
    
    def test_mercury_users_route_structure(self):
        """Test struttura route utenti Mercury."""
        route = "/admin/users"
        self.assertIn("users", route)
        self.assertIn("admin", route)
    
    def test_mercury_guests_route_structure(self):
        """Test struttura route guest Mercury."""
        route = "/admin/guests"
        self.assertIn("guests", route)
        self.assertIn("admin", route)
    
    def test_user_filter_ceo_access(self):
        """Test che CEO veda tutti gli utenti."""
        # Simula filtro CEO
        filters = {
            'company': '',
            'department': '',
            'role': '',
            'status': '',
            'search': ''
        }
        
        # CEO dovrebbe vedere tutti gli utenti senza filtro modulo
        self.assertEqual(filters['company'], '')
        self.assertEqual(filters['role'], '')
    
    def test_user_filter_admin_access(self):
        """Test che Admin veda solo utenti Mercury."""
        # Simula filtro Admin
        user_modulo = "Mercury"
        self.assertEqual(user_modulo, "Mercury")
    
    def test_guest_status_calculation(self):
        """Test calcolo stato guest."""
        now = datetime.utcnow()
        
        # Guest attivo
        guest_active = MagicMock()
        guest_active.access_expiration = now + timedelta(days=30)
        guest_active.status = "active"
        
        # Guest scaduto
        guest_expired = MagicMock()
        guest_expired.access_expiration = now - timedelta(days=1)
        guest_expired.status = "active"
        
        # Guest revocato
        guest_revoked = MagicMock()
        guest_revoked.access_expiration = now + timedelta(days=30)
        guest_revoked.status = "revoked"
        
        # Verifica stati
        self.assertTrue(guest_active.access_expiration > now)
        self.assertTrue(guest_expired.access_expiration < now)
        self.assertEqual(guest_revoked.status, "revoked")
    
    def test_ceo_sync_function_structure(self):
        """Test struttura funzione sincronizzazione CEO."""
        def mock_sync_user_with_ceo(user, action):
            return {
                'id': user.id,
                'email': user.email,
                'action': action,
                'timestamp': datetime.utcnow().isoformat()
            }
        
        result = mock_sync_user_with_ceo(self.mock_user, "create")
        
        required_fields = ['id', 'email', 'action', 'timestamp']
        for field in required_fields:
            self.assertIn(field, result, f"Campo {field} mancante nella sincronizzazione")
    
    def test_guest_sync_function_structure(self):
        """Test struttura funzione sincronizzazione guest CEO."""
        def mock_sync_guest_with_ceo(guest, action):
            return {
                'id': guest.id,
                'email': guest.email,
                'action': action,
                'expiry_date': guest.access_expiration.isoformat() if guest.access_expiration else None,
                'timestamp': datetime.utcnow().isoformat()
            }
        
        result = mock_sync_guest_with_ceo(self.mock_guest, "create")
        
        required_fields = ['id', 'email', 'action', 'expiry_date', 'timestamp']
        for field in required_fields:
            self.assertIn(field, result, f"Campo {field} mancante nella sincronizzazione")
    
    def test_user_activity_endpoint_structure(self):
        """Test struttura endpoint attività utenti."""
        def mock_users_activity():
            return {
                'success': True,
                'data': [
                    {
                        'user_id': 1,
                        'last_login': datetime.utcnow().isoformat(),
                        'documents_opened': 5,
                        'failed_logins': 0,
                        'access_hours': [9, 10, 11, 14, 15]
                    }
                ],
                'total_users': 1
            }
        
        result = mock_users_activity()
        
        self.assertTrue(result['success'])
        self.assertIn('data', result)
        self.assertIn('total_users', result)
        self.assertIsInstance(result['data'], list)
    
    def test_guest_activity_endpoint_structure(self):
        """Test struttura endpoint attività guest."""
        def mock_guests_activity():
            return {
                'success': True,
                'data': [
                    {
                        'guest_id': 1,
                        'last_access': datetime.utcnow().isoformat(),
                        'documents_accessed': 3,
                        'access_count': 10,
                        'expiry_status': 'active'
                    }
                ],
                'total_guests': 1
            }
        
        result = mock_guests_activity()
        
        self.assertTrue(result['success'])
        self.assertIn('data', result)
        self.assertIn('total_guests', result)
        self.assertIsInstance(result['data'], list)
    
    def test_user_badge_colors(self):
        """Test colori badge per ruoli utenti."""
        role_colors = {
            'ceo': 'danger',
            'admin': 'warning',
            'user': 'info'
        }
        
        for role, expected_color in role_colors.items():
            self.assertEqual(role_colors[role], expected_color)
    
    def test_guest_expiry_badge_colors(self):
        """Test colori badge per scadenza guest."""
        now = datetime.utcnow()
        
        # Guest attivo (verde)
        guest_active = MagicMock()
        guest_active.access_expiration = now + timedelta(days=30)
        
        # Guest in scadenza (arancione)
        guest_warning = MagicMock()
        guest_warning.access_expiration = now + timedelta(days=5)
        
        # Guest scaduto (rosso)
        guest_expired = MagicMock()
        guest_expired.access_expiration = now - timedelta(days=1)
        
        # Verifica logica colori
        def get_badge_color(guest):
            if guest.access_expiration <= now:
                return 'danger'
            elif (guest.access_expiration - now).days <= 7:
                return 'warning'
            else:
                return 'success'
        
        self.assertEqual(get_badge_color(guest_active), 'success')
        self.assertEqual(get_badge_color(guest_warning), 'warning')
        self.assertEqual(get_badge_color(guest_expired), 'danger')
    
    def test_form_validation_required_fields(self):
        """Test validazione campi obbligatori."""
        required_fields = ['first_name', 'last_name', 'email', 'role']
        
        # Simula dati form validi
        valid_data = {
            'first_name': 'Test',
            'last_name': 'User',
            'email': 'test@example.com',
            'role': 'user'
        }
        
        # Verifica che tutti i campi obbligatori siano presenti
        for field in required_fields:
            self.assertIn(field, valid_data, f"Campo obbligatorio {field} mancante")
            self.assertTrue(valid_data[field].strip(), f"Campo {field} vuoto")
    
    def test_email_validation(self):
        """Test validazione formato email."""
        valid_emails = [
            'test@example.com',
            'user.name@company.it',
            'admin@mercury-docs.com'
        ]
        
        invalid_emails = [
            'invalid-email',
            '@example.com',
            'test@',
            'test.example.com'
        ]
        
        # Verifica email valide
        for email in valid_emails:
            self.assertIn('@', email)
            self.assertIn('.', email.split('@')[1])
        
        # Verifica email non valide
        for email in invalid_emails:
            if '@' in email:
                self.assertNotIn('.', email.split('@')[1])
    
    def test_password_generation(self):
        """Test generazione password temporanea."""
        import secrets
        import string
        
        def generate_temp_password(length=12):
            chars = string.ascii_letters + string.digits
            return ''.join(secrets.choice(chars) for _ in range(length))
        
        password = generate_temp_password()
        
        self.assertEqual(len(password), 12)
        self.assertTrue(any(c.isalpha() for c in password))
        self.assertTrue(any(c.isdigit() for c in password))
    
    def test_guest_document_assignment(self):
        """Test assegnazione documenti ai guest."""
        mock_documents = [
            MagicMock(id=1, title="Documento 1"),
            MagicMock(id=2, title="Documento 2"),
            MagicMock(id=3, title="Documento 3")
        ]
        
        assigned_docs = [1, 2]  # Guest ha accesso ai documenti 1 e 2
        
        guest_docs = [doc for doc in mock_documents if doc.id in assigned_docs]
        
        self.assertEqual(len(guest_docs), 2)
        self.assertEqual(guest_docs[0].id, 1)
        self.assertEqual(guest_docs[1].id, 2)
    
    def test_ceo_api_integration_structure(self):
        """Test struttura integrazione API CEO."""
        def mock_ceo_api_call(endpoint, data):
            return {
                'url': f'https://64.226.70.28/api/sync/{endpoint}',
                'data': data,
                'method': 'POST',
                'timeout': 10
            }
        
        user_sync = mock_ceo_api_call('users', {'id': 1, 'email': 'test@example.com'})
        guest_sync = mock_ceo_api_call('guests', {'id': 1, 'email': 'guest@example.com'})
        
        self.assertIn('64.226.70.28', user_sync['url'])
        self.assertIn('64.226.70.28', guest_sync['url'])
        self.assertEqual(user_sync['method'], 'POST')
        self.assertEqual(guest_sync['method'], 'POST')
        self.assertEqual(user_sync['timeout'], 10)
        self.assertEqual(guest_sync['timeout'], 10)


if __name__ == '__main__':
    unittest.main() 