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
            print("\n[🎭 The curtain rises on tonight's Muppet Show...]")
            try:
                result = await asyncio.wait_for(run_show(), timeout=300)
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
