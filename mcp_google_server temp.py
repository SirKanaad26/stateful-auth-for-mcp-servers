import os.path
import datetime as dt
# We'll need base64 later if we want to decode email bodies
# import base64
# import re

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# --- CONFIGURATION ---
# These are the permissions your script will request.
# For reading mail:
SCOPES_GMAIL = ['https://www.googleapis.com/auth/gmail.readonly']
# For full calendar access (read/write/delete):
SCOPES_CALENDAR = ['https://www.googleapis.com/auth/calendar']
# Combine all scopes
SCOPES = SCOPES_GMAIL + SCOPES_CALENDAR

# The file token.json stores the user's access and refresh tokens.
# It's created automatically when the authorization flow completes for the first time.
TOKEN_FILE = 'token.json'
# The file you downloaded from Google Cloud Console.
CREDENTIALS_FILE = 'credentials.json'

def get_credentials():
    """
    Gets user credentials for Google APIs.
    Handles the OAuth 2.0 flow and token generation.
    """
    creds = None
    # Check if the token file already exists
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("Credentials expired, refreshing...")
            creds.refresh(Request())
        else:
            print("No valid credentials found, running authorization flow...")
            flow = InstalledAppFlow.from_client_secrets_file(
                CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        
        # Save the credentials for the next run
        with open(TOKEN_FILE, 'w') as token:
            print(f"Saving credentials to {TOKEN_FILE}")
            token.write(creds.to_json())
    
    return creds

def list_recent_emails(service, max_results=5):
    """Lists the user's most recent emails."""
    print(f"\n--- Getting last {max_results} emails ---")
    try:
        # Get a list of message IDs
        # We use 'INBOX' to only get emails from the inbox
        results = service.users().messages().list(userId='me', labelIds=['INBOX'], maxResults=max_results).execute()
        messages = results.get('messages', [])

        if not messages:
            print("No new messages found in INBOX.")
            return

        print("Recent Emails:")
        for msg in messages:
            # Get the full message details for each ID
            # 'metadata' format is faster and gives us headers/snippet
            msg_data = service.users().messages().get(userId='me', id=msg['id'], format='metadata').execute()
            
            # Get headers
            headers = msg_data.get('payload', {}).get('headers', [])
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
            from_email = next((h['value'] for h in headers if h['name'] == 'From'), 'No Sender')
            
            print("--------------------")
            print(f"From: {from_email}")
            print(f"Subject: {subject}")
            print(f"Snippet: {msg_data.get('snippet', 'No Snippet')}")

    except HttpError as error:
        print(f'An error occurred while fetching emails: {error}')


def create_calendar_event(service, summary, start_time, end_time, description=None, location=None):
    """Creates a new event on the user's primary calendar."""
    print(f"\n--- Creating calendar event: '{summary}' ---")
    
    # Get the user's timezone to create correct datetime objects
    try:
        calendar_list_entry = service.calendarList().get(calendarId='primary').execute()
        user_timezone = calendar_list_entry['timeZone']
        print(f"Using timezone: {user_timezone}")
    except HttpError as error:
        print(f"Could not get user timezone, defaulting to UTC. Error: {error}")
        user_timezone = 'UTC'

    event_body = {
        'summary': summary,
        'location': location,
        'description': description,
        'start': {
            'dateTime': start_time.isoformat(),
            'timeZone': user_timezone,
        },
        'end': {
            'dateTime': end_time.isoformat(),
            'timeZone': user_timezone,
        },
        # You can add attendees like this:
        # 'attendees': [
        #     {'email': 'friend@example.com'},
        # ],
        'reminders': {
            'useDefault': True,
        },
    }

    try:
        created_event = service.events().insert(calendarId='primary', body=event_body).execute()
        print(f"Event created successfully!")
        print(f"Link: {created_event.get('htmlLink')}")
        return created_event
    except HttpError as error:
        print(f'An error occurred while creating event: {error}')
        return None


def main():
    """
    Main function to authenticate and call APIs.
    """
    try:
        creds = get_credentials()

        # --- 1. Build API Services ---
        print("Building API services...")
        calendar_service = build('calendar', 'v3', credentials=creds)
        gmail_service = build('gmail', 'v1', credentials=creds)
        
        print("\nSuccessfully connected to both APIs!")

        # --- 2. Call the Gmail API ---
        # Let's read your 5 most recent emails
        list_recent_emails(gmail_service, max_results=5)


        # --- 3. Call the Google Calendar API ---
        # Let's create a sample event for tomorrow
        print("\n--- Scheduling a test event for tomorrow ---")
        
        # Set up start and end times for an event tomorrow at 10:00 AM
        # We use .now() to get a local datetime object. 
        # The create_calendar_event function handles the timezone.
        now = dt.datetime.now() 
        start_time = dt.datetime(now.year, now.month, now.day, 10, 0, 0) + dt.timedelta(days=1)
        end_time = start_time + dt.timedelta(hours=1)
        
        print(f"Scheduling from {start_time} to {end_time}")

        create_calendar_event(
            service=calendar_service,
            summary='MCP Server Test Event',
            description='This is a test event created by my Python script.',
            location='My Computer',
            start_time=start_time,
            end_time=end_time
        )


        # --- Original test code (you can comment this out) ---
        # print("\n--- Google Calendar Test (Original) ---")
        # 'Z' indicates UTC time
        # now_utc = dt.datetime.utcnow().isoformat() + 'Z'  
        # print('Getting the upcoming 10 events:')
        # events_result = calendar_service.events().list(
        #     calendarId='primary', 
        #     timeMin=now_utc,
        #     maxResults=10, 
        #     singleEvents=True,
        #     orderBy='startTime'
        # ).execute()
        # events = events_result.get('items', [])

        # if not events:
        #     print('No upcoming events found.')
        # else:
        #     for event in events:
        #         start = event['start'].get('dateTime', event['start'].get('date'))
        #         print(f"{start} - {event['summary']}")

        # --- Original test code (you ecan comment this out) ---
        # print("\n--- Gmail API Test (Original) ---")
        # # Call the Users.labels.list method
        # results = gmail_service.users().labels().list(userId='me').execute()
        # labels = results.get('labels', [])

        # if not labels:
        #     print('No labels found.')
        # else:
        #     print('Gmail Labels:')
        #     for label in labels:
        #         print(f"- {label['name']}")


    except HttpError as error:
        print(f'An error occurred: {error}')
    except Exception as e:
        print(f'An unexpected error occurred: {e}')

if __name__ == '__main__':
    main()

