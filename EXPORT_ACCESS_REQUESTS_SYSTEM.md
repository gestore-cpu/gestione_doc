# 📤 Sistema Esportazione CSV Richieste Accesso

## 🎯 Panoramica

Il sistema di esportazione CSV per le richieste di accesso permette agli admin di esportare in formato CSV l'elenco completo delle richieste di accesso ai file, con tutti i campi chiave e filtri applicati.

## 🏗️ Architettura

### Route Principale
```python
@admin_bp.route('/admin/access_requests/export')
@login_required
@admin_required
def export_access_requests():
    """
    Esporta le richieste di accesso in formato CSV con filtri applicati.
    """
```

### Sicurezza
- **Protezione**: Solo utenti `@admin_required`
- **Accesso**: Tramite link/button da pagine admin
- **Validazione**: Filtri applicati automaticamente

## 🔧 Funzionalità Implementate

### 1. Filtri Supportati
- **Stato**: pending, approved, denied
- **Intervallo Date**: date_from, date_to
- **Utente**: username specifico
- **Azienda**: nome azienda
- **Reparto**: nome reparto

### 2. Campi CSV Esportati
| Colonna | Origine | Descrizione |
|---------|---------|-------------|
| ID Richiesta | `AccessRequest.id` | ID univoco della richiesta |
| Utente | `User.first_name + last_name` | Nome completo utente |
| Email | `User.email` | Email utente |
| File Richiesto | `Document.title` | Nome del file richiesto |
| Azienda | `Company.name` | Azienda del documento |
| Reparto | `Department.name` | Reparto del documento |
| Stato | `AccessRequest.status` | Stato richiesta |
| Motivazione | `AccessRequest.reason` | Motivazione utente |
| Risposta Admin | `AccessRequest.response_message` | Risposta admin |
| Data Richiesta | `AccessRequest.created_at` | Data creazione |
| Data Risposta | `AccessRequest.resolved_at` | Data risoluzione |

## 📊 Formato CSV

### Intestazioni
```csv
ID Richiesta,Utente,Email,File Richiesto,Azienda,Reparto,Stato,Motivazione,Risposta Admin,Data Richiesta,Data Risposta
```

### Esempio Dati
```csv
1,John Doe,john.doe@example.com,Contratto_2025.pdf,Test Company,Amministrazione,pending,Necessario per revisione,,15/01/2025 10:30,
2,Jane Smith,jane.smith@example.com,Manuale_QA.pdf,Test Company,Qualità,approved,Documentazione progetto,Accesso approvato,16/01/2025 14:20,17/01/2025 09:15
```

## 🛡️ Gestione Dati

### Dati Vuoti
- **Nome Utente**: Se `first_name` o `last_name` sono `None`, usa `username`
- **File**: Se `title` è vuoto, usa `original_filename`
- **Motivazione**: Se vuota, campo vuoto
- **Risposta Admin**: Se vuota, campo vuoto
- **Data Risposta**: Se `resolved_at` è `None`, campo vuoto

### Formattazione Date
- **Formato**: `dd/mm/yyyy HH:MM`
- **Esempio**: `15/01/2025 10:30`
- **Gestione**: Date vuote rimangono vuote

## 🔗 Integrazione UI

### Template Access Requests
```html
<a href="{{ url_for('admin.export_access_requests') }}?{{ request.query_string.decode() }}" class="btn btn-success">
  <i class="fas fa-download"></i> Export CSV
</a>
```

## 📈 Utilizzo

### Per gli Admin
1. **Accedere** alla pagina richieste accesso o dashboard
2. **Applicare filtri** (opzionale)
3. **Cliccare** "Export CSV"
4. **Scaricare** il file generato

### Esempi di Utilizzo
- **Tutte le richieste**: Export senza filtri
- **Solo pending**: `?status=pending`
- **Per periodo**: `?date_from=2025-01-01&date_to=2025-12-31`
- **Per utente**: `?user=username`
- **Combinazione**: `?status=approved&date_from=2025-01-01&company=Test Company`

## 🧪 Testing

### Test Implementati
- ✅ Test intestazioni CSV
- ✅ Test dati riga CSV
- ✅ Test generazione CSV
- ✅ Test parametri filtri
- ✅ Test generazione nome file
- ✅ Test headers risposta
- ✅ Test gestione dati vuoti
- ✅ Test validazione formato CSV
- ✅ Test formattazione date

### Comando Test
```bash
python3 test_export_access_requests.py
```

## 📋 Checklist Implementazione

### ✅ Completato
- [x] Route `/admin/access_requests/export`
- [x] Protezione `@admin_required`
- [x] Filtri applicati (status, date, user, company, department)
- [x] Join con tabelle correlate
- [x] Intestazioni CSV complete
- [x] Formattazione date italiana
- [x] Gestione dati vuoti
- [x] Nome file con timestamp
- [x] Headers risposta corretti
- [x] Integrazione con template esistenti
- [x] Test unitari completi
- [x] Documentazione completa

---

**Sistema Esportazione CSV Richieste Accesso - Implementazione Completa** ✅ 