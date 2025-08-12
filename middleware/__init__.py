"""
Middleware package per il sistema di gestione documenti.
Contiene middleware per audit, sicurezza e monitoraggio.
"""

from .audit_middleware import AuditMiddleware

__all__ = ['AuditMiddleware']
