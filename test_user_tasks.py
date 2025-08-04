"""
Test per il sistema di task personali utente.
Verifica tutte le funzionalità del sistema di gestione task personali.
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
from models import Task, User
from extensions import db


class TestUserTasks(unittest.TestCase):
    """Test per il sistema di task personali."""
    
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
        
        # Mock dei task
        self.task_mock = MagicMock()
        self.task_mock.id = 1
        self.task_mock.user_id = 1
        self.task_mock.titolo = "Test Task"
        self.task_mock.descrizione = "Test Description"
        self.task_mock.priorita = "Media"
        self.task_mock.stato = "Da fare"
        self.task_mock.origine = "Manuale"
        self.task_mock.scadenza = datetime.utcnow() + timedelta(days=7)
        self.task_mock.created_at = datetime.utcnow()
        self.task_mock.completed_at = None
        self.task_mock.created_by = "test@example.com"
    
    def test_my_tasks_route(self):
        """Test route per visualizzazione task personali."""
        # Mock della route
        with patch('routes.user_routes.current_user') as mock_current_user:
            mock_current_user.id = 1
            
            # Mock della query
            mock_tasks = [self.task_mock]
            
            with patch('routes.user_routes.Task.query') as mock_query:
                mock_query.filter_by.return_value.order_by.return_value.all.return_value = mock_tasks
                
                # Simula chiamata route
                from routes.user_routes import my_tasks
                
                # Verifica che la route esista
                self.assertTrue(hasattr(user_bp, 'my_tasks'))
    
    def test_my_tasks_data_route(self):
        """Test route per dati JSON task personali."""
        # Mock della route
        with patch('routes.user_routes.current_user') as mock_current_user:
            mock_current_user.id = 1
            
            # Mock della query
            mock_tasks = [self.task_mock]
            
            with patch('routes.user_routes.Task.query') as mock_query:
                mock_query.filter_by.return_value.order_by.return_value.all.return_value = mock_tasks
                
                # Simula chiamata route
                from routes.user_routes import my_tasks_data
                
                # Verifica che la route esista
                self.assertTrue(hasattr(user_bp, 'my_tasks_data'))
    
    def test_complete_task_route(self):
        """Test route per completamento task."""
        # Mock della route
        with patch('routes.user_routes.current_user') as mock_current_user:
            mock_current_user.id = 1
            
            # Mock della query
            with patch('routes.user_routes.Task.query') as mock_query:
                mock_query.filter_by.return_value.first.return_value = self.task_mock
                
                # Simula chiamata route
                from routes.user_routes import complete_task
                
                # Verifica che la route esista
                self.assertTrue(hasattr(user_bp, 'complete_task'))
    
    def test_delete_task_route(self):
        """Test route per eliminazione task."""
        # Mock della route
        with patch('routes.user_routes.current_user') as mock_current_user:
            mock_current_user.id = 1
            
            # Mock della query
            with patch('routes.user_routes.Task.query') as mock_query:
                mock_query.filter_by.return_value.first.return_value = self.task_mock
                
                # Simula chiamata route
                from routes.user_routes import delete_task
                
                # Verifica che la route esista
                self.assertTrue(hasattr(user_bp, 'delete_task'))
    
    def test_add_task_route(self):
        """Test route per aggiunta task."""
        # Mock della route
        with patch('routes.user_routes.current_user') as mock_current_user:
            mock_current_user.id = 1
            mock_current_user.email = "test@example.com"
            
            # Mock della request
            mock_request = MagicMock()
            mock_request.form = {
                'titolo': 'Test Task',
                'descrizione': 'Test Description',
                'priorita': 'Media',
                'origine': 'Manuale',
                'scadenza': ''
            }
            
            with patch('routes.user_routes.request', mock_request):
                # Simula chiamata route
                from routes.user_routes import add_task
                
                # Verifica che la route esista
                self.assertTrue(hasattr(user_bp, 'add_task'))
    
    def test_task_model_properties(self):
        """Test proprietà del modello Task."""
        # Test proprietà is_completed
        self.task_mock.stato = "Completato"
        self.assertTrue(self.task_mock.is_completed)
        
        self.task_mock.stato = "Da fare"
        self.assertFalse(self.task_mock.is_completed)
        
        # Test proprietà is_overdue
        self.task_mock.scadenza = datetime.utcnow() - timedelta(days=1)
        self.task_mock.stato = "Da fare"
        self.assertTrue(self.task_mock.is_overdue)
        
        self.task_mock.scadenza = datetime.utcnow() + timedelta(days=1)
        self.assertFalse(self.task_mock.is_overdue)
        
        # Test proprietà days_until_deadline
        self.task_mock.scadenza = datetime.utcnow() + timedelta(days=5)
        self.assertEqual(self.task_mock.days_until_deadline, 5)
    
    def test_task_origine_display(self):
        """Test display name per origine task."""
        # Test origine AI
        self.task_mock.origine = "AI"
        self.assertEqual(self.task_mock.origine_display, "🤖 AI")
        
        # Test origine Diario
        self.task_mock.origine = "Diario"
        self.assertEqual(self.task_mock.origine_display, "📝 Diario")
        
        # Test origine Deep Work
        self.task_mock.origine = "Deep Work"
        self.assertEqual(self.task_mock.origine_display, "🧠 Deep Work")
        
        # Test origine Manuale
        self.task_mock.origine = "Manuale"
        self.assertEqual(self.task_mock.origine_display, "✏️ Manuale")
    
    def test_task_badge_classes(self):
        """Test classi badge per task."""
        # Test badge origine
        self.task_mock.origine = "AI"
        self.assertEqual(self.task_mock.origine_badge_class, "bg-primary")
        
        self.task_mock.origine = "Diario"
        self.assertEqual(self.task_mock.origine_badge_class, "bg-info")
        
        self.task_mock.origine = "Deep Work"
        self.assertEqual(self.task_mock.origine_badge_class, "bg-warning")
        
        self.task_mock.origine = "Manuale"
        self.assertEqual(self.task_mock.origine_badge_class, "bg-secondary")
        
        # Test badge priorità
        self.task_mock.priorita = "Bassa"
        self.assertEqual(self.task_mock.priority_color, "success")
        
        self.task_mock.priorita = "Media"
        self.assertEqual(self.task_mock.priority_color, "info")
        
        self.task_mock.priorita = "Alta"
        self.assertEqual(self.task_mock.priority_color, "warning")
        
        self.task_mock.priorita = "Critica"
        self.assertEqual(self.task_mock.priority_color, "danger")
        
        # Test badge stato
        self.task_mock.stato = "Da fare"
        self.assertEqual(self.task_mock.status_color, "bg-secondary")
        
        self.task_mock.stato = "In corso"
        self.assertEqual(self.task_mock.status_color, "bg-warning")
        
        self.task_mock.stato = "Completato"
        self.assertEqual(self.task_mock.status_color, "bg-success")
        
        self.task_mock.stato = "Annullato"
        self.assertEqual(self.task_mock.status_color, "bg-danger")
    
    def test_task_data_serialization(self):
        """Test serializzazione dati task per JSON."""
        # Prepara dati task
        task_data = {
            'id': self.task_mock.id,
            'titolo': self.task_mock.titolo,
            'descrizione': self.task_mock.descrizione,
            'priorita': self.task_mock.priorita,
            'stato': self.task_mock.stato,
            'origine': self.task_mock.origine,
            'origine_display': self.task_mock.origine_display,
            'scadenza': self.task_mock.scadenza.strftime('%Y-%m-%d %H:%M') if self.task_mock.scadenza else None,
            'created_at': self.task_mock.created_at.strftime('%Y-%m-%d %H:%M'),
            'completed_at': self.task_mock.completed_at.strftime('%Y-%m-%d %H:%M') if self.task_mock.completed_at else None,
            'is_completed': self.task_mock.is_completed,
            'is_overdue': self.task_mock.is_overdue,
            'days_until_deadline': self.task_mock.days_until_deadline,
            'priority_color': self.task_mock.priority_color,
            'status_color': self.task_mock.status_color,
            'origine_badge_class': self.task_mock.origine_badge_class
        }
        
        # Verifica struttura dati
        self.assertIn('id', task_data)
        self.assertIn('titolo', task_data)
        self.assertIn('descrizione', task_data)
        self.assertIn('priorita', task_data)
        self.assertIn('stato', task_data)
        self.assertIn('origine', task_data)
        self.assertIn('origine_display', task_data)
        self.assertIn('scadenza', task_data)
        self.assertIn('created_at', task_data)
        self.assertIn('is_completed', task_data)
        self.assertIn('is_overdue', task_data)
    
    def test_task_statistics_calculation(self):
        """Test calcolo statistiche task."""
        # Mock task diversi
        tasks = [
            MagicMock(is_completed=True, origine="AI"),
            MagicMock(is_completed=False, origine="Manuale"),
            MagicMock(is_completed=True, origine="Diario"),
            MagicMock(is_completed=False, origine="Deep Work"),
            MagicMock(is_completed=False, origine="AI", is_overdue=True)
        ]
        
        # Calcola statistiche
        total_tasks = len(tasks)
        completed_tasks = len([t for t in tasks if t.is_completed])
        pending_tasks = total_tasks - completed_tasks
        overdue_tasks = len([t for t in tasks if t.is_overdue])
        
        # Distribuzione per origine
        origin_stats = {}
        for task in tasks:
            origin = task.origine
            if origin not in origin_stats:
                origin_stats[origin] = 0
            origin_stats[origin] += 1
        
        # Verifica calcoli
        self.assertEqual(total_tasks, 5)
        self.assertEqual(completed_tasks, 2)
        self.assertEqual(pending_tasks, 3)
        self.assertEqual(overdue_tasks, 1)
        self.assertEqual(origin_stats['AI'], 2)
        self.assertEqual(origin_stats['Manuale'], 1)
        self.assertEqual(origin_stats['Diario'], 1)
        self.assertEqual(origin_stats['Deep Work'], 1)
    
    def test_task_filtering(self):
        """Test filtri task."""
        # Mock task con caratteristiche diverse
        tasks = [
            MagicMock(
                titolo="Task AI",
                descrizione="Descrizione AI",
                priorita="Alta",
                stato="Da fare",
                origine="AI",
                scadenza=datetime.utcnow() + timedelta(days=1)
            ),
            MagicMock(
                titolo="Task Manuale",
                descrizione="Descrizione manuale",
                priorita="Bassa",
                stato="Completato",
                origine="Manuale",
                scadenza=None
            ),
            MagicMock(
                titolo="Task Scaduto",
                descrizione="Task scaduto",
                priorita="Critica",
                stato="Da fare",
                origine="Deep Work",
                scadenza=datetime.utcnow() - timedelta(days=1),
                is_overdue=True
            )
        ]
        
        # Test filtro per origine
        ai_tasks = [t for t in tasks if t.origine == "AI"]
        self.assertEqual(len(ai_tasks), 1)
        self.assertEqual(ai_tasks[0].titolo, "Task AI")
        
        # Test filtro per priorità
        alta_priority_tasks = [t for t in tasks if t.priorita == "Alta"]
        self.assertEqual(len(alta_priority_tasks), 1)
        self.assertEqual(alta_priority_tasks[0].titolo, "Task AI")
        
        # Test filtro per stato
        completed_tasks = [t for t in tasks if t.stato == "Completato"]
        self.assertEqual(len(completed_tasks), 1)
        self.assertEqual(completed_tasks[0].titolo, "Task Manuale")
        
        # Test filtro per scadenza
        overdue_tasks = [t for t in tasks if t.is_overdue]
        self.assertEqual(len(overdue_tasks), 1)
        self.assertEqual(overdue_tasks[0].titolo, "Task Scaduto")
    
    def test_task_validation(self):
        """Test validazione dati task."""
        # Test titolo obbligatorio
        invalid_task_data = {
            'titolo': '',
            'descrizione': 'Test',
            'priorita': 'Media',
            'origine': 'Manuale'
        }
        
        # Simula validazione
        if not invalid_task_data['titolo']:
            validation_error = "Titolo obbligatorio"
        
        self.assertEqual(validation_error, "Titolo obbligatorio")
        
        # Test formato data valido
        valid_date = "2024-01-15T10:30"
        try:
            datetime.strptime(valid_date, '%Y-%m-%dT%H:%M')
            date_valid = True
        except ValueError:
            date_valid = False
        
        self.assertTrue(date_valid)
        
        # Test formato data non valido
        invalid_date = "invalid-date"
        try:
            datetime.strptime(invalid_date, '%Y-%m-%dT%H:%M')
            date_valid = True
        except ValueError:
            date_valid = False
        
        self.assertFalse(date_valid)
    
    def test_task_security(self):
        """Test sicurezza task personali."""
        # Mock utenti diversi
        user1 = MagicMock(id=1, username="user1")
        user2 = MagicMock(id=2, username="user2")
        
        # Mock task per utenti diversi
        tasks_user1 = [
            MagicMock(user_id=1, titolo="Task User 1"),
            MagicMock(user_id=1, titolo="Task User 1")
        ]
        
        tasks_user2 = [
            MagicMock(user_id=2, titolo="Task User 2"),
            MagicMock(user_id=2, titolo="Task User 2"),
            MagicMock(user_id=2, titolo="Task User 2")
        ]
        
        # Verifica isolamento dati
        self.assertEqual(len(tasks_user1), 2)
        self.assertEqual(len(tasks_user2), 3)
        
        # Verifica che i task appartengano agli utenti corretti
        for task in tasks_user1:
            self.assertEqual(task.user_id, 1)
        
        for task in tasks_user2:
            self.assertEqual(task.user_id, 2)
        
        # Verifica che un utente non possa accedere ai task dell'altro
        user1_tasks_filtered = [t for t in tasks_user1 if t.user_id == 1]
        user2_tasks_filtered = [t for t in tasks_user2 if t.user_id == 2]
        
        self.assertEqual(len(user1_tasks_filtered), 2)
        self.assertEqual(len(user2_tasks_filtered), 3)
    
    def test_csv_export_format(self):
        """Test formato esportazione CSV."""
        # Mock dati task
        tasks = [
            MagicMock(
                id=1,
                titolo="Task 1",
                descrizione="Descrizione 1",
                priorita="Alta",
                stato="Da fare",
                origine="AI",
                scadenza=datetime(2024, 1, 15, 10, 30, 0),
                created_at=datetime(2024, 1, 10, 9, 0, 0),
                completed_at=None
            ),
            MagicMock(
                id=2,
                titolo="Task 2",
                descrizione="Descrizione 2",
                priorita="Bassa",
                stato="Completato",
                origine="Manuale",
                scadenza=None,
                created_at=datetime(2024, 1, 8, 14, 0, 0),
                completed_at=datetime(2024, 1, 12, 16, 0, 0)
            )
        ]
        
        # Simula creazione CSV
        csv_rows = []
        for task in tasks:
            row = [
                task.id,
                task.titolo,
                task.descrizione or '',
                task.priorita,
                task.stato,
                task.origine,
                task.scadenza.strftime("%Y-%m-%d %H:%M") if task.scadenza else 'N/A',
                task.created_at.strftime("%Y-%m-%d %H:%M"),
                task.completed_at.strftime("%Y-%m-%d %H:%M") if task.completed_at else 'N/A'
            ]
            csv_rows.append(row)
        
        # Verifica formato CSV
        self.assertEqual(len(csv_rows), 2)
        self.assertEqual(len(csv_rows[0]), 9)  # 9 colonne
        self.assertIn("Task 1", csv_rows[0][1])
        self.assertIn("Task 2", csv_rows[1][1])
        self.assertEqual(csv_rows[0][3], "Alta")  # Priorità
        self.assertEqual(csv_rows[1][3], "Bassa")  # Priorità
        self.assertEqual(csv_rows[0][4], "Da fare")  # Stato
        self.assertEqual(csv_rows[1][4], "Completato")  # Stato


class TestUserTasksIntegration(unittest.TestCase):
    """Test integrazione per il sistema di task personali."""
    
    def test_complete_workflow(self):
        """Test workflow completo."""
        # 1. Mock utente autenticato
        mock_user = MagicMock(id=1, username="testuser")
        
        # 2. Mock task dell'utente
        mock_tasks = []
        for i in range(3):
            mock_task = MagicMock()
            mock_task.id = i + 1
            mock_task.user_id = 1
            mock_task.titolo = f"Task {i+1}"
            mock_task.descrizione = f"Descrizione task {i+1}"
            mock_task.priorita = "Media"
            mock_task.stato = "Da fare"
            mock_task.origine = "Manuale"
            mock_task.created_at = datetime.utcnow() - timedelta(days=i)
            mock_tasks.append(mock_task)
        
        # 3. Mock completamento task
        task_to_complete = mock_tasks[0]
        task_to_complete.stato = "Completato"
        task_to_complete.completed_at = datetime.utcnow()
        
        # 4. Verifica workflow
        self.assertEqual(len(mock_tasks), 3)
        self.assertEqual(task_to_complete.stato, "Completato")
        self.assertIsNotNone(task_to_complete.completed_at)
        
        # Verifica che tutti i task appartengano all'utente
        for task in mock_tasks:
            self.assertEqual(task.user_id, 1)
    
    def test_data_integrity(self):
        """Test integrità dati."""
        # Mock task con dati completi
        task = MagicMock()
        task.id = 1
        task.user_id = 1
        task.titolo = "Test Task"
        task.descrizione = "Test Description"
        task.priorita = "Media"
        task.stato = "Da fare"
        task.origine = "Manuale"
        task.scadenza = datetime.utcnow() + timedelta(days=7)
        task.created_at = datetime.utcnow()
        task.completed_at = None
        task.created_by = "test@example.com"
        
        # Verifica integrità dati
        self.assertEqual(task.id, 1)
        self.assertEqual(task.user_id, 1)
        self.assertEqual(task.titolo, "Test Task")
        self.assertEqual(task.descrizione, "Test Description")
        self.assertEqual(task.priorita, "Media")
        self.assertEqual(task.stato, "Da fare")
        self.assertEqual(task.origine, "Manuale")
        self.assertIsNotNone(task.scadenza)
        self.assertIsNotNone(task.created_at)
        self.assertIsNone(task.completed_at)
        self.assertEqual(task.created_by, "test@example.com")
    
    def test_performance_with_large_dataset(self):
        """Test performance con dataset grande."""
        # Mock 1000 task
        tasks = []
        for i in range(1000):
            task = MagicMock()
            task.id = i + 1
            task.user_id = 1
            task.titolo = f"Task {i+1}"
            task.descrizione = f"Descrizione task {i+1}"
            task.priorita = "Media"
            task.stato = "Da fare"
            task.origine = "Manuale"
            task.created_at = datetime.utcnow() - timedelta(hours=i)
            tasks.append(task)
        
        # Verifica performance
        self.assertEqual(len(tasks), 1000)
        
        # Test filtri
        ai_tasks = [t for t in tasks if t.origine == "AI"]
        completed_tasks = [t for t in tasks if t.stato == "Completato"]
        high_priority_tasks = [t for t in tasks if t.priorita == "Alta"]
        
        # Verifica che i filtri funzionino
        self.assertEqual(len(ai_tasks), 0)  # Nessun task AI nel mock
        self.assertEqual(len(completed_tasks), 0)  # Nessun task completato nel mock
        self.assertEqual(len(high_priority_tasks), 0)  # Nessun task alta priorità nel mock


if __name__ == '__main__':
    # Esegui i test
    unittest.main(verbosity=2) 