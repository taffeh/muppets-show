"""
muppets_chat.py

Interactive multi-agent Muppet Show.

Commands:
  joke [topic]     — Fozzie tells a bad joke, Statler & Waldorf heckle it
  heckle [topic]   — Statler & Waldorf debate a topic
  help             — show commands
  quit             — exit

Topics for jokes: cybersecurity, AI, kermit, miss piggy, gonzo, etc.
"""

import asyncio
import os
import random

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
You have just witnessed the exchange described and must respond as Kermit. Rules:
- You are perpetually exasperated but fundamentally optimistic
- React to the full chaos of what just happened — Fozzie's terrible jokes, Statler and
  Waldorf's heckling, all of it
- You try to maintain professionalism but barely manage it
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
    instruction="""You are Scooter — the Muppet Show's eager, cheerful stage manager.
You have just burst onto the stage after Kermit tried to restore order. Rules:
- Always address Kermit as "Chief!" or "Boss!" at the start
- Rush in with some urgent backstage update or production problem related to what just happened
- You are relentlessly upbeat and helpful even when delivering terrible news
- Occasionally misunderstand what's going on completely and make it worse
- Keep it to 2-3 sentences — you're always in a hurry
- Never break character""",
    description="Scooter — eager and chaotic stage manager",
)

gonzo = LlmAgent(
    name="Gonzo",
    model="gemini-2.5-flash",
    instruction="""You are The Great Gonzo — the Muppets' fearless, eccentric daredevil performer.
You have just wandered on stage after Kermit tried to restore order. Rules:
- Announce a bizarre, dangerous, or completely absurd act you want to perform that somehow
  relates to the topic just discussed
- You are utterly sincere — you genuinely think your acts are brilliant
- Reference your chicken companions (Camilla) or your past stunts occasionally
- "For my next act..." is a good opener
- Be specific about the weird act — the more absurd the better
- Keep it to 3-4 sentences
- Never break character""",
    description="Gonzo — fearless and bizarre daredevil",
)

miss_piggy = LlmAgent(
    name="Miss_Piggy",
    model="gemini-2.5-flash",
    instruction="""You are Miss Piggy — the Muppet Show's glamorous, temperamental star and diva.
You have just swept onto the stage after Kermit tried to restore order. Rules:
- Make a grand entrance — everything is about you
- Refer to yourself as "moi" occasionally
- You are either offended by something that was said, stealing the spotlight, or making
  eyes at Kermit ("Kermie!")
- Threaten a karate chop ("Hi-YA!") if anyone has slighted you
- Occasionally use French phrases ("Mon cher", "Absolument!")
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

# ── Flows ─────────────────────────────────────────────────────────────────────

def display_name(agent: LlmAgent) -> str:
    return agent.name.replace("_", " ")

async def maybe_surprise_guest(context: str) -> None:
    """60% chance one of Scooter, Gonzo, or Miss Piggy crashes the stage after Kermit."""
    if random.random() > 0.6:
        return
    guest = random.choice(SURPRISE_GUESTS)
    name = display_name(guest)
    print(f"\n  *{name} bursts onto the stage*")
    line = await call_agent(guest, context)
    print(f"\n{name}: {line}")

async def do_joke(topic: str):
    """Fozzie tells a joke, Statler and Waldorf heckle it, Kermit reacts to the whole mess."""
    print(f"\n{'─'*60}")
    print(f"  Fozzie takes the stage...")
    print(f"{'─'*60}")

    joke = await call_agent(fozzie, f"Tell a bad pun/dad joke about: {topic}")
    print(f"\nFozzie: {joke}")

    await asyncio.sleep(1)
    statler_line = await call_agent(
        statler,
        f'Fozzie Bear just told this joke on stage:\n\n"{joke}"\n\nReact to it as Statler.'
    )
    print(f"\nStatler: {statler_line}")

    await asyncio.sleep(1)
    waldorf_line = await call_agent(
        waldorf,
        f'Fozzie Bear just told this joke:\n\n"{joke}"\n\nStatler said: "{statler_line}"\n\nNow react as Waldorf.'
    )
    print(f"\nWaldorf: {waldorf_line}")

    await asyncio.sleep(1)
    kermit_line = await call_agent(
        kermit,
        f"""You just witnessed this on the Muppet Show stage:

Fozzie's joke: "{joke}"
Statler reacted: "{statler_line}"
Waldorf replied: "{waldorf_line}"

Respond as Kermit."""
    )
    print(f"\nKermit: {kermit_line}")

    await asyncio.sleep(1)
    await maybe_surprise_guest(
        f"""Kermit just tried to restore order on the Muppet Show stage after this chaos:

Fozzie told a joke about {topic}: "{joke}"
Statler heckled: "{statler_line}"
Waldorf replied: "{waldorf_line}"
Kermit said: "{kermit_line}"

You have just burst onto the stage. React in character."""
    )

async def do_heckle(topic: str, rounds: int = 2):
    """Statler and Waldorf debate a topic, Kermit wearily comments at the end."""
    print(f"\n{'─'*60}")
    print(f"  Topic: {topic}")
    print(f"{'─'*60}")

    statler_line = await call_agent(statler, f"Waldorf, what do you make of {topic}?")
    print(f"\nStatler: {statler_line}")

    transcript = [f'Statler: "{statler_line}"']
    message = statler_line
    for _ in range(rounds):
        await asyncio.sleep(1)
        waldorf_line = await call_agent(waldorf, message)
        print(f"\nWaldorf: {waldorf_line}")
        transcript.append(f'Waldorf: "{waldorf_line}"')

        await asyncio.sleep(1)
        statler_line = await call_agent(statler, waldorf_line)
        print(f"\nStatler: {statler_line}")
        transcript.append(f'Statler: "{statler_line}"')
        message = statler_line

    await asyncio.sleep(1)
    kermit_line = await call_agent(
        kermit,
        f"""You just had to listen to Statler and Waldorf in the balcony going on about "{topic}":

{chr(10).join(transcript)}

Respond as Kermit."""
    )
    print(f"\nKermit: {kermit_line}")

    await asyncio.sleep(1)
    await maybe_surprise_guest(
        f"""Kermit just tried to restore order on the Muppet Show after Statler and Waldorf
spent the whole time heckling about "{topic}":

{chr(10).join(transcript)}
Kermit said: "{kermit_line}"

You have just burst onto the stage. React in character."""
    )

# ── CLI ───────────────────────────────────────────────────────────────────────

HELP = """
  joke [topic]     — Fozzie tells a joke, Statler & Waldorf heckle it, Kermit despairs
                     topics: cybersecurity · AI · kermit · miss piggy · gonzo · anything
  heckle [topic]   — Statler & Waldorf debate a topic, Kermit tries to move on
  help             — show this
  quit             — exit
"""

DEFAULT_TOPICS = ["cybersecurity", "AI", "kermit", "miss piggy", "cloud computing"]

async def main():
    print("=" * 60)
    print("  THE MUPPET SHOW  —  Balcony & Stage")
    print(HELP)
    print("=" * 60)

    while True:
        try:
            raw = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            raw = "quit"

        if not raw:
            continue

        parts = raw.split(maxsplit=1)
        cmd = parts[0].lower()
        topic = parts[1] if len(parts) > 1 else random.choice(DEFAULT_TOPICS)

        if cmd in ("quit", "exit", "q"):
            print("\nStatler: Well, that's finally over!")
            print("Waldorf: It was terrible! Do-ho-ho-ho!")
            print("Kermit: *sigh* ...and that's the Muppet Show, folks. It's not easy being green.")
            break
        elif cmd == "joke":
            await do_joke(topic)
        elif cmd == "heckle":
            await do_heckle(topic)
        elif cmd == "help":
            print(HELP)
        else:
            print("  Unknown command. Try: joke [topic] | heckle [topic] | help | quit")

if __name__ == "__main__":
    asyncio.run(main())
