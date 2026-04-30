# Stateful Authentication Layer - Implementation Guide

## Overview

This document describes the stateful authentication layer added to the MCP Server to protect sensitive calendar operations. The authentication layer ensures that **only calendar events created by the MCP server can be deleted**, preventing accidental or malicious deletion of external calendar events.

## Architecture

The authentication system consists of three main components:

### 1. **State Manager** (`auth_verifier.py` - `StateManager` class)
- Maintains a persistent record of all calendar events created by the MCP
- Stores state in `auth_state.json` file
- Provides methods to add, remove, and query event records

### 2. **Auth Verifier** (`auth_verifier.py` - `AuthVerifier` class)
- Verifies if operations are allowed based on the current state
- Implements the authorization logic:
  - **CREATE operations**: Always allowed
  - **DELETE operations**: Only allowed for MCP-created events
  - **READ/UPDATE operations**: Always allowed

### 3. **MCP Server Integration** (`mcp_server.py`)
- Integrates the auth verifier into the request handling flow
- Follows a three-step process for each tool call:
  1. **Verify** the request
  2. **Execute** the tool (if allowed)
  3. **Update** the state (if successful)

## Request Flow

```
┌─────────────────────────────────────────────────────────────┐
│                        MCP Server                            │
│                                                              │
│  1. Tool Call Request                                        │
│      ↓                                                       │
│  2. Auth Verifier: verify_request()                         │
│      ├─ Check tool type                                     │
│      ├─ For DELETE: Check if event in state                 │
│      └─ Return ALLOW or DENY                                │
│      ↓                                                       │
│  3. If DENIED: Return error to client                       │
│      ↓                                                       │
│  4. If ALLOWED: Execute tool call                           │
│      ↓                                                       │
│  5. If successful: update_state_after_success()             │
│      ├─ For CREATE: Add event to state                      │
│      └─ For DELETE: Remove event from state                 │
│      ↓                                                       │
│  6. Return result to client                                 │
└─────────────────────────────────────────────────────────────┘
```

## State Structure

The state is stored in `auth_state.json`:

```json
{
  "created_events": [
    {
      "event_id": "abc123xyz",
      "created_at": "2025-11-13T10:30:00.000000",
      "details": {
        "summary": "Team Meeting",
        "start_time": "2025-11-15T10:00:00Z",
        "end_time": "2025-11-15T11:00:00Z",
        "description": "Quarterly planning"
      }
    }
  ],
  "metadata": {
    "created_at": "2025-11-13T10:00:00.000000",
    "last_updated": "2025-11-13T10:30:00.000000"
  }
}
```

## Authorization Rules

| Operation | Authorization Rule | State Update |
|-----------|-------------------|--------------|
| `create_calendar_event` | Always allowed | Add event to state |
| `delete_calendar_event` | Only if event ID exists in state | Remove event from state |
| `update_calendar_event` | Always allowed | No state change |
| `get_calendar_events` | Always allowed | No state change |
| `read_emails` | Always allowed | No state change |

## Usage Examples

### Example 1: Creating an Event (Allowed)

**Request:**
```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "create_calendar_event",
    "arguments": {
      "summary": "Team Meeting",
      "start_time": "2025-11-15T10:00:00Z",
      "end_time": "2025-11-15T11:00:00Z"
    }
  },
  "id": 1
}
```

**Result:**
- ✅ Request is allowed
- Event is created in Google Calendar
- Event ID is added to state
- Success response returned

### Example 2: Deleting MCP-Created Event (Allowed)

**Request:**
```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "delete_calendar_event",
    "arguments": {
      "event_id": "abc123xyz"
    }
  },
  "id": 2
}
```

**Assumptions:**
- Event `abc123xyz` exists in state (was created by MCP)

**Result:**
- ✅ Request is allowed (event found in state)
- Event is deleted from Google Calendar
- Event ID is removed from state
- Success response returned

### Example 3: Deleting External Event (Denied)

**Request:**
```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "delete_calendar_event",
    "arguments": {
      "event_id": "external_event_999"
    }
  },
  "id": 3
}
```

**Assumptions:**
- Event `external_event_999` does NOT exist in state (was not created by MCP)

**Result:**
- ❌ Request is denied
- No API call is made
- State is not modified
- Error response returned:
```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "result": {
    "content": [{
      "type": "text",
      "text": "{
        \"error\": \"Authorization denied\",
        \"reason\": \"Event external_event_999 was not created by MCP and cannot be deleted\",
        \"tool\": \"delete_calendar_event\",
        \"status\": \"DENIED\"
      }"
    }],
    "isError": true
  }
}
```

## Testing

### Running the Test Script

Test the authentication layer independently:

```bash
python test_auth_layer.py
```

This will run through various scenarios and show how the auth layer behaves.

### Testing with the MCP Server

1. Start the MCP server:
```bash
python mcp_server.py
```

2. Send create event request - should succeed
3. Try to delete the created event - should succeed
4. Try to delete an event not created by MCP - should fail

## Key Features

### ✅ Security Benefits

1. **Prevents Unauthorized Deletions**: Only events created by the MCP can be deleted
2. **Persistent State**: State survives server restarts
3. **Audit Trail**: All created events are logged with timestamps
4. **Fail-Safe**: Unknown operations are denied by default

### ✅ Operational Benefits

1. **Non-Intrusive**: CREATE and READ operations work normally
2. **Transparent**: Clear error messages when operations are denied
3. **Maintainable**: State is stored in human-readable JSON format
4. **Extensible**: Easy to add more authorization rules

## File Structure

```
Threat-model-for-Stateful-Auth/
├── mcp_server.py           # MCP server with integrated auth
├── auth_verifier.py        # Authentication verification logic
├── auth_state.json         # State file (created at runtime)
├── test_auth_layer.py      # Test script for auth layer
└── AUTH_IMPLEMENTATION.md  # This file
```

## Implementation Details

### Changes to `mcp_server.py`

1. **Import the verifier module:**
   ```python
   from auth_verifier import create_verifier, AuthVerifier
   ```

2. **Initialize verifier in `MCPServer.__init__`:**
   ```python
   self.auth_verifier = create_verifier()
   ```

3. **Update `tools_call_handler` method:**
   - Added verification step before execution
   - Added state update after successful execution
   - Added error handling for denied requests

### `auth_verifier.py` Components

1. **`StateManager` class:**
   - `_load_state()`: Load state from file
   - `save_state()`: Persist state to file
   - `add_created_event()`: Record new event
   - `is_event_created_by_mcp()`: Check if event exists
   - `remove_event()`: Delete event record

2. **`AuthVerifier` class:**
   - `verify_request()`: Main authorization logic
   - `update_state_after_success()`: Update state after tool execution

## Extending the System

### Adding New Authorization Rules

To add rules for other operations, modify `AuthVerifier.verify_request()`:

```python
def verify_request(self, tool_name: str, tool_input: Dict[str, Any]) -> Tuple[bool, str]:
    # Example: Restrict updates to MCP-created events only
    if tool_name == 'update_calendar_event':
        event_id = tool_input.get('event_id')
        if not self.state_manager.is_event_created_by_mcp(event_id):
            return False, "Can only update MCP-created events"
        return True, "Update allowed"
    
    # ... existing rules ...
```

### Adding More State Information

To track additional information, modify the event record structure:

```python
event_record = {
    'event_id': event_id,
    'created_at': datetime.utcnow().isoformat(),
    'created_by': 'mcp_server',  # New field
    'source': 'api_call',         # New field
    'details': event_details
}
```

## Troubleshooting

### State file not found
- Normal on first run - will be created automatically
- Check write permissions in the directory

### State not persisting
- Check if `save_state()` is called after modifications
- Verify file is not locked by another process

### Auth verifier not working
- Check logs for detailed error messages
- Verify `auth_verifier.py` is in the same directory as `mcp_server.py`

## Future Enhancements

Potential improvements to consider:

1. **User-Based Authorization**: Track which user/agent created each event
2. **Time-Based Rules**: Allow deletion only within X hours of creation
3. **Approval Workflows**: Require confirmation for sensitive operations
4. **Audit Logging**: Detailed logs of all authorization decisions
5. **State Cleanup**: Periodically remove old event records
6. **Backup/Recovery**: Automatic state backups

## Conclusion

The stateful authentication layer provides a robust mechanism to control calendar operations based on event ownership. It follows the principle of least privilege by only allowing deletion of events created by the MCP server itself, preventing potential security issues and accidental data loss.
