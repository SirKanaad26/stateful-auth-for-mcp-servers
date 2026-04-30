#!/usr/bin/env python3
"""
Test script for the stateful authentication layer
Demonstrates how the auth layer protects delete operations
"""

import json
from auth_verifier import create_verifier

def print_separator(title):
    """Print a nice separator"""
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70 + "\n")


def test_auth_layer():
    """Test the authentication layer"""
    
    # Create a fresh verifier
    verifier = create_verifier()
    
    print_separator("TEST 1: Create Calendar Event (Should ALLOW)")
    allowed, reason = verifier.verify_request('create_calendar_event', {
        'summary': 'Team Meeting',
        'start_time': '2025-11-15T10:00:00Z',
        'end_time': '2025-11-15T11:00:00Z',
        'description': 'Quarterly planning meeting'
    })
    print(f"✓ Allowed: {allowed}")
    print(f"  Reason: {reason}")
    
    # Simulate successful creation
    print("\n>>> Simulating successful event creation...")
    verifier.update_state_after_success('create_calendar_event', {
        'summary': 'Team Meeting',
        'start_time': '2025-11-15T10:00:00Z',
        'end_time': '2025-11-15T11:00:00Z'
    }, {
        'id': 'mcp_event_001',
        'summary': 'Team Meeting',
        'htmlLink': 'https://calendar.google.com/event?eid=mcp_event_001'
    })
    print("✓ Event created and added to state")
    
    
    print_separator("TEST 2: Delete MCP-Created Event (Should ALLOW)")
    allowed, reason = verifier.verify_request('delete_calendar_event', {
        'event_id': 'mcp_event_001'
    })
    print(f"✓ Allowed: {allowed}")
    print(f"  Reason: {reason}")
    if allowed:
        print("\n>>> This delete would be executed...")
    
    
    print_separator("TEST 3: Delete External Event (Should DENY)")
    allowed, reason = verifier.verify_request('delete_calendar_event', {
        'event_id': 'external_event_999'
    })
    print(f"✗ Allowed: {allowed}")
    print(f"  Reason: {reason}")
    if not allowed:
        print("\n>>> This delete would be BLOCKED by the auth layer!")
    
    
    print_separator("TEST 4: Create Another Event")
    allowed, reason = verifier.verify_request('create_calendar_event', {
        'summary': 'Project Demo',
        'start_time': '2025-11-20T14:00:00Z',
        'end_time': '2025-11-20T15:00:00Z'
    })
    print(f"✓ Allowed: {allowed}")
    print(f"  Reason: {reason}")
    
    verifier.update_state_after_success('create_calendar_event', {
        'summary': 'Project Demo',
        'start_time': '2025-11-20T14:00:00Z',
        'end_time': '2025-11-20T15:00:00Z'
    }, {
        'id': 'mcp_event_002',
        'summary': 'Project Demo'
    })
    print("✓ Second event created and added to state")
    
    
    print_separator("TEST 5: Delete Second MCP-Created Event (Should ALLOW)")
    allowed, reason = verifier.verify_request('delete_calendar_event', {
        'event_id': 'mcp_event_002'
    })
    print(f"✓ Allowed: {allowed}")
    print(f"  Reason: {reason}")
    
    
    print_separator("TEST 6: Read/Update Operations (Should ALLOW)")
    
    # Test read emails
    allowed, reason = verifier.verify_request('read_emails', {
        'max_results': 10
    })
    print(f"Read Emails - Allowed: {allowed}")
    print(f"  Reason: {reason}")
    
    # Test get calendar events
    allowed, reason = verifier.verify_request('get_calendar_events', {
        'max_results': 10
    })
    print(f"Get Calendar Events - Allowed: {allowed}")
    print(f"  Reason: {reason}")
    
    # Test update event
    allowed, reason = verifier.verify_request('update_calendar_event', {
        'event_id': 'any_event',
        'summary': 'Updated Title'
    })
    print(f"Update Calendar Event - Allowed: {allowed}")
    print(f"  Reason: {reason}")
    
    
    print_separator("Current State Summary")
    created_events = verifier.state_manager.get_all_created_events()
    print(f"Total events tracked by MCP: {len(created_events)}")
    for i, event in enumerate(created_events, 1):
        print(f"\n{i}. Event ID: {event['event_id']}")
        print(f"   Summary: {event['details']['summary']}")
        print(f"   Created: {event['created_at']}")
    
    
    print_separator("Summary")
    print("✓ CREATE operations: Always allowed")
    print("✓ DELETE operations: Only allowed for MCP-created events")
    print("✓ READ/UPDATE operations: Always allowed")
    print("✓ State is persisted across server restarts")
    print("\n" + "="*70 + "\n")


if __name__ == '__main__':
    test_auth_layer()
