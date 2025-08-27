"""
MCP Toolbox Client for ADK Integration
Handles service account authentication and toolset loading
"""

import os
import logging
from typing import Dict, Any, List, Optional, Callable
from google.auth import default
from google.auth.transport.requests import Request
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ServiceAccountAuthProvider:
    """Provides service account authentication for MCP Toolbox"""
    
    def __init__(self, project_id: str = None):
        """
        Initialize service account auth provider
        
        Args:
            project_id: Google Cloud project ID
        """
        self.project_id = project_id or os.getenv("GOOGLE_CLOUD_PROJECT")
        self.credentials = None
        self.token = None
        
        if not self.project_id:
            raise ValueError("Google Cloud project ID must be provided")
        
        self._initialize_credentials()
    
    def _initialize_credentials(self):
        """Initialize service account credentials"""
        try:
            # Get default credentials (service account from environment)
            self.credentials, _ = default(
                scopes=['https://www.googleapis.com/auth/cloud-platform']
            )
            
            # Refresh to get initial token
            request = Request()
            self.credentials.refresh(request)
            self.token = self.credentials.token
            
            logger.info(f"Service account credentials initialized for project: {self.project_id}")
            
        except Exception as e:
            logger.error(f"Failed to initialize service account credentials: {e}")
            raise
    
    def get_auth_token(self) -> str:
        """Get current authentication token, refreshing if needed"""
        try:
            if not self.credentials.valid:
                request = Request()
                self.credentials.refresh(request)
                self.token = self.credentials.token
                logger.debug("Service account token refreshed")
            
            return self.token
            
        except Exception as e:
            logger.error(f"Failed to get auth token: {e}")
            raise
    
    def get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers for MCP Toolbox requests"""
        token = self.get_auth_token()
        return {
            "Authorization": f"Bearer {token}",
            "X-Agent-ID": "travel_advisor_agent",
            "X-Google-Cloud-Project": self.project_id
        }


class ADKToolboxClient:
    """MCP Toolbox client for ADK integration with service account auth"""
    
    def __init__(self, 
                 toolbox_url: str = "http://localhost:5000",
                 project_id: str = None):
        """
        Initialize ADK Toolbox client
        
        Args:
            toolbox_url: URL of the MCP Toolbox server
            project_id: Google Cloud project ID
        """
        self.toolbox_url = toolbox_url
        self.project_id = project_id or os.getenv("GOOGLE_CLOUD_PROJECT")
        
        # Initialize service account auth
        self.auth_provider = ServiceAccountAuthProvider(self.project_id)
        
        # Client will be initialized when needed
        self.sync_client = None
        self.async_client = None
        
        logger.info(f"ADK Toolbox client initialized for: {toolbox_url}")
        logger.info("Note: Make sure MCP Toolbox server is running with tools.yaml")
    
    def get_sync_client(self):
        """Get synchronous MCP Toolbox client with authentication"""
        if self.sync_client is None:
            try:
                from toolbox_core import ToolboxSyncClient
                
                # Create client with dynamic auth headers
                # Pass headers as dict instead of callable to avoid session issues
                auth_headers = self.auth_provider.get_auth_headers()
                
                self.sync_client = ToolboxSyncClient(
                    self.toolbox_url,
                    client_headers=auth_headers
                )
                
                logger.info("Synchronous Toolbox client created")
                
            except ImportError:
                logger.error("toolbox_core not installed. Run: pip install toolbox_core")
                raise
            except Exception as e:
                logger.error(f"Failed to create sync client: {e}")
                raise
        
        return self.sync_client
    
    async def get_async_client(self):
        """Get asynchronous MCP Toolbox client with authentication"""
        if self.async_client is None:
            try:
                from toolbox_core import ToolboxClient
                
                # Create async client with dynamic auth headers  
                self.async_client = ToolboxClient(
                    self.toolbox_url,
                    client_headers=self.auth_provider.get_auth_headers
                )
                
                logger.info("Asynchronous Toolbox client created")
                
            except ImportError:
                logger.error("toolbox_core not installed. Run: pip install toolbox_core")
                raise
            except Exception as e:
                logger.error(f"Failed to create async client: {e}")
                raise
        
        return self.async_client
    
    def load_travel_toolset(self, toolset_name: str = "travel-database"):
        """Load travel database toolset with authentication"""
        try:
            client = self.get_sync_client()
            
            # Don't use context manager here - let the tools manage their own sessions
            tools = client.load_toolset(toolset_name)
            logger.info(f"Loaded toolset '{toolset_name}' with {len(tools)} tools")
            return tools
                
        except Exception as e:
            logger.error(f"Failed to load toolset '{toolset_name}': {e}")
            return []
    
    def load_travel_tool(self, tool_name: str):
        """Load a specific travel database tool"""
        try:
            client = self.get_sync_client()
            
            # Don't use context manager - let the tool manage its session
            tool = client.load_tool(tool_name)
            logger.info(f"Loaded tool '{tool_name}'")
            return tool
                
        except Exception as e:
            logger.error(f"Failed to load tool '{tool_name}': {e}")
            return None
    
    async def load_travel_toolset_async(self, toolset_name: str = "travel-database"):
        """Async version of load_travel_toolset"""
        try:
            client = await self.get_async_client()
            
            async with client:
                tools = await client.load_toolset(toolset_name)
                logger.info(f"Loaded toolset '{toolset_name}' with {len(tools)} tools")
                return tools
                
        except Exception as e:
            logger.error(f"Failed to load toolset '{toolset_name}': {e}")
            return []


class MockToolboxClient:
    """Mock MCP Toolbox client for development/testing when Toolbox server isn't available"""
    
    def __init__(self, database_service):
        """
        Initialize mock client with database service
        
        Args:
            database_service: TravelDatabaseService instance
        """
        self.database_service = database_service
        logger.info("Mock Toolbox client initialized (using direct database service)")
    
    def create_mock_tools(self) -> List[Dict[str, Any]]:
        """Create mock tools that wrap database service methods"""
        
        def search_destinations_tool(user_id: str = "default_user", 
                                   budget_category: str = "",
                                   region: str = "", 
                                   category: str = "",
                                   season: str = "",
                                   limit: int = 10) -> str:
            """Search for travel destinations"""
            try:
                results = self.database_service.search_destinations(
                    user_id=user_id,
                    budget_category=budget_category if budget_category else None,
                    region=region if region else None,
                    category=category if category else None,
                    season=season if season else None,
                    limit=limit
                )
                
                if not results:
                    return "No destinations found matching your criteria."
                
                response = f"Found {len(results)} destinations:\n\n"
                for dest in results:
                    response += f"🌍 **{dest['name']}, {dest['country']}**\n"
                    response += f"   Category: {dest['category']}\n"
                    response += f"   Region: {dest['region']}\n"
                    response += f"   Best Season: {dest['best_season']}\n"
                    response += f"   Budget: {dest['budget_category']}\n"
                    response += f"   Description: {dest['description']}\n\n"
                
                return response
                
            except Exception as e:
                return f"Error searching destinations: {str(e)}"
        
        def save_preferences_tool(user_id: str,
                                preferences_json: str,
                                session_id: str = "default_session") -> str:
            """Save user travel preferences"""
            try:
                preferences = json.loads(preferences_json)
                success = self.database_service.save_user_preferences(
                    user_id=user_id,
                    preferences=preferences,
                    session_id=session_id
                )
                
                if success:
                    return f"✅ Saved preferences for user {user_id}: {list(preferences.keys())}"
                else:
                    return "❌ Failed to save preferences"
                    
            except Exception as e:
                return f"Error saving preferences: {str(e)}"
        
        def get_preferences_tool(user_id: str) -> str:
            """Get user travel preferences"""
            try:
                preferences = self.database_service.get_user_preferences(user_id)
                
                if not preferences:
                    return f"No preferences found for user {user_id}"
                
                response = f"User preferences for {user_id}:\n\n"
                for pref_type, pref_value in preferences.items():
                    response += f"• {pref_type}: {pref_value}\n"
                
                return response
                
            except Exception as e:
                return f"Error getting preferences: {str(e)}"
        
        # Return mock tools as function objects
        tools = [
            {
                "name": "search_destinations",
                "description": "Search for travel destinations based on criteria",
                "function": search_destinations_tool,
                "parameters": {
                    "user_id": {"type": "string", "description": "User identifier"},
                    "budget_category": {"type": "string", "description": "Budget category (budget, mid_range, luxury)"},
                    "region": {"type": "string", "description": "Geographic region"},
                    "category": {"type": "string", "description": "Destination category (beach, mountain, city, cultural)"},
                    "season": {"type": "string", "description": "Best travel season"},
                    "limit": {"type": "integer", "description": "Maximum number of results"}
                }
            },
            {
                "name": "save_user_preferences", 
                "description": "Save user travel preferences",
                "function": save_preferences_tool,
                "parameters": {
                    "user_id": {"type": "string", "description": "User identifier"},
                    "preferences_json": {"type": "string", "description": "JSON string of preferences"},
                    "session_id": {"type": "string", "description": "Session identifier"}
                }
            },
            {
                "name": "get_user_preferences",
                "description": "Get user travel preferences",
                "function": get_preferences_tool,
                "parameters": {
                    "user_id": {"type": "string", "description": "User identifier"}
                }
            }
        ]
        
        logger.info(f"Created {len(tools)} mock database tools")
        return tools


def create_adk_toolbox_client(toolbox_url: str = "http://localhost:5000") -> ADKToolboxClient:
    """Factory function to create ADK Toolbox client"""
    return ADKToolboxClient(toolbox_url=toolbox_url)


def create_mock_toolbox_client() -> MockToolboxClient:
    """Factory function to create mock Toolbox client for development"""
    from .database_tools import get_travel_database_service
    
    db_service = get_travel_database_service()
    return MockToolboxClient(database_service=db_service)


if __name__ == "__main__":
    # Test the Toolbox client
    print("Testing ADK Toolbox Client...")
    
    try:
        # Test service account authentication
        auth_provider = ServiceAccountAuthProvider()
        headers = auth_provider.get_auth_headers()
        print(f"✅ Service account auth working. Project: {auth_provider.project_id}")
        
        # Test mock client (since Toolbox server may not be running)
        print("\nTesting mock Toolbox client...")
        mock_client = create_mock_toolbox_client()
        tools = mock_client.create_mock_tools()
        
        print(f"✅ Mock client created with {len(tools)} tools:")
        for tool in tools:
            print(f"  - {tool['name']}: {tool['description']}")
        
        # Test a mock tool
        search_tool = tools[0]["function"]
        result = search_tool(
            user_id="test_user",
            budget_category="budget", 
            category="beach",
            limit=2
        )
        print(f"\n📊 Sample search result:\n{result}")
        
    except Exception as e:
        print(f"❌ Error testing Toolbox client: {e}")