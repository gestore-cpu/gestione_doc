from difflib import SequenceMatcher
from app.services.naming import genera_nome_file


def confronta_testi(testo1: str, testo2: str) -> float:
    """Calcola la similarità tra due testi usando SequenceMatcher.

    Args:
        testo1 (str): Primo testo da confrontare.
        testo2 (str): Secondo testo da confrontare.

    Returns:
        float: Similarità tra 0 e 1 (1 = identici).
    """
    return SequenceMatcher(None, testo1, testo2).ratio()


def crea_nuova_revisione(documento_vecc, documento_nuovo_text, db):
    """Crea una nuova revisione del documento se il testo è significativamente diverso.

    Args:
        documento_vecc: Istanza del documento precedente.
        documento_nuovo_text (str): Testo estratto dal nuovo documento.
        db: Sessione database.

    Returns:
        nuovo_doc o None: Nuovo documento se revisionato, altrimenti None.
    """
    testo_vecc = documento_vecc.testo_estratto
    sim = confronta_testi(testo_vecc, documento_nuovo_text)

    if sim < 0.9:
        # Crea nuova revisione
        nuova_rev = (documento_vecc.revisione or 1) + 1
        nuovo_nome = genera_nome_file(
            documento_vecc.oggetto,
            documento_vecc.referente,
            documento_vecc.data_creazione,
            nuova_rev
        )
        # Assumiamo che Documento sia il modello SQLAlchemy
        nuovo_doc = documento_vecc.__class__(
            nome=nuovo_nome,
            revisione=nuova_rev,
            originale_id=documento_vecc.originale_id or documento_vecc.id,
            azienda=documento_vecc.azienda,
            reparto=documento_vecc.reparto,
            oggetto=documento_vecc.oggetto,
            referente=documento_vecc.referente,
            testo_estratto=documento_nuovo_text,
            storico=False,
        )
        documento_vecc.storico = True
        db.add(nuovo_doc)
        db.commit()
        return nuovo_doc
    return None 