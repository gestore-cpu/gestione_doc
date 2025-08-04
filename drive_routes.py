from flask import Blueprint

drive_bp = Blueprint('drive', __name__, url_prefix='/drive')

@drive_bp.route('/')
def index():
    return "Gestione Drive"
