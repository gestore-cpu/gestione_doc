# Import di tutti i blueprint
from .auth import auth_bp
from .admin_routes import admin_bp
from .user_routes import user_bp
from .docs import docs_bp
from .dashboard_ceo import ceo_bp
from .drive_upload import drive_bp
from .documents import docs_bp as documents_bp
from .visite_mediche_routes import visite_mediche_bp
from .checklist_compliance_routes import checklist_compliance_bp
from .reminder_routes import reminder_bp
from .firme_manuali_routes import firme_manuali_bp
from .prove_evacuazione_routes import prove_evacuazione_bp
from .visite_mediche_avanzate_routes import visite_mediche_avanzate_bp
from .document_intelligence_routes import document_intelligence_bp

# Lista di tutti i blueprint per la registrazione
blueprints = [
    auth_bp,
    admin_bp,
    user_bp,
    docs_bp,
    ceo_bp,
    drive_bp,
    documents_bp,
    visite_mediche_bp,
    checklist_compliance_bp,
    reminder_bp,
    firme_manuali_bp,
    prove_evacuazione_bp,
    visite_mediche_avanzate_bp,
    document_intelligence_bp
]
