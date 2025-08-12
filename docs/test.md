# 🧪 Guida Test DOCS Mercury

> Guida completa ai test per il modulo DOCS Mercury

## 📋 Panoramica Test

Il modulo DOCS Mercury include una suite completa di test per garantire la qualità e affidabilità del sistema. I test coprono funzionalità base, AI intelligence, integrazioni e performance.

## 🏗️ Struttura Test

```
tests/
├── unit/                    # Test unitari
│   ├── test_models.py
│   ├── test_services.py
│   └── test_utils.py
├── integration/             # Test integrazione
│   ├── test_api.py
│   ├── test_ai.py
│   └── test_database.py
├── ai/                     # Test AI specifici
│   ├── test_auto_verifica_documenti.py
│   ├── test_ai_access_response.py
│   └── test_ai_archive_suggestion.py
├── performance/            # Test performance
│   ├── test_load.py
│   └── test_stress.py
└── fixtures/              # Dati di test
    ├── test_documents.json
    └── test_users.json
```

## 🚀 Esecuzione Test

### Setup Ambiente Test

```bash
# Crea ambiente virtuale per test
python -m venv test_env
source test_env/bin/activate

# Installa dipendenze test
pip install -r requirements-test.txt

# Setup database test
export TESTING=True
export DATABASE_URL=sqlite:///test.db
flask db upgrade
```

### Comandi Test Base

```bash
# Test unitari
python -m pytest tests/unit/ -v

# Test integrazione
python -m pytest tests/integration/ -v

# Test AI specifici
python -m pytest tests/ai/ -v

# Test performance
python -m pytest tests/performance/ -v

# Tutti i test
python -m pytest tests/ -v

# Test con coverage
coverage run -m pytest tests/
coverage report
coverage html
```

## 🧠 Test AI Intelligence

### Test Auto-verifica Documenti

```bash
# Test completo auto-verifica
python test_auto_verifica_documenti.py

# Test specifico estrazione testo
python -c "
from services.document_intelligence import extract_text_from_pdf
result = extract_text_from_pdf('tests/fixtures/test_document.pdf')
print('Test estrazione:', 'OK' if result else 'FAILED')
"
```

**Test Cases:**
- ✅ Documento conforme (tutte le sezioni presenti)
- ❌ Documento non conforme (sezioni mancanti)
- ⚠️ Documento sospetto (contenuto ambiguo)
- 📄 PDF con testo estratto
- 📝 Word document (placeholder)

### Test Risposta AI Accesso

```bash
# Test risposta AI accesso
python test_ai_access_response.py

# Test simulazione richiesta
python -c "
from services.document_intelligence import generate_ai_access_response
result = generate_ai_access_response(1, 'Necessario per progetto urgente')
print('Test risposta AI:', 'OK' if result['success'] else 'FAILED')
"
```

**Test Cases:**
- ✅ Richiesta legittima (accesso concesso)
- ❌ Richiesta illegittima (accesso negato)
- ⚠️ Richiesta ambigua (valutazione manuale)
- 📧 Generazione email automatica
- 🤖 Parere AI per admin

### Test Suggerimento Archiviazione

```bash
# Test suggerimento archiviazione
python test_ai_archive_suggestion.py

# Test simulazione suggerimento
python -c "
from services.document_intelligence import suggerisci_cartella_archiviazione
result = suggerisci_cartella_archiviazione(1)
print('Test suggerimento:', 'OK' if result['success'] else 'FAILED')
"
```

**Test Cases:**
- 📁 Path suggerito corretto
- 🏷️ Tag AI generati
- 📊 Punteggio confidenza
- 🤖 Motivazione AI
- ✅ Accettazione suggerimento

## 🔧 Test API

### Test Endpoint Base

```bash
# Test health check
curl -X GET http://localhost:5000/api/health

# Test autenticazione
curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'

# Test lista documenti
curl -X GET http://localhost:5000/api/documents \
  -H "Authorization: Bearer <token>"
```

### Test AI Endpoints

```bash
# Test auto-verifica
curl -X POST http://localhost:5000/docs/ai/verifica/1 \
  -H "Authorization: Bearer <token>"

# Test suggerimento archiviazione
curl -X GET http://localhost:5000/docs/ai/suggerisci-cartella/1 \
  -H "Authorization: Bearer <token>"

# Test risposta accesso
curl -X POST http://localhost:5000/docs/ai/richiesta-accesso/1/rispondi \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"motivazione":"Progetto urgente"}'
```

### Test Dashboard AI

```bash
# Test dashboard principale
curl -X GET "http://localhost:5000/api/jack/docs/dashboard/1?period=current_month" \
  -H "Authorization: Bearer <token>"

# Test report CEO
curl -X GET "http://localhost:5000/api/jack/docs/report_ceo/2025/01" \
  -H "Authorization: Bearer <token>" \
  --output report_ceo.pdf
```

## 📊 Test Performance

### Test Load

```bash
# Test con Apache Bench
ab -n 1000 -c 10 http://localhost:5000/api/health

# Test con wrk
wrk -t12 -c400 -d30s http://localhost:5000/api/health

# Test upload file
ab -n 100 -c 5 -p test_file.json -T application/json \
  http://localhost:5000/api/documents
```

### Test Stress

```bash
# Test stress database
python tests/performance/test_stress.py

# Test AI services
python tests/performance/test_ai_stress.py

# Test memoria
python tests/performance/test_memory.py
```

## 🗄️ Test Database

### Test Modelli

```python
# test_models.py
import pytest
from models import User, Document, Company, Department

def test_user_creation():
    user = User(
        username='test_user',
        email='test@example.com',
        password='password123',
        role='user'
    )
    assert user.username == 'test_user'
    assert user.role == 'user'

def test_document_creation():
    doc = Document(
        title='Test Document',
        filename='test.pdf',
        user_id=1,
        company_id=1,
        department_id=1
    )
    assert doc.title == 'Test Document'
    assert doc.visibility == 'privato'

def test_ai_models():
    from models import DocumentAIFlag, AIArchiveSuggestion
    
    flag = DocumentAIFlag(
        document_id=1,
        flag_type='conforme',
        ai_analysis='Test analysis',
        compliance_score=85.5
    )
    assert flag.flag_type == 'conforme'
    assert flag.compliance_score == 85.5
```

### Test Relazioni

```python
def test_user_documents_relationship():
    user = User.query.get(1)
    assert len(user.documents) >= 0
    
    doc = Document.query.get(1)
    assert doc.uploader.id == doc.user_id

def test_company_departments():
    company = Company.query.get(1)
    assert len(company.departments) >= 0
    
    dept = Department.query.get(1)
    assert dept.company.id == dept.company_id
```

## 🔍 Test Integrazione

### Test FocusMe AI

```python
# test_focusme_integration.py
import requests

def test_focusme_health():
    response = requests.get('https://64.226.70.28/api/health')
    assert response.status_code == 200

def test_jack_preferences():
    response = requests.get('https://64.226.70.28/api/utente/1/preferenze')
    assert response.status_code == 200
    data = response.json()
    assert 'style' in data
    assert 'mood' in data

def test_jack_branding():
    response = requests.get('https://64.226.70.28/api/jack/branding/1')
    assert response.status_code == 200
    data = response.json()
    assert 'name' in data
    assert 'avatar_url' in data
```

### Test Email

```python
# test_email.py
from flask_mail import Mail, Message

def test_email_sending():
    mail = Mail()
    msg = Message(
        'Test Email',
        sender='noreply@mercury-surgelati.com',
        recipients=['test@example.com']
    )
    msg.body = 'Test email content'
    
    # In ambiente test, verifica che l'email sia stata "inviata"
    assert msg.subject == 'Test Email'
    assert 'test@example.com' in msg.recipients
```

## 📈 Test Coverage

### Configurazione Coverage

```bash
# .coveragerc
[run]
source = .
omit = 
    */tests/*
    */venv/*
    */env/*
    */migrations/*
    */__pycache__/*
    app.py

[report]
exclude_lines =
    pragma: no cover
    def __repr__
    if self.debug:
    if settings.DEBUG
    raise AssertionError
    raise NotImplementedError
    if 0:
    if __name__ == .__main__.:
    class .*\bProtocol\):
    @(abc\.)?abstractmethod
```

### Report Coverage

```bash
# Genera report HTML
coverage html
open htmlcov/index.html

# Report console
coverage report --show-missing

# Target coverage
coverage report --fail-under=80
```

## 🚨 Test Sicurezza

### Test Autenticazione

```python
# test_security.py
def test_invalid_login():
    response = client.post('/api/auth/login', json={
        'username': 'invalid',
        'password': 'wrong'
    })
    assert response.status_code == 401

def test_protected_endpoint():
    response = client.get('/api/documents')
    assert response.status_code == 401

def test_valid_token():
    # Login per ottenere token
    login_response = client.post('/api/auth/login', json={
        'username': 'admin',
        'password': 'admin123'
    })
    token = login_response.json['token']
    
    # Usa token per endpoint protetto
    response = client.get('/api/documents', headers={
        'Authorization': f'Bearer {token}'
    })
    assert response.status_code == 200
```

### Test Permessi

```python
def test_role_based_access():
    # Test admin access
    admin_response = client.get('/api/admin/users', headers={
        'Authorization': f'Bearer {admin_token}'
    })
    assert admin_response.status_code == 200
    
    # Test user access (dovrebbe essere negato)
    user_response = client.get('/api/admin/users', headers={
        'Authorization': f'Bearer {user_token}'
    })
    assert user_response.status_code == 403
```

## 🔄 Test CI/CD

### GitHub Actions

```yaml
# .github/workflows/test.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v2
    
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: 3.8
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install -r requirements-test.txt
    
    - name: Run tests
      run: |
        python -m pytest tests/ -v --cov=.
    
    - name: Upload coverage
      uses: codecov/codecov-action@v1
```

### Test Automatici

```bash
#!/bin/bash
# run_tests.sh

echo "🧪 Running DOCS Mercury Tests..."

# Setup
export TESTING=True
export DATABASE_URL=sqlite:///test.db

# Database setup
flask db upgrade

# Run tests
python -m pytest tests/ -v --cov=. --cov-report=html

# Check coverage
coverage report --fail-under=80

# Cleanup
rm -f test.db
rm -rf htmlcov/

echo "✅ Tests completed!"
```

## 📊 Metriche Test

### KPI Test

- **Coverage**: > 80%
- **Test Duration**: < 5 minuti
- **Success Rate**: > 95%
- **AI Test Accuracy**: > 90%

### Report Test

```bash
# Genera report test
python -m pytest tests/ --html=reports/test_report.html --self-contained-html

# Report performance
python tests/performance/generate_report.py

# Report AI accuracy
python tests/ai/generate_accuracy_report.py
```

## 🐛 Debug Test

### Test Failing

```bash
# Debug test specifico
python -m pytest tests/unit/test_models.py::test_user_creation -v -s

# Debug con pdb
python -m pytest tests/unit/test_models.py::test_user_creation --pdb

# Debug con logging
python -m pytest tests/unit/test_models.py::test_user_creation -v --log-cli-level=DEBUG
```

### Test Database

```bash
# Reset database test
rm -f test.db
flask db upgrade

# Popola dati test
python tests/fixtures/load_test_data.py

# Verifica dati
python -c "
from models import User, Document
print(f'Users: {User.query.count()}')
print(f'Documents: {Document.query.count()}')
"
```

## 📝 Best Practices

### Scrittura Test

```python
# ✅ Buono
def test_user_creation_success():
    user = User(username='test', email='test@example.com')
    assert user.username == 'test'
    assert user.email == 'test@example.com'

# ❌ Cattivo
def test_user():
    user = User()
    # Troppo generico, non testa nulla specifico
```

### Organizzazione Test

```python
# Raggruppa test correlati
class TestUserManagement:
    def test_create_user(self):
        pass
    
    def test_update_user(self):
        pass
    
    def test_delete_user(self):
        pass

class TestDocumentAI:
    def test_auto_verification(self):
        pass
    
    def test_archive_suggestion(self):
        pass
```

### Fixtures

```python
# conftest.py
import pytest
from app import create_app
from models import db

@pytest.fixture
def app():
    app = create_app('testing')
    return app

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def db_session(app):
    with app.app_context():
        db.create_all()
        yield db
        db.drop_all()
```

---

**Ultimo aggiornamento**: 2025-01-27  
**Versione**: 2.0.0  
**Coverage Target**: 80% 