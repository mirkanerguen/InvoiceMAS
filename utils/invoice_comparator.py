# utils/invoice_comparator.py

def compare_invoice_with_reference(rechnungsnummer, lieferant, leistung, betrag, reference_data):
    """
    Vergleicht eine Rechnung mit bekannten Referenzrechnungen.
    Nur wenn die Rechnungsnummer exakt übereinstimmt UND alle weiteren Angaben plausibel sind,
    wird True zurückgegeben.
    """

    def normalize(text):
        return str(text).strip().lower().replace(" ", "").replace("-", "-")

    normalized_input_nr = normalize(rechnungsnummer)
    normalized_input_lieferant = normalize(lieferant)
    normalized_input_leistung = normalize(leistung)
    try:
        betrag_float = round(float(betrag), 2)
    except ValueError:
        betrag_float = 0.0

    for ref in reference_data:
        if normalize(ref["rechnungsnummer"]) != normalized_input_nr:
            continue  # Rechnungsnummer stimmt nicht exakt überein → sofort überspringen

        # Weitere Felder prüfen
        lieferant_match = normalize(ref["lieferant"]) in normalized_input_lieferant or normalized_input_lieferant in normalize(ref["lieferant"])
        leistung_match = normalize(ref["leistung"]) in normalized_input_leistung or normalized_input_leistung in normalize(ref["leistung"])
        betrag_match = abs(float(ref["betrag_brutto"]) - betrag_float) < 1.0

        if lieferant_match and leistung_match and betrag_match:
            return True  # vollständige Übereinstimmung bei richtiger Rechnungsnummer

    return False
