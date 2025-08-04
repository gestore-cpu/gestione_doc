# company_routes.py

from flask import Blueprint, render_template, request, redirect, url_for, flash
from extensions import db
from models import Company, Department

company_bp = Blueprint('company', __name__, url_prefix='/company')

# LIST: tutte le aziende
@company_bp.route('/', methods=['GET'])
def list_companies():
    companies = Company.query.order_by(Company.name).all()
    return render_template('company/list.html', companies=companies)

# CREATE: form di creazione e salvataggio nuova azienda
@company_bp.route('/create', methods=['GET', 'POST'])
def create_company():
    if request.method == 'POST':
        name = request.form.get('name').strip()
        description = request.form.get('description', '').strip()

        # Controllo se già esiste un'azienda con lo stesso nome
        existing = Company.query.filter_by(name=name).first()
        if existing:
            flash(f"L'azienda “{name}” esiste già.", 'warning')
            return redirect(url_for('company.create_company'))

        new_company = Company(name=name, description=description)
        db.session.add(new_company)
        db.session.commit()
        flash(f"Azienda “{name}” creata con successo.", 'success')
        return redirect(url_for('company.list_companies'))

    return render_template('company/create.html')

# EDIT: form di modifica azienda
@company_bp.route('/edit/<int:company_id>', methods=['GET', 'POST'])
def edit_company(company_id):
    company = Company.query.get_or_404(company_id)
    if request.method == 'POST':
        new_name = request.form.get('name').strip()
        new_description = request.form.get('description', '').strip()

        # Se cambia nome, verifico unicità
        if new_name != company.name:
            duplicate = Company.query.filter_by(name=new_name).first()
            if duplicate:
                flash(f"L'azienda “{new_name}” esiste già.", 'warning')
                return redirect(url_for('company.edit_company', company_id=company.id))

        company.name = new_name
        company.description = new_description
        db.session.commit()
        flash(f"Azienda aggiornata con successo.", 'success')
        return redirect(url_for('company.list_companies'))

    return render_template('company/edit.html', company=company)

# DELETE: elimina un'azienda
@company_bp.route('/delete/<int:company_id>', methods=['POST'])
def delete_company(company_id):
    company = Company.query.get_or_404(company_id)

    # Controllo: se esistono reparti o utenti collegati, potresti voler impedire l'eliminazione
    if company.departments or company.users:
        flash("Impossibile eliminare l'azienda: esistono reparti o utenti ad essa collegati.", 'danger')
        return redirect(url_for('company.list_companies'))

    db.session.delete(company)
    db.session.commit()
    flash(f"Azienda eliminata con successo.", 'success')
    return redirect(url_for('company.list_companies'))
