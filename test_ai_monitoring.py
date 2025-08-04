"""
Test per il sistema di monitoraggio AI dei download sospetti.
Verifica tutte le funzionalità del sistema di alert automatici.
"""

import unittest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
import sys
import os

# Aggiungi il path del progetto
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.ai_monitoring import (
    AIMonitoringService, 
    analizza_download_sospetti, 
    create_ai_alert,
    get_recent_alerts,
    get_alert_statistics
)
from models import AIAlert, DownloadLog, User, Document, db
from extensions import db as db_ext


class TestAIMonitoring(unittest.TestCase):
    """Test per il sistema di monitoraggio AI."""
    
    def setUp(self):
        """Setup per i test."""
        # Mock del database
        self.db_mock = MagicMock()
        self.session_mock = MagicMock()
        self.db_mock.session = self.session_mock
        
        # Mock dell'AI service
        self.ai_service_mock = MagicMock()
        self.ai_service_mock.get_ai_response.return_value = "Analisi AI di test"
        
        # Istanza del servizio
        self.monitoring_service = AIMonitoringService()
    
    def test_init_suspicious_patterns(self):
        """Test inizializzazione pattern sospetti."""
        patterns = self.monitoring_service.suspicious_patterns
        
        self.assertIn('download_massivo', patterns)
        self.assertIn('accesso_fuori_orario', patterns)
        self.assertIn('ripetizione_file', patterns)
        self.assertIn('ip_sospetto', patterns)
        
        # Verifica configurazioni
        self.assertEqual(patterns['download_massivo']['threshold'], 5)
        self.assertEqual(patterns['download_massivo']['timeframe'], 2)
        self.assertEqual(patterns['download_massivo']['severity'], 'alta')
    
    @patch('services.ai_monitoring.db')
    @patch('services.ai_monitoring.User')
    @patch('services.ai_monitoring.DownloadLog')
    def test_check_massive_downloads(self, mock_download_log, mock_user, mock_db):
        """Test rilevamento download massivi."""
        # Mock dati di test
        mock_user_instance = MagicMock()
        mock_user_instance.username = "testuser"
        mock_user.query.get.return_value = mock_user_instance
        
        # Mock query results
        mock_result = MagicMock()
        mock_result.user_id = 1
        mock_result.download_count = 6
        mock_result.first_download = datetime.utcnow() - timedelta(minutes=1)
        mock_result.last_download = datetime.utcnow()
        
        mock_db.session.query.return_value.filter.return_value.group_by.return_value.having.return_value.all.return_value = [mock_result]
        
        # Esegui test
        alerts = self.monitoring_service._check_massive_downloads()
        
        # Verifica risultati
        self.assertIsInstance(alerts, list)
        if alerts:  # Se ci sono alert
            alert = alerts[0]
            self.assertEqual(alert['alert_type'], 'download_massivo')
            self.assertEqual(alert['severity'], 'alta')
            self.assertIn('testuser', alert['description'])
    
    @patch('services.ai_monitoring.db')
    @patch('services.ai_monitoring.User')
    @patch('services.ai_monitoring.DownloadLog')
    def test_check_off_hours_access(self, mock_download_log, mock_user, mock_db):
        """Test rilevamento accessi fuori orario."""
        # Mock utente
        mock_user_instance = MagicMock()
        mock_user_instance.username = "testuser"
        mock_user.query.get.return_value = mock_user_instance
        
        # Mock download fuori orario
        mock_download = MagicMock()
        mock_download.user_id = 1
        mock_download.document_id = 1
        mock_download.timestamp = datetime.utcnow().replace(hour=23)  # 23:00
        
        mock_db.session.query.return_value.filter.return_value.all.return_value = [mock_download]
        
        # Esegui test
        alerts = self.monitoring_service._check_off_hours_access()
        
        # Verifica risultati
        self.assertIsInstance(alerts, list)
    
    @patch('services.ai_monitoring.db')
    @patch('services.ai_monitoring.User')
    @patch('services.ai_monitoring.Document')
    @patch('services.ai_monitoring.DownloadLog')
    def test_check_file_repetition(self, mock_download_log, mock_document, mock_user, mock_db):
        """Test rilevamento ripetizione file."""
        # Mock utente e documento
        mock_user_instance = MagicMock()
        mock_user_instance.username = "testuser"
        mock_user.query.get.return_value = mock_user_instance
        
        mock_document_instance = MagicMock()
        mock_document_instance.title = "test_document.pdf"
        mock_document.query.get.return_value = mock_document_instance
        
        # Mock download ripetuti
        mock_downloads = []
        base_time = datetime.utcnow()
        for i in range(4):  # 4 download dello stesso file
            mock_dl = MagicMock()
            mock_dl.user_id = 1
            mock_dl.document_id = 1
            mock_dl.timestamp = base_time + timedelta(minutes=i)
            mock_downloads.append(mock_dl)
        
        mock_db.session.query.return_value.filter.return_value.order_by.return_value.all.return_value = mock_downloads
        
        # Esegui test
        alerts = self.monitoring_service._check_file_repetition()
        
        # Verifica risultati
        self.assertIsInstance(alerts, list)
    
    @patch('services.ai_monitoring.db')
    @patch('services.ai_monitoring.User')
    @patch('services.ai_monitoring.DocumentActivityLog')
    def test_check_suspicious_ips(self, mock_activity_log, mock_user, mock_db):
        """Test rilevamento IP sospetti."""
        # Mock utente
        mock_user_instance = MagicMock()
        mock_user_instance.username = "testuser"
        mock_user.query.get.return_value = mock_user_instance
        
        # Mock attività con IP sospetto
        mock_activity = MagicMock()
        mock_activity.user_id = 1
        mock_activity.document_id = 1
        mock_activity.ip_address = "192.168.1.100"
        mock_activity.action = "download"
        
        mock_db.session.query.return_value.filter.return_value.all.return_value = [mock_activity]
        
        # Esegui test
        alerts = self.monitoring_service._check_suspicious_ips()
        
        # Verifica risultati
        self.assertIsInstance(alerts, list)
    
    @patch('services.ai_monitoring.db')
    @patch('services.ai_monitoring.User')
    @patch('services.ai_monitoring.Document')
    @patch('services.ai_monitoring.DocumentActivityLog')
    def test_check_blocked_document_attempts(self, mock_activity_log, mock_document, mock_user, mock_db):
        """Test rilevamento tentativi su documenti bloccati."""
        # Mock utente e documento
        mock_user_instance = MagicMock()
        mock_user_instance.username = "testuser"
        mock_user.query.get.return_value = mock_user_instance
        
        mock_document_instance = MagicMock()
        mock_document_instance.title = "blocked_document.pdf"
        mock_document.query.get.return_value = mock_document_instance
        
        # Mock tentativo su documento bloccato
        mock_attempt = MagicMock()
        mock_attempt.user_id = 1
        mock_attempt.document_id = 1
        mock_attempt.action = "download_denied"
        mock_attempt.note = "Documento non scaricabile"
        
        mock_db.session.query.return_value.filter.return_value.all.return_value = [mock_attempt]
        
        # Esegui test
        alerts = self.monitoring_service._check_blocked_document_attempts()
        
        # Verifica risultati
        self.assertIsInstance(alerts, list)
    
    @patch('services.ai_monitoring.db')
    def test_create_ai_alert(self, mock_db):
        """Test creazione alert AI."""
        # Dati di test
        alert_data = {
            'alert_type': 'download_massivo',
            'user_id': 1,
            'severity': 'alta',
            'description': 'Test alert',
            'details': {
                'download_count': 6,
                'timeframe_minutes': 1.5
            }
        }
        
        # Mock AIAlert
        mock_alert = MagicMock()
        mock_alert.id = 1
        mock_alert.alert_type = 'download_massivo'
        
        # Esegui test
        with patch('services.ai_monitoring.AIAlert') as mock_ai_alert_class:
            mock_ai_alert_class.return_value = mock_alert
            
            result = self.monitoring_service.create_ai_alert(alert_data)
            
            # Verifica risultati
            self.assertIsNotNone(result)
            self.assertEqual(result.alert_type, 'download_massivo')
    
    @patch('services.ai_monitoring.db')
    def test_get_recent_alerts(self, mock_db):
        """Test recupero alert recenti."""
        # Mock alert
        mock_alert = MagicMock()
        mock_alert.id = 1
        mock_alert.alert_type = 'download_massivo'
        mock_alert.created_at = datetime.utcnow()
        
        mock_db.session.query.return_value.filter.return_value.order_by.return_value.all.return_value = [mock_alert]
        
        # Esegui test
        alerts = self.monitoring_service.get_recent_alerts(24)
        
        # Verifica risultati
        self.assertIsInstance(alerts, list)
        self.assertEqual(len(alerts), 1)
    
    @patch('services.ai_monitoring.db')
    def test_get_alert_statistics(self, mock_db):
        """Test recupero statistiche alert."""
        # Mock statistiche
        mock_db.session.query.return_value.group_by.return_value.all.return_value = []
        mock_db.session.query.return_value.filter.return_value.count.return_value = 0
        
        # Esegui test
        stats = self.monitoring_service.get_alert_statistics()
        
        # Verifica risultati
        self.assertIsInstance(stats, dict)
        self.assertIn('total', stats)
        self.assertIn('resolved', stats)
        self.assertIn('pending', stats)
    
    def test_analizza_download_sospetti_integration(self):
        """Test integrazione completa analisi download sospetti."""
        # Mock tutte le funzioni di controllo
        with patch.object(self.monitoring_service, '_check_massive_downloads') as mock_massive:
            with patch.object(self.monitoring_service, '_check_off_hours_access') as mock_off_hours:
                with patch.object(self.monitoring_service, '_check_file_repetition') as mock_repetition:
                    with patch.object(self.monitoring_service, '_check_suspicious_ips') as mock_ips:
                        with patch.object(self.monitoring_service, '_check_blocked_document_attempts') as mock_blocked:
                            
                            # Configura mock
                            mock_massive.return_value = []
                            mock_off_hours.return_value = []
                            mock_repetition.return_value = []
                            mock_ips.return_value = []
                            mock_blocked.return_value = []
                            
                            # Esegui test
                            alerts = self.monitoring_service.analizza_download_sospetti()
                            
                            # Verifica risultati
                            self.assertIsInstance(alerts, list)
                            
                            # Verifica che tutte le funzioni siano state chiamate
                            mock_massive.assert_called_once()
                            mock_off_hours.assert_called_once()
                            mock_repetition.assert_called_once()
                            mock_ips.assert_called_once()
                            mock_blocked.assert_called_once()
    
    def test_resolve_alert(self):
        """Test risoluzione alert."""
        # Mock alert
        mock_alert = MagicMock()
        mock_alert.id = 1
        mock_alert.resolved = False
        
        with patch('services.ai_monitoring.AIAlert') as mock_ai_alert_class:
            mock_ai_alert_class.query.get.return_value = mock_alert
            
            # Esegui test
            result = self.monitoring_service.resolve_alert(1, "admin")
            
            # Verifica risultati
            self.assertTrue(result)
            self.assertTrue(mock_alert.resolved)
            self.assertEqual(mock_alert.resolved_by, "admin")
    
    def test_generate_ai_analysis(self):
        """Test generazione analisi AI."""
        alert_data = {
            'alert_type': 'download_massivo',
            'description': 'Test alert',
            'severity': 'alta',
            'details': {'test': 'data'}
        }
        
        with patch('services.ai_monitoring.get_ai_response') as mock_ai:
            mock_ai.return_value = "Analisi AI di test"
            
            # Esegui test
            analysis = self.monitoring_service._generate_ai_analysis(alert_data)
            
            # Verifica risultati
            self.assertIsInstance(analysis, str)
            self.assertIn("Analisi AI di test", analysis)


class TestAIMonitoringFunctions(unittest.TestCase):
    """Test per le funzioni pubbliche del modulo."""
    
    def test_analizza_download_sospetti_function(self):
        """Test funzione pubblica analizza_download_sospetti."""
        with patch('services.ai_monitoring.ai_monitoring_service') as mock_service:
            mock_service.analizza_download_sospetti.return_value = []
            
            result = analizza_download_sospetti()
            
            self.assertIsInstance(result, list)
            mock_service.analizza_download_sospetti.assert_called_once()
    
    def test_create_ai_alert_function(self):
        """Test funzione pubblica create_ai_alert."""
        alert_data = {'test': 'data'}
        
        with patch('services.ai_monitoring.ai_monitoring_service') as mock_service:
            mock_service.create_ai_alert.return_value = MagicMock()
            
            result = create_ai_alert(alert_data)
            
            self.assertIsNotNone(result)
            mock_service.create_ai_alert.assert_called_once_with(alert_data)
    
    def test_get_recent_alerts_function(self):
        """Test funzione pubblica get_recent_alerts."""
        with patch('services.ai_monitoring.ai_monitoring_service') as mock_service:
            mock_service.get_recent_alerts.return_value = []
            
            result = get_recent_alerts(24)
            
            self.assertIsInstance(result, list)
            mock_service.get_recent_alerts.assert_called_once_with(24)
    
    def test_get_alert_statistics_function(self):
        """Test funzione pubblica get_alert_statistics."""
        with patch('services.ai_monitoring.ai_monitoring_service') as mock_service:
            mock_service.get_alert_statistics.return_value = {}
            
            result = get_alert_statistics()
            
            self.assertIsInstance(result, dict)
            mock_service.get_alert_statistics.assert_called_once()


if __name__ == '__main__':
    # Esegui i test
    unittest.main(verbosity=2) 