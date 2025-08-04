from extensions import db, bcrypt
from flask_login import UserMixin
from datetime import datetime
import os
import json
import enum

# === IMPORT MODELLO LOG INVIO DOCUMENTO ===
# Import rimosso per evitare circular import - il modello è definito direttamente in questo file

# === ENUM PER TASK AI ===
class OrigineTask(enum.Enum):
    """Enum per l'origine dei task."""
    AI = "AI"
    DIARIO = "Diario"
    DEEP_WORK = "Deep Work"
    MANUALE = "Manuale"

class PrioritaTask(enum.Enum):
    """Enum per la priorità dei task."""
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"

# === Tabelle di associazione molti-a-molti ===
user_companies = db.Table('user_companies',
    db.Column('user_id', db.Integer, db.ForeignKey('users.id'), primary_key=True),
    db.Column('company_id', db.Integer, db.ForeignKey('companies.id'), primary_key=True)
)

user_departments = db.Table('user_departments',
    db.Column('user_id', db.Integer, db.ForeignKey('users.id'), primary_key=True),
    db.Column('department_id', db.Integer, db.ForeignKey('departments.id'), primary_key=True)
)

# === MODELLO APPROVAZIONE DOCUMENTO ===
class ApprovazioneDocumento(db.Model):
    """
    Modello per gestire il workflow di approvazione multilivello dei documenti.
    
    Attributi:
        id (int): ID primario.
        document_id (int): ID documento associato.
        livello (int): Livello di approvazione (1=revisore, 2=responsabile, 3=CEO).
        ruolo_richiesto (str): Ruolo richiesto per l'approvazione.
        utente (str): Username di chi ha approvato.
        stato (str): Stato approvazione ('in_attesa', 'approvato', 'rifiutato').
        commento (str): Commento dell'approvatore.
        data (datetime): Data/ora approvazione.
        document (Document): Relazione con il documento.
    """
    __tablename__ = "document_approvazioni"
    
    id = db.Column(db.Integer, primary_key=True)
    document_id = db.Column(db.Integer, db.ForeignKey('documents.id'), nullable=False)
    livello = db.Column(db.Integer, nullable=False)  # 1 = revisore, 2 = manager, 3 = CEO
    ruolo_richiesto = db.Column(db.String(100), nullable=False)
    utente = db.Column(db.String(150), nullable=True)  # chi ha approvato
    stato = db.Column(db.String(50), default="in_attesa")  # in_attesa | approvato | rifiutato
    commento = db.Column(db.Text, nullable=True)
    data = db.Column(db.DateTime, nullable=True)
    
    # Relazione con il documento
    document = db.relationship("Document", backref="approvazioni")
    
    def __repr__(self):
        """Rappresentazione stringa dell'approvazione."""
        return f'<ApprovazioneDocumento {self.livello} - {self.ruolo_richiesto} - {self.stato}>'
    
    @property
    def is_completed(self):
        """Verifica se l'approvazione è completata."""
        return self.stato in ['approvato', 'rifiutato']
    
    @property
    def is_approved(self):
        """Verifica se l'approvazione è stata approvata."""
        return self.stato == 'approvato'
    
    @property
    def is_rejected(self):
        """Verifica se l'approvazione è stata rifiutata."""
        return self.stato == 'rifiutato'
    
    @property
    def is_pending(self):
        """Verifica se l'approvazione è in attesa."""
        return self.stato == 'in_attesa'

# === MODELLO UTENTE ===
class User(UserMixin, db.Model):
    """
    Modello utente per autenticazione e gestione permessi.

    Attributi:
        id (int): ID primario.
        username (str): Username univoco.
        email (str): Email univoca.
        password (str): Hash della password.
        first_name (str): Nome.
        last_name (str): Cognome.
        role (str): Ruolo ('user', 'guest', 'admin', 'superadmin').
        can_download (bool): Permesso download.
        notifica_preferita (str): Canale preferito ('email', 'whatsapp', 'telegram', 'none').
        password_set_at (datetime): Data ultimo set password.
        must_change_password (bool): Flag cambio password obbligatorio.
        created_at (datetime): Data creazione.
        access_expiration (datetime): Data scadenza accesso.
        companies (list): Aziende associate.
        departments (list): Reparti associati.
        documents (list): Documenti caricati.
        guest_activities (list): Attività ospite.
        password_links (list): Password sicure create.
    """
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)

    username = db.Column(db.String(150), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

    first_name = db.Column(db.String(100))
    last_name = db.Column(db.String(100))
    nome = db.Column(db.String(100), nullable=True)
    cognome = db.Column(db.String(100), nullable=True)

    role = db.Column(db.String(20), nullable=False, default='user')  # 'user', 'guest', 'admin', 'superadmin'
    can_download = db.Column(db.Boolean, default=False)
    # notifica_preferita = db.Column(db.String(20), nullable=False, default='email')  # 'email', 'whatsapp', 'telegram', 'none'

    password_set_at = db.Column(db.DateTime, default=datetime.utcnow)
    must_change_password = db.Column(db.Boolean, default=False)
    access_expiration = db.Column(db.Date, nullable=True)
    
    # === Campi per reminder automatici ===
    reminder_email = db.Column(db.Boolean, default=True)
    reminder_whatsapp = db.Column(db.Boolean, default=False)
    phone = db.Column(db.String(20), nullable=True)  # Numero WhatsApp

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # === Relazioni ===
    companies = db.relationship('Company', secondary=user_companies, backref='users')
    departments = db.relationship('Department', secondary=user_departments, backref='users')
    documents = db.relationship('Document', backref='uploader', lazy=True)
    guest_activities = db.relationship('GuestActivity', backref='user', lazy=True)
    password_links = db.relationship('PasswordLink', backref='creator', lazy=True, foreign_keys='PasswordLink.created_by_id')
    ai_tasks = db.relationship('Task', backref='document_ai', lazy=True, foreign_keys='Document.ai_task_id')
    tasks_ai = db.relationship('TaskAI', back_populates='utente', cascade='all, delete-orphan')

    def __repr__(self):
        """
        Rappresentazione stringa dell'utente.

        Returns:
            str: Rappresentazione.
        """
        return f'<User {self.username}>'

    @property
    def is_admin(self):
        """
        Verifica se l'utente è admin.

        Returns:
            bool: True se admin.
        """
        return self.role == 'admin'

    @property
    def is_ceo(self):
        """
        Verifica se l'utente è CEO.

        Returns:
            bool: True se CEO.
        """
        return self.role == 'ceo'

    @property
    def is_guest(self):
        """
        Verifica se l'utente è guest.

        Returns:
            bool: True se guest.
        """
        return self.role == 'guest'

    @property
    def is_user(self):
        """Restituisce True se l'utente ha ruolo 'user'."""
        return self.role == 'user'

# === MODELLO DOCUMENTO ===
class Document(db.Model):
    """
    Modello documento per gestione file e metadati.

    Attributi principali:
        id (int): ID primario.
        title (str): Titolo.
        filename (str): Nome file salvato.
        original_filename (str): Nome file originale.
        description (str): Descrizione.
        note (str): Note.
        user_id (int): ID utente uploader.
        uploader_email (str): Email uploader.
        company_id (int): ID azienda.
        department_id (int): ID reparto.
        visibility (str): Visibilità ('pubblico', 'privato').
        shared_email (str): Email condivise.
        guest_permission (str): Permessi guest.
        downloadable (bool): Flag download.
        expiry_date (datetime): Data scadenza.
        drive_file_id (str): ID file su Drive.
        created_at (datetime): Data creazione.
    """
    __tablename__ = 'documents'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=True)
    description = db.Column(db.Text, nullable=True)
    note = db.Column(db.Text, nullable=True)

    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    uploader_email = db.Column(db.String(150), nullable=False)

    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=False)

    visibility = db.Column(db.String(20), nullable=False, default='privato')  # pubblico/privato
    shared_email = db.Column(db.Text, nullable=True)
    guest_permission = db.Column(db.String(10), nullable=True)  # read/download
    downloadable = db.Column(db.Boolean, default=True)
    expiry_date = db.Column(db.DateTime, nullable=True)
    richiedi_firma = db.Column(db.Boolean, default=False)
    
    # === Campi per doppia validazione ===
    validazione_admin = db.Column(db.Boolean, default=False)
    validazione_ceo = db.Column(db.Boolean, default=False)
    
    # === Campo per documenti critici ===
    is_critical = db.Column(db.Boolean, default=False)  # True per contratti, certificati, manuali critici

    # === Campi per firma digitale interna ===
    is_signed = db.Column(db.Boolean, default=False)
    signed_at = db.Column(db.DateTime, nullable=True)
    signed_by = db.Column(db.String(150), nullable=True)  # o user_id
    firma_commento = db.Column(db.Text, nullable=True)
    signed_by_ai = db.Column(db.Boolean, default=False)  # Traccia se firmato automaticamente da AI

    # === Campi per workflow di approvazione ===
    stato_approvazione = db.Column(db.String(30), default="bozza")  # bozza, in_attesa, approvato, respinto
    approvato_da = db.Column(db.String(150), nullable=True)
    data_approvazione = db.Column(db.DateTime, nullable=True)
    commento_approvatore = db.Column(db.Text, nullable=True)

    drive_file_id = db.Column(db.String(255), nullable=True)
    drive_uploaded_at = db.Column(db.DateTime, nullable=True)
    drive_status_note = db.Column(db.String(255), nullable=True)  # Bonus: note AI o errori
    archiviato = db.Column(db.Boolean, default=False)  # Flag per documenti archiviati
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # === Campi per classificazione AI e collegamenti cross-modulo ===
    tag = db.Column(db.String(100), nullable=True)  # es. "Danno", "HACCP", "Listino"
    categoria_ai = db.Column(db.String(100), nullable=True)  # es. "Foto incidente"
    collegato_a_modulo = db.Column(db.String(50), nullable=True)  # "service", "qms", "elevate", "acquisti"
    auto_task_generato = db.Column(db.Boolean, default=False)
    
    # === Campi per gestione danni ===
    # asset_id = db.Column(db.Integer, db.ForeignKey("assets.id"), nullable=True)  # Rimossi temporaneamente
    # responsabile_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)  # Rimossi temporaneamente
    
    # === Campo per ricerca semantica ===
    contenuto_testuale = db.Column(db.Text, nullable=True)
    
    # === Campi per Document Intelligence AI ===
    ai_status = db.Column(db.String(50), nullable=True)  # completo, incompleto, scaduto, manca_firma
    ai_explain = db.Column(db.Text, nullable=True)  # Spiegazione AI sulla criticità
    ai_task_id = db.Column(db.Integer, db.ForeignKey('tasks.id'), nullable=True)  # Task AI associato
    ai_analysis = db.Column(db.Text, nullable=True)  # JSON con analisi completa AI
    ai_analyzed_at = db.Column(db.DateTime, nullable=True)  # Data analisi AI
    
    # === Campi per Revisione Ciclica AI ===
    frequenza_revisione = db.Column(db.String(20), nullable=True)  # annuale, biennale, trimestrale, mensile
    data_ultima_revisione = db.Column(db.Date, nullable=True)  # Data ultima revisione effettuata
    prossima_revisione = db.Column(db.Date, nullable=True)  # Data prossima revisione calcolata
    revisione_task_id = db.Column(db.Integer, db.ForeignKey('tasks.id'), nullable=True)  # Task revisione associato

    # === Metodi per workflow di approvazione multilivello ===
    def inizializza_flusso_approvazione(self):
        """
        Inizializza il flusso di approvazione multilivello per il documento.
        
        Crea automaticamente le righe ApprovazioneDocumento per i 3 livelli:
        - Livello 1: Revisore
        - Livello 2: Responsabile  
        - Livello 3: CEO
        """
        from extensions import db
        
        # Flusso predefinito
        flusso = [
            {"livello": 1, "ruolo": "revisore"},
            {"livello": 2, "ruolo": "responsabile"},
            {"livello": 3, "ruolo": "ceo"}
        ]
        
        for step in flusso:
            approvazione = ApprovazioneDocumento(
                document_id=self.id,
                livello=step["livello"],
                ruolo_richiesto=step["ruolo"],
                stato="in_attesa"
            )
            db.session.add(approvazione)
        
        self.stato_approvazione = "in_attesa"
        db.session.commit()
    
    def get_approvazioni_ordinate(self):
        """
        Restituisce le approvazioni ordinate per livello.
        
        Returns:
            list: Lista delle approvazioni ordinate.
        """
        return sorted(self.approvazioni, key=lambda x: x.livello)
    
    def get_prossimo_livello_da_approvare(self):
        """
        Restituisce il prossimo livello da approvare.
        
        Returns:
            ApprovazioneDocumento: Prossima approvazione in attesa, None se tutte completate.
        """
        approvazioni_ordinate = self.get_approvazioni_ordinate()
        
        for approvazione in approvazioni_ordinate:
            if approvazione.stato == "in_attesa":
                return approvazione
        
        return None
    
    def get_stato_flusso(self):
        """
        Restituisce lo stato generale del flusso di approvazione.
        
        Returns:
            str: Stato del flusso ('completato', 'in_corso', 'bloccato').
        """
        approvazioni = self.get_approvazioni_ordinate()
        
        # Se non ci sono approvazioni, il flusso non è iniziato
        if not approvazioni:
            return "non_iniziato"
        
        # Controlla se c'è un rifiuto
        for approvazione in approvazioni:
            if approvazione.stato == "rifiutato":
                return "bloccato"
        
        # Controlla se tutte sono approvate
        tutte_approvate = all(approvazione.stato == "approvato" for approvazione in approvazioni)
        if tutte_approvate:
            return "completato"
        
        # Altrimenti è in corso
        return "in_corso"
    
    def approva_livello(self, livello, utente, commento=None):
        """
        Approva un livello specifico del flusso.
        
        Args:
            livello (int): Livello da approvare.
            utente (str): Username di chi approva.
            commento (str, optional): Commento dell'approvazione.
        """
        from extensions import db
        from datetime import datetime
        
        approvazione = ApprovazioneDocumento.query.filter_by(
            document_id=self.id, 
            livello=livello
        ).first()
        
        if not approvazione:
            raise ValueError(f"Livello {livello} non trovato per il documento {self.id}")
        
        if approvazione.stato != "in_attesa":
            raise ValueError(f"Livello {livello} già {approvazione.stato}")
        
        # Approva il livello
        approvazione.stato = "approvato"
        approvazione.utente = utente
        approvazione.commento = commento
        approvazione.data = datetime.utcnow()
        
        # Aggiorna stato documento se è l'ultimo livello
        prossimo = self.get_prossimo_livello_da_approvare()
        if prossimo is None:
            self.stato_approvazione = "approvato"
            self.approvato_da = utente
            self.data_approvazione = datetime.utcnow()
        
        db.session.commit()
    
    def rifiuta_livello(self, livello, utente, commento=None):
        """
        Rifiuta un livello specifico del flusso.
        
        Args:
            livello (int): Livello da rifiutare.
            utente (str): Username di chi rifiuta.
            commento (str, optional): Commento del rifiuto.
        """
        from extensions import db
        from datetime import datetime
        
        approvazione = ApprovazioneDocumento.query.filter_by(
            document_id=self.id, 
            livello=livello
        ).first()
        
        if not approvazione:
            raise ValueError(f"Livello {livello} non trovato per il documento {self.id}")
        
        if approvazione.stato != "in_attesa":
            raise ValueError(f"Livello {livello} già {approvazione.stato}")
        
        # Rifiuta il livello
        approvazione.stato = "rifiutato"
        approvazione.utente = utente
        approvazione.commento = commento
        approvazione.data = datetime.utcnow()
        
        # Blocca il flusso
        self.stato_approvazione = "rifiutato"
        
        db.session.commit()
    
    def get_progresso_approvazione(self):
        """
        Calcola il progresso dell'approvazione in percentuale.
        
        Returns:
            int: Percentuale di completamento (0-100).
        """
        approvazioni = self.get_approvazioni_ordinate()
        if not approvazioni:
            return 0
        
        completate = sum(1 for a in approvazioni if a.stato in ["approvato", "rifiutato"])
        totale = len(approvazioni)
        
        return int((completate / totale) * 100)
    
    def can_be_approved_by(self, user):
        """
        Verifica se l'utente può approvare il prossimo livello.
        
        Args:
            user (User): Utente da verificare.
            
        Returns:
            tuple: (può_approvare, livello, messaggio).
        """
        prossimo = self.get_prossimo_livello_da_approvare()
        
        if not prossimo:
            return False, None, "Nessun livello in attesa di approvazione"
        
        if user.role != prossimo.ruolo_richiesto:
            return False, prossimo.livello, f"Ruolo richiesto: {prossimo.ruolo_richiesto}"
        
        return True, prossimo.livello, "Autorizzato"
    
    def calcola_prossima_revisione(self):
        """
        Calcola la prossima data di revisione basata sulla frequenza.
        
        Returns:
            datetime.date or None: Data prossima revisione
        """
        from datetime import timedelta
        
        if not self.data_ultima_revisione or not self.frequenza_revisione:
            return None
        
        frequenze = {
            "annuale": 365,
            "biennale": 730,
            "trimestrale": 90,
            "mensile": 30,
            "semestrale": 180
        }
        
        giorni = frequenze.get(self.frequenza_revisione, 0)
        if giorni == 0:
            return None
        
        return self.data_ultima_revisione + timedelta(days=giorni)
    
    def aggiorna_revisione(self, data_revisione=None):
        """
        Aggiorna la data di ultima revisione e ricalcola la prossima.
        
        Args:
            data_revisione (datetime.date, optional): Data revisione. Default oggi.
        """
        from datetime import date
        
        if data_revisione is None:
            data_revisione = date.today()
        
        self.data_ultima_revisione = data_revisione
        self.prossima_revisione = self.calcola_prossima_revisione()
        
        # Rimuovi task revisione esistente
        self.revisione_task_id = None
    
    @property
    def read_by(self):
        """Restituisce la lista degli utenti che hanno letto il documento."""
        return [log.user for log in self.read_logs]

    # Relazione per versioni AI (da implementare in futuro)
    # versioni_ai = db.relationship(
    #     "VersioneAnalisiAI",
    #     back_populates="documento",
    #     cascade="all, delete-orphan"
    # )

# === MODELLO AZIENDA ===
class Company(db.Model):
    """
    Modello azienda.

    Attributi:
        id (int): ID primario.
        name (str): Nome azienda.
        created_at (datetime): Data creazione.
        departments (list): Reparti associati.
        documents (list): Documenti associati.
    """
    __tablename__ = 'companies'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    departments = db.relationship('Department', backref='company', lazy=True)
    documents = db.relationship('Document', backref='company', lazy=True)

# === MODELLO DIPARTIMENTO ===
class Department(db.Model):
    """
    Modello reparto aziendale.

    Attributi:
        id (int): ID primario.
        name (str): Nome reparto.
        company_id (int): ID azienda.
        documents (list): Documenti associati.
    """
    __tablename__ = 'departments'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)

    documents = db.relationship('Document', backref='department', lazy=True)

# === MODELLO ATTIVITÀ OSPITE ===
class GuestActivity(db.Model):
    """
    Log attività ospite (view/download).

    Attributi:
        id (int): ID primario.
        guest_email (str): Email ospite.
        user_id (int): ID utente associato.
        document_id (int): ID documento.
        action (str): Tipo azione.
        timestamp (datetime): Data/ora.
    """
    __tablename__ = 'guest_activities'

    id = db.Column(db.Integer, primary_key=True)
    guest_email = db.Column(db.String(120))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))  # ✅ Associazione a User
    document_id = db.Column(db.Integer, db.ForeignKey('documents.id'))
    action = db.Column(db.String(50))  # view/download
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

# === MODELLO COMMENTI OSPITI ===
class GuestComment(db.Model):
    """
    Commento lasciato da ospite su documento.

    Attributi:
        id (int): ID primario.
        guest_email (str): Email ospite.
        document_id (int): ID documento.
        message (str): Messaggio.
        timestamp (datetime): Data/ora.
    """
    __tablename__ = 'guest_comments'

    id = db.Column(db.Integer, primary_key=True)
    guest_email = db.Column(db.String(120))
    document_id = db.Column(db.Integer, db.ForeignKey('documents.id'))
    message = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

# === MODELLO LOG ATTIVITÀ ADMIN ===
class AdminLog(db.Model):
    """
    Log attività amministrative.

    Attributi:
        id (int): ID primario.
        action (str): Azione.
        timestamp (datetime): Data/ora.
        performed_by (str): Chi ha eseguito.
        document_id (int): ID documento.
        downloadable (bool): Flag download.
    """
    __tablename__ = 'admin_log'

    id = db.Column(db.Integer, primary_key=True)
    action = db.Column(db.String(255), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    performed_by = db.Column(db.String(150), nullable=False)
    document_id = db.Column(db.Integer, db.ForeignKey('documents.id'))
    downloadable = db.Column(db.Boolean, default=False)
    extra_info = db.Column(db.Text, nullable=True)  # Informazioni aggiuntive per alert

# === MODELLO LINK/PASSWORD SICURE ===
class PasswordLink(db.Model):
    """
    Link/password sicura salvata dall'utente.

    Attributi:
        id (int): ID primario.
        title (str): Titolo.
        encrypted_password (bytes): Password criptata.
        url (str): URL associato.
        notes (str): Note.
        created_at (datetime): Data creazione.
        created_by_id (int): ID utente creatore.
    """
    __tablename__ = 'password_links'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    encrypted_password = db.Column(db.LargeBinary, nullable=False)
    url = db.Column(db.String(250), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))

# === MODELLO GUEST USER ===
class GuestUser(db.Model):
    """
    Modello utente guest (registrazione ospite).

    Attributi:
        id (int): ID primario.
        email (str): Email.
        password_hash (str): Hash password.
        registered_at (datetime): Data registrazione.
    """
    __tablename__ = 'guest_users'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    registered_at = db.Column(db.DateTime, default=datetime.utcnow)

# === MODELLO RICHIESTE ACCESSO DOCUMENTI ===
class AccessRequest(db.Model):
    __tablename__ = "access_requests"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    document_id = db.Column(db.Integer, db.ForeignKey("documents.id"), nullable=False)
    status = db.Column(db.String(20), default="pending")  # pending, approved, denied
    note = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    resolved_at = db.Column(db.DateTime, nullable=True)
    
    # === Campi per risposta AI automatica ===
    risposta_ai = db.Column(db.Text, nullable=True)  # Risposta formale generata dall'AI
    parere_ai = db.Column(db.Text, nullable=True)    # Parere AI per admin (es. "consigliato concedere")
    email_inviata = db.Column(db.Boolean, default=False)  # Se l'email è stata inviata
    email_destinatario = db.Column(db.String(150), nullable=True)  # Email destinatario
    email_testo = db.Column(db.Text, nullable=True)  # Testo email inviata
    email_inviata_at = db.Column(db.DateTime, nullable=True)  # Data invio email
    ai_analyzed_at = db.Column(db.DateTime, nullable=True)  # Data analisi AI

    user = db.relationship("User", backref="access_requests")
    document = db.relationship("Document", backref="access_requests")

    def __repr__(self):
        return f"<AccessRequest {self.id}: {self.user_id} -> {self.document_id} ({self.status})>"
    
    @property
    def has_ai_response(self):
        """Verifica se esiste una risposta AI."""
        return bool(self.risposta_ai)
    
    @property
    def ai_parere_display(self):
        """Restituisce il parere AI per visualizzazione."""
        if not self.parere_ai:
            return "Nessun parere AI"
        
        parere_lower = self.parere_ai.lower()
        if "consigliato" in parere_lower and "concedere" in parere_lower:
            return "✅ Consigliato concedere"
        elif "consigliato" in parere_lower and "negare" in parere_lower:
            return "❌ Consigliato negare"
        elif "valutare" in parere_lower:
            return "🤔 Richiede valutazione"
        else:
            return f"💬 {self.parere_ai}"
    
    @property
    def email_status_display(self):
        """Restituisce lo stato dell'email per visualizzazione."""
        if not self.email_inviata:
            return "📧 Non inviata"
        elif self.email_inviata and self.email_inviata_at:
            return f"✅ Inviata il {self.email_inviata_at.strftime('%d/%m/%Y %H:%M')}"
        else:
            return "📧 Inviata"

# === MODELLO LOG DOWNLOAD DOCUMENTI ===
class DownloadLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    document_id = db.Column(db.Integer, db.ForeignKey("documents.id"))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", backref="download_logs")
    document = db.relationship("Document", backref="download_logs")

class AuthorizedAccess(db.Model):
    __tablename__ = 'authorized_access'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    document_id = db.Column(db.Integer, db.ForeignKey('documents.id'), nullable=False)
    granted_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relazioni opzionali (utile per backref)
    user = db.relationship('User', backref='authorized_documents')
    document = db.relationship('Document', backref='authorized_users')

    __table_args__ = (
        db.UniqueConstraint('user_id', 'document_id', name='uix_user_document'),
    )

class DocumentActivityLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    document_id = db.Column(db.Integer, db.ForeignKey('documents.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    action = db.Column(db.String(50))  # es: 'download', 'access_denied', 'update', ecc.
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    note = db.Column(db.Text)

    document = db.relationship('Document', backref='activity_logs')
    user = db.relationship('User')

# === MODELLO LOG FIRME PRESA VISIONE DOCUMENTI ===
class DocumentReadLog(db.Model):
    __tablename__ = "document_read_logs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    document_id = db.Column(db.Integer, db.ForeignKey("documents.id"), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    # === Campi per conferma firma via email/PEC ===
    confermata = db.Column(db.Boolean, default=False)
    token_conferma = db.Column(db.String(64), nullable=True)
    data_conferma = db.Column(db.DateTime, nullable=True)
    
    # === Campo per associare firma a versione specifica ===
    version_id = db.Column(db.Integer, db.ForeignKey('document_versions.id'), nullable=True)
    
    # === Campi per tracciamento lettura ===
    is_first_read = db.Column(db.Boolean, default=True)  # Prima lettura
    read_duration = db.Column(db.Integer, nullable=True)  # Durata lettura in secondi
    ip_address = db.Column(db.String(45), nullable=True)  # IP del client
    user_agent = db.Column(db.Text, nullable=True)  # User agent del browser
    
    # Relazioni
    user = db.relationship("User", backref="read_logs")
    document = db.relationship("Document", backref="read_logs")

    def __repr__(self):
        """
        Rappresentazione stringa del log di lettura.

        Returns:
            str: Rappresentazione.
        """
        return f'<DocumentReadLog {self.user_id}:{self.document_id}:{self.timestamp}>'

    @property
    def stato_firma(self):
        """
        Restituisce lo stato della firma per visualizzazione.

        Returns:
            str: Stato della firma.
        """
        if not self.confermata:
            return "in_attesa"
        elif self.data_conferma:
            return "confermata"
        else:
            return "firmata"

# === MODELLO AUDIT LOG ===
class AuditLog(db.Model):
    """
    Modello per audit log di tutte le azioni critiche.

    Attributi:
        id (int): ID primario.
        user_id (int): ID utente che ha eseguito l'azione.
        document_id (int): ID documento coinvolto.
        azione (str): Tipo di azione ('approvazione_admin', 'approvazione_ceo', 'firma', 'download').
        timestamp (datetime): Data/ora dell'azione.
        user (User): Relazione con l'utente.
        document (Document): Relazione con il documento.
    """
    __tablename__ = 'audit_logs'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    document_id = db.Column(db.Integer, db.ForeignKey('documents.id'), nullable=False)
    azione = db.Column(db.String(50), nullable=False)  # 'approvazione_admin', 'approvazione_ceo', 'firma', 'download'
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    note = db.Column(db.Text, nullable=True)  # Note aggiuntive opzionali

    # Relazioni
    user = db.relationship('User', backref='audit_logs')
    document = db.relationship('Document', backref='audit_logs')

    def __repr__(self):
        """
        Rappresentazione stringa dell'audit log.

        Returns:
            str: Rappresentazione.
        """
        return f'<AuditLog {self.user.username}:{self.azione}:{self.document.title}:{self.timestamp}>'

    @property
    def azione_display(self):
        """
        Restituisce il nome visualizzabile dell'azione.

        Returns:
            str: Nome visualizzabile dell'azione.
        """
        azioni_map = {
            'approvazione_admin': '✅ Approvazione Admin',
            'approvazione_ceo': '👑 Approvazione CEO',
            'firma': '✍️ Firma/Presa Visione',
            'download': '📥 Download',
            'accesso_negato': '🚫 Accesso Negato',
            'visualizzazione': '👁️ Visualizzazione'
        }
        return azioni_map.get(self.azione, self.azione)

# === MODELLO VERSIONI DOCUMENTI ===
class DocumentVersion(db.Model):
    """
    Modello per le versioni dei documenti con analisi AI avanzata.
    
    Attributi:
        id (int): ID primario.
        document_id (int): ID del documento principale.
        version_number (int): Numero progressivo della versione.
        uploaded_at (datetime): Data e ora di upload.
        uploaded_by (str): Username di chi ha caricato la versione.
        file_path (str): Percorso del file della versione.
        notes (str): Note opzionali sulla versione.
        ai_summary (str): Descrizione AI della versione.
        diff_ai (str): Differenze con versione precedente (analisi AI).
        is_active (bool): Se questa è la versione attualmente attiva.
        document (Document): Relazione con il documento principale.
    """
    __tablename__ = "document_versions"
    
    id = db.Column(db.Integer, primary_key=True)
    document_id = db.Column(db.Integer, db.ForeignKey("documents.id"), nullable=False)
    version_number = db.Column(db.Integer, nullable=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    uploaded_by = db.Column(db.String(150))
    file_path = db.Column(db.String(255))
    notes = db.Column(db.Text)
    ai_summary = db.Column(db.Text)  # descrizione AI della versione
    diff_ai = db.Column(db.Text)     # differenze con versione precedente
    is_active = db.Column(db.Boolean, default=False)

    document = db.relationship("Document", backref="versions")
    
    def __repr__(self):
        return f"<DocumentVersion(id={self.id}, document_id={self.document_id}, version={self.version_number})>"
    
    @property
    def uploaded_at_formatted(self):
        """Restituisce la data formattata."""
        return self.uploaded_at.strftime('%d/%m/%Y %H:%M') if self.uploaded_at else "N/A"
    
    @property
    def file_size(self):
        """Restituisce la dimensione del file in MB."""
        try:
            if os.path.exists(self.file_path):
                size_bytes = os.path.getsize(self.file_path)
                return round(size_bytes / (1024 * 1024), 2)
            return 0
        except:
            return 0
    
    @property
    def status_display(self):
        """Restituisce lo stato visualizzabile."""
        return "✅ Attiva" if self.is_active else "📄 Storico"
    
    @property
    def has_ai_analysis(self):
        """Verifica se la versione ha analisi AI."""
        return bool(self.ai_summary or self.diff_ai)
    
    @property
    def diff_ai_preview(self):
        """Anteprima delle differenze AI (primi 100 caratteri)."""
        if self.diff_ai:
            return self.diff_ai[:100] + "..." if len(self.diff_ai) > 100 else self.diff_ai
        return None

class DownloadDeniedLog(db.Model):
    """
    Modello per tracciare i tentativi di download negati.
    
    Attributi:
        id (int): ID primario.
        user_id (int): ID utente che ha tentato il download.
        document_id (int): ID documento richiesto.
        reason (str): Motivo del rifiuto (es. "Documento scaduto", "Firma mancante").
        timestamp (datetime): Data/ora del tentativo.
        ip_address (str): IP del client.
        user_agent (str): User agent del browser.
        user (User): Relazione con l'utente.
        document (Document): Relazione con il documento.
    """
    __tablename__ = "download_denied_logs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    document_id = db.Column(db.Integer, db.ForeignKey("documents.id"), nullable=False)
    reason = db.Column(db.String(255), nullable=False)  # es. "Documento scaduto", "Firma mancante", "Permessi insufficienti"
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    ip_address = db.Column(db.String(45), nullable=True)  # IPv4 or IPv6
    user_agent = db.Column(db.Text, nullable=True)

    # Relazioni
    user = db.relationship("User", backref="denied_download_logs")
    document = db.relationship("Document", backref="denied_download_logs")

    def __repr__(self):
        return f'<DownloadDeniedLog {self.user.username} denied access to {self.document.title} for reason "{self.reason}">'


class InsightAI(db.Model):
    """
    Modello per salvare gli insight generati dall'AI.
    
    Attributi:
        id (int): ID primario.
        insight_text (str): Testo dell'insight in linguaggio naturale.
        insight_type (str): Tipo di insight (sicurezza, firma, ripetizione, pattern).
        severity (str): Severità (critico, attenzione, informativo).
        status (str): Stato (attivo, risolto, ignorato).
        created_at (datetime): Data creazione.
        resolved_at (datetime): Data risoluzione (se risolto).
        resolved_by (str): Chi ha risolto l'insight.
        action_taken (str): Azione intrapresa (task, email, ecc.).
        affected_users (str): JSON con utenti coinvolti.
        affected_documents (str): JSON con documenti coinvolti.
        pattern_data (str): JSON con dati del pattern rilevato.
    """
    __tablename__ = "insight_ai"

    id = db.Column(db.Integer, primary_key=True)
    insight_text = db.Column(db.Text, nullable=False)
    insight_type = db.Column(db.String(50), nullable=False)  # sicurezza, firma, ripetizione, pattern
    severity = db.Column(db.String(20), nullable=False)  # critico, attenzione, informativo
    status = db.Column(db.String(20), default="attivo")  # attivo, risolto, ignorato
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    resolved_at = db.Column(db.DateTime, nullable=True)
    resolved_by = db.Column(db.String(100), nullable=True)
    action_taken = db.Column(db.Text, nullable=True)  # Azione intrapresa (task, email, ecc.)
    
    # Dati di contesto per l'insight
    affected_users = db.Column(db.Text, nullable=True)  # JSON con utenti coinvolti
    affected_documents = db.Column(db.Text, nullable=True)  # JSON con documenti coinvolti
    pattern_data = db.Column(db.Text, nullable=True)  # JSON con dati del pattern rilevato
    
    # === Campi per trasformazione in task ===
    task_id = db.Column(db.Integer, db.ForeignKey('tasks.id'), nullable=True)
    trasformato_in_task = db.Column(db.Boolean, default=False)
    task = db.relationship("Task", backref="related_insight", uselist=False, foreign_keys=[task_id])

    def __repr__(self):
        return f"<InsightAI(id={self.id}, type='{self.insight_type}', severity='{self.severity}', status='{self.status}')>"


# === MODELLO TASK AI ===
class TaskAI(db.Model):
    """
    Modello per la gestione dei task AI personali.
    
    Attributi:
        id (int): ID primario.
        user_id (int): ID utente assegnato.
        titolo (str): Titolo del task.
        descrizione (str): Descrizione dettagliata.
        data_scadenza (datetime): Data di scadenza.
        priorita (PrioritaTask): Priorità (Low, Medium, High).
        origine (OrigineTask): Origine del task (AI, Diario, Deep Work, Manuale).
        stato (bool): Stato del task (False = da fare, True = completato).
        data_creazione (datetime): Data creazione.
    """
    __tablename__ = "task_ai"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    titolo = db.Column(db.String(255), nullable=False)
    descrizione = db.Column(db.Text, nullable=True)
    data_scadenza = db.Column(db.DateTime, nullable=True)
    priorita = db.Column(db.Enum(PrioritaTask), default=PrioritaTask.MEDIUM)
    origine = db.Column(db.Enum(OrigineTask), default=OrigineTask.MANUALE)
    stato = db.Column(db.Boolean, default=False)  # False = da fare, True = completato
    data_creazione = db.Column(db.DateTime, default=datetime.utcnow)

    # Relazioni
    utente = db.relationship("User", back_populates="tasks_ai")

    def __repr__(self):
        return f"<TaskAI(id={self.id}, titolo={self.titolo}, user_id={self.user_id}, completato={self.stato})>"
    
    @property
    def is_completed(self):
        """Verifica se il task è completato."""
        return self.stato
    
    @property
    def is_overdue(self):
        """Verifica se il task è scaduto."""
        if self.data_scadenza and not self.stato:
            return datetime.utcnow() > self.data_scadenza
        return False
    
    @property
    def days_until_deadline(self):
        """Giorni rimanenti alla scadenza."""
        if self.data_scadenza:
            delta = self.data_scadenza - datetime.utcnow()
            return delta.days
        return None
    
    @property
    def priority_color(self):
        """Restituisce il colore Bootstrap per la priorità."""
        colors = {
            PrioritaTask.LOW: "success",
            PrioritaTask.MEDIUM: "info", 
            PrioritaTask.HIGH: "warning"
        }
        return colors.get(self.priorita, "secondary")
    
    @property
    def status_color(self):
        """Colore del badge in base allo stato."""
        if self.stato:
            return 'bg-success'
        return 'bg-secondary'
    
    @property
    def origine_badge_class(self):
        """Classe badge per l'origine del task."""
        colors = {
            OrigineTask.AI: 'bg-primary',
            OrigineTask.DIARIO: 'bg-info',
            OrigineTask.DEEP_WORK: 'bg-warning',
            OrigineTask.MANUALE: 'bg-secondary'
        }
        return colors.get(self.origine, 'bg-secondary')
    
    @property
    def origine_display(self):
        """Display name per l'origine del task."""
        display_names = {
            OrigineTask.AI: '🤖 AI',
            OrigineTask.DIARIO: '📝 Diario',
            OrigineTask.DEEP_WORK: '🧠 Deep Work',
            OrigineTask.MANUALE: '✏️ Manuale'
        }
        return display_names.get(self.origine, self.origine.value)

# === MODELLO TASK (LEGACY - MANTENUTO PER COMPATIBILITÀ) ===
class Task(db.Model):
    """
    Modello per la gestione dei task generati dall'AI (legacy).
    
    Attributi:
        id (int): ID primario.
        user_id (int): ID utente assegnato.
        titolo (str): Titolo del task.
        descrizione (str): Descrizione dettagliata.
        priorita (str): Priorità (Bassa, Media, Alta, Critica).
        assegnato_a (str): Email dell'utente assegnato.
        stato (str): Stato del task (Da fare, In corso, Completato, Annullato).
        scadenza (datetime): Data di scadenza.
        created_at (datetime): Data creazione.
        completed_at (datetime): Data completamento.
        created_by (str): Email di chi ha creato il task.
        insight_id (int): ID dell'insight che ha generato il task.
        origine (str): Origine del task (AI, Diario, Deep Work, Manuale).
    """
    __tablename__ = "tasks"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)  # Utente assegnato
    titolo = db.Column(db.String(200), nullable=False)
    descrizione = db.Column(db.Text, nullable=True)
    priorita = db.Column(db.String(20), default="Media")  # Bassa, Media, Alta, Critica
    assegnato_a = db.Column(db.String(150), nullable=True)
    stato = db.Column(db.String(20), default="Da fare")  # Da fare, In corso, Completato, Annullato
    scadenza = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)
    created_by = db.Column(db.String(150), nullable=False)
    origine = db.Column(db.String(50), default="Manuale")  # AI, Diario, Deep Work, Manuale
    
    # Relazioni
    user = db.relationship("User", backref="tasks")
    insight_id = db.Column(db.Integer, db.ForeignKey('insight_ai.id'), nullable=True)
    insight = db.relationship("InsightAI", backref="tasks", uselist=False, foreign_keys=[insight_id])

    def __repr__(self):
        return f"<Task(id={self.id}, titolo='{self.titolo}', stato='{self.stato}', priorita='{self.priorita}')>"
    
    @property
    def is_overdue(self):
        """Verifica se il task è scaduto."""
        if self.scadenza and self.stato not in ["Completato", "Annullato"]:
            return datetime.utcnow() > self.scadenza
        return False
    
    @property
    def priority_color(self):
        """Restituisce il colore Bootstrap per la priorità."""
        colors = {
            "Bassa": "success",
            "Media": "info", 
            "Alta": "warning",
            "Critica": "danger"
        }
        return colors.get(self.priorita, "secondary")
    
    @property
    def status_color(self):
        """
        Colore del badge in base allo stato.

        Returns:
            str: Classe CSS per il colore.
        """
        colors = {
            'Da fare': 'bg-secondary',
            'In corso': 'bg-warning',
            'Completato': 'bg-success',
            'Annullato': 'bg-danger'
        }
        return colors.get(self.stato, 'bg-secondary')
    
    @property
    def origine_badge_class(self):
        """
        Classe badge per l'origine del task.
        
        Returns:
            str: Classe CSS per il badge.
        """
        colors = {
            'AI': 'bg-primary',
            'Diario': 'bg-info',
            'Deep Work': 'bg-warning',
            'Manuale': 'bg-secondary'
        }
        return colors.get(self.origine, 'bg-secondary')
    
    @property
    def origine_display(self):
        """
        Display name per l'origine del task.
        
        Returns:
            str: Nome visualizzato per l'origine.
        """
        display_names = {
            'AI': '🤖 AI',
            'Diario': '📝 Diario',
            'Deep Work': '🧠 Deep Work',
            'Manuale': '✏️ Manuale'
        }
        return display_names.get(self.origine, self.origine)
    
    @property
    def is_completed(self):
        """
        Verifica se il task è completato.
        
        Returns:
            bool: True se completato.
        """
        return self.stato == "Completato"
    
    @property
    def is_overdue(self):
        """
        Verifica se il task è scaduto.
        
        Returns:
            bool: True se scaduto.
        """
        if self.scadenza and self.stato not in ["Completato", "Annullato"]:
            return datetime.utcnow() > self.scadenza
        return False
    
    @property
    def days_until_deadline(self):
        """
        Giorni rimanenti alla scadenza.
        
        Returns:
            int: Giorni rimanenti (negativo se scaduto).
        """
        if self.scadenza:
            delta = self.scadenza - datetime.utcnow()
            return delta.days
        return None

# === MODELLO LOG APPROVAZIONI DOCUMENTI ===
class DocumentApprovalLog(db.Model):
    """
    Modello per tracciare lo storico delle approvazioni documenti.
    
    Attributi:
        id (int): ID primario.
        document_id (int): ID del documento approvato.
        approver_id (int): ID dell'utente che ha approvato.
        approver_role (str): Ruolo dell'approvatore (admin, ceo, ai).
        timestamp (datetime): Data/ora dell'approvazione.
        action (str): Tipo di azione (approved, rejected, commented).
        method (str): Metodo di approvazione (manual, AI).
        note (str): Note aggiuntive dell'approvazione.
        document (Document): Relazione con il documento.
        approver (User): Relazione con l'utente approvatore.
    """
    __tablename__ = "document_approval_logs"

    id = db.Column(db.Integer, primary_key=True)
    document_id = db.Column(db.Integer, db.ForeignKey("documents.id"), nullable=False)
    approver_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    approver_role = db.Column(db.String(50), nullable=False)  # admin, ceo, ai
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    action = db.Column(db.String(50), nullable=False)  # approved, rejected, commented
    method = db.Column(db.String(50), nullable=False)  # manual, AI
    note = db.Column(db.Text, nullable=True)

    # Relazioni
    document = db.relationship("Document", backref="approval_logs")
    approver = db.relationship("User", backref="approvals")

    def __repr__(self):
        """
        Rappresentazione stringa del log approvazione.

        Returns:
            str: Rappresentazione.
        """
        return f'<DocumentApprovalLog {self.action} by {self.approver_id} on {self.document_id}>'

    @property
    def action_display(self):
        """
        Testo visualizzabile per l'azione.

        Returns:
            str: Testo dell'azione.
        """
        actions = {
            'approved': '✅ Approvato',
            'rejected': '❌ Respinto',
            'commented': '💬 Commentato',
            'submitted': '📤 Inviato per approvazione',
            'auto_approved': '🤖 Approvato automaticamente'
        }
        return actions.get(self.action, self.action.capitalize())

    @property
    def method_display(self):
        """
        Testo visualizzabile per il metodo.

        Returns:
            str: Testo del metodo.
        """
        methods = {
            'manual': '👤 Manuale',
            'AI': '🧠 AI',
            'auto': '🤖 Automatico'
        }
        return methods.get(self.method, self.method.capitalize())

    @property
    def approver_display(self):
        """
        Nome visualizzabile dell'approvatore.

        Returns:
            str: Nome dell'approvatore.
        """
        if self.approver:
            if self.approver.first_name and self.approver.last_name:
                return f"{self.approver.first_name} {self.approver.last_name}"
            elif self.approver.username:
                return self.approver.username
            else:
                return self.approver.email
        return "Utente sconosciuto"

    @property
    def document_title(self):
        """
        Titolo del documento.

        Returns:
            str: Titolo del documento.
        """
        if self.document:
            return self.document.title
        return "Documento non trovato"

    @property
    def is_ai_approval(self):
        """
        Verifica se è un'approvazione AI.

        Returns:
            bool: True se approvazione AI.
        """
        return self.method in ['AI', 'auto'] or self.action == 'auto_approved'

# === MODELLO STEP APPROVAZIONE MULTI-STEP ===
class ApprovalStep(db.Model):
    """
    Modello per gestire i step di approvazione multi-step dei documenti.
    
    Attributi:
        id (int): ID primario.
        document_id (int): ID del documento.
        step_name (str): Nome dello step (es. 'Validazione Manager').
        approver_id (int): ID dell'approvatore assegnato.
        approver_role (str): Ruolo richiesto per l'approvazione.
        status (str): Stato dello step (pending, approved, rejected).
        approved_at (datetime): Data/ora approvazione.
        method (str): Metodo di approvazione (manual, AI).
        note (str): Note aggiuntive dello step.
        auto_approval (bool): Flag per approvazione automatica.
        document (Document): Relazione con il documento.
        approver (User): Relazione con l'approvatore.
    """
    __tablename__ = 'approval_steps'

    id = db.Column(db.Integer, primary_key=True)
    document_id = db.Column(db.Integer, db.ForeignKey('documents.id'), nullable=False)
    step_name = db.Column(db.String(100), nullable=False)  # Es: 'Validazione Manager'
    approver_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    approver_role = db.Column(db.String(50))  # Es: 'manager', 'admin', 'ceo'
    status = db.Column(db.String(20), default='pending')  # 'pending', 'approved', 'rejected'
    approved_at = db.Column(db.DateTime, nullable=True)
    method = db.Column(db.String(50), default='manual')  # 'manual', 'ai'
    note = db.Column(db.Text, nullable=True)
    auto_approval = db.Column(db.Boolean, default=False)  # Flag per approvazione automatica

    # Relazioni
    document = db.relationship("Document", backref="approval_steps")
    approver = db.relationship("User", backref="approval_steps")

    def __repr__(self):
        """
        Rappresentazione stringa dello step di approvazione.

        Returns:
            str: Rappresentazione.
        """
        return f'<ApprovalStep {self.step_name} for document {self.document_id}>'

    @property
    def status_display(self):
        """
        Testo visualizzabile per lo stato.

        Returns:
            str: Testo dello stato.
        """
        status_map = {
            'pending': '⏳ In attesa',
            'approved': '✅ Approvato',
            'rejected': '❌ Respinto',
            'in_progress': '🔄 In corso'
        }
        return status_map.get(self.status, self.status.capitalize())

    @property
    def status_badge_class(self):
        """
        Classe CSS per il badge dello stato.

        Returns:
            str: Classe CSS per il badge.
        """
        badge_classes = {
            'pending': 'bg-warning text-dark',
            'approved': 'bg-success',
            'rejected': 'bg-danger',
            'in_progress': 'bg-info'
        }
        return badge_classes.get(self.status, 'bg-secondary')

    @property
    def method_display(self):
        """
        Testo visualizzabile per il metodo.

        Returns:
            str: Testo del metodo.
        """
        methods = {
            'manual': '👤 Manuale',
            'AI': '🧠 AI',
            'auto': '🤖 Automatico'
        }
        return methods.get(self.method, self.method.capitalize())

    @property
    def approver_display(self):
        """
        Nome visualizzabile dell'approvatore.

        Returns:
            str: Nome dell'approvatore.
        """
        if self.approver:
            if self.approver.first_name and self.approver.last_name:
                return f"{self.approver.first_name} {self.approver.last_name}"
            elif self.approver.username:
                return self.approver.username
            else:
                return self.approver.email
        return "Non assegnato"

    @property
    def is_ai_approval(self):
        """
        Verifica se è un'approvazione AI.

        Returns:
            bool: True se approvazione AI.
        """
        return self.method in ['AI', 'auto']

    @property
    def can_be_approved_by(self, user):
        """
        Verifica se l'utente può approvare questo step.

        Args:
            user (User): Utente da verificare.

        Returns:
            bool: True se l'utente può approvare.
        """
        if not user:
            return False
        
        # Se è l'approvatore assegnato
        if self.approver_id and self.approver_id == user.id:
            return True
        
        # Se ha il ruolo richiesto
        if self.approver_role and user.role == self.approver_role:
            return True
        
        # Se è admin/CEO e lo step non ha approvatore specifico
        if user.is_admin or user.is_ceo:
            return True
        
        return False

    @property
    def is_completed(self):
        """
        Verifica se lo step è completato.

        Returns:
            bool: True se lo step è completato.
        """
        return self.status in ['approved', 'rejected']

    @property
    def is_pending(self):
        """
        Verifica se lo step è in attesa.

        Returns:
            bool: True se lo step è in attesa.
        """
        return self.status == 'pending'

    @property
    def is_rejected(self):
        """
        Verifica se lo step è stato respinto.

        Returns:
            bool: True se lo step è stato respinto.
        """
        return self.status == 'rejected'

    @property
    def approval_date_formatted(self):
        """
        Data di approvazione formattata.

        Returns:
            str: Data formattata o '—' se non approvato.
        """
        if self.approved_at:
            return self.approved_at.strftime('%d/%m/%Y %H:%M')
        return '—'


# === MODELLO INSIGHT QMS AI ===
class InsightQMSAI(db.Model):
    """
    Modello per gli insight AI del sistema QMS.
    
    Attributi:
        id (int): ID primario.
        insight_text (str): Testo dell'insight in linguaggio naturale.
        insight_type (str): Tipo di insight (scadenza, mancante, revisione, struttura).
        severity (str): Severità (critico, attenzione, informativo).
        stato (str): Stato (attivo, risolto, ignorato).
        documento_id (int): ID del documento QMS coinvolto.
        modulo_qms (str): Modulo QMS di riferimento.
        data_creazione (datetime): Data creazione.
        task_id (int): ID del task associato (se trasformato).
        documento (DocumentiQMS): Relazione con il documento QMS.
        task (Task): Relazione con il task generato.
    """
    __tablename__ = "insight_qms_ai"
    
    id = db.Column(db.Integer, primary_key=True)
    insight_text = db.Column(db.Text, nullable=False)
    insight_type = db.Column(db.String(50), nullable=False)  # scadenza, mancante, revisione, struttura
    severity = db.Column(db.String(20), nullable=False)  # critico, attenzione, informativo
    stato = db.Column(db.String(20), default="attivo")  # attivo, risolto, ignorato
    documento_id = db.Column(db.Integer, nullable=True)  # Rimosso ForeignKey per tabella inesistente
    modulo_qms = db.Column(db.String(50), nullable=True)
    data_creazione = db.Column(db.DateTime, default=datetime.utcnow)
    task_id = db.Column(db.Integer, db.ForeignKey('tasks.id'), nullable=True)
    
    # Relazioni
    # documento = db.relationship("DocumentiQMS", backref="insights_ai")
    task = db.relationship("Task", backref="qms_insight", uselist=False, foreign_keys=[task_id])
    
    def __repr__(self):
        """
        Rappresentazione stringa dell'insight QMS AI.

        Returns:
            str: Rappresentazione.
        """
        return f'<InsightQMSAI {self.insight_type}:{self.severity}:{self.stato}>'

# === MODELLO EVENTO FORMAZIONE ===
class EventoFormazione(db.Model):
    """
    Modello per gli eventi di formazione.
    
    Attributi:
        id (int): ID primario.
        titolo (str): Titolo dell'evento.
        descrizione (str): Descrizione dell'evento.
        data_evento (datetime): Data dell'evento.
        durata_ore (int): Durata in ore.
        luogo (str): Luogo dell'evento.
        trainer (str): Nome del trainer.
        max_partecipanti (int): Numero massimo partecipanti.
        stato (str): Stato dell'evento (programmato, in_corso, completato, annullato).
        created_at (datetime): Data creazione.
        partecipazioni (list): Lista delle partecipazioni.
    """
    __tablename__ = 'eventi_formazione'
    
    id = db.Column(db.Integer, primary_key=True)
    titolo = db.Column(db.String(200), nullable=False)
    descrizione = db.Column(db.Text, nullable=True)
    data_evento = db.Column(db.DateTime, nullable=True)
    durata_ore = db.Column(db.Integer, default=1)
    luogo = db.Column(db.String(200), nullable=True)
    trainer = db.Column(db.String(100), nullable=True)
    max_partecipanti = db.Column(db.Integer, nullable=True)
    stato = db.Column(db.String(20), default='programmato')  # programmato, in_corso, completato, annullato
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relazioni
    partecipazioni = db.relationship('PartecipazioneFormazione', backref='evento', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        """
        Rappresentazione stringa dell'evento formazione.

        Returns:
            str: Rappresentazione.
        """
        return f'<EventoFormazione {self.titolo}:{self.data_evento}>'
    
    @property
    def partecipanti_totali(self):
        """
        Restituisce il numero totale di partecipanti.

        Returns:
            int: Numero totale partecipanti.
        """
        return len(self.partecipazioni)
    
    @property
    def partecipanti_firmati(self):
        """
        Restituisce il numero di partecipanti che hanno firmato la presenza.

        Returns:
            int: Numero partecipanti con firma.
        """
        return sum(1 for p in self.partecipazioni if p.firma_presenza_path)
    
    @property
    def attestati_completati(self):
        """
        Restituisce il numero di attestati completati.

        Returns:
            int: Numero attestati completati.
        """
        return sum(1 for p in self.partecipazioni if p.attestato_path and p.completato)
    
    @property
    def percentuale_copertura(self):
        """
        Restituisce la percentuale di copertura attestati.

        Returns:
            float: Percentuale di copertura.
        """
        if self.partecipanti_totali == 0:
            return 0.0
        return round((self.attestati_completati / self.partecipanti_totali) * 100, 1)
    
    @property
    def stato_copertura(self):
        """
        Restituisce lo stato della copertura attestati.

        Returns:
            str: Stato copertura (completato, parziale, incompleto).
        """
        if self.percentuale_copertura == 100:
            return "completato"
        elif self.percentuale_copertura >= 60:
            return "parziale"
        else:
            return "incompleto"

# === MODELLO PARTECIPAZIONE FORMAZIONE ===
class PartecipazioneFormazione(db.Model):
    """
    Modello per le partecipazioni agli eventi di formazione.
    
    Attributi:
        id (int): ID primario.
        evento_id (int): ID dell'evento.
        user_id (int): ID dell'utente partecipante.
        data_iscrizione (datetime): Data iscrizione.
        stato_partecipazione (str): Stato (iscritto, presente, assente, completato).
        firma_presenza_path (str): Percorso file firma presenza.
        attestato_path (str): Percorso file attestato.
        completato (bool): Flag completamento.
        data_completamento (datetime): Data completamento.
        note (str): Note aggiuntive.
        user (User): Relazione con l'utente.
        evento (EventoFormazione): Relazione con l'evento.
    """
    __tablename__ = 'partecipazioni_formazione'
    
    id = db.Column(db.Integer, primary_key=True)
    evento_id = db.Column(db.Integer, db.ForeignKey('eventi_formazione.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    data_iscrizione = db.Column(db.DateTime, default=datetime.utcnow)
    stato_partecipazione = db.Column(db.String(20), default='iscritto')  # iscritto, presente, assente, completato
    firma_presenza_path = db.Column(db.String(255), nullable=True)
    attestato_path = db.Column(db.String(255), nullable=True)
    completato = db.Column(db.Boolean, default=False)
    data_completamento = db.Column(db.DateTime, nullable=True)
    note = db.Column(db.Text, nullable=True)
    
    # Relazioni
    user = db.relationship('User', backref='partecipazioni_formazione')
    
    def __repr__(self):
        """
        Rappresentazione stringa della partecipazione.

        Returns:
            str: Rappresentazione.
        """
        return f'<PartecipazioneFormazione {self.user_id}:{self.evento_id}:{self.stato_partecipazione}>'
    
    @property
    def ha_firmato_presenza(self):
        """
        Verifica se ha firmato la presenza.

        Returns:
            bool: True se ha firmato.
        """
        return self.firma_presenza_path is not None
    
    @property
    def ha_attestato(self):
        """
        Verifica se ha l'attestato.

        Returns:
            bool: True se ha attestato.
        """
        return self.attestato_path is not None and self.completato
    
    @property
    def stato_display(self):
        """
        Restituisce lo stato visualizzabile.

        Returns:
            str: Stato visualizzabile.
        """
        stati_map = {
            'iscritto': '📝 Iscritto',
            'presente': '✅ Presente',
            'assente': '❌ Assente',
            'completato': '🎓 Completato'
        }
        return stati_map.get(self.stato_partecipazione, self.stato_partecipazione)
    
    @property
    def badge_class(self):
        """
        Restituisce la classe CSS per il badge dello stato.

        Returns:
            str: Classe CSS badge.
        """
        classi_map = {
            'iscritto': 'secondary',
            'presente': 'info',
            'assente': 'danger',
            'completato': 'success'
        }
        return classi_map.get(self.stato_partecipazione, 'secondary')


# === MODELLO FIRMA DOCUMENTO ===
class FirmaDocumento(db.Model):
    """
    Modello per gestire le firme elettroniche sui documenti.
    
    Attributi:
        id (int): ID primario.
        document_id (int): ID del documento firmato.
        user_id (int): ID dell'utente che ha firmato.
        data_firma (datetime): Data/ora della firma.
        nome_firma (str): Nome inserito dall'utente per la firma.
        ip_address (str): IP del client al momento della firma.
        user_agent (str): User agent del browser.
        document (Document): Relazione con il documento.
        user (User): Relazione con l'utente.
    """
    __tablename__ = "firme_documenti"
    
    id = db.Column(db.Integer, primary_key=True)
    document_id = db.Column(db.Integer, db.ForeignKey("documents.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    nome_firma = db.Column(db.String(200), nullable=False)
    data_firma = db.Column(db.DateTime, default=datetime.utcnow)
    ip = db.Column(db.String(50), nullable=True)
    user_agent = db.Column(db.String(255), nullable=True)
    firma_immagine = db.Column(db.String(255), nullable=True)  # path PNG firma
    
    # === Campi per validazione gerarchica ===
    firma_admin = db.Column(db.Boolean, default=False)  # Validazione admin
    data_firma_admin = db.Column(db.DateTime, nullable=True)  # Data validazione admin
    approvato_dal_ceo = db.Column(db.Boolean, default=False)  # Approvazione finale CEO
    data_firma_ceo = db.Column(db.DateTime, nullable=True)  # Data approvazione CEO
    
    # === Campi per invio automatico ===
    inviato_auto = db.Column(db.Boolean, default=False)  # Indica se il documento è già stato inviato
    data_invio_auto = db.Column(db.DateTime, nullable=True)  # Data e ora dell'invio automatico
    email_inviata_a = db.Column(db.String(255), nullable=True)  # Email del destinatario (o lista)
    errore_invio = db.Column(db.String(255), nullable=True)  # Eventuale messaggio di errore per il retry

    document = db.relationship("Document", backref="firme")
    user = db.relationship("User", backref="firme_documenti")

    def __repr__(self):
        return f"<FirmaDocumento(id={self.id}, document_id={self.document_id}, user_id={self.user_id})>"
    
    @property
    def data_firma_formatted(self):
        """Restituisce la data della firma formattata."""
        return self.data_firma.strftime('%d/%m/%Y %H:%M')
    
    @property
    def firma_completa(self):
        """Restituisce la firma completa con nome e data."""
        return f"{self.nome_firma} - {self.data_firma_formatted}"
    
    @property
    def stato_firma_gerarchica(self):
        """Restituisce lo stato della firma gerarchica."""
        if self.approvato_dal_ceo:
            return "approvato"
        elif self.firma_admin:
            return "in_attesa_ceo"
        elif self.data_firma:
            return "firmato_utente"
        else:
            return "non_firmato"
    
    @property
    def stato_firma_display(self):
        """Restituisce lo stato visualizzabile della firma."""
        stati = {
            "approvato": "✅ Approvato",
            "in_attesa_ceo": "⚠️ In attesa CEO",
            "firmato_utente": "📝 Firmato Utente",
            "non_firmato": "❌ Non firmato"
        }
        return stati.get(self.stato_firma_gerarchica, "❓ Stato sconosciuto")
    
    @property
    def badge_class_stato(self):
        """Restituisce la classe CSS per il badge dello stato."""
        classi = {
            "approvato": "bg-success",
            "in_attesa_ceo": "bg-warning text-dark",
            "firmato_utente": "bg-info",
            "non_firmato": "bg-danger"
        }
        return classi.get(self.stato_firma_gerarchica, "bg-secondary")
    
    @property
    def stato_invio_auto(self):
        """Restituisce lo stato dell'invio automatico."""
        if self.inviato_auto and not self.errore_invio:
            return "inviato"
        elif self.inviato_auto and self.errore_invio:
            return "errore"
        elif self.approvato_dal_ceo and not self.inviato_auto:
            return "da_inviare"
        else:
            return "non_applicabile"
    
    @property
    def stato_invio_display(self):
        """Restituisce lo stato visualizzabile dell'invio."""
        stati = {
            "inviato": "✅ Inviato",
            "errore": "❌ Errore Invio",
            "da_inviare": "📤 Da Inviare",
            "non_applicabile": "⏸️ Non Applicabile"
        }
        return stati.get(self.stato_invio_auto, "❓ Stato sconosciuto")
    
    @property
    def badge_class_invio(self):
        """Restituisce la classe CSS per il badge dell'invio."""
        classi = {
            "inviato": "bg-success",
            "errore": "bg-danger",
            "da_inviare": "bg-warning text-dark",
            "non_applicabile": "bg-secondary"
        }
        return classi.get(self.stato_invio_auto, "bg-secondary")

class DocumentoAIInsight(db.Model):
    """
    Modello per gli insight AI sui documenti.
    
    Attributi:
        id (int): ID primario.
        document_id (int): ID del documento analizzato.
        tipo (str): Tipo di insight (duplicato, obsoleto, vecchio, inutilizzato).
        valore (str): Dettagli dell'insight (ID documento simile, note, ecc.).
        timestamp (datetime): Data/ora dell'analisi.
        severity (str): Severità (critico, attenzione, informativo).
        status (str): Stato (attivo, risolto, ignorato).
        document (Document): Relazione con il documento.
    """
    __tablename__ = "document_ai_insights"
    
    id = db.Column(db.Integer, primary_key=True)
    document_id = db.Column(db.Integer, db.ForeignKey('documents.id'), nullable=False)
    tipo = db.Column(db.String(50), nullable=False)  # duplicato, obsoleto, vecchio, inutilizzato
    valore = db.Column(db.String(500), nullable=True)  # ID documento simile o note
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    severity = db.Column(db.String(20), default="attenzione")  # critico, attenzione, informativo
    status = db.Column(db.String(20), default="attivo")  # attivo, risolto, ignorato
    
    # Relazioni
    document = db.relationship("Document", backref="ai_insights")
    
    def __repr__(self):
        """
        Rappresentazione stringa dell'insight AI.

        Returns:
            str: Rappresentazione.
        """
        return f'<DocumentoAIInsight {self.document_id}:{self.tipo}:{self.severity}>'
    
    @property
    def tipo_display(self):
        """
        Restituisce il tipo visualizzabile.

        Returns:
            str: Tipo visualizzabile.
        """
        tipi_map = {
            'duplicato': '🔄 Duplicato',
            'obsoleto': '⚠️ Obsoleto',
            'vecchio': '📅 Vecchio',
            'inutilizzato': '📊 Inutilizzato'
        }
        return tipi_map.get(self.tipo, self.tipo)
    
    @property
    def severity_badge_class(self):
        """
        Restituisce la classe CSS per il badge della severità.

        Returns:
            str: Classe CSS badge.
        """
        classi_map = {
            'critico': 'danger',
            'attenzione': 'warning',
            'informativo': 'info'
        }
        return classi_map.get(self.severity, 'secondary')
    
    @property
    def status_badge_class(self):
        """
        Restituisce la classe CSS per il badge dello stato.

        Returns:
            str: Classe CSS badge.
        """
        classi_map = {
            'attivo': 'primary',
            'risolto': 'success',
            'ignorato': 'secondary'
        }
        return classi_map.get(self.status, 'secondary')

class AIAnalysisLog(db.Model):
    """
    Modello per tracciare lo storico delle analisi AI sui documenti.
    
    Attributi:
        id (int): ID primario.
        document_id (int): ID del documento analizzato.
        action_type (str): Tipo di azione AI (es: "tag_suggerito", "task_generato", "alert_ai").
        payload (str): Dettagli dell'intervento AI in formato JSON.
        timestamp (datetime): Data/ora dell'analisi.
        accepted_by_user (bool): Se l'intervento è stato accettato dall'utente.
        user_id (int): ID dell'utente che ha accettato/rifiutato (se applicabile).
        document (Document): Relazione con il documento.
        user (User): Relazione con l'utente.
    """
    __tablename__ = "ai_analysis_logs"
    
    id = db.Column(db.Integer, primary_key=True)
    document_id = db.Column(db.Integer, db.ForeignKey("documents.id"), nullable=False)
    action_type = db.Column(db.String(100), nullable=False)  # es: "tag_suggerito", "task_generato", "alert_ai", "classificazione_ai", "ricerca_semantica"
    payload = db.Column(db.Text, nullable=True)  # dettagli dell'intervento in JSON
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    accepted_by_user = db.Column(db.Boolean, default=False)  # se l'intervento è stato accettato
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)  # chi ha accettato/rifiutato
    
    # Relazioni
    document = db.relationship("Document", backref="ai_analysis_logs")
    user = db.relationship("User", backref="ai_analysis_logs")
    
    def __repr__(self):
        """Rappresentazione stringa del log AI."""
        return f'<AIAnalysisLog {self.action_type} - {self.document_id} - {self.timestamp}>'
    
    @property
    def action_display(self):
        """Restituisce il nome visualizzabile dell'azione."""
        action_map = {
            "tag_suggerito": "Tag AI Suggerito",
            "task_generato": "Task Generato",
            "alert_ai": "Alert AI",
            "classificazione_ai": "Classificazione AI",
            "ricerca_semantica": "Ricerca Semantica",
            "firma_ai": "Firma AI",
            "approvazione_ai": "Approvazione AI",
            "insight_ai": "Insight AI"
        }
        return action_map.get(self.action_type, self.action_type)
    
    @property
    def payload_parsed(self):
        """Restituisce il payload parsato come dizionario."""
        import json
        try:
            return json.loads(self.payload) if self.payload else {}
        except (json.JSONDecodeError, TypeError):
            return {}
    
    @property
    def status_display(self):
        """Restituisce lo stato di accettazione."""
        if self.accepted_by_user:
            return "Accettato"
        elif self.user_id is not None:
            return "Rifiutato"
        else:
            return "In attesa"
    
    @property
    def status_badge_class(self):
        """Restituisce la classe CSS per il badge di stato."""
        if self.accepted_by_user:
            return "badge bg-success"
        elif self.user_id is not None:
            return "badge bg-danger"
        else:
            return "badge bg-warning"

class LogInvioDocumento(db.Model):
    """
    Modello per tracciare il logging degli invii di documenti.
    
    Attributi:
        id (int): ID primario.
        firma_id (int): ID della firma associata.
        documento_id (int): ID del documento inviato.
        email_destinatario (str): Email del destinatario.
        stato (str): Stato dell'invio ('success', 'errore').
        errore (str): Messaggio di errore (se applicabile).
        data_invio (datetime): Data/ora dell'invio.
        firma (FirmaDocumento): Relazione con la firma.
        documento (Document): Relazione con il documento.
    """
    __tablename__ = 'log_invio_documento'

    id = db.Column(db.Integer, primary_key=True)
    firma_id = db.Column(db.Integer, db.ForeignKey('firme_documenti.id'), nullable=False)
    documento_id = db.Column(db.Integer, db.ForeignKey('documents.id'), nullable=False)
    
    email_destinatario = db.Column(db.String(255), nullable=False)
    stato = db.Column(db.String(50), nullable=False)  # success, errore
    errore = db.Column(db.Text, nullable=True)
    
    data_invio = db.Column(db.DateTime, default=datetime.utcnow)

    # Relazioni
    firma = db.relationship("FirmaDocumento", backref="log_invii")
    documento = db.relationship("Document", backref="log_invii")

    def __repr__(self):
        """
        Rappresentazione stringa del log invio.

        Returns:
            str: Rappresentazione.
        """
        return f"<LogInvioDocumento {self.id} - {self.email_destinatario} - {self.stato}>"
    
    @property
    def stato_display(self):
        """
        Restituisce lo stato visualizzabile.

        Returns:
            str: Stato visualizzabile.
        """
        stati = {
            'success': '✅ Successo',
            'errore': '❌ Errore'
        }
        return stati.get(self.stato, self.stato)
    
    @property
    def badge_class_stato(self):
        """
        Restituisce la classe CSS per il badge dello stato.

        Returns:
            str: Classe CSS.
        """
        classi = {
            'success': 'bg-success',
            'errore': 'bg-danger'
        }
        return classi.get(self.stato, 'bg-secondary')
    
    @property
    def data_invio_formatted(self):
        """
        Restituisce la data di invio formattata.

        Returns:
            str: Data formattata.
        """
        return self.data_invio.strftime('%d/%m/%Y %H:%M:%S')

class AuditVerificaLog(db.Model):
    """
    Modello per tracciare le verifiche audit degli eventi formativi.
    
    Attributi:
        id (int): ID primario.
        evento_id (int): ID dell'evento verificato.
        data (datetime): Data/ora della verifica.
        esito (str): Esito della verifica ('completo', 'incompleto').
        anomalie (int): Numero di anomalie rilevate.
        evento (EventoFormazione): Relazione con l'evento.
    """
    __tablename__ = 'audit_verifica_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    evento_id = db.Column(db.Integer, db.ForeignKey('eventi_formazione.id'), nullable=False)
    data = db.Column(db.DateTime, default=datetime.utcnow)
    esito = db.Column(db.String(50))  # completo / incompleto
    anomalie = db.Column(db.Integer, default=0)
    dettagli_problemi = db.Column(db.Text, nullable=True)  # JSON con dettagli problemi
    
    # Relazioni
    evento = db.relationship("EventoFormazione", backref="audit_logs")
    
    def __repr__(self):
        return f"<AuditVerificaLog {self.evento_id} - {self.esito} - {self.anomalie} anomalie>"
    
    @property
    def data_formatted(self):
        """Data formattata per visualizzazione."""
        return self.data.strftime('%d/%m/%Y %H:%M:%S')
    
    @property
    def esito_display(self):
        """Esito formattato per visualizzazione."""
        stati = {
            'completo': '🟢 Completo',
            'incompleto': '🟡 Incompleto'
        }
        return stati.get(self.esito, self.esito)
    
    @property
    def badge_class(self):
        """Classe CSS per badge."""
        classi = {
            'completo': 'bg-success',
            'incompleto': 'bg-warning'
        }
        return classi.get(self.esito, 'bg-secondary')

# === MODELLO GUEST ACCESS ===
class GuestAccess(db.Model):
    """
    Modello per gestire l'accesso guest ai documenti.
    
    Attributi:
        id (int): ID primario.
        guest_id (int): ID dell'utente guest.
        document_id (int): ID del documento.
        can_download (bool): Se il guest può scaricare il documento.
        expires_at (datetime): Data di scadenza dell'accesso.
        created_at (datetime): Data creazione dell'accesso.
        guest (User): Relazione con l'utente guest.
        document (Document): Relazione con il documento.
    """
    __tablename__ = 'guest_access'
    
    id = db.Column(db.Integer, primary_key=True)
    guest_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    document_id = db.Column(db.Integer, db.ForeignKey('documents.id'), nullable=False)
    can_download = db.Column(db.Boolean, default=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Relazioni
    guest = db.relationship('User', foreign_keys=[guest_id], backref='guest_access')
    document = db.relationship('Document', backref='guest_access')
    created_by = db.relationship('User', foreign_keys=[created_by_user_id], backref='created_guest_access')
    
    def __repr__(self):
        """
        Rappresentazione stringa dell'accesso guest.

        Returns:
            str: Rappresentazione.
        """
        return f'<GuestAccess {self.guest_id}:{self.document_id}:{self.can_download}>'
    
    @property
    def is_expired(self):
        """
        Verifica se l'accesso è scaduto.

        Returns:
            bool: True se scaduto.
        """
        return datetime.utcnow() > self.expires_at
    
    @property
    def days_until_expiry(self):
        """
        Calcola i giorni rimanenti fino alla scadenza.

        Returns:
            int: Giorni rimanenti (negativo se scaduto).
        """
        delta = self.expires_at - datetime.utcnow()
        return delta.days
    
    @property
    def status_display(self):
        """
        Restituisce lo stato visualizzabile dell'accesso.

        Returns:
            str: Stato visualizzabile.
        """
        if self.is_expired:
            return '❌ Scaduto'
        elif self.can_download:
            return '✅ Accesso completo'
        else:
            return '👁️ Solo visualizzazione'
    
    @property
    def badge_class(self):
        """
        Restituisce la classe CSS per il badge dello stato.

        Returns:
            str: Classe CSS badge.
        """
        if self.is_expired:
            return 'danger'
        elif self.can_download:
            return 'success'
        else:
            return 'info'

class DocumentAuditLog(db.Model):
    """
    Log di audit per tracciare tutte le attività sui documenti.
    
    Attributes:
        id (int): ID primario del log
        document_id (int): ID del documento associato
        user_id (int): ID dell'utente che ha eseguito l'azione (nullable per azioni di sistema)
        evento (str): Descrizione dell'evento
        timestamp (datetime): Data e ora dell'evento
        note_ai (str): Note aggiuntive generate dall'AI
    """
    __tablename__ = 'document_audit_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    document_id = db.Column(db.Integer, db.ForeignKey('documents.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    evento = db.Column(db.String(255), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    note_ai = db.Column(db.Text, nullable=True)
    
    # Relazioni
    document = db.relationship('Document', backref='document_audit_logs')
    user = db.relationship('User', backref='audit_actions')
    
    def __repr__(self):
        return f'<DocumentAuditLog {self.evento} - {self.timestamp}>'

# === MODELLO VISITA MEDICA ===
class VisitaMedica(db.Model):
    """
    Modello per gestire le visite mediche dei dipendenti.
    
    Attributi:
        id (int): ID primario.
        user_id (int): ID dell'utente.
        ruolo (str): Ruolo del dipendente.
        tipo_visita (str): Tipo di visita medica.
        data_visita (date): Data della visita.
        scadenza (date): Data di scadenza.
        esito (str): Esito della visita.
        certificato_filename (str): Nome file certificato.
        certificato_path (str): Percorso file certificato.
        note (str): Note aggiuntive.
        created_at (datetime): Data creazione.
        user (User): Relazione con l'utente.
    """
    __tablename__ = "visite_mediche"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    ruolo = db.Column(db.String(100), nullable=False)
    tipo_visita = db.Column(db.String(150), nullable=False)
    data_visita = db.Column(db.Date, nullable=False)
    scadenza = db.Column(db.Date, nullable=False)
    esito = db.Column(db.String(50), nullable=False)  # Es: "Idoneo", "Non idoneo"
    certificato_filename = db.Column(db.String(255))
    certificato_path = db.Column(db.String(255))
    note = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relazione con l'utente
    user = db.relationship("User", backref="visite_mediche")
    
    def __repr__(self):
        return f'<VisitaMedica {self.tipo_visita} - {self.user.username if self.user else "N/A"} - {self.data_visita}>'
    
    @property
    def is_expired(self):
        """Verifica se la visita è scaduta."""
        from datetime import date
        return date.today() > self.scadenza
    
    @property
    def days_until_expiry(self):
        """Giorni rimanenti fino alla scadenza."""
        from datetime import date
        delta = self.scadenza - date.today()
        return delta.days
    
    @property
    def status_display(self):
        """Stato visuale della visita."""
        if self.is_expired:
            return "Scaduta"
        elif self.days_until_expiry <= 30:
            return "In scadenza"
        else:
            return "Valida"
    
    @property
    def badge_class(self):
        """Classe CSS per il badge di stato."""
        if self.is_expired:
            return "bg-danger"
        elif self.days_until_expiry <= 30:
            return "bg-warning"
        else:
            return "bg-success"


# === MODELLO LOG VISITA MEDICA (AUDIT COMPLIANCE) ===
class LogVisitaMedica(db.Model):
    """
    Modello per tracciare tutte le modifiche alle visite mediche (audit compliance).
    
    Attributi:
        id (int): ID primario.
        visita_id (int): ID della visita modificata.
        user_id (int): ID dell'utente che ha eseguito l'azione.
        azione (str): Tipo di azione ('Creazione', 'Modifica', 'Eliminazione').
        timestamp (datetime): Data/ora dell'azione.
        dettagli (dict): Dettagli dell'azione in formato JSON.
        visita (VisitaMedica): Relazione con la visita.
        user (User): Relazione con l'utente.
    """
    __tablename__ = "log_visite_mediche"
    
    id = db.Column(db.Integer, primary_key=True)
    visita_id = db.Column(db.Integer, db.ForeignKey('visite_mediche.id'), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    azione = db.Column(db.String(50), nullable=False)  # 'Creazione', 'Modifica', 'Eliminazione'
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    dettagli = db.Column(db.Text, nullable=True)  # JSON con dettagli dell'azione
    
    # Relazioni
    visita = db.relationship('VisitaMedica', backref='log_azioni')
    user = db.relationship('User', backref='log_visite_mediche')
    
    def __repr__(self):
        return f'<LogVisitaMedica {self.azione} - {self.timestamp}>'
    
    @property
    def azione_display(self):
        """Display dell'azione in italiano."""
        azioni = {
            'Creazione': 'Creazione visita',
            'Modifica': 'Modifica visita',
            'Eliminazione': 'Eliminazione visita'
        }
        return azioni.get(self.azione, self.azione)
    
    @property
    def timestamp_formatted(self):
        """Timestamp formattato."""
        return self.timestamp.strftime('%d/%m/%Y %H:%M')

# === MODELLO CHECKLIST COMPLIANCE AUDIT-READY ===
class ChecklistCompliance(db.Model):
    """
    Modello per gestire checklist di compliance documentale secondo standard ISO, GDPR, HACCP, BRC, IFS, NIS2, ecc.
    
    Attributi:
        id (int): ID primario.
        documento_id (int): ID del documento associato.
        tipo_standard (str): Categoria standard di riferimento (ISO 9001, GDPR, HACCP, BRC, IFS, NIS2).
        voce (str): Punto della checklist da verificare.
        is_completa (bool): True se completato da un utente abilitato.
        completata_da (str): Nome dell'utente che ha validato la voce.
        completata_il (datetime): Timestamp validazione.
        note (str): Annotazioni libere (per audit).
        document (Document): Relazione con il documento.
    """
    __tablename__ = 'checklist_compliance'
    
    id = db.Column(db.Integer, primary_key=True)
    documento_id = db.Column(db.Integer, db.ForeignKey('documents.id'), nullable=False)
    tipo_standard = db.Column(db.String(50), nullable=False)  # es: ISO 9001, GDPR, HACCP, BRC, IFS, NIS2
    voce = db.Column(db.String(255), nullable=False)          # es: "Controllo revisioni"
    is_completa = db.Column(db.Boolean, default=False)
    completata_da = db.Column(db.String(150), nullable=True)
    completata_il = db.Column(db.DateTime, nullable=True)
    note = db.Column(db.Text, nullable=True)
    
    # Relazione con il documento
    document = db.relationship('Document', backref='checklist_compliance')
    
    def __repr__(self):
        """Rappresentazione stringa della checklist."""
        return f'<ChecklistCompliance {self.tipo_standard} - {self.voce} - {self.is_completa}>'
    
    @property
    def stato_display(self):
        """Stato visuale della checklist."""
        return "Completata" if self.is_completa else "In attesa"
    
    @property
    def badge_class(self):
        """Classe CSS per il badge di stato."""
        return "bg-success" if self.is_completa else "bg-warning"
    
    @property
    def completata_il_formatted(self):
        """Data completamento formattata."""
        if self.completata_il:
            return self.completata_il.strftime('%d/%m/%Y %H:%M')
        return "Non completata"
    
    @property
    def tipo_standard_display(self):
        """Display del tipo standard in italiano."""
        standard_map = {
            'ISO 9001': 'ISO 9001 - Gestione Qualità',
            'ISO 14001': 'ISO 14001 - Gestione Ambientale',
            'ISO 45001': 'ISO 45001 - Sicurezza e Salute',
            'GDPR': 'GDPR - Protezione Dati',
            'HACCP': 'HACCP - Sicurezza Alimentare',
            'BRC': 'BRC - Standard Sicurezza Alimentare',
            'IFS': 'IFS - Standard Sicurezza Alimentare',
            'NIS2': 'NIS2 - Sicurezza Informatica',
            'ISO 27001': 'ISO 27001 - Sicurezza Informatica',
            'SOX': 'SOX - Controlli Finanziari',
            'FDA': 'FDA - Sicurezza Farmaceutica',
            'GxP': 'GxP - Buone Pratiche Farmaceutiche'
        }
        return standard_map.get(self.tipo_standard, self.tipo_standard)
    
    @property
    def can_be_completed_by(self, user):
        """Verifica se l'utente può completare questa checklist."""
        if not user.is_authenticated:
            return False
        
        # Solo Admin, HR, Auditor, Responsabili Qualità possono completare
        allowed_roles = ['admin', 'ceo', 'hr', 'auditor', 'quality_manager']
        return user.role in allowed_roles
    
    def completa_checklist(self, user, note=None):
        """Completa la checklist con i dati dell'utente."""
        if not self.can_be_completed_by(user):
            raise ValueError("Utente non autorizzato a completare questa checklist")
        
        self.is_completa = True
        self.completata_da = f"{user.first_name} {user.last_name}" if user.first_name and user.last_name else user.username
        self.completata_il = datetime.utcnow()
        if note:
            self.note = note
        
        return True
    
    def reset_checklist(self, user):
        """Resetta la checklist (solo per admin/auditor)."""
        if user.role not in ['admin', 'ceo', 'auditor']:
            raise ValueError("Solo admin e auditor possono resettare le checklist")
        
        self.is_completa = False
        self.completata_da = None
        self.completata_il = None
        self.note = None
        
        return True

# === MODELLO FIRMA MANUALE ===
class FirmaManuale(db.Model):
    __tablename__ = 'firme_manuali'
    
    id = db.Column(db.Integer, primary_key=True)
    documento_id = db.Column(db.Integer, db.ForeignKey('documents.id'), nullable=False)
    firmato_da = db.Column(db.String(150), nullable=False)
    ruolo = db.Column(db.String(100), nullable=True)
    data_firma = db.Column(db.Date, nullable=False)
    file_scan = db.Column(db.String(255), nullable=True)  # path file
    note = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Relazioni
    documento = db.relationship('Document', backref='firme_manuali')
    created_by_user = db.relationship('User', backref='firme_creati')
    
    @property
    def file_scan_url(self):
        """Restituisce l'URL del file scan se presente."""
        if self.file_scan:
            return url_for('static', filename=f'uploads/firme_manuali/{self.file_scan}')
        return None
    
    @property
    def data_firma_display(self):
        """Formatta la data firma per visualizzazione."""
        return self.data_firma.strftime('%d/%m/%Y') if self.data_firma else ''
    
    @property
    def is_recente(self):
        """Verifica se la firma è recente (ultimi 30 giorni)."""
        if not self.data_firma:
            return False
        return (datetime.now().date() - self.data_firma).days <= 30
    
    def __repr__(self):
        return f'<FirmaManuale {self.id}: {self.firmato_da} su {self.documento_id}>'

# === MODELLO REMINDER AUTOMATICI ===
class Reminder(db.Model):
    """
    Modello per gestire i reminder automatici per documenti a scadenza.
    
    Attributi:
        id (int): ID primario.
        tipo (str): Tipo di reminder ('documento', 'checklist', 'visita_medica', 'revisione').
        entita_id (int): ID dell'entità (documento, checklist, visita, ecc.).
        entita_tipo (str): Tipo di entità ('Document', 'ChecklistCompliance', 'VisitaMedica').
        destinatario_email (str): Email del destinatario.
        destinatario_ruolo (str): Ruolo del destinatario ('hr', 'rspp', 'auditor', 'ceo').
        scadenza (datetime): Data di scadenza.
        giorni_anticipo (int): Giorni di anticipo per il reminder.
        stato (str): Stato del reminder ('attivo', 'inviato', 'scaduto', 'disabilitato').
        ultimo_invio (datetime): Data ultimo invio.
        prossimo_invio (datetime): Data prossimo invio.
        messaggio (str): Messaggio personalizzato.
        canale (str): Canale di invio ('email', 'interno', 'entrambi').
        created_at (datetime): Data creazione.
        created_by (int): ID utente che ha creato il reminder.
    """
    __tablename__ = 'reminders'
    
    id = db.Column(db.Integer, primary_key=True)
    tipo = db.Column(db.String(50), nullable=False)  # documento, checklist, visita_medica, revisione
    entita_id = db.Column(db.Integer, nullable=False)
    entita_tipo = db.Column(db.String(50), nullable=False)  # Document, ChecklistCompliance, VisitaMedica
    destinatario_email = db.Column(db.String(150), nullable=False)
    destinatario_ruolo = db.Column(db.String(50), nullable=False)  # hr, rspp, auditor, ceo
    scadenza = db.Column(db.DateTime, nullable=False)
    giorni_anticipo = db.Column(db.Integer, default=30)  # Giorni prima della scadenza
    stato = db.Column(db.String(20), default='attivo')  # attivo, inviato, scaduto, disabilitato
    ultimo_invio = db.Column(db.DateTime, nullable=True)
    prossimo_invio = db.Column(db.DateTime, nullable=True)
    messaggio = db.Column(db.Text, nullable=True)
    canale = db.Column(db.String(20), default='email')  # email, interno, entrambi
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Relazioni
    created_by_user = db.relationship('User', backref='reminders_creati')
    
    def __repr__(self):
        """Rappresentazione stringa del reminder."""
        return f'<Reminder {self.tipo} - {self.destinatario_email} - {self.scadenza}>'
    
    @property
    def giorni_alla_scadenza(self):
        """Giorni rimanenti alla scadenza."""
        from datetime import datetime
        delta = self.scadenza - datetime.utcnow()
        return delta.days
    
    @property
    def is_scaduto(self):
        """Verifica se il reminder è scaduto."""
        from datetime import datetime
        return datetime.utcnow() > self.scadenza
    
    @property
    def is_urgente(self):
        """Verifica se il reminder è urgente (≤ 7 giorni)."""
        return self.giorni_alla_scadenza <= 7 and not self.is_scaduto
    
    @property
    def is_critico(self):
        """Verifica se il reminder è critico (≤ 3 giorni)."""
        return self.giorni_alla_scadenza <= 3 and not self.is_scaduto
    
    @property
    def stato_display(self):
        """Stato visuale del reminder."""
        if self.is_scaduto:
            return "Scaduto"
        elif self.is_critico:
            return "Critico"
        elif self.is_urgente:
            return "Urgente"
        else:
            return "Attivo"
    
    @property
    def badge_class(self):
        """Classe CSS per il badge di stato."""
        if self.is_scaduto:
            return "bg-danger"
        elif self.is_critico:
            return "bg-danger"
        elif self.is_urgente:
            return "bg-warning"
        else:
            return "bg-success"
    
    @property
    def tipo_display(self):
        """Display del tipo in italiano."""
        tipi_map = {
            'documento': 'Documento',
            'checklist': 'Checklist Compliance',
            'visita_medica': 'Visita Medica',
            'revisione': 'Revisione Periodica'
        }
        return tipi_map.get(self.tipo, self.tipo)
    
    @property
    def canale_display(self):
        """Display del canale in italiano."""
        canali_map = {
            'email': 'Email',
            'interno': 'Notifica Interna',
            'entrambi': 'Email + Interna'
        }
        return canali_map.get(self.canale, self.canale)
    
    def calcola_prossimo_invio(self):
        """Calcola la data del prossimo invio basata sui giorni di anticipo."""
        from datetime import datetime, timedelta
        self.prossimo_invio = self.scadenza - timedelta(days=self.giorni_anticipo)
        return self.prossimo_invio
    
    def invia_reminder(self):
        """Invia il reminder e aggiorna lo stato."""
        try:
            # Logica di invio (implementata nel service)
            self.ultimo_invio = datetime.utcnow()
            self.stato = 'inviato'
            return True
        except Exception as e:
            current_app.logger.error(f"Errore invio reminder {self.id}: {str(e)}")
            return False
    
    def reset_reminder(self):
        """Resetta il reminder per il prossimo ciclo."""
        self.stato = 'attivo'
        self.ultimo_invio = None
        self.calcola_prossimo_invio()
    
    def disabilita_reminder(self):
        """Disabilita il reminder."""
        self.stato = 'disabilitato'
        self.ultimo_invio = None
        self.prossimo_invio = None

class ReminderLog(db.Model):
    """
    Modello per tracciare il log degli invii reminder.
    
    Attributi:
        id (int): ID primario.
        reminder_id (int): ID del reminder.
        inviato_a (str): Email destinatario.
        canale (str): Canale di invio.
        messaggio (str): Messaggio inviato.
        esito (str): Esito dell'invio ('success', 'error').
        errore (str): Messaggio di errore (se applicabile).
        timestamp (datetime): Data/ora invio.
        reminder (Reminder): Relazione con il reminder.
    """
    __tablename__ = 'reminder_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    reminder_id = db.Column(db.Integer, db.ForeignKey('reminders.id'), nullable=False)
    inviato_a = db.Column(db.String(150), nullable=False)
    canale = db.Column(db.String(20), nullable=False)
    messaggio = db.Column(db.Text, nullable=True)
    esito = db.Column(db.String(20), nullable=False)  # success, error
    errore = db.Column(db.Text, nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relazioni
    reminder = db.relationship('Reminder', backref='log_invii')
    
    def __repr__(self):
        """Rappresentazione stringa del log."""
        return f'<ReminderLog {self.reminder_id} - {self.esito} - {self.timestamp}>'
    
    @property
    def esito_display(self):
        """Display dell'esito in italiano."""
        return "Successo" if self.esito == 'success' else "Errore"
    
    @property
    def badge_class(self):
        """Classe CSS per il badge di esito."""
        return "bg-success" if self.esito == 'success' else "bg-danger"
    
    @property
    def timestamp_formatted(self):
        """Timestamp formattato."""
        return self.timestamp.strftime('%d/%m/%Y %H:%M')

# === MODELLO PROVA EVACUAZIONE ===
class ProvaEvacuazione(db.Model):
    """
    Modello per gestire le prove di evacuazione aziendali.
    
    Attributi:
        id (int): ID primario.
        data (date): Data in cui si è svolta la prova.
        luogo (str): Sede, edificio o reparto coinvolto.
        responsabile (str): Chi ha coordinato la prova.
        note (str): Osservazioni, anomalie, valutazioni.
        verbale_filename (str): File PDF con descrizione ufficiale.
        planimetria_filename (str): Planimetria zona evacuata (PDF/JPG).
        foto_filename (str): Foto evento o aree evacuate (facoltativo).
        created_at (datetime): Data creazione record.
        created_by (int): ID utente che ha creato il record.
        user (User): Relazione con l'utente creatore.
    """
    __tablename__ = 'prove_evacuazione'
    
    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(db.Date, nullable=False)
    luogo = db.Column(db.String(255), nullable=False)
    responsabile = db.Column(db.String(150), nullable=False)
    note = db.Column(db.Text, nullable=True)
    verbale_filename = db.Column(db.String(255), nullable=True)
    planimetria_filename = db.Column(db.String(255), nullable=True)
    foto_filename = db.Column(db.String(255), nullable=True)
    punti_mappa = db.Column(db.Text, nullable=True)  # JSON for interactive points
    link_fleetfix = db.Column(db.String(500), nullable=True)  # External link
    firma_responsabile = db.Column(db.LargeBinary, nullable=True) # Firma digitale responsabile
    firma_ai_simulata = db.Column(db.Boolean, default=False) # Firma AI simulata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    user = db.relationship('User', backref='prove_evacuazione_creati')

    @property
    def punti_mappa_dict(self):
        """Converte punti_mappa JSON in dizionario Python."""
        if self.punti_mappa:
            try:
                return json.loads(self.punti_mappa)
            except:
                return {}
        return {}

    @punti_mappa_dict.setter
    def punti_mappa_dict(self, value):
        """Converte dizionario Python in JSON per salvare."""
        if value:
            self.punti_mappa = json.dumps(value)
        else:
            self.punti_mappa = None

    @property
    def has_firma_responsabile(self):
        """Verifica se ha una firma del responsabile."""
        return bool(self.firma_responsabile)

    @property
    def has_firma_ai(self):
        """Verifica se ha una firma AI simulata."""
        return self.firma_ai_simulata

class VersionePlanimetriaEvacuazione(db.Model):
    __tablename__ = 'versioni_planimetrie_evacuazione'
    id = db.Column(db.Integer, primary_key=True)
    prova_id = db.Column(db.Integer, db.ForeignKey('prove_evacuazione.id'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    uploaded_by = db.Column(db.String(100))
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    note = db.Column(db.Text)
    prova = db.relationship('ProvaEvacuazione', backref='versioni_planimetrie')

class AuditTrailEvacuazione(db.Model):
    __tablename__ = 'audit_trail_evacuazione'
    id = db.Column(db.Integer, primary_key=True)
    prova_id = db.Column(db.Integer, db.ForeignKey('prove_evacuazione.id'), nullable=False)
    campo_modificato = db.Column(db.String(100))
    valore_precedente = db.Column(db.Text)
    valore_nuovo = db.Column(db.Text)
    modificato_da = db.Column(db.String(150))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    prova = db.relationship('ProvaEvacuazione', backref='audit_trails')

class PianoVisitePerMansione(db.Model):
    __tablename__ = 'piano_visite_per_mansione'
    id = db.Column(db.Integer, primary_key=True)
    mansione = db.Column(db.String(150), nullable=False)  # es. "Autista"
    tipo_visita = db.Column(db.String(150), nullable=False)  # es. "Test vista", "ECG"
    frequenza_anni = db.Column(db.Integer, default=1)  # Ogni quanti anni
    obbligatoria = db.Column(db.Boolean, default=True)
    note = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    created_by_user = db.relationship('User', backref='piani_visite_creati')

    @property
    def display_name(self):
        """Nome visualizzabile per il piano visite."""
        return f"{self.mansione} - {self.tipo_visita}"

    @property
    def frequenza_display(self):
        """Frequenza in formato leggibile."""
        if self.frequenza_anni == 1:
            return "Annuale"
        elif self.frequenza_anni == 2:
            return "Biennale"
        elif self.frequenza_anni == 3:
            return "Triennale"
        else:
            return f"Ogni {self.frequenza_anni} anni"

class VisitaMedicaEffettuata(db.Model):
    __tablename__ = 'visite_mediche_effettuate'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    tipo_visita = db.Column(db.String(150), nullable=False)  # es. "ECG"
    data_visita = db.Column(db.Date, nullable=False)
    esito = db.Column(db.String(255))  # "Idoneo", "Non idoneo", "Idoneo con limitazioni"
    scadenza = db.Column(db.Date)
    mansione_riferimento = db.Column(db.String(150))  # Mansione per cui è stata fatta
    
    certificato_finale = db.Column(db.Boolean, default=False)
    allegato_certificato = db.Column(db.LargeBinary)
    filename_certificato = db.Column(db.String(255))
    
    note = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    utente = db.relationship('User', backref='visite_mediche_effettuate')
    created_by_user = db.relationship('User', foreign_keys=[created_by], backref='visite_mediche_registrate')

    @property
    def data_visita_display(self):
        """Data visita formattata."""
        return self.data_visita.strftime('%d/%m/%Y') if self.data_visita else ''

    @property
    def scadenza_display(self):
        """Data scadenza formattata."""
        return self.scadenza.strftime('%d/%m/%Y') if self.scadenza else ''

    @property
    def is_scaduta(self):
        """Verifica se la visita è scaduta."""
        if not self.scadenza:
            return False
        return self.scadenza < datetime.now().date()

    @property
    def is_in_scadenza(self):
        """Verifica se la visita è in scadenza (30 giorni)."""
        if not self.scadenza:
            return False
        giorni_alla_scadenza = (self.scadenza - datetime.now().date()).days
        return 0 <= giorni_alla_scadenza <= 30

    @property
    def has_certificato(self):
        """Verifica se ha un certificato allegato."""
        return bool(self.allegato_certificato)

    @property
    def esito_badge_class(self):
        """Classe CSS per il badge dell'esito."""
        if not self.esito:
            return "bg-secondary"
        elif "idoneo" in self.esito.lower():
            return "bg-success"
        elif "non idoneo" in self.esito.lower():
            return "bg-danger"
        elif "limitazioni" in self.esito.lower():
            return "bg-warning"
        else:
            return "bg-info"

class DocumentoRelazioneMedico(db.Model):
    __tablename__ = 'documenti_relazione_medico'
    id = db.Column(db.Integer, primary_key=True)
    anno = db.Column(db.Integer, nullable=False)
    data_caricamento = db.Column(db.DateTime, default=datetime.utcnow)
    file_data = db.Column(db.LargeBinary, nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    caricato_da = db.Column(db.String(150), nullable=False)
    note = db.Column(db.Text)
    
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_by_user = db.relationship('User', backref='relazioni_mediche_caricate')

    @property
    def data_caricamento_display(self):
        """Data caricamento formattata."""
        return self.data_caricamento.strftime('%d/%m/%Y %H:%M') if self.data_caricamento else ''

    @property
    def file_size_display(self):
        """Dimensione file formattata."""
        if self.file_data:
            size = len(self.file_data)
            if size < 1024:
                return f"{size} B"
            elif size < 1024 * 1024:
                return f"{size // 1024} KB"
            else:
                return f"{size // (1024 * 1024)} MB"
        return "0 B"

class LogReminderVisita(db.Model):
    """Log dei reminder inviati per le visite mediche in scadenza."""
    __tablename__ = 'log_reminder_visita'
    
    id = db.Column(db.Integer, primary_key=True)
    visita_id = db.Column(db.Integer, db.ForeignKey('visite_mediche_effettuate.id'), nullable=False)
    data_invio = db.Column(db.Date, nullable=False)
    tipo = db.Column(db.String(50), nullable=False)  # "in_scadenza" o "scaduta"
    destinatari = db.Column(db.Text)  # Lista email separate da virgola
    messaggio_inviato = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    visita = db.relationship('VisitaMedicaEffettuata', backref='reminder_logs')

class SignatureToken(db.Model):
    """
    Modello per token di firma digitale con 2FA.
    
    Attributi:
        id (int): ID primario
        token (str): Token univoco di 6 cifre
        user_id (int): ID utente che richiede la firma
        version_id (int): ID versione documento da firmare
        created_at (datetime): Data creazione token
        expires_at (datetime): Data scadenza token (15 minuti)
        used (bool): Se il token è stato utilizzato
        user (User): Relazione con l'utente
        version (DocumentVersion): Relazione con la versione
    """
    __tablename__ = "signature_tokens"
    
    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String(6), unique=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    version_id = db.Column(db.Integer, db.ForeignKey("document_versions.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
    used = db.Column(db.Boolean, default=False)
    
    # Relazioni
    user = db.relationship("User", backref="signature_tokens")
    version = db.relationship("DocumentVersion", backref="signature_tokens")
    
    def __repr__(self):
        """Rappresentazione stringa del token."""
        return f'<SignatureToken {self.token} - {self.user.username if self.user else "N/A"} - {"Usato" if self.used else "Valido"}>'
    
    @property
    def is_expired(self):
        """Verifica se il token è scaduto."""
        return datetime.utcnow() > self.expires_at
    
    @property
    def is_valid(self):
        """Verifica se il token è valido (non scaduto e non usato)."""
        return not self.used and not self.is_expired
    
    @property
    def minutes_remaining(self):
        """Minuti rimanenti prima della scadenza."""
        if self.is_expired:
            return 0
        delta = self.expires_at - datetime.utcnow()
        return int(delta.total_seconds() / 60)

class DocumentSignature(db.Model):
    """
    Modello per le firme digitali dei documenti.
    
    Attributi:
        id (int): ID primario
        version_id (int): ID versione documento firmata
        signed_by (str): Username di chi ha firmato
        role (str): Ruolo del firmatario
        hash_sha256 (str): Hash SHA256 del documento
        signature_note (str): Note sulla firma
        token_used (str): Token utilizzato per la firma
        created_at (datetime): Data/ora firma
        version (DocumentVersion): Relazione con la versione
    """
    __tablename__ = "document_signatures"
    
    id = db.Column(db.Integer, primary_key=True)
    version_id = db.Column(db.Integer, db.ForeignKey("document_versions.id"), nullable=False)
    signed_by = db.Column(db.String(150), nullable=False)
    role = db.Column(db.String(50), nullable=False)  # CEO, RSPP, DIRIGENTE, ecc.
    hash_sha256 = db.Column(db.String(64), nullable=False)  # Hash SHA256 del documento
    signature_note = db.Column(db.Text, nullable=True)
    token_used = db.Column(db.String(6), nullable=True)  # Token utilizzato per 2FA
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relazioni
    version = db.relationship("DocumentVersion", backref="signatures")
    
    def __repr__(self):
        """Rappresentazione stringa della firma."""
        return f'<DocumentSignature {self.signed_by} - {self.role} - {self.created_at.strftime("%d/%m/%Y %H:%M")}>'
    
    @property
    def created_at_formatted(self):
        """Data/ora firma formattata."""
        return self.created_at.strftime("%d/%m/%Y %H:%M")
    
    @property
    def is_recent(self):
        """Verifica se la firma è recente (ultimi 7 giorni)."""
        return (datetime.utcnow() - self.created_at).days <= 7
    
    @property
    def tipo_display(self):
        """Restituisce il tipo di notifica formattato."""
        return {
            'in_scadenza': 'In Scadenza',
            'scaduta': 'Scaduta'
        }.get(self.tipo, self.tipo)
    
    @property
    def destinatari_list(self):
        """Restituisce la lista dei destinatari."""
        return self.destinatari.split(',') if self.destinatari else []

class Feedback(db.Model):
    """
    Modello per feedback CEO (talenti, criticità, idee).
    """
    __tablename__ = 'feedback'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Informazioni base
    dipendente_id = db.Column(db.String(100), nullable=False)
    dipendente_nome = db.Column(db.String(200))
    dipartimento = db.Column(db.String(100))
    
    # Contenuto feedback
    tipo = db.Column(db.String(50), nullable=False)  # 'talento', 'criticità', 'idea'
    testo = db.Column(db.Text, nullable=False)
    note = db.Column(db.Text)
    
    # Autore e stato
    autore_id = db.Column(db.String(100), nullable=False)
    autore_nome = db.Column(db.String(200))
    autore_ruolo = db.Column(db.String(100))
    stato = db.Column(db.String(50), default='in_attesa')  # 'in_attesa', 'valutato', 'archiviato'
    
    # Timestamps
    data_creazione = db.Column(db.DateTime, default=datetime.utcnow)
    data_valutazione = db.Column(db.DateTime)
    data_commento_ceo = db.Column(db.DateTime)
    
    # Valutazione CEO
    valutato_da = db.Column(db.Integer, db.ForeignKey('users.id'))
    commento_ceo = db.Column(db.Text)
    commentato_da_ceo = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    # Relazioni
    valutatore = db.relationship('User', foreign_keys=[valutato_da], backref='feedback_valutati')
    commentatore = db.relationship('User', foreign_keys=[commentato_da_ceo], backref='feedback_commentati')
    
    def __repr__(self):
        return f'<Feedback {self.id}: {self.tipo} - {self.dipendente_id}>'

# === MODELLO FLAG AI DOCUMENTO ===
class DocumentAIFlag(db.Model):
    """
    Modello per salvare i flag AI sui documenti (conforme/non conforme).
    
    Attributi:
        id (int): ID primario.
        document_id (int): ID documento verificato.
        flag_type (str): Tipo di flag ('conforme', 'non_conforme', 'sospetto').
        ai_analysis (str): Analisi AI dettagliata.
        missing_sections (str): Sezioni mancanti identificate.
        compliance_score (float): Punteggio compliance (0-100).
        created_at (datetime): Data verifica.
        document (Document): Relazione con il documento.
    """
    __tablename__ = 'document_ai_flags'
    
    id = db.Column(db.Integer, primary_key=True)
    document_id = db.Column(db.Integer, db.ForeignKey('documents.id'), nullable=False)
    flag_type = db.Column(db.String(50), nullable=False)  # conforme, non_conforme, sospetto
    ai_analysis = db.Column(db.Text, nullable=False)  # Analisi AI dettagliata
    missing_sections = db.Column(db.Text, nullable=True)  # Sezioni mancanti
    compliance_score = db.Column(db.Float, nullable=True)  # Punteggio 0-100
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relazione con il documento
    document = db.relationship('Document', backref='ai_flags')
    
    def __repr__(self):
        return f'<DocumentAIFlag {self.flag_type} - {self.compliance_score}%>'
    
    @property
    def is_conforme(self):
        """Verifica se il documento è conforme."""
        return self.flag_type == 'conforme'
    
    @property
    def is_non_conforme(self):
        """Verifica se il documento non è conforme."""
        return self.flag_type == 'non_conforme'
    
    @property
    def is_sospetto(self):
        """Verifica se il documento è sospetto."""
        return self.flag_type == 'sospetto'
    
    @property
    def badge_class(self):
        """Restituisce la classe CSS per il badge."""
        if self.is_conforme:
            return 'bg-success'
        elif self.is_non_conforme:
            return 'bg-danger'
        else:
            return 'bg-warning'
    
    @property
    def flag_display(self):
        """Restituisce il testo di visualizzazione del flag."""
        if self.is_conforme:
            return '✅ Conforme'
        elif self.is_non_conforme:
            return '❌ Non Conforme'
        else:
            return '⚠️ Sospetto'

# === MODELLO ALERT AI COMPORTAMENTI SOSPETTI ===
class AIAlert(db.Model):
    """
    Modello per gli alert AI su comportamenti sospetti.
    
    Attributi:
        id (int): ID primario.
        alert_type (str): Tipo di alert ('download_massivo', 'ip_sospetto', 'accesso_insolito').
        user_id (int): ID utente coinvolto.
        document_id (int): ID documento coinvolto (opzionale).
        severity (str): Severità ('bassa', 'media', 'alta', 'critica').
        description (str): Descrizione dell'alert.
        ip_address (str): IP del client.
        user_agent (str): User agent del browser.
        resolved (bool): Se l'alert è stato risolto.
        resolved_by (str): Chi ha risolto l'alert.
        resolved_at (datetime): Data risoluzione.
        created_at (datetime): Data creazione.
        user (User): Relazione con l'utente.
        document (Document): Relazione con il documento.
    """
    __tablename__ = 'ai_alerts'
    
    id = db.Column(db.Integer, primary_key=True)
    alert_type = db.Column(db.String(50), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    document_id = db.Column(db.Integer, db.ForeignKey('documents.id'), nullable=True)
    severity = db.Column(db.String(20), nullable=False)  # bassa, media, alta, critica
    description = db.Column(db.Text, nullable=False)
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.Text, nullable=True)
    resolved = db.Column(db.Boolean, default=False)
    resolved_by = db.Column(db.String(150), nullable=True)
    resolved_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relazioni
    user = db.relationship('User', backref='ai_alerts')
    document = db.relationship('Document', backref='ai_alerts')
    
    def __repr__(self):
        return f'<AIAlert {self.alert_type} - {self.severity}>'
    
    @property
    def is_resolved(self):
        """Verifica se l'alert è stato risolto."""
        return self.resolved
    
    @property
    def severity_badge_class(self):
        """Restituisce la classe CSS per il badge di severità."""
        severity_classes = {
            'bassa': 'bg-info',
            'media': 'bg-warning',
            'alta': 'bg-danger',
            'critica': 'bg-dark'
        }
        return severity_classes.get(self.severity, 'bg-secondary')
    
    @property
    def alert_type_display(self):
        """Restituisce il testo di visualizzazione del tipo di alert."""
        type_displays = {
            'download_massivo': '📥 Download Massivo',
            'ip_sospetto': '🌐 IP Sospetto',
            'accesso_insolito': '🚨 Accesso Insolito',
            'comportamento_anomalo': '⚠️ Comportamento Anomalo'
        }
        return type_displays.get(self.alert_type, self.alert_type)

# === MODELLO SUGGERIMENTI ARCHIVIAZIONE AI ===
class AIArchiveSuggestion(db.Model):
    """
    Modello per i suggerimenti AI di archiviazione.
    
    Attributi:
        id (int): ID primario.
        document_id (int): ID documento.
        suggested_folder (str): Cartella suggerita.
        confidence_score (float): Punteggio confidenza (0-100).
        reasoning (str): Motivazione del suggerimento.
        accepted (bool): Se il suggerimento è stato accettato.
        created_at (datetime): Data creazione.
        document (Document): Relazione con il documento.
    """
    __tablename__ = 'ai_archive_suggestions'
    
    id = db.Column(db.Integer, primary_key=True)
    document_id = db.Column(db.Integer, db.ForeignKey('documents.id'), nullable=False)
    suggested_folder = db.Column(db.String(255), nullable=False)
    confidence_score = db.Column(db.Float, nullable=False)
    reasoning = db.Column(db.Text, nullable=False)
    accepted = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # === Campi estesi per suggerimento completo ===
    path_suggerito = db.Column(db.String(500), nullable=True)  # Path completo es. /Mercury/Qualità/HACCP
    categoria_suggerita = db.Column(db.String(100), nullable=True)  # es. "Qualità", "Sicurezza", "Amministrazione"
    tag_ai = db.Column(db.Text, nullable=True)  # JSON array di tag es. ["haccp", "manuale", "formazione"]
    motivazione_ai = db.Column(db.Text, nullable=True)  # Spiegazione dettagliata AI
    azienda_suggerita = db.Column(db.String(100), nullable=True)  # Nome azienda suggerita
    reparto_suggerito = db.Column(db.String(100), nullable=True)  # Nome reparto suggerito
    tipo_documento_ai = db.Column(db.String(100), nullable=True)  # Tipo documento rilevato dall'AI
    
    # Relazione con il documento
    document = db.relationship('Document', backref='archive_suggestions')
    
    def __repr__(self):
        return f'<AIArchiveSuggestion {self.suggested_folder} - {self.confidence_score}%>'
    
    @property
    def confidence_badge_class(self):
        """Restituisce la classe CSS per il badge di confidenza."""
        if self.confidence_score >= 80:
            return 'bg-success'
        elif self.confidence_score >= 60:
            return 'bg-warning'
        else:
            return 'bg-info'
    
    @property
    def confidence_display(self):
        """Restituisce il testo di visualizzazione della confidenza."""
        if self.confidence_score >= 80:
            return 'Alta'
        elif self.confidence_score >= 60:
            return 'Media'
        else:
            return 'Bassa'
    
    @property
    def tag_list(self):
        """Restituisce la lista dei tag come array Python."""
        try:
            if self.tag_ai:
                return json.loads(self.tag_ai)
            return []
        except:
            return []
    
    @property
    def tag_display(self):
        """Restituisce i tag per visualizzazione."""
        tags = self.tag_list
        if tags:
            return ", ".join(tags)
        return "Nessun tag"
    
    @property
    def path_display(self):
        """Restituisce il path per visualizzazione."""
        if self.path_suggerito:
            return self.path_suggerito
        elif self.azienda_suggerita and self.reparto_suggerito:
            return f"/{self.azienda_suggerita}/{self.reparto_suggerito}"
        else:
            return self.suggested_folder

# === MODELLO RISPOSTE AUTOMATICHE AI ===
class AIReply(db.Model):
    """
    Modello per le risposte automatiche generate dall'AI.
    
    Attributi:
        id (int): ID primario.
        request_type (str): Tipo di richiesta ('accesso_negato', 'documento_bloccato').
        user_id (int): ID utente richiedente.
        document_id (int): ID documento coinvolto.
        ai_generated_reply (str): Risposta generata dall'AI.
        sent_via (str): Canale di invio ('email', 'interno').
        sent_at (datetime): Data invio.
        status (str): Stato ('generato', 'inviato', 'fallito').
        created_at (datetime): Data creazione.
        user (User): Relazione con l'utente.
        document (Document): Relazione con il documento.
    """
    __tablename__ = 'ai_replies'
    
    id = db.Column(db.Integer, primary_key=True)
    request_type = db.Column(db.String(50), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    document_id = db.Column(db.Integer, db.ForeignKey('documents.id'), nullable=True)
    ai_generated_reply = db.Column(db.Text, nullable=False)
    sent_via = db.Column(db.String(20), nullable=False)  # email, interno
    sent_at = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(20), default='generato')  # generato, inviato, fallito
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relazioni
    user = db.relationship('User', backref='ai_replies')
    document = db.relationship('Document', backref='ai_replies')
    
    def __repr__(self):
        return f'<AIReply {self.request_type} - {self.status}>'
    
    @property
    def is_sent(self):
        """Verifica se la risposta è stata inviata."""
        return self.status == 'inviato'
    
    @property
    def status_badge_class(self):
        """Restituisce la classe CSS per il badge di stato."""
        status_classes = {
            'generato': 'bg-info',
            'inviato': 'bg-success',
            'fallito': 'bg-danger'
        }
        return status_classes.get(self.status, 'bg-secondary')
    
    @property
    def request_type_display(self):
        """Restituisce il testo di visualizzazione del tipo di richiesta."""
        type_displays = {
            'accesso_negato': '🚫 Accesso Negato',
            'documento_bloccato': '🔒 Documento Bloccato',
            'permessi_insufficienti': '⚠️ Permessi Insufficienti'
        }
        return type_displays.get(self.request_type, self.request_type)

# === MODELLI QUALITY ===

class Certificazione(db.Model):
    """
    Modello per le certificazioni di qualità.
    
    Attributi:
        id (int): ID primario.
        nome (str): Nome della certificazione.
        tipo (str): Tipo certificazione (ISO 9001, ISO 14001, ecc.).
        ente_certificatore (str): Ente che ha rilasciato la certificazione.
        data_rilascio (date): Data di rilascio.
        data_scadenza (date): Data di scadenza.
        stato (str): Stato (attiva, scaduta, sospesa).
        note (str): Note aggiuntive.
        created_at (datetime): Data creazione.
        created_by (int): ID utente creatore.
    """
    __tablename__ = 'certificazioni'
    
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(200), nullable=False)
    tipo = db.Column(db.String(100), nullable=False)
    ente_certificatore = db.Column(db.String(200), nullable=False)
    data_rilascio = db.Column(db.Date, nullable=False)
    data_scadenza = db.Column(db.Date, nullable=False)
    stato = db.Column(db.String(20), default='attiva')  # attiva, scaduta, sospesa
    note = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Relazioni
    created_by_user = db.relationship('User', backref='certificazioni_creati')
    documenti = db.relationship('DocumentoQualita', backref='certificazione', lazy=True)
    
    def __repr__(self):
        return f'<Certificazione {self.nome}:{self.tipo}>'
    
    @property
    def is_scaduta(self):
        """Verifica se la certificazione è scaduta."""
        return datetime.now().date() > self.data_scadenza
    
    @property
    def giorni_alla_scadenza(self):
        """Calcola i giorni alla scadenza."""
        return (self.data_scadenza - datetime.now().date()).days
    
    @property
    def stato_display(self):
        """Restituisce lo stato di visualizzazione."""
        if self.is_scaduta:
            return 'Scaduta'
        elif self.giorni_alla_scadenza <= 30:
            return 'In Scadenza'
        else:
            return 'Attiva'

class DocumentoQualita(db.Model):
    """
    Modello per i documenti di qualità.
    
    Attributi:
        id (int): ID primario.
        titolo (str): Titolo del documento.
        versione (str): Versione del documento.
        certificazione_id (int): ID certificazione associata.
        filename (str): Nome file salvato.
        original_filename (str): Nome file originale.
        approvato (bool): Se il documento è approvato.
        approvato_da (str): Chi ha approvato.
        data_approvazione (datetime): Data approvazione.
        created_at (datetime): Data creazione.
        created_by (int): ID utente creatore.
    """
    __tablename__ = 'documenti_qualita'
    
    id = db.Column(db.Integer, primary_key=True)
    titolo = db.Column(db.String(200), nullable=False)
    versione = db.Column(db.String(50), nullable=False)
    certificazione_id = db.Column(db.Integer, db.ForeignKey('certificazioni.id'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=True)
    approvato = db.Column(db.Boolean, default=False)
    approvato_da = db.Column(db.String(150), nullable=True)
    data_approvazione = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Relazioni
    created_by_user = db.relationship('User', backref='documenti_qualita_creati')
    
    def __repr__(self):
        return f'<DocumentoQualita {self.titolo}:{self.versione}>'

class Audit(db.Model):
    """
    Modello per gli audit di qualità.
    
    Attributi:
        id (int): ID primario.
        titolo (str): Titolo dell'audit.
        tipo (str): Tipo audit (interno, esterno, di sorveglianza).
        data_inizio (date): Data inizio audit.
        data_fine (date): Data fine audit.
        auditor (str): Nome dell'auditor.
        stato (str): Stato audit (programmato, in_corso, completato).
        note (str): Note aggiuntive.
        created_at (datetime): Data creazione.
        created_by (int): ID utente creatore.
    """
    __tablename__ = 'audit_qualita'
    
    id = db.Column(db.Integer, primary_key=True)
    titolo = db.Column(db.String(200), nullable=False)
    tipo = db.Column(db.String(50), nullable=False)  # interno, esterno, sorveglianza
    data_inizio = db.Column(db.Date, nullable=False)
    data_fine = db.Column(db.Date, nullable=True)
    auditor = db.Column(db.String(150), nullable=False)
    stato = db.Column(db.String(20), default='programmato')  # programmato, in_corso, completato
    note = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Relazioni
    created_by_user = db.relationship('User', backref='audit_creati')
    checklist_items = db.relationship('AuditChecklist', backref='audit', lazy=True)
    azioni_correttive = db.relationship('AzioneCorrettiva', backref='audit', lazy=True)
    
    def __repr__(self):
        return f'<Audit {self.titolo}:{self.tipo}>'

class AuditChecklist(db.Model):
    """
    Modello per gli elementi della checklist audit.
    
    Attributi:
        id (int): ID primario.
        audit_id (int): ID audit associato.
        domanda (str): Domanda della checklist.
        risposta (str): Risposta (conforme, non_conforme, non_applicabile).
        note (str): Note aggiuntive.
        created_at (datetime): Data creazione.
    """
    __tablename__ = 'audit_checklist'
    
    id = db.Column(db.Integer, primary_key=True)
    audit_id = db.Column(db.Integer, db.ForeignKey('audit_qualita.id'), nullable=False)
    domanda = db.Column(db.Text, nullable=False)
    risposta = db.Column(db.String(20), nullable=True)  # conforme, non_conforme, non_applicabile
    note = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<AuditChecklist {self.domanda[:50]}...>'

class AzioneCorrettiva(db.Model):
    """
    Modello per le azioni correttive.
    
    Attributi:
        id (int): ID primario.
        titolo (str): Titolo dell'azione correttiva.
        descrizione (str): Descrizione dettagliata.
        audit_id (int): ID audit associato (opzionale).
        documento_id (int): ID documento associato (opzionale).
        formazione_id (int): ID formazione associata (opzionale).
        assegnato_a (int): ID utente assegnato.
        priorita (str): Priorità (bassa, media, alta, critica).
        stato (str): Stato (aperta, in_corso, completata, chiusa).
        data_scadenza (date): Data scadenza.
        data_completamento (date): Data completamento.
        note (str): Note aggiuntive.
        created_at (datetime): Data creazione.
        created_by (int): ID utente creatore.
    """
    __tablename__ = 'azioni_correttive'
    
    id = db.Column(db.Integer, primary_key=True)
    titolo = db.Column(db.String(200), nullable=False)
    descrizione = db.Column(db.Text, nullable=False)
    audit_id = db.Column(db.Integer, db.ForeignKey('audit_qualita.id'), nullable=True)
    documento_id = db.Column(db.Integer, db.ForeignKey('documents.id'), nullable=True)
    formazione_id = db.Column(db.Integer, db.ForeignKey('eventi_formazione.id'), nullable=True)
    assegnato_a = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    priorita = db.Column(db.String(20), default='media')  # bassa, media, alta, critica
    stato = db.Column(db.String(20), default='aperta')  # aperta, in_corso, completata, chiusa
    data_scadenza = db.Column(db.Date, nullable=False)
    data_completamento = db.Column(db.Date, nullable=True)
    note = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Relazioni
    created_by_user = db.relationship('User', foreign_keys=[created_by], backref='azioni_correttive_creati')
    assegnato_user = db.relationship('User', foreign_keys=[assegnato_a], backref='azioni_correttive_assegnate')
    documento = db.relationship('Document', backref='azioni_correttive')
    formazione = db.relationship('EventoFormazione', backref='azioni_correttive')
    
    def __repr__(self):
        return f'<AzioneCorrettiva {self.titolo}:{self.stato}>'
    
    @property
    def is_scaduta(self):
        """Verifica se l'azione è scaduta."""
        return datetime.now().date() > self.data_scadenza
    
    @property
    def giorni_alla_scadenza(self):
        """Calcola i giorni alla scadenza."""
        return (self.data_scadenza - datetime.now().date()).days

class AttestatoFormazione(db.Model):
    """
    Modello per gli attestati di formazione.
    
    Attributi:
        id (int): ID primario.
        evento_id (int): ID evento formazione.
        user_id (int): ID utente.
        filename (str): Nome file attestato.
        data_rilascio (date): Data rilascio attestato.
        firmato_da (str): Chi ha firmato l'attestato.
        note (str): Note aggiuntive.
        created_at (datetime): Data creazione.
    """
    __tablename__ = 'attestati_formazione'
    
    id = db.Column(db.Integer, primary_key=True)
    evento_id = db.Column(db.Integer, db.ForeignKey('eventi_formazione.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    data_rilascio = db.Column(db.Date, nullable=False)
    firmato_da = db.Column(db.String(150), nullable=True)
    note = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relazioni
    evento = db.relationship('EventoFormazione', backref='attestati')
    user = db.relationship('User', backref='attestati')
    
    def __repr__(self):
        return f'<AttestatoFormazione {self.evento.titolo}:{self.user.username}>'
