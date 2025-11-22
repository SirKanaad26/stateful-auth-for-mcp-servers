#!/usr/bin/env python3
"""
Integration Example: Using MCP Server with Stateful Authentication

This script demonstrates how to interact with the MCP server
and shows the authentication layer in action.
"""

import json
import sys

def create_json_rpc_request(method, params, request_id):
    """Create a JSON-RPC 2.0 request"""
    return {
        "jsonrpc": "2.0",
        "method": method,
        "params": params,
        "id": request_id
    }

def print_section(title):
    """Print a formatted section header"""
    print("\n" + "="*80)
    print(f" {title}")
    print("="*80 + "\n")

def main():
    """
    Demonstrates the MCP server usage with authentication examples
    
    NOTE: This is a demonstration script showing the request format.
    To actually run these requests, pipe them to mcp_server.py:
        echo '{"jsonrpc":"2.0",...}' | python3 mcp_server.py
    """
    
    print_section("MCP Server with Stateful Authentication - Integration Examples")
    
    # Example 1: Initialize the server
    print_section("Example 1: Initialize Server")
    init_request = create_json_rpc_request(
        "initialize",
        {
            "protocolVersion": "2025-06-18",
            "capabilities": {},
            "clientInfo": {
                "name": "test_client",
                "version": "1.0.0"
            }
        },
        1
    )
    print("Request:")
    print(json.dumps(init_request, indent=2))
    print("\nExpected Response: Server capabilities and info")
    
    # Example 2: List available tools
    print_section("Example 2: List Available Tools")
    list_request = create_json_rpc_request("tools/list", {}, 2)
    print("Request:")
    print(json.dumps(list_request, indent=2))
    print("\nExpected Response: List of all available tools")
    
    # Example 3: Create a calendar event (ALLOWED)
    print_section("Example 3: Create Calendar Event (✅ ALLOWED)")
    create_request = create_json_rpc_request(
        "tools/call",
        {
            "name": "create_calendar_event",
            "arguments": {
                "summary": "Team Standup",
                "start_time": "2025-11-15T09:00:00Z",
                "end_time": "2025-11-15T09:30:00Z",
                "description": "Daily team standup meeting"
            }
        },
        3
    )
    print("Request:")
    print(json.dumps(create_request, indent=2))
    print("\n✅ Authorization: ALLOWED (Create operations are always allowed)")
    print("📝 State Update: Event ID will be added to auth_state.json")
    print("Expected Response: Event details including event ID")
    
    # Example 4: Delete MCP-created event (ALLOWED)
    print_section("Example 4: Delete MCP-Created Event (✅ ALLOWED)")
    delete_mcp_request = create_json_rpc_request(
        "tools/call",
        {
            "name": "delete_calendar_event",
            "arguments": {
                "event_id": "event_created_by_mcp_123"  # Assume this was created by MCP
            }
        },
        4
    )
    print("Request:")
    print(json.dumps(delete_mcp_request, indent=2))
    print("\n✅ Authorization: ALLOWED (Event exists in state)")
    print("🔍 Verification: Auth layer checks if event_id is in auth_state.json")
    print("📝 State Update: Event ID will be removed from auth_state.json")
    print("Expected Response: Success confirmation")
    
    # Example 5: Delete external event (DENIED)
    print_section("Example 5: Delete External Event (❌ DENIED)")
    delete_external_request = create_json_rpc_request(
        "tools/call",
        {
            "name": "delete_calendar_event",
            "arguments": {
                "event_id": "external_event_not_created_by_mcp"
            }
        },
        5
    )
    print("Request:")
    print(json.dumps(delete_external_request, indent=2))
    print("\n❌ Authorization: DENIED (Event not in state)")
    print("🔍 Verification: Auth layer checks - event_id NOT in auth_state.json")
    print("🚫 No API Call: Request blocked before reaching Google Calendar API")
    print("📝 State Update: No changes")
    print("\nExpected Response:")
    print(json.dumps({
        "jsonrpc": "2.0",
        "id": 5,
        "result": {
            "content": [{
                "type": "text",
                "text": json.dumps({
                    "error": "Authorization denied",
                    "reason": "Event external_event_not_created_by_mcp was not created by MCP and cannot be deleted",
                    "tool": "delete_calendar_event",
                    "status": "DENIED"
                }, indent=2)
            }],
            "isError": True
        }
    }, indent=2))
    
    # Example 6: Get calendar events (ALLOWED)
    print_section("Example 6: Get Calendar Events (✅ ALLOWED)")
    get_events_request = create_json_rpc_request(
        "tools/call",
        {
            "name": "get_calendar_events",
            "arguments": {
                "max_results": 10
            }
        },
        6
    )
    print("Request:")
    print(json.dumps(get_events_request, indent=2))
    print("\n✅ Authorization: ALLOWED (Read operations are always allowed)")
    print("📝 State Update: No changes")
    print("Expected Response: List of upcoming calendar events")
    
    # Example 7: Read emails (ALLOWED)
    print_section("Example 7: Read Emails (✅ ALLOWED)")
    read_emails_request = create_json_rpc_request(
        "tools/call",
        {
            "name": "read_emails",
            "arguments": {
                "max_results": 5,
                "query": "is:unread"
            }
        },
        7
    )
    print("Request:")
    print(json.dumps(read_emails_request, indent=2))
    print("\n✅ Authorization: ALLOWED (Read operations are always allowed)")
    print("📝 State Update: No changes")
    print("Expected Response: List of recent emails")
    
    # Summary
    print_section("Authorization Summary")
    print("""
    Operation                  | Authorization Rule
    ---------------------------|---------------------------------------
    create_calendar_event      | ✅ Always ALLOWED → Adds to state
    delete_calendar_event      | ✅ ALLOWED if event in state
                              | ❌ DENIED if event not in state
    update_calendar_event      | ✅ Always ALLOWED → No state change
    get_calendar_events        | ✅ Always ALLOWED → No state change
    read_emails                | ✅ Always ALLOWED → No state change
    
    Security Benefits:
    🔒 Prevents accidental deletion of external calendar events
    💾 State persists across server restarts (auth_state.json)
    📝 Complete audit trail with timestamps
    🚫 Clear error messages when operations are denied
    """)
    
    print_section("How to Use These Examples")
    print("""
    Method 1: Pipe single request to server
    ----------------------------------------
    echo '{"jsonrpc":"2.0","method":"tools/list","params":{},"id":1}' | python3 mcp_server.py
    
    Method 2: Interactive session (stdin/stdout)
    -------------------------------------------
    python3 mcp_server.py
    # Then type JSON-RPC requests line by line
    
    Method 3: Use with MCP client
    ----------------------------
    Configure your MCP client to use this server:
    {
      "mcpServers": {
        "google": {
          "command": "python3",
          "args": ["mcp_server.py"]
        }
      }
    }
    
    Method 4: Test the auth layer independently
    ------------------------------------------
    python3 test_auth_layer.py
    """)
    
    print_section("Next Steps")
    print("""
    1. Start the MCP server:
       python3 mcp_server.py
    
    2. Test authentication:
       python3 test_auth_layer.py
    
    3. Create a calendar event and note the event ID
    
    4. Try to delete it (should succeed)
    
    5. Try to delete an event not created by MCP (should fail)
    
    6. Check auth_state.json to see the tracked events
    """)
    
    print("\n" + "="*80 + "\n")

if __name__ == '__main__':
    main()
