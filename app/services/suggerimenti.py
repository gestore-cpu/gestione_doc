from app.models.suggerimento_ai import SuggerimentoAI

def salva_suggerimento_ai(db, titolo, contenuto, categoria, fonte="AI"):
    suggerimento = SuggerimentoAI(
        titolo=titolo,
        contenuto=contenuto,
        categoria=categoria,
        fonte=fonte
    )
    db.add(suggerimento)
    db.commit()
    db.refresh(suggerimento)
    return suggerimento 