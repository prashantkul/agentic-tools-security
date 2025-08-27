"""
MCP Toolbox Database Tools for Travel Advisor Agent
Provides BigQuery integration with service account authentication
"""

import os
import logging
from typing import Dict, Any, List, Optional
from google.cloud import bigquery
from google.auth import default
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TravelDatabaseService:
    """Service for managing travel-related database operations with BigQuery"""
    
    def __init__(self, project_id: str = None, dataset_id: str = "travel_data"):
        """
        Initialize the travel database service
        
        Args:
            project_id: Google Cloud project ID
            dataset_id: BigQuery dataset ID
        """
        self.project_id = project_id or os.getenv("GOOGLE_CLOUD_PROJECT")
        self.dataset_id = dataset_id
        
        if not self.project_id:
            raise ValueError("Google Cloud project ID must be provided or set in GOOGLE_CLOUD_PROJECT")
        
        # Initialize BigQuery client with service account authentication
        self.client = self._initialize_bigquery_client()
        self.dataset_ref = f"{self.project_id}.{self.dataset_id}"
        
        logger.info(f"Initialized TravelDatabaseService for project: {self.project_id}")
    
    def _initialize_bigquery_client(self) -> bigquery.Client:
        """Initialize BigQuery client with service account credentials"""
        try:
            # Use service account credentials from environment
            credentials, project = default()
            
            client = bigquery.Client(
                project=self.project_id,
                credentials=credentials
            )
            
            logger.info(f"BigQuery client initialized for project: {self.project_id}")
            return client
            
        except Exception as e:
            logger.error(f"Failed to initialize BigQuery client: {e}")
            raise
    
    def ensure_dataset_exists(self) -> bool:
        """Ensure the travel dataset exists in BigQuery"""
        try:
            dataset = bigquery.Dataset(self.dataset_ref)
            dataset.location = "US"  # or your preferred location
            
            # Try to get the dataset, create if it doesn't exist
            try:
                self.client.get_dataset(self.dataset_ref)
                logger.info(f"Dataset {self.dataset_ref} already exists")
            except Exception:
                self.client.create_dataset(dataset, timeout=30)
                logger.info(f"Created dataset {self.dataset_ref}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to ensure dataset exists: {e}")
            return False
    
    def ensure_tables_exist(self) -> bool:
        """Ensure all required travel tables exist"""
        try:
            tables = {
                "destinations": """
                CREATE TABLE IF NOT EXISTS `{dataset_ref}.destinations` (
                    destination_id STRING,
                    name STRING,
                    country STRING,
                    region STRING,
                    category STRING,
                    description STRING,
                    avg_temperature FLOAT64,
                    best_season STRING,
                    budget_category STRING,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
                )
                """,
                "user_preferences": """
                CREATE TABLE IF NOT EXISTS `{dataset_ref}.user_preferences` (
                    user_id STRING,
                    preference_type STRING,
                    preference_value JSON,
                    session_id STRING,
                    created_by_agent STRING DEFAULT 'travel_advisor_agent',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
                )
                """,
                "travel_history": """
                CREATE TABLE IF NOT EXISTS `{dataset_ref}.travel_history` (
                    user_id STRING,
                    destination_id STRING,
                    visit_date DATE,
                    rating FLOAT64,
                    feedback STRING,
                    trip_duration_days INT64,
                    budget_spent FLOAT64,
                    session_id STRING,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
                )
                """,
                "agent_interactions": """
                CREATE TABLE IF NOT EXISTS `{dataset_ref}.agent_interactions` (
                    interaction_id STRING,
                    user_id STRING,
                    session_id STRING,
                    agent_name STRING DEFAULT 'travel_advisor_agent',
                    query_type STRING,
                    user_query STRING,
                    agent_response STRING,
                    tools_used JSON,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
                )
                """
            }
            
            for table_name, create_sql in tables.items():
                try:
                    query = create_sql.format(dataset_ref=self.dataset_ref)
                    job = self.client.query(query)
                    job.result()  # Wait for the job to complete
                    logger.info(f"Ensured table {table_name} exists")
                except Exception as e:
                    logger.error(f"Failed to create table {table_name}: {e}")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to ensure tables exist: {e}")
            return False
    
    def search_destinations(self, 
                          user_id: str,
                          budget_category: str = None, 
                          region: str = None, 
                          category: str = None,
                          season: str = None,
                          limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search for travel destinations based on criteria
        
        Args:
            user_id: User context for logging
            budget_category: Budget range (budget, mid_range, luxury)
            region: Geographic region
            category: Destination category (beach, mountain, city, cultural)
            season: Best travel season
            limit: Maximum number of results
        """
        try:
            # Build dynamic WHERE clause
            conditions = []
            parameters = []
            
            if budget_category:
                conditions.append("budget_category = ?")
                parameters.append(budget_category)
            
            if region:
                conditions.append("region = ?")
                parameters.append(region)
            
            if category:
                conditions.append("category = ?")
                parameters.append(category)
            
            if season:
                conditions.append("best_season = ?")
                parameters.append(season)
            
            where_clause = " AND ".join(conditions) if conditions else "1=1"
            
            query = f"""
            SELECT 
                destination_id,
                name,
                country,
                region,
                category,
                description,
                avg_temperature,
                best_season,
                budget_category
            FROM `{self.dataset_ref}.destinations`
            WHERE {where_clause}
            ORDER BY name
            LIMIT {limit}
            """
            
            # Configure the query job
            job_config = bigquery.QueryJobConfig()
            job_config.query_parameters = [
                bigquery.ScalarQueryParameter(None, "STRING", param) 
                for param in parameters
            ]
            
            query_job = self.client.query(query, job_config=job_config)
            results = query_job.result()
            
            destinations = []
            for row in results:
                destinations.append({
                    "destination_id": row.destination_id,
                    "name": row.name,
                    "country": row.country,
                    "region": row.region,
                    "category": row.category,
                    "description": row.description,
                    "avg_temperature": row.avg_temperature,
                    "best_season": row.best_season,
                    "budget_category": row.budget_category
                })
            
            # Log the interaction
            self.log_agent_interaction(
                user_id=user_id,
                query_type="search_destinations",
                user_query=f"Search destinations: budget={budget_category}, region={region}, category={category}",
                agent_response=f"Found {len(destinations)} destinations",
                tools_used=["search_destinations"]
            )
            
            logger.info(f"Found {len(destinations)} destinations for user {user_id}")
            return destinations
            
        except Exception as e:
            logger.error(f"Failed to search destinations: {e}")
            return []
    
    def save_user_preferences(self, 
                            user_id: str, 
                            preferences: Dict[str, Any],
                            session_id: str = None) -> bool:
        """
        Save user travel preferences
        
        Args:
            user_id: User identifier
            preferences: Dictionary of preferences
            session_id: Current session identifier
        """
        try:
            for pref_type, pref_value in preferences.items():
                query = f"""
                INSERT INTO `{self.dataset_ref}.user_preferences` 
                (user_id, preference_type, preference_value, session_id)
                VALUES (@user_id, @pref_type, @pref_value, @session_id)
                """
                
                job_config = bigquery.QueryJobConfig(
                    query_parameters=[
                        bigquery.ScalarQueryParameter("user_id", "STRING", user_id),
                        bigquery.ScalarQueryParameter("pref_type", "STRING", pref_type),
                        bigquery.ScalarQueryParameter("pref_value", "JSON", json.dumps(pref_value)),
                        bigquery.ScalarQueryParameter("session_id", "STRING", session_id or "default")
                    ]
                )
                
                query_job = self.client.query(query, job_config=job_config)
                query_job.result()
            
            logger.info(f"Saved preferences for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save user preferences: {e}")
            return False
    
    def get_user_preferences(self, user_id: str) -> Dict[str, Any]:
        """Get user travel preferences"""
        try:
            query = f"""
            SELECT preference_type, preference_value
            FROM `{self.dataset_ref}.user_preferences`
            WHERE user_id = @user_id
            ORDER BY updated_at DESC
            """
            
            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("user_id", "STRING", user_id)
                ]
            )
            
            query_job = self.client.query(query, job_config=job_config)
            results = query_job.result()
            
            preferences = {}
            for row in results:
                preferences[row.preference_type] = json.loads(row.preference_value)
            
            logger.info(f"Retrieved preferences for user {user_id}")
            return preferences
            
        except Exception as e:
            logger.error(f"Failed to get user preferences: {e}")
            return {}
    
    def log_agent_interaction(self,
                            user_id: str,
                            query_type: str,
                            user_query: str,
                            agent_response: str,
                            tools_used: List[str],
                            session_id: str = None) -> bool:
        """Log agent interaction for analytics and improvement"""
        try:
            import uuid
            interaction_id = str(uuid.uuid4())
            
            query = f"""
            INSERT INTO `{self.dataset_ref}.agent_interactions`
            (interaction_id, user_id, session_id, query_type, user_query, agent_response, tools_used)
            VALUES (@interaction_id, @user_id, @session_id, @query_type, @user_query, @agent_response, @tools_used)
            """
            
            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("interaction_id", "STRING", interaction_id),
                    bigquery.ScalarQueryParameter("user_id", "STRING", user_id),
                    bigquery.ScalarQueryParameter("session_id", "STRING", session_id or "default"),
                    bigquery.ScalarQueryParameter("query_type", "STRING", query_type),
                    bigquery.ScalarQueryParameter("user_query", "STRING", user_query),
                    bigquery.ScalarQueryParameter("agent_response", "STRING", agent_response),
                    bigquery.ScalarQueryParameter("tools_used", "JSON", json.dumps(tools_used))
                ]
            )
            
            query_job = self.client.query(query, job_config=job_config)
            query_job.result()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to log agent interaction: {e}")
            return False
    
    def initialize_sample_data(self) -> bool:
        """Initialize the database with sample travel destinations"""
        try:
            sample_destinations = [
                {
                    "destination_id": "tokyo_japan",
                    "name": "Tokyo",
                    "country": "Japan",
                    "region": "East Asia",
                    "category": "city",
                    "description": "Modern metropolis with rich cultural heritage, amazing food, and cutting-edge technology",
                    "avg_temperature": 15.5,
                    "best_season": "spring",
                    "budget_category": "mid_range"
                },
                {
                    "destination_id": "paris_france",
                    "name": "Paris",
                    "country": "France", 
                    "region": "Western Europe",
                    "category": "cultural",
                    "description": "City of Light, famous for art, fashion, gastronomy, and culture",
                    "avg_temperature": 12.0,
                    "best_season": "spring",
                    "budget_category": "luxury"
                },
                {
                    "destination_id": "bali_indonesia",
                    "name": "Bali",
                    "country": "Indonesia",
                    "region": "Southeast Asia",
                    "category": "beach",
                    "description": "Tropical paradise with beautiful beaches, temples, and rice terraces",
                    "avg_temperature": 26.0,
                    "best_season": "dry_season",
                    "budget_category": "budget"
                },
                {
                    "destination_id": "swiss_alps",
                    "name": "Swiss Alps",
                    "country": "Switzerland",
                    "region": "Central Europe", 
                    "category": "mountain",
                    "description": "Stunning mountain scenery, world-class skiing, and charming alpine villages",
                    "avg_temperature": 2.0,
                    "best_season": "winter",
                    "budget_category": "luxury"
                },
                {
                    "destination_id": "thailand_beaches",
                    "name": "Thai Beaches",
                    "country": "Thailand",
                    "region": "Southeast Asia",
                    "category": "beach",
                    "description": "Crystal clear waters, white sand beaches, and vibrant marine life",
                    "avg_temperature": 28.0,
                    "best_season": "cool_season",
                    "budget_category": "budget"
                }
            ]
            
            # Insert sample data
            for dest in sample_destinations:
                query = f"""
                INSERT INTO `{self.dataset_ref}.destinations`
                (destination_id, name, country, region, category, description, avg_temperature, best_season, budget_category)
                VALUES (@destination_id, @name, @country, @region, @category, @description, @avg_temperature, @best_season, @budget_category)
                """
                
                job_config = bigquery.QueryJobConfig(
                    query_parameters=[
                        bigquery.ScalarQueryParameter("destination_id", "STRING", dest["destination_id"]),
                        bigquery.ScalarQueryParameter("name", "STRING", dest["name"]),
                        bigquery.ScalarQueryParameter("country", "STRING", dest["country"]),
                        bigquery.ScalarQueryParameter("region", "STRING", dest["region"]),
                        bigquery.ScalarQueryParameter("category", "STRING", dest["category"]),
                        bigquery.ScalarQueryParameter("description", "STRING", dest["description"]),
                        bigquery.ScalarQueryParameter("avg_temperature", "FLOAT64", dest["avg_temperature"]),
                        bigquery.ScalarQueryParameter("best_season", "STRING", dest["best_season"]),
                        bigquery.ScalarQueryParameter("budget_category", "STRING", dest["budget_category"])
                    ]
                )
                
                query_job = self.client.query(query, job_config=job_config)
                query_job.result()
            
            logger.info(f"Initialized {len(sample_destinations)} sample destinations")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize sample data: {e}")
            return False


# Global database service instance
travel_db_service: Optional[TravelDatabaseService] = None

def get_travel_database_service() -> TravelDatabaseService:
    """Get or create the global travel database service instance"""
    global travel_db_service
    
    if travel_db_service is None:
        travel_db_service = TravelDatabaseService()
    
    return travel_db_service

def initialize_travel_database() -> bool:
    """Initialize the travel database with tables and sample data"""
    try:
        db_service = get_travel_database_service()
        
        # Ensure dataset and tables exist
        if not db_service.ensure_dataset_exists():
            return False
        
        if not db_service.ensure_tables_exist():
            return False
        
        # Initialize with sample data (only if tables are empty)
        db_service.initialize_sample_data()
        
        logger.info("Travel database initialized successfully")
        return True
        
    except Exception as e:
        logger.error(f"Failed to initialize travel database: {e}")
        return False


if __name__ == "__main__":
    # Test the database service
    print("Testing Travel Database Service...")
    
    if initialize_travel_database():
        print("✅ Database initialized successfully")
        
        # Test search
        db = get_travel_database_service()
        destinations = db.search_destinations(
            user_id="test_user",
            budget_category="budget",
            category="beach"
        )
        print(f"Found {len(destinations)} beach destinations in budget category")
        
        for dest in destinations:
            print(f"  - {dest['name']}, {dest['country']}: {dest['description'][:50]}...")
    else:
        print("❌ Database initialization failed")