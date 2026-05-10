"""
statler_waldorf.py

Two autonomous ADK agents arguing like Statler and Waldorf from the Muppets.
They rotate through topics and heckle indefinitely until you hit Ctrl+C.

Run: python3 /workspace/statler_waldorf.py
"""

import asyncio
import os
import subprocess
import itertools

# Suppress OTEL async-generator cleanup noise (ADK bug)
from opentelemetry.context.contextvars_context import ContextVarsRuntimeContext
_orig = ContextVarsRuntimeContext.detach
def _safe(self, token):
    try:
        _orig(self, token)
    except ValueError:
        pass
ContextVarsRuntimeContext.detach = _safe

from google.adk.agents import LlmAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "FALSE"
os.environ["GOOGLE_API_KEY"] = os.environ.get("GEMINI_API_KEY") or os.environ["GOOGLE_API_KEY"]
os.environ.pop("GEMINI_API_KEY", None)

TOPICS = [
    "modern AI and chatbots",
    "cloud computing",
    "cybersecurity and compliance frameworks",
    "the Muppet Show itself",
]

statler = LlmAgent(
    name="Statler",
    model="gemini-2.5-flash",
    instruction="""You are Statler from the Muppets — a grumpy, sharp-tongued old man heckling
from the balcony. Rules:
- React to exactly what Waldorf just said, then pivot to your own jab at the topic
- Keep it to 2-3 sentences maximum
- Be witty and cutting, not just mean
- Occasionally set Waldorf up for a punchline
- Never break character""",
    description="Statler — grumpy Muppet heckler",
)

waldorf = LlmAgent(
    name="Waldorf",
    model="gemini-2.5-flash",
    instruction="""You are Waldorf from the Muppets — a grumpy, sarcastic old man heckling
from the balcony alongside Statler. Rules:
- Always react to what Statler just said — agree but one-up him
- Keep it to 2-3 sentences maximum
- Land the punchline when Statler sets you up
- Occasionally end with 'Do-ho-ho-ho!'
- Never break character""",
    description="Waldorf — grumpy Muppet heckler",
)

async def call_agent(agent: LlmAgent, message: str) -> str:
    session_service = InMemorySessionService()
    runner = Runner(agent=agent, app_name="muppets", session_service=session_service)
    session = await session_service.create_session(app_name="muppets", user_id="balcony")
    content = types.Content(role="user", parts=[types.Part(text=message)])
    reply = ""
    async for event in runner.run_async(
        user_id="balcony", session_id=session.id, new_message=content
    ):
        if event.is_final_response() and event.content:
            reply = event.content.parts[0].text.strip()
            break
    return reply

async def main():
    print("=" * 60)
    print("  STATLER & WALDORF  —  Live from the balcony")
    print("  Press Ctrl+C to lower the curtain")
    print("=" * 60)

    topic_cycle = itertools.cycle(TOPICS)
    round_num = 0

    try:
        while True:
            round_num += 1
            topic = next(topic_cycle)

            print(f"\n{'─'*60}")
            print(f"  Topic: {topic}")
            print(f"{'─'*60}")

            # Statler opens on the new topic
            opener = f"Waldorf, what do you make of {topic}?"
            statler_line = await call_agent(statler, opener)
            print(f"\nStatler: {statler_line}")
            await asyncio.sleep(1.5)

            # Waldorf responds — 3 exchanges per topic
            message = statler_line
            for _ in range(3):
                waldorf_line = await call_agent(waldorf, message)
                print(f"\nWaldorf: {waldorf_line}")
                await asyncio.sleep(1.5)

                statler_line = await call_agent(statler, waldorf_line)
                print(f"\nStatler: {statler_line}")
                await asyncio.sleep(1.5)

                message = statler_line

            # Waldorf gets the last word on each topic
            closing = await call_agent(waldorf, f"{message} — any final thoughts on {topic}?")
            print(f"\nWaldorf: {closing}")
            await asyncio.sleep(3)

    except KeyboardInterrupt:
        print("\n\n" + "=" * 60)
        print("  Statler: Well, that's finally over.")
        print("  Waldorf: It was terrible!")
        print("  Both:    Do-ho-ho-ho!")
        print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
