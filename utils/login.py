import json
from config import CREDENTIALS_PATH

def check_credentials(username: str, password: str, role: str = None) -> bool:
    try:
        with open(CREDENTIALS_PATH, "r", encoding="utf-8") as f:
            users = json.load(f).get("users", [])
    except Exception as e:
        print(f"Fehler beim Laden der Login-Daten: {e}")
        return False

    role_map = {
        "employee": "Mitarbeiter",
        "teamlead": "Teamleiter",
        "departmentlead": "Abteilungsleiter",
        "manager": "Manager"
    }
    expected_role_label = role_map.get(role, role)

    for user in users:
        if user.get("username") == username and user.get("password") == password:
            user_role = user.get("role", "").strip()
            if role is None or user_role == expected_role_label:
                print(f"[DEBUG] Login akzeptiert ({username}, Rolle: {user_role})")
                return True
            else:
                print(f"[DEBUG] Login abgelehnt - falsche Rolle: erwartet '{expected_role_label}', aber war '{user_role}'")
                return False

    print(f"[DEBUG] Login abgelehnt - Benutzername oder Passwort falsch")
    return False