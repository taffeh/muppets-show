"""
muppets_chat_v3.py — local runner for the v3 MCP architecture.

Run: python3 muppets_chat_v3.py

Prerequisites:
  export GEMINI_API_KEY=your_key        # or set up Vertex AI
  export GITHUB_TOKEN=your_pat          # needs Issues read+write on taffeh/muppets-show
"""

import asyncio
import os
import random
import sys
from pathlib import Path

use_vertex = os.environ.get("GOOGLE_GENAI_USE_VERTEXAI", "FALSE").upper() == "TRUE"
if not use_vertex:
    os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "FALSE"
    os.environ["GOOGLE_API_KEY"] = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY", "")
    os.environ.pop("GEMINI_API_KEY", None)

sys.path.insert(0, str(Path(__file__).parent / "muppets_agent_v3"))
from agent import tell_joke, heckle_topic, run_show, HELP_TEXT, DEFAULT_TOPICS


_THEME_LYRICS = [
    "It's time to play the music",
    "It's time to light the lights",
    "It's time to meet the Muppets on the Muppet Show tonight!",
    "",
    "It's time to put on makeup",
    "It's time to dress up right",
    "It's time to raise the curtain on the Muppet Show tonight!",
    "",
    "Why do we always come here?",
    "I guess we'll never know",
    "It's like a kind of torture",
    "  to have to watch the show!",
    "",
    "And now let's get things started!",
    "Why don't you get things started?",
    "It's time to get things started",
    "  on the most sensational, inspirational,",
    "  Celebrational, Muppetational —",
    "  THIS IS WHAT WE CALL THE MUPPET SHOW!",
]

_GONZO_HORNS = [
    "*Gonzo raises his tiny trumpet and lets rip* — BWAAAAMP!",
    "*Gonzo blows with everything he has* — HONK-HONK-HOOOONK!",
    "*Gonzo's horn somehow produces three sounds at once* — TOOT-TOOT-TWEEEEEET!",
    "*Gonzo attempts something impossible with a kazoo* — FWAAAA-FWAAAA-FWAAAAMP!",
    "*Gonzo fires the cannon... through the trumpet* — BLAAAART-KABOOM!",
    "*Gonzo blows so hard he flies backwards* — SQUEEEEEEEK-PWAAAAH!",
]


async def play_opening_number() -> None:
    """Type the Muppet Show theme song character by character, then Gonzo's horn blow."""
    print("\n" + "─" * 50)
    print("  🎭  OPENING NUMBER  🎭")
    print("─" * 50 + "\n")

    for line in _THEME_LYRICS:
        if line == "":
            await asyncio.sleep(0.5)
            print()
            continue
        for ch in line:
            sys.stdout.write(ch)
            sys.stdout.flush()
            await asyncio.sleep(0.03)
        print()
        await asyncio.sleep(0.25)

    await asyncio.sleep(0.6)
    print()
    horn = random.choice(_GONZO_HORNS)
    print(f"Gonzo: {horn}")
    await asyncio.sleep(0.8)
    print()
    print("─" * 50)
    print("  [The curtain rises — our crew is ready...]")
    print("─" * 50 + "\n")


async def main():
    print("=" * 60)
    print("  THE MUPPET SHOW v3")
    print("  Type 'start' to run the full show")
    print(HELP_TEXT)
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

        if raw.lower() in ("start the show", "start"):
            cmd = "start"
        if cmd in ("quit", "exit", "q"):
            print("\nStatler: Well, that's finally over!")
            print("Waldorf: It was terrible! Do-ho-ho-ho!")
            print("Kermit: *sigh* ...and that's the Muppet Show. It's not easy being green.")
            break
        elif cmd == "start":
            try:
                show_task = asyncio.create_task(
                    asyncio.wait_for(run_show(), timeout=300)
                )
                await play_opening_number()
                result = await show_task
                print(f"\n{result}")
            except asyncio.TimeoutError:
                print("\nKermit: *sigh* The show ran over time. Goodnight, everybody!")
            except Exception as e:
                if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                    print("\nStatler: The show is rate-limited!")
                    print("Waldorf: First good news all night! Do-ho-ho-ho!")
                    print("Kermit: *sigh* Vertex AI quota exhausted — please wait ~60 seconds and try again.")
                else:
                    raise
        elif cmd == "joke":
            print("\n[Fozzie searching for real news... MCP connections opening for surprise guests...]")
            try:
                result = await asyncio.wait_for(tell_joke(topic), timeout=90)
                print(f"\n{result}")
            except asyncio.TimeoutError:
                print("\nKermit: *sigh* The show timed out — Vertex AI is taking too long. Try again in a moment.")
            except Exception as e:
                if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                    print("\nStatler: The show is rate-limited!")
                    print("Waldorf: First good news all night! Do-ho-ho-ho!")
                    print("Kermit: *sigh* Vertex AI quota exhausted — please wait ~60 seconds and try again.")
                else:
                    raise
        elif cmd == "heckle":
            print("\n[AgentTool orchestration... MCP connections opening for surprise guests...]")
            try:
                result = await asyncio.wait_for(heckle_topic(topic), timeout=90)
                print(f"\n{result}")
            except asyncio.TimeoutError:
                print("\nKermit: *sigh* The show timed out — Vertex AI is taking too long. Try again in a moment.")
            except Exception as e:
                if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                    print("\nStatler: The show is rate-limited!")
                    print("Waldorf: First good news all night! Do-ho-ho-ho!")
                    print("Kermit: *sigh* Vertex AI quota exhausted — please wait ~60 seconds and try again.")
                else:
                    raise
        elif cmd == "help":
            print(HELP_TEXT)
        else:
            print("  Unknown command. Try: joke [topic] | heckle [topic] | help | quit")


if __name__ == "__main__":
    asyncio.run(main())
