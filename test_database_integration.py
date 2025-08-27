#!/usr/bin/env python3
"""
Test script for database integration with BigQuery
Tests service account authentication and database tools
"""

import os
import sys
import asyncio
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add agent module to path
sys.path.insert(0, str(Path(__file__).parent))

async def test_database_service():
    """Test the TravelDatabaseService with BigQuery"""
    print("🔧 Testing TravelDatabaseService...")
    
    try:
        from agent.database_tools import TravelDatabaseService, initialize_travel_database
        
        # Test database service initialization
        print(f"📊 Project: {os.getenv('GOOGLE_CLOUD_PROJECT')}")
        print(f"🔐 Credentials: {os.getenv('GOOGLE_APPLICATION_CREDENTIALS')}")
        
        # Initialize database
        print("\n1. Initializing database...")
        success = initialize_travel_database()
        if success:
            print("✅ Database initialized successfully")
        else:
            print("❌ Database initialization failed")
            return False
        
        # Test database operations
        db_service = TravelDatabaseService()
        
        print("\n2. Testing destination search...")
        destinations = db_service.search_destinations(
            user_id="test_user",
            budget_category="budget",
            category="beach",
            limit=3
        )
        
        if destinations:
            print(f"✅ Found {len(destinations)} destinations:")
            for dest in destinations[:2]:  # Show first 2
                print(f"  - {dest['name']}, {dest['country']}")
        else:
            print("ℹ️ No destinations found (expected if tables are empty)")
        
        print("\n3. Testing user preferences...")
        prefs = {
            "budget": "mid_range",
            "preferred_season": "spring",
            "activities": ["hiking", "sightseeing"]
        }
        
        success = db_service.save_user_preferences(
            user_id="test_user",
            preferences=prefs,
            session_id="test_session"
        )
        
        if success:
            print("✅ Preferences saved successfully")
            
            # Retrieve preferences
            retrieved_prefs = db_service.get_user_preferences("test_user")
            print(f"✅ Retrieved preferences: {list(retrieved_prefs.keys())}")
        else:
            print("❌ Failed to save preferences")
        
        return True
        
    except Exception as e:
        print(f"❌ Database service test failed: {e}")
        return False

async def test_toolbox_client():
    """Test the MCP Toolbox client"""
    print("\n🔧 Testing MCP Toolbox Client...")
    
    try:
        from agent.mcp_toolbox_client import ServiceAccountAuthProvider, create_mock_toolbox_client
        
        # Test service account authentication
        print("\n1. Testing service account authentication...")
        auth_provider = ServiceAccountAuthProvider()
        headers = auth_provider.get_auth_headers()
        
        print(f"✅ Auth headers created:")
        print(f"  - Project: {headers.get('X-Google-Cloud-Project')}")
        print(f"  - Agent ID: {headers.get('X-Agent-ID')}")
        print(f"  - Has Authorization: {'Authorization' in headers}")
        
        # Test mock toolbox client
        print("\n2. Testing mock Toolbox client...")
        mock_client = create_mock_toolbox_client()
        tools = mock_client.create_mock_tools()
        
        print(f"✅ Created {len(tools)} mock tools:")
        for tool in tools:
            print(f"  - {tool['name']}: {tool['description'][:50]}...")
        
        # Test a mock tool function
        print("\n3. Testing mock tool function...")
        search_tool = tools[0]["function"]  # search_destinations
        result = search_tool(
            user_id="test_user",
            budget_category="budget",
            category="beach",
            limit=2
        )
        
        print(f"✅ Mock tool result:\n{result[:200]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ Toolbox client test failed: {e}")
        return False

async def test_agent_tools():
    """Test the integrated agent tools"""
    print("\n🔧 Testing Agent Tools Integration...")
    
    try:
        from agent.tools import get_travel_tools, search_destinations_with_context
        
        print("\n1. Loading travel tools...")
        tools = get_travel_tools()
        
        print(f"✅ Loaded {len(tools)} travel tools:")
        for tool in tools:
            print(f"  - {tool.name}: {tool.description[:50]}...")
        
        # Test enhanced search function
        print("\n2. Testing enhanced destination search...")
        result = search_destinations_with_context(
            user_id="test_user",
            query="I want cheap beach destinations for summer vacation",
            limit=2
        )
        
        print(f"✅ Enhanced search result:\n{result[:300]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ Agent tools test failed: {e}")
        return False

async def test_bigquery_permissions():
    """Test BigQuery permissions and connectivity"""
    print("\n🔧 Testing BigQuery Permissions...")
    
    try:
        from google.cloud import bigquery
        from google.auth import default
        
        # Initialize BigQuery client
        credentials, project = default()
        client = bigquery.Client(project=project, credentials=credentials)
        
        print(f"✅ BigQuery client created for project: {project}")
        
        # Test basic query
        query = "SELECT 1 as test_value"
        query_job = client.query(query)
        results = list(query_job.result())
        
        if results and results[0].test_value == 1:
            print("✅ BigQuery permissions working - can execute queries")
        
        # Test dataset access
        dataset_id = "travel_data"
        dataset_ref = f"{project}.{dataset_id}"
        
        try:
            dataset = client.get_dataset(dataset_ref)
            print(f"✅ Dataset {dataset_id} exists and is accessible")
        except Exception:
            print(f"ℹ️ Dataset {dataset_id} doesn't exist yet (will be created)")
        
        return True
        
    except Exception as e:
        print(f"❌ BigQuery permissions test failed: {e}")
        return False

async def main():
    """Run all tests"""
    print("🚀 Starting Database Integration Tests")
    print("=" * 50)
    
    # Check environment
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
    credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    
    if not project_id:
        print("❌ GOOGLE_CLOUD_PROJECT not set")
        return False
    
    if not credentials_path or not os.path.exists(credentials_path):
        print("❌ GOOGLE_APPLICATION_CREDENTIALS not set or file doesn't exist")
        return False
    
    print(f"📋 Environment Check:")
    print(f"  - Project: {project_id}")
    print(f"  - Credentials: {credentials_path}")
    print("")
    
    # Run tests
    tests = [
        ("BigQuery Permissions", test_bigquery_permissions),
        ("Database Service", test_database_service),
        ("Toolbox Client", test_toolbox_client),
        ("Agent Tools", test_agent_tools)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "="*50)
    print("🎯 Test Summary:")
    print("="*50)
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
        if result:
            passed += 1
    
    print(f"\n📊 Results: {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        print("\n🎉 All tests passed! Your database integration is ready.")
        print("\n💡 Next steps:")
        print("1. Set up your BigQuery dataset: 'travel_data'")
        print("2. Test with ADK web interface")
        print("3. Try asking: 'Find me budget beach destinations'")
    else:
        print(f"\n⚠️ Some tests failed. Please check the errors above.")
    
    return passed == len(results)

if __name__ == "__main__":
    asyncio.run(main())