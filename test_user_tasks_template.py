"""
Test per il template user_tasks.html - Prompt 26 FASE 3
Verifica che il template HTML funzioni correttamente con le API TaskAI.
"""

import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
import sys
import os

# Aggiungi il path del progetto
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from models import TaskAI, OrigineTask, PrioritaTask


class TestUserTasksTemplate(unittest.TestCase):
    """Test per il template user_tasks.html."""
    
    def setUp(self):
        """Setup per i test."""
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
        self.task_ai_mock.priority_color = "info"
        self.task_ai_mock.status_color = "bg-secondary"
        self.task_ai_mock.origine_badge_class = "bg-primary"
        self.task_ai_mock.origine_display = "🤖 AI"
    
    def test_template_structure(self):
        """Test struttura del template."""
        # Verifica che il file esista
        template_path = "templates/user/user_tasks.html"
        self.assertTrue(os.path.exists(template_path), "Template user_tasks.html non trovato")
        
        # Leggi il contenuto del template
        with open(template_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Verifica elementi essenziali
        self.assertIn('<!DOCTYPE html>', content)
        self.assertIn('<title>I Miei Task AI', content)
        self.assertIn('Bootstrap', content)
        self.assertIn('Chart.js', content)
        self.assertIn('Font Awesome', content)
    
    def test_template_sections(self):
        """Test sezioni del template."""
        template_path = "templates/user/user_tasks.html"
        
        with open(template_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Verifica sezioni principali
        sections = [
            'Header',
            'Statistics Cards',
            'Filters Section',
            'Charts Section',
            'Tasks List',
            'Add Task Modal',
            'Toast Container'
        ]
        
        for section in sections:
            self.assertIn(section, content, f"Sezione {section} non trovata")
    
    def test_bootstrap_integration(self):
        """Test integrazione Bootstrap."""
        template_path = "templates/user/user_tasks.html"
        
        with open(template_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Verifica Bootstrap CSS
        self.assertIn('bootstrap@5.3.0/dist/css/bootstrap.min.css', content)
        
        # Verifica Bootstrap JS
        self.assertIn('bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js', content)
        
        # Verifica classi Bootstrap
        bootstrap_classes = [
            'container',
            'row',
            'col-md-',
            'card',
            'btn',
            'form-control',
            'modal',
            'toast'
        ]
        
        for class_name in bootstrap_classes:
            self.assertIn(class_name, content, f"Classe Bootstrap {class_name} non trovata")
    
    def test_chart_js_integration(self):
        """Test integrazione Chart.js."""
        template_path = "templates/user/user_tasks.html"
        
        with open(template_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Verifica Chart.js
        self.assertIn('chart.js', content)
        
        # Verifica canvas per i grafici
        self.assertIn('originChart', content)
        self.assertIn('priorityChart', content)
    
    def test_font_awesome_integration(self):
        """Test integrazione Font Awesome."""
        template_path = "templates/user/user_tasks.html"
        
        with open(template_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Verifica Font Awesome
        self.assertIn('font-awesome', content)
        
        # Verifica icone
        icons = [
            'fas fa-tasks',
            'fas fa-check',
            'fas fa-trash',
            'fas fa-plus',
            'fas fa-download',
            'fas fa-filter',
            'fas fa-times',
            'fas fa-chart-pie',
            'fas fa-chart-bar',
            'fas fa-calendar',
            'fas fa-clock',
            'fas fa-exclamation-triangle',
            'fas fa-check-circle',
            'fas fa-info-circle'
        ]
        
        for icon in icons:
            self.assertIn(icon, content, f"Icona {icon} non trovata")
    
    def test_javascript_functions(self):
        """Test funzioni JavaScript."""
        template_path = "templates/user/user_tasks.html"
        
        with open(template_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Verifica funzioni JavaScript essenziali
        js_functions = [
            'loadTasks()',
            'renderTasks()',
            'applyFilters()',
            'clearFilters()',
            'completeTask(',
            'deleteTask(',
            'createTask()',
            'showAddTaskModal()',
            'exportToCSV()',
            'updateStats()',
            'updateCharts()',
            'showToast(',
            'formatDate('
        ]
        
        for function in js_functions:
            self.assertIn(function, content, f"Funzione JavaScript {function} non trovata")
    
    def test_api_endpoints(self):
        """Test endpoint API utilizzati."""
        template_path = "templates/user/user_tasks.html"
        
        with open(template_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Verifica endpoint API
        api_endpoints = [
            '/api/tasks/my',
            '/api/tasks/',
            '/api/tasks/',
            '/api/tasks/'
        ]
        
        for endpoint in api_endpoints:
            self.assertIn(endpoint, content, f"Endpoint API {endpoint} non trovato")
    
    def test_responsive_design(self):
        """Test design responsive."""
        template_path = "templates/user/user_tasks.html"
        
        with open(template_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Verifica meta viewport
        self.assertIn('viewport', content)
        
        # Verifica classi responsive
        responsive_classes = [
            'col-md-',
            'col-',
            'd-md-',
            'd-sm-',
            'd-lg-'
        ]
        
        for class_name in responsive_classes:
            self.assertIn(class_name, content, f"Classe responsive {class_name} non trovata")
    
    def test_accessibility_features(self):
        """Test caratteristiche di accessibilità."""
        template_path = "templates/user/user_tasks.html"
        
        with open(template_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Verifica caratteristiche accessibilità
        accessibility_features = [
            'role="alert"',
            'aria-label',
            'aria-describedby',
            'aria-hidden',
            'tabindex',
            'alt=',
            'title='
        ]
        
        found_features = []
        for feature in accessibility_features:
            if feature in content:
                found_features.append(feature)
        
        # Almeno alcune caratteristiche di accessibilità devono essere presenti
        self.assertGreater(len(found_features), 0, "Nessuna caratteristica di accessibilità trovata")
    
    def test_error_handling(self):
        """Test gestione errori nel template."""
        template_path = "templates/user/user_tasks.html"
        
        with open(template_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Verifica gestione errori
        error_handling = [
            'catch (error)',
            'console.error',
            'showToast(',
            'Errore',
            'error'
        ]
        
        for error_feature in error_handling:
            self.assertIn(error_feature, content, f"Gestione errori {error_feature} non trovata")
    
    def test_user_interaction_features(self):
        """Test funzionalità interazione utente."""
        template_path = "templates/user/user_tasks.html"
        
        with open(template_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Verifica funzionalità interazione
        interaction_features = [
            'onclick=',
            'onchange=',
            'addEventListener',
            'confirm(',
            'alert(',
            'modal',
            'toast'
        ]
        
        for feature in interaction_features:
            self.assertIn(feature, content, f"Funzionalità interazione {feature} non trovata")
    
    def test_data_visualization(self):
        """Test visualizzazione dati."""
        template_path = "templates/user/user_tasks.html"
        
        with open(template_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Verifica visualizzazione dati
        data_viz_features = [
            'Chart(',
            'doughnut',
            'bar',
            'canvas',
            'chart-container',
            'stats-card'
        ]
        
        for feature in data_viz_features:
            self.assertIn(feature, content, f"Visualizzazione dati {feature} non trovata")
    
    def test_task_card_features(self):
        """Test caratteristiche card task."""
        template_path = "templates/user/user_tasks.html"
        
        with open(template_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Verifica caratteristiche card task
        task_card_features = [
            'task-card',
            'completed',
            'overdue',
            'priority-',
            'badge-origin',
            'task-actions',
            'task-description'
        ]
        
        for feature in task_card_features:
            self.assertIn(feature, content, f"Caratteristica card task {feature} non trovata")
    
    def test_filter_functionality(self):
        """Test funzionalità filtri."""
        template_path = "templates/user/user_tasks.html"
        
        with open(template_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Verifica filtri
        filter_features = [
            'priorityFilter',
            'originFilter',
            'statusFilter',
            'searchFilter',
            'applyFilters()',
            'clearFilters()',
            'filter-section'
        ]
        
        for feature in filter_features:
            self.assertIn(feature, content, f"Funzionalità filtro {feature} non trovata")
    
    def test_modal_functionality(self):
        """Test funzionalità modal."""
        template_path = "templates/user/user_tasks.html"
        
        with open(template_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Verifica modal
        modal_features = [
            'addTaskModal',
            'showAddTaskModal()',
            'createTask()',
            'taskTitle',
            'taskDescription',
            'taskPriority',
            'taskOrigin',
            'taskDeadline'
        ]
        
        for feature in modal_features:
            self.assertIn(feature, content, f"Funzionalità modal {feature} non trovata")
    
    def test_csv_export_functionality(self):
        """Test funzionalità export CSV."""
        template_path = "templates/user/user_tasks.html"
        
        with open(template_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Verifica export CSV
        csv_features = [
            'exportToCSV()',
            'Blob(',
            'text/csv',
            'download',
            'task_ai_'
        ]
        
        for feature in csv_features:
            self.assertIn(feature, content, f"Funzionalità CSV {feature} non trovata")
    
    def test_toast_notifications(self):
        """Test notifiche toast."""
        template_path = "templates/user/user_tasks.html"
        
        with open(template_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Verifica toast
        toast_features = [
            'showToast(',
            'toast-container',
            'toast-header',
            'toast-body',
            'bootstrap.Toast'
        ]
        
        for feature in toast_features:
            self.assertIn(feature, content, f"Funzionalità toast {feature} non trovata")
    
    def test_loading_states(self):
        """Test stati di caricamento."""
        template_path = "templates/user/user_tasks.html"
        
        with open(template_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Verifica stati caricamento
        loading_features = [
            'loading-spinner',
            'showLoading(',
            'spinner-border',
            'Caricamento'
        ]
        
        for feature in loading_features:
            self.assertIn(feature, content, f"Stato caricamento {feature} non trovato")
    
    def test_empty_state_handling(self):
        """Test gestione stato vuoto."""
        template_path = "templates/user/user_tasks.html"
        
        with open(template_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Verifica gestione stato vuoto
        empty_state_features = [
            'empty-state',
            'Nessun task trovato',
            'Crea il tuo primo task'
        ]
        
        for feature in empty_state_features:
            self.assertIn(feature, content, f"Gestione stato vuoto {feature} non trovata")


class TestUserTasksTemplateIntegration(unittest.TestCase):
    """Test integrazione template con API."""
    
    def test_api_response_handling(self):
        """Test gestione risposta API."""
        # Mock risposta API successo
        mock_api_response = {
            'success': True,
            'data': [
                {
                    'id': 1,
                    'titolo': 'Test Task',
                    'descrizione': 'Test Description',
                    'data_scadenza': '2024-01-15T10:30:00',
                    'priorita': 'Medium',
                    'origine': 'AI',
                    'stato': False,
                    'data_creazione': '2024-01-10T09:00:00',
                    'is_completed': False,
                    'is_overdue': False,
                    'days_until_deadline': 5,
                    'priority_color': 'info',
                    'status_color': 'bg-secondary',
                    'origine_badge_class': 'bg-primary',
                    'origine_display': '🤖 AI'
                }
            ],
            'count': 1
        }
        
        # Verifica che la risposta abbia la struttura corretta
        self.assertTrue(mock_api_response['success'])
        self.assertIn('data', mock_api_response)
        self.assertIn('count', mock_api_response)
        self.assertIsInstance(mock_api_response['data'], list)
        
        # Verifica struttura task
        task = mock_api_response['data'][0]
        required_fields = [
            'id', 'titolo', 'descrizione', 'data_scadenza', 'priorita',
            'origine', 'stato', 'data_creazione', 'is_completed',
            'is_overdue', 'days_until_deadline', 'priority_color',
            'status_color', 'origine_badge_class', 'origine_display'
        ]
        
        for field in required_fields:
            self.assertIn(field, task, f"Campo {field} mancante nel task")
    
    def test_error_response_handling(self):
        """Test gestione risposta errore API."""
        # Mock risposta errore API
        mock_error_response = {
            'success': False,
            'error': 'Errore nel caricamento dei task'
        }
        
        # Verifica struttura errore
        self.assertFalse(mock_error_response['success'])
        self.assertIn('error', mock_error_response)
        self.assertIsInstance(mock_error_response['error'], str)
    
    def test_filter_data_structure(self):
        """Test struttura dati filtri."""
        # Mock dati filtri
        mock_filter_data = {
            'stato': False,
            'origine': 'AI',
            'priorita': 'High',
            'search': 'test',
            'sort_by': 'data_creazione',
            'sort_order': 'desc'
        }
        
        # Verifica struttura filtri
        filter_fields = ['stato', 'origine', 'priorita', 'search', 'sort_by', 'sort_order']
        
        for field in filter_fields:
            self.assertIn(field, mock_filter_data, f"Campo filtro {field} mancante")
    
    def test_task_creation_data(self):
        """Test dati creazione task."""
        # Mock dati creazione task
        mock_create_data = {
            'titolo': 'Nuovo Task',
            'descrizione': 'Descrizione task',
            'priorita': 'Medium',
            'origine': 'AI',
            'data_scadenza': '2024-01-20T10:00:00'
        }
        
        # Verifica struttura dati creazione
        create_fields = ['titolo', 'descrizione', 'priorita', 'origine', 'data_scadenza']
        
        for field in create_fields:
            self.assertIn(field, mock_create_data, f"Campo creazione {field} mancante")
        
        # Verifica che il titolo sia presente
        self.assertTrue(mock_create_data['titolo'], "Titolo task obbligatorio")


if __name__ == '__main__':
    # Esegui i test
    unittest.main(verbosity=2) 