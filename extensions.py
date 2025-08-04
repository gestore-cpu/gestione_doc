from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_mail import Mail
from flask_wtf import CSRFProtect  # Importa CSRFProtect

# Istanza delle estensioni
db = SQLAlchemy()
bcrypt = Bcrypt()
mail = Mail()
csrf = CSRFProtect()  # Aggiungi l’istanza CSRFProtect
