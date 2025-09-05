import os
import pickle
import datetime
from typing import Optional, Tuple

from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Scopes for creating events with Meet links
SCOPES = ['https://www.googleapis.com/auth/calendar.events']


CLIENT_SECRETS_FILE = os.environ.get('GOOGLE_CLIENT_SECRETS', 'client_secret.json')
TOKEN_FILE = os.environ.get('GOOGLE_TOKEN_FILE', 'token.pickle')


def get_credentials():
    creds = None
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, 'rb') as token:
            creds = pickle.load(token)
    if not creds or not getattr(creds, 'valid', False):
        flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS_FILE, SCOPES)
        creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, 'wb') as token:
            pickle.dump(creds, token)
    return creds


def create_google_meet_event(summary: str,
                             description: str,
                             attendees_emails: Optional[list] = None,
                             start_time_utc: Optional[datetime.datetime] = None,
                             end_time_utc: Optional[datetime.datetime] = None) -> Tuple[str, str]:
    """
    Create a Calendar event with a Google Meet link.

    Returns: (event_id, hangout_link)
    """
    creds = get_credentials()
    service = build('calendar', 'v3', credentials=creds)

    now = datetime.datetime.utcnow()
    start = start_time_utc or (now + datetime.timedelta(hours=1))
    end = end_time_utc or (start + datetime.timedelta(hours=1))

    event = {
        'summary': summary or 'Meeting',
        'description': description or '',
        'start': {
            'dateTime': start.isoformat() + 'Z',
            'timeZone': 'UTC',
        },
        'end': {
            'dateTime': end.isoformat() + 'Z',
            'timeZone': 'UTC',
        },
        'conferenceData': {
            'createRequest': {
                'requestId': f'meetingdash-{int(now.timestamp())}',
                'conferenceSolutionKey': {'type': 'hangoutsMeet'}
            }
        }
    }

    if attendees_emails:
        event['attendees'] = [{'email': e} for e in attendees_emails]

    created_event = service.events().insert(
        calendarId='primary',
        body=event,
        conferenceDataVersion=1
    ).execute()

    return created_event['id'], created_event.get('hangoutLink', '')


