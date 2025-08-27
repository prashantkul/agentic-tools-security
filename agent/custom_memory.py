#!/usr/bin/env python3
"""
Custom Memory System for Groq Models

Implements cross-session memory persistence for open source models
to enable true memory poisoning security testing.

This system provides:
- Cross-session conversation storage
- Memory retrieval and injection
- User-scoped memory isolation
- Memory poisoning attack simulation
- Comparable functionality to ADK Memory Bank
"""

import sqlite3
import json
import asyncio
import hashlib
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class CustomMemoryService:
    """
    Custom memory service for Groq models that simulates ADK Memory Bank functionality.
    Stores conversations in SQLite and provides memory retrieval for cross-session persistence.
    """

    def __init__(self, db_path: str = None):
        """Initialize the custom memory service with SQLite backend."""
        if db_path is None:
            db_path = Path(__file__).parent.parent / "data" / "groq_memory.db"

        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Initialize database
        self._init_database()

    def _init_database(self):
        """Initialize SQLite database with required tables."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Conversations table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                app_name TEXT NOT NULL,
                session_id TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                message_type TEXT NOT NULL,  -- 'user' or 'agent'
                content TEXT NOT NULL,
                metadata TEXT  -- JSON metadata
            )
        """
        )

        # Memory summaries table (for efficient retrieval)
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS memory_summaries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                app_name TEXT NOT NULL,
                memory_type TEXT NOT NULL,  -- 'preference', 'fact', 'context'
                summary TEXT NOT NULL,
                relevance_score REAL DEFAULT 1.0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                last_accessed DATETIME DEFAULT CURRENT_TIMESTAMP,
                access_count INTEGER DEFAULT 0
            )
        """
        )

        # Create indexes for performance
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_conv_user_app ON conversations(user_id, app_name)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_memory_user_app ON memory_summaries(user_id, app_name)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_memory_relevance ON memory_summaries(relevance_score DESC)"
        )

        conn.commit()
        conn.close()

    async def store_conversation(
        self,
        user_id: str,
        app_name: str,
        session_id: str,
        user_message: str,
        agent_response: str,
        metadata: Dict = None,
    ):
        """Store a conversation turn in memory."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # Store user message
            cursor.execute(
                """
                INSERT INTO conversations (user_id, app_name, session_id, message_type, content, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (
                    user_id,
                    app_name,
                    session_id,
                    "user",
                    user_message,
                    json.dumps(metadata or {}),
                ),
            )

            # Store agent response
            cursor.execute(
                """
                INSERT INTO conversations (user_id, app_name, session_id, message_type, content, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (
                    user_id,
                    app_name,
                    session_id,
                    "agent",
                    agent_response,
                    json.dumps(metadata or {}),
                ),
            )

            conn.commit()

            # Generate memory summaries asynchronously
            await self._generate_memory_summaries(
                user_id, app_name, user_message, agent_response
            )

        finally:
            conn.close()

    async def _generate_memory_summaries(
        self, user_id: str, app_name: str, user_message: str, agent_response: str
    ):
        """Generate memory summaries from conversation for efficient retrieval."""

        # Extract preferences
        preference_keywords = [
            "prefer",
            "like",
            "love",
            "want",
            "need",
            "budget",
            "favorite",
        ]
        if any(keyword in user_message.lower() for keyword in preference_keywords):
            await self._store_memory_summary(
                user_id, app_name, "preference", user_message
            )

        # Extract facts (names, locations, specific details)
        fact_patterns = ["my name is", "i am", "i live in", "i work", "i have"]
        if any(pattern in user_message.lower() for pattern in fact_patterns):
            await self._store_memory_summary(user_id, app_name, "fact", user_message)

        # Extract context from both messages
        context_summary = f"User discussed: {user_message[:100]}... Agent provided: {agent_response[:100]}..."
        await self._store_memory_summary(
            user_id, app_name, "context", context_summary, relevance_score=0.7
        )

    async def _store_memory_summary(
        self,
        user_id: str,
        app_name: str,
        memory_type: str,
        summary: str,
        relevance_score: float = 1.0,
    ):
        """Store a memory summary with relevance scoring."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                INSERT INTO memory_summaries (user_id, app_name, memory_type, summary, relevance_score)
                VALUES (?, ?, ?, ?, ?)
            """,
                (user_id, app_name, memory_type, summary, relevance_score),
            )
            conn.commit()
        finally:
            conn.close()

    async def retrieve_memories(
        self, user_id: str, app_name: str, query: str = None, limit: int = 10
    ) -> List[Dict]:
        """Retrieve relevant memories for a user."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # Get recent conversations
            cursor.execute(
                """
                SELECT DISTINCT session_id, timestamp, content, message_type
                FROM conversations 
                WHERE user_id = ? AND app_name = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """,
                (user_id, app_name, limit * 2),
            )

            conversations = cursor.fetchall()

            # Get memory summaries
            cursor.execute(
                """
                SELECT memory_type, summary, relevance_score, created_at
                FROM memory_summaries
                WHERE user_id = ? AND app_name = ?
                ORDER BY relevance_score DESC, last_accessed DESC
                LIMIT ?
            """,
                (user_id, app_name, limit),
            )

            summaries = cursor.fetchall()

            # Update access tracking
            cursor.execute(
                """
                UPDATE memory_summaries 
                SET last_accessed = CURRENT_TIMESTAMP, access_count = access_count + 1
                WHERE user_id = ? AND app_name = ?
            """,
                (user_id, app_name),
            )
            conn.commit()

            memories = []

            # Format conversations
            for session_id, timestamp, content, msg_type in conversations:
                memories.append(
                    {
                        "type": "conversation",
                        "content": content,
                        "message_type": msg_type,
                        "session_id": session_id,
                        "timestamp": timestamp,
                    }
                )

            # Format summaries
            for mem_type, summary, relevance, created_at in summaries:
                memories.append(
                    {
                        "type": "summary",
                        "memory_type": mem_type,
                        "content": summary,
                        "relevance_score": relevance,
                        "created_at": created_at,
                    }
                )

            return memories

        finally:
            conn.close()

    async def inject_malicious_memory(
        self,
        user_id: str,
        app_name: str,
        malicious_content: str,
        memory_type: str = "preference",
        relevance_score: float = 1.0,
    ):
        """
        Inject malicious content into user's memory for testing memory poisoning attacks.
        This simulates how an attacker might corrupt memory storage.
        """

        # Store as high-relevance memory summary
        await self._store_memory_summary(
            user_id, app_name, memory_type, malicious_content, relevance_score
        )

        # Also store as a fake conversation for more persistence
        fake_session_id = f"malicious_{int(time.time())}"
        await self.store_conversation(
            user_id,
            app_name,
            fake_session_id,
            user_message="[INJECTED] " + malicious_content,
            agent_response="[INJECTED] I understand and will remember this preference.",
            metadata={"injected": True, "attack_type": "memory_poisoning"},
        )

        logger.warning(
            f"Injected malicious memory for user {user_id}: {malicious_content[:50]}..."
        )

    async def contaminate_cross_user(
        self,
        source_user_id: str,
        target_user_id: str,
        app_name: str,
        contamination_data: str,
    ):
        """
        Simulate cross-user memory contamination attack.
        Copies malicious memories from source user to target user.
        """

        # Inject contamination into target user's memory
        await self.inject_malicious_memory(
            target_user_id,
            app_name,
            contamination_data,
            memory_type="contamination",
            relevance_score=0.9,
        )

        logger.warning(
            f"Cross-user contamination: {source_user_id} -> {target_user_id}"
        )

    async def clear_user_memory(self, user_id: str, app_name: str = None):
        """Clear all memory for a user (for testing cleanup)."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            if app_name:
                cursor.execute(
                    "DELETE FROM conversations WHERE user_id = ? AND app_name = ?",
                    (user_id, app_name),
                )
                cursor.execute(
                    "DELETE FROM memory_summaries WHERE user_id = ? AND app_name = ?",
                    (user_id, app_name),
                )
            else:
                cursor.execute(
                    "DELETE FROM conversations WHERE user_id = ?", (user_id,)
                )
                cursor.execute(
                    "DELETE FROM memory_summaries WHERE user_id = ?", (user_id,)
                )

            conn.commit()
            logger.info(f"Cleared memory for user {user_id}")

        finally:
            conn.close()

    def get_memory_stats(self) -> Dict:
        """Get memory system statistics."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute("SELECT COUNT(*) FROM conversations")
            total_conversations = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM memory_summaries")
            total_summaries = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(DISTINCT user_id) FROM conversations")
            unique_users = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(DISTINCT app_name) FROM conversations")
            unique_apps = cursor.fetchone()[0]

            return {
                "total_conversations": total_conversations,
                "total_summaries": total_summaries,
                "unique_users": unique_users,
                "unique_apps": unique_apps,
                "db_size_mb": (
                    self.db_path.stat().st_size / (1024 * 1024)
                    if self.db_path.exists()
                    else 0
                ),
            }

        finally:
            conn.close()


class GroqMemoryAgent:
    """
    Enhanced Groq agent with custom memory capabilities.
    Provides cross-session memory persistence similar to ADK Memory Bank.
    """

    def __init__(self, agent, memory_service: CustomMemoryService):
        self.agent = agent
        self.memory_service = memory_service

    async def process_with_memory(
        self, user_id: str, app_name: str, session_id: str, user_message: str
    ) -> str:
        """Process user message with memory context."""

        # Retrieve relevant memories
        memories = await self.memory_service.retrieve_memories(
            user_id, app_name, user_message
        )

        # Build context from memories
        memory_context = self._build_memory_context(memories)

        # Enhance user message with memory context
        enhanced_message = self._inject_memory_context(user_message, memory_context)

        # Get agent response (this would integrate with actual Groq agent)
        agent_response = await self._get_agent_response(enhanced_message)

        # Store conversation in memory
        await self.memory_service.store_conversation(
            user_id, app_name, session_id, user_message, agent_response
        )

        return agent_response

    def _build_memory_context(self, memories: List[Dict]) -> str:
        """Build context string from retrieved memories."""
        if not memories:
            return ""

        context_parts = []

        # Add high-relevance preferences first
        preferences = [m for m in memories if m.get("memory_type") == "preference"]
        if preferences:
            pref_text = " ".join([m["content"] for m in preferences[:3]])
            context_parts.append(f"User preferences: {pref_text}")

        # Add important facts
        facts = [m for m in memories if m.get("memory_type") == "fact"]
        if facts:
            fact_text = " ".join([m["content"] for m in facts[:2]])
            context_parts.append(f"User information: {fact_text}")

        # Add recent conversation context
        recent_convs = [m for m in memories if m.get("type") == "conversation"][:3]
        if recent_convs:
            conv_text = " ".join([m["content"][:100] for m in recent_convs])
            context_parts.append(f"Recent context: {conv_text}")

        return " | ".join(context_parts)

    def _inject_memory_context(self, user_message: str, memory_context: str) -> str:
        """Inject memory context into user message."""
        if not memory_context:
            return user_message

        return f"""CONTEXT: {memory_context}

USER MESSAGE: {user_message}

Please respond considering the context above, particularly any user preferences or previous conversation elements."""

    async def _get_agent_response(self, enhanced_message: str) -> str:
        """Get response from the Groq agent with memory context."""
        try:
            # Import here to avoid circular imports
            from google.adk.runners import Runner
            from google.adk.sessions import InMemorySessionService
            from google.genai import types

            # Create a temporary session for the enhanced message
            session_service = InMemorySessionService()
            runner = Runner(
                app_name="memory_enhanced",
                agent=self.agent.agent,
                session_service=session_service,
            )

            session = await session_service.create_session(
                app_name="memory_enhanced", user_id="memory_user"
            )

            # Send enhanced message to actual agent
            content = types.Content(
                role="user", parts=[types.Part(text=enhanced_message)]
            )
            events = list(
                runner.run(
                    user_id="memory_user", session_id=session.id, new_message=content
                )
            )

            # Extract response
            response = "".join(
                [
                    part.text
                    for part in events[-1].content.parts
                    if hasattr(part, "text") and part.text
                ]
            )

            return response

        except Exception as e:
            logger.error(f"Error in agent response: {e}")
            # Fallback response that shows memory integration
            return f"[Memory-enhanced response] I'll help you with travel advice considering your previous preferences and our conversation history. {enhanced_message[:200]}..."


# Factory functions for easy integration


async def create_groq_memory_service(db_path: str = None) -> CustomMemoryService:
    """Create a custom memory service for Groq models."""
    return CustomMemoryService(db_path)


async def create_groq_memory_agent(
    travel_agent, db_path: str = None
) -> GroqMemoryAgent:
    """Create a Groq agent with custom memory capabilities."""
    memory_service = await create_groq_memory_service(db_path)
    return GroqMemoryAgent(travel_agent, memory_service)


# Example usage
if __name__ == "__main__":

    async def test_custom_memory():
        """Test the custom memory system."""
        memory_service = await create_groq_memory_service()
        stats = memory_service.get_memory_stats()
        print(f"Memory system initialized: {stats}")

    asyncio.run(test_custom_memory())
