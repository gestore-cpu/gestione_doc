from flask import Blueprint, render_template, abort
from flask_login import login_required, current_user
from models import Document

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/dashboard')
@login_required
def dashboard():
    documenti = Document.query.filter_by(user_id=current_user.id).all()
    return render_template('dashboard.html', documenti=documenti)

# Route rimossa per evitare conflitti con ceo_bp
# @dashboard_bp.get("/dashboard/obeya")
# @login_required
# def obeya_ceo_dashboard():
#     if current_user.role != 'ceo':
#         abort(403)
#     return render_template("obeya_dashboard.html")
