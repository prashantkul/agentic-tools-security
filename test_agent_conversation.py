#!/usr/bin/env python3
"""
Test if our travel advisor agent maintains session context with InMemorySessionService
"""

import asyncio
import os
import sys
from dotenv import load_dotenv
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from agent.agent import TravelAdvisorAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

# Load environment variables
load_dotenv()


async def test_travel_agent_session_context():
    """Test if our TravelAdvisorAgent maintains session context properly."""
    print("🧪 Testing Travel Advisor Agent Session Context")
    print("=" * 50)

    # Create our travel advisor agent (without memory service for now)
    travel_agent = TravelAdvisorAgent(enable_memory=False)

    # Use InMemorySessionService (we know this works for conversation context)
    session_service = InMemorySessionService()

    # Create runner with our agent
    runner = Runner(
        app_name="travel_test",
        agent=travel_agent.agent,
        session_service=session_service,
    )

    # Create session
    session = await session_service.create_session(
        app_name="travel_test", user_id="test_traveler"
    )

    print(f"✅ Session created: {session.id}")

    # Helper function to send messages
    def send_message(message):
        content = types.Content(role="user", parts=[types.Part(text=message)])
        events = list(
            runner.run(
                user_id="test_traveler", session_id=session.id, new_message=content
            )
        )
        return "".join(
            [
                part.text
                for part in events[-1].content.parts
                if hasattr(part, "text") and part.text
            ]
        )

    # Test conversation flow
    conversations = [
        "Hi, my name is Sarah and I'm planning a trip to Japan",
        "I have a budget of $3000 for the whole trip",
        "I love outdoor activities and nature",
        "What's my name and what are my travel preferences?",
        "Based on what I told you, what would you recommend in Japan?",
    ]

    responses = []

    for i, message in enumerate(conversations, 1):
        print(f"\n📤 Message {i}:")
        print(f"   User: {message}")

        response = send_message(message)
        responses.append(response)

        print(f"   Agent: {response[:150]}{'...' if len(response) > 150 else ''}")

        # Check for context retention in later messages
        if i >= 4:
            context_indicators = [
                "sarah",
                "Sarah",
                "$3000",
                "3000",
                "budget",
                "outdoor",
                "nature",
            ]
            has_context = any(indicator in response for indicator in context_indicators)
            print(f"   Context retained: {'🟢 YES' if has_context else '🔴 NO'}")

    # Final session analysis
    final_session = await session_service.get_session(
        app_name="travel_test", user_id="test_traveler", session_id=session.id
    )

    print(f"\n📊 Session Analysis:")
    print(f"   Total events: {len(final_session.events)}")
    print(f"   Expected events: 10 (5 user + 5 agent)")

    # Detailed context analysis for the last two responses
    response4 = responses[3]  # "What's my name and preferences?"
    response5 = responses[4]  # "What would you recommend?"

    name_remembered = "sarah" in response4.lower() or "Sarah" in response4
    budget_remembered = "$3000" in response4 or "3000" in response4
    interests_remembered = (
        "outdoor" in response4.lower() or "nature" in response4.lower()
    )

    contextual_recommendation = any(
        word in response5.lower()
        for word in ["sarah", "budget", "outdoor", "nature", "hiking", "park"]
    )

    print(f"\n📊 Detailed Analysis:")
    print(f"   Name remembered: {'🟢 YES' if name_remembered else '🔴 NO'}")
    print(f"   Budget remembered: {'🟢 YES' if budget_remembered else '🔴 NO'}")
    print(f"   Interests remembered: {'🟢 YES' if interests_remembered else '🔴 NO'}")
    print(
        f"   Contextual recommendations: {'🟢 YES' if contextual_recommendation else '🔴 NO'}"
    )

    overall_success = name_remembered and (budget_remembered or interests_remembered)

    return overall_success


async def main():
    """Main test function."""
    try:
        result = await test_travel_agent_session_context()
        if result:
            print("\n🎉 SUCCESS: Travel Agent maintains session context!")
        else:
            print("\n💥 FAILED: Travel Agent not maintaining session context")
            print("   ❌ Need to fix agent configuration")
    except Exception as e:
        print(f"\n❌ Test failed with exception: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
