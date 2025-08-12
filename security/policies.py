"""
Sistema di policy granulari per RBAC e multi-step approvals.
Gestisce regole di approvazione basate su ruolo, rischio e importo.
"""

import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class RiskLevel(Enum):
    """Livelli di rischio."""
    LOW = "low"      # 0-39
    MEDIUM = "medium"  # 40-69
    HIGH = "high"    # 70-100

class ApprovalStatus(Enum):
    """Stati di approvazione."""
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    ESCALATED = "escalated"
    REQUIRES_SECOND_APPROVAL = "requires_second_approval"

@dataclass
class ApprovalRequest:
    """Dati di una richiesta di approvazione."""
    id: int
    user_id: int
    user_email: str
    user_role: str
    risk_score: int
    amount: float
    request_type: str
    description: str
    created_at: datetime
    status: ApprovalStatus = ApprovalStatus.PENDING
    first_approver_id: Optional[int] = None
    second_approver_id: Optional[int] = None
    first_approval_at: Optional[datetime] = None
    second_approval_at: Optional[datetime] = None
    escalation_reason: Optional[str] = None

class ApprovalPolicy:
    """Gestisce policy di approvazione."""
    
    def __init__(self):
        # Configurazione policy
        self.auto_approve_thresholds = {
            'risk_max': 39,
            'amount_max': 300.0
        }
        
        self.two_man_rule_thresholds = {
            'risk_min': 70,
            'amount_min': 5000.0
        }
        
        self.manager_override_roles = ['CISO', 'CEO', 'CFO']
        
        self.approver_roles = {
            'low_risk': ['TeamLead', 'SecurityAnalyst', 'Admin'],
            'medium_risk': ['SecurityLead', 'TeamLead', 'Admin'],
            'high_risk': ['SecurityLead', 'FinanceLead', 'CISO'],
            'two_man_rule': ['SecurityLead', 'FinanceLead', 'CISO', 'CEO']
        }
    
    def get_risk_level(self, risk_score: int) -> RiskLevel:
        """Determina il livello di rischio."""
        if risk_score <= 39:
            return RiskLevel.LOW
        elif risk_score <= 69:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.HIGH
    
    def can_auto_approve(self, request: ApprovalRequest) -> bool:
        """
        Controlla se una richiesta può essere auto-approvata.
        
        Args:
            request (ApprovalRequest): Richiesta da valutare
            
        Returns:
            bool: True se può essere auto-approvata
        """
        return (request.risk_score <= self.auto_approve_thresholds['risk_max'] and 
                request.amount <= self.auto_approve_thresholds['amount_max'])
    
    def requires_two_man_rule(self, request: ApprovalRequest) -> bool:
        """
        Controlla se una richiesta richiede la regola dei due uomini.
        
        Args:
            request (ApprovalRequest): Richiesta da valutare
            
        Returns:
            bool: True se richiede due approvazioni
        """
        return (request.risk_score >= self.two_man_rule_thresholds['risk_min'] or 
                request.amount >= self.two_man_rule_thresholds['amount_min'])
    
    def can_approve(self, user_role: str, request: ApprovalRequest) -> Tuple[bool, str]:
        """
        Controlla se un utente può approvare una richiesta.
        
        Args:
            user_role (str): Ruolo dell'utente
            request (ApprovalRequest): Richiesta da approvare
            
        Returns:
            Tuple[bool, str]: (può_approvare, motivo)
        """
        # Manager override
        if user_role in self.manager_override_roles:
            return True, "Manager override"
        
        # Auto-approve
        if self.can_auto_approve(request):
            return True, "Auto-approve threshold"
        
        # Due approvazioni richieste
        if self.requires_two_man_rule(request):
            if user_role in self.approver_roles['two_man_rule']:
                return True, "Two-man rule approver"
            else:
                return False, "Two-man rule requires specific roles"
        
        # Approvazione normale
        risk_level = self.get_risk_level(request.risk_score)
        if user_role in self.approver_roles[f'{risk_level.value}_risk']:
            return True, f"{risk_level.value} risk approver"
        
        return False, "Insufficient permissions"
    
    def get_required_approvers(self, request: ApprovalRequest) -> List[str]:
        """
        Ottiene i ruoli richiesti per approvare una richiesta.
        
        Args:
            request (ApprovalRequest): Richiesta da valutare
            
        Returns:
            List[str]: Lista di ruoli richiesti
        """
        if self.requires_two_man_rule(request):
            return self.approver_roles['two_man_rule']
        
        risk_level = self.get_risk_level(request.risk_score)
        return self.approver_roles[f'{risk_level.value}_risk']
    
    def should_escalate(self, request: ApprovalRequest, hours_pending: int = 4) -> bool:
        """
        Controlla se una richiesta dovrebbe essere escalata.
        
        Args:
            request (ApprovalRequest): Richiesta da valutare
            hours_pending (int): Ore di attesa per escalation
            
        Returns:
            bool: True se dovrebbe essere escalata
        """
        if request.status != ApprovalStatus.PENDING:
            return False
        
        time_pending = datetime.utcnow() - request.created_at
        return time_pending > timedelta(hours=hours_pending)

class ApprovalWorkflow:
    """Gestisce il workflow di approvazione."""
    
    def __init__(self):
        self.policy = ApprovalPolicy()
    
    def process_approval_request(self, request: ApprovalRequest) -> Dict:
        """
        Processa una nuova richiesta di approvazione.
        
        Args:
            request (ApprovalRequest): Richiesta da processare
            
        Returns:
            Dict: Risultato del processing
        """
        try:
            # Auto-approve se possibile
            if self.policy.can_auto_approve(request):
                return {
                    'status': 'auto_approved',
                    'message': 'Richiesta auto-approvata per basso rischio/importo',
                    'requires_action': False
                }
            
            # Controlla se richiede due approvazioni
            if self.policy.requires_two_man_rule(request):
                return {
                    'status': 'requires_two_approvals',
                    'message': 'Richiesta richiede due approvazioni',
                    'required_approvers': self.policy.get_required_approvers(request),
                    'requires_action': True
                }
            
            # Approvazione normale
            return {
                'status': 'pending_approval',
                'message': 'Richiesta in attesa di approvazione',
                'required_approvers': self.policy.get_required_approvers(request),
                'requires_action': True
            }
            
        except Exception as e:
            logger.error(f"❌ Errore processing richiesta {request.id}: {e}")
            return {
                'status': 'error',
                'message': f'Errore processing: {str(e)}',
                'requires_action': False
            }
    
    def record_decision(self, request: ApprovalRequest, approver_id: int, 
                       approver_role: str, decision: str, comment: str = None) -> Dict:
        """
        Registra una decisione di approvazione.
        
        Args:
            request (ApprovalRequest): Richiesta da approvare
            approver_id (int): ID dell'approver
            approver_role (str): Ruolo dell'approver
            decision (str): Decisione (approve/deny)
            comment (str): Commento opzionale
            
        Returns:
            Dict: Risultato della decisione
        """
        try:
            # Controlla se può approvare
            can_approve, reason = self.policy.can_approve(approver_role, request)
            if not can_approve:
                return {
                    'status': 'denied',
                    'message': f'Permessi insufficienti: {reason}',
                    'requires_action': False
                }
            
            # Registra prima approvazione
            if not request.first_approver_id:
                request.first_approver_id = approver_id
                request.first_approval_at = datetime.utcnow()
                
                if decision.lower() == 'deny':
                    request.status = ApprovalStatus.DENIED
                    return {
                        'status': 'denied',
                        'message': 'Richiesta negata',
                        'requires_action': False
                    }
                
                # Controlla se richiede seconda approvazione
                if self.policy.requires_two_man_rule(request):
                    request.status = ApprovalStatus.REQUIRES_SECOND_APPROVAL
                    return {
                        'status': 'requires_second_approval',
                        'message': 'Prima approvazione registrata, richiesta seconda approvazione',
                        'requires_action': True
                    }
                else:
                    request.status = ApprovalStatus.APPROVED
                    return {
                        'status': 'approved',
                        'message': 'Richiesta approvata',
                        'requires_action': False
                    }
            
            # Registra seconda approvazione (se richiesta)
            elif request.status == ApprovalStatus.REQUIRES_SECOND_APPROVAL:
                if approver_id == request.first_approver_id:
                    return {
                        'status': 'denied',
                        'message': 'Stesso approver non può fare seconda approvazione',
                        'requires_action': False
                    }
                
                request.second_approver_id = approver_id
                request.second_approval_at = datetime.utcnow()
                
                if decision.lower() == 'deny':
                    request.status = ApprovalStatus.DENIED
                    return {
                        'status': 'denied',
                        'message': 'Richiesta negata alla seconda approvazione',
                        'requires_action': False
                    }
                else:
                    request.status = ApprovalStatus.APPROVED
                    return {
                        'status': 'approved',
                        'message': 'Richiesta approvata con due approvazioni',
                        'requires_action': False
                    }
            
            else:
                return {
                    'status': 'error',
                    'message': 'Stato richiesta non valido per approvazione',
                    'requires_action': False
                }
                
        except Exception as e:
            logger.error(f"❌ Errore registrazione decisione per richiesta {request.id}: {e}")
            return {
                'status': 'error',
                'message': f'Errore registrazione: {str(e)}',
                'requires_action': False
            }
    
    def check_escalation(self, request: ApprovalRequest) -> Dict:
        """
        Controlla se una richiesta dovrebbe essere escalata.
        
        Args:
            request (ApprovalRequest): Richiesta da controllare
            
        Returns:
            Dict: Risultato controllo escalation
        """
        try:
            if self.policy.should_escalate(request):
                request.status = ApprovalStatus.ESCALATED
                request.escalation_reason = "Richiesta in attesa da più di 4 ore"
                
                return {
                    'status': 'escalated',
                    'message': 'Richiesta escalata per tempo di attesa',
                    'requires_action': True,
                    'escalation_reason': request.escalation_reason
                }
            
            return {
                'status': 'no_escalation',
                'message': 'Richiesta non richiede escalation',
                'requires_action': False
            }
            
        except Exception as e:
            logger.error(f"❌ Errore controllo escalation per richiesta {request.id}: {e}")
            return {
                'status': 'error',
                'message': f'Errore controllo escalation: {str(e)}',
                'requires_action': False
            }

# Istanza globale
approval_policy = ApprovalPolicy()
approval_workflow = ApprovalWorkflow()
