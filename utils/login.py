import json

def check_credentials(username: str, password: str, role: str = None) -> bool:
    with open("data/credentials.json", "r", encoding="utf-8") as f:
        users = json.load(f)["users"]
    
    for user in users:
        if user["username"] == username and user["password"] == password:
            if role is None or user.get("role", "").lower() == role.lower():
                return True
    return False
