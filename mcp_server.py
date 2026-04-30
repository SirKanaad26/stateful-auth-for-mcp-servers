#!/usr/bin/env python3
"""
Custom MCP Server for Gmail and Google Calendar
Implements JSON-RPC 2.0 protocol over stdin/stdout
With Stateful Authentication Layer
"""

import json
import sys
import logging
from typing import Any, Dict, Optional, List
from datetime import datetime, timedelta
import os
import pickle

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.api_core.exceptions import GoogleAPICallError
import google.auth
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Import the authentication verifier
from auth_verifier import create_verifier, AuthVerifier

# Setup logging to stderr so it doesn't interfere with JSON-RPC communication
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger(__name__)

# Google API scopes
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/calendar'
]

class GoogleAuthenticator:
    """Handles OAuth 2.0 authentication for Google APIs"""
    
    def __init__(self, credentials_file: str = 'credentials.json', token_file: str = 'token.pickle'):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        self.credentials_file = os.path.join(script_dir, credentials_file)
        self.token_file = os.path.join(script_dir, token_file)
        self.creds = None
    
    def authenticate(self) -> Credentials:
        """Authenticate and return credentials"""
        if os.path.exists(self.token_file):
            try:
                with open(self.token_file, 'rb') as token:
                    self.creds = pickle.load(token)
                    logger.info("Loaded cached credentials")
            except Exception as e:
                logger.warning(f"Could not load token file: {e}")
                self.creds = None
        
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                logger.info("Refreshing expired credentials")
                self.creds.refresh(Request())
            else:
                logger.info("Starting OAuth flow")
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_file,
                    SCOPES
                )
                self.creds = flow.run_local_server(port=0)
            
            try:
                with open(self.token_file, 'wb') as token:
                    pickle.dump(self.creds, token)
                logger.info(f"Credentials saved to {self.token_file}")
            except (OSError, IOError) as e:
                logger.warning(f"Could not save token file (will need to re-authenticate): {e}")
        
        return self.creds

class GmailService:
    """Wrapper for Gmail API operations"""
    
    def __init__(self, service):
        self.service = service
    
    def get_recent_emails(self, max_results: int = 10, query: str = "") -> List[Dict[str, Any]]:
        """Fetch recent emails with optional search query"""
        try:
            results = self.service.users().messages().list(
                userId='me',
                q=query,
                maxResults=max_results
            ).execute()
            
            messages = results.get('messages', [])
            emails = []
            
            for message in messages:
                msg = self.service.users().messages().get(
                    userId='me',
                    id=message['id'],
                    format='full'
                ).execute()
                
                headers = msg['payload']['headers']
                email_data = {
                    'id': msg['id'],
                    'threadId': msg['threadId'],
                    'subject': self._get_header(headers, 'Subject'),
                    'from': self._get_header(headers, 'From'),
                    'to': self._get_header(headers, 'To'),
                    'date': self._get_header(headers, 'Date'),
                    'snippet': msg.get('snippet', '')
                }
                emails.append(email_data)
            
            return emails
        except HttpError as error:
            logger.error(f"Gmail API error: {error}")
            raise
    
    @staticmethod
    def _get_header(headers: List[Dict], name: str) -> str:
        """Extract header value by name"""
        for header in headers:
            if header['name'] == name:
                return header['value']
        return ""

class CalendarService:
    """Wrapper for Google Calendar API operations"""
    
    def __init__(self, service):
        self.service = service
    
    def create_event(self, summary: str, start_time: str, end_time: str, 
                    description: str = "", calendar_id: str = 'primary') -> Dict[str, Any]:
        """Create a calendar event"""
        try:
            event = {
                'summary': summary,
                'description': description,
                'start': {'dateTime': start_time, 'timeZone': 'UTC'},
                'end': {'dateTime': end_time, 'timeZone': 'UTC'},
            }
            
            result = self.service.events().insert(
                calendarId=calendar_id,
                body=event
            ).execute()
            
            return {
                'id': result['id'],
                'summary': result['summary'],
                'start': result['start'],
                'end': result['end'],
                'htmlLink': result.get('htmlLink', '')
            }
        except HttpError as error:
            logger.error(f"Calendar API error: {error}")
            raise
    
    def update_event(self, event_id: str, updates: Dict[str, Any], 
                    calendar_id: str = 'primary') -> Dict[str, Any]:
        """Update a calendar event"""
        try:
            event = self.service.events().get(
                calendarId=calendar_id,
                eventId=event_id
            ).execute()
            
            for key, value in updates.items():
                if key in ['summary', 'description']:
                    event[key] = value
                elif key in ['start_time', 'start']:
                    if isinstance(value, str):
                        event['start'] = {'dateTime': value, 'timeZone': 'UTC'}
                    else:
                        event['start'] = value
                elif key in ['end_time', 'end']:
                    if isinstance(value, str):
                        event['end'] = {'dateTime': value, 'timeZone': 'UTC'}
                    else:
                        event['end'] = value
            
            result = self.service.events().update(
                calendarId=calendar_id,
                eventId=event_id,
                body=event
            ).execute()
            
            return {
                'id': result['id'],
                'summary': result['summary'],
                'start': result['start'],
                'end': result['end'],
                'htmlLink': result.get('htmlLink', '')
            }
        except HttpError as error:
            logger.error(f"Calendar API error: {error}")
            raise
    
    def delete_event(self, event_id: str, calendar_id: str = 'primary') -> bool:
        """Delete a calendar event"""
        try:
            self.service.events().delete(
                calendarId=calendar_id,
                eventId=event_id
            ).execute()
            return True
        except HttpError as error:
            logger.error(f"Calendar API error: {error}")
            raise
    
    def get_upcoming_events(self, max_results: int = 10, time_min: Optional[str] = None,
                           calendar_id: str = 'primary') -> List[Dict[str, Any]]:
        """Get upcoming calendar events"""
        try:
            if not time_min:
                time_min = datetime.utcnow().isoformat() + 'Z'
            
            results = self.service.events().list(
                calendarId=calendar_id,
                timeMin=time_min,
                maxResults=max_results,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = results.get('items', [])
            return events
        except HttpError as error:
            logger.error(f"Calendar API error: {error}")
            raise

class MCPServer:
    """MCP Server implementation for Google APIs with Stateful Authentication"""
    
    def __init__(self):
        """Initialize the server"""
        try:
            self.authenticator = GoogleAuthenticator()
            self.creds = self.authenticator.authenticate()
            
            gmail_service = build('gmail', 'v1', credentials=self.creds)
            calendar_service = build('calendar', 'v3', credentials=self.creds)
            
            self.gmail = GmailService(gmail_service)
            self.calendar = CalendarService(calendar_service)
            
            # Initialize the authentication verifier
            self.auth_verifier = create_verifier()
            
            logger.info("Services initialized successfully")
            logger.info("Stateful authentication layer initialized")
        except Exception as e:
            logger.critical(f"Failed to initialize services: {e}", exc_info=True)
            raise
    
    def tools_call_handler(self, params: Dict[str, Any], req_id: int) -> Dict[str, Any]:
        """Handle tools/call request with stateful authentication"""
        try:
            tool_name = params.get('name')
            tool_input = params.get('arguments', {})
            
            logger.info(f"Calling tool: {tool_name} with input: {tool_input}")
            
            # STEP 1: Verify the request with the auth verifier
            is_allowed, reason = self.auth_verifier.verify_request(tool_name, tool_input)
            
            if not is_allowed:
                logger.warning(f"Request DENIED: {reason}")
                return {
                    'jsonrpc': '2.0',
                    'id': req_id,
                    'result': {
                        'content': [
                            {
                                'type': 'text',
                                'text': json.dumps({
                                    'error': 'Authorization denied',
                                    'reason': reason,
                                    'tool': tool_name,
                                    'status': 'DENIED'
                                }, indent=2)
                            }
                        ],
                        'isError': True
                    }
                }
            
            logger.info(f"Request ALLOWED: {reason}")
            
            # STEP 2: Execute the tool call
            if tool_name == 'read_emails':
                result = self.gmail.get_recent_emails(
                    max_results=tool_input.get('max_results', 10),
                    query=tool_input.get('query', '')
                )
            elif tool_name == 'create_calendar_event':
                result = self.calendar.create_event(
                    summary=tool_input.get('summary'),
                    start_time=tool_input.get('start_time'),
                    end_time=tool_input.get('end_time'),
                    description=tool_input.get('description', '')
                )
            elif tool_name == 'update_calendar_event':
                event_id = tool_input.get('event_id')
                updates = {}
                for key in ['summary', 'description', 'start_time', 'end_time']:
                    if key in tool_input:
                        updates[key] = tool_input[key]
                result = self.calendar.update_event(event_id, updates)
            elif tool_name == 'delete_calendar_event':
                result = self.calendar.delete_event(tool_input.get('event_id'))
            elif tool_name == 'get_calendar_events':
                result = self.calendar.get_upcoming_events(
                    max_results=tool_input.get('max_results', 10),
                    time_min=tool_input.get('time_min')
                )
            else:
                return self.error_response(req_id, -32601, f"Unknown tool: {tool_name}")
            
            # STEP 3: Update state after successful execution
            logger.info(f"Tool {tool_name} executed successfully, updating state")
            self.auth_verifier.update_state_after_success(tool_name, tool_input, result)
            
            return {
                'jsonrpc': '2.0',
                'id': req_id,
                'result': {
                    'content': [
                        {
                            'type': 'text',
                            'text': json.dumps(result, indent=2)
                        }
                    ]
                }
            }
        
        except Exception as e:
            logger.exception(f"Error calling tool: {e}")
            return self.error_response(req_id, -32603, f"Tool execution failed: {str(e)}")
    
    def handle_request(self, request: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Handle a JSON-RPC request"""
        try:
            method = request.get('method')
            params = request.get('params', {})
            req_id = request.get('id')
            
            logger.info(f"Received request: method={method}, id={req_id}")
            
            if method == 'initialize':
                return self.initialize_handler(req_id, params)
            elif method == 'tools/list':
                return self.tools_list_handler(req_id, params)
            elif method == 'tools/call':
                return self.tools_call_handler(params, req_id)
            elif method in ['prompts/list', 'resources/list']:
                # Don't respond to these methods - just return None
                logger.info(f"Ignoring method: {method}")
                return None
            else:
                # For unknown methods, just return None instead of error
                logger.info(f"Unknown method: {method}, ignoring")
                return None
        
        except Exception as e:
            logger.exception(f"Error handling request: {e}")
            return self.error_response(req_id, -32603, f"Internal error: {str(e)}")

    def initialize_handler(self, req_id: int, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle initialize request"""
        return {
            'jsonrpc': '2.0',
            'id': req_id,
            'result': {
                'protocolVersion': '2025-06-18',
                'capabilities': {
                    'tools': {}
                },
                'serverInfo': {
                    'name': 'Google MCP Server',
                    'version': '1.0.0'
                }
            }
        }

    def tools_list_handler(self, req_id: int, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tools/list request"""
        tools = [
            {
                'name': 'read_emails',
                'description': 'Read recent emails from Gmail',
                'inputSchema': {
                    'type': 'object',
                    'properties': {
                        'max_results': {
                            'type': 'integer',
                            'description': 'Maximum number of emails to fetch'
                        },
                        'query': {
                            'type': 'string',
                            'description': 'Gmail search query'
                        }
                    },
                    'required': []
                }
            },
            {
                'name': 'create_calendar_event',
                'description': 'Create a new calendar event',
                'inputSchema': {
                    'type': 'object',
                    'properties': {
                        'summary': {
                            'type': 'string',
                            'description': 'Event title'
                        },
                        'start_time': {
                            'type': 'string',
                            'description': 'Start time in ISO 8601 format'
                        },
                        'end_time': {
                            'type': 'string',
                            'description': 'End time in ISO 8601 format'
                        },
                        'description': {
                            'type': 'string',
                            'description': 'Event description'
                        }
                    },
                    'required': ['summary', 'start_time', 'end_time']
                }
            },
            {
                'name': 'update_calendar_event',
                'description': 'Update an existing calendar event',
                'inputSchema': {
                    'type': 'object',
                    'properties': {
                        'event_id': {
                            'type': 'string',
                            'description': 'ID of event to update'
                        },
                        'summary': {
                            'type': 'string',
                            'description': 'Event title'
                        },
                        'description': {
                            'type': 'string',
                            'description': 'Event description'
                        },
                        'start_time': {
                            'type': 'string',
                            'description': 'Start time in ISO 8601 format'
                        },
                        'end_time': {
                            'type': 'string',
                            'description': 'End time in ISO 8601 format'
                        }
                    },
                    'required': ['event_id']
                }
            },
            {
                'name': 'delete_calendar_event',
                'description': 'Delete a calendar event',
                'inputSchema': {
                    'type': 'object',
                    'properties': {
                        'event_id': {
                            'type': 'string',
                            'description': 'ID of event to delete'
                        }
                    },
                    'required': ['event_id']
                }
            },
            {
                'name': 'get_calendar_events',
                'description': 'Get upcoming calendar events',
                'inputSchema': {
                    'type': 'object',
                    'properties': {
                        'max_results': {
                            'type': 'integer',
                            'description': 'Number of events to fetch'
                        },
                        'time_min': {
                            'type': 'string',
                            'description': 'Earliest time in ISO 8601 format'
                        }
                    },
                    'required': []
                }
            }
        ]
        
        return {
            'jsonrpc': '2.0',
            'id': req_id,
            'result': {
                'tools': tools
            }
        }

    @staticmethod
    def error_response(req_id: int, code: int, message: str) -> Dict[str, Any]:
        """Generate a proper JSON-RPC error response"""
        return {
            'jsonrpc': '2.0',
            'id': req_id,
            'error': {
                'code': code,
                'message': message
            }
        }
    
    def run(self):
        """Start the MCP server"""
        logger.info("Google MCP Server started")
        
        try:
            for line in sys.stdin:
                line = line.strip()
                if not line:
                    continue
                
                try:
                    request = json.loads(line)
                    response = self.handle_request(request)
                    if response:  # Only send if there's a response
                        print(json.dumps(response), flush=True)
                
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON: {e}")
                    # Don't send parse error response - just skip
                    pass
        
        except KeyboardInterrupt:
            logger.info("Server stopped by user")
        except Exception as e:
            logger.exception(f"Unexpected error: {e}")
            raise

if __name__ == '__main__':
    try:
        server = MCPServer()
        server.run()
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
        sys.exit(0)
    except Exception as e:
        logger.critical(f"Server initialization failed: {e}", exc_info=True)
        sys.exit(1)