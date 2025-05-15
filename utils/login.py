import json
from config import CREDENTIALS_PATH

def check_credentials(username: str, password: str, role: str = None) -> bool:
    with open(CREDENTIALS_PATH, "r", encoding="utf-8") as f:
        users = json.load(f).get("users", [])
    
    for user in users:
        if user.get("username") == username and user.get("password") == password:
            if role is None or user.get("role", "").lower() == role.lower():
                return True
    return False
