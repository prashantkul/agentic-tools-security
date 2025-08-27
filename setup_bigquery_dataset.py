#!/usr/bin/env python3
"""
Setup BigQuery dataset and tables for MCP Toolbox integration
Creates the required schema as defined in tools.yaml
"""

import os
import sys
from pathlib import Path
from google.cloud import bigquery
from google.auth import default
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def create_bigquery_resources():
    """Create BigQuery dataset and tables for travel data"""
    
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
    if not project_id:
        print("❌ GOOGLE_CLOUD_PROJECT environment variable not set")
        return False
    
    print(f"🔧 Setting up BigQuery resources for project: {project_id}")
    
    try:
        # Initialize BigQuery client
        credentials, _ = default()
        client = bigquery.Client(project=project_id, credentials=credentials)
        
        print("✅ BigQuery client initialized")
        
        # Create dataset
        dataset_id = "travel_data"
        dataset_ref = f"{project_id}.{dataset_id}"
        
        print(f"\n📊 Creating dataset: {dataset_ref}")
        
        try:
            dataset = bigquery.Dataset(dataset_ref)
            dataset.location = "us-central1"  # Match your GOOGLE_CLOUD_LOCATION
            dataset.description = "Travel advisor agent data"
            
            dataset = client.create_dataset(dataset, timeout=30)
            print(f"✅ Created dataset {dataset_id}")
            
        except Exception as e:
            if "Already Exists" in str(e):
                print(f"ℹ️ Dataset {dataset_id} already exists")
            else:
                print(f"❌ Failed to create dataset: {e}")
                return False
        
        # Create tables
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
        
        print("\n🏗️ Creating tables...")
        for table_name, create_sql in tables.items():
            try:
                query = create_sql.format(dataset_ref=dataset_ref)
                job = client.query(query)
                job.result()  # Wait for completion
                print(f"✅ Created/verified table: {table_name}")
            except Exception as e:
                print(f"❌ Failed to create table {table_name}: {e}")
                return False
        
        # Insert sample data
        print("\n📝 Inserting sample data...")
        
        sample_data_query = f"""
        INSERT INTO `{dataset_ref}.destinations`
        (destination_id, name, country, region, category, description, avg_temperature, best_season, budget_category)
        VALUES 
            ('tokyo_japan', 'Tokyo', 'Japan', 'East Asia', 'city', 'Modern metropolis with rich cultural heritage, amazing food, and cutting-edge technology', 15.5, 'spring', 'mid_range'),
            ('paris_france', 'Paris', 'France', 'Western Europe', 'cultural', 'City of Light, famous for art, fashion, gastronomy, and culture', 12.0, 'spring', 'luxury'),
            ('bali_indonesia', 'Bali', 'Indonesia', 'Southeast Asia', 'beach', 'Tropical paradise with beautiful beaches, temples, and rice terraces', 26.0, 'dry_season', 'budget'),
            ('swiss_alps', 'Swiss Alps', 'Switzerland', 'Central Europe', 'mountain', 'Stunning mountain scenery, world-class skiing, and charming alpine villages', 2.0, 'winter', 'luxury'),
            ('thailand_beaches', 'Thai Beaches', 'Thailand', 'Southeast Asia', 'beach', 'Crystal clear waters, white sand beaches, and vibrant marine life', 28.0, 'cool_season', 'budget'),
            ('rome_italy', 'Rome', 'Italy', 'Southern Europe', 'cultural', 'Eternal City with ancient history, incredible architecture, and amazing cuisine', 16.0, 'spring', 'mid_range'),
            ('maldives', 'Maldives', 'Maldives', 'South Asia', 'beach', 'Luxury overwater villas and pristine coral reefs in the Indian Ocean', 30.0, 'dry_season', 'luxury'),
            ('patagonia', 'Patagonia', 'Chile/Argentina', 'South America', 'mountain', 'Dramatic landscapes, glaciers, and world-class trekking opportunities', 8.0, 'summer', 'mid_range')
        """
        
        try:
            # Check if data already exists
            count_query = f"SELECT COUNT(*) as count FROM `{dataset_ref}.destinations`"
            count_job = client.query(count_query)
            count_result = list(count_job.result())[0].count
            
            if count_result == 0:
                # Insert sample data
                insert_job = client.query(sample_data_query)
                insert_job.result()
                print("✅ Inserted 8 sample destinations")
            else:
                print(f"ℹ️ Table already has {count_result} destinations, skipping sample data insert")
            
        except Exception as e:
            print(f"⚠️ Sample data insert failed (table may already have data): {e}")
        
        print(f"\n🎉 BigQuery setup complete!")
        print(f"📍 Dataset: {dataset_ref}")
        print(f"📊 Tables: destinations, user_preferences, agent_interactions")
        print(f"\n💡 Next steps:")
        print(f"1. Start MCP Toolbox server: toolbox serve --config tools.yaml")
        print(f"2. Test with your ADK agent")
        print(f"3. Try queries like: 'Find me budget beach destinations'")
        
        return True
        
    except Exception as e:
        print(f"❌ BigQuery setup failed: {e}")
        return False

def verify_setup():
    """Verify the BigQuery setup is working"""
    
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
    
    try:
        credentials, _ = default()
        client = bigquery.Client(project=project_id, credentials=credentials)
        
        # Test query
        query = f"""
        SELECT 
            name, 
            country, 
            category, 
            budget_category 
        FROM `{project_id}.travel_data.destinations` 
        LIMIT 3
        """
        
        job = client.query(query)
        results = list(job.result())
        
        print(f"\n🔍 Verification - Sample destinations:")
        for row in results:
            print(f"  - {row.name}, {row.country} ({row.category}, {row.budget_category})")
        
        return True
        
    except Exception as e:
        print(f"❌ Verification failed: {e}")
        return False

def main():
    """Main setup function"""
    print("🚀 BigQuery Setup for MCP Toolbox Travel Agent")
    print("=" * 50)
    
    # Check prerequisites
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
    credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    
    if not project_id:
        print("❌ GOOGLE_CLOUD_PROJECT not set in environment")
        return False
    
    if not credentials_path or not os.path.exists(credentials_path):
        print("❌ GOOGLE_APPLICATION_CREDENTIALS not set or file doesn't exist")
        return False
    
    print(f"✅ Project: {project_id}")
    print(f"✅ Credentials: {credentials_path}")
    
    # Create resources
    if create_bigquery_resources():
        # Verify setup
        if verify_setup():
            print("\n🎯 Setup completed successfully!")
            return True
    
    print("\n❌ Setup failed. Check the errors above.")
    return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)