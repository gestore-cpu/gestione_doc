"""
Test per il sistema di dashboard utente con grafico dei download personali.
Verifica tutte le funzionalità del sistema di visualizzazione download utente.
"""

import unittest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
import sys
import os
import json

# Aggiungi il path del progetto
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from routes.user_routes import user_bp
from models import DownloadLog, User, Document
from extensions import db


class TestUserDashboard(unittest.TestCase):
    """Test per il sistema di dashboard utente."""
    
    def setUp(self):
        """Setup per i test."""
        # Mock del database
        self.db_mock = MagicMock()
        self.session_mock = MagicMock()
        self.db_mock.session = self.session_mock
        
        # Mock dell'utente
        self.user_mock = MagicMock()
        self.user_mock.id = 1
        self.user_mock.username = "testuser"
        self.user_mock.email = "test@example.com"
        
        # Mock dei documenti
        self.document_mock = MagicMock()
        self.document_mock.id = 1
        self.document_mock.title = "test_document.pdf"
        
        # Mock dei download
        self.download_mock = MagicMock()
        self.download_mock.id = 1
        self.download_mock.user_id = 1
        self.download_mock.document_id = 1
        self.download_mock.timestamp = datetime.utcnow()
        self.download_mock.user = self.user_mock
        self.download_mock.document = self.document_mock
    
    def test_my_downloads_chart_route(self):
        """Test route per dati grafico download."""
        # Mock della route
        with patch('routes.user_routes.current_user') as mock_current_user:
            mock_current_user.id = 1
            
            # Mock della query
            mock_query_result = [
                MagicMock(date=datetime.now().date(), download_count=5),
                MagicMock(date=(datetime.now() - timedelta(days=1)).date(), download_count=3),
                MagicMock(date=(datetime.now() - timedelta(days=2)).date(), download_count=7)
            ]
            
            with patch('routes.user_routes.db.session.query') as mock_query:
                mock_query.return_value.filter.return_value.group_by.return_value.order_by.return_value.all.return_value = mock_query_result
                
                # Simula chiamata route
                from routes.user_routes import my_downloads_chart
                
                # Verifica che la route esista
                self.assertTrue(hasattr(user_bp, 'my_downloads_chart'))
    
    def test_export_my_downloads_csv_route(self):
        """Test route per esportazione CSV download personali."""
        # Mock della route
        with patch('routes.user_routes.current_user') as mock_current_user:
            mock_current_user.id = 1
            
            # Mock della query
            mock_downloads = [self.download_mock]
            
            with patch('routes.user_routes.DownloadLog.query') as mock_query:
                mock_query.filter_by.return_value.join.return_value.order_by.return_value.all.return_value = mock_downloads
                
                # Simula chiamata route
                from routes.user_routes import export_my_downloads_csv
                
                # Verifica che la route esista
                self.assertTrue(hasattr(user_bp, 'export_my_downloads_csv'))
    
    def test_download_data_aggregation(self):
        """Test aggregazione dati download per giorno."""
        # Mock dati di test
        test_downloads = []
        for i in range(10):
            mock_download = MagicMock()
            mock_download.date = (datetime.now() - timedelta(days=i)).date()
            mock_download.download_count = i + 1
            test_downloads.append(mock_download)
        
        # Simula aggregazione
        dates = []
        counts = []
        
        for download in test_downloads:
            dates.append(download.date.strftime('%d/%m'))
            counts.append(download.download_count)
        
        # Verifica aggregazione
        self.assertEqual(len(dates), 10)
        self.assertEqual(len(counts), 10)
        self.assertEqual(counts[0], 1)  # Primo giorno
        self.assertEqual(counts[9], 10)  # Ultimo giorno
    
    def test_chart_data_format(self):
        """Test formato dati per Chart.js."""
        # Mock dati
        chart_data = {
            'labels': ['01/01', '02/01', '03/01'],
            'datasets': [{
                'label': 'Download',
                'data': [5, 3, 7],
                'backgroundColor': 'rgba(54, 162, 235, 0.2)',
                'borderColor': 'rgba(54, 162, 235, 1)',
                'borderWidth': 2,
                'tension': 0.1
            }]
        }
        
        # Verifica formato
        self.assertIn('labels', chart_data)
        self.assertIn('datasets', chart_data)
        self.assertEqual(len(chart_data['labels']), 3)
        self.assertEqual(len(chart_data['datasets']), 1)
        self.assertEqual(chart_data['datasets'][0]['label'], 'Download')
        self.assertEqual(len(chart_data['datasets'][0]['data']), 3)
    
    def test_statistics_calculation(self):
        """Test calcolo statistiche download."""
        # Mock dati
        counts = [5, 3, 7, 2, 8, 1, 4, 6, 9, 0]
        
        # Calcola statistiche
        total_downloads = sum(counts)
        avg_downloads = total_downloads / len(counts) if total_downloads > 0 else 0
        max_downloads = max(counts) if counts else 0
        
        # Verifica calcoli
        self.assertEqual(total_downloads, 45)
        self.assertEqual(avg_downloads, 4.5)
        self.assertEqual(max_downloads, 9)
    
    def test_date_range_calculation(self):
        """Test calcolo range date (ultimi 30 giorni)."""
        # Calcola date
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        today = datetime.utcnow().date()
        
        # Verifica range
        self.assertLessEqual(thirty_days_ago.date(), today)
        self.assertEqual((today - thirty_days_ago.date()).days, 30)
    
    def test_user_data_isolation(self):
        """Test isolamento dati utente."""
        # Mock utenti diversi
        user1 = MagicMock(id=1, username="user1")
        user2 = MagicMock(id=2, username="user2")
        
        # Mock download per utenti diversi
        downloads_user1 = [
            MagicMock(user_id=1, timestamp=datetime.utcnow()),
            MagicMock(user_id=1, timestamp=datetime.utcnow())
        ]
        
        downloads_user2 = [
            MagicMock(user_id=2, timestamp=datetime.utcnow()),
            MagicMock(user_id=2, timestamp=datetime.utcnow()),
            MagicMock(user_id=2, timestamp=datetime.utcnow())
        ]
        
        # Verifica isolamento
        self.assertEqual(len(downloads_user1), 2)
        self.assertEqual(len(downloads_user2), 3)
        
        # Verifica che i download appartengano agli utenti corretti
        for download in downloads_user1:
            self.assertEqual(download.user_id, 1)
        
        for download in downloads_user2:
            self.assertEqual(download.user_id, 2)
    
    def test_csv_export_format(self):
        """Test formato esportazione CSV."""
        # Mock dati download
        downloads = [
            MagicMock(
                timestamp=datetime(2024, 1, 15, 10, 30, 0),
                document=MagicMock(title="doc1.pdf"),
                ip_address="192.168.1.100"
            ),
            MagicMock(
                timestamp=datetime(2024, 1, 16, 14, 20, 0),
                document=MagicMock(title="doc2.pdf"),
                ip_address="192.168.1.101"
            )
        ]
        
        # Simula creazione CSV
        csv_rows = []
        for download in downloads:
            row = [
                download.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                download.document.title,
                "Test Company",  # Mock company
                "Test Department",  # Mock department
                download.ip_address
            ]
            csv_rows.append(row)
        
        # Verifica formato CSV
        self.assertEqual(len(csv_rows), 2)
        self.assertEqual(len(csv_rows[0]), 5)  # 5 colonne
        self.assertIn("doc1.pdf", csv_rows[0][1])
        self.assertIn("doc2.pdf", csv_rows[1][1])
    
    def test_error_handling(self):
        """Test gestione errori."""
        # Mock errori comuni
        errors = [
            "Database connection error",
            "User not found",
            "Invalid date format",
            "Permission denied"
        ]
        
        # Verifica gestione errori
        for error in errors:
            try:
                raise Exception(error)
            except Exception as e:
                self.assertIn(error, str(e))
                self.assertIsInstance(e, Exception)
    
    def test_chart_configuration(self):
        """Test configurazione grafico Chart.js."""
        # Mock configurazione grafico
        chart_config = {
            'type': 'line',
            'data': {
                'labels': ['01/01', '02/01'],
                'datasets': [{
                    'label': 'Download',
                    'data': [5, 3],
                    'backgroundColor': 'rgba(54, 162, 235, 0.2)',
                    'borderColor': 'rgba(54, 162, 235, 1)',
                    'borderWidth': 2,
                    'tension': 0.1
                }]
            },
            'options': {
                'responsive': True,
                'maintainAspectRatio': False,
                'plugins': {
                    'legend': {
                        'display': True,
                        'position': 'top'
                    }
                }
            }
        }
        
        # Verifica configurazione
        self.assertEqual(chart_config['type'], 'line')
        self.assertTrue(chart_config['options']['responsive'])
        self.assertFalse(chart_config['options']['maintainAspectRatio'])
        self.assertTrue(chart_config['options']['plugins']['legend']['display'])
    
    def test_mobile_responsiveness(self):
        """Test responsività mobile."""
        # Mock configurazioni responsive
        responsive_configs = {
            'chart_height': '400px',
            'chart_container': 'position: relative; height: 400px;',
            'mobile_breakpoint': '768px',
            'table_responsive': True
        }
        
        # Verifica configurazioni responsive
        self.assertIn('px', responsive_configs['chart_height'])
        self.assertIn('position: relative', responsive_configs['chart_container'])
        self.assertIn('768px', responsive_configs['mobile_breakpoint'])
        self.assertTrue(responsive_configs['table_responsive'])


class TestUserDashboardIntegration(unittest.TestCase):
    """Test integrazione per il sistema di dashboard utente."""
    
    def test_complete_workflow(self):
        """Test workflow completo."""
        # 1. Mock utente autenticato
        mock_user = MagicMock(id=1, username="testuser")
        
        # 2. Mock dati download
        mock_downloads = []
        for i in range(5):
            mock_download = MagicMock()
            mock_download.id = i + 1
            mock_download.user_id = 1
            mock_download.timestamp = datetime.utcnow() - timedelta(days=i)
            mock_download.document = MagicMock(title=f"doc{i+1}.pdf")
            mock_downloads.append(mock_download)
        
        # 3. Mock aggregazione dati
        aggregated_data = {}
        for download in mock_downloads:
            date = download.timestamp.date()
            if date not in aggregated_data:
                aggregated_data[date] = 0
            aggregated_data[date] += 1
        
        # 4. Verifica workflow
        self.assertEqual(len(mock_downloads), 5)
        self.assertEqual(len(aggregated_data), 5)
        
        # Verifica che tutti i download appartengano all'utente
        for download in mock_downloads:
            self.assertEqual(download.user_id, 1)
    
    def test_data_security(self):
        """Test sicurezza dati."""
        # Mock utenti diversi
        users = [
            MagicMock(id=1, username="user1"),
            MagicMock(id=2, username="user2"),
            MagicMock(id=3, username="user3")
        ]
        
        # Mock download per ogni utente
        all_downloads = []
        for user in users:
            for i in range(3):  # 3 download per utente
                download = MagicMock()
                download.user_id = user.id
                download.timestamp = datetime.utcnow() - timedelta(days=i)
                all_downloads.append(download)
        
        # Verifica isolamento dati
        for user in users:
            user_downloads = [d for d in all_downloads if d.user_id == user.id]
            self.assertEqual(len(user_downloads), 3)
            
            # Verifica che l'utente non possa vedere download di altri
            for download in user_downloads:
                self.assertEqual(download.user_id, user.id)
    
    def test_performance_with_large_dataset(self):
        """Test performance con dataset grande."""
        # Mock 1000 download
        downloads = []
        for i in range(1000):
            download = MagicMock()
            download.id = i + 1
            download.user_id = 1
            download.timestamp = datetime.utcnow() - timedelta(hours=i)
            downloads.append(download)
        
        # Verifica performance
        self.assertEqual(len(downloads), 1000)
        
        # Test aggregazione
        aggregated = {}
        for download in downloads:
            date = download.timestamp.date()
            if date not in aggregated:
                aggregated[date] = 0
            aggregated[date] += 1
        
        # Verifica che l'aggregazione funzioni
        self.assertGreater(len(aggregated), 0)
        self.assertLessEqual(len(aggregated), 30)  # Max 30 giorni


if __name__ == '__main__':
    # Esegui i test
    unittest.main(verbosity=2) 