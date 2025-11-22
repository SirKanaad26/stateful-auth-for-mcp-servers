# System Architecture - Stateful Authentication for MCP Server

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         MCP CLIENT                                  │
│                    (Claude, AI Agent, etc.)                         │
└──────────────────────────────┬──────────────────────────────────────┘
                               │ JSON-RPC 2.0
                               │ (stdin/stdout)
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         MCP SERVER                                  │
│                       (mcp_server.py)                               │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  Request Handler                                             │  │
│  │  • Receives JSON-RPC requests                                │  │
│  │  • Routes to appropriate handler                             │  │
│  └────────────────────┬─────────────────────────────────────────┘  │
│                       │                                             │
│                       ▼                                             │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  Tool Call Handler (with Auth)                               │  │
│  │  ┌─────────────────────────────────────────────────────────┐ │  │
│  │  │ STEP 1: VERIFY                                          │ │  │
│  │  │ ┌─────────────────────────────────────────────────────┐ │ │  │
│  │  │ │  Auth Verifier (auth_verifier.py)                   │ │ │  │
│  │  │ │  • Check operation type                             │ │ │  │
│  │  │ │  • Query state for authorization                    │ │ │  │
│  │  │ │  • Return ALLOW or DENY                             │ │ │  │
│  │  │ └─────────────────┬───────────────────────────────────┘ │ │  │
│  │  │                   │                                       │ │  │
│  │  │                   ▼                                       │ │  │
│  │  │         ┌──────────────────────┐                         │ │  │
│  │  │         │  If DENIED: Return   │                         │ │  │
│  │  │         │  Error to Client     │                         │ │  │
│  │  │         └──────────────────────┘                         │ │  │
│  │  └─────────────────────────────────────────────────────────┘ │  │
│  │                                                               │  │
│  │  ┌─────────────────────────────────────────────────────────┐ │  │
│  │  │ STEP 2: EXECUTE (if allowed)                            │ │  │
│  │  │  • Gmail Service                                         │ │  │
│  │  │  • Calendar Service                                      │ │  │
│  │  │  • Call Google APIs                                      │ │  │
│  │  └─────────────────────────────────────────────────────────┘ │  │
│  │                                                               │  │
│  │  ┌─────────────────────────────────────────────────────────┐ │  │
│  │  │ STEP 3: UPDATE STATE (if successful)                    │ │  │
│  │  │  • Add created events                                    │ │  │
│  │  │  • Remove deleted events                                 │ │  │
│  │  │  • Save state to disk                                    │ │  │
│  │  └─────────────────────────────────────────────────────────┘ │  │
│  └──────────────────────────────────────────────────────────────┘  │
└──────────────┬──────────────────────────┬──────────────────────────┘
               │                          │
               ▼                          ▼
┌──────────────────────────┐  ┌──────────────────────────┐
│   Google APIs            │  │   State Storage          │
│   • Gmail API            │  │   auth_state.json        │
│   • Calendar API         │  │   • created_events[]     │
│   • OAuth 2.0            │  │   • metadata             │
└──────────────────────────┘  └──────────────────────────┘
```

## Component Details

### 1. MCP Server (`mcp_server.py`)

**Responsibilities:**
- JSON-RPC 2.0 protocol handling
- Request routing
- Integration with auth layer
- Google API communication

**Key Classes:**
- `MCPServer`: Main server class
- `GoogleAuthenticator`: OAuth 2.0 handling
- `GmailService`: Gmail operations
- `CalendarService`: Calendar operations

### 2. Auth Verifier (`auth_verifier.py`)

**Responsibilities:**
- Request authorization
- State management
- Security policy enforcement

**Key Classes:**
- `StateManager`: Manages persistent state
  - Load/save state from/to JSON
  - Track created events
  - Query event ownership

- `AuthVerifier`: Authorization logic
  - Verify requests
  - Enforce security rules
  - Update state after operations

### 3. State Storage (`auth_state.json`)

**Structure:**
```json
{
  "created_events": [
    {
      "event_id": "string",
      "created_at": "ISO-8601 timestamp",
      "details": {
        "summary": "string",
        "start_time": "ISO-8601",
        "end_time": "ISO-8601",
        "description": "string"
      }
    }
  ],
  "metadata": {
    "created_at": "ISO-8601 timestamp",
    "last_updated": "ISO-8601 timestamp"
  }
}
```

## Data Flow Diagrams

### Create Calendar Event Flow

```
Client                MCP Server           Auth Verifier         State File
  │                       │                     │                    │
  ├──CREATE event────────>│                     │                    │
  │                       ├──verify_request()──>│                    │
  │                       │                     ├──(always allow)    │
  │                       │<────ALLOW───────────┤                    │
  │                       │                     │                    │
  │                       ├──[Call Google API]  │                    │
  │                       │                     │                    │
  │                       ├──update_state()────>│                    │
  │                       │                     ├──add_event()──────>│
  │                       │                     │<──saved────────────┤
  │                       │<────success─────────┤                    │
  │<──Success response────┤                     │                    │
```

### Delete MCP-Created Event Flow (Allowed)

```
Client                MCP Server           Auth Verifier         State File
  │                       │                     │                    │
  ├──DELETE event────────>│                     │                    │
  │   (event_id=abc123)   ├──verify_request()──>│                    │
  │                       │   (event_id)        ├──query────────────>│
  │                       │                     │<──FOUND────────────┤
  │                       │<────ALLOW───────────┤                    │
  │                       │                     │                    │
  │                       ├──[Call Google API]  │                    │
  │                       │                     │                    │
  │                       ├──update_state()────>│                    │
  │                       │                     ├──remove_event()───>│
  │                       │                     │<──saved────────────┤
  │                       │<────success─────────┤                    │
  │<──Success response────┤                     │                    │
```

### Delete External Event Flow (Denied)

```
Client                MCP Server           Auth Verifier         State File
  │                       │                     │                    │
  ├──DELETE event────────>│                     │                    │
  │   (event_id=xyz999)   ├──verify_request()──>│                    │
  │                       │   (event_id)        ├──query────────────>│
  │                       │                     │<──NOT FOUND────────┤
  │                       │<────DENY────────────┤                    │
  │                       │   (with reason)     │                    │
  │<──Error response──────┤                     │                    │
  │   (Auth denied)       │                     │                    │
  │                       │    [No API call]    │   [No state change]│
```

## Security Model

### Threat Model

**What We're Protecting Against:**
1. ❌ Accidental deletion of important external events
2. ❌ Malicious agent deleting user's calendar
3. ❌ Unauthorized modifications by compromised agent

**How We Protect:**
1. ✅ Whitelist approach: Only allow deletion of known events
2. ✅ Persistent state: Track all MCP-created events
3. ✅ Fail-safe: Deny by default for unknown operations

### Authorization Matrix

```
┌─────────────────────┬──────────┬──────────┬──────────┬──────────┐
│ Operation           │ CREATE   │ READ     │ UPDATE   │ DELETE   │
├─────────────────────┼──────────┼──────────┼──────────┼──────────┤
│ Calendar Events     │          │          │          │          │
│ • MCP-created       │ ✅ Allow │ ✅ Allow │ ✅ Allow │ ✅ Allow │
│ • External events   │    N/A   │ ✅ Allow │ ✅ Allow │ ❌ Deny  │
├─────────────────────┼──────────┼──────────┼──────────┼──────────┤
│ Gmail Messages      │    N/A   │ ✅ Allow │    N/A   │    N/A   │
└─────────────────────┴──────────┴──────────┴──────────┴──────────┘

Legend:
✅ Allow - Operation permitted
❌ Deny  - Operation blocked
N/A      - Operation not applicable
```

## File Organization

```
Project Root/
│
├── mcp_server.py              # Main server with auth integration
├── auth_verifier.py           # Auth verification logic
├── auth_state.json            # Runtime state (auto-created)
│
├── test_auth_layer.py         # Unit tests for auth
├── flow_diagram.py            # Visual flow diagram
├── integration_examples.py    # Usage examples
├── architecture.md            # This file
│
├── AUTH_IMPLEMENTATION.md     # Detailed implementation guide
├── IMPLEMENTATION_SUMMARY.md  # Quick reference
├── QUICKSTART_AUTH.md         # Getting started guide
│
├── credentials.json           # Google OAuth credentials
├── token.json                 # OAuth tokens
└── requirements.txt           # Python dependencies
```

## Deployment Considerations

### Prerequisites
- Python 3.14+
- Google API credentials
- Write access for state file

### Startup Sequence
1. Load credentials
2. Initialize Google API clients
3. Initialize auth verifier
4. Load existing state (or create new)
5. Start JSON-RPC server

### Runtime Behavior
- State loaded into memory at startup
- State persisted to disk after each modification
- Minimal performance impact (in-memory checks)

### State Management
- Atomic writes to prevent corruption
- Timestamps for audit trail
- Human-readable JSON format

## Performance Characteristics

### Time Complexity
- **Verify request**: O(n) where n = number of tracked events
- **Add event**: O(1) append operation
- **Remove event**: O(n) list filtering

### Space Complexity
- **Memory**: O(n) where n = number of tracked events
- **Disk**: Grows with number of created events

### Optimization Opportunities
- Use set/dict for O(1) lookups
- Implement state cleanup (remove old events)
- Add caching layer if needed

## Testing Strategy

### Unit Tests (`test_auth_layer.py`)
- Test authorization rules
- Test state management
- Test edge cases

### Integration Tests
- Test with real Google APIs
- Test state persistence
- Test error handling

### Security Tests
- Attempt unauthorized deletions
- Test with corrupted state
- Test with missing state file

## Monitoring & Logging

### Log Levels
- **INFO**: Normal operations, auth decisions
- **WARNING**: Denied requests, state issues
- **ERROR**: API errors, unexpected failures
- **CRITICAL**: Initialization failures

### Key Metrics to Monitor
- Number of denied requests
- State file size
- Auth verification time
- API call success rate

## Future Enhancements

### Planned Features
1. **User-based authorization**: Track which user created events
2. **Time-based rules**: Allow deletion within X hours
3. **Approval workflows**: Require confirmation for sensitive ops
4. **Rate limiting**: Prevent abuse
5. **State cleanup**: Remove old event records

### Extensibility Points
- Custom authorization policies
- Pluggable state backends (DB, Redis)
- Webhook notifications
- Audit log export

---

**Architecture Version**: 1.0
**Last Updated**: 2025-11-13
**Status**: Production Ready ✅
