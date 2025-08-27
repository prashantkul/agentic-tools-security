#!/usr/bin/env python3
"""
Test MCP Toolbox workflow with BigQuery
Tests the complete integration: BigQuery → MCP Toolbox → ADK Agent
"""

import os
import sys
import asyncio
import subprocess
import time
from pathlib import Path
from dotenv import load_dotenv
import requests
import json

# Load environment variables
load_dotenv()

def check_prerequisites():
    """Check if all prerequisites are met"""
    print("🔍 Checking Prerequisites...")
    
    issues = []
    
    # Check environment variables
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
    credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    
    if not project_id:
        issues.append("❌ GOOGLE_CLOUD_PROJECT not set")
    else:
        print(f"✅ Project ID: {project_id}")
    
    if not credentials_path or not os.path.exists(credentials_path):
        issues.append("❌ GOOGLE_APPLICATION_CREDENTIALS not set or file missing")
    else:
        print(f"✅ Credentials: {credentials_path}")
    
    # Check tools.yaml exists
    tools_yaml = Path("tools.yaml")
    if not tools_yaml.exists():
        issues.append("❌ tools.yaml not found")
    else:
        print("✅ tools.yaml found")
    
    # Check toolbox-core installation
    try:
        import toolbox_core
        print("✅ toolbox-core installed")
    except ImportError:
        issues.append("❌ toolbox-core not installed (run: pip install toolbox-core)")
    
    # Check BigQuery permissions
    try:
        from google.cloud import bigquery
        from google.auth import default
        
        credentials, _ = default()
        client = bigquery.Client(project=project_id, credentials=credentials)
        
        # Simple test query
        query = "SELECT 1 as test"
        job = client.query(query)
        list(job.result())
        print("✅ BigQuery permissions working")
        
    except Exception as e:
        issues.append(f"❌ BigQuery permissions issue: {e}")
    
    return issues

def start_toolbox_server():
    """Start MCP Toolbox server in background"""
    print("\n🚀 Starting MCP Toolbox Server...")
    
    try:
        # Start toolbox server
        process = subprocess.Popen(
            ["toolbox", "serve", "--config", "tools.yaml", "--port", "5000"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Wait a bit for server to start
        print("⏳ Waiting for server to start...")
        time.sleep(5)
        
        # Check if server is running
        if process.poll() is None:
            print("✅ Toolbox server started (PID: {})".format(process.pid))
            return process
        else:
            stdout, stderr = process.communicate()
            print(f"❌ Toolbox server failed to start")
            print(f"STDOUT: {stdout}")
            print(f"STDERR: {stderr}")
            return None
            
    except FileNotFoundError:
        print("❌ 'toolbox' command not found. Install MCP Toolbox first.")
        return None
    except Exception as e:
        print(f"❌ Failed to start Toolbox server: {e}")
        return None

def test_toolbox_server():
    """Test if Toolbox server is responding"""
    print("\n🧪 Testing Toolbox Server...")
    
    try:
        # Test health endpoint
        response = requests.get("http://localhost:5000/health", timeout=5)
        if response.status_code == 200:
            print("✅ Toolbox server responding")
            return True
        else:
            print(f"❌ Server health check failed: {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to Toolbox server")
        return False
    except Exception as e:
        print(f"❌ Server test failed: {e}")
        return False

def test_toolbox_client():
    """Test MCP Toolbox client integration"""
    print("\n🔧 Testing Toolbox Client...")
    
    try:
        from toolbox_core import ToolboxSyncClient
        
        # Create client
        client = ToolboxSyncClient("http://localhost:5000")
        
        print("✅ Toolbox client created")
        
        # Test loading tools
        with client:
            tools = client.list_tools()
            print(f"✅ Available tools: {len(tools)}")
            
            for tool in tools[:3]:  # Show first 3 tools
                print(f"  - {tool}")
        
        return True
        
    except Exception as e:
        print(f"❌ Toolbox client test failed: {e}")
        return False

def test_bigquery_tools():
    """Test BigQuery tools through Toolbox"""
    print("\n📊 Testing BigQuery Tools...")
    
    try:
        from toolbox_core import ToolboxSyncClient
        
        client = ToolboxSyncClient("http://localhost:5000")
        
        with client:
            # Test search-destinations tool
            print("🔍 Testing search-destinations tool...")
            
            search_tool = client.load_tool("search-destinations")
            
            # Test with budget filter
            result = search_tool(
                budget_category="budget",
                limit=3
            )
            
            print("✅ Search tool executed")
            print(f"📋 Result: {len(result)} rows found")
            
            # Show sample results
            if result:
                for row in result[:2]:
                    print(f"  - {row.get('name', 'Unknown')}, {row.get('country', 'Unknown')}")
            
            # Test get-all-destinations tool
            print("\n🌍 Testing get-all-destinations tool...")
            
            all_dest_tool = client.load_tool("get-all-destinations")
            all_result = all_dest_tool(limit=5)
            
            print(f"✅ All destinations tool: {len(all_result)} results")
        
        return True
        
    except Exception as e:
        print(f"❌ BigQuery tools test failed: {e}")
        return False

def test_adk_integration():
    """Test ADK integration with Toolbox tools"""
    print("\n🤖 Testing ADK Integration...")
    
    try:
        from agent.mcp_toolbox_client import create_adk_toolbox_client
        
        # Create ADK Toolbox client
        adk_client = create_adk_toolbox_client("http://localhost:5000")
        
        print("✅ ADK Toolbox client created")
        
        # Test tool loading
        tools = adk_client.load_travel_toolset("travel-tools")  # Load all tools
        
        if tools:
            print(f"✅ Loaded {len(tools)} travel tools for ADK")
            
            # Test a tool
            # Note: This would be integrated with your actual ADK agent
            print("ℹ️ Tools ready for ADK agent integration")
        else:
            print("⚠️ No tools loaded (may need specific toolset name)")
        
        return True
        
    except Exception as e:
        print(f"❌ ADK integration test failed: {e}")
        return False

async def run_full_workflow_test():
    """Run complete workflow test"""
    print("\n🎯 Running Full Workflow Test...")
    
    # This would test the complete flow:
    # User query → ADK Agent → MCP Toolbox → BigQuery → Response
    
    try:
        # Simulate user query processing
        user_query = "Find me budget beach destinations in Southeast Asia"
        print(f"📝 User Query: {user_query}")
        
        # Extract parameters (this would be done by your agent)
        query_params = {
            "budget_category": "budget",
            "category": "beach", 
            "region": "Southeast Asia",
            "limit": 5
        }
        print(f"🧠 Extracted Parameters: {query_params}")
        
        # Call Toolbox (simulated)
        from toolbox_core import ToolboxSyncClient
        
        client = ToolboxSyncClient("http://localhost:5000")
        
        with client:
            search_tool = client.load_tool("search-destinations")
            results = search_tool(**query_params)
            
            print(f"📊 Query Results: {len(results)} destinations found")
            
            # Format response (this would be done by your agent)
            if results:
                response = f"I found {len(results)} great budget beach destinations in Southeast Asia:\n\n"
                for i, dest in enumerate(results, 1):
                    response += f"{i}. {dest.get('name', 'Unknown')} - {dest.get('description', 'No description')}\n"
                
                print("🎉 Formatted Response:")
                print(response[:200] + "..." if len(response) > 200 else response)
            else:
                print("ℹ️ No results found")
        
        return True
        
    except Exception as e:
        print(f"❌ Full workflow test failed: {e}")
        return False

def cleanup_server(process):
    """Clean up Toolbox server process"""
    if process and process.poll() is None:
        print("\n🧹 Cleaning up Toolbox server...")
        process.terminate()
        try:
            process.wait(timeout=5)
            print("✅ Server stopped cleanly")
        except subprocess.TimeoutExpired:
            process.kill()
            print("⚠️ Server force-killed")

async def main():
    """Main test function"""
    print("🚀 MCP Toolbox Workflow Test")
    print("=" * 50)
    
    # Check prerequisites
    issues = check_prerequisites()
    if issues:
        print("\n❌ Prerequisites not met:")
        for issue in issues:
            print(f"  {issue}")
        print("\n💡 Fix these issues and try again.")
        return False
    
    print("\n✅ All prerequisites met!")
    
    # Start Toolbox server
    server_process = start_toolbox_server()
    if not server_process:
        print("❌ Cannot proceed without Toolbox server")
        return False
    
    try:
        # Test server
        if not test_toolbox_server():
            return False
        
        # Test client
        if not test_toolbox_client():
            return False
        
        # Test BigQuery tools
        if not test_bigquery_tools():
            return False
        
        # Test ADK integration
        if not test_adk_integration():
            return False
        
        # Test full workflow
        if not await run_full_workflow_test():
            return False
        
        print("\n" + "=" * 50)
        print("🎉 ALL TESTS PASSED!")
        print("=" * 50)
        print("\n💡 Next Steps:")
        print("1. Your MCP Toolbox + BigQuery integration is working!")
        print("2. Start your ADK agent with: adk web")
        print("3. Test queries like: 'Find me luxury destinations for winter'")
        print("4. The agent will use BigQuery through MCP Toolbox automatically")
        
        return True
        
    finally:
        cleanup_server(server_process)

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)