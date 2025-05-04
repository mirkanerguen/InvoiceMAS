import json

def check_credentials(username, password, credentials_path="data/credentials.json"):
    with open(credentials_path, "r", encoding="utf-8") as f:
        creds = json.load(f)

    return any(user["username"] == username and user["password"] == password for user in creds["users"])
