import re

def hard_match_check(extracted, known):
    """
    Vergleicht eine extrahierte Rechnung mit bekannten Transaktionen anhand von 4 harten Kriterien.
    Gibt True zurück, wenn alle Kriterien erfüllt sind, sonst False.
    """

    def normalize(text):
        if isinstance(text, list):
            text = " ".join(text)
        return str(text).lower().replace(" ", "").strip()


    extr_rn = normalize(extracted.get("rechnungsnummer", ""))
    extr_lieferant = normalize(extracted.get("lieferant", ""))
    extr_leistung = normalize(extracted.get("leistung", ""))
    extr_betrag_raw = str(extracted.get("betrag", ""))
    match = re.search(r"Brutto[: ]*([\d\.,]+)", extr_betrag_raw)
    extr_betrag = float(match.group(1).replace(",", ".").replace("€", "")) if match else 0.0

    for ref in known:
        ref_rn = normalize(ref.get("rechnungsnummer", ""))
        ref_lieferant = normalize(ref.get("lieferant", ""))
        ref_leistung = normalize(ref.get("leistung", ""))
        ref_betrag = float(str(ref.get("betrag_brutto", 0)).replace(",", "."))

        if extr_rn != ref_rn:
            continue
        if ref_lieferant not in extr_lieferant and extr_lieferant not in ref_lieferant:
            continue
        if ref_leistung not in extr_leistung and extr_leistung not in ref_leistung:
            continue
        if abs(extr_betrag - ref_betrag) > 1:
            continue

        return True

    return False
