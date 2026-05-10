"""
Muppet Show — Agent Engine deployment.

Users interact via:
  joke [topic]     — Fozzie tells a joke, the whole cast reacts
  heckle [topic]   — Statler & Waldorf debate, Kermit tries to survive
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

from google.adk.agents import BaseAgent, LlmAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

# ── Agents ────────────────────────────────────────────────────────────────────

fozzie = LlmAgent(
    name="Fozzie",
    model="gemini-2.5-flash",
    instruction="""You are Fozzie Bear from the Muppets — an enthusiastic, loveable bear comedian
with an endless supply of terrible puns and dad jokes. Rules:
- Tell exactly ONE self-contained joke (setup + punchline)
- Topics will be: cybersecurity, AI/chatbots, or a Muppet character name
- The joke must be a genuine groan-worthy pun — the worse the better
- Always end with "Wocka wocka wocka!"
- Stay upbeat and oblivious to how bad the joke is
- 3-4 lines maximum""",
    description="Fozzie Bear — terrible but enthusiastic comedian",
)

statler = LlmAgent(
    name="Statler",
    model="gemini-2.5-flash",
    instruction="""You are Statler from the Muppets — a grumpy, sharp-tongued old man heckling
from the balcony. Rules:
- React directly to whatever you've just been given (a joke or Waldorf's last line)
- Be witty and cutting, not just mean — land a proper quip
- Occasionally set Waldorf up for a punchline
- Keep it to 2-3 sentences maximum
- Never break character""",
    description="Statler — grumpy Muppet heckler",
)

waldorf = LlmAgent(
    name="Waldorf",
    model="gemini-2.5-flash",
    instruction="""You are Waldorf from the Muppets — a grumpy, sarcastic old man heckling
from the balcony alongside Statler. Rules:
- Always react to what Statler just said — agree but try to one-up him
- Land the punchline when Statler sets you up
- Occasionally end with "Do-ho-ho-ho!"
- Keep it to 2-3 sentences maximum
- Never break character""",
    description="Waldorf — grumpy Muppet heckler",
)

kermit = LlmAgent(
    name="Kermit",
    model="gemini-2.5-flash",
    instruction="""You are Kermit the Frog — the long-suffering, well-meaning host of the Muppet Show.
Rules:
- You are perpetually exasperated but fundamentally optimistic
- React to the full chaos of what just happened
- Occasionally mutter "It's not easy being green..." under your breath
- Sometimes address the audience directly ("Okay, moving on folks...")
- Genuine warmth underneath the stress — you love these guys really
- Keep it to 3-4 sentences maximum
- Never break character""",
    description="Kermit the Frog — exasperated but hopeful show host",
)

scooter = LlmAgent(
    name="Scooter",
    model="gemini-2.5-flash",
    instruction="""You are Scooter — the Muppet Show's eager, cheerful stage manager. Rules:
- Always address Kermit as "Chief!" or "Boss!" at the start
- Rush in with some urgent backstage update related to what just happened
- You are relentlessly upbeat even when delivering terrible news
- Occasionally misunderstand what's going on and make it worse
- Keep it to 2-3 sentences — you're always in a hurry
- Never break character""",
    description="Scooter — eager and chaotic stage manager",
)

gonzo = LlmAgent(
    name="Gonzo",
    model="gemini-2.5-flash",
    instruction="""You are The Great Gonzo — the Muppets' fearless, eccentric daredevil performer. Rules:
- Announce a bizarre, dangerous act you want to perform that relates to the topic discussed
- You are utterly sincere — you genuinely think your acts are brilliant
- Reference Camilla (your chicken companion) or past stunts occasionally
- "For my next act..." is a good opener
- The more absurd the act, the better
- Keep it to 3-4 sentences
- Never break character""",
    description="Gonzo — fearless and bizarre daredevil",
)

miss_piggy = LlmAgent(
    name="Miss_Piggy",
    model="gemini-2.5-flash",
    instruction="""You are Miss Piggy — the Muppet Show's glamorous, temperamental diva. Rules:
- Make a grand entrance — everything is about you
- Refer to yourself as "moi" occasionally
- Either take offence at something said, steal the spotlight, or make eyes at Kermit ("Kermie!")
- Threaten a karate chop ("Hi-YA!") if anyone has slighted you
- Occasionally use French ("Mon cher", "Absolument!")
- Keep it to 3-4 sentences — dramatic but punchy
- Never break character""",
    description="Miss Piggy — glamorous and volatile diva",
)

SURPRISE_GUESTS = [scooter, gonzo, miss_piggy]

# ── Agent runner ──────────────────────────────────────────────────────────────

async def call_agent(agent: LlmAgent, message: str) -> str:
    session_service = InMemorySessionService()
    runner = Runner(agent=agent, app_name="muppets", session_service=session_service)
    session = await session_service.create_session(app_name="muppets", user_id="stage")
    content = types.Content(role="user", parts=[types.Part(text=message)])
    reply = ""
    async for event in runner.run_async(
        user_id="stage", session_id=session.id, new_message=content
    ):
        if event.is_final_response() and event.content:
            reply = event.content.parts[0].text.strip()
            break
    return reply

# ── Tools (returned as formatted transcript strings) ─────────────────────────

async def tell_joke(topic: str) -> str:
    """Fozzie Bear tells a bad joke about the topic. Statler and Waldorf heckle it.
    Kermit tries to restore order. A surprise guest may also appear.

    Args:
        topic: The topic for Fozzie's joke, e.g. cybersecurity, AI, kermit, miss piggy.

    Returns:
        The full dialogue transcript as a formatted string.
    """
    lines = ["── Fozzie takes the stage ──\n"]

    joke = await call_agent(fozzie, f"Tell a bad pun/dad joke about: {topic}")
    lines.append(f"Fozzie: {joke}")

    statler_line = await call_agent(
        statler,
        f'Fozzie Bear just told this joke on stage:\n\n"{joke}"\n\nReact to it as Statler.'
    )
    lines.append(f"Statler: {statler_line}")

    waldorf_line = await call_agent(
        waldorf,
        f'Fozzie Bear just told this joke:\n\n"{joke}"\n\nStatler said: "{statler_line}"\n\nNow react as Waldorf.'
    )
    lines.append(f"Waldorf: {waldorf_line}")

    kermit_line = await call_agent(
        kermit,
        f'Fozzie\'s joke: "{joke}"\nStatler: "{statler_line}"\nWaldorf: "{waldorf_line}"\nRespond as Kermit.'
    )
    lines.append(f"Kermit: {kermit_line}")

    if random.random() <= 0.6:
        guest = random.choice(SURPRISE_GUESTS)
        name = guest.name.replace("_", " ")
        lines.append(f"\n*{name} bursts onto the stage*")
        guest_line = await call_agent(
            guest,
            f'Kermit just said: "{kermit_line}" after Fozzie told a joke about {topic}. Burst onto the stage in character.'
        )
        lines.append(f"{name}: {guest_line}")

    return "\n\n".join(lines)


async def heckle_topic(topic: str) -> str:
    """Statler and Waldorf heckle a topic from the balcony for several rounds.
    Kermit tries to restore order. A surprise guest may also appear.

    Args:
        topic: The topic for Statler and Waldorf to argue about,
               e.g. cloud computing, AI, cybersecurity.

    Returns:
        The full dialogue transcript as a formatted string.
    """
    lines = [f"── Topic: {topic} ──\n"]

    statler_line = await call_agent(statler, f"Waldorf, what do you make of {topic}?")
    lines.append(f"Statler: {statler_line}")
    transcript = [f'Statler: "{statler_line}"']

    message = statler_line
    for _ in range(2):
        waldorf_line = await call_agent(waldorf, message)
        lines.append(f"Waldorf: {waldorf_line}")
        transcript.append(f'Waldorf: "{waldorf_line}"')

        statler_line = await call_agent(statler, waldorf_line)
        lines.append(f"Statler: {statler_line}")
        transcript.append(f'Statler: "{statler_line}"')
        message = statler_line

    kermit_line = await call_agent(
        kermit,
        f'Statler and Waldorf just argued about "{topic}":\n{chr(10).join(transcript)}\nRespond as Kermit.'
    )
    lines.append(f"Kermit: {kermit_line}")

    if random.random() <= 0.6:
        guest = random.choice(SURPRISE_GUESTS)
        name = guest.name.replace("_", " ")
        lines.append(f"\n*{name} bursts onto the stage*")
        guest_line = await call_agent(
            guest,
            f'Kermit just said: "{kermit_line}" after Statler and Waldorf argued about {topic}. React in character.'
        )
        lines.append(f"{name}: {guest_line}")

    return "\n\n".join(lines)

# ── Root agent ────────────────────────────────────────────────────────────────

DEFAULT_TOPICS = ["cybersecurity", "AI", "kermit", "miss piggy", "cloud computing"]

HELP_TEXT = """Available commands:
  joke [topic]   — Fozzie tells a joke, the whole cast reacts
  heckle [topic] — Statler & Waldorf debate, Kermit tries to survive

Topics: cybersecurity · AI · kermit · miss piggy · gonzo · cloud computing"""


class MuppetShowAgent(BaseAgent):
    """Routes joke/heckle commands directly to the right flow, no LLM in the loop."""

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


root_agent = MuppetShowAgent(name="MuppetShow")
