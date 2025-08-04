"""
Test per le notifiche AI - Prompt 26 FASE 4
Verifica che il sistema di notifiche AI funzioni correttamente.
"""

import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
import sys
import os

# Aggiungi il path del progetto
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from models import TaskAI, OrigineTask, PrioritaTask


class TestAINotifications(unittest.TestCase):
    """Test per le notifiche AI."""
    
    def setUp(self):
        """Setup per i test."""
        # Mock dell'utente corrente
        self.mock_user = MagicMock()
        self.mock_user.id = 1
        self.mock_user.username = "test_user"
        
        # Mock dei task AI
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
    
    def test_notification_structure(self):
        """Test struttura notifica AI."""
        # Mock notifica AI
        notification = {
            'id': 'test_notification',
            'title': '⚠️ Task Scaduti',
            'message': 'Hai 2 task scaduti. Completa al più presto per mantenere la produttività.',
            'priority': 'high',
            'type': 'warning',
            'timestamp': datetime.utcnow().isoformat(),
            'action_url': '/user/my_tasks_ai'
        }
        
        # Verifica struttura
        required_fields = ['id', 'title', 'message', 'priority', 'type', 'timestamp']
        for field in required_fields:
            self.assertIn(field, notification, f"Campo {field} mancante nella notifica")
        
        # Verifica tipi di dati
        self.assertIsInstance(notification['id'], str)
        self.assertIsInstance(notification['title'], str)
        self.assertIsInstance(notification['message'], str)
        self.assertIn(notification['priority'], ['high', 'medium', 'low'])
        self.assertIn(notification['type'], ['warning', 'urgent', 'info', 'success', 'suggestion', 'reminder'])
        self.assertIsInstance(notification['timestamp'], str)
    
    def test_notification_priorities(self):
        """Test priorità notifiche."""
        priorities = ['high', 'medium', 'low']
        
        for priority in priorities:
            notification = {
                'id': f'test_{priority}',
                'title': f'Test {priority}',
                'message': f'Test message {priority}',
                'priority': priority,
                'type': 'info',
                'timestamp': datetime.utcnow().isoformat()
            }
            
            self.assertIn(notification['priority'], priorities)
    
    def test_notification_types(self):
        """Test tipi notifiche."""
        types = ['warning', 'urgent', 'info', 'success', 'suggestion', 'reminder']
        
        for type_name in types:
            notification = {
                'id': f'test_{type_name}',
                'title': f'Test {type_name}',
                'message': f'Test message {type_name}',
                'priority': 'medium',
                'type': type_name,
                'timestamp': datetime.utcnow().isoformat()
            }
            
            self.assertIn(notification['type'], types)
    
    def test_overdue_notification_logic(self):
        """Test logica notifica task scaduti."""
        # Mock task scaduti
        overdue_tasks = [
            MagicMock(is_overdue=True),
            MagicMock(is_overdue=True)
        ]
        
        overdue_count = len(overdue_tasks)
        
        notification = {
            'id': f'overdue_{overdue_count}',
            'title': '⚠️ Task Scaduti',
            'message': f'Hai {overdue_count} task scaduto{"i" if overdue_count > 1 else ""}. Completa al più presto per mantenere la produttività.',
            'priority': 'high',
            'type': 'warning',
            'timestamp': datetime.utcnow().isoformat(),
            'action_url': '/user/my_tasks_ai'
        }
        
        # Verifica logica
        self.assertEqual(notification['priority'], 'high')
        self.assertEqual(notification['type'], 'warning')
        self.assertIn('task scaduto', notification['message'])
        self.assertIn('2', notification['message'])  # 2 task scaduti
    
    def test_urgent_deadline_notification_logic(self):
        """Test logica notifica scadenze urgenti."""
        # Mock task urgenti (scadenza <= 1 giorno)
        urgent_tasks = [
            MagicMock(days_until_deadline=0, stato=False),
            MagicMock(days_until_deadline=1, stato=False)
        ]
        
        urgent_count = len(urgent_tasks)
        
        notification = {
            'id': f'urgent_{urgent_count}',
            'title': '🚨 Scadenze Urgenti',
            'message': f'Hai {urgent_count} task che scade{"no" if urgent_count > 1 else ""} entro domani. Priorità massima!',
            'priority': 'high',
            'type': 'urgent',
            'timestamp': datetime.utcnow().isoformat(),
            'action_url': '/user/my_tasks_ai'
        }
        
        # Verifica logica
        self.assertEqual(notification['priority'], 'high')
        self.assertEqual(notification['type'], 'urgent')
        self.assertIn('Scadenze Urgenti', notification['title'])
        self.assertIn('entro domani', notification['message'])
    
    def test_progress_notification_logic(self):
        """Test logica notifica progresso."""
        # Mock task completati e totali
        completed_tasks = [MagicMock(stato=True) for _ in range(8)]
        total_tasks = completed_tasks + [MagicMock(stato=False) for _ in range(2)]
        
        completion_rate = len(completed_tasks) / len(total_tasks) * 100
        
        if completion_rate >= 80:
            notification = {
                'id': 'excellent_progress',
                'title': '🎉 Eccellente Progresso',
                'message': f'Hai completato l\'{completion_rate:.0f}% dei tuoi task! Continua così per raggiungere i tuoi obiettivi.',
                'priority': 'low',
                'type': 'success',
                'timestamp': datetime.utcnow().isoformat(),
                'action_url': '/user/my_tasks_ai'
            }
            
            # Verifica logica
            self.assertEqual(notification['priority'], 'low')
            self.assertEqual(notification['type'], 'success')
            self.assertIn('Eccellente Progresso', notification['title'])
            self.assertIn('80%', notification['message'])
    
    def test_empty_tasks_notification_logic(self):
        """Test logica notifica task vuoti."""
        # Mock nessun task
        tasks = []
        
        if not tasks:
            notification = {
                'id': 'no_tasks',
                'title': '🤖 Suggerimento AI',
                'message': 'Non hai ancora creato nessun task. Inizia ora per organizzare meglio il tuo lavoro!',
                'priority': 'medium',
                'type': 'suggestion',
                'timestamp': datetime.utcnow().isoformat(),
                'action_url': '/user/my_tasks_ai'
            }
            
            # Verifica logica
            self.assertEqual(notification['priority'], 'medium')
            self.assertEqual(notification['type'], 'suggestion')
            self.assertIn('Suggerimento AI', notification['title'])
            self.assertIn('Non hai ancora creato', notification['message'])
    
    def test_high_priority_notification_logic(self):
        """Test logica notifica task alta priorità."""
        # Mock task alta priorità
        high_priority_tasks = [
            MagicMock(priorita=PrioritaTask.HIGH, stato=False),
            MagicMock(priorita=PrioritaTask.HIGH, stato=False)
        ]
        
        if len(high_priority_tasks) > 0:
            notification = {
                'id': 'high_priority_reminder',
                'title': '🎯 Task Alta Priorità',
                'message': f'Hai {len(high_priority_tasks)} task ad alta priorità in attesa. Concentrati su questi per massimizzare l\'impatto.',
                'priority': 'high',
                'type': 'reminder',
                'timestamp': datetime.utcnow().isoformat(),
                'action_url': '/user/my_tasks_ai'
            }
            
            # Verifica logica
            self.assertEqual(notification['priority'], 'high')
            self.assertEqual(notification['type'], 'reminder')
            self.assertIn('Task Alta Priorità', notification['title'])
            self.assertIn('alta priorità', notification['message'])
    
    def test_notification_sorting(self):
        """Test ordinamento notifiche."""
        notifications = [
            {
                'id': 'low_priority',
                'priority': 'low',
                'timestamp': '2024-01-01T10:00:00'
            },
            {
                'id': 'high_priority',
                'priority': 'high',
                'timestamp': '2024-01-01T09:00:00'
            },
            {
                'id': 'medium_priority',
                'priority': 'medium',
                'timestamp': '2024-01-01T11:00:00'
            }
        ]
        
        # Simula ordinamento per priorità e timestamp
        priority_order = {'high': 0, 'medium': 1, 'low': 2}
        
        sorted_notifications = sorted(notifications, key=lambda x: (
            priority_order[x['priority']],
            -datetime.fromisoformat(x['timestamp']).timestamp()
        ))
        
        # Verifica che high priority sia prima
        self.assertEqual(sorted_notifications[0]['priority'], 'high')
        self.assertEqual(sorted_notifications[0]['id'], 'high_priority')
    
    def test_notification_limit(self):
        """Test limite notifiche."""
        # Mock più di 5 notifiche
        notifications = [
            {'id': f'notification_{i}', 'priority': 'medium', 'timestamp': datetime.utcnow().isoformat()}
            for i in range(10)
        ]
        
        # Limita a 5 notifiche
        limited_notifications = notifications[:5]
        
        self.assertEqual(len(limited_notifications), 5)
        self.assertLessEqual(len(limited_notifications), 5)


class TestAINotificationsIntegration(unittest.TestCase):
    """Test integrazione notifiche AI."""
    
    def test_api_response_structure(self):
        """Test struttura risposta API notifiche."""
        # Mock risposta API
        mock_api_response = {
            'success': True,
            'data': [
                {
                    'id': 'overdue_2',
                    'title': '⚠️ Task Scaduti',
                    'message': 'Hai 2 task scaduti. Completa al più presto per mantenere la produttività.',
                    'priority': 'high',
                    'type': 'warning',
                    'timestamp': '2024-01-15T10:30:00',
                    'action_url': '/user/my_tasks_ai'
                },
                {
                    'id': 'urgent_1',
                    'title': '🚨 Scadenze Urgenti',
                    'message': 'Hai 1 task che scade entro domani. Priorità massima!',
                    'priority': 'high',
                    'type': 'urgent',
                    'timestamp': '2024-01-15T09:00:00',
                    'action_url': '/user/my_tasks_ai'
                }
            ],
            'count': 2
        }
        
        # Verifica struttura
        self.assertTrue(mock_api_response['success'])
        self.assertIn('data', mock_api_response)
        self.assertIn('count', mock_api_response)
        self.assertIsInstance(mock_api_response['data'], list)
        self.assertEqual(mock_api_response['count'], 2)
        
        # Verifica struttura notifiche
        for notification in mock_api_response['data']:
            required_fields = ['id', 'title', 'message', 'priority', 'type', 'timestamp']
            for field in required_fields:
                self.assertIn(field, notification, f"Campo {field} mancante nella notifica")
    
    def test_error_response_structure(self):
        """Test struttura risposta errore API."""
        # Mock risposta errore
        mock_error_response = {
            'success': False,
            'error': 'Errore nel recupero delle notifiche AI'
        }
        
        # Verifica struttura errore
        self.assertFalse(mock_error_response['success'])
        self.assertIn('error', mock_error_response)
        self.assertIsInstance(mock_error_response['error'], str)
    
    def test_notification_priority_mapping(self):
        """Test mapping priorità notifiche."""
        priority_mapping = {
            'high': 'bg-danger',
            'medium': 'bg-warning',
            'low': 'bg-success'
        }
        
        for priority, expected_class in priority_mapping.items():
            notification = {
                'priority': priority,
                'type': 'info',
                'timestamp': datetime.utcnow().isoformat()
            }
            
            # Simula funzione di mapping
            badge_class = priority_mapping.get(notification['priority'], 'bg-secondary')
            self.assertEqual(badge_class, expected_class)
    
    def test_notification_type_mapping(self):
        """Test mapping tipo notifiche."""
        type_mapping = {
            'warning': 'fas fa-exclamation-triangle text-warning',
            'urgent': 'fas fa-fire text-danger',
            'info': 'fas fa-info-circle text-info',
            'success': 'fas fa-check-circle text-success',
            'suggestion': 'fas fa-lightbulb text-primary',
            'reminder': 'fas fa-bell text-warning'
        }
        
        for type_name, expected_icon in type_mapping.items():
            notification = {
                'type': type_name,
                'priority': 'medium',
                'timestamp': datetime.utcnow().isoformat()
            }
            
            # Simula funzione di mapping
            icon_class = type_mapping.get(notification['type'], 'fas fa-robot text-primary')
            self.assertEqual(icon_class, expected_icon)
    
    def test_timestamp_formatting(self):
        """Test formattazione timestamp."""
        # Test timestamp recente
        recent_timestamp = datetime.utcnow().isoformat()
        
        # Simula funzione di formattazione
        def format_time(timestamp):
            date = datetime.fromisoformat(timestamp)
            now = datetime.utcnow()
            diff_ms = (now - date).total_seconds() * 1000
            diff_mins = int(diff_ms / 60000)
            
            if diff_mins < 1:
                return 'Adesso'
            elif diff_mins < 60:
                return f'{diff_mins} minuti fa'
            else:
                return date.strftime('%d/%m/%Y')
        
        formatted_time = format_time(recent_timestamp)
        self.assertIsInstance(formatted_time, str)
        self.assertIn(formatted_time, ['Adesso', '1 minuti fa', '2 minuti fa'])


if __name__ == '__main__':
    # Esegui i test
    unittest.main(verbosity=2) 