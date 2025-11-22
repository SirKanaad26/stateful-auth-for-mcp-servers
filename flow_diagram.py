"""
Visual representation of the stateful authentication flow
"""

def print_flow_diagram():
    print("""
╔══════════════════════════════════════════════════════════════════════════╗
║                    STATEFUL AUTHENTICATION FLOW                          ║
╚══════════════════════════════════════════════════════════════════════════╝

┌─────────────────────────────────────────────────────────────────────────┐
│                          CLIENT REQUEST                                  │
│  Example: Delete Calendar Event with ID "xyz789"                        │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                          MCP SERVER                                      │
│  Receives JSON-RPC request via stdin                                    │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
                                 ▼
╔═════════════════════════════════════════════════════════════════════════╗
║                    STEP 1: VERIFICATION                                 ║
║                                                                         ║
║  ┌─────────────────────────────────────────────────────────┐           ║
║  │  Auth Verifier: verify_request()                        │           ║
║  │  • Check tool_name = "delete_calendar_event"            │           ║
║  │  • Extract event_id = "xyz789"                          │           ║
║  │  • Query state: Is "xyz789" in created_events?          │           ║
║  └──────────────────────────┬──────────────────────────────┘           ║
║                             │                                           ║
║              ┌──────────────┴──────────────┐                           ║
║              ▼                              ▼                           ║
║         ┌─────────┐                   ┌─────────┐                      ║
║         │  FOUND  │                   │NOT FOUND│                      ║
║         │ IN STATE│                   │IN STATE │                      ║
║         └────┬────┘                   └────┬────┘                      ║
║              │                              │                           ║
║              ▼                              ▼                           ║
║       ✅ ALLOW                        ❌ DENY                           ║
║       Return True                     Return False                     ║
╚══════════════╪═════════════════════════════╪═══════════════════════════╝
               │                              │
               │                              ▼
               │                      ┌───────────────────┐
               │                      │ Return Error to   │
               │                      │ Client:           │
               │                      │ "Event not        │
               │                      │ created by MCP"   │
               │                      └───────────────────┘
               │                              │
               ▼                              ▼
╔═════════════════════════════════════════════════════════════════════════╗
║                    STEP 2: EXECUTION (if allowed)                       ║
║                                                                         ║
║  ┌─────────────────────────────────────────────────────────┐           ║
║  │  CalendarService.delete_event("xyz789")                 │           ║
║  │  • Make Google Calendar API call                        │           ║
║  │  • Delete event from user's calendar                    │           ║
║  └──────────────────────────┬──────────────────────────────┘           ║
║                             │                                           ║
║              ┌──────────────┴──────────────┐                           ║
║              ▼                              ▼                           ║
║         ┌─────────┐                   ┌─────────┐                      ║
║         │ SUCCESS │                   │ FAILURE │                      ║
║         └────┬────┘                   └────┬────┘                      ║
║              │                              │                           ║
║              ▼                              ▼                           ║
║       Proceed to Step 3            Return Error to Client              ║
╚══════════════╪═════════════════════════════════════════════════════════╝
               │
               ▼
╔═════════════════════════════════════════════════════════════════════════╗
║                    STEP 3: STATE UPDATE (if successful)                 ║
║                                                                         ║
║  ┌─────────────────────────────────────────────────────────┐           ║
║  │  Auth Verifier: update_state_after_success()            │           ║
║  │  • Remove "xyz789" from created_events list             │           ║
║  │  • Update metadata timestamp                            │           ║
║  │  • Save state to auth_state.json                        │           ║
║  └──────────────────────────┬──────────────────────────────┘           ║
║                             │                                           ║
║                             ▼                                           ║
║                    ✓ State Updated                                     ║
╚══════════════════════════════╪═════════════════════════════════════════╝
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    RETURN SUCCESS TO CLIENT                              │
│  JSON-RPC response with deletion confirmation                           │
└─────────────────────────────────────────────────────────────────────────┘


╔══════════════════════════════════════════════════════════════════════════╗
║                        STATE FILE STRUCTURE                              ║
╚══════════════════════════════════════════════════════════════════════════╝

    auth_state.json
    {
      "created_events": [
        {
          "event_id": "abc123",        ← Tracked for auth
          "created_at": "2025-11-13...",
          "details": {...}
        },
        {
          "event_id": "def456",        ← Tracked for auth
          "created_at": "2025-11-13...",
          "details": {...}
        }
      ],
      "metadata": {
        "created_at": "2025-11-13T10:00:00",
        "last_updated": "2025-11-13T10:30:00"
      }
    }


╔══════════════════════════════════════════════════════════════════════════╗
║                    AUTHORIZATION RULES SUMMARY                           ║
╚══════════════════════════════════════════════════════════════════════════╝

    ┌─────────────────────────┬──────────────────┬───────────────────┐
    │ Operation               │ Authorization    │ State Update      │
    ├─────────────────────────┼──────────────────┼───────────────────┤
    │ create_calendar_event   │ ✅ Always Allow  │ Add event to list │
    │ delete_calendar_event   │ ✅ If in state   │ Remove from list  │
    │                         │ ❌ If not in st. │ No change         │
    │ update_calendar_event   │ ✅ Always Allow  │ No change         │
    │ get_calendar_events     │ ✅ Always Allow  │ No change         │
    │ read_emails             │ ✅ Always Allow  │ No change         │
    └─────────────────────────┴──────────────────┴───────────────────┘


╔══════════════════════════════════════════════════════════════════════════╗
║                         KEY SECURITY FEATURES                            ║
╚══════════════════════════════════════════════════════════════════════════╝

    🔒 Prevents deletion of events not created by MCP
    💾 Persistent state across server restarts
    📝 Complete audit trail with timestamps
    🚫 Fail-safe: Unknown operations denied by default
    🔍 Transparent error messages for denied requests
    ⚡ Fast in-memory operations with disk persistence

""")

if __name__ == '__main__':
    print_flow_diagram()
