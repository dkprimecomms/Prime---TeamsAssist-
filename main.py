import json
import os
from datetime import datetime, timedelta, timezone

from flask import Flask, request, jsonify
import msal
import requests
from dotenv import load_dotenv

load_dotenv()

TENANT_ID = os.getenv("TENANT_ID")
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
WEBHOOK_PUBLIC_BASE = os.getenv("WEBHOOK_PUBLIC_BASE")
CLIENT_STATE = os.getenv("WEBHOOK_CLIENT_STATE", "someRandomState")
AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
SCOPE = ["https://graph.microsoft.com/.default"]
GRAPH_BASE = "https://graph.microsoft.com/v1.0"

app = Flask(__name__)

#Get token from Azure AD
def get_app_token():
    app_confidential = msal.ConfidentialClientApplication(
        CLIENT_ID,
        authority=AUTHORITY,
        client_credential=CLIENT_SECRET,
    )
    result = app_confidential.acquire_token_for_client(scopes=SCOPE)
    if "access_token" not in result:
        print("Error acquiring token:", result)
        raise SystemExit("Cannot get app token")
    return result["access_token"]


# --------------------------
# Subscription management
# --------------------------
def create_callrecord_subscription():
    """
    Creates a callRecord subscription:
    - resource: /communications/callRecords
    - changeType: created (new callRecord = call/call-meeting ended)
    """
    access_token = get_app_token()

    # Subscriptions have a max lifetime. For callRecords it's short (e.g. few hours).
    # Here we set expiration to ~1 hour from now. You must renew it periodically.
    expiry = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()

    notification_url = f"{WEBHOOK_PUBLIC_BASE}/graph/webhook"

    body = {
        "changeType": "created",
        "notificationUrl": notification_url,
        "resource": "/communications/callRecords",
        "expirationDateTime": expiry,
        "clientState": CLIENT_STATE,
    }

    print("Creating subscription with body:")
    print(json.dumps(body, indent=2))

    resp = requests.post(
        f"{GRAPH_BASE}/subscriptions",
        headers={"Authorization": f"Bearer {access_token}"},
        json=body,
    )
    print("Subscription status:", resp.status_code, resp.reason)
    print("Response:", resp.text)


# --------------------------
# Transcript placeholder
# --------------------------
def fetch_transcript_for_call(call_record: dict):
    """
    Placeholder function where YOU implement:
    - find transcript for this callRecord
    - download transcript text
    - store/summarize as needed

    This is tenant-specific:
      * If using Graph transcripts API:
          - Map callRecord to onlineMeetingId
          - Call /communications/onlineMeetings/{id}/transcripts
      * If transcripts are in OneDrive/SharePoint:
          - Use organizer + time window to search drive for transcript file
          - Download and parse VTT/DOCX
    """
    print("\n[fetch_transcript_for_call] Called for callRecord:")
    print(json.dumps(call_record, indent=2))
    print("""
[TODO] Implement:
  - Check if this call involved your user (or any user you care about)
  - Check for transcript-related info (if present in callRecord)
  - Or query OneDrive/SharePoint/Graph transcript endpoints to locate transcript
  - Download transcript content
  - Summarize & store in DB
""")


def handle_callrecord_id(callrecord_id: str):
    """Fetch a callRecord by ID and pass it to transcript handler."""
    print(f"\n[handle_callrecord_id] Processing callRecordId={callrecord_id}")
    token = get_app_token()

    url = f"{GRAPH_BASE}/communications/callRecords/{callrecord_id}"
    resp = requests.get(url, headers={"Authorization": f"Bearer {token}"})

    print("callRecord GET status:", resp.status_code, resp.reason)
    if resp.status_code != 200:
        print("Body:", resp.text)
        return

    call_record = resp.json()

    # TODO: Filter to *your* meetings/calls only if needed:
    # - Get your user id / upn
    # - Inspect call_record["participants"] list
    # - If you're not a participant, skip
    # For now, just call the placeholder unconditionally:
    fetch_transcript_for_call(call_record)


# --------------------------
# Webhook endpoint
# --------------------------
@app.route("/graph/webhook", methods=["GET", "POST"])
def graph_webhook():
    # 1) Validation handshake (when subscription is created or renewed)
    validation_token = request.args.get("validationToken")
    if validation_token:
        print("[webhook] Validation request received.")
        # According to Graph docs, you must echo the validationToken
        return validation_token, 200, {"Content-Type": "text/plain"}

    # 2) Normal notifications
    data = request.get_json(force=True, silent=True) or {}
    print("\n[webhook] Notification received:")
    print(json.dumps(data, indent=2))

    value = data.get("value", [])
    for notification in value:
        # Optional: validate clientState
        if notification.get("clientState") != CLIENT_STATE:
            print("[webhook] clientState does not match, ignoring notification.")
            continue

        resource = notification.get("resource", "")
        resource_data = notification.get("resourceData", {})
        record_id = resource_data.get("id")

        # Typically resource is like "communications/callRecords/{id}"
        print(f"[webhook] resource={resource}, id={record_id}")

        if record_id:
            # Here you might enqueue this id into a queue/job instead of inline
            handle_callrecord_id(record_id)

    # Graph expects 202 Accepted quickly
    return "", 202


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    print(f"Starting Flask app on port {port}")
    app.run(host="0.0.0.0", port=port, debug=True)
