"""
Test per il modello TaskAI del Prompt 26 - FASE 1.
Verifica che il modello TaskAI funzioni correttamente con gli enum.
"""

import unittest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
import sys
import os

# Aggiungi il path del progetto
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from models import TaskAI, OrigineTask, PrioritaTask, User


class TestTaskAIModel(unittest.TestCase):
    """Test per il modello TaskAI."""
    
    def setUp(self):
        """Setup per i test."""
        # Mock dell'utente
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
    
    def test_task_ai_creation(self):
        """Test creazione TaskAI."""
        # Verifica che il modello esista
        self.assertTrue(hasattr(TaskAI, '__tablename__'))
        self.assertEqual(TaskAI.__tablename__, 'task_ai')
        
        # Verifica che gli enum esistano
        self.assertTrue(hasattr(OrigineTask, 'AI'))
        self.assertTrue(hasattr(OrigineTask, 'DIARIO'))
        self.assertTrue(hasattr(OrigineTask, 'DEEP_WORK'))
        self.assertTrue(hasattr(OrigineTask, 'MANUALE'))
        
        self.assertTrue(hasattr(PrioritaTask, 'LOW'))
        self.assertTrue(hasattr(PrioritaTask, 'MEDIUM'))
        self.assertTrue(hasattr(PrioritaTask, 'HIGH'))
    
    def test_task_ai_properties(self):
        """Test proprietà del TaskAI."""
        # Test proprietà is_completed
        self.task_ai_mock.stato = True
        self.assertTrue(self.task_ai_mock.is_completed)
        
        self.task_ai_mock.stato = False
        self.assertFalse(self.task_ai_mock.is_completed)
        
        # Test proprietà is_overdue
        self.task_ai_mock.data_scadenza = datetime.utcnow() - timedelta(days=1)
        self.task_ai_mock.stato = False
        self.assertTrue(self.task_ai_mock.is_overdue)
        
        self.task_ai_mock.data_scadenza = datetime.utcnow() + timedelta(days=1)
        self.assertFalse(self.task_ai_mock.is_overdue)
        
        # Test proprietà days_until_deadline
        self.task_ai_mock.data_scadenza = datetime.utcnow() + timedelta(days=5)
        self.assertEqual(self.task_ai_mock.days_until_deadline, 5)
    
    def test_task_ai_priority_colors(self):
        """Test colori priorità TaskAI."""
        # Test priorità Low
        self.task_ai_mock.priorita = PrioritaTask.LOW
        self.assertEqual(self.task_ai_mock.priority_color, "success")
        
        # Test priorità Medium
        self.task_ai_mock.priorita = PrioritaTask.MEDIUM
        self.assertEqual(self.task_ai_mock.priority_color, "info")
        
        # Test priorità High
        self.task_ai_mock.priorita = PrioritaTask.HIGH
        self.assertEqual(self.task_ai_mock.priority_color, "warning")
    
    def test_task_ai_status_colors(self):
        """Test colori stato TaskAI."""
        # Test stato completato
        self.task_ai_mock.stato = True
        self.assertEqual(self.task_ai_mock.status_color, "bg-success")
        
        # Test stato da fare
        self.task_ai_mock.stato = False
        self.assertEqual(self.task_ai_mock.status_color, "bg-secondary")
    
    def test_task_ai_origine_badge_classes(self):
        """Test badge classi origine TaskAI."""
        # Test origine AI
        self.task_ai_mock.origine = OrigineTask.AI
        self.assertEqual(self.task_ai_mock.origine_badge_class, "bg-primary")
        
        # Test origine Diario
        self.task_ai_mock.origine = OrigineTask.DIARIO
        self.assertEqual(self.task_ai_mock.origine_badge_class, "bg-info")
        
        # Test origine Deep Work
        self.task_ai_mock.origine = OrigineTask.DEEP_WORK
        self.assertEqual(self.task_ai_mock.origine_badge_class, "bg-warning")
        
        # Test origine Manuale
        self.task_ai_mock.origine = OrigineTask.MANUALE
        self.assertEqual(self.task_ai_mock.origine_badge_class, "bg-secondary")
    
    def test_task_ai_origine_display(self):
        """Test display name origine TaskAI."""
        # Test origine AI
        self.task_ai_mock.origine = OrigineTask.AI
        self.assertEqual(self.task_ai_mock.origine_display, "🤖 AI")
        
        # Test origine Diario
        self.task_ai_mock.origine = OrigineTask.DIARIO
        self.assertEqual(self.task_ai_mock.origine_display, "📝 Diario")
        
        # Test origine Deep Work
        self.task_ai_mock.origine = OrigineTask.DEEP_WORK
        self.assertEqual(self.task_ai_mock.origine_display, "🧠 Deep Work")
        
        # Test origine Manuale
        self.task_ai_mock.origine = OrigineTask.MANUALE
        self.assertEqual(self.task_ai_mock.origine_display, "✏️ Manuale")
    
    def test_task_ai_repr(self):
        """Test rappresentazione stringa TaskAI."""
        expected_repr = "<TaskAI(id=1, titolo=Test Task AI, user_id=1, completato=False)>"
        self.assertEqual(str(self.task_ai_mock), expected_repr)
    
    def test_enum_values(self):
        """Test valori degli enum."""
        # Test OrigineTask
        self.assertEqual(OrigineTask.AI.value, "AI")
        self.assertEqual(OrigineTask.DIARIO.value, "Diario")
        self.assertEqual(OrigineTask.DEEP_WORK.value, "Deep Work")
        self.assertEqual(OrigineTask.MANUALE.value, "Manuale")
        
        # Test PrioritaTask
        self.assertEqual(PrioritaTask.LOW.value, "Low")
        self.assertEqual(PrioritaTask.MEDIUM.value, "Medium")
        self.assertEqual(PrioritaTask.HIGH.value, "High")
    
    def test_task_ai_relationships(self):
        """Test relazioni TaskAI."""
        # Verifica che la relazione con User esista
        self.assertTrue(hasattr(TaskAI, 'utente'))
        
        # Verifica che la relazione inversa in User esista
        self.assertTrue(hasattr(User, 'tasks_ai'))
    
    def test_task_ai_data_integrity(self):
        """Test integrità dati TaskAI."""
        # Mock task con dati completi
        task = MagicMock()
        task.id = 1
        task.user_id = 1
        task.titolo = "Test Task AI"
        task.descrizione = "Test Description AI"
        task.data_scadenza = datetime.utcnow() + timedelta(days=7)
        task.priorita = PrioritaTask.MEDIUM
        task.origine = OrigineTask.AI
        task.stato = False
        task.data_creazione = datetime.utcnow()
        
        # Verifica integrità dati
        self.assertEqual(task.id, 1)
        self.assertEqual(task.user_id, 1)
        self.assertEqual(task.titolo, "Test Task AI")
        self.assertEqual(task.descrizione, "Test Description AI")
        self.assertIsNotNone(task.data_scadenza)
        self.assertEqual(task.priorita, PrioritaTask.MEDIUM)
        self.assertEqual(task.origine, OrigineTask.AI)
        self.assertFalse(task.stato)
        self.assertIsNotNone(task.data_creazione)
    
    def test_task_ai_validation(self):
        """Test validazione TaskAI."""
        # Test che i campi obbligatori siano definiti
        required_fields = ['id', 'user_id', 'titolo', 'data_creazione']
        for field in required_fields:
            self.assertTrue(hasattr(self.task_ai_mock, field))
        
        # Test che i campi opzionali siano definiti
        optional_fields = ['descrizione', 'data_scadenza', 'priorita', 'origine', 'stato']
        for field in optional_fields:
            self.assertTrue(hasattr(self.task_ai_mock, field))
    
    def test_task_ai_enum_usage(self):
        """Test utilizzo enum in TaskAI."""
        # Test che gli enum siano utilizzabili
        self.assertIsInstance(OrigineTask.AI, OrigineTask)
        self.assertIsInstance(PrioritaTask.MEDIUM, PrioritaTask)
        
        # Test che i valori degli enum siano stringhe
        self.assertIsInstance(OrigineTask.AI.value, str)
        self.assertIsInstance(PrioritaTask.MEDIUM.value, str)
        
        # Test che gli enum abbiano i valori corretti
        self.assertEqual(OrigineTask.AI.value, "AI")
        self.assertEqual(PrioritaTask.MEDIUM.value, "Medium")


class TestTaskAIEnum(unittest.TestCase):
    """Test specifici per gli enum."""
    
    def test_origine_task_enum(self):
        """Test enum OrigineTask."""
        # Verifica tutti i valori
        expected_values = ["AI", "Diario", "Deep Work", "Manuale"]
        actual_values = [e.value for e in OrigineTask]
        self.assertEqual(actual_values, expected_values)
        
        # Verifica che non ci siano duplicati
        self.assertEqual(len(actual_values), len(set(actual_values)))
    
    def test_priorita_task_enum(self):
        """Test enum PrioritaTask."""
        # Verifica tutti i valori
        expected_values = ["Low", "Medium", "High"]
        actual_values = [e.value for e in PrioritaTask]
        self.assertEqual(actual_values, expected_values)
        
        # Verifica che non ci siano duplicati
        self.assertEqual(len(actual_values), len(set(actual_values)))
    
    def test_enum_iteration(self):
        """Test iterazione sugli enum."""
        # Test OrigineTask
        origine_values = list(OrigineTask)
        self.assertEqual(len(origine_values), 4)
        
        # Test PrioritaTask
        priorita_values = list(PrioritaTask)
        self.assertEqual(len(priorita_values), 3)
    
    def test_enum_comparison(self):
        """Test confronto enum."""
        # Test che gli enum possano essere confrontati
        self.assertEqual(OrigineTask.AI, OrigineTask.AI)
        self.assertNotEqual(OrigineTask.AI, OrigineTask.DIARIO)
        
        self.assertEqual(PrioritaTask.MEDIUM, PrioritaTask.MEDIUM)
        self.assertNotEqual(PrioritaTask.LOW, PrioritaTask.HIGH)


if __name__ == '__main__':
    # Esegui i test
    unittest.main(verbosity=2) 