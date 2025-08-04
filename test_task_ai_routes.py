"""
Test per le route TaskAI - Prompt 26 FASE 2
Verifica che tutte le API CRUD per TaskAI funzionino correttamente.
"""

import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
import json
import sys
import os

# Aggiungi il path del progetto
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from routes.task_ai_routes import task_ai_bp
from models import TaskAI, OrigineTask, PrioritaTask
from schemas.task_schemas import TaskAICreate, TaskAIUpdate, TaskAIRead, TaskAIFilter, TaskAIStats


class TestTaskAIRoutes(unittest.TestCase):
    """Test per le route TaskAI."""
    
    def setUp(self):
        """Setup per i test."""
        # Mock dell'utente corrente
        self.user_mock = MagicMock()
        self.user_mock.id = 1
        self.user_mock.username = "testuser"
        self.user_mock.email = "test@example.com"
        
        # Mock del task AI
        self.task_ai_mock = MagicMock()
        self.task_ai_mock.id = 1
        self.task_ai_mock.user_id = 1
        self.task_ai_mock.titolo = "Test Task AI"
        self.task_ai_mock.descrizione = "Test Description AI"
        self.task_ai_mock.data_scadenza = datetime.utcnow() + timedelta(days=7)
        self.task_ai_mock.priorita = PrioritaTask.MEDIUM
        self.task_ai_mock.origine = OrigineTask.AI
        self.task_ai_mock.stato = False
        self.task_ai_mock.data_creazione = datetime.utcnow()
        
        # Mock delle proprietà calcolate
        self.task_ai_mock.is_completed = False
        self.task_ai_mock.is_overdue = False
        self.task_ai_mock.days_until_deadline = 7
        self.task_ai_mock.priority_color = "info"
        self.task_ai_mock.status_color = "bg-secondary"
        self.task_ai_mock.origine_badge_class = "bg-primary"
        self.task_ai_mock.origine_display = "🤖 AI"
    
    def test_get_my_tasks_route(self):
        """Test route GET /api/tasks/my."""
        with patch('routes.task_ai_routes.current_user', self.user_mock), \
             patch('routes.task_ai_routes.TaskAI') as mock_task_ai_class:
            
            # Mock della query
            mock_query = MagicMock()
            mock_task_ai_class.query = mock_query
            mock_query.filter_by.return_value.order_by.return_value.all.return_value = [self.task_ai_mock]
            
            # Mock della risposta JSON
            with patch('routes.task_ai_routes.jsonify') as mock_jsonify:
                mock_jsonify.return_value = MagicMock()
                
                # Simula la chiamata alla route
                from routes.task_ai_routes import get_my_tasks
                response = get_my_tasks()
                
                # Verifica che la query sia stata chiamata correttamente
                mock_query.filter_by.assert_called_with(user_id=1)
                
                # Verifica che jsonify sia stato chiamato
                mock_jsonify.assert_called()
    
    def test_create_task_route(self):
        """Test route POST /api/tasks/."""
        with patch('routes.task_ai_routes.current_user', self.user_mock), \
             patch('routes.task_ai_routes.request') as mock_request, \
             patch('routes.task_ai_routes.TaskAI') as mock_task_ai_class, \
             patch('routes.task_ai_routes.database') as mock_db:
            
            # Mock dei dati di richiesta
            mock_request.get_json.return_value = {
                'titolo': 'Nuovo Task',
                'descrizione': 'Descrizione task',
                'priorita': 'Medium',
                'origine': 'AI'
            }
            
            # Mock del nuovo task
            new_task_mock = MagicMock()
            new_task_mock.id = 2
            new_task_mock.user_id = 1
            new_task_mock.titolo = 'Nuovo Task'
            new_task_mock.descrizione = 'Descrizione task'
            new_task_mock.priorita = PrioritaTask.MEDIUM
            new_task_mock.origine = OrigineTask.AI
            new_task_mock.stato = False
            new_task_mock.data_creazione = datetime.utcnow()
            new_task_mock.data_scadenza = None
            
            # Mock delle proprietà calcolate
            new_task_mock.is_completed = False
            new_task_mock.is_overdue = False
            new_task_mock.days_until_deadline = None
            new_task_mock.priority_color = "info"
            new_task_mock.status_color = "bg-secondary"
            new_task_mock.origine_badge_class = "bg-primary"
            new_task_mock.origine_display = "🤖 AI"
            
            mock_task_ai_class.return_value = new_task_mock
            
            # Mock della risposta JSON
            with patch('routes.task_ai_routes.jsonify') as mock_jsonify:
                mock_jsonify.return_value = MagicMock()
                
                # Simula la chiamata alla route
                from routes.task_ai_routes import create_task
                response = create_task()
                
                # Verifica che il task sia stato aggiunto al database
                mock_db.session.add.assert_called_with(new_task_mock)
                mock_db.session.commit.assert_called()
                
                # Verifica che jsonify sia stato chiamato
                mock_jsonify.assert_called()
    
    def test_complete_task_route(self):
        """Test route PATCH /api/tasks/{task_id}/complete."""
        with patch('routes.task_ai_routes.current_user', self.user_mock), \
             patch('routes.task_ai_routes.TaskAI') as mock_task_ai_class, \
             patch('routes.task_ai_routes.database') as mock_db:
            
            # Mock della query
            mock_query = MagicMock()
            mock_task_ai_class.query = mock_query
            mock_query.filter_by.return_value.first.return_value = self.task_ai_mock
            
            # Mock della risposta JSON
            with patch('routes.task_ai_routes.jsonify') as mock_jsonify:
                mock_jsonify.return_value = MagicMock()
                
                # Simula la chiamata alla route
                from routes.task_ai_routes import complete_task
                response = complete_task(1)
                
                # Verifica che lo stato sia stato aggiornato
                self.assertEqual(self.task_ai_mock.stato, True)
                mock_db.session.commit.assert_called()
                
                # Verifica che jsonify sia stato chiamato
                mock_jsonify.assert_called()
    
    def test_delete_task_route(self):
        """Test route DELETE /api/tasks/{task_id}."""
        with patch('routes.task_ai_routes.current_user', self.user_mock), \
             patch('routes.task_ai_routes.TaskAI') as mock_task_ai_class, \
             patch('routes.task_ai_routes.database') as mock_db:
            
            # Mock della query
            mock_query = MagicMock()
            mock_task_ai_class.query = mock_query
            mock_query.filter_by.return_value.first.return_value = self.task_ai_mock
            
            # Mock della risposta JSON
            with patch('routes.task_ai_routes.jsonify') as mock_jsonify:
                mock_jsonify.return_value = MagicMock()
                
                # Simula la chiamata alla route
                from routes.task_ai_routes import delete_task
                response = delete_task(1)
                
                # Verifica che il task sia stato eliminato
                mock_db.session.delete.assert_called_with(self.task_ai_mock)
                mock_db.session.commit.assert_called()
                
                # Verifica che jsonify sia stato chiamato
                mock_jsonify.assert_called()
    
    def test_update_task_route(self):
        """Test route PUT /api/tasks/{task_id}."""
        with patch('routes.task_ai_routes.current_user', self.user_mock), \
             patch('routes.task_ai_routes.request') as mock_request, \
             patch('routes.task_ai_routes.TaskAI') as mock_task_ai_class, \
             patch('routes.task_ai_routes.database') as mock_db:
            
            # Mock dei dati di richiesta
            mock_request.get_json.return_value = {
                'titolo': 'Task Aggiornato',
                'stato': True
            }
            
            # Mock della query
            mock_query = MagicMock()
            mock_task_ai_class.query = mock_query
            mock_query.filter_by.return_value.first.return_value = self.task_ai_mock
            
            # Mock della risposta JSON
            with patch('routes.task_ai_routes.jsonify') as mock_jsonify:
                mock_jsonify.return_value = MagicMock()
                
                # Simula la chiamata alla route
                from routes.task_ai_routes import update_task
                response = update_task(1)
                
                # Verifica che i campi siano stati aggiornati
                self.assertEqual(self.task_ai_mock.titolo, 'Task Aggiornato')
                self.assertEqual(self.task_ai_mock.stato, True)
                mock_db.session.commit.assert_called()
                
                # Verifica che jsonify sia stato chiamato
                mock_jsonify.assert_called()
    
    def test_get_my_task_stats_route(self):
        """Test route GET /api/tasks/my/stats."""
        with patch('routes.task_ai_routes.current_user', self.user_mock), \
             patch('routes.task_ai_routes.TaskAI') as mock_task_ai_class:
            
            # Mock della query
            mock_query = MagicMock()
            mock_task_ai_class.query = mock_query
            mock_query.filter_by.return_value.all.return_value = [self.task_ai_mock]
            
            # Mock della risposta JSON
            with patch('routes.task_ai_routes.jsonify') as mock_jsonify:
                mock_jsonify.return_value = MagicMock()
                
                # Simula la chiamata alla route
                from routes.task_ai_routes import get_my_task_stats
                response = get_my_task_stats()
                
                # Verifica che la query sia stata chiamata
                mock_query.filter_by.assert_called_with(user_id=1)
                
                # Verifica che jsonify sia stato chiamato
                mock_jsonify.assert_called()
    
    def test_filter_my_tasks_route(self):
        """Test route POST /api/tasks/my/filter."""
        with patch('routes.task_ai_routes.current_user', self.user_mock), \
             patch('routes.task_ai_routes.request') as mock_request, \
             patch('routes.task_ai_routes.TaskAI') as mock_task_ai_class:
            
            # Mock dei dati di richiesta
            mock_request.get_json.return_value = {
                'stato': False,
                'origine': 'AI',
                'sort_by': 'data_creazione',
                'sort_order': 'desc'
            }
            
            # Mock della query
            mock_query = MagicMock()
            mock_task_ai_class.query = mock_query
            mock_query.filter_by.return_value.filter.return_value.order_by.return_value.all.return_value = [self.task_ai_mock]
            
            # Mock della risposta JSON
            with patch('routes.task_ai_routes.jsonify') as mock_jsonify:
                mock_jsonify.return_value = MagicMock()
                
                # Simula la chiamata alla route
                from routes.task_ai_routes import filter_my_tasks
                response = filter_my_tasks()
                
                # Verifica che la query sia stata chiamata
                mock_query.filter_by.assert_called_with(user_id=1)
                
                # Verifica che jsonify sia stato chiamato
                mock_jsonify.assert_called()


class TestTaskAISchemas(unittest.TestCase):
    """Test per gli schemi TaskAI."""
    
    def test_task_ai_create_schema(self):
        """Test schema TaskAICreate."""
        # Test creazione valida
        task_data = {
            'titolo': 'Test Task',
            'descrizione': 'Test Description',
            'priorita': 'Medium',
            'origine': 'AI'
        }
        
        task_create = TaskAICreate(**task_data)
        self.assertEqual(task_create.titolo, 'Test Task')
        self.assertEqual(task_create.priorita, 'Medium')
        self.assertEqual(task_create.origine, 'AI')
        
        # Test validazione titolo obbligatorio
        with self.assertRaises(ValueError):
            TaskAICreate(titolo='')
        
        # Test validazione priorità non valida
        with self.assertRaises(ValueError):
            TaskAICreate(titolo='Test', priorita='Invalid')
        
        # Test validazione origine non valida
        with self.assertRaises(ValueError):
            TaskAICreate(titolo='Test', origine='Invalid')
    
    def test_task_ai_update_schema(self):
        """Test schema TaskAIUpdate."""
        # Test aggiornamento valido
        task_update = TaskAIUpdate(
            titolo='Updated Task',
            stato=True
        )
        
        result = task_update.to_dict()
        self.assertEqual(result['titolo'], 'Updated Task')
        self.assertEqual(result['stato'], True)
        self.assertNotIn('descrizione', result)  # Non dovrebbe essere incluso se None
    
    def test_task_ai_read_schema(self):
        """Test schema TaskAIRead."""
        # Mock del task AI
        task_mock = MagicMock()
        task_mock.id = 1
        task_mock.titolo = 'Test Task'
        task_mock.descrizione = 'Test Description'
        task_mock.data_scadenza = datetime.utcnow() + timedelta(days=7)
        task_mock.priorita = PrioritaTask.MEDIUM
        task_mock.origine = OrigineTask.AI
        task_mock.stato = False
        task_mock.data_creazione = datetime.utcnow()
        task_mock.is_completed = False
        task_mock.is_overdue = False
        task_mock.days_until_deadline = 7
        task_mock.priority_color = "info"
        task_mock.status_color = "bg-secondary"
        task_mock.origine_badge_class = "bg-primary"
        task_mock.origine_display = "🤖 AI"
        
        # Test creazione da TaskAI
        task_read = TaskAIRead.from_task_ai(task_mock)
        self.assertEqual(task_read.id, 1)
        self.assertEqual(task_read.titolo, 'Test Task')
        self.assertEqual(task_read.priorita, 'Medium')
        self.assertEqual(task_read.origine, 'AI')
    
    def test_task_ai_filter_schema(self):
        """Test schema TaskAIFilter."""
        # Test filtro valido
        filter_data = {
            'stato': False,
            'origine': 'AI',
            'sort_by': 'data_creazione',
            'sort_order': 'desc'
        }
        
        task_filter = TaskAIFilter(**filter_data)
        self.assertEqual(task_filter.stato, False)
        self.assertEqual(task_filter.origine, 'AI')
        
        # Test validazione origine non valida
        with self.assertRaises(ValueError):
            TaskAIFilter(origine='Invalid')
        
        # Test validazione sort_by non valido
        with self.assertRaises(ValueError):
            TaskAIFilter(sort_by='Invalid')
    
    def test_task_ai_stats_schema(self):
        """Test schema TaskAIStats."""
        # Mock dei task
        tasks_mock = [MagicMock(), MagicMock()]
        tasks_mock[0].is_completed = True
        tasks_mock[0].is_overdue = False
        tasks_mock[0].origine = OrigineTask.AI
        tasks_mock[0].priorita = PrioritaTask.MEDIUM
        
        tasks_mock[1].is_completed = False
        tasks_mock[1].is_overdue = True
        tasks_mock[1].origine = OrigineTask.DIARIO
        tasks_mock[1].priorita = PrioritaTask.HIGH
        
        # Test calcolo statistiche
        stats = TaskAIStats.calculate_from_tasks(tasks_mock)
        self.assertEqual(stats.total_tasks, 2)
        self.assertEqual(stats.completed_tasks, 1)
        self.assertEqual(stats.pending_tasks, 1)
        self.assertEqual(stats.overdue_tasks, 1)
        self.assertEqual(stats.completion_rate, 50.0)


class TestTaskAIValidation(unittest.TestCase):
    """Test per le funzioni di validazione."""
    
    def test_validate_task_data(self):
        """Test funzione validate_task_data."""
        from schemas.task_schemas import validate_task_data
        
        # Test validazione dati validi
        data = {
            'titolo': 'Test Task',
            'descrizione': 'Test Description',
            'priorita': 'Medium',
            'origine': 'AI'
        }
        
        validated = validate_task_data(data)
        self.assertEqual(validated['titolo'], 'Test Task')
        self.assertEqual(validated['priorita'], 'Medium')
        
        # Test validazione titolo obbligatorio
        with self.assertRaises(ValueError):
            validate_task_data({'titolo': ''})
        
        # Test validazione priorità non valida
        with self.assertRaises(ValueError):
            validate_task_data({'titolo': 'Test', 'priorita': 'Invalid'})
    
    def test_serialize_task_ai(self):
        """Test funzione serialize_task_ai."""
        from schemas.task_schemas import serialize_task_ai
        
        # Mock del task AI
        task_mock = MagicMock()
        task_mock.id = 1
        task_mock.titolo = 'Test Task'
        task_mock.descrizione = 'Test Description'
        task_mock.data_scadenza = datetime.utcnow() + timedelta(days=7)
        task_mock.priorita = PrioritaTask.MEDIUM
        task_mock.origine = OrigineTask.AI
        task_mock.stato = False
        task_mock.data_creazione = datetime.utcnow()
        task_mock.is_completed = False
        task_mock.is_overdue = False
        task_mock.days_until_deadline = 7
        task_mock.priority_color = "info"
        task_mock.status_color = "bg-secondary"
        task_mock.origine_badge_class = "bg-primary"
        task_mock.origine_display = "🤖 AI"
        
        # Test serializzazione
        serialized = serialize_task_ai(task_mock)
        self.assertEqual(serialized['id'], 1)
        self.assertEqual(serialized['titolo'], 'Test Task')
        self.assertEqual(serialized['priorita'], 'Medium')
        self.assertEqual(serialized['origine'], 'AI')
        self.assertFalse(serialized['stato'])


if __name__ == '__main__':
    # Esegui i test
    unittest.main(verbosity=2) 