#!/usr/bin/env python3
"""
Stateful Authentication Verification Program
Verifies if operations are allowed based on the current state
"""

import json
import logging
import os
from typing import Dict, Any, Tuple
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class StateManager:
    """Manages the state of calendar events created by the MCP server"""
    
    def __init__(self, state_file: str = 'auth_state.json'):
        """Initialize the state manager"""
        script_dir = os.path.dirname(os.path.abspath(__file__))
        self.state_file = os.path.join(script_dir, state_file)
        self.state = self._load_state()
    
    def _load_state(self) -> Dict[str, Any]:
        """Load state from file or create new state"""
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, 'r') as f:
                    state = json.load(f)
                    logger.info(f"Loaded state with {len(state.get('created_events', []))} events")
                    return state
            except Exception as e:
                logger.error(f"Error loading state file: {e}")
                return self._create_empty_state()
        else:
            logger.info("No existing state file, creating new state")
            return self._create_empty_state()
    
    def _create_empty_state(self) -> Dict[str, Any]:
        """Create an empty state structure"""
        return {
            'created_events': [],  # List of event IDs created by the MCP
            'metadata': {
                'created_at': datetime.utcnow().isoformat(),
                'last_updated': datetime.utcnow().isoformat()
            }
        }
    
    def save_state(self) -> None:
        """Save state to file"""
        try:
            self.state['metadata']['last_updated'] = datetime.utcnow().isoformat()
            with open(self.state_file, 'w') as f:
                json.dump(self.state, f, indent=2)
            logger.info(f"State saved with {len(self.state.get('created_events', []))} events")
        except Exception as e:
            logger.error(f"Error saving state: {e}")
            raise
    
    def add_created_event(self, event_id: str, event_details: Dict[str, Any]) -> None:
        """Add a newly created event to the state"""
        event_record = {
            'event_id': event_id,
            'created_at': datetime.utcnow().isoformat(),
            'details': event_details
        }
        self.state['created_events'].append(event_record)
        logger.info(f"Added event {event_id} to state")
    
    def is_event_created_by_mcp(self, event_id: str) -> bool:
        """Check if an event was created by the MCP server"""
        created_ids = [event['event_id'] for event in self.state.get('created_events', [])]
        is_created = event_id in created_ids
        logger.info(f"Event {event_id} created by MCP: {is_created}")
        return is_created
    
    def remove_event(self, event_id: str) -> None:
        """Remove an event from the state (after successful deletion)"""
        self.state['created_events'] = [
            event for event in self.state['created_events'] 
            if event['event_id'] != event_id
        ]
        logger.info(f"Removed event {event_id} from state")
    
    def get_all_created_events(self) -> list:
        """Get all events created by the MCP"""
        return self.state.get('created_events', [])


class AuthVerifier:
    """Verifies if operations are allowed based on the current state"""
    
    def __init__(self, state_manager: StateManager):
        """Initialize the verifier with a state manager"""
        self.state_manager = state_manager
    
    def verify_request(self, tool_name: str, tool_input: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Verify if a tool call is allowed
        
        Args:
            tool_name: Name of the tool being called
            tool_input: Input parameters for the tool
        
        Returns:
            Tuple of (is_allowed, reason)
        """
        logger.info(f"Verifying request: tool={tool_name}, input={tool_input}")
        
        # CREATE operations are always allowed
        if tool_name == 'create_calendar_event':
            logger.info("CREATE operation - ALLOWED by default")
            return True, "Create operations are allowed by default"
        
        # DELETE operations require verification
        if tool_name == 'delete_calendar_event':
            event_id = tool_input.get('event_id')
            
            if not event_id:
                logger.warning("DELETE operation - DENIED (no event_id provided)")
                return False, "Event ID is required for delete operations"
            
            # Check if the event was created by the MCP
            if self.state_manager.is_event_created_by_mcp(event_id):
                logger.info(f"DELETE operation for {event_id} - ALLOWED (event created by MCP)")
                return True, f"Event {event_id} was created by MCP and can be deleted"
            else:
                logger.warning(f"DELETE operation for {event_id} - DENIED (event not created by MCP)")
                return False, f"Event {event_id} was not created by MCP and cannot be deleted"
        
        # UPDATE and READ operations are allowed by default
        # (You can add more granular controls here if needed)
        if tool_name in ['update_calendar_event', 'get_calendar_events', 'read_emails']:
            logger.info(f"{tool_name} operation - ALLOWED by default")
            return True, f"{tool_name} operations are allowed by default"
        
        # Unknown operations are denied by default
        logger.warning(f"Unknown operation {tool_name} - DENIED by default")
        return False, f"Unknown operation {tool_name} is not allowed"
    
    def update_state_after_success(self, tool_name: str, tool_input: Dict[str, Any], 
                                   result: Any) -> None:
        """
        Update state after a successful tool call
        
        Args:
            tool_name: Name of the tool that was called
            tool_input: Input parameters that were used
            result: Result returned by the tool
        """
        logger.info(f"Updating state after successful {tool_name}")
        
        # Add created events to state
        if tool_name == 'create_calendar_event':
            if isinstance(result, dict) and 'id' in result:
                event_id = result['id']
                event_details = {
                    'summary': tool_input.get('summary'),
                    'start_time': tool_input.get('start_time'),
                    'end_time': tool_input.get('end_time'),
                    'description': tool_input.get('description', '')
                }
                self.state_manager.add_created_event(event_id, event_details)
                self.state_manager.save_state()
                logger.info(f"State updated with new event {event_id}")
        
        # Remove deleted events from state
        elif tool_name == 'delete_calendar_event':
            event_id = tool_input.get('event_id')
            if event_id:
                self.state_manager.remove_event(event_id)
                self.state_manager.save_state()
                logger.info(f"State updated - removed event {event_id}")


def create_verifier() -> AuthVerifier:
    """Factory function to create a new verifier instance"""
    state_manager = StateManager()
    verifier = AuthVerifier(state_manager)
    return verifier


# For testing purposes
if __name__ == '__main__':
    # Test the verifier
    verifier = create_verifier()
    
    # Test: Allow create
    print("\n=== Test 1: Create Event (should allow) ===")
    allowed, reason = verifier.verify_request('create_calendar_event', {
        'summary': 'Test Event',
        'start_time': '2025-11-15T10:00:00Z',
        'end_time': '2025-11-15T11:00:00Z'
    })
    print(f"Allowed: {allowed}, Reason: {reason}")
    
    # Simulate successful creation
    print("\n=== Simulating successful event creation ===")
    verifier.update_state_after_success('create_calendar_event', {
        'summary': 'Test Event',
        'start_time': '2025-11-15T10:00:00Z',
        'end_time': '2025-11-15T11:00:00Z'
    }, {'id': 'test_event_123', 'summary': 'Test Event'})
    
    # Test: Delete created event (should allow)
    print("\n=== Test 2: Delete MCP-created Event (should allow) ===")
    allowed, reason = verifier.verify_request('delete_calendar_event', {
        'event_id': 'test_event_123'
    })
    print(f"Allowed: {allowed}, Reason: {reason}")
    
    # Test: Delete non-created event (should deny)
    print("\n=== Test 3: Delete Non-MCP Event (should deny) ===")
    allowed, reason = verifier.verify_request('delete_calendar_event', {
        'event_id': 'external_event_456'
    })
    print(f"Allowed: {allowed}, Reason: {reason}")
    
    print("\n=== All Tests Complete ===")
    print(f"Current state: {len(verifier.state_manager.get_all_created_events())} events tracked")
