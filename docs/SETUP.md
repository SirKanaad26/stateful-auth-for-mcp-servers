# Google MCP Server Setup Guide

This is a custom MCP (Model Context Protocol) server that provides access to Gmail and Google Calendar APIs.

## Prerequisites

- Python 3.8 or higher
- A Google account (dummy account recommended)
- pip package manager

## Setup Instructions

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Create Google Cloud Project and Get Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (e.g., "MCP Google Server")
3. Enable the following APIs:
   - Gmail API
   - Google Calendar API

4. Create OAuth 2.0 Desktop Application credentials:
   - Go to "Credentials" → "Create Credentials" → "OAuth 2.0 Client ID"
   - Choose "Desktop application"
   - Download the JSON file and save it as `credentials.json` in the same directory as `mcp_google_server.py`

### 3. Make the Server Executable

```bash
chmod +x mcp_google_server.py
```

### 4. Run the Server

```bash
python3 mcp_google_server.py
```

**First Run**: The script will open a browser window asking you to authorize access to Gmail and Calendar. After authorization, it will save a `token.pickle` file for future use.

## MCP Server Protocol

The server implements JSON-RPC 2.0 over stdin/stdout. Communication format:

### Initialize Request
```json
{"jsonrpc": "2.0", "method": "initialize", "id": 1}
```

### List Available Tools
```json
{"jsonrpc": "2.0", "method": "tools/list", "id": 2}
```

### Call a Tool
```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "read_emails",
    "arguments": {
      "max_results": 10,
      "query": ""
    }
  },
  "id": 3
}
```

## Available Tools

### 1. read_emails
Read recent emails from Gmail.

**Parameters:**
- `max_results` (integer, default: 10): Number of emails to fetch
- `query` (string, default: ""): Gmail search query (e.g., "from:someone@example.com", "is:unread")

**Example:**
```json
{
  "name": "read_emails",
  "arguments": {
    "max_results": 5,
    "query": "is:unread"
  }
}
```

### 2. create_calendar_event
Create a new calendar event.

**Parameters:**
- `summary` (string, required): Event title
- `start_time` (string, required): Start time in ISO 8601 format (e.g., "2025-10-26T10:00:00")
- `end_time` (string, required): End time in ISO 8601 format
- `description` (string, optional): Event description

**Example:**
```json
{
  "name": "create_calendar_event",
  "arguments": {
    "summary": "Team Meeting",
    "start_time": "2025-10-27T14:00:00",
    "end_time": "2025-10-27T15:00:00",
    "description": "Weekly sync with the team"
  }
}
```

### 3. update_calendar_event
Update an existing calendar event.

**Parameters:**
- `event_id` (string, required): ID of the event to update
- `summary` (string, optional): New event title
- `description` (string, optional): New event description
- `start_time` (string, optional): New start time
- `end_time` (string, optional): New end time

**Example:**
```json
{
  "name": "update_calendar_event",
  "arguments": {
    "event_id": "abc123",
    "summary": "Updated Meeting Title",
    "start_time": "2025-10-27T15:00:00"
  }
}
```

### 4. delete_calendar_event
Delete a calendar event.

**Parameters:**
- `event_id` (string, required): ID of the event to delete

**Example:**
```json
{
  "name": "delete_calendar_event",
  "arguments": {
    "event_id": "abc123"
  }
}
```

### 5. get_calendar_events
Get upcoming calendar events.

**Parameters:**
- `max_results` (integer, default: 10): Number of events to fetch
- `time_min` (string, optional): Earliest time in ISO 8601 format (default: now)

**Example:**
```json
{
  "name": "get_calendar_events",
  "arguments": {
    "max_results": 10
  }
}
```

## Testing the Server

### Using curl and stdin (manual testing)

```bash
# Start the server in one terminal
python3 mcp_google_server.py

# In another terminal, send requests
echo '{"jsonrpc": "2.0", "method": "initialize", "id": 1}' | nc localhost <port>
```

### Using Python test client

Create a test script (e.g., `test_mcp.py`):

```python
import json
import subprocess
import sys

def send_request(request):
    proc = subprocess.Popen(
        ['python3', 'mcp_google_server.py'],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    stdout, stderr = proc.communicate(
        input=json.dumps(request) + '\n'
    )
    
    if stdout:
        return json.loads(stdout)
    return None

# Test initialize
result = send_request({
    "jsonrpc": "2.0",
    "method": "initialize",
    "id": 1
})
print(json.dumps(result, indent=2))
```

## Configuration

### Timezone

The server uses UTC timezone by default. To change it, modify the `SCOPES` and calendar calls:

```python
'start': {'dateTime': start_time, 'timeZone': 'America/Los_Angeles'}
```

### Multiple Calendars

To access multiple calendars, modify the tool calls to accept a `calendar_id` parameter or list all calendars:

```python
def list_calendars(self):
    result = self.service.calendarList().list().execute()
    return result.get('items', [])
```

## Troubleshooting

### "credentials.json not found"
Make sure you've downloaded the OAuth 2.0 credentials from Google Cloud Console and saved them as `credentials.json`.

### "token.pickle is invalid"
Delete `token.pickle` and re-run the server to re-authenticate.

### Gmail API disabled
Enable the Gmail API in Google Cloud Console under "APIs & Services" → "Library".

### Calendar API disabled
Enable the Google Calendar API in Google Cloud Console under "APIs & Services" → "Library".

### "Permission denied"
Ensure your OAuth credentials have the following scopes:
- `https://www.googleapis.com/auth/gmail.readonly`
- `https://www.googleapis.com/auth/calendar`

## Integration with Claude

Once the server is running, you can configure it in Claude's MCP settings to use it directly. The server will handle all JSON-RPC communication automatically.

## Security Notes

- Keep `credentials.json` and `token.pickle` private and never commit them to version control
- Add them to `.gitignore`:
  ```
  credentials.json
  token.pickle
  *.pickle
  ```
- The server runs locally and communicates via stdin/stdout (no network exposure by default)

## Extending the Server

To add more features:

1. Add new methods to `GmailService` or `CalendarService` classes
2. Add corresponding tools in the `tools_list_handler` method
3. Handle the tool call in the `tools_call_handler` method

Example: Adding a method to mark emails as read

```python
def mark_email_as_read(self, message_id: str):
    self.service.users().messages().modify(
        userId='me',
        id=message_id,
        body={'removeLabelIds': ['UNREAD']}
    ).execute()
```

## License

This code is provided as-is for educational purposes.