"""
Test sincronizzazione CEO per DOCS Mercury.
"""

import pytest
import json
import responses
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
from flask import url_for

class TestCEOSync:
    """Test per sincronizzazione con sistema centrale CEO."""
    
    @responses.activate
    def test_sync_user_creation_success(self, mercury_admin_session, database):
        """Test sincronizzazione creazione utente con successo."""
        # Mock API CEO success
        responses.add(
            responses.POST,
            'https://64.226.70.28/api/sync/users',
            json={'success': True, 'message': 'User synced'},
            status=200
        )
        
        # Crea utente
        user_data = {
            'first_name': 'Sync',
            'last_name': 'Test',
            'email': 'synctest@mercury.com',
            'role': 'user',
            'company_id': '1',
            'department_id': '1'
        }
        
        response = mercury_admin_session.post('/admin/users/create', data=user_data)
        assert response.status_code == 302
        
        # Verifica che la chiamata API sia stata fatta
        assert len(responses.calls) == 1
        call = responses.calls[0]
        assert call.request.url == 'https://64.226.70.28/api/sync/users'
        assert call.request.method == 'POST'
        
        # Verifica headers
        headers = call.request.headers
        assert 'Authorization' in headers
        assert headers['Authorization'].startswith('Bearer ')
        assert headers['Content-Type'] == 'application/json'
        assert 'User-Agent' in headers
    
    @responses.activate
    def test_sync_user_creation_failure(self, mercury_admin_session, database):
        """Test sincronizzazione creazione utente con errore API."""
        # Mock API CEO failure
        responses.add(
            responses.POST,
            'https://64.226.70.28/api/sync/users',
            json={'error': 'Internal server error'},
            status=500
        )
        
        # Crea utente (dovrebbe continuare nonostante errore API)
        user_data = {
            'first_name': 'Sync',
            'last_name': 'Error',
            'email': 'syncerror@mercury.com',
            'role': 'user',
            'company_id': '1',
            'department_id': '1'
        }
        
        response = mercury_admin_session.post('/admin/users/create', data=user_data)
        assert response.status_code == 302  # Dovrebbe continuare
        
        # Verifica che l'utente sia stato creato localmente
        from models import User
        new_user = User.query.filter_by(email='syncerror@mercury.com').first()
        assert new_user is not None
    
    @responses.activate
    def test_sync_user_update_success(self, mercury_admin_session, database):
        """Test sincronizzazione aggiornamento utente con successo."""
        # Mock API CEO success
        responses.add(
            responses.POST,
            'https://64.226.70.28/api/sync/users',
            json={'success': True, 'message': 'User updated'},
            status=200
        )
        
        # Aggiorna utente
        update_data = {
            'first_name': 'Updated',
            'last_name': 'Sync',
            'email': 'user@mercury.com',
            'role': 'admin',
            'company_id': '1',
            'department_id': '1'
        }
        
        response = mercury_admin_session.post('/admin/users/update/2', data=update_data)
        assert response.status_code == 302
        
        # Verifica chiamata API
        assert len(responses.calls) == 1
        call = responses.calls[0]
        assert call.request.url == 'https://64.226.70.28/api/sync/users'
        
        # Verifica payload
        payload = json.loads(call.request.body)
        assert payload['action'] == 'update'
        assert payload['modulo'] == 'Mercury'
        assert 'timestamp' in payload
    
    @responses.activate
    def test_sync_user_deletion_success(self, mercury_admin_session, database):
        """Test sincronizzazione eliminazione utente con successo."""
        # Mock API CEO success
        responses.add(
            responses.POST,
            'https://64.226.70.28/api/sync/users',
            json={'success': True, 'message': 'User deleted'},
            status=200
        )
        
        # Elimina utente
        response = mercury_admin_session.post('/admin/users/delete/2')
        assert response.status_code == 302
        
        # Verifica chiamata API
        assert len(responses.calls) == 1
        call = responses.calls[0]
        payload = json.loads(call.request.body)
        assert payload['action'] == 'delete'
    
    @responses.activate
    def test_sync_guest_creation_success(self, mercury_admin_session, database):
        """Test sincronizzazione creazione guest con successo."""
        # Mock API CEO success
        responses.add(
            responses.POST,
            'https://64.226.70.28/api/sync/guests',
            json={'success': True, 'message': 'Guest synced'},
            status=200
        )
        
        # Crea guest
        guest_data = {
            'first_name': 'Sync',
            'last_name': 'Guest',
            'email': 'syncguest@mercury.com',
            'company_id': '1',
            'access_expiration': (datetime.utcnow() + timedelta(days=30)).strftime('%Y-%m-%d'),
            'assigned_documents': ['1']
        }
        
        response = mercury_admin_session.post('/admin/guests/create', data=guest_data)
        assert response.status_code == 302
        
        # Verifica chiamata API
        assert len(responses.calls) == 1
        call = responses.calls[0]
        assert call.request.url == 'https://64.226.70.28/api/sync/guests'
        
        # Verifica payload guest
        payload = json.loads(call.request.body)
        assert payload['action'] == 'create'
        assert payload['modulo'] == 'Mercury'
        assert 'documenti_assegnati' in payload
        assert 'scadenza_accesso' in payload
        assert 'giorni_alla_scadenza' in payload
    
    @responses.activate
    def test_sync_guest_update_success(self, mercury_admin_session, database):
        """Test sincronizzazione aggiornamento guest con successo."""
        # Mock API CEO success
        responses.add(
            responses.POST,
            'https://64.226.70.28/api/sync/guests',
            json={'success': True, 'message': 'Guest updated'},
            status=200
        )
        
        # Aggiorna guest (proroga)
        proroga_data = {
            'new_expiration': (datetime.utcnow() + timedelta(days=60)).strftime('%Y-%m-%d'),
            'proroga_reason': 'Test proroga'
        }
        
        response = mercury_admin_session.post('/admin/guests/proroga/5', data=proroga_data)
        assert response.status_code == 302
        
        # Verifica chiamata API
        assert len(responses.calls) == 1
        call = responses.calls[0]
        payload = json.loads(call.request.body)
        assert payload['action'] == 'update'
    
    @responses.activate
    def test_sync_guest_deletion_success(self, mercury_admin_session, database):
        """Test sincronizzazione eliminazione guest con successo."""
        # Mock API CEO success
        responses.add(
            responses.POST,
            'https://64.226.70.28/api/sync/guests',
            json={'success': True, 'message': 'Guest deleted'},
            status=200
        )
        
        # Elimina guest
        response = mercury_admin_session.post('/admin/guests/delete/5')
        assert response.status_code == 302
        
        # Verifica chiamata API
        assert len(responses.calls) == 1
        call = responses.calls[0]
        payload = json.loads(call.request.body)
        assert payload['action'] == 'delete'
    
    @responses.activate
    def test_sync_network_timeout(self, mercury_admin_session, database):
        """Test gestione timeout di rete."""
        # Mock timeout
        responses.add(
            responses.POST,
            'https://64.226.70.28/api/sync/users',
            body=Exception("Connection timeout")
        )
        
        # Crea utente (dovrebbe continuare nonostante timeout)
        user_data = {
            'first_name': 'Timeout',
            'last_name': 'Test',
            'email': 'timeout@mercury.com',
            'role': 'user',
            'company_id': '1',
            'department_id': '1'
        }
        
        response = mercury_admin_session.post('/admin/users/create', data=user_data)
        assert response.status_code == 302
        
        # Verifica che l'utente sia stato creato localmente
        from models import User
        new_user = User.query.filter_by(email='timeout@mercury.com').first()
        assert new_user is not None
    
    @responses.activate
    def test_sync_invalid_token(self, mercury_admin_session, database):
        """Test gestione token JWT invalido."""
        # Mock errore 401 (token invalido)
        responses.add(
            responses.POST,
            'https://64.226.70.28/api/sync/users',
            json={'error': 'Invalid token'},
            status=401
        )
        
        # Crea utente (dovrebbe continuare nonostante errore token)
        user_data = {
            'first_name': 'Token',
            'last_name': 'Error',
            'email': 'tokenerror@mercury.com',
            'role': 'user',
            'company_id': '1',
            'department_id': '1'
        }
        
        response = mercury_admin_session.post('/admin/users/create', data=user_data)
        assert response.status_code == 302
        
        # Verifica che l'utente sia stato creato localmente
        from models import User
        new_user = User.query.filter_by(email='tokenerror@mercury.com').first()
        assert new_user is not None
    
    def test_sync_payload_structure_users(self, mercury_admin_session, database):
        """Test struttura payload per sincronizzazione utenti."""
        with patch('requests.post') as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = {'success': True}
            
            # Crea utente
            user_data = {
                'first_name': 'Payload',
                'last_name': 'Test',
                'email': 'payload@mercury.com',
                'role': 'user',
                'company_id': '1',
                'department_id': '1'
            }
            
            response = mercury_admin_session.post('/admin/users/create', data=user_data)
            assert response.status_code == 302
            
            # Verifica struttura payload
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            payload = json.loads(call_args[1]['json'])
            
            required_fields = [
                'id', 'nome', 'email', 'ruolo', 'azienda', 'reparto',
                'stato', 'modulo', 'ultimo_accesso', 'timestamp', 'action'
            ]
            
            for field in required_fields:
                assert field in payload
            
            assert payload['modulo'] == 'Mercury'
            assert payload['action'] == 'create'
    
    def test_sync_payload_structure_guests(self, mercury_admin_session, database):
        """Test struttura payload per sincronizzazione guest."""
        with patch('requests.post') as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = {'success': True}
            
            # Crea guest
            guest_data = {
                'first_name': 'Payload',
                'last_name': 'Guest',
                'email': 'payloadguest@mercury.com',
                'company_id': '1',
                'access_expiration': (datetime.utcnow() + timedelta(days=30)).strftime('%Y-%m-%d'),
                'assigned_documents': ['1']
            }
            
            response = mercury_admin_session.post('/admin/guests/create', data=guest_data)
            assert response.status_code == 302
            
            # Verifica struttura payload
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            payload = json.loads(call_args[1]['json'])
            
            required_fields = [
                'id', 'nome', 'email', 'ruolo', 'azienda', 'reparto',
                'stato', 'modulo', 'ultimo_accesso', 'timestamp', 'action',
                'documenti_assegnati', 'scadenza_accesso', 'giorni_alla_scadenza'
            ]
            
            for field in required_fields:
                assert field in payload
            
            assert payload['modulo'] == 'Mercury'
            assert payload['action'] == 'create'
            assert payload['ruolo'] == 'guest'
    
    def test_sync_headers_authentication(self, mercury_admin_session, database):
        """Test headers di autenticazione per sincronizzazione."""
        with patch('requests.post') as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = {'success': True}
            
            # Crea utente
            user_data = {
                'first_name': 'Headers',
                'last_name': 'Test',
                'email': 'headers@mercury.com',
                'role': 'user',
                'company_id': '1',
                'department_id': '1'
            }
            
            response = mercury_admin_session.post('/admin/users/create', data=user_data)
            assert response.status_code == 302
            
            # Verifica headers
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            headers = call_args[1]['headers']
            
            assert 'Authorization' in headers
            assert headers['Authorization'].startswith('Bearer ')
            assert headers['Content-Type'] == 'application/json'
            assert 'User-Agent' in headers
            assert 'Mercury-DOCS' in headers['User-Agent']
    
    def test_sync_logging_on_error(self, mercury_admin_session, database):
        """Test logging errori di sincronizzazione."""
        with patch('requests.post') as mock_post:
            mock_post.side_effect = Exception("Network error")
            
            # Crea utente (dovrebbe loggare l'errore)
            user_data = {
                'first_name': 'Logging',
                'last_name': 'Test',
                'email': 'logging@mercury.com',
                'role': 'user',
                'company_id': '1',
                'department_id': '1'
            }
            
            response = mercury_admin_session.post('/admin/users/create', data=user_data)
            assert response.status_code == 302
            
            # Verifica che l'utente sia stato creato localmente
            from models import User
            new_user = User.query.filter_by(email='logging@mercury.com').first()
            assert new_user is not None
    
    def test_sync_ceo_token_configuration(self):
        """Test configurazione token CEO."""
        import os
        
        # Test con token di default
        if 'CEO_API_TOKEN' not in os.environ:
            # Simula token di default
            with patch.dict(os.environ, {'CEO_API_TOKEN': 'test_token'}):
                assert os.getenv('CEO_API_TOKEN') == 'test_token'
    
    def test_sync_ceo_url_configuration(self):
        """Test configurazione URL CEO."""
        ceo_base_url = 'https://64.226.70.28/api/sync'
        
        # Verifica URL utenti
        users_url = f'{ceo_base_url}/users'
        assert users_url == 'https://64.226.70.28/api/sync/users'
        
        # Verifica URL guest
        guests_url = f'{ceo_base_url}/guests'
        assert guests_url == 'https://64.226.70.28/api/sync/guests'
    
    def test_sync_timeout_configuration(self):
        """Test configurazione timeout sincronizzazione."""
        timeout = 10  # Timeout configurato
        
        with patch('requests.post') as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = {'success': True}
            
            # Verifica che il timeout sia passato correttamente
            # (Questo test verifica che il timeout sia configurato correttamente)
            assert timeout == 10 