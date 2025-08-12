# 📋 VDOCS.018 – Storico Richieste Accesso per Utenti

## 🎯 Obiettivo
Consentire a ogni utente (non admin) di visualizzare lo storico delle proprie richieste di accesso ai documenti, inclusi:
- Stato (approvata / negata / in attesa)
- Motivazione
- Data richiesta
- Esito e messaggio del responsabile

## 🏗️ Architettura Implementata

### 📂 File Principali

#### 1. **Route Flask** - `routes/user_routes.py`
```python
@user_bp.route('/my_access_requests', methods=['GET'])
@login_required
def my_access_requests():
    """
    Visualizza lo storico delle richieste di accesso dell'utente corrente.
    """
```

**Funzionalità:**
- ✅ Filtri personali (stato, date, file)
- ✅ Isolamento dati per utente corrente
- ✅ Query ottimizzata con JOIN
- ✅ Statistiche personali
- ✅ Ordinamento per data (più recenti prima)

#### 2. **Template HTML** - `templates/user/my_access_requests.html`
- ✅ Design moderno e responsive
- ✅ Cards statistiche con gradienti
- ✅ Tabella interattiva con hover effects
- ✅ Badge di stato colorati
- ✅ Gestione stato vuoto
- ✅ Auto-refresh per richieste pendenti

#### 3. **Integrazione Dashboard** - `templates/user/dashboard.html`
- ✅ Link "Le mie Richieste" nella dashboard utente
- ✅ Card dedicata con icona chiave
- ✅ Accesso rapido allo storico

## 📊 Funzionalità Implementate

### 🔐 Sicurezza e Isolamento
- **Accesso Protetto**: Solo utenti autenticati (`@login_required`)
- **Isolamento Dati**: Filtro automatico per `current_user.id`
- **Separazione Admin/User**: Route diverse per admin e utenti

### 📋 Visualizzazione Dati
- **Data Richiesta**: Formato italiano (dd/mm/yyyy HH:MM)
- **File Richiesto**: Nome documento + azienda/reparto
- **Motivazione**: Testo completo con hover per troncamento
- **Stato**: Badge colorati (🟡 In Attesa, 🟢 Approvata, 🔴 Negata)
- **Risposta Admin**: Messaggio di risposta con tooltip

### 🔍 Filtri Disponibili
- **Stato**: Tutti, In Attesa, Approvate, Negate
- **Date**: Range personalizzabile (da/a)
- **File**: Ricerca per nome documento
- **Pulisci Filtri**: Reset rapido

### 📈 Statistiche Personali
- **Totale Richieste**: Numero complessivo
- **In Attesa**: Richieste pendenti
- **Approvate**: Richieste accettate
- **Negate**: Richieste respinte

## 🎨 Design e UX

### 🎯 Caratteristiche UI/UX
- **Responsive Design**: Ottimizzato per mobile e desktop
- **Cards Statistiche**: Con gradienti colorati e icone
- **Tabella Interattiva**: Hover effects e tooltip
- **Badge Colorati**: Distinzione visiva immediata degli stati
- **Empty State**: Messaggio informativo quando non ci sono richieste

### 🎨 Elementi Visivi
```css
/* Cards statistiche con gradienti */
.stats-card {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    border-radius: 10px;
}

/* Badge di stato */
.status-badge {
    font-size: 0.8rem;
    padding: 0.25rem 0.5rem;
}

/* Hover effects per celle troncate */
.reason-cell:hover {
    white-space: normal;
    overflow: visible;
    z-index: 1000;
}
```

## 🔧 Funzionalità Tecniche

### 📊 Query Ottimizzata
```python
query = db.session.query(
    AccessRequest,
    Document.title.label('document_title'),
    Document.original_filename.label('document_filename'),
    Company.name.label('company_name'),
    Department.name.label('department_name')
).join(
    Document, AccessRequest.document_id == Document.id
).outerjoin(
    Company, Document.company_id == Company.id
).outerjoin(
    Department, Document.department_id == Department.id
).filter(
    AccessRequest.user_id == current_user.id  # Isolamento utente
)
```

### 🔄 Auto-Refresh
- **Intervallo**: 60 secondi se ci sono richieste pendenti
- **Condizione**: Solo se `pending_requests > 0`
- **Beneficio**: Aggiornamento automatico dello stato

### 📱 Responsive Features
- **Mobile First**: Layout adattivo
- **Table Responsive**: Scroll orizzontale su mobile
- **Cards Grid**: Layout flessibile per statistiche

## 🧪 Test Implementati

### ✅ Test Unitari - `test_my_access_requests.py`
- **17 test completati** con successo
- **Copertura**: Route, template, isolamento dati, filtri
- **Sicurezza**: Verifica accesso negato ad admin/guest
- **Funzionalità**: Statistiche, formattazione date, stati

### 📋 Test Categories
1. **Route Access**: Verifica protezione `@login_required`
2. **Data Isolation**: Controllo isolamento dati utente
3. **Status Display**: Test badge di stato
4. **Date Formatting**: Verifica formattazione date
5. **Filter Functionality**: Test filtri personali
6. **Statistics Calculation**: Verifica calcoli statistiche
7. **Responsive Design**: Test layout responsive
8. **Security**: Verifica accesso negato ad admin/guest

## 🚀 Accesso e Navigazione

### 📍 URL Accesso
- **Route**: `/user/my_access_requests`
- **Dashboard Link**: Card "Le mie Richieste" nella dashboard utente
- **Breadcrumb**: Dashboard Utente → Le mie Richieste

### 🔗 Integrazione Dashboard
```html
<div class="card">
    <div class="card-body">
        <h5 class="card-title">
            <i class="fas fa-key text-warning"></i>
            Le mie Richieste
        </h5>
        <p class="card-text">Storico richieste di accesso</p>
        <a href="{{ url_for('user.my_access_requests') }}" class="btn btn-warning">
            <i class="fas fa-key"></i> Richieste
        </a>
    </div>
</div>
```

## 📊 Esempi di Utilizzo

### 👤 Scenario Utente
1. **Accesso**: Login come utente normale
2. **Navigazione**: Dashboard → "Le mie Richieste"
3. **Visualizzazione**: Storico completo delle richieste
4. **Filtri**: Applicazione filtri per stato/date/file
5. **Monitoraggio**: Auto-refresh per richieste pendenti

### 📈 Statistiche Esempio
```
Totale Richieste: 15
In Attesa: 3
Approvate: 10
Negate: 2
```

### 🎯 Stati Richieste
- **🟡 In Attesa**: Richiesta ricevuta, in valutazione
- **🟢 Approvata**: Accesso concesso al documento
- **🔴 Negata**: Richiesta respinta con motivazione

## 🔒 Sicurezza e Compliance

### 🛡️ Misure di Sicurezza
- **Isolamento Dati**: Filtro automatico per utente corrente
- **Accesso Protetto**: Decoratore `@login_required`
- **Separazione Ruoli**: Route diverse per admin e utenti
- **Validazione Input**: Sanitizzazione filtri di ricerca

### 📋 Compliance
- **GDPR**: Accesso ai propri dati personali
- **Trasparenza**: Visualizzazione completa dello storico
- **Controllo**: Possibilità di monitorare le proprie richieste
- **Audit Trail**: Tracciabilità completa delle richieste

## 🎉 Risultati Ottenuti

### ✅ Funzionalità Complete
- ✅ Route `/user/my_access_requests` funzionante
- ✅ Template responsive con design moderno
- ✅ Isolamento dati per utente corrente
- ✅ Filtri personali (stato, date, file)
- ✅ Statistiche personali in tempo reale
- ✅ Badge di stato colorati e intuitivi
- ✅ Visualizzazione risposta admin
- ✅ Link integrato nella dashboard utente
- ✅ Auto-refresh per richieste pendenti
- ✅ Test unitari completi (17 test)

### 🎯 Benefici per l'Utente
- **Trasparenza**: Visualizzazione completa dello storico
- **Controllo**: Monitoraggio delle proprie richieste
- **Efficienza**: Filtri rapidi per trovare richieste specifiche
- **Aggiornamenti**: Auto-refresh per richieste pendenti
- **Accessibilità**: Design responsive per tutti i dispositivi

### 🔧 Benefici Tecnici
- **Performance**: Query ottimizzata con JOIN
- **Sicurezza**: Isolamento dati e protezione accessi
- **Manutenibilità**: Codice ben strutturato e testato
- **Scalabilità**: Architettura estendibile per nuove funzionalità

---

**🎯 VDOCS.018 Completato con Successo!** ✅

Il sistema permette ora agli utenti di visualizzare e monitorare lo storico completo delle proprie richieste di accesso ai documenti, garantendo trasparenza, controllo e una migliore esperienza utente. 