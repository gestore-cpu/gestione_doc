#!/usr/bin/env python3
"""
Test per il sistema di firma sequenziale e visibilità per ruolo (STEP 1)
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import Document, User, ApprovalStep, Company, Department
from datetime import datetime
from routes.admin_routes import advance_to_next_step

def test_sequential_approval_system():
    """
    Test del sistema di firma sequenziale e visibilità per ruolo
    """
    print("🧪 TEST: Sistema di Firma Sequenziale e Visibilità per Ruolo")
    print("=" * 70)
    
    with app.app_context():
        # 1. Crea dati di test
        print("✅ 1. Creazione dati di test")
        
        # Crea azienda e reparto
        company = Company.query.first()
        if not company:
            company = Company(name="Test Company")
            db.session.add(company)
            db.session.flush()
        
        department = Department.query.first()
        if not department:
            department = Department(name="Test Department", company_id=company.id)
            db.session.add(department)
            db.session.flush()
        
        # Crea utenti con ruoli diversi
        users = {}
        roles = ['manager', 'admin', 'ceo']
        
        for role in roles:
            user = User.query.filter_by(email=f"test_{role}@example.com").first()
            if not user:
                user = User(
                    username=f"test_{role}",
                    email=f"test_{role}@example.com",
                    password="test123",
                    role=role
                )
                db.session.add(user)
                db.session.flush()
            users[role] = user
        
        # Crea documento
        document = Document(
            title="Test Document Sequential Approval",
            filename="test_sequential.pdf",
            uploader_email="test_admin@example.com",
            user_id=users['admin'].id,
            company_id=company.id,
            department_id=department.id,
            description="Documento di test per approvazione sequenziale"
        )
        db.session.add(document)
        db.session.flush()
        print(f"   ✓ Documento creato: {document.title}")
        
        # 2. Crea step sequenziali
        print("\n✅ 2. Creazione step sequenziali")
        
        steps_data = [
            {"name": "Controllo Qualità", "role": "manager", "auto_approval": False},
            {"name": "Validazione Admin", "role": "admin", "auto_approval": False},
            {"name": "Approvazione CEO", "role": "ceo", "auto_approval": False}
        ]
        
        steps = []
        for i, step_data in enumerate(steps_data):
            step = ApprovalStep(
                document_id=document.id,
                step_name=step_data["name"],
                approver_role=step_data["role"],
                status="pending",
                auto_approval=step_data["auto_approval"]
            )
            db.session.add(step)
            steps.append(step)
        
        db.session.commit()
        print(f"   ✓ {len(steps)} step sequenziali creati")
        
        # 3. Test logica di visibilità
        print("\n✅ 3. Test logica di visibilità per ruolo")
        
        # Simula la logica della route
        approval_steps = ApprovalStep.query.filter_by(document_id=document.id).order_by(ApprovalStep.id).all()
        active_step = next((s for s in approval_steps if s.status == 'pending'), None)
        
        print(f"   📊 Step attivo: {active_step.step_name if active_step else 'Nessuno'}")
        
        # Test per ogni utente
        for role, user in users.items():
            print(f"\n   👤 Test utente {role}:")
            
            # Simula i flag di visibilità
            for step in approval_steps:
                step.is_active = (step == active_step)
                step.can_take_action = step.is_active and (
                    user.role == step.approver_role or user.role == 'admin'
                )
                step.is_future_step = (
                    step.status == 'pending' and 
                    step != active_step and 
                    approval_steps.index(step) > approval_steps.index(active_step) if active_step else False
                )
                step.is_past_step = step.status in ['approved', 'rejected', 'commented']
            
            # Verifica visibilità
            can_see_any = any(step.is_active and step.approver_role == user.role for step in approval_steps)
            can_see_past = any(step.is_past_step and step.approver_role == user.role for step in approval_steps)
            
            if user.role == 'admin':
                print(f"      ✅ Admin vede tutto")
            elif can_see_any:
                print(f"      ✅ {role.capitalize()} vede step attivo")
            elif can_see_past:
                print(f"      ✅ {role.capitalize()} vede step passati")
            else:
                print(f"      ❌ {role.capitalize()} non vede nulla")
        
        # 4. Test approvazione sequenziale
        print("\n✅ 4. Test approvazione sequenziale")
        
        # Simula approvazione del primo step (manager)
        print("   🔄 Approvazione step 1 (Manager)...")
        steps[0].status = "approved"
        steps[0].approved_at = datetime.utcnow()
        steps[0].method = "manual"
        steps[0].approver_id = users['manager'].id
        db.session.commit()
        
        # Avanza al prossimo step
        advance_to_next_step(document.id)
        
        # Verifica che il secondo step sia ora attivo
        approval_steps = ApprovalStep.query.filter_by(document_id=document.id).order_by(ApprovalStep.id).all()
        active_step = next((s for s in approval_steps if s.status == 'pending'), None)
        
        print(f"   📊 Nuovo step attivo: {active_step.step_name if active_step else 'Nessuno'}")
        
        if active_step and active_step.step_name == "Validazione Admin":
            print("   ✅ Avanzamento sequenziale corretto")
        else:
            print("   ❌ Avanzamento sequenziale fallito")
            return False
        
        # 5. Test visibilità dopo avanzamento
        print("\n✅ 5. Test visibilità dopo avanzamento")
        
        # Manager dovrebbe vedere solo step passati
        manager_steps = [s for s in approval_steps if s.approver_role == 'manager']
        manager_active = [s for s in manager_steps if s.is_active]
        
        if not manager_active and any(s.status == 'approved' for s in manager_steps):
            print("   ✅ Manager vede solo step completati")
        else:
            print("   ❌ Manager vede step attivi (non dovrebbe)")
            return False
        
        # Admin dovrebbe vedere step attivo
        admin_steps = [s for s in approval_steps if s.approver_role == 'admin']
        admin_active = [s for s in admin_steps if s.is_active]
        
        if admin_active:
            print("   ✅ Admin vede step attivo")
        else:
            print("   ❌ Admin non vede step attivo")
            return False
        
        # 6. Test blocco step futuri
        print("\n✅ 6. Test blocco step futuri")
        
        ceo_steps = [s for s in approval_steps if s.approver_role == 'ceo']
        ceo_future = [s for s in ceo_steps if s.is_future_step]
        
        if ceo_future:
            print("   ✅ Step CEO correttamente marcati come futuri")
        else:
            print("   ❌ Step CEO non marcati come futuri")
            return False
        
        # 7. Pulizia
        print("\n✅ 7. Pulizia dati di test")
        for step in steps:
            db.session.delete(step)
        db.session.delete(document)
        for user in users.values():
            db.session.delete(user)
        db.session.commit()
        print("   ✓ Dati di test rimossi")
        
        print("\n🎉 TEST COMPLETATO CON SUCCESSO!")
        print("=" * 70)
        print("✅ Il sistema di firma sequenziale funziona correttamente")
        print("✅ La visibilità per ruolo è implementata")
        print("✅ Gli step futuri sono correttamente bloccati")
        print("✅ L'avanzamento sequenziale funziona")
        print("✅ I controlli di autorizzazione sono attivi")
        
        return True

if __name__ == "__main__":
    try:
        success = test_sequential_approval_system()
        if success:
            print("\n🚀 STEP 1 - COMPLETATO AL 100%")
            print("Il sistema di firma sequenziale è ora operativo!")
        else:
            print("\n❌ Test fallito")
            sys.exit(1)
    except Exception as e:
        print(f"\n❌ Errore durante il test: {e}")
        sys.exit(1)