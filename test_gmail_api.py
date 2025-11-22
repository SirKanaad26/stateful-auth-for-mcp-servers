#!/usr/bin/env python3
"""
Debug script to test Gmail API connection and email reading
"""

import os
import sys
import pickle
import logging
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

def test_gmail_connection():
    """Test Gmail API connection and read emails"""
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    credentials_file = os.path.join(script_dir, 'credentials.json')
    token_file = os.path.join(script_dir, 'token.pickle')
    
    print(f"\n{'='*60}")
    print("GMAIL API DEBUG TEST")
    print(f"{'='*60}\n")
    
    # Check if credentials.json exists
    print(f"1. Checking for credentials.json...")
    if not os.path.exists(credentials_file):
        print(f"   ❌ NOT FOUND at: {credentials_file}")
        print(f"   Please make sure credentials.json is in the same directory as this script")
        return False
    else:
        print(f"   ✅ Found at: {credentials_file}")
    
    # Try to authenticate
    print(f"\n2. Authenticating with Google...")
    creds = None
    
    # Check for cached token
    if os.path.exists(token_file):
        try:
            with open(token_file, 'rb') as token:
                creds = pickle.load(token)
                print(f"   ✅ Loaded cached token from: {token_file}")
        except Exception as e:
            print(f"   ⚠️  Could not load token: {e}")
            creds = None
    else:
        print(f"   ℹ️  No cached token found at: {token_file}")
    
    # If no valid credentials, get new ones
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print(f"   Refreshing expired credentials...")
            try:
                creds.refresh(Request())
                print(f"   ✅ Credentials refreshed")
            except Exception as e:
                print(f"   ❌ Failed to refresh: {e}")
                return False
        else:
            print(f"   Starting OAuth flow...")
            try:
                flow = InstalledAppFlow.from_client_secrets_file(
                    credentials_file,
                    SCOPES
                )
                creds = flow.run_local_server(port=0)
                print(f"   ✅ OAuth flow completed")
                
                # Save credentials
                try:
                    with open(token_file, 'wb') as token:
                        pickle.dump(creds, token)
                    print(f"   ✅ Credentials saved to: {token_file}")
                except Exception as e:
                    print(f"   ⚠️  Could not save credentials: {e}")
            except Exception as e:
                print(f"   ❌ OAuth flow failed: {e}")
                return False
    
    # Build Gmail service
    print(f"\n3. Building Gmail service...")
    try:
        service = build('gmail', 'v1', credentials=creds)
        print(f"   ✅ Gmail service built successfully")
    except Exception as e:
        print(f"   ❌ Failed to build service: {e}")
        return False
    
    # Test listing messages
    print(f"\n4. Fetching recent emails...")
    try:
        results = service.users().messages().list(userId='me', maxResults=5).execute()
        messages = results.get('messages', [])
        print(f"   ✅ Successfully fetched messages list")
        print(f"   Found {len(messages)} recent messages")
        
        if not messages:
            print(f"   ℹ️  No messages found in mailbox")
            return True
        
        # Get details of first email
        print(f"\n5. Fetching details of first email...")
        msg = service.users().messages().get(userId='me', id=messages[0]['id'], format='full').execute()
        
        headers = msg['payload']['headers']
        subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'N/A')
        from_addr = next((h['value'] for h in headers if h['name'] == 'From'), 'N/A')
        to_addr = next((h['value'] for h in headers if h['name'] == 'To'), 'N/A')
        date = next((h['value'] for h in headers if h['name'] == 'Date'), 'N/A')
        
        print(f"   ✅ Successfully fetched email details")
        print(f"   Subject: {subject}")
        print(f"   From: {from_addr}")
        print(f"   To: {to_addr}")
        print(f"   Date: {date}")
        
        print(f"\n{'='*60}")
        print("✅ ALL TESTS PASSED - Gmail API is working!")
        print(f"{'='*60}\n")
        return True
        
    except HttpError as error:
        print(f"   ❌ Gmail API error: {error}")
        return False
    except Exception as e:
        print(f"   ❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = test_gmail_connection()
    sys.exit(0 if success else 1)