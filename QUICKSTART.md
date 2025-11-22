# Quick Start Guide

## 1. Install Dependencies

```bash
pip install -r requirements.txt
```

## 2. Create Google Cloud Credentials

1. Visit https://console.cloud.google.com/
2. Create a new project
3. Search for and enable:
   - **Gmail API**
   - **Google Calendar API**
4. Create OAuth 2.0 Desktop Client credentials
5. Download the JSON file and save as `credentials.json`

## 3. Run the Server

```bash
python3 mcp_google_server.py
```

First run will open a browser asking for authorization. Grant access and you'll be good to go!

## 4. Test It

In a new terminal:

```bash
python3 test_mcp.py
```

This will:
- Initialize the server
- List available tools
- Read your 3 most recent emails
- Show your next 5 calendar events
- Create a test calendar event

## 5. Integrate with Claude

Once the server is running, configure it in Claude's MCP settings to connect to this server.

## Files Included

- **mcp_google_server.py** - Main MCP server (no frameworks, pure Python)
- **requirements.txt** - Python dependencies
- **test_mcp.py** - Test client for manual testing
- **SETUP.md** - Detailed setup and reference documentation

## Available Tools

### Reading Emails
```json
{
  "name": "read_emails",
  "arguments": {
    "max_results": 10,
    "query": "is:unread"
  }
}
```

### Creating Events
```json
{
  "name": "create_calendar_event",
  "arguments": {
    "summary": "My Event",
    "start_time": "2025-10-27T10:00:00",
    "end_time": "2025-10-27T11:00:00",
    "description": "Optional description"
  }
}
```

### Getting Events
```json
{
  "name": "get_calendar_events",
  "arguments": {
    "max_results": 10
  }
}
```

### Updating Events
```json
{
  "name": "update_calendar_event",
  "arguments": {
    "event_id": "abc123xyz",
    "summary": "Updated Title",
    "start_time": "2025-10-27T15:00:00"
  }
}
```

### Deleting Events
```json
{
  "name": "delete_calendar_event",
  "arguments": {
    "event_id": "abc123xyz"
  }
}
```

## Troubleshooting

**"credentials.json not found"**
- Download it from Google Cloud Console

**"Gmail API not enabled"**
- Enable it in Google Cloud Console → APIs & Services

**"Permission denied"**
- Delete `token.pickle` and re-authorize in the browser

**"No email/events show up"**
- Make sure the dummy account has emails and calendar events

## Next Steps

- Extend with more Gmail features (labels, attachments, etc.)
- Add support for other Google APIs (Drive, Sheets, etc.)
- Integrate with Claude for automated workflows
- Deploy as a persistent service