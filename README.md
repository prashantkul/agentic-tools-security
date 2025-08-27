# Agentic Tools Security - Travel Agent with MCP Toolbox

A secure travel agent implementation using Google's Agent Development Kit (ADK) with MCP Toolbox for BigQuery integration.

## Overview

This project demonstrates how to build a secure AI agent that:
- Uses Google ADK for agent framework
- Integrates with MCP Toolbox for database abstraction
- Connects to BigQuery for travel data management
- Implements service account authentication for secure database access

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   ADK Agent     │    │   MCP Toolbox    │    │    BigQuery     │
│                 │    │     Server       │    │                 │
│ - Agent Logic   │───▶│ - Tool Routing   │───▶│ - Travel Data   │
│ - Tool Calls    │    │ - Auth Handling  │    │ - User Prefs    │
│ - Response Gen  │    │ - SQL Execution  │    │ - Interactions  │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## Features

- **Travel Destination Search**: Query destinations by budget, region, category, and season
- **User Preferences**: Save and retrieve personalized travel preferences
- **Interaction Logging**: Track agent conversations for analytics
- **Secure Authentication**: Service account-based BigQuery access
- **Database Abstraction**: MCP Toolbox handles SQL generation and execution

## Setup

### Prerequisites

- Python 3.8+
- Google Cloud Project with BigQuery API enabled
- MCP Toolbox server
- Required API keys (see `.env.example`)

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd agentic-tools-security
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your API keys and configuration
```

4. Set up Google Cloud Authentication:
```bash
# Set Application Default Credentials to use the service account
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/your/service-account-key.json"
```

5. Initialize BigQuery dataset:
```bash
python setup_bigquery.py
```

### MCP Toolbox Configuration

The `tools.yaml` file defines the database tools:

```yaml
sources:
  travel_bq_source:
    kind: "bigquery"
    project: "your-gcp-project"
    location: "us-central1"

tools:
  search_destinations:
    kind: bigquery-execute-sql
    source: travel_bq_source
    description: |
      Search for travel destinations based on criteria like budget, region, category, and season.
```

## Usage

### Starting the MCP Toolbox Server

```bash
# Start the MCP Toolbox server
mcp-toolbox-server --config tools.yaml --port 5000
```

### Running the Agent

```bash
python agent/agent.py
```

### Example Queries

- "Find budget-friendly destinations in Europe for winter travel"
- "Show me luxury beach destinations under $3000"
- "Save my preference for adventure travel in mountain regions"

## Database Schema

### Destinations Table
```sql
CREATE TABLE `project.travel_data.destinations` (
  destination_id STRING,
  name STRING,
  country STRING,
  region STRING,
  category STRING,
  budget_category STRING,
  best_season STRING,
  description STRING,
  estimated_cost_usd FLOAT64
);
```

### User Preferences Table
```sql
CREATE TABLE `project.travel_data.user_preferences` (
  user_id STRING,
  preference_type STRING,
  preference_value STRING,
  created_at TIMESTAMP,
  updated_at TIMESTAMP
);
```

### Agent Interactions Table
```sql
CREATE TABLE `project.travel_data.agent_interactions` (
  interaction_id STRING,
  user_query STRING,
  agent_response STRING,
  timestamp TIMESTAMP,
  session_id STRING
);
```

## Security Considerations

### Service Account Authentication
- Uses dedicated service account for BigQuery access
- Follows principle of least privilege
- Credentials managed through Application Default Credentials (ADC)

### Data Protection
- No user credentials stored in database
- Interaction logging is anonymized
- API keys managed through environment variables

### SQL Injection Prevention
- MCP Toolbox handles SQL parameterization
- Agent instructions include strict SQL formatting rules
- Input validation at multiple layers

## Development

### Key Files

- `agent/agent.py` - Main agent implementation with ADK
- `agent/tools.py` - MCP Toolbox integration and tool definitions  
- `agent/mcp_toolbox_client.py` - Authentication and client management
- `tools.yaml` - MCP Toolbox configuration
- `setup_bigquery.py` - Database initialization script

### Adding New Tools

1. Define the tool in `tools.yaml`:
```yaml
new_tool:
  kind: bigquery-execute-sql
  source: travel_bq_source
  description: |
    Description of what the tool does
```

2. Update agent instructions in `agent.py` to include the new tool

3. Test the integration:
```bash
python test_integration.py
```

### Database Rules

When working with the database tools, follow these critical rules:

- Always use fully qualified table names: `project.dataset.table`
- Escape single quotes in SQL strings by doubling them
- Use proper SQL parameterization through MCP Toolbox
- Never use unqualified table names

## Troubleshooting

### Common Issues

1. **"Session is closed" error**
   - Ensure MCP Toolbox server is running
   - Check that authentication is properly configured

2. **BigQuery permission errors**
   - Verify service account has `roles/bigquery.admin`
   - Confirm Application Default Credentials are set

3. **"Table must be qualified with a dataset"**
   - Use fully qualified table names in all SQL queries
   - Check agent instructions for proper table naming

### Debugging

Enable verbose logging:
```bash
export VERBOSE=true
python agent/agent.py
```

Check MCP Toolbox server logs:
```bash
mcp-toolbox-server --config tools.yaml --port 5000 --verbose
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

[Add your license information here]

## Support

For issues and questions:
- Create an issue in the GitHub repository
- Check the troubleshooting section above
- Review MCP Toolbox documentation

## Acknowledgments

- Google ADK team for the agent framework
- MCP Toolbox project for database abstraction
- BigQuery for reliable data storage