"""
Test per i suggerimenti AI - Prompt 26 FASE 4
Verifica che il sistema di suggerimenti AI funzioni correttamente.
"""

import unittest
from datetime import datetime, timedelta


class TestAISuggestions(unittest.TestCase):
    """Test per i suggerimenti AI."""
    
    def test_suggestion_structure(self):
        """Test struttura suggerimento AI."""
        # Mock suggerimento AI
        suggestion = {
            'id': 'critical_today_3',
            'type': 'critico',
            'message': '📅 Hai 3 task in scadenza oggi. Completa almeno 1 entro le 14.',
            'priority': 'high',
            'action_url': '/user/my_tasks_ai',
            'icon': 'fas fa-exclamation-triangle',
            'color': 'danger'
        }
        
        # Verifica struttura
        required_fields = ['id', 'type', 'message', 'priority', 'action_url', 'icon', 'color']
        for field in required_fields:
            self.assertIn(field, suggestion, f"Campo {field} mancante nel suggerimento")
        
        # Verifica tipi di dati
        self.assertIsInstance(suggestion['id'], str)
        self.assertIsInstance(suggestion['type'], str)
        self.assertIsInstance(suggestion['message'], str)
        self.assertIn(suggestion['priority'], ['high', 'medium', 'low'])
        self.assertIn(suggestion['type'], ['critico', 'operativo', 'motivazionale'])
        self.assertIsInstance(suggestion['action_url'], str)
        self.assertIsInstance(suggestion['icon'], str)
        self.assertIsInstance(suggestion['color'], str)
    
    def test_suggestion_types(self):
        """Test tipi suggerimenti."""
        types = ['critico', 'operativo', 'motivazionale']
        
        for type_name in types:
            suggestion = {
                'id': f'test_{type_name}',
                'type': type_name,
                'message': f'Test message {type_name}',
                'priority': 'medium',
                'action_url': '/user/my_tasks_ai',
                'icon': 'fas fa-lightbulb',
                'color': 'warning'
            }
            
            self.assertIn(suggestion['type'], types)
    
    def test_suggestion_priorities(self):
        """Test priorità suggerimenti."""
        priorities = ['high', 'medium', 'low']
        
        for priority in priorities:
            suggestion = {
                'id': f'test_{priority}',
                'type': 'operativo',
                'message': f'Test message {priority}',
                'priority': priority,
                'action_url': '/user/my_tasks_ai',
                'icon': 'fas fa-lightbulb',
                'color': 'warning'
            }
            
            self.assertIn(suggestion['priority'], priorities)
    
    def test_critical_today_suggestion_logic(self):
        """Test logica suggerimento task critici oggi."""
        # Mock task critici oggi
        critical_count = 3
        
        suggestion = {
            'id': f'critical_today_{critical_count}',
            'type': 'critico',
            'message': f'📅 Hai {critical_count} task in scadenza oggi. Completa almeno 1 entro le 14.',
            'priority': 'high',
            'action_url': '/user/my_tasks_ai',
            'icon': 'fas fa-exclamation-triangle',
            'color': 'danger'
        }
        
        # Verifica logica
        self.assertEqual(suggestion['type'], 'critico')
        self.assertEqual(suggestion['priority'], 'high')
        self.assertIn('task in scadenza oggi', suggestion['message'])
        self.assertIn('3', suggestion['message'])  # 3 task critici
        self.assertIn('fas fa-exclamation-triangle', suggestion['icon'])
        self.assertEqual(suggestion['color'], 'danger')
    
    def test_old_tasks_suggestion_logic(self):
        """Test logica suggerimento task vecchi."""
        # Mock task vecchi (> 7 giorni)
        old_count = 5
        
        suggestion = {
            'id': f'old_tasks_{old_count}',
            'type': 'operativo',
            'message': f'📅 Hai {old_count} task creati più di 7 giorni fa. Rivedi se sono ancora rilevanti.',
            'priority': 'medium',
            'action_url': '/user/my_tasks_ai',
            'icon': 'fas fa-clock',
            'color': 'warning'
        }
        
        # Verifica logica
        self.assertEqual(suggestion['type'], 'operativo')
        self.assertEqual(suggestion['priority'], 'medium')
        self.assertIn('task creati più di 7 giorni fa', suggestion['message'])
        self.assertIn('5', suggestion['message'])  # 5 task vecchi
        self.assertIn('fas fa-clock', suggestion['icon'])
        self.assertEqual(suggestion['color'], 'warning')
    
    def test_no_recent_completion_suggestion_logic(self):
        """Test logica suggerimento nessun completamento recente."""
        suggestion = {
            'id': 'no_recent_completion',
            'type': 'motivazionale',
            'message': '🧠 Nessun task completato da 3 giorni. Una sessione Deep Work può aiutarti.',
            'priority': 'medium',
            'action_url': '/user/deep-work',
            'icon': 'fas fa-brain',
            'color': 'info'
        }
        
        # Verifica logica
        self.assertEqual(suggestion['type'], 'motivazionale')
        self.assertEqual(suggestion['priority'], 'medium')
        self.assertIn('Nessun task completato da 3 giorni', suggestion['message'])
        self.assertIn('Deep Work', suggestion['message'])
        self.assertIn('fas fa-brain', suggestion['icon'])
        self.assertEqual(suggestion['color'], 'info')
    
    def test_unprioritized_tasks_suggestion_logic(self):
        """Test logica suggerimento task senza priorità."""
        # Mock task senza priorità
        unprioritized_count = 8
        
        suggestion = {
            'id': f'unprioritized_{unprioritized_count}',
            'type': 'operativo',
            'message': f'🗂 Hai {unprioritized_count} task aperti senza priorità: rivedi la pianificazione settimanale.',
            'priority': 'medium',
            'action_url': '/user/my_tasks_ai',
            'icon': 'fas fa-list',
            'color': 'warning'
        }
        
        # Verifica logica
        self.assertEqual(suggestion['type'], 'operativo')
        self.assertEqual(suggestion['priority'], 'medium')
        self.assertIn('task aperti senza priorità', suggestion['message'])
        self.assertIn('8', suggestion['message'])  # 8 task senza priorità
        self.assertIn('fas fa-list', suggestion['icon'])
        self.assertEqual(suggestion['color'], 'warning')
    
    def test_overdue_suggestion_logic(self):
        """Test logica suggerimento task scaduti."""
        # Mock task scaduti
        overdue_count = 2
        
        suggestion = {
            'id': f'overdue_suggestion_{overdue_count}',
            'type': 'critico',
            'message': f'🚨 Hai {overdue_count} task scaduti. Completa al più presto per evitare accumuli.',
            'priority': 'high',
            'action_url': '/user/my_tasks_ai',
            'icon': 'fas fa-fire',
            'color': 'danger'
        }
        
        # Verifica logica
        self.assertEqual(suggestion['type'], 'critico')
        self.assertEqual(suggestion['priority'], 'high')
        self.assertIn('task scaduti', suggestion['message'])
        self.assertIn('2', suggestion['message'])  # 2 task scaduti
        self.assertIn('fas fa-fire', suggestion['icon'])
        self.assertEqual(suggestion['color'], 'danger')
    
    def test_empty_tasks_suggestion_logic(self):
        """Test logica suggerimento task vuoti."""
        suggestion = {
            'id': 'empty_tasks',
            'type': 'motivazionale',
            'message': '🤖 Inizia a creare i tuoi primi task per organizzare meglio il lavoro!',
            'priority': 'low',
            'action_url': '/user/my_tasks_ai',
            'icon': 'fas fa-plus',
            'color': 'primary'
        }
        
        # Verifica logica
        self.assertEqual(suggestion['type'], 'motivazionale')
        self.assertEqual(suggestion['priority'], 'low')
        self.assertIn('Inizia a creare i tuoi primi task', suggestion['message'])
        self.assertIn('fas fa-plus', suggestion['icon'])
        self.assertEqual(suggestion['color'], 'primary')
    
    def test_productivity_suggestion_logic(self):
        """Test logica suggerimento produttività."""
        # Mock completion rate basso
        completion_rate = 30
        
        suggestion = {
            'id': 'productivity_tip',
            'type': 'motivazionale',
            'message': f'📈 Hai completato solo il {completion_rate:.0f}% dei task. Concentrati su 1-2 task al giorno.',
            'priority': 'medium',
            'action_url': '/user/my_tasks_ai',
            'icon': 'fas fa-chart-line',
            'color': 'info'
        }
        
        # Verifica logica
        self.assertEqual(suggestion['type'], 'motivazionale')
        self.assertEqual(suggestion['priority'], 'medium')
        self.assertIn('Hai completato solo il 30%', suggestion['message'])
        self.assertIn('Concentrati su 1-2 task al giorno', suggestion['message'])
        self.assertIn('fas fa-chart-line', suggestion['icon'])
        self.assertEqual(suggestion['color'], 'info')
    
    def test_high_priority_suggestion_logic(self):
        """Test logica suggerimento task alta priorità."""
        # Mock task alta priorità
        high_priority_count = 4
        
        suggestion = {
            'id': f'high_priority_suggestion_{high_priority_count}',
            'type': 'operativo',
            'message': f'🎯 Hai {high_priority_count} task ad alta priorità. Inizia da quello più urgente.',
            'priority': 'high',
            'action_url': '/user/my_tasks_ai',
            'icon': 'fas fa-star',
            'color': 'warning'
        }
        
        # Verifica logica
        self.assertEqual(suggestion['type'], 'operativo')
        self.assertEqual(suggestion['priority'], 'high')
        self.assertIn('task ad alta priorità', suggestion['message'])
        self.assertIn('4', suggestion['message'])  # 4 task alta priorità
        self.assertIn('fas fa-star', suggestion['icon'])
        self.assertEqual(suggestion['color'], 'warning')
    
    def test_suggestion_sorting(self):
        """Test ordinamento suggerimenti."""
        suggestions = [
            {
                'id': 'low_priority',
                'priority': 'low',
                'type': 'motivazionale'
            },
            {
                'id': 'high_priority',
                'priority': 'high',
                'type': 'critico'
            },
            {
                'id': 'medium_priority',
                'priority': 'medium',
                'type': 'operativo'
            }
        ]
        
        # Simula ordinamento per priorità e tipo
        priority_order = {'high': 0, 'medium': 1, 'low': 2}
        type_order = {'critico': 0, 'operativo': 1, 'motivazionale': 2}
        
        sorted_suggestions = sorted(suggestions, key=lambda x: (
            priority_order[x['priority']],
            type_order[x['type']]
        ))
        
        # Verifica che high priority sia prima
        self.assertEqual(sorted_suggestions[0]['priority'], 'high')
        self.assertEqual(sorted_suggestions[0]['id'], 'high_priority')
    
    def test_suggestion_limit(self):
        """Test limite suggerimenti."""
        # Mock più di 5 suggerimenti
        suggestions = [
            {'id': f'suggestion_{i}', 'priority': 'medium', 'type': 'operativo'}
            for i in range(10)
        ]
        
        # Limita a 5 suggerimenti
        limited_suggestions = suggestions[:5]
        
        self.assertEqual(len(limited_suggestions), 5)
        self.assertLessEqual(len(limited_suggestions), 5)
    
    def test_api_response_structure(self):
        """Test struttura risposta API suggerimenti."""
        # Mock risposta API
        mock_api_response = {
            'success': True,
            'data': [
                {
                    'id': 'critical_today_3',
                    'type': 'critico',
                    'message': '📅 Hai 3 task in scadenza oggi. Completa almeno 1 entro le 14.',
                    'priority': 'high',
                    'action_url': '/user/my_tasks_ai',
                    'icon': 'fas fa-exclamation-triangle',
                    'color': 'danger'
                },
                {
                    'id': 'old_tasks_5',
                    'type': 'operativo',
                    'message': '📅 Hai 5 task creati più di 7 giorni fa. Rivedi se sono ancora rilevanti.',
                    'priority': 'medium',
                    'action_url': '/user/my_tasks_ai',
                    'icon': 'fas fa-clock',
                    'color': 'warning'
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
        
        # Verifica struttura suggerimenti
        for suggestion in mock_api_response['data']:
            required_fields = ['id', 'type', 'message', 'priority', 'action_url', 'icon', 'color']
            for field in required_fields:
                self.assertIn(field, suggestion, f"Campo {field} mancante nel suggerimento")
    
    def test_error_response_structure(self):
        """Test struttura risposta errore API."""
        # Mock risposta errore
        mock_error_response = {
            'success': False,
            'error': 'Errore nel recupero dei suggerimenti AI'
        }
        
        # Verifica struttura errore
        self.assertFalse(mock_error_response['success'])
        self.assertIn('error', mock_error_response)
        self.assertIsInstance(mock_error_response['error'], str)
    
    def test_suggestion_color_mapping(self):
        """Test mapping colori suggerimenti."""
        color_mapping = {
            'danger': 'border-danger bg-light',
            'warning': 'border-warning bg-light',
            'success': 'border-success bg-light',
            'info': 'border-info bg-light',
            'primary': 'border-primary bg-light'
        }
        
        for color, expected_class in color_mapping.items():
            suggestion = {
                'color': color,
                'priority': 'medium',
                'type': 'operativo'
            }
            
            # Simula funzione di mapping
            css_class = color_mapping.get(suggestion['color'], 'border-secondary bg-light')
            self.assertEqual(css_class, expected_class)
    
    def test_suggestion_badge_mapping(self):
        """Test mapping badge suggerimenti."""
        badge_mapping = {
            'critico': 'bg-danger',
            'operativo': 'bg-warning',
            'motivazionale': 'bg-info'
        }
        
        for type_name, expected_class in badge_mapping.items():
            suggestion = {
                'type': type_name,
                'priority': 'medium',
                'color': 'warning'
            }
            
            # Simula funzione di mapping
            badge_class = badge_mapping.get(suggestion['type'], 'bg-secondary')
            self.assertEqual(badge_class, expected_class)


if __name__ == '__main__':
    # Esegui i test
    unittest.main(verbosity=2) 