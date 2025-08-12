"""
Test endpoint AI activity per DOCS Mercury.
"""

import pytest
import json
from datetime import datetime, timedelta
from flask import url_for

class TestAIActivityEndpoints:
    """Test per endpoint AI activity."""
    
    def test_users_activity_ceo_access(self, ceo_session, database):
        """Test endpoint /admin/users/activity come CEO."""
        response = ceo_session.get('/admin/users/activity')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['success'] == True
        assert 'data' in data
        assert 'total_users' in data
        assert 'anomalous_count' in data
        
        # CEO dovrebbe vedere tutti gli utenti
        assert len(data['data']) >= 4  # Tutti gli utenti nel DB
        
        # Verifica struttura dati
        for user in data['data']:
            assert 'id' in user
            assert 'nome' in user
            assert 'email' in user
            assert 'ultimo_accesso' in user
            assert 'documenti_aperti' in user
            assert 'download_totali' in user
            assert 'upload_totali' in user
            assert 'tentativi_login_falliti' in user
            assert 'orari_accesso' in user
            assert 'comportamento_anomalo' in user
            assert 'ruolo' in user
            assert 'azienda' in user
            assert 'reparto' in user
            assert 'stato' in user
    
    def test_users_activity_admin_access(self, mercury_admin_session, database):
        """Test endpoint /admin/users/activity come admin Mercury."""
        response = mercury_admin_session.get('/admin/users/activity')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['success'] == True
        
        # Admin dovrebbe vedere solo utenti Mercury
        mercury_users = [user for user in data['data'] 
                       if user['email'] in ['admin@mercury.com', 'user@mercury.com']]
        assert len(mercury_users) == 2
        
        # NON dovrebbe vedere utenti altri moduli
        other_users = [user for user in data['data'] 
                      if user['email'] in ['admin@other.com']]
        assert len(other_users) == 0
    
    def test_users_activity_user_access_denied(self, mercury_user_session, database):
        """Test che user NON può accedere all'endpoint AI."""
        response = mercury_user_session.get('/admin/users/activity')
        assert response.status_code == 403
    
    def test_guests_activity_ceo_access(self, ceo_session, database):
        """Test endpoint /admin/guests/activity come CEO."""
        response = ceo_session.get('/admin/guests/activity')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['success'] == True
        assert 'data' in data
        assert 'total_guests' in data
        assert 'anomalous_count' in data
        assert 'expired_count' in data
        
        # CEO dovrebbe vedere tutti i guest
        assert len(data['data']) >= 2  # Tutti i guest nel DB
        
        # Verifica struttura dati
        for guest in data['data']:
            assert 'id' in guest
            assert 'nome' in guest
            assert 'email' in guest
            assert 'ultimo_accesso' in guest
            assert 'documenti_aperti' in guest
            assert 'download_totali' in guest
            assert 'upload_totali' in guest
            assert 'tentativi_login_falliti' in guest
            assert 'orari_accesso' in guest
            assert 'comportamento_anomalo' in guest
            assert 'azienda' in guest
            assert 'documenti_assegnati' in guest
            assert 'scadenza_accesso' in guest
            assert 'giorni_alla_scadenza' in guest
            assert 'stato' in guest
    
    def test_guests_activity_admin_access(self, mercury_admin_session, database):
        """Test endpoint /admin/guests/activity come admin Mercury."""
        response = mercury_admin_session.get('/admin/guests/activity')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['success'] == True
        
        # Admin dovrebbe vedere solo guest Mercury
        mercury_guests = [guest for guest in data['data'] 
                         if guest['email'] in ['guest@mercury.com', 'expired@mercury.com']]
        assert len(mercury_guests) == 2
    
    def test_guests_activity_user_access_denied(self, mercury_user_session, database):
        """Test che user NON può accedere all'endpoint AI guest."""
        response = mercury_user_session.get('/admin/guests/activity')
        assert response.status_code == 403
    
    def test_users_activity_anomalous_behavior_detection(self, ceo_session, database):
        """Test rilevamento comportamenti anomali per utenti."""
        response = ceo_session.get('/admin/users/activity')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        
        # Verifica che il conteggio anomalie sia presente
        assert 'anomalous_count' in data
        assert isinstance(data['anomalous_count'], int)
        
        # Verifica che ogni utente abbia il campo comportamento_anomalo
        for user in data['data']:
            assert 'comportamento_anomalo' in user
            assert isinstance(user['comportamento_anomalo'], bool)
    
    def test_guests_activity_anomalous_behavior_detection(self, ceo_session, database):
        """Test rilevamento comportamenti anomali per guest."""
        response = ceo_session.get('/admin/guests/activity')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        
        # Verifica che il conteggio anomalie sia presente
        assert 'anomalous_count' in data
        assert isinstance(data['anomalous_count'], int)
        
        # Verifica che il conteggio scaduti sia presente
        assert 'expired_count' in data
        assert isinstance(data['expired_count'], int)
        
        # Verifica che ogni guest abbia il campo comportamento_anomalo
        for guest in data['data']:
            assert 'comportamento_anomalo' in guest
            assert isinstance(guest['comportamento_anomalo'], bool)
    
    def test_users_activity_access_hours_analysis(self, ceo_session, database):
        """Test analisi orari accesso per utenti."""
        response = ceo_session.get('/admin/users/activity')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        
        for user in data['data']:
            assert 'orari_accesso' in user
            access_hours = user['orari_accesso']
            
            # Verifica struttura orari accesso
            assert 'morning' in access_hours
            assert 'afternoon' in access_hours
            assert 'evening' in access_hours
            assert 'night' in access_hours
            
            # Verifica che i valori siano numeri
            for period in access_hours.values():
                assert isinstance(period, int)
    
    def test_guests_activity_access_hours_analysis(self, ceo_session, database):
        """Test analisi orari accesso per guest."""
        response = ceo_session.get('/admin/guests/activity')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        
        for guest in data['data']:
            assert 'orari_accesso' in guest
            access_hours = guest['orari_accesso']
            
            # Verifica struttura orari accesso
            assert 'morning' in access_hours
            assert 'afternoon' in access_hours
            assert 'evening' in access_hours
            assert 'night' in access_hours
    
    def test_users_activity_document_counting(self, ceo_session, database):
        """Test conteggio documenti aperti per utenti."""
        response = ceo_session.get('/admin/users/activity')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        
        for user in data['data']:
            assert 'documenti_aperti' in user
            assert isinstance(user['documenti_aperti'], int)
            assert user['documenti_aperti'] >= 0
    
    def test_guests_activity_document_counting(self, ceo_session, database):
        """Test conteggio documenti aperti per guest."""
        response = ceo_session.get('/admin/guests/activity')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        
        for guest in data['data']:
            assert 'documenti_aperti' in guest
            assert isinstance(guest['documenti_aperti'], int)
            assert guest['documenti_aperti'] >= 0
    
    def test_users_activity_failed_logins_tracking(self, ceo_session, database):
        """Test tracking tentativi login falliti per utenti."""
        response = ceo_session.get('/admin/users/activity')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        
        for user in data['data']:
            assert 'tentativi_login_falliti' in user
            assert isinstance(user['tentativi_login_falliti'], int)
            assert user['tentativi_login_falliti'] >= 0
    
    def test_guests_activity_failed_logins_tracking(self, ceo_session, database):
        """Test tracking tentativi login falliti per guest."""
        response = ceo_session.get('/admin/guests/activity')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        
        for guest in data['data']:
            assert 'tentativi_login_falliti' in guest
            assert isinstance(guest['tentativi_login_falliti'], int)
            assert guest['tentativi_login_falliti'] >= 0
    
    def test_users_activity_last_login_format(self, ceo_session, database):
        """Test formato ultimo accesso per utenti."""
        response = ceo_session.get('/admin/users/activity')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        
        for user in data['data']:
            assert 'ultimo_accesso' in user
            # Può essere None o stringa ISO
            if user['ultimo_accesso'] is not None:
                assert isinstance(user['ultimo_accesso'], str)
                # Verifica formato ISO
                try:
                    datetime.fromisoformat(user['ultimo_accesso'].replace('Z', '+00:00'))
                except ValueError:
                    pytest.fail(f"Formato ultimo_accesso non valido: {user['ultimo_accesso']}")
    
    def test_guests_activity_last_login_format(self, ceo_session, database):
        """Test formato ultimo accesso per guest."""
        response = ceo_session.get('/admin/guests/activity')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        
        for guest in data['data']:
            assert 'ultimo_accesso' in guest
            # Può essere None o stringa ISO
            if guest['ultimo_accesso'] is not None:
                assert isinstance(guest['ultimo_accesso'], str)
    
    def test_users_activity_status_calculation(self, ceo_session, database):
        """Test calcolo stato utenti."""
        response = ceo_session.get('/admin/users/activity')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        
        for user in data['data']:
            assert 'stato' in user
            assert user['stato'] in ['active', 'expired']
    
    def test_guests_activity_status_calculation(self, ceo_session, database):
        """Test calcolo stato guest."""
        response = ceo_session.get('/admin/guests/activity')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        
        for guest in data['data']:
            assert 'stato' in guest
            assert guest['stato'] in ['active', 'expired']
    
    def test_users_activity_error_handling(self, ceo_session, database):
        """Test gestione errori endpoint utenti."""
        # Simula errore nel database
        with pytest.raises(Exception):
            # Questo test verifica che gli errori vengano gestiti correttamente
            response = ceo_session.get('/admin/users/activity')
            if response.status_code == 500:
                data = json.loads(response.data)
                assert data['success'] == False
                assert 'error' in data
    
    def test_guests_activity_error_handling(self, ceo_session, database):
        """Test gestione errori endpoint guest."""
        # Simula errore nel database
        with pytest.raises(Exception):
            # Questo test verifica che gli errori vengano gestiti correttamente
            response = ceo_session.get('/admin/guests/activity')
            if response.status_code == 500:
                data = json.loads(response.data)
                assert data['success'] == False
                assert 'error' in data
    
    def test_ai_analysis_function_mock(self, ceo_session, database):
        """Test mock funzione analisi AI."""
        # Simula chiamata endpoint che dovrebbe triggerare analisi AI
        response = ceo_session.get('/admin/users/activity')
        assert response.status_code == 200
        
        # Verifica che i dati siano pronti per analisi AI
        data = json.loads(response.data)
        assert len(data['data']) > 0
        
        # Verifica che ogni record abbia i campi necessari per AI
        for record in data['data']:
            required_fields = [
                'id', 'nome', 'email', 'ultimo_accesso', 'documenti_aperti',
                'download_totali', 'upload_totali', 'tentativi_login_falliti',
                'orari_accesso', 'comportamento_anomalo'
            ]
            for field in required_fields:
                assert field in record 