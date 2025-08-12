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

# === ENUM PER SICUREZZA ===
class SeverityLevel(enum.Enum):
    """Enum per il livello di severità degli alert di sicurezza."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class AlertStatus(enum.Enum):
    """Enum per lo stato degli alert di sicurezza."""
    OPEN = "open"
    CLOSED = "closed"

class AntivirusVerdict(enum.Enum):
    """Enum per il verdetto dell'antivirus."""
    CLEAN = "clean"
    INFECTED = "infected"

class AccessRequestStatus(enum.Enum):
    """Enum per lo stato delle richieste di accesso."""
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    EXTENDED = "extended"

# === ENUM PER ALERT DOWNLOAD ===
class DownloadAlertStatus(enum.Enum):
    """Enum per lo stato degli alert di download."""
    NEW = 'new'
    SEEN = 'seen'
    RESOLVED = 'resolved'

class DownloadAlertSeverity(enum.Enum):
    """Enum per la severità degli alert di download."""
    WARNING = 'warning'
    CRITICAL = 'critical'

# === ENUM PER RICHIESTE ACCESSO ===
class AccessRequestStatus(enum.Enum):
    """Enum per lo stato delle richieste di accesso."""
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    EXPIRED = "expired"

# === Tabelle di associazione molti-a-molti ===
user_companies = db.Table('user_companies',
    db.Column('user_id', db.Integer, db.ForeignKey('users.id'), primary_key=True),
    db.Column('company_id', db.Integer, db.ForeignKey('companies.id'), primary_key=True)
)

user_departments = db.Table('user_departments',
    db.Column('user_id', db.Integer, db.ForeignKey('users.id'), primary_key=True),
    db.Column('department_id', db.Integer, db.ForeignKey('departments.id'), primary_key=True)
)

# === Tabella di associazione Documenti-Tag ===
file_tag = db.Table('file_tag',
    db.Column('document_id', db.Integer, db.ForeignKey('documents.id'), primary_key=True),
    db.Column('tag_id', db.Integer, db.ForeignKey('tags.id'), primary_key=True)
)

# === Tabella di associazione Diario-Principi ===
diario_principi_association = db.Table('diario_principi_association',
    db.Column('diario_id', db.Integer, db.ForeignKey('diario_entries.id'), primary_key=True),
    db.Column('principio_id', db.Integer, db.ForeignKey('principi_personali.id'), primary_key=True)
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
    cooldown_until = db.Column(db.DateTime, nullable=True)  # Per blocchi temporanei

    # === Relazioni ===
    companies = db.relationship('Company', secondary=user_companies, backref='users')
    departments = db.relationship('Department', secondary=user_departments, backref='users')
    documents = db.relationship('Document', foreign_keys='Document.user_id', backref='uploader', lazy=True)
    guest_activities = db.relationship('GuestActivity', backref='user', lazy=True)
    password_links = db.relationship('PasswordLink', backref='creator', lazy=True, foreign_keys='PasswordLink.created_by_id')
    # ai_tasks = db.relationship('Task', backref='document_ai', lazy=True, foreign_keys='Document.ai_task_id')
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
    
    # === Campi per File Manager ===
    classification = db.Column(db.String(20), default='public')  # public, internal, confidential
    file_size = db.Column(db.BigInteger, nullable=True)  # Dimensione file in bytes
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # Proprietario file
    
    # === Campi per Document Intelligence AI ===
    ai_status = db.Column(db.String(50), nullable=True)  # completo, incompleto, scaduto, manca_firma
    ai_explain = db.Column(db.Text, nullable=True)  # Spiegazione AI sulla criticità
    ai_task_id = db.Column(db.Integer, db.ForeignKey('tasks.id'), nullable=True)  # Task AI associato
    ai_analysis = db.Column(db.Text, nullable=True)  # JSON con analisi completa AI
    ai_analyzed_at = db.Column(db.DateTime, nullable=True)  # Data analisi AI
    
    # === Relazione con i tag ===
    tags = db.relationship('Tag', secondary=file_tag, back_populates='documents')
    
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
class Tag(db.Model):
    """
    Modello per i tag dei documenti.
    
    Attributi:
        id (int): ID primario.
        name (str): Nome del tag.
        color (str): Colore del tag (es. 'primary', 'secondary').
        created_at (datetime): Data creazione.
        documents (list): Documenti associati.
    """
    __tablename__ = 'tags'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)
    color = db.Column(db.String(20), default='primary')  # Bootstrap colors
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relazione con i documenti
    documents = db.relationship('Document', secondary=file_tag, back_populates='tags')
    
    def __repr__(self):
        """Rappresentazione stringa del tag."""
        return f'<Tag {self.name}>'
    
    @property
    def color_class(self):
        """Restituisce la classe CSS del colore."""
        return f'bg-{self.color}'


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


# === ALIAS PER COMPATIBILITÀ ===
# Mantiene compatibilità con il codice esistente che usa AuditLog
AuditLog = AdminLog

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



# === MODELLO LOG DOWNLOAD DOCUMENTI ===
class DownloadLog(db.Model):
    """
    Modello per il log dei download dei documenti.
    
    Attributi:
        id (int): ID primario.
        user_id (int): ID utente che ha fatto il download.
        document_id (int): ID documento scaricato.
        timestamp (datetime): Data/ora del download.
        ip_address (str): Indirizzo IP del client.
        user_agent (str): User agent del browser.
        status (str): Stato del download ('success', 'blocked').
        reason_block (str): Motivo del blocco (se status='blocked').
        source (str): Fonte del download ('web', 'api').
        filesize (int): Dimensione del file scaricato in bytes.
        user (User): Relazione con l'utente.
        document (Document): Relazione con il documento.
    """
    __tablename__ = "download_log"
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    document_id = db.Column(db.Integer, db.ForeignKey("documents.id"), nullable=False, index=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    ip_address = db.Column(db.String(45), nullable=True)  # IPv4 or IPv6
    user_agent = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), default='success', nullable=False, index=True)  # success, blocked
    reason_block = db.Column(db.String(255), nullable=True)  # Motivo del blocco
    source = db.Column(db.String(20), default='web', nullable=False)  # web, api
    filesize = db.Column(db.BigInteger, nullable=True)  # Dimensione file in bytes

    user = db.relationship("User", backref="download_logs")
    document = db.relationship("Document", backref="download_logs")
    
    def __repr__(self):
        """Rappresentazione stringa del log download."""
        return f'<DownloadLog {self.user_id}:{self.document_id}:{self.timestamp}>'
    
    @property
    def username(self):
        """Restituisce lo username dell'utente."""
        return self.user.username if self.user else 'N/A'
    
    @property
    def filename(self):
        """Restituisce il nome del file."""
        return self.document.filename if self.document else 'N/A'
    
    @property
    def filesize_formatted(self):
        """Restituisce la dimensione del file formattata."""
        if not self.filesize:
            return 'N/A'
        
        for unit in ['B', 'KB', 'MB', 'GB']:
            if self.filesize < 1024.0:
                return f"{self.filesize:.1f} {unit}"
            self.filesize /= 1024.0
        return f"{self.filesize:.1f} TB"

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
    Modello per tracciare le firme digitali sui documenti.
    
    Attributi:
        id (int): ID primario.
        user_id (int): ID utente che ha firmato.
        document_id (int): ID documento firmato.
        timestamp (datetime): Data/ora della firma.
        ip_address (str): IP del client.
        user_agent (str): User agent del browser.
        stato (str): Stato firma ('firmato', 'rifiutato', 'in_attesa').
        commento (str): Commento opzionale alla firma.
        user (User): Relazione con l'utente.
        document (Document): Relazione con il documento.
    """
    __tablename__ = 'firme_documenti'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    document_id = db.Column(db.Integer, db.ForeignKey('documents.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    ip_address = db.Column(db.String(100), nullable=True)
    user_agent = db.Column(db.String(300), nullable=True)
    stato = db.Column(db.String(20), default='in_attesa')  # firmato, rifiutato, in_attesa
    commento = db.Column(db.Text, nullable=True)
    
    # Relazioni
    user = db.relationship('User', backref='firme_documenti')
    document = db.relationship('Document', backref='firme_documenti')
    
    def __repr__(self):
        return f'<FirmaDocumento {self.id}: User {self.user_id} -> Document {self.document_id} - {self.stato}>'
    
    @property
    def timestamp_formatted(self):
        """Formatta il timestamp per la visualizzazione."""
        return self.timestamp.strftime('%d/%m/%Y %H:%M:%S')
    
    @property
    def user_display(self):
        """Nome completo dell'utente."""
        if self.user:
            return f"{self.user.first_name} {self.user.last_name}".strip() or self.user.username
        return "Utente sconosciuto"
    
    @property
    def document_display(self):
        """Titolo del documento."""
        if self.document:
            return self.document.title
        return "Documento sconosciuto"
    
    @property
    def stato_badge_class(self):
        """Classe CSS per il badge dello stato."""
        if self.stato == 'firmato':
            return 'bg-success'
        elif self.stato == 'rifiutato':
            return 'bg-danger'
        else:
            return 'bg-warning'
    
    @property
    def stato_display(self):
        """Testo dello stato per la visualizzazione."""
        stati = {
            'firmato': '✅ Firmato',
            'rifiutato': '❌ Rifiutato',
            'in_attesa': '⏳ In Attesa'
        }
        return stati.get(self.stato, self.stato)
    
    @property
    def is_firmato(self):
        """Verifica se il documento è stato firmato."""
        return self.stato == 'firmato'
    
    @property
    def is_rifiutato(self):
        """Verifica se il documento è stato rifiutato."""
        return self.stato == 'rifiutato'
    
    @property
    def is_in_attesa(self):
        """Verifica se il documento è in attesa di firma."""
        return self.stato == 'in_attesa'

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

# === MODELLO ATTIVITÀ AI POST-MIGRAZIONE ===
class AttivitaAI(db.Model):
    """
    Modello per tracciare le attività AI degli utenti/guest post-migrazione.
    
    Attributi:
        id (int): ID primario.
        user_id (int): ID utente (opzionale).
        guest_id (int): ID guest (opzionale).
        stato_iniziale (str): Stato iniziale ('nuovo_import', 'monitorato', 'stabile').
        note (str): Note sull'attività.
        created_at (datetime): Data creazione record.
        updated_at (datetime): Data ultimo aggiornamento.
        user (User): Relazione con utente.
        guest (GuestUser): Relazione con guest.
    """
    __tablename__ = 'attivita_ai'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    guest_id = db.Column(db.Integer, db.ForeignKey('guest_users.id'), nullable=True)
    stato_iniziale = db.Column(db.String(50), nullable=False, default='nuovo_import')
    note = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relazioni
    user = db.relationship('User', backref='attivita_ai')
    guest = db.relationship('GuestUser', backref='attivita_ai')
    
    def __repr__(self):
        return f'<AttivitaAI {self.stato_iniziale} - {self.created_at}>'
    
    @property
    def is_nuovo_import(self):
        """Verifica se è un nuovo import."""
        return self.stato_iniziale == 'nuovo_import'
    
    @property
    def giorni_da_import(self):
        """Calcola i giorni trascorsi dall'import."""
        delta = datetime.utcnow() - self.created_at
        return delta.days
    
    @property
    def badge_class(self):
        """Restituisce la classe CSS per il badge."""
        if self.giorni_da_import <= 7:
            return 'badge-danger'
        elif self.giorni_da_import <= 30:
            return 'badge-warning'
        else:
            return 'badge-success'
    
    @property
    def display_text(self):
        """Restituisce il testo di visualizzazione."""
        if self.giorni_da_import <= 7:
            return f"Nuovo import ({self.giorni_da_import} giorni)"
        elif self.giorni_da_import <= 30:
            return f"Import recente ({self.giorni_da_import} giorni)"
        else:
            return "Import stabile"


# === MODELLO ALERT AI POST-MIGRAZIONE ===
class AlertAI(db.Model):
    """
    Modello per gli alert AI post-migrazione.
    
    Attributi:
        id (int): ID primario.
        user_id (int): ID utente (opzionale).
        guest_id (int): ID guest (opzionale).
        tipo_alert (str): Tipo di alert ('download_massivo', 'accessi_falliti', 'ip_sospetto').
        descrizione (str): Descrizione dell'alert.
        timestamp (datetime): Data/ora dell'alert.
        stato (str): Stato alert ('nuovo', 'in_revisione', 'chiuso').
        ip_address (str): IP dell'utente.
        user_agent (str): User agent del browser.
        created_at (datetime): Data creazione.
        user (User): Relazione con utente.
        guest (GuestUser): Relazione con guest.
    """
    __tablename__ = 'alert_ai'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    guest_id = db.Column(db.Integer, db.ForeignKey('guest_users.id'), nullable=True)
    tipo_alert = db.Column(db.String(50), nullable=False)
    descrizione = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    stato = db.Column(db.String(20), default='nuovo')  # nuovo, in_revisione, chiuso
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.Text, nullable=True)
    livello = db.Column(db.String(20), default='medio')  # basso, medio, alto, critico
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relazioni
    user = db.relationship('User', backref='alert_ai')
    guest = db.relationship('GuestUser', backref='alert_ai')
    
    def __repr__(self):
        return f'<AlertAI {self.tipo_alert} - {self.stato}>'
    
    @property
    def is_nuovo(self):
        """Verifica se l'alert è nuovo."""
        return self.stato == 'nuovo'
    
    @property
    def is_in_revisione(self):
        """Verifica se l'alert è in revisione."""
        return self.stato == 'in_revisione'
    
    @property
    def is_chiuso(self):
        """Verifica se l'alert è chiuso."""
        return self.stato == 'chiuso'
    
    @property
    def stato_badge_class(self):
        """Restituisce la classe CSS per il badge di stato."""
        if self.stato == 'nuovo':
            return 'badge-danger'
        elif self.stato == 'in_revisione':
            return 'badge-warning'
        else:
            return 'badge-success'
    
    @property
    def tipo_alert_display(self):
        """Restituisce il testo di visualizzazione del tipo alert."""
        tipo_display = {
            'download_massivo': 'Download Massivo',
            'accessi_falliti': 'Accessi Falliti',
            'ip_sospetto': 'IP Sospetto',
            'comportamento_anomalo': 'Comportamento Anomalo',
            'accesso_fuori_orario': 'Accesso Fuori Orario',
            'accesso_simultaneo': 'Accesso Simultaneo',
            'accesso_non_autorizzato': 'Accesso Non Autorizzato'
        }
        return tipo_display.get(self.tipo_alert, self.tipo_alert)
    
    @property
    def utente_display(self):
        """Restituisce il nome dell'utente o guest."""
        if self.user:
            return f"{self.user.first_name} {self.user.last_name}"
        elif self.guest:
            return f"Guest: {self.guest.email}"
        else:
            return "Utente sconosciuto"
    
    @property
    def livello_badge_class(self):
        """Restituisce la classe CSS per il badge del livello."""
        livello_classes = {
            'basso': 'badge-secondary',
            'medio': 'badge-warning',
            'alto': 'badge-danger',
            'critico': 'badge-dark'
        }
        return livello_classes.get(self.livello, 'badge-secondary')
    
    @property
    def livello_display(self):
        """Restituisce il testo di visualizzazione del livello."""
        livello_display = {
            'basso': 'Basso',
            'medio': 'Medio',
            'alto': 'Alto',
            'critico': 'Critico'
        }
        return livello_display.get(self.livello, self.livello)


class LogInvioPDF(db.Model):
    """
    Modello per il log centralizzato degli invii PDF via email.
    
    Attributi:
        id (int): ID primario.
        id_utente_o_guest (int): ID dell'utente o guest.
        tipo (str): Tipo ('user' o 'guest').
        inviato_da (str): Email dell'admin o CEO che ha inviato.
        inviato_a (str): Email del destinatario.
        oggetto_email (str): Oggetto dell'email.
        messaggio_email (str): Messaggio aggiuntivo (opzionale).
        timestamp (datetime): Data/ora dell'invio.
        esito (str): Esito ('successo' o 'errore').
        errore (str): Messaggio errore se fallito (nullable).
        user (User): Relazione con l'utente (se tipo='user').
    """
    __tablename__ = 'log_invio_pdf'
    
    id = db.Column(db.Integer, primary_key=True)
    id_utente_o_guest = db.Column(db.Integer, nullable=False)  # ID utente o guest
    tipo = db.Column(db.String(10), nullable=False)  # 'user' o 'guest'
    inviato_da = db.Column(db.String(150), nullable=False)  # Email admin/CEO
    inviato_a = db.Column(db.String(150), nullable=False)  # Email destinatario
    oggetto_email = db.Column(db.String(255), nullable=False)
    messaggio_email = db.Column(db.Text, nullable=True)  # Messaggio aggiuntivo
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    esito = db.Column(db.String(20), nullable=False)  # 'successo' o 'errore'
    errore = db.Column(db.Text, nullable=True)  # Messaggio errore se fallito
    
    # Relazione con User (per tipo='user')
    user = db.relationship('User', 
                         primaryjoin="and_(LogInvioPDF.id_utente_o_guest == User.id, "
                                   "LogInvioPDF.tipo == 'user')",
                         backref='pdf_inviati',
                         foreign_keys=[id_utente_o_guest])
    
    def __repr__(self):
        """Rappresentazione stringa del log invio PDF."""
        return f'<LogInvioPDF {self.tipo} - {self.inviato_a} - {self.esito}>'
    
    @property
    def is_successo(self):
        """Verifica se l'invio è stato un successo."""
        return self.esito == 'successo'
    
    @property
    def is_errore(self):
        """Verifica se l'invio ha avuto un errore."""
        return self.esito == 'errore'
    
    @property
    def esito_badge_class(self):
        """Restituisce la classe CSS per il badge dell'esito."""
        return 'badge-success' if self.is_successo else 'badge-danger'
    
    @property
    def esito_display(self):
        """Restituisce il testo di visualizzazione dell'esito."""
        return '✅ Successo' if self.is_successo else '❌ Errore'
    
    @property
    def tipo_display(self):
        """Restituisce il testo di visualizzazione del tipo."""
        return 'Utente' if self.tipo == 'user' else 'Guest'
    
    @property
    def nome_utente_guest(self):
        """Restituisce il nome dell'utente o guest."""
        if self.tipo == 'user' and self.user:
            return f"{self.user.first_name or self.user.nome or ''} {self.user.last_name or self.user.cognome or ''}".strip() or self.user.email
        else:
            # Per guest, cerca nel database User con role='guest'
            from extensions import db
            guest = db.session.query(User).filter_by(id=self.id_utente_o_guest, role='guest').first()
            if guest:
                return f"{guest.first_name or guest.nome or ''} {guest.last_name or guest.cognome or ''}".strip() or guest.email
            return f"Guest #{self.id_utente_o_guest}"
    
    @property
    def timestamp_formatted(self):
        """Restituisce il timestamp formattato."""
        return self.timestamp.strftime('%d/%m/%Y %H:%M') if self.timestamp else 'N/A'
    
    @property
    def messaggio_preview(self):
        """Restituisce un'anteprima del messaggio email."""
        if self.messaggio_email:
            return self.messaggio_email[:50] + '...' if len(self.messaggio_email) > 50 else self.messaggio_email
        return 'Nessun messaggio aggiuntivo'


class QMSStandardRequirement(db.Model):
    """
    Modello per i requisiti normativi degli standard di qualità.
    
    Attributi:
        id (int): ID primario.
        standard_name (str): Nome dello standard (es. ISO 9001, HACCP, BRC, IFS).
        clause (str): Clausola del requisito (es. "4.2.1", "7.5.1").
        description (str): Descrizione dettagliata del requisito.
        category (str): Categoria del requisito (es. "Documentazione", "Formazione", "Controllo").
        priority (str): Priorità del requisito (bassa, media, alta, critica).
        is_mandatory (bool): Se il requisito è obbligatorio.
        created_at (datetime): Data creazione.
        mappings (list): Mappature con documenti.
    """
    __tablename__ = 'qms_standard_requirements'
    
    id = db.Column(db.Integer, primary_key=True)
    standard_name = db.Column(db.String(100), nullable=False)  # ISO 9001, HACCP, BRC, IFS
    clause = db.Column(db.String(50), nullable=False)  # 4.2.1, 7.5.1, ecc.
    description = db.Column(db.Text, nullable=False)  # Descrizione dettagliata
    category = db.Column(db.String(100), nullable=True)  # Documentazione, Formazione, Controllo
    priority = db.Column(db.String(20), default='media')  # bassa, media, alta, critica
    is_mandatory = db.Column(db.Boolean, default=True)  # Se obbligatorio
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relazioni
    mappings = db.relationship('QMSRequirementMapping', backref='requirement', lazy=True)
    
    def __repr__(self):
        """Rappresentazione stringa del requisito."""
        return f'<QMSStandardRequirement {self.standard_name} - {self.clause}>'
    
    @property
    def priority_badge_class(self):
        """Restituisce la classe CSS per il badge della priorità."""
        priority_classes = {
            'bassa': 'badge-secondary',
            'media': 'badge-warning',
            'alta': 'badge-danger',
            'critica': 'badge-dark'
        }
        return priority_classes.get(self.priority, 'badge-secondary')
    
    @property
    def priority_display(self):
        """Restituisce il testo di visualizzazione della priorità."""
        priority_display = {
            'bassa': 'Bassa',
            'media': 'Media',
            'alta': 'Alta',
            'critica': 'Critica'
        }
        return priority_display.get(self.priority, self.priority)
    
    @property
    def standard_display(self):
        """Restituisce il nome dello standard formattato."""
        return self.standard_name.replace('_', ' ').title()
    
    @property
    def clause_display(self):
        """Restituisce la clausola formattata."""
        return f"Clausola {self.clause}"
    
    @property
    def coverage_score(self):
        """Calcola il punteggio di copertura basato sulle mappature."""
        if not self.mappings:
            return 0
        
        total_score = sum(mapping.mapping_score for mapping in self.mappings)
        return min(100, total_score)  # Massimo 100
    
    @property
    def coverage_status(self):
        """Restituisce lo stato di copertura del requisito."""
        score = self.coverage_score
        if score >= 80:
            return 'completo'
        elif score >= 50:
            return 'parziale'
        else:
            return 'mancante'
    
    @property
    def coverage_badge_class(self):
        """Restituisce la classe CSS per il badge di copertura."""
        status_classes = {
            'completo': 'badge-success',
            'parziale': 'badge-warning',
            'mancante': 'badge-danger'
        }
        return status_classes.get(self.coverage_status, 'badge-secondary')
    
    @property
    def coverage_display(self):
        """Restituisce il testo di visualizzazione della copertura."""
        status_display = {
            'completo': '✅ Completo',
            'parziale': '⚠️ Parziale',
            'mancante': '❌ Mancante'
        }
        return status_display.get(self.coverage_status, 'Sconosciuto')


class QMSRequirementMapping(db.Model):
    """
    Modello per la mappatura tra requisiti normativi e documenti aziendali.
    
    Attributi:
        id (int): ID primario.
        requirement_id (int): ID requisito normativo.
        document_id (int): ID documento aziendale.
        mapped_by (str): Email dell'admin che ha creato la mappatura.
        mapping_score (float): Punteggio di mappatura (0-100).
        ai_analysis (str): Analisi AI della mappatura.
        confidence_score (float): Punteggio di confidenza AI (0-100).
        mapping_notes (str): Note sulla mappatura.
        created_at (datetime): Data creazione.
        requirement (QMSStandardRequirement): Relazione con il requisito.
        document (Document): Relazione con il documento.
    """
    __tablename__ = 'qms_requirement_mappings'
    
    id = db.Column(db.Integer, primary_key=True)
    requirement_id = db.Column(db.Integer, db.ForeignKey('qms_standard_requirements.id'), nullable=False)
    document_id = db.Column(db.Integer, db.ForeignKey('documents.id'), nullable=False)
    mapped_by = db.Column(db.String(150), nullable=False)  # Email admin
    mapping_score = db.Column(db.Float, nullable=False)  # 0-100
    ai_analysis = db.Column(db.Text, nullable=True)  # Analisi AI
    confidence_score = db.Column(db.Float, nullable=True)  # 0-100
    mapping_notes = db.Column(db.Text, nullable=True)  # Note mappatura
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relazioni
    document = db.relationship('Document', backref='qms_mappings')
    
    def __repr__(self):
        """Rappresentazione stringa della mappatura."""
        return f'<QMSRequirementMapping {self.requirement_id} -> {self.document_id}>'
    
    @property
    def mapping_score_display(self):
        """Restituisce il punteggio di mappatura formattato."""
        return f"{self.mapping_score:.1f}%"
    
    @property
    def confidence_score_display(self):
        """Restituisce il punteggio di confidenza formattato."""
        if self.confidence_score:
            return f"{self.confidence_score:.1f}%"
        return "N/A"
    
    @property
    def mapping_status(self):
        """Restituisce lo stato della mappatura."""
        if self.mapping_score >= 80:
            return 'eccellente'
        elif self.mapping_score >= 60:
            return 'buona'
        elif self.mapping_score >= 40:
            return 'sufficiente'
        else:
            return 'insufficiente'
    
    @property
    def mapping_badge_class(self):
        """Restituisce la classe CSS per il badge di mappatura."""
        status_classes = {
            'eccellente': 'badge-success',
            'buona': 'badge-info',
            'sufficiente': 'badge-warning',
            'insufficiente': 'badge-danger'
        }
        return status_classes.get(self.mapping_status, 'badge-secondary')
    
    @property
    def mapping_display(self):
        """Restituisce il testo di visualizzazione della mappatura."""
        status_display = {
            'eccellente': '⭐ Eccellente',
            'buona': '✅ Buona',
            'sufficiente': '⚠️ Sufficiente',
            'insufficiente': '❌ Insufficiente'
        }
        return status_display.get(self.mapping_status, 'Sconosciuto')
    
    @property
    def created_at_formatted(self):
        """Restituisce la data di creazione formattata."""
        return self.created_at.strftime('%d/%m/%Y %H:%M') if self.created_at else 'N/A'

# === MODELLO PRINCIPIO PERSONALE ===
class PrincipioPersonale(db.Model):
    """
    Modello per i principi personali del CEO.
    
    Attributi:
        id (int): ID primario.
        user_id (int): ID utente CEO.
        titolo (str): Titolo del principio.
        descrizione (str): Descrizione dettagliata.
        categoria (str): Categoria del principio (es. "Leadership", "Equilibrio", "Innovazione").
        attiva (bool): Se il principio è attualmente attivo.
        data_creazione (datetime): Data creazione.
        data_aggiornamento (datetime): Data ultimo aggiornamento.
        priorita (int): Priorità del principio (1-10).
        colore (str): Colore per visualizzazione.
        user (User): Relazione con l'utente.
        diario_entries (list): Entrate diario collegate.
    """
    __tablename__ = "principi_personali"
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    titolo = db.Column(db.String(200), nullable=False)
    descrizione = db.Column(db.Text, nullable=True)
    categoria = db.Column(db.String(100), nullable=True)
    attiva = db.Column(db.Boolean, default=True)
    data_creazione = db.Column(db.DateTime, default=datetime.utcnow)
    data_aggiornamento = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    priorita = db.Column(db.Integer, default=5)  # 1-10
    colore = db.Column(db.String(20), default='primary')  # Bootstrap colors
    
    # Relazioni
    user = db.relationship("User", backref="principi_personali")
    diario_entries = db.relationship("DiarioEntry", secondary="diario_principi_association", back_populates="principi_collegati_rel")
    
    def __repr__(self):
        return f"<PrincipioPersonale(id={self.id}, titolo={self.titolo}, attiva={self.attiva})>"
    
    @property
    def is_active(self):
        """Verifica se il principio è attivo."""
        return self.attiva
    
    @property
    def priority_display(self):
        """Display della priorità."""
        return f"⭐ {self.priorita}/10"
    
    @property
    def color_class(self):
        """Classe colore Bootstrap."""
        return f"bg-{self.colore}"

# === MODELLO DIARIO ENTRY ===
class DiarioEntry(db.Model):
    """
    Modello per le entrate del diario CEO.
    
    Attributi:
        id (int): ID primario.
        user_id (int): ID utente CEO.
        data (date): Data dell'entrata.
        titolo (str): Titolo dell'entrata.
        contenuto (str): Contenuto del diario.
        umore (str): Umore del giorno (1-10).
        energia (str): Livello energia (1-10).
        gratitudine (str): Cosa sono grato oggi.
        sfide (str): Sfide affrontate.
        obiettivi (str): Obiettivi per domani.
        riflessioni (str): Riflessioni personali.
        data_creazione (datetime): Data creazione.
        data_aggiornamento (datetime): Data ultimo aggiornamento.
        analisi_ai (str): JSON con analisi AI.
        principi_collegati (list): Principi collegati.
        task_generati (list): Task AI generati.
        user (User): Relazione con l'utente.
        principi_collegati (list): Relazione con principi.
        task_generati (list): Relazione con task AI.
    """
    __tablename__ = "diario_entries"
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    data = db.Column(db.Date, nullable=False)
    titolo = db.Column(db.String(200), nullable=False)
    contenuto = db.Column(db.Text, nullable=True)
    umore = db.Column(db.Integer, nullable=True)  # 1-10
    energia = db.Column(db.Integer, nullable=True)  # 1-10
    gratitudine = db.Column(db.Text, nullable=True)
    sfide = db.Column(db.Text, nullable=True)
    obiettivi = db.Column(db.Text, nullable=True)
    riflessioni = db.Column(db.Text, nullable=True)
    data_creazione = db.Column(db.DateTime, default=datetime.utcnow)
    data_aggiornamento = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # === Campi per analisi AI e collegamenti ===
    analisi_ai = db.Column(db.Text, nullable=True)  # JSON con analisi AI
    principi_collegati = db.Column(db.Text, nullable=True)  # JSON array di ID principi
    task_generati = db.Column(db.Text, nullable=True)  # JSON array di ID task
    
    # Relazioni
    user = db.relationship("User", backref="diario_entries")
    principi_collegati_rel = db.relationship("PrincipioPersonale", secondary="diario_principi_association", back_populates="diario_entries")
    
    def __repr__(self):
        return f"<DiarioEntry(id={self.id}, data={self.data}, titolo={self.titolo})>"
    
    @property
    def data_formatted(self):
        """Data formattata."""
        return self.data.strftime("%d/%m/%Y")
    
    @property
    def umore_display(self):
        """Display dell'umore."""
        if self.umore:
            emoji = "😊" if self.umore >= 7 else "😐" if self.umore >= 4 else "😔"
            return f"{emoji} {self.umore}/10"
        return "N/A"
    
    @property
    def energia_display(self):
        """Display dell'energia."""
        if self.energia:
            emoji = "⚡" if self.energia >= 7 else "🔋" if self.energia >= 4 else "🔋"
            return f"{emoji} {self.energia}/10"
        return "N/A"
    
    @property
    def principi_collegati_list(self):
        """Lista ID principi collegati."""
        if self.principi_collegati:
            try:
                import json
                return json.loads(self.principi_collegati)
            except:
                return []
        return []
    
    @property
    def task_generati_list(self):
        """Lista ID task generati."""
        if self.task_generati:
            try:
                import json
                return json.loads(self.task_generati)
            except:
                return []
        return []
    
    @property
    def analisi_ai_dict(self):
        """Dizionario analisi AI."""
        if self.analisi_ai:
            try:
                import json
                return json.loads(self.analisi_ai)
            except:
                return {}
        return {}
    
    def aggiungi_principio_collegato(self, principio_id):
        """Aggiunge un principio collegato."""
        principi = self.principi_collegati_list
        if principio_id not in principi:
            principi.append(principio_id)
            self.principi_collegati = json.dumps(principi)
    
    def aggiungi_task_generato(self, task_id):
        """Aggiunge un task generato."""
        task = self.task_generati_list
        if task_id not in task:
            task.append(task_id)
            self.task_generati = json.dumps(task)

# === MODELLO NOTIFICA CEO ===
class NotificaCEO(db.Model):
    """
    Modello per le notifiche automatiche al CEO per invii PDF sensibili.
    
    Attributi:
        id (int): ID primario.
        titolo (str): Titolo della notifica.
        descrizione (str): Descrizione dettagliata.
        tipo (str): Tipo notifica ('invio_pdf_sensibile', 'alert_ai', 'guest_scadenza').
        email_mittente (str): Email di chi ha inviato il PDF.
        email_destinatario (str): Email destinatario del PDF.
        nome_utente_guest (str): Nome dell'utente/guest coinvolto.
        stato (str): Stato notifica ('nuovo', 'letto').
        data_creazione (datetime): Data/ora creazione.
        data_lettura (datetime): Data/ora lettura (opzionale).
        log_invio_id (int): ID del log invio associato.
        log_invio (LogInvioPDF): Relazione con il log invio.
    """
    __tablename__ = "notifiche_ceo"
    
    id = db.Column(db.Integer, primary_key=True)
    titolo = db.Column(db.String(200), nullable=False)
    descrizione = db.Column(db.Text, nullable=True)
    tipo = db.Column(db.String(50), nullable=False)  # invio_pdf_sensibile, alert_ai, guest_scadenza
    email_mittente = db.Column(db.String(150), nullable=False)
    email_destinatario = db.Column(db.String(150), nullable=False)
    nome_utente_guest = db.Column(db.String(200), nullable=True)
    stato = db.Column(db.String(20), default='nuovo')  # nuovo, letto
    data_creazione = db.Column(db.DateTime, default=datetime.utcnow)
    data_lettura = db.Column(db.DateTime, nullable=True)
    log_invio_id = db.Column(db.Integer, db.ForeignKey('log_invio_pdf.id'), nullable=True)
    
    # Relazioni
    log_invio = db.relationship("LogInvioPDF", backref="notifiche_ceo")
    
    def __repr__(self):
        """Rappresentazione stringa della notifica."""
        return f"<NotificaCEO {self.id} - {self.titolo} - {self.stato}>"
    
    @property
    def is_nuovo(self):
        """Verifica se la notifica è nuova."""
        return self.stato == 'nuovo'
    
    @property
    def is_letta(self):
        """Verifica se la notifica è stata letta."""
        return self.stato == 'letto'
    
    @property
    def stato_badge_class(self):
        """Restituisce la classe CSS per il badge dello stato."""
        classi = {
            'nuovo': 'bg-danger',
            'letto': 'bg-secondary'
        }
        return classi.get(self.stato, 'bg-secondary')
    
    @property
    def stato_display(self):
        """Restituisce lo stato visualizzabile."""
        stati = {
            'nuovo': '🆕 Nuovo',
            'letto': '✅ Letto'
        }
        return stati.get(self.stato, self.stato)
    
    @property
    def tipo_display(self):
        """Restituisce il tipo visualizzabile."""
        tipi = {
            'invio_pdf_sensibile': '📄 Invio PDF Sensibile',
            'alert_ai': '🤖 Alert AI',
            'guest_scadenza': '⏰ Guest Scadenza'
        }
        return tipi.get(self.tipo, self.tipo)
    
    @property
    def data_creazione_formatted(self):
        """Restituisce la data di creazione formattata."""
        return self.data_creazione.strftime('%d/%m/%Y %H:%M:%S')
    
    @property
    def data_lettura_formatted(self):
        """Restituisce la data di lettura formattata."""
        if self.data_lettura:
            return self.data_lettura.strftime('%d/%m/%Y %H:%M:%S')
        return '-'
    
    def marca_letta(self):
        """Marca la notifica come letta."""
        self.stato = 'letto'
        self.data_lettura = datetime.utcnow()

# === MODELLO ALERT REPORT CEO ===
class AlertReportCEO(db.Model):
    """
    Modello per gli alert automatici sui report CEO mensili.
    
    Attributi:
        id (int): ID primario.
        mese (int): Mese del report (1-12).
        anno (int): Anno del report.
        numero_invii_critici (int): Numero di invii critici rilevati.
        trigger_attivo (bool): Se l'alert è attualmente attivo.
        data_trigger (datetime): Data/ora attivazione alert.
        id_report_ceo (str): Nome file del report associato.
        letto (bool): Se l'alert è stato letto dal CEO.
        data_lettura (datetime): Data/ora lettura (opzionale).
        note (str): Note aggiuntive sull'alert.
    """
    __tablename__ = "alert_report_ceo"
    
    id = db.Column(db.Integer, primary_key=True)
    mese = db.Column(db.Integer, nullable=False)
    anno = db.Column(db.Integer, nullable=False)
    numero_invii_critici = db.Column(db.Integer, nullable=False, default=0)
    trigger_attivo = db.Column(db.Boolean, default=True)
    data_trigger = db.Column(db.DateTime, default=datetime.utcnow)
    id_report_ceo = db.Column(db.String(255), nullable=True)  # Nome file report
    letto = db.Column(db.Boolean, default=False)
    data_lettura = db.Column(db.DateTime, nullable=True)
    note = db.Column(db.Text, nullable=True)
    
    def __repr__(self):
        """Rappresentazione stringa dell'alert report."""
        return f"<AlertReportCEO {self.mese}/{self.anno} - {self.numero_invii_critici} critici>"
    
    @property
    def is_attivo(self):
        """Verifica se l'alert è attivo."""
        return self.trigger_attivo and not self.letto
    
    @property
    def is_letto(self):
        """Verifica se l'alert è stato letto."""
        return self.letto
    
    @property
    def periodo_display(self):
        """Restituisce il periodo visualizzabile."""
        mesi = {
            1: 'Gennaio', 2: 'Febbraio', 3: 'Marzo', 4: 'Aprile',
            5: 'Maggio', 6: 'Giugno', 7: 'Luglio', 8: 'Agosto',
            9: 'Settembre', 10: 'Ottobre', 11: 'Novembre', 12: 'Dicembre'
        }
        return f"{mesi.get(self.mese, f'Mese {self.mese}')} {self.anno}"
    
    @property
    def livello_criticita(self):
        """Determina il livello di criticità basato sul numero di invii critici."""
        if self.numero_invii_critici >= 10:
            return 'critico'
        elif self.numero_invii_critici >= 5:
            return 'alto'
        elif self.numero_invii_critici >= 3:
            return 'medio'
        else:
            return 'basso'
    
    @property
    def livello_badge_class(self):
        """Restituisce la classe CSS per il badge del livello."""
        classi = {
            'critico': 'badge-danger',
            'alto': 'badge-warning',
            'medio': 'badge-info',
            'basso': 'badge-secondary'
        }
        return classi.get(self.livello_criticita, 'badge-secondary')
    
    @property
    def livello_display(self):
        """Restituisce il testo di visualizzazione del livello."""
        livelli = {
            'critico': '🔴 Critico',
            'alto': '🟡 Alto',
            'medio': '🔵 Medio',
            'basso': '⚪ Basso'
        }
        return livelli.get(self.livello_criticita, 'Sconosciuto')
    
    @property
    def data_trigger_formatted(self):
        """Restituisce la data di trigger formattata."""
        return self.data_trigger.strftime('%d/%m/%Y %H:%M:%S') if self.data_trigger else '-'
    
    @property
    def data_lettura_formatted(self):
        """Restituisce la data di lettura formattata."""
        if self.data_lettura:
            return self.data_lettura.strftime('%d/%m/%Y %H:%M:%S')
        return '-'
    
    def marca_letto(self):
        """Marca l'alert come letto."""
        self.letto = True
        self.data_lettura = datetime.utcnow()
    
    def disattiva_alert(self):
        """Disattiva l'alert."""
        self.trigger_attivo = False
    
    @classmethod
    def get_alert_attivo_per_periodo(cls, mese, anno):
        """Ottiene l'alert attivo per un periodo specifico."""
        return cls.query.filter_by(
            mese=mese,
            anno=anno,
            trigger_attivo=True
        ).first()
    
    @classmethod
    def get_alert_non_letti(cls):
        """Ottiene tutti gli alert non letti."""
        return cls.query.filter_by(
            trigger_attivo=True,
            letto=False
        ).order_by(cls.data_trigger.desc()).all()
    
    @classmethod
    def count_alert_non_letti(cls):
        """Conta gli alert non letti."""
        return cls.query.filter_by(
            trigger_attivo=True,
            letto=False
        ).count()

# === MODELLO LETTURA PDF ===
class LetturaPDF(db.Model):
    """
    Modello per tracciare ogni volta che un utente apre un PDF.
    
    Attributi:
        id (int): ID primario.
        user_id (int): ID utente che ha letto il PDF.
        document_id (int): ID documento PDF letto.
        timestamp (datetime): Data/ora della lettura.
        ip_address (str): IP del client.
        user_agent (str): User agent del browser.
        user (User): Relazione con l'utente.
        document (Document): Relazione con il documento.
    """
    __tablename__ = 'letture_pdf'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    document_id = db.Column(db.Integer, db.ForeignKey('documents.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    ip_address = db.Column(db.String(100), nullable=True)
    user_agent = db.Column(db.String(300), nullable=True)
    
    # Relazioni
    user = db.relationship('User', backref='letture_pdf')
    document = db.relationship('Document', backref='letture_pdf')
    
    def __repr__(self):
        return f'<LetturaPDF {self.id}: User {self.user_id} -> Document {self.document_id} at {self.timestamp}>'
    
    @property
    def timestamp_formatted(self):
        """Formatta il timestamp per la visualizzazione."""
        return self.timestamp.strftime('%d/%m/%Y %H:%M:%S')
    
    @property
    def user_display(self):
        """Nome completo dell'utente."""
        if self.user:
            return f"{self.user.first_name} {self.user.last_name}".strip() or self.user.username
        return "Utente sconosciuto"
    
    @property
    def document_display(self):
        """Titolo del documento."""
        if self.document:
            return self.document.title
        return "Documento sconosciuto"

# === MODELLO AGGREGATO REGISTRO INVII PDF ===
class RegistroInviiDTO:
    """
    Data Transfer Object per aggregare i dati di invio, lettura e firma dei documenti.
    Questo modello non è una tabella del database, ma un oggetto per rappresentare
    i dati aggregati dal registro invii.
    
    Attributi:
        documento_id (int): ID del documento.
        documento_titolo (str): Titolo del documento.
        utente_id (int): ID dell'utente destinatario.
        utente_nome (str): Nome completo dell'utente.
        utente_email (str): Email dell'utente.
        data_invio (datetime): Data/ora dell'invio PDF.
        inviato_da (str): Email di chi ha inviato.
        esito_invio (str): Esito dell'invio ('successo' o 'errore').
        data_lettura (datetime): Data/ora dell'ultima lettura (opzionale).
        stato_lettura (str): Stato lettura ('letto', 'non_letto').
        data_firma (datetime): Data/ora della firma (opzionale).
        stato_firma (str): Stato firma ('firmato', 'rifiutato', 'in_attesa').
        commento_firma (str): Commento alla firma (opzionale).
        ip_lettura (str): IP dell'ultima lettura.
        ip_firma (str): IP della firma.
    """
    
    def __init__(self, documento_id, documento_titolo, utente_id, utente_nome, utente_email,
                 data_invio, inviato_da, esito_invio, data_lettura=None, stato_lettura='non_letto',
                 data_firma=None, stato_firma='in_attesa', commento_firma=None,
                 ip_lettura=None, ip_firma=None):
        self.documento_id = documento_id
        self.documento_titolo = documento_titolo
        self.utente_id = utente_id
        self.utente_nome = utente_nome
        self.utente_email = utente_email
        self.data_invio = data_invio
        self.inviato_da = inviato_da
        self.esito_invio = esito_invio
        self.data_lettura = data_lettura
        self.stato_lettura = stato_lettura
        self.data_firma = data_firma
        self.stato_firma = stato_firma
        self.commento_firma = commento_firma
        self.ip_lettura = ip_lettura
        self.ip_firma = ip_firma
    
    @property
    def data_invio_formatted(self):
        """Formatta la data di invio."""
        return self.data_invio.strftime('%d/%m/%Y %H:%M') if self.data_invio else 'N/A'
    
    @property
    def data_lettura_formatted(self):
        """Formatta la data di lettura."""
        return self.data_lettura.strftime('%d/%m/%Y %H:%M') if self.data_lettura else 'N/A'
    
    @property
    def data_firma_formatted(self):
        """Formatta la data di firma."""
        return self.data_firma.strftime('%d/%m/%Y %H:%M') if self.data_firma else 'N/A'
    
    @property
    def stato_lettura_badge_class(self):
        """Classe CSS per il badge dello stato lettura."""
        return 'bg-success' if self.stato_lettura == 'letto' else 'bg-secondary'
    
    @property
    def stato_lettura_display(self):
        """Testo dello stato lettura per la visualizzazione."""
        return '✅ Letto' if self.stato_lettura == 'letto' else '❌ Non letto'
    
    @property
    def stato_firma_badge_class(self):
        """Classe CSS per il badge dello stato firma."""
        if self.stato_firma == 'firmato':
            return 'bg-success'
        elif self.stato_firma == 'rifiutato':
            return 'bg-danger'
        else:
            return 'bg-warning'
    
    @property
    def stato_firma_display(self):
        """Testo dello stato firma per la visualizzazione."""
        stati = {
            'firmato': '✅ Firmato',
            'rifiutato': '❌ Rifiutato',
            'in_attesa': '⏳ In Attesa'
        }
        return stati.get(self.stato_firma, self.stato_firma)
    
    @property
    def esito_invio_badge_class(self):
        """Classe CSS per il badge dell'esito invio."""
        return 'bg-success' if self.esito_invio == 'successo' else 'bg-danger'
    
    @property
    def esito_invio_display(self):
        """Testo dell'esito invio per la visualizzazione."""
        return '✅ Successo' if self.esito_invio == 'successo' else '❌ Errore'
    
    @property
    def is_completo(self):
        """Verifica se il processo è completo (letto e firmato)."""
        return self.stato_lettura == 'letto' and self.stato_firma == 'firmato'
    
    @property
    def is_in_attesa(self):
        """Verifica se è in attesa di lettura o firma."""
        return self.stato_lettura == 'non_letto' or self.stato_firma == 'in_attesa'
    
    @property
    def is_rifiutato(self):
        """Verifica se è stato rifiutato."""
        return self.stato_firma == 'rifiutato'
    
    @property
    def progresso_percentuale(self):
        """Calcola la percentuale di completamento."""
        progresso = 0
        if self.stato_lettura == 'letto':
            progresso += 50
        if self.stato_firma == 'firmato':
            progresso += 50
        elif self.stato_firma == 'rifiutato':
            progresso += 50  # Considera il rifiuto come completamento
        return progresso
    
    @property
    def progresso_badge_class(self):
        """Classe CSS per il badge del progresso."""
        if self.progresso_percentuale == 100:
            return 'bg-success'
        elif self.progresso_percentuale >= 50:
            return 'bg-warning'
        else:
            return 'bg-secondary'
    
    @property
    def progresso_display(self):
        """Testo del progresso per la visualizzazione."""
        if self.progresso_percentuale == 100:
            return '✅ Completato'
        elif self.progresso_percentuale >= 50:
            return '🔄 In Corso'
        else:
            return '⏳ In Attesa'


# === MODELLI SICUREZZA E AUDIT ===

class SecurityAuditLog(db.Model):
    """
    Modello per il log di audit delle azioni degli utenti (Sistema sicurezza).
    
    Attributi:
        id (int): ID primario.
        ts (datetime): Timestamp dell'azione.
        user_id (int): ID dell'utente (FK).
        ip (str): Indirizzo IP dell'utente.
        action (str): Azione eseguita (endpoint + metodo).
        object_type (str): Tipo di oggetto interessato.
        object_id (int): ID dell'oggetto interessato.
        meta (dict): Metadati aggiuntivi in formato JSON.
        user_agent (str): User agent del browser.
    """
    __tablename__ = 'security_audit_log'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    ts = db.Column(db.DateTime(timezone=True), default=datetime.utcnow, nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True, index=True)
    ip = db.Column(db.String(45), nullable=False)
    action = db.Column(db.String(100), nullable=False)
    object_type = db.Column(db.String(50), nullable=True)
    object_id = db.Column(db.Integer, nullable=True)
    meta = db.Column(db.JSON, nullable=True)
    user_agent = db.Column(db.String(255), nullable=True)
    
    # Relazioni
    user = db.relationship('User', backref='security_audit_logs')
    
    def __repr__(self):
        return f'<SecurityAuditLog {self.id}: {self.action} by {self.user_id}>'


class SecurityAlert(db.Model):
    """
    Modello per gli alert di sicurezza.
    
    Attributi:
        id (int): ID primario.
        ts (datetime): Timestamp dell'alert.
        user_id (int): ID dell'utente coinvolto (FK).
        rule_id (str): ID della regola che ha generato l'alert.
        severity (SeverityLevel): Livello di severità.
        details (str): Dettagli dell'alert.
        status (AlertStatus): Stato dell'alert.
    """
    __tablename__ = 'security_alert'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    ts = db.Column(db.DateTime(timezone=True), default=datetime.utcnow, nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    rule_id = db.Column(db.String(50), nullable=False)
    severity = db.Column(db.Enum(SeverityLevel), nullable=False, index=True)
    details = db.Column(db.Text, nullable=False)
    status = db.Column(db.Enum(AlertStatus), default=AlertStatus.OPEN, nullable=False, index=True)
    
    # Relazioni
    user = db.relationship('User', backref='security_alerts')
    
    def __repr__(self):
        return f'<SecurityAlert {self.id}: {self.rule_id} - {self.severity.value}>'


class FileHash(db.Model):
    """
    Modello per gli hash dei file.
    
    Attributi:
        file_id (int): ID del file (FK, PK).
        algo (str): Algoritmo di hash utilizzato.
        value (str): Valore dell'hash.
        created_at (datetime): Data di creazione dell'hash.
    """
    __tablename__ = 'file_hash'
    
    file_id = db.Column(db.Integer, db.ForeignKey('documents.id'), primary_key=True)
    algo = db.Column(db.String(10), nullable=False)
    value = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    
    # Relazioni
    file = db.relationship('Document', backref='hashes')
    
    def __repr__(self):
        return f'<FileHash {self.file_id}: {self.algo}>'


class AntivirusScan(db.Model):
    """
    Modello per i risultati delle scansioni antivirus.
    
    Attributi:
        id (int): ID primario.
        file_id (int): ID del file scansionato (FK).
        engine (str): Nome del motore antivirus.
        signature (str): Versione signature database.
        verdict (AntivirusVerdict): Verdetto della scansione.
        ts (datetime): Timestamp della scansione.
    """
    __tablename__ = 'antivirus_scan'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    file_id = db.Column(db.Integer, db.ForeignKey('documents.id'), nullable=False, index=True)
    engine = db.Column(db.String(50), nullable=False)
    signature = db.Column(db.String(100), nullable=False)
    verdict = db.Column(db.Enum(AntivirusVerdict), nullable=False)
    ts = db.Column(db.DateTime(timezone=True), default=datetime.utcnow, nullable=False, index=True)
    
    # Relazioni
    file = db.relationship('Document', backref='antivirus_scans')
    
    def __repr__(self):
        return f'<AntivirusScan {self.id}: {self.file_id} - {self.verdict.value}>'


class AccessRequest(db.Model):
    """
    Modello per le richieste di accesso ai file.
    
    Attributi:
        id (int): ID primario.
        file_id (int): ID del documento richiesto (FK).
        requested_by (int): ID dell'utente richiedente (FK).
        owner_id (int): ID del proprietario del documento (FK, nullable).
        reason (str): Motivo della richiesta (nullable).
        status (AccessRequestStatus): Stato della richiesta.
        decision_reason (str): Motivo della decisione (nullable).
        created_at (datetime): Data creazione.
        updated_at (datetime): Data ultimo aggiornamento.
        decided_at (datetime): Data decisione (nullable).
        expires_at (datetime): Data scadenza accesso (nullable).
        approver_id (int): ID dell'admin che ha deciso (nullable).
    """
    __tablename__ = 'access_requests'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    
    # Campi principali
    file_id = db.Column(db.Integer, db.ForeignKey('documents.id'), nullable=False, index=True)
    requested_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    reason = db.Column(db.Text, nullable=True)
    status = db.Column(db.Enum(AccessRequestStatus), default=AccessRequestStatus.PENDING, nullable=False, index=True)
    decision_reason = db.Column(db.Text, nullable=True)
    
    # Timestamp
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    decided_at = db.Column(db.DateTime, nullable=True)
    expires_at = db.Column(db.DateTime, nullable=True)
    approver_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    # Campi per compatibilità con sistema esistente
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.Text, nullable=True)
    
    # Relazioni
    file = db.relationship('Document', backref='access_requests')
    requested_by_user = db.relationship('User', foreign_keys=[requested_by], backref='access_requests_made')
    owner = db.relationship('User', foreign_keys=[owner_id], backref='access_requests_received')
    approver = db.relationship('User', foreign_keys=[approver_id], backref='access_requests_approved')
    
    # Indici compositi richiesti
    __table_args__ = (
        db.Index('idx_access_requests_status_created', 'status', 'created_at'),
        db.Index('idx_access_requests_file_user', 'file_id', 'requested_by'),
    )
    
    def __repr__(self):
        """Rappresentazione stringa della richiesta di accesso."""
        return f'<AccessRequest {self.id}: {self.file_id} - {self.status.value}>'
    
    @property
    def is_pending(self):
        """Verifica se la richiesta è in attesa."""
        return self.status == AccessRequestStatus.PENDING
    
    @property
    def is_approved(self):
        """Verifica se la richiesta è stata approvata."""
        return self.status == AccessRequestStatus.APPROVED
    
    @property
    def is_denied(self):
        """Verifica se la richiesta è stata negata."""
        return self.status == AccessRequestStatus.DENIED
    
    @property
    def is_expired(self):
        """Verifica se la richiesta è scaduta."""
        return self.status == AccessRequestStatus.EXPIRED
    
    @property
    def is_active(self):
        """Verifica se l'accesso è ancora attivo (approvato e non scaduto)."""
        if not self.is_approved:
            return False
        if self.expires_at and self.expires_at < datetime.utcnow():
            return False
        return True
    
    @property
    def status_display(self):
        """Restituisce il nome visualizzabile dello stato."""
        status_map = {
            AccessRequestStatus.PENDING: "In attesa",
            AccessRequestStatus.APPROVED: "Approvata",
            AccessRequestStatus.DENIED: "Negata",
            AccessRequestStatus.EXPIRED: "Scaduta"
        }
        return status_map.get(self.status, str(self.status.value))
    
    @property
    def status_badge_class(self):
        """Restituisce la classe CSS per il badge dello stato."""
        status_map = {
            AccessRequestStatus.PENDING: "badge-warning",
            AccessRequestStatus.APPROVED: "badge-success",
            AccessRequestStatus.DENIED: "badge-danger",
            AccessRequestStatus.EXPIRED: "badge-secondary"
        }
        return status_map.get(self.status, "badge-secondary")

# === MODELLO ALERT DOWNLOAD SOSPETTI ===
class DownloadAlert(db.Model):
    """
    Modello per gli alert di download sospetti rilevati dall'AI.
    
    Attributi:
        id (int): ID primario.
        rule (str): Regola che ha generato l'alert (R1, R2, R3).
        severity (DownloadAlertSeverity): Severità dell'alert.
        user_id (int): ID dell'utente (FK, nullable).
        ip_address (str): Indirizzo IP (nullable).
        user_agent (str): User agent (nullable).
        file_id (int): ID del file (FK, nullable).
        window_from (datetime): Inizio finestra temporale.
        window_to (datetime): Fine finestra temporale.
        details (dict): Dettagli JSON con counts, esempi, note.
        status (DownloadAlertStatus): Stato dell'alert.
        created_at (datetime): Data creazione.
        resolved_at (datetime): Data risoluzione (nullable).
        resolved_by (int): ID utente che ha risolto (FK, nullable).
    """
    __tablename__ = "download_alerts"
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    rule = db.Column(db.String(10), nullable=False, index=True)  # R1, R2, R3
    severity = db.Column(db.Enum(DownloadAlertSeverity), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True, index=True)
    ip_address = db.Column(db.String(45), nullable=True, index=True)
    user_agent = db.Column(db.Text, nullable=True)
    file_id = db.Column(db.Integer, db.ForeignKey('documents.id'), nullable=True, index=True)
    window_from = db.Column(db.DateTime, nullable=False)
    window_to = db.Column(db.DateTime, nullable=False)
    details = db.Column(db.JSON, nullable=True)  # Payload con counts, esempi, note
    status = db.Column(db.Enum(DownloadAlertStatus), default=DownloadAlertStatus.NEW, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    resolved_at = db.Column(db.DateTime, nullable=True)
    resolved_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    # Relazioni
    user = db.relationship('User', foreign_keys=[user_id], backref='download_alerts')
    file = db.relationship('Document', foreign_keys=[file_id], backref='download_alerts')
    resolver = db.relationship('User', foreign_keys=[resolved_by], backref='resolved_download_alerts')
    
    # Indici compositi richiesti
    __table_args__ = (
        db.Index('idx_download_alerts_severity_status_created', 'severity', 'status', 'created_at'),
    )
    
    def __repr__(self):
        """Rappresentazione stringa dell'alert."""
        return f'<DownloadAlert {self.user.username} - {self.filename} - {self.reason}>'
    
    def to_dict(self):
        """
        Converte l'alert in dizionario per API.
        
        Returns:
            dict: Dizionario con i dati dell'alert.
        """
        return {
            'id': self.id,
            'user_id': self.user_id,
            'user_name': self.user.username if self.user else 'N/A',
            'document_id': self.document_id,
            'filename': self.filename,
            'reason': self.reason,
            'ip_address': self.ip_address,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'status': self.status.value if self.status else None,
            'severity': self.severity,
            'details': self.details,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None,
            'resolved_by': self.resolved_by_user.username if self.resolved_by_user else None
        }

# === MODELLO RICHIESTE ACCESSO (NUOVO) ===
class AccessRequestNew(db.Model):
    """
    Modello per le richieste di accesso ai documenti bloccati.
    
    Attributi:
        id (int): ID primario.
        file_id (int): ID del documento richiesto.
        requested_by (int): ID dell'utente che ha fatto la richiesta.
        owner_id (int): ID del proprietario del documento (nullable).
        reason (str): Motivo della richiesta (opzionale).
        status (AccessRequestStatus): Stato della richiesta.
        decision_reason (str): Motivo della decisione (opzionale).
        created_at (datetime): Data creazione.
        updated_at (datetime): Data ultimo aggiornamento.
        decided_at (datetime): Data decisione (nullable).
        expires_at (datetime): Data scadenza accesso (nullable).
        approver_id (int): ID dell'admin che ha deciso (nullable).
        file (Document): Relazione con il documento.
        requested_by_user (User): Relazione con l'utente richiedente.
        owner (User): Relazione con il proprietario.
        approver (User): Relazione con l'approvatore.
    """
    __tablename__ = "access_requests_new"
    
    id = db.Column(db.Integer, primary_key=True)
    file_id = db.Column(db.Integer, db.ForeignKey('documents.id'), nullable=False, index=True)
    requested_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    reason = db.Column(db.Text, nullable=True)
    status = db.Column(db.Enum(AccessRequestStatus), default=AccessRequestStatus.PENDING, nullable=False, index=True)
    decision_reason = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    decided_at = db.Column(db.DateTime, nullable=True)
    expires_at = db.Column(db.DateTime, nullable=True)
    approver_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)  # IP del client
    user_agent = db.Column(db.Text, nullable=True)  # User agent del browser
    
    # Relazioni
    file = db.relationship('Document', backref='access_requests_new')
    requested_by_user = db.relationship('User', foreign_keys=[requested_by], backref='access_requests_made')
    owner = db.relationship('User', foreign_keys=[owner_id], backref='access_requests_received')
    approver = db.relationship('User', foreign_keys=[approver_id], backref='access_requests_approved')
    
    def __repr__(self):
        """Rappresentazione stringa della richiesta."""
        return f'<AccessRequestNew {self.file_id}:{self.requested_by}:{self.status.value}>'
    
    @property
    def is_pending(self):
        """Verifica se la richiesta è in attesa."""
        return self.status == AccessRequestStatus.PENDING
    
    @property
    def is_approved(self):
        """Verifica se la richiesta è stata approvata."""
        return self.status == AccessRequestStatus.APPROVED
    
    @property
    def is_denied(self):
        """Verifica se la richiesta è stata negata."""
        return self.status == AccessRequestStatus.DENIED
    
    @property
    def is_expired(self):
        """Verifica se la richiesta è scaduta."""
        return self.status == AccessRequestStatus.EXPIRED
    
    @property
    def is_active(self):
        """Verifica se l'accesso è ancora attivo (approvato e non scaduto)."""
        if not self.is_approved or not self.expires_at:
            return False
        return datetime.utcnow() < self.expires_at
    
    @property
    def status_display(self):
        """Restituisce lo stato per visualizzazione."""
        status_map = {
            AccessRequestStatus.PENDING: "In attesa",
            AccessRequestStatus.APPROVED: "Approvata",
            AccessRequestStatus.DENIED: "Negata",
            AccessRequestStatus.EXPIRED: "Scaduta"
        }
        return status_map.get(self.status, str(self.status.value))
    
    @property
    def status_badge_class(self):
        """Restituisce la classe CSS per il badge dello stato."""
        badge_map = {
            AccessRequestStatus.PENDING: "bg-warning",
            AccessRequestStatus.APPROVED: "bg-success",
            AccessRequestStatus.DENIED: "bg-danger",
            AccessRequestStatus.EXPIRED: "bg-secondary"
        }
        return badge_map.get(self.status, "bg-secondary")

# === ENUM PER ALERT RICHIESTE ACCESSO ===
class AccessRequestAlertSeverity(enum.Enum):
    """Enum per la severità degli alert delle richieste di accesso."""
    WARNING = "warning"
    CRITICAL = "critical"

class AccessRequestAlertStatus(enum.Enum):
    """Enum per lo stato degli alert delle richieste di accesso."""
    NEW = "new"
    SEEN = "seen"
    RESOLVED = "resolved"

# === MODELLO ALERT RICHIESTE ACCESSO ===
class AccessRequestAlert(db.Model):
    """
    Modello per gli alert delle richieste di accesso anomale.
    
    Attributi:
        id (int): ID primario.
        rule (str): Regola che ha generato l'alert (R1, R2, R3, R4, R5).
        severity (AccessRequestAlertSeverity): Severità dell'alert.
        user_id (int): ID dell'utente coinvolto (nullable).
        file_id (int): ID del file coinvolto (nullable).
        ip_address (str): Indirizzo IP (nullable).
        user_agent (str): User agent (nullable).
        window_from (datetime): Inizio finestra temporale.
        window_to (datetime): Fine finestra temporale.
        details (str): Dettagli JSON dell'alert.
        status (AccessRequestAlertStatus): Stato dell'alert.
        created_at (datetime): Data creazione.
        resolved_at (datetime): Data risoluzione (nullable).
        resolved_by (int): ID admin che ha risolto (nullable).
        user (User): Relazione con l'utente.
        file (Document): Relazione con il documento.
        resolver (User): Relazione con l'admin risolutore.
    """
    __tablename__ = "access_request_alerts"
    
    id = db.Column(db.Integer, primary_key=True)
    rule = db.Column(db.String(10), nullable=False, index=True)
    severity = db.Column(db.Enum(AccessRequestAlertSeverity), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True, index=True)
    file_id = db.Column(db.Integer, db.ForeignKey('documents.id'), nullable=True, index=True)
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.Text, nullable=True)
    window_from = db.Column(db.DateTime, nullable=False)
    window_to = db.Column(db.DateTime, nullable=False)
    details = db.Column(db.Text, nullable=True)  # JSON string
    status = db.Column(db.Enum(AccessRequestAlertStatus), default=AccessRequestAlertStatus.NEW, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    resolved_at = db.Column(db.DateTime, nullable=True)
    resolved_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    # Relazioni
    user = db.relationship('User', foreign_keys=[user_id], backref='access_request_alerts')
    file = db.relationship('Document', backref='access_request_alerts')
    resolver = db.relationship('User', foreign_keys=[resolved_by], backref='access_request_alerts_resolved')
    
    def __repr__(self):
        """Rappresentazione stringa dell'alert."""
        return f'<AccessRequestAlert {self.rule}:{self.severity.value}:{self.status.value}>'
    
    @property
    def is_new(self):
        """Verifica se l'alert è nuovo."""
        return self.status == AccessRequestAlertStatus.NEW
    
    @property
    def is_critical(self):
        """Verifica se l'alert è critico."""
        return self.severity == AccessRequestAlertSeverity.CRITICAL
    
    @property
    def is_warning(self):
        """Verifica se l'alert è un warning."""
        return self.severity == AccessRequestAlertSeverity.WARNING
    
    @property
    def severity_display(self):
        """Restituisce la severità per visualizzazione."""
        severity_map = {
            AccessRequestAlertSeverity.WARNING: "Warning",
            AccessRequestAlertSeverity.CRITICAL: "Critical"
        }
        return severity_map.get(self.severity, str(self.severity.value))
    
    @property
    def severity_badge_class(self):
        """Restituisce la classe CSS per il badge della severità."""
        badge_map = {
            AccessRequestAlertSeverity.WARNING: "bg-warning",
            AccessRequestAlertSeverity.CRITICAL: "bg-danger"
        }
        return badge_map.get(self.severity, "bg-secondary")
    
    @property
    def status_display(self):
        """Restituisce lo stato per visualizzazione."""
        status_map = {
            AccessRequestAlertSeverity.NEW: "Nuovo",
            AccessRequestAlertSeverity.SEEN: "Visto",
            AccessRequestAlertSeverity.RESOLVED: "Risolto"
        }
        return status_map.get(self.status, str(self.status.value))
    
    @property
    def details_json(self):
        """Restituisce i dettagli come JSON."""
        if not self.details:
            return {}
        try:
            return json.loads(self.details)
        except:
            return {}

# === MODELLO CONCESSIONI TEMPORANEE ===
class DocumentShare(db.Model):
    """
    Modello per le concessioni temporanee di accesso ai documenti.
    
    Attributi:
        id (int): ID primario.
        file_id (int): ID del documento (FK).
        user_id (int): ID dell'utente che ha ricevuto l'accesso (FK).
        granted_by (int): ID dell'admin che ha concesso l'accesso (FK).
        granted_at (datetime): Data concessione.
        expires_at (datetime): Data scadenza.
        scope (str): Ambito dell'accesso (default 'download').
        notes (str): Note aggiuntive (nullable).
        file (Document): Relazione con il documento.
        user (User): Relazione con l'utente.
        granted_by_user (User): Relazione con l'admin.
    """
    __tablename__ = "document_shares"
    
    id = db.Column(db.Integer, primary_key=True)
    file_id = db.Column(db.Integer, db.ForeignKey('documents.id'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    granted_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    granted_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False, index=True)
    scope = db.Column(db.String(50), default='download', nullable=False)
    notes = db.Column(db.Text, nullable=True)
    
    # Relazioni
    file = db.relationship('Document', backref='document_shares')
    user = db.relationship('User', foreign_keys=[user_id], backref='document_shares_received')
    granted_by_user = db.relationship('User', foreign_keys=[granted_by], backref='document_shares_granted')
    
    # Indici compositi richiesti
    __table_args__ = (
        db.Index('idx_document_shares_file_user', 'file_id', 'user_id'),
        db.Index('idx_document_shares_expires', 'expires_at'),
    )
    
    def __repr__(self):
        """Rappresentazione stringa della concessione."""
        return f'<DocumentShare {self.file_id}:{self.user_id}:{self.scope}>'
    
    @property
    def is_active(self):
        """Verifica se la concessione è ancora attiva."""
        return datetime.utcnow() < self.expires_at
    
    @property
    def is_expired(self):
        """Verifica se la concessione è scaduta."""
        return datetime.utcnow() >= self.expires_at
    
    @property
    def time_remaining(self):
        """Restituisce il tempo rimanente in ore."""
        if self.is_expired:
            return 0
        delta = self.expires_at - datetime.utcnow()
        return max(0, delta.total_seconds() / 3600)
    
    @property
    def time_remaining_display(self):
        """Restituisce il tempo rimanente formattato."""
        hours = self.time_remaining
        if hours < 1:
            return "Meno di 1 ora"
        elif hours < 24:
            return f"{int(hours)} ore"
        else:
            days = hours / 24
            return f"{int(days)} giorni"


# === MODELLI MANUS CORE ===

class ManusManualLink(db.Model):
    """
    Modello per il collegamento tra documenti QMS e manuali Manus.
    
    Attributi:
        id (int): ID primario.
        azienda_id (int): ID dell'azienda (FK).
        documento_id (int): ID del documento QMS (FK).
        manus_manual_id (str): ID del manuale in Manus.
        manus_version (str): Versione del manuale Manus.
        last_sync_at (datetime): Data ultimo sync.
    """
    __tablename__ = "manus_manual_link"
    
    id = db.Column(db.Integer, primary_key=True)
    azienda_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False)
    documento_id = db.Column(db.Integer, db.ForeignKey("documents.id"), nullable=False)
    manus_manual_id = db.Column(db.String(64), nullable=False, index=True)
    manus_version = db.Column(db.String(64), nullable=False)
    last_sync_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Relazioni
    azienda = db.relationship('Company', backref='manus_manual_links')
    documento = db.relationship('Document', backref='manus_manual_links')
    
    def __repr__(self):
        return f'<ManusManualLink {self.id}: {self.manus_manual_id} -> {self.documento_id}>'


class ManusCourseLink(db.Model):
    """
    Modello per il collegamento tra requisiti formativi e corsi Manus.
    
    Attributi:
        id (int): ID primario.
        azienda_id (int): ID dell'azienda (FK).
        requisito_id (int): ID del requisito formativo (FK).
        manus_course_id (str): ID del corso in Manus.
        last_sync_at (datetime): Data ultimo sync.
    """
    __tablename__ = "manus_course_link"
    
    id = db.Column(db.Integer, primary_key=True)
    azienda_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False)
    requisito_id = db.Column(db.Integer, db.ForeignKey("documents.id"), nullable=False)  # Usa documents come requisiti
    manus_course_id = db.Column(db.String(64), nullable=False, index=True)
    last_sync_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Relazioni
    azienda = db.relationship('Company', backref='manus_course_links')
    requisito = db.relationship('Document', backref='manus_course_links')
    
    def __repr__(self):
        return f'<ManusCourseLink {self.id}: {self.manus_course_id} -> {self.requisito_id}>'


class TrainingCompletionManus(db.Model):
    """
    Modello per i completamenti di formazione da Manus.
    
    Attributi:
        id (int): ID primario.
        user_id (int): ID dell'utente (FK).
        requisito_id (int): ID del requisito formativo (FK).
        manus_course_id (str): ID del corso Manus.
        completed_at (datetime): Data completamento.
        source (str): Fonte del completamento (default 'manus').
    """
    __tablename__ = "training_completion_manus"
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    requisito_id = db.Column(db.Integer, db.ForeignKey("documents.id"), nullable=False)
    manus_course_id = db.Column(db.String(64), nullable=False)
    completed_at = db.Column(db.DateTime, nullable=False)
    source = db.Column(db.String(16), default="manus", nullable=False)
    
    # Relazioni
    user = db.relationship('User', backref='training_completions_manus')
    requisito = db.relationship('Document', backref='training_completions_manus')
    
    # Vincolo unico per evitare duplicati
    __table_args__ = (db.UniqueConstraint("user_id", "requisito_id", name="uq_user_req_manus"),)
    
    def __repr__(self):
        return f'<TrainingCompletionManus {self.id}: {self.user_id} -> {self.requisito_id}>'


class ManusUserMapping(db.Model):
    """
    Modello per il mapping tra utenti Manus e utenti SYNTHIA.
    
    Attributi:
        id (int): ID primario.
        manus_user_id (str): ID utente in Manus.
        email (str): Email utente in Manus.
        syn_user_id (int): ID utente in SYNTHIA (FK).
        active (bool): Se il mapping è attivo.
        created_at (datetime): Data creazione mapping.
        updated_at (datetime): Data ultimo aggiornamento.
    """
    __tablename__ = "manus_user_mapping"
    
    id = db.Column(db.Integer, primary_key=True)
    manus_user_id = db.Column(db.String(64), unique=True, index=True, nullable=False)
    email = db.Column(db.String(255), index=True, nullable=True)
    syn_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relazioni
    syn_user = db.relationship('User', backref='manus_mappings')
    
    def __repr__(self):
        return f'<ManusUserMapping {self.id}: {self.manus_user_id} -> {self.syn_user_id}>'


class TrainingCoverageReport(db.Model):
    """
    Modello per i report di copertura formazione.
    
    Attributi:
        id (int): ID primario.
        azienda_id (int): ID dell'azienda.
        user_id (int): ID dell'utente (FK).
        requisito_id (int): ID del requisito formativo (FK).
        status (str): Status copertura ('completo', 'parziale', 'mancante').
        source (str): Fonte dati ('manus', 'manual', 'import').
        last_seen_at (datetime): Data ultimo aggiornamento.
    """
    __tablename__ = "training_coverage_report"
    
    id = db.Column(db.Integer, primary_key=True)
    azienda_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    requisito_id = db.Column(db.Integer, db.ForeignKey("documents.id"), nullable=False)
    status = db.Column(db.String(16), nullable=False)  # 'completo','parziale','mancante'
    source = db.Column(db.String(16), default="manus", nullable=False)
    last_seen_at = db.Column(db.DateTime, nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relazioni
    azienda = db.relationship('Company', backref='training_coverage_reports')
    user = db.relationship('User', backref='training_coverage_reports')
    requisito = db.relationship('Document', backref='training_coverage_reports')
    
    # Vincoli unici
    __table_args__ = (
        db.UniqueConstraint("user_id", "requisito_id", name="uq_cov_user_req"),
    )
    
    def __repr__(self):
        return f'<TrainingCoverageReport {self.id}: {self.user_id} -> {self.requisito_id} ({self.status})>'


