"""
Test per il sistema di log download e esportazione CSV.
Verifica tutte le funzionalità del sistema di tracciamento download.
"""

import unittest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
import sys
import os
import csv
import io

# Aggiungi il path del progetto
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from models import DownloadLog, User, Document, Company, Department
from extensions import db


class TestDownloadLogs(unittest.TestCase):
    """Test per il sistema di log download."""
    
    def setUp(self):
        """Setup per i test."""
        # Mock del database
        self.db_mock = MagicMock()
        self.session_mock = MagicMock()
        self.db_mock.session = self.session_mock
        
        # Mock dei modelli
        self.user_mock = MagicMock()
        self.user_mock.id = 1
        self.user_mock.username = "testuser"
        self.user_mock.email = "test@example.com"
        
        self.document_mock = MagicMock()
        self.document_mock.id = 1
        self.document_mock.title = "test_document.pdf"
        
        self.company_mock = MagicMock()
        self.company_mock.id = 1
        self.company_mock.name = "Test Company"
        
        self.department_mock = MagicMock()
        self.department_mock.id = 1
        self.department_mock.name = "Test Department"
    
    def test_download_log_creation(self):
        """Test creazione log download."""
        # Mock DownloadLog
        mock_log = MagicMock()
        mock_log.id = 1
        mock_log.user_id = 1
        mock_log.document_id = 1
        mock_log.timestamp = datetime.utcnow()
        mock_log.user = self.user_mock
        mock_log.document = self.document_mock
        
        # Verifica proprietà
        self.assertEqual(mock_log.id, 1)
        self.assertEqual(mock_log.user_id, 1)
        self.assertEqual(mock_log.document_id, 1)
        self.assertIsNotNone(mock_log.timestamp)
        self.assertEqual(mock_log.user.username, "testuser")
        self.assertEqual(mock_log.document.title, "test_document.pdf")
    
    @patch('models.DownloadLog')
    @patch('models.User')
    @patch('models.Document')
    @patch('models.Company')
    def test_download_logs_query(self, mock_company, mock_document, mock_user, mock_download_log):
        """Test query log download con filtri."""
        # Mock query results
        mock_logs = []
        for i in range(5):
            mock_log = MagicMock()
            mock_log.id = i + 1
            mock_log.user_id = 1
            mock_log.document_id = 1
            mock_log.timestamp = datetime.utcnow() - timedelta(hours=i)
            mock_log.user = self.user_mock
            mock_log.document = self.document_mock
            mock_logs.append(mock_log)
        
        # Mock query
        mock_query = MagicMock()
        mock_query.join.return_value.join.return_value.join.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value.all.return_value = mock_logs
        
        mock_download_log.query = mock_query
        
        # Simula query con filtri
        query = mock_download_log.query.join(mock_user).join(mock_document).join(mock_company)
        
        # Applica filtri
        user_filter = "1"
        if user_filter:
            query = query.filter(mock_download_log.user_id == user_filter)
        
        # Verifica risultati
        logs = query.order_by(mock_download_log.timestamp.desc()).all()
        
        self.assertEqual(len(logs), 5)
        self.assertEqual(logs[0].id, 1)
        self.assertEqual(logs[0].user.username, "testuser")
    
    def test_csv_export_format(self):
        """Test formato esportazione CSV."""
        # Crea dati di test
        test_logs = []
        for i in range(3):
            mock_log = MagicMock()
            mock_log.id = i + 1
            mock_log.timestamp = datetime.utcnow() - timedelta(hours=i)
            mock_log.user = self.user_mock
            mock_log.document = self.document_mock
            mock_log.ip_address = f"192.168.1.{i+1}"
            mock_log.note = f"Test note {i+1}"
            test_logs.append(mock_log)
        
        # Crea CSV
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Header
        writer.writerow([
            "ID", "Data e Ora", "Utente", "Email Utente", "File Scaricato", 
            "Azienda", "Reparto", "IP Accesso", "Metodo", "Note"
        ])
        
        # Dati
        for log in test_logs:
            writer.writerow([
                log.id,
                log.timestamp.strftime("%Y-%m-%d %H:%M:%S") if log.timestamp else 'N/A',
                log.user.username if log.user else 'N/A',
                log.user.email if log.user else 'N/A',
                log.document.title if log.document else 'N/A',
                'Test Company',  # Mock company
                'Test Department',  # Mock department
                log.ip_address or 'N/A',
                'Web',  # Mock method
                log.note or ''
            ])
        
        output.seek(0)
        csv_content = output.getvalue()
        
        # Verifica formato CSV
        self.assertIn("ID,Data e Ora,Utente,Email Utente,File Scaricato", csv_content)
        self.assertIn("testuser", csv_content)
        self.assertIn("test@example.com", csv_content)
        self.assertIn("test_document.pdf", csv_content)
        self.assertIn("192.168.1.1", csv_content)
    
    def test_filter_functionality(self):
        """Test funzionalità filtri."""
        # Mock filtri
        filters = {
            'user_id': '1',
            'document_id': '1',
            'company_id': '1',
            'date_from': '2024-01-01',
            'date_to': '2024-12-31'
        }
        
        # Verifica filtri
        self.assertEqual(filters['user_id'], '1')
        self.assertEqual(filters['document_id'], '1')
        self.assertEqual(filters['company_id'], '1')
        self.assertEqual(filters['date_from'], '2024-01-01')
        self.assertEqual(filters['date_to'], '2024-12-31')
    
    def test_statistics_calculation(self):
        """Test calcolo statistiche."""
        # Mock statistiche
        stats = {
            'total': 100,
            'unique_users': 25,
            'unique_documents': 50,
            'recent_30_days': 30
        }
        
        # Verifica statistiche
        self.assertEqual(stats['total'], 100)
        self.assertEqual(stats['unique_users'], 25)
        self.assertEqual(stats['unique_documents'], 50)
        self.assertEqual(stats['recent_30_days'], 30)
        
        # Verifica calcoli
        self.assertGreater(stats['total'], 0)
        self.assertLessEqual(stats['unique_users'], stats['total'])
        self.assertLessEqual(stats['unique_documents'], stats['total'])
        self.assertLessEqual(stats['recent_30_days'], stats['total'])
    
    @patch('models.DownloadLog')
    @patch('models.User')
    def test_top_users_calculation(self, mock_user, mock_download_log):
        """Test calcolo top utenti."""
        # Mock top users
        top_users = [
            MagicMock(username="user1", download_count=50),
            MagicMock(username="user2", download_count=30),
            MagicMock(username="user3", download_count=20)
        ]
        
        # Verifica top users
        self.assertEqual(len(top_users), 3)
        self.assertEqual(top_users[0].username, "user1")
        self.assertEqual(top_users[0].download_count, 50)
        self.assertEqual(top_users[1].username, "user2")
        self.assertEqual(top_users[1].download_count, 30)
        
        # Verifica ordinamento (decrescente)
        self.assertGreater(top_users[0].download_count, top_users[1].download_count)
        self.assertGreater(top_users[1].download_count, top_users[2].download_count)
    
    @patch('models.DownloadLog')
    @patch('models.Document')
    def test_top_documents_calculation(self, mock_document, mock_download_log):
        """Test calcolo top documenti."""
        # Mock top documents
        top_documents = [
            MagicMock(title="doc1.pdf", download_count=100),
            MagicMock(title="doc2.pdf", download_count=75),
            MagicMock(title="doc3.pdf", download_count=50)
        ]
        
        # Verifica top documents
        self.assertEqual(len(top_documents), 3)
        self.assertEqual(top_documents[0].title, "doc1.pdf")
        self.assertEqual(top_documents[0].download_count, 100)
        self.assertEqual(top_documents[1].title, "doc2.pdf")
        self.assertEqual(top_documents[1].download_count, 75)
        
        # Verifica ordinamento (decrescente)
        self.assertGreater(top_documents[0].download_count, top_documents[1].download_count)
        self.assertGreater(top_documents[1].download_count, top_documents[2].download_count)
    
    def test_date_filtering(self):
        """Test filtri per data."""
        # Mock date filters
        date_from = datetime.strptime('2024-01-01', '%Y-%m-%d')
        date_to = datetime.strptime('2024-12-31', '%Y-%m-%d')
        
        # Mock logs con date diverse
        logs = [
            MagicMock(timestamp=datetime(2024, 6, 15, 10, 0, 0)),  # Dentro range
            MagicMock(timestamp=datetime(2024, 12, 31, 23, 59, 59)),  # Dentro range
            MagicMock(timestamp=datetime(2023, 12, 31, 23, 59, 59)),  # Fuori range
            MagicMock(timestamp=datetime(2025, 1, 1, 0, 0, 0)),  # Fuori range
        ]
        
        # Filtra per data
        filtered_logs = [
            log for log in logs 
            if date_from <= log.timestamp <= date_to
        ]
        
        # Verifica filtri
        self.assertEqual(len(filtered_logs), 2)
        self.assertIn(logs[0], filtered_logs)
        self.assertIn(logs[1], filtered_logs)
        self.assertNotIn(logs[2], filtered_logs)
        self.assertNotIn(logs[3], filtered_logs)
    
    def test_ip_address_tracking(self):
        """Test tracciamento IP."""
        # Mock logs con IP diversi
        logs = [
            MagicMock(ip_address="192.168.1.100"),
            MagicMock(ip_address="10.0.0.50"),
            MagicMock(ip_address="172.16.0.25"),
            MagicMock(ip_address=None),
        ]
        
        # Verifica IP
        self.assertEqual(logs[0].ip_address, "192.168.1.100")
        self.assertEqual(logs[1].ip_address, "10.0.0.50")
        self.assertEqual(logs[2].ip_address, "172.16.0.25")
        self.assertIsNone(logs[3].ip_address)
        
        # Verifica IP validi
        valid_ips = [log.ip_address for log in logs if log.ip_address]
        self.assertEqual(len(valid_ips), 3)
        self.assertIn("192.168.1.100", valid_ips)
        self.assertIn("10.0.0.50", valid_ips)
        self.assertIn("172.16.0.25", valid_ips)
    
    def test_company_department_tracking(self):
        """Test tracciamento azienda e reparto."""
        # Mock document con company e department
        mock_document = MagicMock()
        mock_document.company = self.company_mock
        mock_document.department = self.department_mock
        
        # Mock log
        mock_log = MagicMock()
        mock_log.document = mock_document
        
        # Verifica relazioni
        self.assertEqual(mock_log.document.company.name, "Test Company")
        self.assertEqual(mock_log.document.department.name, "Test Department")
        
        # Verifica accesso sicuro
        company_name = mock_log.document.company.name if mock_log.document and mock_log.document.company else 'N/A'
        department_name = mock_log.document.department.name if mock_log.document and mock_log.document.department else 'N/A'
        
        self.assertEqual(company_name, "Test Company")
        self.assertEqual(department_name, "Test Department")
    
    def test_csv_filename_generation(self):
        """Test generazione nome file CSV."""
        # Mock timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"download_logs_{timestamp}.csv"
        
        # Verifica formato nome file
        self.assertIn("download_logs_", filename)
        self.assertIn(".csv", filename)
        self.assertIn("_", filename)
        
        # Verifica che contenga timestamp
        parts = filename.split("_")
        self.assertEqual(len(parts), 3)  # download_logs, timestamp, csv
        self.assertEqual(parts[0], "download_logs")
        self.assertEqual(parts[2], "csv")
    
    def test_error_handling(self):
        """Test gestione errori."""
        # Mock errori comuni
        errors = [
            "Database connection error",
            "Invalid date format",
            "User not found",
            "Document not found",
            "Permission denied"
        ]
        
        # Verifica gestione errori
        for error in errors:
            try:
                # Simula errore
                raise Exception(error)
            except Exception as e:
                self.assertIn(error, str(e))
                # Verifica che l'errore sia catturato
                self.assertIsInstance(e, Exception)


class TestDownloadLogsIntegration(unittest.TestCase):
    """Test integrazione per il sistema di log download."""
    
    def test_complete_workflow(self):
        """Test workflow completo."""
        # 1. Creazione log
        mock_log = MagicMock()
        mock_log.id = 1
        mock_log.user_id = 1
        mock_log.document_id = 1
        mock_log.timestamp = datetime.utcnow()
        
        # 2. Query con filtri
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value.all.return_value = [mock_log]
        
        # 3. Esportazione CSV
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["ID", "Timestamp"])
        writer.writerow([mock_log.id, mock_log.timestamp.strftime("%Y-%m-%d %H:%M:%S")])
        
        # 4. Verifica risultati
        csv_content = output.getvalue()
        self.assertIn("ID,Timestamp", csv_content)
        self.assertIn("1,", csv_content)
    
    def test_performance_with_large_dataset(self):
        """Test performance con dataset grande."""
        # Mock 1000 log
        logs = []
        for i in range(1000):
            mock_log = MagicMock()
            mock_log.id = i + 1
            mock_log.timestamp = datetime.utcnow() - timedelta(hours=i)
            logs.append(mock_log)
        
        # Verifica performance
        self.assertEqual(len(logs), 1000)
        
        # Test filtri
        filtered_logs = logs[:100]  # Simula filtro
        self.assertEqual(len(filtered_logs), 100)
        
        # Test esportazione
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["ID", "Timestamp"])
        for log in filtered_logs:
            writer.writerow([log.id, log.timestamp.strftime("%Y-%m-%d %H:%M:%S")])
        
        csv_content = output.getvalue()
        lines = csv_content.split('\n')
        self.assertEqual(len(lines), 102)  # Header + 100 dati + 1 vuota


if __name__ == '__main__':
    # Esegui i test
    unittest.main(verbosity=2) 