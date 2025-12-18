import msal
import requests
import os
from dotenv import load_dotenv
import json
import base64

load_dotenv()

TENANT_ID = os.getenv("TENANT_ID")
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")

AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
SCOPE = ["https://graph.microsoft.com/.default"]

# ⭐ Create a completely fresh token cache
fresh_cache = msal.TokenCache()   # This is empty

app = msal.ConfidentialClientApplication(
    CLIENT_ID,
    authority=AUTHORITY,
    client_credential=CLIENT_SECRET,
    token_cache=fresh_cache
)

# ⭐ Acquire a completely fresh token
result = app.acquire_token_for_client(scopes=SCOPE)
print("Access Token", result)

def decode_jwt_part(part):
    part += '=' * (-len(part) % 4)
    return json.loads(base64.urlsafe_b64decode(part).decode("utf-8"))

if "access_token" in result:
    print("Access token acquired.\n")
    header_b64, payload_b64, signature_b64 = result["access_token"].split(".")
    payload = decode_jwt_part(payload_b64)
    print(json.dumps(payload, indent=2))
else:
    print("Error acquiring token:")
    print(result.get("error_description"))
