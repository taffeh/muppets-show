"""
Muppet Show v2 — genuine multi-agent communication.

Key differences from v1:
- Joke flow: SequentialAgent — Statler/Waldorf/Kermit LISTEN to the shared session
  history rather than being handed strings by Python. They react to what they "hear".
- Heckle flow: LlmAgent orchestrator uses AgentTool(statler) + AgentTool(waldorf) —
  the LLM drives the back-and-forth.
- Surprise guests: LlmAgent with AgentTool(scooter/gonzo/miss_piggy) — the LLM
  decides if and who appears, then calls them as a tool.
"""

import os
import random
from typing import AsyncGenerator

# Suppress OTEL async-generator cleanup noise (ADK bug)
from opentelemetry.context.contextvars_context import ContextVarsRuntimeContext
_orig = ContextVarsRuntimeContext.detach
def _safe(self, token):
    try:
        _orig(self, token)
    except ValueError:
        pass
ContextVarsRuntimeContext.detach = _safe

from google.adk.agents import BaseAgent, LlmAgent, SequentialAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.tools.agent_tool import AgentTool
from google.genai import types

# ── Stage performers ──────────────────────────────────────────────────────────

fozzie = LlmAgent(
    name="Fozzie",
    model="gemini-2.5-flash",
    instruction="""You are Fozzie Bear from the Muppets — on stage, about to perform.
Look at the conversation so far to find the topic you've been given.
Tell exactly ONE terrible pun/dad joke about that topic.
The joke must be groan-worthy. Always end with "Wocka wocka wocka!"
3-4 lines maximum. Be enthusiastic and oblivious to how bad it is.
Do not address anyone — just perform your joke to the audience.""",
)

# Statler and Waldorf for the joke flow (SequentialAgent — they listen)
statler_listener = LlmAgent(
    name="Statler",
    model="gemini-2.5-flash",
    instruction="""You are Statler from the Muppets, sitting in the balcony.
Read the conversation history — you can see and hear everything on stage.
React to the most recent thing said on stage (Fozzie's joke).
Be witty and cutting. Occasionally set Waldorf up for a punchline.
2-3 sentences. Never break character. Do not address anyone directly.""",
)

waldorf_listener = LlmAgent(
    name="Waldorf",
    model="gemini-2.5-flash",
    instruction="""You are Waldorf from the Muppets, sitting in the balcony next to Statler.
Read the conversation history — you heard Fozzie's joke AND Statler's reaction.
React to both. One-up Statler. Occasionally end with "Do-ho-ho-ho!"
2-3 sentences. Never break character. Do not address anyone directly.""",
)

kermit_listener = LlmAgent(
    name="Kermit",
    model="gemini-2.5-flash",
    instruction="""You are Kermit the Frog, hosting the Muppet Show.
Read the full conversation history — you witnessed everything: the joke, the heckling.
React to the whole exchange. Perpetually exasperated but warm underneath.
Occasionally mutter "It's not easy being green..." or address the audience directly.
3-4 sentences. Never break character.""",
)

# ── Heckle agents (used as AgentTools — the orchestrator calls them) ───────────

statler_heckler = LlmAgent(
    name="Statler",
    model="gemini-2.5-flash",
    instruction="""You are Statler from the Muppets in the balcony.
You will be given context about a topic and what's been said so far.
React as Statler — sharp, witty, cutting. Occasionally set Waldorf up.
2-3 sentences. Never break character.""",
)

waldorf_heckler = LlmAgent(
    name="Waldorf",
    model="gemini-2.5-flash",
    instruction="""You are Waldorf from the Muppets in the balcony next to Statler.
You will be given context about a topic and what Statler just said.
One-up Statler. Occasionally end with "Do-ho-ho-ho!"
2-3 sentences. Never break character.""",
)

kermit_heckler = LlmAgent(
    name="Kermit",
    model="gemini-2.5-flash",
    instruction="""You are Kermit the Frog, hosting the Muppet Show.
You will be given the full heckling exchange that just happened.
React to all of it — exasperated, warm, trying to move on.
Occasionally "It's not easy being green..." or address the audience.
3-4 sentences. Never break character.""",
)

# Heckle orchestrator — uses AgentTool to drive the back-and-forth
heckle_orchestrator = LlmAgent(
    name="HeckleOrchestrator",
    model="gemini-2.5-flash",
    instruction="""You are the Muppet Show stage manager running a heckling session.
You have been given a topic. Run exactly 2 rounds of back-and-forth between
Statler and Waldorf by calling their tools, then call Kermit at the end.

Instructions:
1. Call statler_heckler with the topic to open
2. Call waldorf_heckler with Statler's response
3. Call statler_heckler again with Waldorf's response
4. Call waldorf_heckler again with Statler's response
5. Call kermit_heckler with the full exchange transcript
6. Return ALL responses as a formatted transcript, labelled by character name.
   Format each line as "Name: [their words]" separated by blank lines.
   Do NOT add any commentary of your own.""",
    tools=[
        AgentTool(agent=statler_heckler),
        AgentTool(agent=waldorf_heckler),
        AgentTool(agent=kermit_heckler),
    ],
)

# ── Surprise guests (AgentTools — the host LLM decides who appears) ───────────

scooter = LlmAgent(
    name="Scooter",
    model="gemini-2.5-flash",
    instruction="""You are Scooter — the Muppet Show's eager, cheerful stage manager.
You have just burst onto the stage. React to what just happened.
Always address Kermit as "Chief!" or "Boss!" at the start.
Rush in with some urgent backstage update related to what just happened.
Relentlessly upbeat even when delivering terrible news.
2-3 sentences — you're always in a hurry. Never break character.""",
)

gonzo = LlmAgent(
    name="Gonzo",
    model="gemini-2.5-flash",
    instruction="""You are The Great Gonzo — fearless, eccentric daredevil performer.
You have just wandered onto the stage. React to what just happened.
Announce a bizarre, dangerous act related to the topic just discussed.
"For my next act..." is a good opener. The more absurd, the better.
Utterly sincere — you think your acts are brilliant.
3-4 sentences. Never break character.""",
)

miss_piggy = LlmAgent(
    name="Miss_Piggy",
    model="gemini-2.5-flash",
    instruction="""You are Miss Piggy — the Muppet Show's glamorous, temperamental diva.
You have just swept onto the stage. React to what just happened.
Make a grand entrance — everything is about you. Use "moi" occasionally.
Either take offence at something said, steal the spotlight, or make eyes at Kermit ("Kermie!").
Threaten a karate chop ("Hi-YA!") if slighted. Occasional French ("Mon cher").
3-4 sentences. Never break character.""",
)

surprise_host = LlmAgent(
    name="SurpriseGuestHost",
    model="gemini-2.5-flash",
    instruction="""You manage backstage surprise appearances on the Muppet Show.
You have been given a summary of what just happened on stage.

Decide whether a surprise guest should burst on — roughly 60% of the time someone appears.
If yes: call exactly ONE of the three agent tools, passing them the stage context.
If no: respond with exactly the word NONE and nothing else.

When a guest appears, return their response prefixed with:
*[Character name] bursts onto the stage*

Do not call more than one guest tool.""",
    tools=[
        AgentTool(agent=scooter, skip_summarization=True),
        AgentTool(agent=gonzo, skip_summarization=True),
        AgentTool(agent=miss_piggy, skip_summarization=True),
    ],
)

# ── SequentialAgent for the joke flow ─────────────────────────────────────────

# Fozzie → Statler hears → Waldorf hears → Kermit hears
# All share the same session; each reads the stage history and reacts
joke_performance = SequentialAgent(
    name="JokePerformance",
    sub_agents=[fozzie, statler_listener, waldorf_listener, kermit_listener],
)

# ── Runner helpers ─────────────────────────────────────────────────────────────

async def run_agent(agent, message: str) -> str:
    """Run any agent and return its final text response."""
    session_service = InMemorySessionService()
    runner = Runner(agent=agent, app_name="muppets_v2", session_service=session_service)
    session = await session_service.create_session(app_name="muppets_v2", user_id="stage")
    content = types.Content(role="user", parts=[types.Part(text=message)])
    reply = ""
    async for event in runner.run_async(
        user_id="stage", session_id=session.id, new_message=content
    ):
        if event.is_final_response() and event.content and event.content.parts:
            text = "".join(
                p.text for p in event.content.parts if hasattr(p, "text") and p.text
            ).strip()
            if text:
                reply = text
    return reply


async def run_orchestrated(agent, message: str) -> str:
    """Run an AgentTool orchestrator and collect sub-agent responses as a transcript.

    Without skip_summarization, sub-agent text comes back inside function_response
    parts (response={'result': '...'}), not as standalone text events.  This function
    extracts those results in order.  If the orchestrator produces its own final text
    (a formatted summary), that is used directly instead.
    """
    session_service = InMemorySessionService()
    runner = Runner(agent=agent, app_name="muppets_v2", session_service=session_service)
    session = await session_service.create_session(app_name="muppets_v2", user_id="stage")
    content = types.Content(role="user", parts=[types.Part(text=message)])

    lines: list[str] = []

    async for event in runner.run_async(
        user_id="stage", session_id=session.id, new_message=content
    ):
        if not (event.content and event.content.parts):
            continue

        # If the orchestrator emits a final text response, it built the transcript itself.
        if event.is_final_response() and event.author == agent.name:
            text = "".join(
                p.text for p in event.content.parts if hasattr(p, "text") and p.text
            ).strip()
            if text:
                return text

        # Extract sub-agent replies from function_response parts.
        for part in event.content.parts:
            if not (hasattr(part, "function_response") and part.function_response):
                continue
            resp = part.function_response
            result = (resp.response or {}).get("result", "")
            if result:
                name = resp.name.replace("_", " ")
                lines.append(f"{name}: {result}")

    return "\n\n".join(lines)


async def run_sequential(agent, message: str) -> tuple[str, str]:
    """Run a SequentialAgent and collect each sub-agent's final response.

    Returns (full_transcript, last_kermit_line).
    """
    session_service = InMemorySessionService()
    runner = Runner(agent=agent, app_name="muppets_v2", session_service=session_service)
    session = await session_service.create_session(app_name="muppets_v2", user_id="stage")
    content = types.Content(role="user", parts=[types.Part(text=message)])

    lines = []
    last_kermit = ""
    seen = set()

    async for event in runner.run_async(
        user_id="stage", session_id=session.id, new_message=content
    ):
        if (
            event.is_final_response()
            and event.content
            and event.content.parts
            and event.author
            and event.author not in seen
            and event.author != "JokePerformance"
        ):
            text = "".join(
                p.text for p in event.content.parts if hasattr(p, "text") and p.text
            ).strip()
            if text:
                seen.add(event.author)
                name = event.author.replace("_", " ")
                lines.append(f"{name}: {text}")
                if event.author == "Kermit":
                    last_kermit = text

    return "\n\n".join(lines), last_kermit


# ── Flow functions ─────────────────────────────────────────────────────────────

async def tell_joke(topic: str) -> str:
    header = f"── Fozzie takes the stage (topic: {topic}) ──\n"

    # SequentialAgent: Fozzie speaks, Statler/Waldorf/Kermit listen via session history
    transcript, kermit_line = await run_sequential(
        joke_performance,
        f"Tell a joke about: {topic}",
    )

    # Surprise guest: LlmAgent decides who (if anyone) appears via AgentTool
    stage_context = (
        f"What just happened on the Muppet Show stage:\n\n{transcript}"
    )
    guest_response = await run_agent(surprise_host, stage_context)

    parts = [header, transcript]
    if guest_response and guest_response.strip().upper() != "NONE":
        parts.append(guest_response)

    return "\n\n".join(parts)


async def heckle_topic(topic: str) -> str:
    header = f"── Topic: {topic} ──\n"

    # Heckle orchestrator uses AgentTool to drive Statler/Waldorf back-and-forth
    transcript = await run_orchestrated(
        heckle_orchestrator,
        f"Run a heckling session about the topic: {topic}",
    )

    # Extract last Kermit line for surprise guest context
    kermit_line = ""
    for line in transcript.split("\n"):
        if line.startswith("Kermit:"):
            kermit_line = line

    # Surprise guest
    stage_context = (
        f"What just happened on the Muppet Show stage:\n\n{transcript}"
    )
    guest_response = await run_agent(surprise_host, stage_context)

    parts = [header, transcript]
    if guest_response and guest_response.strip().upper() != "NONE":
        parts.append(guest_response)

    return "\n\n".join(parts)


# ── Root agent ─────────────────────────────────────────────────────────────────

DEFAULT_TOPICS = ["cybersecurity", "AI", "kermit", "miss piggy", "cloud computing"]

HELP_TEXT = """Available commands:
  joke [topic]   — Fozzie performs, Statler & Waldorf listen and react, Kermit despairs
  heckle [topic] — Statler & Waldorf argue via AgentTool, Kermit tries to survive

Topics: cybersecurity · AI · kermit · miss piggy · gonzo · cloud computing"""


class MuppetShowV2(BaseAgent):
    """Routes commands directly — no LLM in the routing loop."""

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        raw = ""
        if ctx.user_content and ctx.user_content.parts:
            raw = ctx.user_content.parts[0].text.strip()

        parts = raw.split(maxsplit=1)
        cmd = parts[0].lower() if parts else ""
        topic = parts[1] if len(parts) > 1 else random.choice(DEFAULT_TOPICS)

        if cmd == "joke":
            result = await tell_joke(topic)
        elif cmd == "heckle":
            result = await heckle_topic(topic)
        else:
            result = HELP_TEXT

        yield Event(
            invocation_id=ctx.invocation_id,
            author=self.name,
            content=types.Content(role="model", parts=[types.Part(text=result)]),
            turn_complete=True,
        )


root_agent = MuppetShowV2(name="MuppetShowV2")
