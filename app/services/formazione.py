def trasforma_in_modulo_formativo(suggerimento):
    return {
        "titolo": f"Formazione – {suggerimento.titolo}",
        "contenuto": suggerimento.contenuto,
        "tags": [suggerimento.categoria, "AI", "Miglioramento continuo"],
        "origine": "Suggerimento AI",
        "visibile_a": "manager,reparti_interessati"
    } 