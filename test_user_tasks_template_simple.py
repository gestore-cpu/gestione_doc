"""
Test semplificato per il template user_tasks.html - Prompt 26 FASE 3
Verifica che il template HTML abbia la struttura corretta.
"""

import unittest
import os


class TestUserTasksTemplateSimple(unittest.TestCase):
    """Test semplificato per il template user_tasks.html."""
    
    def test_template_exists(self):
        """Test che il template esista."""
        template_path = "templates/user/user_tasks.html"
        self.assertTrue(os.path.exists(template_path), "Template user_tasks.html non trovato")
    
    def test_template_structure(self):
        """Test struttura del template."""
        template_path = "templates/user/user_tasks.html"
        
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


if __name__ == '__main__':
    # Esegui i test
    unittest.main(verbosity=2) 