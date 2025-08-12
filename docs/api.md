# 📚 Documentazione API DOCS Mercury

> Documentazione completa degli endpoint API per il modulo DOCS Mercury

## 🔗 Base URL

```
Produzione: https://138.68.80.169
Sviluppo: http://localhost:5000
```

## 🔐 Autenticazione

Tutte le API richiedono autenticazione tramite JWT token o session cookie.

### Headers Richiesti

```bash
Authorization: Bearer <jwt_token>
Content-Type: application/json
```

### Login

```bash
POST /api/auth/login
Content-Type: application/json

{
    "username": "admin",
    "password": "admin123"
}
```

**Response:**
```json
{
    "success": true,
    "token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "user": {
        "id": 1,
        "username": "admin",
        "email": "admin@mercury-surgelati.com",
        "role": "admin",
        "first_name": "Admin",
        "last_name": "Mercury"
    }
}
```

## 📄 Documenti API

### Lista Documenti

```bash
GET /api/documents
Authorization: Bearer <token>
```

**Query Parameters:**
- `page`: Numero pagina (default: 1)
- `per_page`: Elementi per pagina (default: 20)
- `search`: Ricerca testuale
- `company_id`: Filtra per azienda
- `department_id`: Filtra per reparto
- `user_id`: Filtra per utente
- `visibility`: Filtra per visibilità (pubblico/privato)
- `expired`: Filtra documenti scaduti (true/false)

**Response:**
```json
{
    "success": true,
    "documents": [
        {
            "id": 1,
            "title": "Manuale HACCP",
            "filename": "manuale_haccp.pdf",
            "description": "Manuale procedure HACCP",
            "company": "Mercury",
            "department": "Qualità",
            "uploader": "admin",
            "uploaded_at": "2025-01-27T10:30:00Z",
            "expiry_date": "2025-12-31T23:59:59Z",
            "visibility": "privato",
            "downloadable": true,
            "ai_status": "completo",
            "ai_confidence": 85.5
        }
    ],
    "pagination": {
        "page": 1,
        "per_page": 20,
        "total": 150,
        "pages": 8
    }
}
```

### Upload Documento

```bash
POST /api/documents
Authorization: Bearer <token>
Content-Type: multipart/form-data

Form Data:
- file: <file>
- title: "Titolo documento"
- description: "Descrizione documento"
- company_id: 1
- department_id: 2
- visibility: "privato"
- downloadable: true
- expiry_date: "2025-12-31"
- shared_email: "user@example.com"
```

**Response:**
```json
{
    "success": true,
    "document": {
        "id": 123,
        "title": "Titolo documento",
        "filename": "documento_123.pdf",
        "uploaded_at": "2025-01-27T10:30:00Z"
    },
    "ai_analysis": {
        "status": "in_progress",
        "suggestion_id": 456
    }
}
```

### Dettagli Documento

```bash
GET /api/documents/{document_id}
Authorization: Bearer <token>
```

**Response:**
```json
{
    "success": true,
    "document": {
        "id": 123,
        "title": "Manuale HACCP",
        "filename": "manuale_haccp.pdf",
        "original_filename": "HACCP_Manual_2025.pdf",
        "description": "Manuale procedure HACCP",
        "note": "Documento aggiornato",
        "company": {
            "id": 1,
            "name": "Mercury"
        },
        "department": {
            "id": 2,
            "name": "Qualità"
        },
        "uploader": {
            "id": 1,
            "username": "admin",
            "email": "admin@mercury-surgelati.com"
        },
        "uploaded_at": "2025-01-27T10:30:00Z",
        "expiry_date": "2025-12-31T23:59:59Z",
        "visibility": "privato",
        "downloadable": true,
        "shared_email": "user@example.com",
        "guest_permission": "read",
        "is_critical": true,
        "is_signed": false,
        "stato_approvazione": "approvato",
        "ai_status": "completo",
        "ai_explain": "Documento conforme alle normative HACCP",
        "ai_confidence": 85.5,
        "tag": "haccp,manuale,qualità",
        "categoria_ai": "Manuale HACCP"
    },
    "ai_flags": [
        {
            "id": 1,
            "flag_type": "conforme",
            "compliance_score": 85.5,
            "missing_sections": null,
            "created_at": "2025-01-27T10:31:00Z"
        }
    ],
    "archive_suggestions": [
        {
            "id": 1,
            "path_suggerito": "/Mercury/Qualità/HACCP",
            "categoria_suggerita": "Qualità",
            "tag_ai": ["haccp", "manuale", "formazione"],
            "confidence_score": 85.0,
            "accepted": false
        }
    ]
}
```

### Download Documento

```bash
GET /api/documents/{document_id}/download
Authorization: Bearer <token>
```

**Response:** File binary

### Aggiorna Documento

```bash
PUT /api/documents/{document_id}
Authorization: Bearer <token>
Content-Type: application/json

{
    "title": "Nuovo titolo",
    "description": "Nuova descrizione",
    "visibility": "pubblico",
    "downloadable": false,
    "expiry_date": "2026-01-31"
}
```

### Elimina Documento

```bash
DELETE /api/documents/{document_id}
Authorization: Bearer <token>
```

## 🧠 AI Intelligence API

### Auto-verifica Documento

```bash
POST /docs/ai/verifica/{document_id}
Authorization: Bearer <token>
```

**Response:**
```json
{
    "success": true,
    "verification": {
        "flag_type": "conforme",
        "compliance_score": 85.5,
        "missing_sections": [],
        "ai_analysis": "Documento conforme alle normative. Tutte le sezioni richieste sono presenti.",
        "suggestions": [
            "Considerare aggiunta firma digitale",
            "Verificare scadenza certificazioni"
        ]
    }
}
```

### Suggerimento Archiviazione

```bash
GET /docs/ai/suggerisci-cartella/{document_id}
Authorization: Bearer <token>
```

**Response:**
```json
{
    "success": true,
    "path_suggerito": "/Mercury/Qualità/HACCP",
    "categoria_suggerita": "Qualità",
    "tag_ai": ["haccp", "manuale", "formazione", "qualità", "urgente"],
    "motivazione_ai": "Documento classificato come 'haccp' e assegnato alla categoria 'Qualità'.\n\nRipartimento suggerito: Qualità\nTag identificati: haccp, manuale, formazione, qualità, urgente\n\nMotivazione: Manuale operativo per formazione e riferimento del personale.",
    "suggested_folder": "Qualità/Qualità",
    "confidence_score": 85.0,
    "azienda_suggerita": "Mercury",
    "reparto_suggerito": "Qualità",
    "tipo_documento_ai": "haccp",
    "suggestion_id": 789
}
```

### Risposta AI Accesso

```bash
POST /docs/ai/richiesta-accesso/{request_id}/rispondi
Authorization: Bearer <token>
```

**Response:**
```json
{
    "success": true,
    "response": {
        "risposta_ai": "Gentile utente, la sua richiesta di accesso al documento 'Manuale HACCP' è stata valutata. Il documento contiene informazioni riservate relative alle procedure di sicurezza alimentare. L'accesso è concesso con le seguenti limitazioni: solo visualizzazione, divieto di download e condivisione.",
        "parere_ai": "CONSIGLIATO CONCEDERE - L'utente ha motivazioni legittime per l'accesso e il documento non è critico per la sicurezza.",
        "email_suggestion": "📧 INVIA EMAIL A: user@example.com\n\nOggetto: Accesso documento \"Manuale HACCP\" - APPROVATO\n\nGentile utente, la sua richiesta di accesso al documento 'Manuale HACCP' è stata valutata...\n\n---\nNota: L'AI consiglia di concedere l'accesso."
    }
}
```

### Lista Suggerimenti Archiviazione

```bash
GET /docs/ai/suggerimenti-archiviazione/{document_id}
Authorization: Bearer <token>
```

**Response:**
```json
{
    "success": true,
    "document_id": 123,
    "document_title": "Manuale HACCP",
    "suggestions": [
        {
            "id": 1,
            "suggested_folder": "Qualità/Qualità",
            "path_suggerito": "/Mercury/Qualità/HACCP",
            "categoria_suggerita": "Qualità",
            "tag_ai": ["haccp", "manuale", "formazione"],
            "motivazione_ai": "Documento classificato come 'haccp'...",
            "confidence_score": 85.0,
            "azienda_suggerita": "Mercury",
            "reparto_suggerito": "Qualità",
            "tipo_documento_ai": "haccp",
            "accepted": false,
            "created_at": "2025-01-27T10:30:00Z",
            "confidence_display": "Alta",
            "tag_display": "haccp, manuale, formazione",
            "path_display": "/Mercury/Qualità/HACCP"
        }
    ],
    "total": 1
}
```

### Accetta Suggerimento Archiviazione

```bash
POST /docs/ai/suggerimento-archiviazione/{suggestion_id}/accetta
Authorization: Bearer <token>
Content-Type: application/json

{
    "apply_to_document": true,
    "custom_path": "/custom/path"
}
```

### Statistiche Suggerimenti AI

```bash
GET /docs/ai/suggerimenti-archiviazione/stats
Authorization: Bearer <token>
```

**Response:**
```json
{
    "success": true,
    "statistics": {
        "total_suggestions": 150,
        "accepted_suggestions": 120,
        "acceptance_rate": 80.0,
        "average_confidence": 75.5,
        "top_categories": [
            {"categoria": "Qualità", "count": 45},
            {"categoria": "Sicurezza", "count": 30},
            {"categoria": "Amministrazione", "count": 25}
        ],
        "top_departments": [
            {"reparto": "Qualità", "count": 50},
            {"reparto": "Sicurezza", "count": 35},
            {"reparto": "Risorse Umane", "count": 20}
        ]
    }
}
```

## 📊 Dashboard AI API

### Dashboard Principale

```bash
GET /api/jack/docs/dashboard/{user_id}
Authorization: Bearer <token>
```

**Query Parameters:**
- `period`: Periodo (current_month, last_month, quarter)
- `company`: Filtra per azienda

**Response:**
```json
{
    "success": true,
    "dashboard": {
        "kpis": {
            "documents_expiring": 15,
            "missing_signatures": 8,
            "unapproved_uploads": 12,
            "obsolete_documents": 5
        },
        "criticita_per_reparto": [
            {
                "reparto": "Qualità",
                "criticita": 8,
                "documenti": 45,
                "percentuale": 17.8
            },
            {
                "reparto": "Sicurezza",
                "criticita": 5,
                "documenti": 30,
                "percentuale": 16.7
            }
        ],
        "ai_suggestion": "Attenzione: 15 documenti in scadenza nei prossimi 30 giorni. Consigliato rivedere procedure di rinnovo automatico.",
        "period": "current_month",
        "company": "Mercury"
    }
}
```

### Dettagli Criticità Reparto

```bash
GET /api/jack/docs/dashboard/{user_id}/reparto/{reparto_id}
Authorization: Bearer <token>
```

### Dati Trend

```bash
GET /api/jack/docs/dashboard/{user_id}/trend
Authorization: Bearer <token>
```

## 📄 Report API

### Report CEO Mensile

```bash
GET /api/jack/docs/report_ceo/{year}/{month}
Authorization: Bearer <token>
```

**Response:** File PDF

### Report Personalizzato

```bash
POST /api/jack/docs/report_ceo/personalizzato
Authorization: Bearer <token>
Content-Type: application/json

{
    "start_date": "2025-01-01",
    "end_date": "2025-01-31",
    "company_id": 1,
    "include_ai_analysis": true
}
```

## 👥 Utenti API

### Lista Utenti

```bash
GET /api/users
Authorization: Bearer <token>
```

**Query Parameters:**
- `role`: Filtra per ruolo
- `company_id`: Filtra per azienda
- `active`: Filtra utenti attivi

### Crea Utente

```bash
POST /api/users
Authorization: Bearer <token>
Content-Type: application/json

{
    "username": "nuovo_utente",
    "email": "nuovo@mercury-surgelati.com",
    "password": "password123",
    "first_name": "Nuovo",
    "last_name": "Utente",
    "role": "user",
    "company_id": 1,
    "department_id": 2
}
```

### Aggiorna Utente

```bash
PUT /api/users/{user_id}
Authorization: Bearer <token>
Content-Type: application/json

{
    "first_name": "Nome Aggiornato",
    "last_name": "Cognome Aggiornato",
    "role": "admin"
}
```

## 🏢 Aziende e Reparti API

### Lista Aziende

```bash
GET /api/companies
Authorization: Bearer <token>
```

### Lista Reparti

```bash
GET /api/departments
Authorization: Bearer <token>
```

**Query Parameters:**
- `company_id`: Filtra per azienda

## 🔍 Ricerca e Filtri

### Ricerca Documenti

```bash
GET /api/search/documents
Authorization: Bearer <token>
```

**Query Parameters:**
- `q`: Query di ricerca
- `type`: Tipo documento
- `date_from`: Data inizio
- `date_to`: Data fine
- `tags`: Tag separati da virgola

### Ricerca Avanzata

```bash
POST /api/search/advanced
Authorization: Bearer <token>
Content-Type: application/json

{
    "query": "haccp manuale",
    "filters": {
        "company_id": 1,
        "department_id": 2,
        "date_range": {
            "from": "2025-01-01",
            "to": "2025-01-31"
        },
        "tags": ["haccp", "manuale"],
        "ai_status": "completo"
    },
    "sort": {
        "field": "uploaded_at",
        "order": "desc"
    }
}
```

## 📈 Statistiche API

### Statistiche Generali

```bash
GET /api/stats/general
Authorization: Bearer <token>
```

**Response:**
```json
{
    "success": true,
    "stats": {
        "total_documents": 1250,
        "total_users": 45,
        "total_companies": 3,
        "documents_this_month": 45,
        "uploads_today": 3,
        "ai_suggestions_accepted": 120,
        "alerts_generated": 8
    }
}
```

### Statistiche AI

```bash
GET /api/stats/ai
Authorization: Bearer <token>
```

### Statistiche per Azienda

```bash
GET /api/stats/company/{company_id}
Authorization: Bearer <token>
```

## 🚨 Alert e Notifiche API

### Lista Alert

```bash
GET /api/alerts
Authorization: Bearer <token>
```

### Risolvi Alert

```bash
POST /api/alerts/{alert_id}/resolve
Authorization: Bearer <token>
Content-Type: application/json

{
    "resolution_note": "Alert risolto manualmente"
}
```

### Configura Notifiche

```bash
PUT /api/users/{user_id}/notifications
Authorization: Bearer <token>
Content-Type: application/json

{
    "email_notifications": true,
    "whatsapp_notifications": false,
    "telegram_notifications": false,
    "notification_types": ["document_expiry", "ai_suggestions", "alerts"]
}
```

## 🔐 Gestione Accessi API

### Richieste Accesso

```bash
GET /api/access-requests
Authorization: Bearer <token>
```

### Approva/Rifiuta Accesso

```bash
POST /api/access-requests/{request_id}/approve
Authorization: Bearer <token>
Content-Type: application/json

{
    "approved": true,
    "note": "Accesso approvato per progetto specifico"
}
```

## 📋 Quality Module API

### Certificazioni

```bash
GET /quality/certificazioni
Authorization: Bearer <token>
```

```bash
POST /quality/certificazioni
Authorization: Bearer <token>
Content-Type: application/json

{
    "nome": "ISO 9001:2015",
    "tipo": "ISO 9001",
    "ente_certificatore": "TÜV Italia",
    "data_rilascio": "2023-01-15",
    "data_scadenza": "2026-01-15",
    "note": "Certificazione qualità aziendale"
}
```

### Documenti Qualità

```bash
GET /quality/documenti
Authorization: Bearer <token>
```

```bash
POST /quality/documenti
Authorization: Bearer <token>
Content-Type: multipart/form-data

Form Data:
- file: <file>
- titolo: "Procedura Qualità"
- versione: "1.0"
- certificazione_id: 1
```

### Audit

```bash
GET /quality/audit
Authorization: Bearer <token>
```

```bash
POST /quality/audit
Authorization: Bearer <token>
Content-Type: application/json

{
    "titolo": "Audit Interno Qualità",
    "tipo": "interno",
    "data_inizio": "2025-02-01",
    "data_fine": "2025-02-15",
    "auditor": "Mario Rossi",
    "note": "Audit annuale sistema qualità"
}
```

### Azioni Correttive

```bash
GET /quality/azioni-correttive
Authorization: Bearer <token>
```

```bash
POST /quality/azioni-correttive
Authorization: Bearer <token>
Content-Type: application/json

{
    "titolo": "Miglioramento Procedure",
    "descrizione": "Aggiornamento procedure HACCP",
    "assegnato_a": 1,
    "priorita": "alta",
    "data_scadenza": "2025-03-31"
}
```

## 🔄 Integrazione API Esterne

### FocusMe AI

```bash
# Preferenze Jack
GET https://64.226.70.28/api/utente/{user_id}/preferenze

# Branding Jack
GET https://64.226.70.28/api/jack/branding/{user_id}

# Messaggi Jack
GET https://64.226.70.28/api/jack/docs/messages/{user_id}

# Task AI
GET https://64.226.70.28/api/jack/docs/tasks/{user_id}

# Suggerimenti
GET https://64.226.70.28/api/jack/docs/suggestions/{user_id}

# Report
GET https://64.226.70.28/api/jack/docs/report?year=2025&month=01
```

## 📝 Codici di Errore

### HTTP Status Codes

- `200 OK`: Richiesta completata con successo
- `201 Created`: Risorsa creata con successo
- `400 Bad Request`: Richiesta malformata
- `401 Unauthorized`: Autenticazione richiesta
- `403 Forbidden`: Accesso negato
- `404 Not Found`: Risorsa non trovata
- `422 Unprocessable Entity`: Dati non validi
- `500 Internal Server Error`: Errore server

### Error Response Format

```json
{
    "success": false,
    "error": "Descrizione errore",
    "error_code": "ERROR_CODE",
    "details": {
        "field": "campo specifico",
        "message": "messaggio specifico"
    }
}
```

### Codici Errore Comuni

- `AUTH_REQUIRED`: Autenticazione richiesta
- `INVALID_TOKEN`: Token non valido
- `PERMISSION_DENIED`: Permessi insufficienti
- `DOCUMENT_NOT_FOUND`: Documento non trovato
- `FILE_TOO_LARGE`: File troppo grande
- `INVALID_FILE_TYPE`: Tipo file non supportato
- `AI_SERVICE_UNAVAILABLE`: Servizio AI non disponibile
- `DATABASE_ERROR`: Errore database

## 📊 Rate Limiting

### Limiti API

- **Autenticati**: 1000 richieste/ora
- **Guest**: 100 richieste/ora
- **Upload**: 50 file/ora
- **AI Analysis**: 100 analisi/ora

### Headers Rate Limiting

```bash
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 950
X-RateLimit-Reset: 1643299200
```

## 🔧 Testing API

### Health Check

```bash
GET /api/health
```

**Response:**
```json
{
    "status": "healthy",
    "timestamp": "2025-01-27T10:30:00Z",
    "version": "2.0.0",
    "services": {
        "database": "connected",
        "ai_services": "available",
        "file_storage": "available"
    }
}
```

### Test AI Services

```bash
GET /api/test/ai
Authorization: Bearer <token>
```

### Test Email

```bash
POST /api/test/email
Authorization: Bearer <token>
Content-Type: application/json

{
    "to": "test@example.com",
    "subject": "Test Email",
    "body": "Test email from DOCS Mercury"
}
```

---

**Ultimo aggiornamento**: 2025-01-27  
**Versione API**: 2.0.0  
**Base URL**: https://138.68.80.169 