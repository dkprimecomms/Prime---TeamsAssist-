import msal
import requests
import os
from dotenv import load_dotenv
import pprint
load_dotenv()

TENANT_ID = os.getenv("TENANT_ID")
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")

AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
SCOPE = ["https://graph.microsoft.com/.default"]

app = msal.ConfidentialClientApplication(
    CLIENT_ID,
    authority=AUTHORITY,
    client_credential=CLIENT_SECRET,
)

result = app.acquire_token_for_client(scopes=SCOPE)
print("Acess Token: ",result)

if "access_token" in result:
    print("Access token acquired.\n")
    # Call Microsoft Graph - list first 10 users
    graph_url = "https://graph.microsoft.com/v1.0/users?$top=20"
    response = requests.get(
        graph_url,
        headers={"Authorization": f"Bearer {result['access_token']}"}
    )

    print("Response from Microsoft Graph:\n")
    # print(response.status_code, response.reason)
    # pprint.pprint(response.json())
else:
    print("Error acquiring token:")
    print(result.get("error_description"))
