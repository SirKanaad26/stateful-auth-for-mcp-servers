#!/usr/bin/env python3
"""
Simple test client for the Google MCP Server
Useful for testing server functionality without Claude
"""

import json
import subprocess
import sys
from datetime import datetime, timedelta

class MCPClient:
    """Simple client for testing the MCP server"""
    
    def __init__(self, server_script: str = 'mcp_google_server.py'):
        self.server_script = server_script
        self.request_id = 0
    
    def send_request(self, method: str, params: dict = None) -> dict:
        """Send a request to the MCP server and get response"""
        self.request_id += 1
        
        request = {
            'jsonrpc': '2.0',
            'method': method,
            'id': self.request_id
        }
        
        if params:
            request['params'] = params
        
        try:
            proc = subprocess.Popen(
                [sys.executable, self.server_script],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            stdout, stderr = proc.communicate(
                input=json.dumps(request) + '\n',
                timeout=30
            )
            
            if stderr:
                print(f"[Server Logs]\n{stderr}", file=sys.stderr)
            
            if stdout:
                return json.loads(stdout.strip())
            else:
                return {'error': 'No response from server'}
        
        except subprocess.TimeoutExpired:
            proc.kill()
            return {'error': 'Request timeout'}
        except Exception as e:
            return {'error': str(e)}
    
    def initialize(self) -> bool:
        """Initialize the server"""
        print("🔧 Initializing server...")
        result = self.send_request('initialize')
        
        if 'result' in result:
            print(f"✅ Server initialized: {result['result']['serverInfo']['name']}")
            return True
        else:
            print(f"❌ Initialization failed: {result}")
            return False
    
    def list_tools(self) -> list:
        """List available tools"""
        print("\n📋 Listing tools...")
        result = self.send_request('tools/list')
        
        if 'result' in result:
            tools = result['result']['tools']
            for tool in tools:
                print(f"  - {tool['name']}: {tool['description']}")
            return tools
        else:
            print(f"❌ Failed to list tools: {result}")
            return []
    
    def read_emails(self, max_results: int = 5, query: str = "") -> dict:
        """Read recent emails"""
        print(f"\n📧 Reading {max_results} emails...")
        
        result = self.send_request('tools/call', {
            'name': 'read_emails',
            'arguments': {
                'max_results': max_results,
                'query': query
            }
        })
        
        return result
    
    def get_calendar_events(self, max_results: int = 5) -> dict:
        """Get upcoming calendar events"""
        print(f"\n📅 Getting {max_results} upcoming events...")
        
        result = self.send_request('tools/call', {
            'name': 'get_calendar_events',
            'arguments': {
                'max_results': max_results
            }
        })
        
        return result
    
    def create_event(self, summary: str, start_time: str, end_time: str, 
                    description: str = "") -> dict:
        """Create a calendar event"""
        print(f"\n➕ Creating event: {summary}")
        
        result = self.send_request('tools/call', {
            'name': 'create_calendar_event',
            'arguments': {
                'summary': summary,
                'start_time': start_time,
                'end_time': end_time,
                'description': description
            }
        })
        
        return result
    
    def print_json_response(self, response: dict):
        """Pretty print JSON response"""
        print(json.dumps(response, indent=2, default=str))

def main():
    """Run test suite"""
    client = MCPClient()
    
    # Step 1: Initialize
    if not client.initialize():
        sys.exit(1)
    
    # Step 2: List tools
    client.list_tools()
    
    # Step 3: Read emails
    print("\n" + "="*60)
    print("TEST 1: Reading Emails")
    print("="*60)
    response = client.read_emails(max_results=3)
    client.print_json_response(response)
    
    # Step 4: Get calendar events
    print("\n" + "="*60)
    print("TEST 2: Getting Calendar Events")
    print("="*60)
    response = client.get_calendar_events(max_results=5)
    client.print_json_response(response)
    
    # Step 5: Create a test event
    print("\n" + "="*60)
    print("TEST 3: Creating Calendar Event")
    print("="*60)
    
    now = datetime.utcnow()
    start = (now + timedelta(hours=1)).isoformat()
    end = (now + timedelta(hours=2)).isoformat()
    
    response = client.create_event(
        summary="MCP Test Event",
        start_time=start,
        end_time=end,
        description="This is a test event created by the MCP test client"
    )
    client.print_json_response(response)
    
    print("\n✅ Test suite completed!")

if __name__ == '__main__':
    main()