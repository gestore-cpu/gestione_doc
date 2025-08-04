from app.models.ai_analysis import DocumentoAnalizzato
from app.models import User
from app.services.permissions import filter_documents_for_user
from sqlalchemy.orm import Session

def verifica_visibilita_documenti(db: Session):
    utenti = db.query(User).all()
    docs = db.query(DocumentoAnalizzato).all()
    doc_id_to_users = {doc.id: set() for doc in docs}
    orfani = set(doc.id for doc in docs)
    non_assegnabili = []
    accessi_illegittimi = []

    for user in utenti:
        visibili = filter_documents_for_user(db, user)
        for doc in visibili:
            doc_id_to_users[doc.id].add(user.email)
            if doc.id in orfani:
                orfani.remove(doc.id)

    for doc in docs:
        # Documenti non assegnabili (mancano metadata)
        if not doc.azienda or not doc.reparto:
            non_assegnabili.append(doc)
        # Documenti orfani (nessun utente può vederli)
        if not doc_id_to_users[doc.id]:
            print(f"[ORFANO] {doc.filename} (id={doc.id}) non è accessibile da nessun utente")

    # Accessi illegittimi: utente che vede un doc che non dovrebbe
    for user in utenti:
        user_aziende = [a.nome for a in getattr(user, 'aziende', [])]
        user_reparti = [r.nome for r in getattr(user, 'reparti', [])]
        for doc in docs:
            # Se l'utente vede il doc ma non dovrebbe
            if doc.id in doc_id_to_users and user.email in doc_id_to_users[doc.id]:
                if doc.azienda not in user_aziende or not set(doc.reparto or []).intersection(user_reparti):
                    accessi_illegittimi.append((user.email, doc.filename))
                    print(f"[ILLEGITTIMO] {user.email} vede {doc.filename} senza permesso")

    for doc in non_assegnabili:
        print(f"[NON ASSEGNABILE] {doc.filename} (id={doc.id}) manca di metadata validi")

    print(f"Totale documenti orfani: {len(orfani)}")
    print(f"Totale documenti non assegnabili: {len(non_assegnabili)}")
    print(f"Totale accessi illegittimi: {len(accessi_illegittimi)}") 