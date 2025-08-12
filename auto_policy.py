"""
Modello per le regole AI automatiche di approvazione/negazione richieste accesso.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from extensions import db

class AutoPolicy(db.Model):
    """
    Modello per le regole AI automatiche di gestione richieste accesso.
    
    Attributes:
        id: ID univoco della regola
        name: Nome della regola
        description: Descrizione della regola
        condition: Condizione in formato JSON o linguaggio naturale
        condition_type: Tipo di condizione (json, natural_language)
        action: Azione da eseguire (approve/deny)
        priority: Priorità della regola (1=più alta)
        active: Se la regola è attiva
        created_at: Data creazione
        updated_at: Data ultimo aggiornamento
        created_by: ID admin che ha creato la regola
        approved_by: ID admin che ha approvato la regola
        approved_at: Data approvazione
    """
    
    __tablename__ = 'auto_policies'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    condition = Column(Text, nullable=False)
    condition_type = Column(String(50), nullable=False, default='json')
    action = Column(String(10), nullable=False)  # approve / deny
    priority = Column(Integer, nullable=False, default=1)
    active = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    created_by = Column(Integer, ForeignKey('users.id'), nullable=False)
    approved_by = Column(Integer, ForeignKey('users.id'), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    
    # Relazioni
    creator = relationship('User', foreign_keys=[created_by], backref='created_policies')
    approver = relationship('User', foreign_keys=[approved_by], backref='approved_policies')
    
    def __repr__(self):
        """Rappresentazione stringa del modello."""
        return f'<AutoPolicy {self.name}: {self.action}>'
    
    def to_dict(self):
        """Converte il modello in dizionario."""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'condition': self.condition,
            'condition_type': self.condition_type,
            'action': self.action,
            'priority': self.priority,
            'active': self.active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'created_by': self.created_by,
            'approved_by': self.approved_by,
            'approved_at': self.approved_at.isoformat() if self.approved_at else None,
            'creator_name': self.creator.username if self.creator else None,
            'approver_name': self.approver.username if self.approver else None
        }
    
    @classmethod
    def get_active_policies(cls):
        """Recupera tutte le regole attive ordinate per priorità."""
        return cls.query.filter_by(active=True).order_by(cls.priority.asc()).all()
    
    @classmethod
    def get_pending_policies(cls):
        """Recupera tutte le regole in attesa di approvazione."""
        return cls.query.filter_by(active=False).order_by(cls.created_at.desc()).all()
    
    def evaluate_condition(self, request_data):
        """
        Valuta se la condizione della regola è soddisfatta.
        
        Args:
            request_data: Dizionario con i dati della richiesta
            
        Returns:
            bool: True se la condizione è soddisfatta
        """
        try:
            if self.condition_type == 'json':
                return self._evaluate_json_condition(request_data)
            else:
                return self._evaluate_natural_condition(request_data)
        except Exception as e:
            print(f"Errore valutazione condizione regola {self.id}: {e}")
            return False
    
    def _evaluate_json_condition(self, request_data):
        """Valuta condizione in formato JSON."""
        import json
        
        try:
            condition_data = json.loads(self.condition)
            
            # Esempi di condizioni supportate:
            # {"field": "user_role", "operator": "equals", "value": "admin"}
            # {"field": "document_department", "operator": "equals", "value": "IT"}
            # {"field": "user_company", "operator": "equals", "value": "document_company"}
            
            field = condition_data.get('field')
            operator = condition_data.get('operator')
            value = condition_data.get('value')
            
            if not all([field, operator, value]):
                return False
            
            # Ottieni il valore del campo dalla richiesta
            request_value = request_data.get(field)
            
            if operator == 'equals':
                return request_value == value
            elif operator == 'not_equals':
                return request_value != value
            elif operator == 'contains':
                return value in str(request_value) if request_value else False
            elif operator == 'in':
                return request_value in value if isinstance(value, list) else False
            elif operator == 'not_in':
                return request_value not in value if isinstance(value, list) else False
            elif operator == 'field_equals':
                # Confronta due campi della richiesta
                other_field = value
                other_value = request_data.get(other_field)
                return request_value == other_value
            else:
                return False
                
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            print(f"Errore parsing condizione JSON regola {self.id}: {e}")
            return False
    
    def _evaluate_natural_condition(self, request_data):
        """Valuta condizione in linguaggio naturale (semplificato)."""
        # Per ora implementiamo solo alcune condizioni comuni
        condition_lower = self.condition.lower()
        
        # Condizioni predefinite
        if "admin" in condition_lower and "user_role" in condition_lower:
            return request_data.get('user_role') == 'admin'
        
        if "same company" in condition_lower or "stessa azienda" in condition_lower:
            user_company = request_data.get('user_company')
            doc_company = request_data.get('document_company')
            return user_company == doc_company
        
        if "same department" in condition_lower or "stesso reparto" in condition_lower:
            user_dept = request_data.get('user_department')
            doc_dept = request_data.get('document_department')
            return user_dept == doc_dept
        
        if "confidential" in condition_lower or "confidenziale" in condition_lower:
            doc_tags = request_data.get('document_tags', [])
            return 'confidenziale' in [tag.lower() for tag in doc_tags]
        
        if "guest" in condition_lower and "deny" in condition_lower:
            user_role = request_data.get('user_role')
            return user_role == 'guest'
        
        return False
    
    def apply_to_request(self, request_data):
        """
        Applica la regola a una richiesta di accesso.
        
        Args:
            request_data: Dizionario con i dati della richiesta
            
        Returns:
            dict: Risultato dell'applicazione della regola
        """
        if not self.active:
            return {
                'applied': False,
                'reason': 'Regola non attiva'
            }
        
        if self.evaluate_condition(request_data):
            return {
                'applied': True,
                'action': self.action,
                'policy_id': self.id,
                'policy_name': self.name,
                'reason': f'Regola automatica: {self.name}'
            }
        else:
            return {
                'applied': False,
                'reason': 'Condizione non soddisfatta'
            }
    
    def activate(self, approved_by_user_id):
        """Attiva la regola."""
        self.active = True
        self.approved_by = approved_by_user_id
        self.approved_at = datetime.utcnow()
        db.session.commit()
    
    def deactivate(self):
        """Disattiva la regola."""
        self.active = False
        self.approved_by = None
        self.approved_at = None
        db.session.commit()
    
    def toggle(self):
        """Attiva/disattiva la regola."""
        self.active = not self.active
        if self.active:
            self.approved_by = None  # Reset approver when toggling
            self.approved_at = None
        db.session.commit()
        return self.active
    
    def get_status_display(self):
        """Restituisce lo stato della regola per visualizzazione."""
        if self.active:
            return "✅ Attiva"
        else:
            return "❌ Inattiva"
    
    def get_action_display(self):
        """Restituisce l'azione della regola per visualizzazione."""
        if self.action == 'approve':
            return "✅ Approva"
        else:
            return "❌ Nega"
    
    def get_priority_display(self):
        """Restituisce la priorità per visualizzazione."""
        priority_labels = {
            1: "🔴 Critica",
            2: "🟠 Alta", 
            3: "🟡 Media",
            4: "🟢 Bassa",
            5: "⚪ Molto Bassa"
        }
        return priority_labels.get(self.priority, f"Priorità {self.priority}")
    
    def get_confidence_display(self):
        """Restituisce la confidenza per visualizzazione."""
        if self.confidence >= 90:
            return f"🟢 {self.confidence}% (Molto Alta)"
        elif self.confidence >= 80:
            return f"🟡 {self.confidence}% (Alta)"
        elif self.confidence >= 70:
            return f"🟠 {self.confidence}% (Media)"
        else:
            return f"🔴 {self.confidence}% (Bassa)"
    
    def get_condition_summary(self):
        """Restituisce un riassunto della condizione per visualizzazione."""
        try:
            import json
            condition_data = json.loads(self.condition)
            field = condition_data.get('field', '')
            operator = condition_data.get('operator', '')
            value = condition_data.get('value', '')
            
            operator_labels = {
                'equals': '=',
                'not_equals': '≠',
                'contains': 'contiene',
                'in': 'in',
                'not_in': 'not in',
                'field_equals': '='
            }
            
            op_label = operator_labels.get(operator, operator)
            
            if operator == 'field_equals':
                return f"{field} = {value}"
            else:
                return f"{field} {op_label} {value}"
                
        except (json.JSONDecodeError, KeyError):
            return self.condition[:50] + "..." if len(self.condition) > 50 else self.condition
    
    @classmethod
    def evaluate_all_policies(cls, request_data):
        """
        Valuta tutte le regole attive su una richiesta.
        
        Args:
            request_data: Dizionario con i dati della richiesta
            
        Returns:
            dict: Primo risultato applicabile o None
        """
        active_policies = cls.get_active_policies()
        
        for policy in active_policies:
            result = policy.apply_to_request(request_data)
            if result['applied']:
                return result
        
        return None 