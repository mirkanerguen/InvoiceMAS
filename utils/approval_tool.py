from config import APPROVAL_RULES

def map_bruttobetrag_to_role(brutto: float) -> str:
    if brutto <= APPROVAL_RULES["employee"]:
        return "1"
    elif brutto <= APPROVAL_RULES["teamlead"]:
        return "2"
    elif brutto <= APPROVAL_RULES["departmentlead"]:
        return "3"
    else:
        return "4"
