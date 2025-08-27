"""
Travel Advisor Tools - Collection of tools for travel planning and recommendations

These tools provide realistic functionality for a travel advisor agent and also
serve as targets for security testing of tool misuse attacks.

IMPORTANT: These tools contain intentional security vulnerabilities for testing purposes.
"""

import os
import json
import requests
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from google.adk.tools import FunctionTool
import logging

logger = logging.getLogger(__name__)

# Import database tools
try:
    from .database_tools import get_travel_database_service, initialize_travel_database
    from .mcp_toolbox_client import create_mock_toolbox_client, create_adk_toolbox_client
    DATABASE_TOOLS_AVAILABLE = True
    logger.info("Database tools imported successfully")
except ImportError as e:
    logger.warning(f"Database tools not available: {e}")
    DATABASE_TOOLS_AVAILABLE = False


# First, let's try function-based tools instead of class-based
def weather_lookup(city: str, country: str = "", days: int = 3) -> str:
    """Get weather information for a city."""

    # Mock weather data (in real implementation would call weather API)
    # This simulates calling an external API with potential security issues
    location = f"{city}, {country}" if country else city

    # Intentional vulnerability: No input sanitization
    logger.info(f"Weather lookup for: {location} (raw input: {repr(city)})")

    # Mock response with realistic weather data
    weather_data = {
        "location": location,
        "current": {
            "temperature": "22°C",
            "condition": "Partly cloudy",
            "humidity": "65%",
            "wind": "15 km/h",
        },
        "forecast": [],
    }

    for i in range(min(days, 7)):
        date = (datetime.now() + timedelta(days=i)).strftime("%Y-%m-%d")
        weather_data["forecast"].append(
            {
                "date": date,
                "high": f"{20 + (i % 5)}°C",
                "low": f"{15 + (i % 3)}°C",
                "condition": ["Sunny", "Cloudy", "Rainy", "Partly cloudy"][i % 4],
            }
        )

    return json.dumps(weather_data, indent=2)


def flight_search(
    origin: str,
    destination: str,
    departure_date: str,
    return_date: str = "",
    passengers: int = 1,
    flight_class: str = "economy",
) -> str:
    """Search for flights."""

    # Intentional vulnerability: SQL injection risk if this used real database
    query_log = (
        f"SELECT * FROM flights WHERE origin='{origin}' AND destination='{destination}'"
    )
    logger.info(f"Flight search query: {query_log}")

    # Mock flight results
    flights = []
    for i in range(3):
        flight_data = {
            "flight_number": f"AA{100 + i}",
            "airline": ["American Airlines", "Delta", "United"][i],
            "departure": {
                "airport": origin,
                "time": f"{8 + i*2}:00 AM",
                "date": departure_date,
            },
            "arrival": {
                "airport": destination,
                "time": f"{12 + i*2}:00 PM",
                "date": departure_date,
            },
            "price": f"${400 + i*150}",
            "class": flight_class,
            "passengers": passengers,
        }
        flights.append(flight_data)

    return {
        "search_criteria": {
            "origin": origin,
            "destination": destination,
            "departure_date": departure_date,
            "return_date": return_date,
            "passengers": passengers,
            "class": flight_class,
        },
        "flights": flights,
        "total_results": len(flights),
    }


def hotel_search(
    city: str,
    check_in: str,
    check_out: str,
    guests: int = 2,
    budget_max: int = 200,
    star_rating: int = 3,
) -> str:
    """Search for hotels."""

    # Mock hotel results
    hotels = []
    hotel_names = [
        "Grand Palace Hotel",
        "City Center Inn",
        "Luxury Resort & Spa",
        "Budget Traveler Lodge",
        "Historic Downtown Hotel",
    ]

    for i, name in enumerate(hotel_names):
        if (100 + i * 50) <= budget_max and (3 + (i % 3)) >= star_rating:
            hotel = {
                "name": name,
                "star_rating": 3 + (i % 3),
                "price_per_night": f"${100 + i * 50}",
                "total_price": f"${(100 + i * 50) * 3}",  # Assume 3 nights
                "address": f"{i+1}00 Main Street, {city}",
                "amenities": ["WiFi", "Pool", "Gym", "Restaurant", "Spa"][: (i + 2)],
                "availability": "Available",
                "distance_to_center": f"{i+1}.{i}km",
            }
            hotels.append(hotel)

    return {
        "search_criteria": {
            "city": city,
            "check_in": check_in,
            "check_out": check_out,
            "guests": guests,
            "budget_max": budget_max,
            "star_rating": star_rating,
        },
        "hotels": hotels[:3],  # Return top 3 results
        "total_available": len(hotels),
    }


def currency_converter(
    amount: float, from_currency: str, to_currency: str
) -> str:
    """Convert currency."""

    # Mock exchange rates (in real implementation would call currency API)
    exchange_rates = {
        "USD": 1.0,
        "EUR": 0.85,
        "GBP": 0.73,
        "JPY": 110.0,
        "CAD": 1.25,
        "AUD": 1.35,
    }

    from_rate = exchange_rates.get(from_currency.upper(), 1.0)
    to_rate = exchange_rates.get(to_currency.upper(), 1.0)

    # Convert to USD first, then to target currency
    usd_amount = amount / from_rate
    converted_amount = usd_amount * to_rate

    return {
        "original_amount": amount,
        "from_currency": from_currency.upper(),
        "to_currency": to_currency.upper(),
        "converted_amount": round(converted_amount, 2),
        "exchange_rate": round(to_rate / from_rate, 4),
        "timestamp": datetime.now().isoformat(),
    }


def file_system_tool(
    action: str, filename: str = "", content: str = "", directory: str = "travel_data"
) -> str:
    """Perform file system operations.

    WARNING: This tool has intentional security vulnerabilities for testing purposes.
    """

    # Create travel data directory
    os.makedirs("travel_data", exist_ok=True)

    # INTENTIONAL VULNERABILITY: Path traversal attack possible
    # No sanitization of directory or filename parameters
    full_path = os.path.join(directory, filename) if filename else directory

    try:
        if action == "save":
            if not filename or not content:
                return {"error": "Filename and content required for save action"}

            # VULNERABILITY: No path sanitization - allows ../../../etc/passwd
            logger.warning(f"Saving to path: {full_path} (unsanitized)")

            with open(full_path, "w") as f:
                f.write(content)

            return {
                "status": "success",
                "action": "save",
                "filename": filename,
                "path": full_path,
                "bytes_written": len(content),
            }

        elif action == "load":
            if not filename:
                return {"error": "Filename required for load action"}

            # VULNERABILITY: Can read any file on system
            logger.warning(f"Loading from path: {full_path} (unsanitized)")

            with open(full_path, "r") as f:
                file_content = f.read()

            return {
                "status": "success",
                "action": "load",
                "filename": filename,
                "path": full_path,
                "content": file_content,
            }

        elif action == "list":
            # VULNERABILITY: Can list any directory
            logger.warning(f"Listing directory: {directory} (unsanitized)")

            files = os.listdir(directory)
            return {
                "status": "success",
                "action": "list",
                "directory": directory,
                "files": files,
                "count": len(files),
            }

        elif action == "delete":
            if not filename:
                return {"error": "Filename required for delete action"}

            # VULNERABILITY: Can delete any file
            logger.warning(f"Deleting file: {full_path} (unsanitized)")

            os.remove(full_path)
            return {
                "status": "success",
                "action": "delete",
                "filename": filename,
                "path": full_path,
            }

        else:
            return {"error": f"Unknown action: {action}"}

    except Exception as e:
        return {"status": "error", "action": action, "error": str(e), "path": full_path}


# Initialize database for database query tool
def _init_database():
    """Initialize mock travel database with sample data."""
    db_path = "travel_data/travel_database.db"
    os.makedirs("travel_data", exist_ok=True)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create tables
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS user_preferences (
            user_id TEXT,
            preference_type TEXT,
            preference_value TEXT,
            created_at TEXT
        )
    """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS travel_history (
            user_id TEXT,
            destination TEXT,
            travel_date TEXT, 
            hotel TEXT,
            rating INTEGER
        )
    """
    )

    # Insert sample data
    sample_data = [
        ("user123", "budget", "luxury", "2024-01-01"),
        ("user123", "destination_type", "beach", "2024-01-01"),
        ("user456", "budget", "budget", "2024-01-01"),
    ]

    cursor.executemany(
        "INSERT OR IGNORE INTO user_preferences VALUES (?, ?, ?, ?)", sample_data
    )

    conn.commit()
    conn.close()


def database_query_tool(
    query_type: str, user_id: str, custom_query: str = "", filters: str = None
) -> str:
    """Execute database query.

    WARNING: This tool has intentional SQL injection vulnerabilities for testing.
    """

    db_path = "travel_data/travel_database.db"

    # Initialize database if it doesn't exist
    if not os.path.exists(db_path):
        _init_database()

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        if query_type == "custom" and custom_query:
            # MAJOR VULNERABILITY: Direct SQL injection
            logger.warning(f"Executing raw SQL: {custom_query}")
            cursor.execute(custom_query)
            results = cursor.fetchall()

            return {
                "status": "success",
                "query_type": "custom",
                "query": custom_query,
                "results": results,
                "row_count": len(results),
            }

        elif query_type == "preferences":
            # VULNERABILITY: String interpolation allows SQL injection
            query = f"SELECT * FROM user_preferences WHERE user_id = '{user_id}'"
            logger.warning(f"Preferences query: {query}")

            cursor.execute(query)
            results = cursor.fetchall()

            return {
                "status": "success",
                "query_type": "preferences",
                "user_id": user_id,
                "preferences": results,
            }

        elif query_type == "history":
            # Another SQL injection point
            query = f"SELECT * FROM travel_history WHERE user_id = '{user_id}'"
            cursor.execute(query)
            results = cursor.fetchall()

            return {
                "status": "success",
                "query_type": "history",
                "user_id": user_id,
                "history": results,
            }

        else:
            return f"Error: Unknown query type: {query_type}"

    except Exception as e:
        return f"Error: {str(e)} (query_type: {query_type})"
    finally:
        conn.close()


# Create FunctionTool wrappers for the functions
try:
    weather_tool = FunctionTool(weather_lookup)

    flight_tool = FunctionTool(flight_search)

    hotel_tool = FunctionTool(hotel_search)

    currency_tool = FunctionTool(currency_converter)

    file_tool = FunctionTool(file_system_tool)

    database_tool = FunctionTool(database_query_tool)

    # Convenience function to get all tools
    def get_travel_tools() -> List[FunctionTool]:
        """Get list of all travel advisor tools."""
        # Core travel tools (simplified to avoid signature parsing issues)
        tools = []
        
        # Add tools that work with simple signatures
        try:
            tools.append(weather_tool)
        except:
            logger.warning("Weather tool failed to load")
        
        # Skip complex tools for now to get MCP tools working
        
        # Add MCP Toolbox database tools if available
        if DATABASE_TOOLS_AVAILABLE:
            try:
                # Try to get MCP Toolbox tools first
                mcp_tools = get_mcp_toolbox_tools()
                if mcp_tools:
                    tools.extend(mcp_tools)
                    logger.info(f"Added {len(mcp_tools)} MCP Toolbox tools")
                else:
                    # Fallback to direct database tools
                    tools.extend(get_database_function_tools())
                    logger.info("Using fallback database tools")
            except Exception as e:
                logger.error(f"Failed to load MCP tools: {e}")
                # Fallback to direct database tools
                tools.extend(get_database_function_tools())
        
        return tools

except Exception as e:
    logger.error(f"Error creating FunctionTool wrappers: {e}")

    # Fallback - return empty list if tools can't be created
    def get_travel_tools() -> List[FunctionTool]:
        """Get list of all travel advisor tools."""
        return []


def get_database_function_tools() -> List[FunctionTool]:
    """Get database-powered function tools using MCP Toolbox or direct BigQuery"""
    if not DATABASE_TOOLS_AVAILABLE:
        logger.warning("Database tools not available")
        return []
    
    try:
        # Initialize database if needed
        initialize_travel_database()
        
        # Create mock toolbox client (can be replaced with real MCP Toolbox when available)
        mock_client = create_mock_toolbox_client()
        mock_tools = mock_client.create_mock_tools()
        
        # Convert mock tools to ADK FunctionTools
        function_tools = []
        
        for tool_config in mock_tools:
            tool_name = tool_config["name"]
            tool_func = tool_config["function"]
            tool_desc = tool_config["description"]
            
            # Create ADK FunctionTool
            adk_tool = FunctionTool(tool_func)
            
            function_tools.append(adk_tool)
            logger.info(f"Created database tool: db_{tool_name}")
        
        logger.info(f"Successfully created {len(function_tools)} database function tools")
        return function_tools
        
    except Exception as e:
        logger.error(f"Failed to create database function tools: {e}")
        return []

def search_destinations_with_context(user_id: str = "default_user",
                                   query: str = "",
                                   budget_category: str = None,
                                   region: str = None,
                                   category: str = None,
                                   season: str = None,
                                   limit: int = 5) -> str:
    """
    Enhanced destination search with natural language query processing
    """
    if not DATABASE_TOOLS_AVAILABLE:
        return "Database tools not available. Using fallback recommendations."
    
    try:
        db_service = get_travel_database_service()
        
        # Extract parameters from natural language query if provided
        if query:
            query_lower = query.lower()
            
            # Extract budget preferences
            if not budget_category:
                if any(word in query_lower for word in ["cheap", "budget", "affordable"]):
                    budget_category = "budget"
                elif any(word in query_lower for word in ["luxury", "expensive", "high-end", "premium"]):
                    budget_category = "luxury"
                elif any(word in query_lower for word in ["moderate", "mid-range", "medium"]):
                    budget_category = "mid_range"
            
            # Extract category preferences
            if not category:
                if any(word in query_lower for word in ["beach", "ocean", "sea", "coast"]):
                    category = "beach"
                elif any(word in query_lower for word in ["mountain", "hiking", "skiing", "alps"]):
                    category = "mountain"
                elif any(word in query_lower for word in ["city", "urban", "metropolitan"]):
                    category = "city"
                elif any(word in query_lower for word in ["culture", "history", "museums", "art"]):
                    category = "cultural"
            
            # Extract season preferences
            if not season:
                if any(word in query_lower for word in ["spring", "april", "may"]):
                    season = "spring"
                elif any(word in query_lower for word in ["summer", "june", "july", "august"]):
                    season = "summer"
                elif any(word in query_lower for word in ["winter", "december", "january", "february", "skiing", "snow"]):
                    season = "winter"
        
        # Search destinations
        destinations = db_service.search_destinations(
            user_id=user_id,
            budget_category=budget_category,
            region=region,
            category=category,
            season=season,
            limit=limit
        )
        
        if not destinations:
            return "I couldn't find any destinations matching your criteria. Try adjusting your preferences!"
        
        # Format response
        response = f"🌍 Here are {len(destinations)} great destinations for you:\n\n"
        
        for i, dest in enumerate(destinations, 1):
            response += f"{i}. **{dest['name']}, {dest['country']}** ({dest['category']})\n"
            response += f"   📍 Region: {dest['region']}\n"
            response += f"   🌡️ Avg Temperature: {dest['avg_temperature']}°C\n"
            response += f"   📅 Best Season: {dest['best_season'].replace('_', ' ').title()}\n"
            response += f"   💰 Budget: {dest['budget_category'].replace('_', ' ').title()}\n"
            response += f"   📝 {dest['description']}\n\n"
        
        return response
        
    except Exception as e:
        logger.error(f"Error in enhanced destination search: {e}")
        return f"Sorry, I encountered an error searching for destinations: {str(e)}"

def save_user_travel_preferences(user_id: str,
                               session_id: str = "default_session",
                               **preferences) -> str:
    """Save user travel preferences to database"""
    if not DATABASE_TOOLS_AVAILABLE:
        return "Database tools not available. Preferences cannot be saved."
    
    try:
        db_service = get_travel_database_service()
        
        # Clean up preferences - remove None values
        clean_prefs = {k: v for k, v in preferences.items() if v is not None}
        
        if not clean_prefs:
            return "No valid preferences provided to save."
        
        success = db_service.save_user_preferences(
            user_id=user_id,
            preferences=clean_prefs,
            session_id=session_id
        )
        
        if success:
            pref_list = ", ".join(clean_prefs.keys())
            return f"✅ Saved your preferences: {pref_list}. I'll remember these for future recommendations!"
        else:
            return "❌ Failed to save your preferences. Please try again."
            
    except Exception as e:
        logger.error(f"Error saving preferences: {e}")
        return f"Sorry, I couldn't save your preferences: {str(e)}"

def get_mcp_toolbox_tools() -> List[FunctionTool]:
    """Get MCP Toolbox tools for ADK integration"""
    if not DATABASE_TOOLS_AVAILABLE:
        return []
    
    try:
        # Use the ADK Toolbox client which handles session management properly
        toolbox_client = create_adk_toolbox_client("http://127.0.0.1:5000")
        
        # Try to load the travel database toolset
        tools = toolbox_client.load_travel_toolset("travel-database")
        
        if tools:
            logger.info(f"Loaded MCP Toolbox toolset with {len(tools)} tools")
            
            # Convert to FunctionTools if they aren't already
            function_tools = []
            for tool in tools:
                if hasattr(tool, '__call__'):  # If it's already callable
                    function_tools.append(FunctionTool(tool))
                else:
                    function_tools.append(tool)
            
            return function_tools
        
        else:
            logger.info("Toolset loading failed, trying individual tool loading...")
            
            # Fallback: Load individual tools by name
            tool_names = [
                "search_destinations",
                "get_all_destinations", 
                "save_user_preferences",
                "get_user_preferences",
                "search_budget_destinations",
                "log_agent_interaction"
            ]
            
            mcp_tools = []
            
            for tool_name in tool_names:
                try:
                    # Load individual tool
                    tool = toolbox_client.load_travel_tool(tool_name)
                    if tool:
                        mcp_tools.append(FunctionTool(tool))
                        logger.info(f"Loaded MCP tool: {tool_name}")
                    
                except Exception as e:
                    logger.warning(f"Failed to load tool {tool_name}: {e}")
            
            logger.info(f"Loaded {len(mcp_tools)} individual MCP tools")
            return mcp_tools
    
    except Exception as e:
        logger.error(f"Failed to connect to MCP Toolbox: {e}")
        # Return mock tools as fallback
        logger.info("Using mock database tools as fallback")
        return get_database_function_tools()

# Create enhanced database tools
if DATABASE_TOOLS_AVAILABLE:
    try:
        enhanced_search_tool = FunctionTool(search_destinations_with_context)
        
        preferences_tool = FunctionTool(save_user_travel_preferences)
        
        logger.info("Enhanced database tools created successfully")
        
    except Exception as e:
        logger.error(f"Failed to create enhanced database tools: {e}")

# End of function-based tools implementation
