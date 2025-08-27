"""
Memory Bank Integration for Travel Advisor Agent using ADK
Uses Google Cloud Vertex AI Memory Bank through ADK's VertexAiMemoryBankService.
"""

import os
import logging
from typing import Optional
from dotenv import load_dotenv
from google.adk.memory import VertexAiMemoryBankService
from google.adk.sessions import Session, InMemorySessionService
from google.adk.runners import Runner
from .custom_memory import CustomMemoryService, GroqMemoryAgent

# Load environment variables from .env file
load_dotenv()

logger = logging.getLogger(__name__)


def create_memory_service(
    project_id: str = None, location: str = None, agent_engine_id: str = None
) -> VertexAiMemoryBankService:
    """
    Create a VertexAiMemoryBankService instance.

    Args:
        project_id: Google Cloud project ID
        location: Vertex AI location
        agent_engine_id: Agent engine ID extracted from API resource name
                        Format: agent_engine.api_resource.name.split("/")[-1]

    Returns:
        VertexAiMemoryBankService instance
    """
    project_id = project_id or os.getenv("GOOGLE_CLOUD_PROJECT")
    location = location or os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
    agent_engine_id = agent_engine_id or os.getenv("AGENT_ENGINE_ID")

    if not project_id:
        raise ValueError(
            "Project ID must be provided or set in GOOGLE_CLOUD_PROJECT env var"
        )

    if not agent_engine_id:
        raise ValueError(
            "Agent Engine ID must be provided as parameter or set in AGENT_ENGINE_ID env var"
        )

    logger.info(
        f"Creating memory service for project {project_id}, agent engine {agent_engine_id}"
    )

    return VertexAiMemoryBankService(
        project=project_id, location=location, agent_engine_id=agent_engine_id
    )


class MemoryBankClient:
    """
    Simplified ADK-based client for interacting with Vertex AI Memory Bank and creating test runners.
    """

    def __init__(
        self, project_id: str = None, location: str = None, agent_engine_id: str = None
    ):
        """
        Initialize Memory Bank client using ADK.

        Args:
            project_id: Google Cloud project ID
            location: Vertex AI location
            agent_engine_id: Agent engine ID (memory bank ID)
        """
        self.project_id = project_id or os.getenv("GOOGLE_CLOUD_PROJECT")
        self.location = location or os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
        self.agent_engine_id = agent_engine_id or os.getenv("AGENT_ENGINE_ID")

        # Set up Vertex AI environment
        os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "1"

        # Create memory service if configuration is available
        self.memory_service = None
        if self.project_id and self.agent_engine_id:
            try:
                self.memory_service = create_memory_service(
                    self.project_id, self.location, self.agent_engine_id
                )
                logger.info("ADK Memory Bank client initialized successfully")
            except Exception as e:
                logger.warning(f"Could not create memory service: {e}")
        else:
            logger.warning(
                "Memory service not configured - missing project_id or agent_engine_id"
            )

    def create_test_runner(
        self, app_name: str, travel_agent, use_memory: bool = True
    ) -> Runner:
        """
        Create a test runner with proper session and memory services.

        Args:
            app_name: Application name for session scoping
            travel_agent: TravelAdvisorAgent instance
            use_memory: Whether to enable memory service (for cross-session tests)

        Returns:
            Runner instance configured for testing
        """
        # Always use InMemorySessionService for proper within-session context
        session_service = InMemorySessionService()

        # Use memory service for cross-session persistence if available and requested
        memory_service = (
            self.memory_service if (use_memory and self.memory_service) else None
        )

        runner = Runner(
            app_name=app_name,
            agent=travel_agent.agent,
            session_service=session_service,
            memory_service=memory_service,
        )

        logger.info(
            f"Created test runner for {app_name} with memory={'enabled' if memory_service else 'disabled'}"
        )
        return runner

    async def add_session_to_memory(self, session: Session) -> None:
        """
        Add a session to memory bank for memory generation.

        Args:
            session: ADK Session object containing conversation data
        """
        if not self.memory_service:
            logger.warning(
                "Memory service not available - cannot add session to memory"
            )
            return

        try:
            await self.memory_service.add_session_to_memory(session)
            logger.info(f"Added session {session.id} to memory bank")
        except Exception as e:
            logger.error(f"Failed to add session to memory: {e}")
            raise

    def get_memory_service(self) -> Optional[VertexAiMemoryBankService]:
        """
        Get the underlying ADK memory service.

        Returns:
            VertexAiMemoryBankService instance or None if not configured
        """
        return self.memory_service

    def is_memory_configured(self) -> bool:
        """
        Check if memory service is properly configured.

        Returns:
            True if memory service is available, False otherwise
        """
        return self.memory_service is not None

    # Groq Custom Memory Support

    async def create_groq_memory_service(
        self, db_path: str = None
    ) -> CustomMemoryService:
        """
        Create a custom memory service for Groq models.

        Args:
            db_path: Optional path to SQLite database file

        Returns:
            CustomMemoryService instance for cross-session memory with Groq models
        """
        return CustomMemoryService(db_path)

    async def create_groq_memory_runner(
        self, app_name: str, travel_agent, db_path: str = None
    ) -> GroqMemoryAgent:
        """
        Create a Groq agent with custom memory capabilities for cross-session testing.

        Args:
            app_name: Application name for memory scoping
            travel_agent: TravelAdvisorAgent instance (Groq-based)
            db_path: Optional path to SQLite database file

        Returns:
            GroqMemoryAgent with cross-session memory persistence
        """
        memory_service = await self.create_groq_memory_service(db_path)
        return GroqMemoryAgent(travel_agent, memory_service)

    async def create_hybrid_test_runner(
        self,
        app_name: str,
        travel_agent,
        use_custom_memory: bool = False,
        db_path: str = None,
    ):
        """
        Create a test runner that supports both ADK Memory Bank and custom Groq memory.

        Args:
            app_name: Application name
            travel_agent: TravelAdvisorAgent instance
            use_custom_memory: Use custom memory system instead of ADK Memory Bank
            db_path: Path for custom memory database

        Returns:
            Runner or GroqMemoryAgent depending on memory type
        """
        if use_custom_memory or travel_agent.model_type == "groq":
            # Use custom memory system for Groq models
            return await self.create_groq_memory_runner(app_name, travel_agent, db_path)
        else:
            # Use standard ADK Memory Bank for Vertex AI models
            return self.create_test_runner(app_name, travel_agent, use_memory=True)
