import datetime
import os
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from flask import jsonify

# Google API Configuration
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SCOPES = ["https://www.googleapis.com/auth/calendar"]
TOKEN_PATH = os.path.join(BASE_DIR, "token.json")
print(TOKEN_PATH)
CLIENT_SECRET_FILE = os.getenv("GOOGLE_CREDENTIALS_FILE", os.path.join(BASE_DIR, "credentials.json"))

def get_google_credentials():
    """Handles Google OAuth authentication and returns credentials."""
    creds = None
    print("token path")
    print(TOKEN_PATH)
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as e:
                print(f"Error refreshing token: {e}")
                os.remove(TOKEN_PATH)
                creds = None
        if not creds:
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
            creds = flow.run_local_server(port=0)

            with open(TOKEN_PATH, "w") as token_file:
                token_file.write(creds.to_json())
    
    return creds

def add_appointment(email, appointment_date, start_time, end_time, description):
    try:
        creds = get_google_credentials()
        service = build("calendar", "v3", credentials=creds)

        event = {
            "summary": "Dental Appointment",
            "location": "Virtual Event",
            "description": description,
            "colorId": "6",
            "start": {
                "dateTime": f"{appointment_date}T{start_time}:00+05:30",
                "timeZone": "Asia/Kolkata"
            },
            "end": {
                "dateTime": f"{appointment_date}T{end_time}:00+05:30",
                "timeZone": "Asia/Kolkata"
            },
            "attendees": [
                {"email": "digismile.doc@gmail.com"},
                {"email": email}
            ]
        }

        event = service.events().insert(calendarId="primary", body=event).execute()
        event_id = event.get("id")  # Extract only event ID
        print(f"Event created: {event.get('htmlLink')}")
        return event_id  # Return only event ID (string)

    except HttpError as error:
        print(f"Google Calendar API error: {error}")
        return None  # Return None on failure

def cancel_event(event_id):
    """Deletes an event from Google Calendar."""
    try:
        creds = get_google_credentials()
        service = build("calendar", "v3", credentials=creds)
        service.events().delete(calendarId="primary", eventId=event_id).execute()
        print(f"Event with ID {event_id} deleted successfully.")
        return {"message": "Event successfully deleted"}
    except Exception as error:
        print(f"An error occurred: {error}")
        return {"error": "Failed to delete event"}
