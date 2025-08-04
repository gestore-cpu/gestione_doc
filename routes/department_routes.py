from flask import Blueprint, render_template, request, redirect, url_for, flash
from extensions import db
from models import Department, Company

department_bp = Blueprint('department', __name__, url_prefix='/department')

@department_bp.route('/', methods=['GET'])
def list_departments():
    departments = Department.query.join(Company).order_by(Company.name, Department.name).all()
    return render_template('department/list.html', departments=departments)

@department_bp.route('/create', methods=['GET', 'POST'])
def create_department():
    companies = Company.query.order_by(Company.name).all()
    if request.method == 'POST':
        name = request.form.get('name').strip()
        company_id = request.form.get('company_id')
        if not company_id:
            flash("Seleziona un'azienda per il reparto.", 'warning')
            return redirect(url_for('department.create_department'))
        if Department.query.filter_by(name=name, company_id=company_id).first():
            flash("Reparto già esistente per quell'azienda.", 'warning')
            return redirect(url_for('department.create_department'))

        new_dep = Department(name=name, company_id=company_id)
        db.session.add(new_dep)
        db.session.commit()
        flash("Reparto creato con successo.", 'success')
        return redirect(url_for('department.list_departments'))
    return render_template('department/create.html', companies=companies)

@department_bp.route('/edit/<int:department_id>', methods=['GET', 'POST'])
def edit_department(department_id):
    department = Department.query.get_or_404(department_id)
    companies = Company.query.order_by(Company.name).all()
    if request.method == 'POST':
        new_name = request.form.get('name').strip()
        new_cid = request.form.get('company_id')
        if Department.query.filter_by(name=new_name, company_id=new_cid).first():
            flash("Reparto già esistente per quell'azienda.", 'warning')
            return redirect(url_for('department.edit_department', department_id=department.id))
        department.name = new_name
        department.company_id = new_cid
        db.session.commit()
        flash("Reparto aggiornato con successo.", 'success')
        return redirect(url_for('department.list_departments'))
    return render_template('department/edit.html', department=department, companies=companies)

@department_bp.route('/delete/<int:department_id>', methods=['POST'])
def delete_department(department_id):
    department = Department.query.get_or_404(department_id)
    # blocca se ci sono utenti o documenti
    if getattr(department, 'users', []) or getattr(department, 'documents', []):
        flash("Impossibile eliminare: utenti o documenti collegati.", 'danger')
        return redirect(url_for('department.list_departments'))
    db.session.delete(department)
    db.session.commit()
    flash("Reparto eliminato.", 'success')
    return redirect(url_for('department.list_departments'))
